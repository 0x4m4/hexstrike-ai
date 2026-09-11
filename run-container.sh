#!/usr/bin/env bash
# ============================================================================
# HexStrike AI API — run del contenedor aislado (2026-08-06)
#
# Uso:
#   ./run-container.sh            # build (si falta) + run + logs
#   ./run-container.sh stop       # detiene y elimina el contenedor
#   ./run-container.sh status     # estado del contenedor
#
# El contenedor complementa (NO reemplaza) el auth X-API-Key:
#   - usuario no-root (uid 10001)
#   - rootfs read-only (--read-only) con /tmp y /home/hexstrike como tmpfs
#   - --cap-drop ALL + --security-opt no-new-privileges
#   - bind solo a loopback del host (127.0.0.1:8889)
#
# Nota: el server debe bindear 0.0.0.0 DENTRO del contenedor (HEXSTRIKE_HOST=
# 0.0.0.0) porque el port-forward de podman rootless no alcanza un bind de
# loopback interno. La seguridad del host la da `-p 127.0.0.1:...` + el token.
# ============================================================================
set -euo pipefail

NAME="hexstrike-ai"
IMAGE="hexstrike-ai:isolated"
HOST_PORT="8889"          # 8889 para no chocar con el servicio del host (8888)
ENV_FILE="$HOME/.config/hexstrike.env"

KEY="$(
    if [[ -f "$ENV_FILE" ]] && grep -q 'HEXSTRIKE_API_KEY=' "$ENV_FILE"; then
        grep -oP '(?<=HEXSTRIKE_API_KEY=).*' "$ENV_FILE"
    else
        echo "FALTA $ENV_FILE con HEXSTRIKE_API_KEY=..." >&2
        exit 1
    fi
)"

cmd="${1:-run}"

case "$cmd" in
    run)
        if ! podman image exists "$IMAGE"; then
            echo ">> construyendo imagen (primera vez, tarda unos minutos)..."
            podman build -t "$IMAGE" .
        fi
        if podman container exists "$NAME"; then
            echo ">> contenedor $NAME ya existe — arrancando"
            podman start "$NAME"
        else
            echo ">> lanzando contenedor aislado en 127.0.0.1:$HOST_PORT"
            podman run -d --name "$NAME" \
                -p 127.0.0.1:${HOST_PORT}:8888 \
                --read-only \
                --cap-drop ALL \
                --security-opt no-new-privileges \
                --tmpfs /tmp:rw,size=256m \
                --tmpfs /home/hexstrike:rw,size=64m \
                -e HEXSTRIKE_API_KEY="$KEY" \
                -e HEXSTRIKE_HOST=0.0.0.0 \
                "$IMAGE"
        fi
        sleep 8
        echo ">> health: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:${HOST_PORT}/health)"
        echo ">> logs (Ctrl+C para salir):"
        podman logs -f "$NAME"
        ;;
    stop)
        echo ">> deteniendo y eliminando $NAME"
        podman rm -f "$NAME" 2>/dev/null || true
        ;;
    status)
        podman ps --filter name="$NAME" --format '{{.Names}} | {{.Status}} | {{.Ports}}'
        ;;
    *)
        echo "uso: $0 [run|stop|status]" >&2
        exit 1
        ;;
esac
