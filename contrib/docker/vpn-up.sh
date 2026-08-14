#!/usr/bin/env bash
###############################################################################
# vpn-up.sh — route the container's OUTBOUND traffic through Mullvad WireGuard
# while keeping the published mcpo port reachable (split / policy routing).
#
# Called by entrypoint.sh before the app starts. No-op if MULLVAD_ACCOUNT is
# unset (container then runs with normal, untunneled egress).
#
# Env:
#   MULLVAD_ACCOUNT     Mullvad account number. Required to enable the VPN.
#   MULLVAD_LOCATION    Country code (default "ca" = Canada), city code, or a
#                       full relay hostname (e.g. "ca-tor-wg-001"). Configurable.
#   MULLVAD_PRIVATE_KEY / MULLVAD_ADDRESS
#                       Optional: reuse a pre-registered WireGuard key + tunnel
#                       address instead of registering a fresh ephemeral key
#                       each start (avoids filling the account's key slots).
#   MULLVAD_DNS         DNS server inside the tunnel (default 10.64.0.1 = Mullvad).
#   MULLVAD_KILLSWITCH  1 (default) = drop any egress that is not via the tunnel.
#   MCPO_PORT           Published port whose inbound replies must bypass the VPN
#                       (default 8000; read from the environment).
#
# Requires: NET_ADMIN, the host's wireguard kernel module, wireguard-tools,
#           iproute2, iptables, curl, jq.
###############################################################################
set -euo pipefail
log() { echo "[vpn] $*"; }

ACCOUNT="${MULLVAD_ACCOUNT:-}"
PROVIDED_KEY="${MULLVAD_PRIVATE_KEY:-}"

if [ -z "$ACCOUNT" ] && [ -z "$PROVIDED_KEY" ]; then
    log "MULLVAD_ACCOUNT not set — running WITHOUT VPN (outbound traffic is NOT tunneled)"
    exit 0
fi

LOCATION="${MULLVAD_LOCATION:-ca}"
DNS="${MULLVAD_DNS:-10.64.0.1}"
MCPO_PORT="${MCPO_PORT:-8000}"
KILLSWITCH="${MULLVAD_KILLSWITCH:-1}"
API="https://api.mullvad.net"
MARK="0x1"
TABLE="100"

# --- 1. Obtain a WireGuard key + tunnel address (these calls need normal egress,
#        so they run BEFORE the killswitch is installed) -----------------------
if [ -n "$PROVIDED_KEY" ] && [ -n "${MULLVAD_ADDRESS:-}" ]; then
    PRIV="$PROVIDED_KEY"; ADDR="$MULLVAD_ADDRESS"
    log "using provided WireGuard key + address (no registration)"
else
    [ -n "$ACCOUNT" ] || { log "ERROR: MULLVAD_ACCOUNT required to register a key"; exit 1; }
    PRIV="$(wg genkey)"; PUB="$(printf '%s' "$PRIV" | wg pubkey)"
    log "registering ephemeral WireGuard key with Mullvad..."
    ADDR="$(curl -sSf --retry 3 --retry-delay 2 --max-time 30 \
                 "$API/wg" -d account="$ACCOUNT" --data-urlencode pubkey="$PUB")" \
        || { log "ERROR: Mullvad key registration failed (bad/expired account?)"; exit 1; }
fi
ADDR4="$(printf '%s' "$ADDR" | tr ',' '\n' | grep -E '^[0-9]+\.' | head -1 || true)"
[ -n "$ADDR4" ] || { log "ERROR: no IPv4 tunnel address from Mullvad (got: $ADDR)"; exit 1; }

