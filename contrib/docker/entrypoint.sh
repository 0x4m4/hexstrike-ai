#!/usr/bin/env bash
###############################################################################
# HexStrike-AI MCP entrypoint
#
#   1) start hexstrike_server.py (Flask REST API) in the background
#   2) health-gate on http://127.0.0.1:$HEXSTRIKE_PORT/health (up to ~60s)
#   3) start the front-end transport on $PORT:
#        default          -> hexstrike_mcp.py as a Streamable HTTP MCP server
#                            (endpoint http://<host>:$PORT/mcp)
#        OPENAPI truthy    -> mcpo, wrapping the stdio MCP client as OpenAPI
#                            (docs at http://<host>:$PORT/docs)
#
# Env vars (with defaults):
#   PORT             default 8000   (the single published port; used by whichever
#                                    transport is active)
#   HEXSTRIKE_PORT   default 8888   (Flask API port; hexstrike_server reads it)
#   OPENAPI          unset          (truthy 1/true/yes/on -> OpenAPI via mcpo)
#   MCPO_API_KEY     optional       (OPENAPI mode only -> mcpo requires this key)
###############################################################################
set -euo pipefail

PORT="${PORT:-${MCPO_PORT:-8000}}"   # MCPO_PORT accepted as a legacy alias
HEXSTRIKE_PORT="${HEXSTRIKE_PORT:-8888}"
MCPO_API_KEY="${MCPO_API_KEY:-}"

HEXSTRIKE_PY=/opt/hexstrike-venv/bin/python
MCPO_BIN=/opt/mcpo-venv/bin/mcpo

SERVER_PID=""

log() { echo "[entrypoint] $*"; }

cleanup() {
    # The front-end (MCP server or mcpo) is the primary/foreground service but is
    # backgrounded so this trap can run; `wait` does NOT forward signals, so we
    # must signal it ourselves. FRONTEND_PID is unset during the health-gate
    # phase, hence the :- guard.
    if [[ -n "${FRONTEND_PID:-}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
        log "shutting down front-end (pid ${FRONTEND_PID})"
        kill -TERM "${FRONTEND_PID}" 2>/dev/null || true
    fi
    if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
        log "shutting down hexstrike_server (pid ${SERVER_PID})"
        kill -TERM "${SERVER_PID}" 2>/dev/null || true
        wait "${SERVER_PID}" 2>/dev/null || true
    fi
}
trap cleanup TERM INT EXIT

# hexstrike_server.py reads HEXSTRIKE_PORT from the environment (default 8888).
export HEXSTRIKE_PORT

# ---------------------------------------------------------------------------
# VPN egress (optional): route ALL outbound traffic through Mullvad WireGuard,
# while the published mcpo port stays reachable (vpn-up.sh does the split
# routing). No-op unless MULLVAD_ACCOUNT (or MULLVAD_PRIVATE_KEY) is set.
# Fail closed: if the VPN is requested but cannot come up, refuse to start
# rather than leak un-tunneled egress.
# ---------------------------------------------------------------------------
if [ -n "${MULLVAD_ACCOUNT:-}" ] || [ -n "${MULLVAD_PRIVATE_KEY:-}" ]; then
    log "configuring Mullvad VPN egress (location=${MULLVAD_LOCATION:-ca})..."
    if /usr/local/bin/vpn-up.sh; then
        log "VPN egress active — all container-initiated traffic is tunneled"
    else
        log "FATAL: VPN requested but failed to initialize; refusing to run with un-tunneled egress"
        exit 1
    fi
fi

log "starting hexstrike_server.py (Flask API) on :${HEXSTRIKE_PORT}"
# Prefix the server's stdout/stderr so it is distinguishable in `docker logs`.
# Process substitution (not a pipe) keeps $! pointing at the python server
# itself, so the liveness check and cleanup trap target the right PID.
"${HEXSTRIKE_PY}" /opt/hexstrike-ai/hexstrike_server.py \
    > >(sed -u 's/^/[hexstrike-server] /') 2>&1 &
SERVER_PID=$!

# ---------------------------------------------------------------------------
# Health-gate. Do NOT let a failed curl abort the script (set -e); the loop
# body is guarded. If the server never becomes healthy we warn and still
# start mcpo so the OpenAPI surface comes up.
# ---------------------------------------------------------------------------
log "waiting for Flask health endpoint (up to 60s)..."
healthy=0
for i in $(seq 1 60); do
    if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
        log "WARNING: hexstrike_server exited during startup"
        break
    fi
    if curl -fsS "http://127.0.0.1:${HEXSTRIKE_PORT}/health" >/dev/null 2>&1; then
        healthy=1
        log "Flask API healthy after ${i}s"
        break
    fi
    sleep 1
done

if [[ "${healthy}" -ne 1 ]]; then
    log "WARNING: Flask API did not report healthy; starting the front-end anyway"
fi

# ---------------------------------------------------------------------------
# Front-end transport (FRONTEND_PID = the foreground service, whichever it is):
#   default          -> run hexstrike_mcp.py as a Streamable HTTP MCP server
#       directly on $PORT (no mcpo, no stdio bridge). Endpoint /mcp.
#   OPENAPI truthy    -> mcpo wraps the stdio MCP client and exposes OpenAPI.
# ---------------------------------------------------------------------------
OPENAPI_LC="$(printf '%s' "${OPENAPI:-}" | tr '[:upper:]' '[:lower:]')"
if [[ "$OPENAPI_LC" =~ ^(1|true|yes|on)$ ]]; then
    # Build mcpo argv. --api-key only added when MCPO_API_KEY is non-empty.
    MCPO_ARGS=(--host 0.0.0.0 --port "${PORT}")
    if [[ -n "${MCPO_API_KEY}" ]]; then
        log "mcpo will require an API key (MCPO_API_KEY is set)"
        MCPO_ARGS+=(--api-key "${MCPO_API_KEY}")
    else
        log "mcpo starting WITHOUT an API key (set MCPO_API_KEY to require one)"
    fi
    log "OPENAPI mode: starting mcpo on :${PORT} -> OpenAPI docs at /docs"
    "${MCPO_BIN}" "${MCPO_ARGS[@]}" -- \
        "${HEXSTRIKE_PY}" /opt/hexstrike-ai/hexstrike_mcp.py \
        --server "http://127.0.0.1:${HEXSTRIKE_PORT}" &
    FRONTEND_PID=$!
else
    # Default: Streamable HTTP MCP server. hexstrike_mcp.py switches transport
    # on STREAMABLE_HTTP, so set it here (the user-facing switch is OPENAPI).
    export STREAMABLE_HTTP=true
    export STREAMABLE_HTTP_PORT="${PORT}"
    [[ -n "${MCPO_API_KEY}" ]] && log "NOTE: MCPO_API_KEY is ignored in MCP mode (mcpo is bypassed); set OPENAPI=true to use it"
    log "starting HexStrike MCP over streamable-http on :${PORT} -> MCP endpoint /mcp"
    "${HEXSTRIKE_PY}" /opt/hexstrike-ai/hexstrike_mcp.py \
        --server "http://127.0.0.1:${HEXSTRIKE_PORT}" &
    FRONTEND_PID=$!
fi

# Block until the front-end exits. On SIGTERM/SIGINT the trap fires cleanup()
# (which signals BOTH the front-end and Flask); `wait` doesn't forward signals.
wait "${FRONTEND_PID}"
