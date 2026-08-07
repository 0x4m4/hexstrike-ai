FROM kalilinux/kali-rolling

LABEL maintainer="thesaint"
LABEL description="HexStrike AI MCP server, hardened + containerized for isolated per-engagement use"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# ── Security tools ───────────────────────────────────────────────────────
# Kali's apt repos cover most of the "Core Tools (Essential)" set from the
# README directly. This is NOT the full 150+ tool list (many of the
# ProjectDiscovery/Go-based recon tools — nuclei, subfinder, httpx, katana,
# dalfox, ffuf — aren't in apt and need `go install`; add them below in the
# "Go-based tools" block as needed). Extend this list rather than installing
# tools ad-hoc inside a running container, so the image stays reproducible.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv python3-dev build-essential \
    nmap masscan \
    gobuster dirb nikto whatweb wafw00f sslscan \
    sqlmap wpscan \
    hydra john hashcat medusa \
    smbmap enum4linux responder \
    radare2 binwalk foremost steghide exiftool checksec \
    golang-go libcap2-bin \
    git curl wget ca-certificates \
    arsenal-ng gef wpprobe xsstrike sstimap \
    && rm -rf /var/lib/apt/lists/*

# ── Go-based tools (ProjectDiscovery etc.) ──────────────────────────────
# Each install is capped at 3min and non-fatal: a single stalled module
# proxy fetch shouldn't block the whole image build. Missing tools are
# reported in the build log — rerun `docker build` later to retry them,
# or add more here with the same pattern.
ENV GOPATH=/opt/go
ENV PATH=$PATH:/opt/go/bin
ENV GOPROXY=https://proxy.golang.org,direct
RUN --mount=type=cache,target=/root/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    for pkg in \
        "github.com/projectdiscovery/httpx/cmd/httpx" \
        "github.com/ffuf/ffuf/v2" \
        "github.com/projectdiscovery/subfinder/v2/cmd/subfinder" \
        "github.com/projectdiscovery/nuclei/v3/cmd/nuclei" \
    ; do \
        echo "→ go install $pkg"; \
        timeout 180 go install "${pkg}@latest" || echo "⚠️  SKIPPED (timeout/failed): $pkg"; \
    done

# ── Non-root execution ───────────────────────────────────────────────────
# Run as an unprivileged user; grant raw-socket capabilities directly to
# the two binaries that need them (SYN scans, packet crafting) instead of
# running the whole container as root or with --privileged.
RUN useradd -m -u 1000 -s /bin/bash hexstrike && \
    setcap cap_net_raw,cap_net_admin+eip /usr/bin/nmap && \
    setcap cap_net_raw,cap_net_admin+eip /usr/bin/masscan

# gef (GDB Enhanced Features): the apt package only drops gef.py at
# /usr/share/gdb/gef.py, it doesn't wire it into gdb's startup — normally
# gef's own installer appends a `source` line to ~/.gdbinit, apt doesn't.
RUN echo "source /usr/share/gdb/gef.py" >> /etc/gdb/gdbinit

WORKDIR /app
COPY requirements.txt .
# venv, not system pip — Kali ships several Python packages (bcrypt etc.)
# as dpkg-managed system packages that pip can't safely uninstall/upgrade
# even with --break-system-packages (PEP 668). Isolating into a venv
# avoids that whole conflict class.
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt
# xsstrike pulls this in at runtime on first use if missing — bake it in
# so a per-engagement container doesn't need outbound pip access mid-test.
RUN pip install --no-cache-dir fuzzywuzzy
# atomic-operator (MITRE ATT&CK/Atomic Red Team technique execution) isn't
# in Kali's apt repo — PyPI-only. Two issues, both fixed here:
# (1) its dependency atomic-operator-runner hard-pins pydantic 1.x
#     (conflicts with mcp/fastmcp's pydantic 2.x requirement) — isolated
#     into its own venv so it can't touch the main app's dependencies.
# (2) its dependency `fire` still imports the stdlib `pipes` module, which
#     was removed in Python 3.13 (Kali-rolling's default python3) — this
#     is a known, still-open upstream bug (google/python-fire#444) with no
#     fixed release. `pipes.quote` and `shlex.quote` are functionally
#     identical (that's literally fire's documented migration path), so
#     aliasing the import is a safe, minimal local patch.
RUN python3 -m venv /opt/atomic-operator-venv && \
    /opt/atomic-operator-venv/bin/pip install --no-cache-dir atomic-operator attrs && \
    ln -s /opt/atomic-operator-venv/bin/atomic-operator /usr/local/bin/atomic-operator && \
    find /opt/atomic-operator-venv -path "*/fire/*.py" -exec sed -i 's/^import pipes$/import shlex as pipes/' {} +

COPY hexstrike_server.py hexstrike_mcp.py scope.example.json ./
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# /tmp is where the server's existing tool-output code writes by default
# (hexstrike_files, autorecon_*, prowler_* etc — see FileOperationsManager
# and per-tool output_dir defaults). Bind-mounting the HOST's per-engagement
# directory over this container's /tmp is what gives each engagement its
# own isolated, inspectable output — see hex-engage in .zshrc.
RUN mkdir -p /tmp/hexstrike_files && chown -R hexstrike:hexstrike /app /tmp/hexstrike_files

USER hexstrike
EXPOSE 8888

# NOTE: binding 0.0.0.0 here is intentional and NOT a regression of the
# 127.0.0.1-only rule from the bare-metal setup. Inside Docker's isolated
# network namespace, 0.0.0.0 just means "listen on this container's
# interface" — actual host/LAN exposure is controlled entirely by the
# `-p` flag on `docker run`. hex-engage always maps `-p 127.0.0.1:PORT:8888`,
# so the net effect on the host is identical: loopback-only.
ENTRYPOINT ["/entrypoint.sh"]