# bring_up_tunnel — (re)select a relay and (re)establish wg0 + routing + kill
# switch. Idempotent: safe to call at start AND from the watchdog on a drop.
# Sets globals RHOST/RIP/RPUB (relay) and ORIG_GW/ORIG_IF/DOCKER_NET (egress).
bring_up_tunnel() {
    # --- 2. Select a relay for the requested location -----------------------
    log "selecting Mullvad WireGuard relay for location '$LOCATION'..."
    curl -sSf --retry 3 --retry-delay 2 --max-time 30 \
         "$API/public/relays/wireguard/v1/" -o /tmp/mullvad-relays.json \
        || { log "ERROR: could not fetch Mullvad relay list"; return 1; }

    # NB: the public wireguard/v1 relay list has no "active" field — it only
    # lists usable relays — so we select by location (hostname > country >
    # city), no filter.
    SEL="$(jq -r --arg loc "$LOCATION" '
        [ .countries[] as $c | $c.cities[] as $ci | $ci.relays[]
          | {hostname, ip: .ipv4_addr_in, pub: .public_key, cc: $c.code, city: $ci.code} ]
        | ( map(select(.hostname == $loc))
          + map(select(.cc      == $loc))
          + map(select(.city    == $loc)) )
        | .[0] // empty
        | "\(.hostname) \(.ip) \(.pub)"' /tmp/mullvad-relays.json)"
    [ -n "$SEL" ] || { log "ERROR: no active Mullvad relay matches location '$LOCATION'"; return 1; }
    RHOST="${SEL%% *}"; _r="${SEL#* }"; RIP="${_r%% *}"; RPUB="${_r#* }"
    log "relay: $RHOST ($RIP)"

    # --- 3. Discover the original (docker bridge) egress --------------------
    # Read it from the fwmark table first (survives after default -> wg0), then
    # fall back to the live default route (first run, before any change).
    ORIG_GW="$(ip route show default table "$TABLE" 2>/dev/null | awk '/default/{print $3; exit}')"
    ORIG_IF="$(ip route show default table "$TABLE" 2>/dev/null | awk '/default/{print $5; exit}')"
    [ -n "$ORIG_GW" ] || ORIG_GW="$(ip route show default | awk '/default/{print $3; exit}')"
    [ -n "$ORIG_IF" ] || ORIG_IF="$(ip route show default | awk '/default/{print $5; exit}')"
    DOCKER_NET="$(ip -o -4 route show scope link dev "$ORIG_IF" | awk '{print $1; exit}')"
    [ -n "$ORIG_GW" ] && [ -n "$ORIG_IF" ] || { log "ERROR: cannot determine original gateway"; return 1; }
    log "original egress: gw=$ORIG_GW dev=$ORIG_IF subnet=$DOCKER_NET"

    # sysctls WireGuard + policy routing rely on (best-effort; need NET_ADMIN).
    sysctl -w net.ipv4.conf.all.src_valid_mark=1 >/dev/null 2>&1 || true
    sysctl -w net.ipv4.conf.all.rp_filter=2      >/dev/null 2>&1 || true

    # --- 4. Bring up the WireGuard interface (manual = no wg-quick hijack) --
    ip link del wg0 2>/dev/null || true
    ip link add wg0 type wireguard
    wg set wg0 private-key <(printf '%s' "$PRIV") \
        peer "$RPUB" endpoint "$RIP:51820" allowed-ips 0.0.0.0/0 persistent-keepalive 25
    ip -4 address add "$ADDR4" dev wg0
    ip link set mtu 1380 up dev wg0

    # --- 5. Routing ---------------------------------------------------------
    # 5a. Pin the tunnel's OUTER (encrypted) packets to the real interface so
    #     they don't recurse into wg0.
    ip route replace "$RIP/32" via "$ORIG_GW" dev "$ORIG_IF"
    # 5b. Everything else (new outbound) goes through the tunnel.
    ip route replace default dev wg0
    # 5c. Replies to INBOUND connections on the published port must leave via
    #     the original gateway. Mark inbound conns, restore the mark on their
    #     replies, and route marked packets through a table using the real gw.
    ip route replace default via "$ORIG_GW" dev "$ORIG_IF" table "$TABLE"
    ip rule add fwmark "$MARK" table "$TABLE" priority 100 2>/dev/null || true
    ip rule add to "$DOCKER_NET" table "$TABLE" priority 90 2>/dev/null || true
    iptables -t mangle -C PREROUTING -i "$ORIG_IF" -p tcp --dport "$MCPO_PORT" -j CONNMARK --set-mark "$MARK" 2>/dev/null \
        || iptables -t mangle -A PREROUTING -i "$ORIG_IF" -p tcp --dport "$MCPO_PORT" -j CONNMARK --set-mark "$MARK"
    iptables -t mangle -C OUTPUT -j CONNMARK --restore-mark 2>/dev/null \
        || iptables -t mangle -A OUTPUT -j CONNMARK --restore-mark

    # --- 6. DNS through the tunnel (prevent DNS leaks) ----------------------
    cp -f /etc/resolv.conf /etc/resolv.conf.orig 2>/dev/null || true
    printf 'nameserver %s\n' "$DNS" > /etc/resolv.conf

    # --- 7. Kill switch: block any egress that is not the tunnel ------------
    # -C guards keep re-establishes idempotent (no duplicate rules).
    if [ "$KILLSWITCH" = "1" ]; then
        iptables -C OUTPUT -o lo -j ACCEPT 2>/dev/null || iptables -A OUTPUT -o lo -j ACCEPT
        iptables -C OUTPUT -o wg0 -j ACCEPT 2>/dev/null || iptables -A OUTPUT -o wg0 -j ACCEPT
        iptables -C OUTPUT -d "$DOCKER_NET" -j ACCEPT 2>/dev/null || iptables -A OUTPUT -d "$DOCKER_NET" -j ACCEPT
        iptables -C OUTPUT -p udp -d "$RIP" --dport 51820 -j ACCEPT 2>/dev/null || iptables -A OUTPUT -p udp -d "$RIP" --dport 51820 -j ACCEPT
        iptables -C OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
        iptables -C OUTPUT -j DROP 2>/dev/null || iptables -A OUTPUT -j DROP
        # Block IPv6 egress entirely (avoid v6 leaks; tunnel here is v4-only).
        if command -v ip6tables >/dev/null 2>&1; then
            ip6tables -C OUTPUT -o lo -j ACCEPT 2>/dev/null || ip6tables -A OUTPUT -o lo -j ACCEPT 2>/dev/null || true
            ip6tables -C OUTPUT -j DROP 2>/dev/null || ip6tables -A OUTPUT -j DROP 2>/dev/null || true
        fi
        log "kill switch enabled (non-tunnel egress blocked)"
    fi

    # --- 8. Wait for the handshake ------------------------------------------
    for _ in $(seq 1 15); do
        hs="$(wg show wg0 latest-handshakes 2>/dev/null | awk '{print $2}')"
        [ -n "${hs:-}" ] && [ "$hs" != "0" ] && { log "handshake established"; break; }
        sleep 1
    done
    log "VPN up — outbound egress via $RHOST ($LOCATION). Tunnel addr $ADDR4."
}

