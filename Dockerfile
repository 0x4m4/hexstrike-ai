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
    gobuster nikto whatweb wafw00f sslscan \
    sqlmap wpscan \
    hydra john hashcat medusa \
    smbmap enum4linux responder \
    radare2 binwalk foremost steghide exiftool checksec \
    golang-go libcap2-bin \
    git curl wget ca-certificates \
    arsenal-ng gef wpprobe xsstrike sstimap python3-atomic-operator \
    amass feroxbuster python3-impacket netexec certipy-ad \
    && rm -rf /var/lib/apt/lists/*

# RustScan isn't in Kali's apt repo (checked the live index directly) —
# it ships prebuilt releases on GitHub instead, as rustscan.deb.zip (a
# .deb wrapped in a zip, not a raw .deb — worth knowing, the naming
# isn't what you'd guess). Using GitHub's stable /latest/download/ redirect
# rather than the releases API, which is rate-limited per-IP and this
# build already got throttled by it once this session. python3 (already
# installed above) handles the unzip so this doesn't need a new apt
# package just for one archive.
RUN curl -sL https://github.com/RustScan/RustScan/releases/latest/download/rustscan.deb.zip -o /tmp/rustscan.zip \
    && python3 -m zipfile -e /tmp/rustscan.zip /tmp/rustscan_extracted/ \
    && dpkg -i /tmp/rustscan_extracted/*.deb \
    && rm -rf /tmp/rustscan.zip /tmp/rustscan_extracted

# ── Go-based tools (ProjectDiscovery etc.) ──────────────────────────────
# Each install is capped at 3min and non-fatal: a single stalled module
# proxy fetch shouldn't block the whole image build. Missing tools are
# reported in the build log — rerun `docker build` later to retry them,
# or add more here with the same pattern.
ENV GOPATH=/opt/go
# /opt/go/bin goes FIRST, not appended. apt/pip install same-named CLIs for
# unrelated tools (pip's httpx[cli] HTTP client vs. ProjectDiscovery's httpx
# recon scanner is the concrete case that shipped broken — appended-PATH
# order let the pip shim silently shadow the real binary). Putting our Go
# tools first makes every `go install` binary in this list authoritative,
# not just httpx.
ENV PATH=/opt/go/bin:$PATH
ENV GOPROXY=https://proxy.golang.org,direct
RUN --mount=type=cache,target=/root/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    for pkg in \
        "github.com/projectdiscovery/httpx/cmd/httpx" \
        "github.com/ffuf/ffuf/v2" \
        "github.com/projectdiscovery/subfinder/v2/cmd/subfinder" \
        "github.com/projectdiscovery/nuclei/v3/cmd/nuclei" \
        "github.com/tomnomnom/waybackurls" \
    ; do \
        echo "→ go install $pkg"; \
        timeout 300 go install "${pkg}@latest" 2>&1 | tail -20 || echo "⚠️  SKIPPED (timeout/failed): $pkg"; \
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

# amass's apt wrapper (/usr/bin/amass) checks for libpostal's data dir and,
# if missing, shells out to `sudo libpostal_data download all` — which
# fails outright under the non-root hexstrike user, and even as root would
# pull ~1-2GB just for one optional address-normalization feature amass
# barely uses (its actual recon functionality — DNS enum, ASN lookups,
# cert-transparency, subdomain brute-force — doesn't touch libpostal at
# all). Satisfying the wrapper's existence check with an empty sentinel
# avoids both the sudo failure and the multi-GB download; only the
# address-parsing-specific amass features would be affected, not the
# ones this is actually installed for.
RUN mkdir -p /var/lib/libpostal && touch /usr/share/libpostal/transliteration

WORKDIR /app
COPY requirements.txt .
# venv, not system pip — Kali ships several Python packages (bcrypt etc.)
# as dpkg-managed system packages that pip can't safely uninstall/upgrade
# even with --break-system-packages (PEP 668). Isolating into a venv
# avoids that whole conflict class.
#
# IMPORTANT: deliberately NOT prepending /opt/venv/bin to the global PATH
# here (as an earlier version of this file did). Several apt-packaged
# tools (confirmed: impacket-secretsdump and friends) ship thin shell
# wrappers that call bare `python3` rather than an absolute path — with
# venv-first PATH, those silently resolve to THIS isolated venv instead of
# system python3, and since venvs don't see system dist-packages, they
# fail with ModuleNotFoundError for a library that's actually installed
# and present. Root-caused by hand: verified the wrapper's shebang/exec
# line, verified the library was genuinely on disk, verified system
# python3's sys.path included dist-packages, isolated it to the PATH
# shadowing. Fix: reference the venv by absolute path (/opt/venv/bin/pip,
# /opt/venv/bin/python3 in entrypoint.sh) everywhere WE need it, and leave
# bare `python3` on PATH resolving to the system interpreter so every
# other apt-packaged tool's wrapper keeps working as its maintainer
# intended. This likely isn't impacket-specific — any Kali tool with a
# similar wrapper pattern was at risk before this fix.
RUN python3 -m venv /opt/venv
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt
# xsstrike pulls this in at runtime on first use if missing — bake it in
# so a per-engagement container doesn't need outbound pip access mid-test.
RUN /opt/venv/bin/pip install --no-cache-dir fuzzywuzzy
# atomic-operator itself comes from apt (python3-atomic-operator, above) —
# NOT pip. Its dependency chain (atomic-operator-runner pins pydantic 1.x;
# its other dependency `fire` still imports the stdlib `pipes` module,
# removed in Python 3.13/Kali-rolling's default python3 — a known,
# still-open upstream bug, google/python-fire#444) would conflict badly
# with mcp/fastmcp's pydantic 2.x requirement if installed into this venv
# via pip — confirmed by hand, it silently downgrades pydantic and breaks
# hexstrike_mcp.py's imports at runtime. Kali's own apt packaging already
# resolves both problems correctly (confirmed by hand: apt installs into
# system dist-packages, completely separate from this venv, and imports
# clean with no patching needed) — apt is the correct install path here,
# not pip.

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