# "reconnect" mode: only (re)establish the tunnel, no watchdog. Used by an
# externally-injected watchdog to run the full re-establish path.
if [ "${1:-}" = "reconnect" ]; then
    bring_up_tunnel || { log "ERROR: reconnect failed"; exit 1; }
    exit 0
fi

bring_up_tunnel || { log "ERROR: initial tunnel bring-up failed"; exit 1; }

# --- 9. Watchdog: auto-reconnect if the tunnel goes stale -------------------
# Runs in the background for the container's lifetime. Never exits the
# container; a dead tunnel + kill switch means zero egress, so recovery here is
# what keeps a long-lived pentest alive across idle / netswitch / hibernate.
#   VPN_WATCHDOG           1 (default) = on, 0 = off
#   VPN_WATCHDOG_INTERVAL  seconds between checks (default 30)
watchdog_loop() {
    local interval="${VPN_WATCHDOG_INTERVAL:-30}"
    local stale_after=150 fails=0
    while sleep "$interval"; do
        # newest handshake across peers (epoch); 0/empty = never
        local now newest age
        now="$(date +%s)"
        newest="$(wg show wg0 latest-handshakes 2>/dev/null | awk '{print $2}' | sort -rn | head -1)"
        age=$(( now - ${newest:-0} ))
        if [ "${newest:-0}" != "0" ] && [ "$age" -lt "$stale_after" ]; then
            fails=0; continue                       # fresh handshake — healthy
        fi
        fails=$((fails + 1))
        log "watchdog: tunnel stale (handshake age=${age}s, strike ${fails})"
        if [ "$fails" -le 2 ]; then
            # cheap path: re-pin endpoint and nudge a fresh handshake
            wg set wg0 peer "$RPUB" endpoint "$RIP:51820" 2>/dev/null || true
            ping -c1 -W3 -I wg0 10.64.0.1 >/dev/null 2>&1 || true
        else
            log "watchdog: full re-establish"
            bring_up_tunnel && fails=0 || log "watchdog: re-establish failed, will retry"
        fi
    done
}
if [ "${VPN_WATCHDOG:-1}" = "1" ]; then
    watchdog_loop &
    log "watchdog started (interval ${VPN_WATCHDOG_INTERVAL:-30}s)"
fi
