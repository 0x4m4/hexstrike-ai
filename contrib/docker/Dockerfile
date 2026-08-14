# syntax=docker/dockerfile:1
###############################################################################
# HexStrike-AI MCP  (Kali-based offensive security MCP server)
#
# Architecture:
#   hexstrike_server.py  (Flask REST API, :8888)  <- executes the security tools
#        ^ HTTP
#   hexstrike_mcp.py     (FastMCP)                 --server http://127.0.0.1:8888
#        |
#        +-- default        -> Streamable HTTP MCP server on :8000  (endpoint /mcp)
#        +-- OPENAPI=true    -> stdio, wrapped by mcpo as OpenAPI on :8000 (/docs)
#
# Two ISOLATED venvs because the mcp/fastmcp pins conflict:
#   /opt/hexstrike-venv  (python3.13)  -> requirements.txt (server + mcp client)
#   /opt/mcpo-venv       (python3)     -> mcpo
###############################################################################
# Base pinned by digest to the image this was built & tested against (kali-rolling
# moves fast). Override BASE_IMAGE to rebuild on a newer Kali at your own risk.
ARG BASE_IMAGE=kalilinux/kali-rolling@sha256:f49124869e4eee549315879c3bd7ef92f23b8753fec7544537bcec1493277096
FROM ${BASE_IMAGE}

LABEL org.opencontainers.image.title="hexstrike-ai-mcp" \
      org.opencontainers.image.description="HexStrike-AI security tooling exposed as a Streamable HTTP MCP server (OPENAPI=true switches to OpenAPI via mcpo), on Kali" \
      org.opencontainers.image.source="https://github.com/0x4m4/hexstrike-ai" \
      org.opencontainers.image.documentation="https://github.com/0x4m4/hexstrike-ai/blob/master/contrib/docker/README.md" \
      org.opencontainers.image.licenses="MIT"

# ---------------------------------------------------------------------------
# Pinned versions / refs — the exact ones this image was built and tested with.
# Bump deliberately; leaving these floating makes builds non-reproducible.
# ---------------------------------------------------------------------------
# HexStrike app source (cloned at build time, then patched mcp.py is overlaid).
# Point HEXSTRIKE_REPO at a fork to build that instead of upstream.
ARG HEXSTRIKE_REPO=https://github.com/0x4m4/hexstrike-ai.git
ARG HEXSTRIKE_REF=d689933ff579d839c676c82b231f8e98326c5f04
# Prebuilt release tags/versions.
ARG X8_TAG=v4.3.0
ARG HELM_VERSION=v4.2.4
ARG OPA_VERSION=v1.19.0
ARG KUBE_BENCH_VERSION=0.16.0
ARG TERRASCAN_VERSION=1.19.9
# git clone commit SHAs (repos with no release cadence).
ARG JWT_TOOL_REF=3bc7407cf2222d6a821dcc19c776e5a1b1cb9a9b
ARG NOSQLMAP_REF=5a6dc7a0477345a424bc66f76cb7a2634c61a3af
ARG TPLMAP_REF=616b0e527f62dd0930e6346ede6bef79e9bcf717
ARG OUTGUESS_REF=24810e14327c2bbeedeaadd3e24491f2a4425c02
ARG LIBC_DATABASE_REF=b7e948f7324cde8ac5cdb26bc4d58fbeeb1fbb5c
ARG DOCKER_BENCH_REF=154869da6418089decf7e1ab0cfca0e1cdfc5c49
ARG CLOUDMAPPER_REF=ec8fbf201b8b43e66720cd3ee9079a801e49c61c

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIP_NO_CACHE_DIR=1 \
    PIPX_HOME=/opt/pipx \
    PIPX_BIN_DIR=/usr/local/bin \
    GOPATH=/root/go \
    GOBIN=/usr/local/bin \
    # Chromium / Selenium browser agent (system driver, NOT webdriver-manager)
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER=/usr/bin/chromedriver
# Put both venvs + go/local bins ahead of the system PATH.
ENV PATH=/opt/hexstrike-venv/bin:/opt/mcpo-venv/bin:/usr/local/bin:/root/go/bin:${PATH}

# Build-image layers are ephemeral, so dpkg's per-package fsync() buys nothing
# and is pathologically slow on some storage (e.g. an Unraid array / loop
# device). Disable it for the whole build — this alone cuts the apt layers from
# ~an hour to a few minutes on slow disks. Also skip apt translation downloads.
RUN printf 'force-unsafe-io\n' > /etc/dpkg/dpkg.cfg.d/02-build-speed && \
    printf 'Acquire::Languages "none";\n' > /etc/apt/apt.conf.d/02-no-languages

# ---------------------------------------------------------------------------
# (a1) Base toolchain / build deps / interpreters
#      Kali enforces PEP-668: NEVER pip-install into system python.
#      We rely on venvs (server/mcpo) + pipx (isolated CLIs).
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        gcc \
        git \
        golang-go \
        jq \
        patchelf \
        pipx \
        python3-dev \
        python3-venv \
        python3.13 \
        python3.13-dev \
        python3.13-venv \
        ruby \
        ruby-dev \
        unzip \
        wget \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# (a2) The big security-tool apt layer (all categories, deduped + sorted).
#      Every name below was verified against the live kali-rolling apt index.
#      Grouped in its own RUN so it caches independently of the toolchain.
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        amass \
        arjun \
        arp-scan \
        autorecon \
        awscli \
        azure-cli \
        binutils \
        binwalk \
        bulk-extractor \
        checksec \
        chromium \
        chromium-driver \
        commix \
        crackmapexec \
        dirb \
        dirsearch \
        dnsenum \
        enum4linux \
        enum4linux-ng \
        evil-winrm \
        feroxbuster \
        ffuf \
        fierce \
        foremost \
        gdb \
        gdb-peda \
        gef \
        ghidra \
        gobuster \
        hakrawler \
        hash-identifier \
        hashcat \
        hashid \
        httpx-toolkit \
        hydra \
        john \
        john-data \
        kubectl \
        libimage-exiftool-perl \
        masscan \
        medusa \
        metasploit-framework \
        nbtscan \
        netexec \
        nikto \
        nmap \
        nuclei \
        onesixtyone \
        ophcrack-cli \
        pacu \
        paramspider \
        patator \
        python2 \
        python3-ropgadget \
        radare2 \
        recon-ng \
        responder \
        ropper \
        samba-common-bin \
        scalpel \
        seclists \
        sherlock \
        sleuthkit \
        smbclient \
        smbmap \
        snmp \
        spiderfoot \
        sqlmap \
        sslscan \
        sslyze \
        steghide \
        stegseek \
        subfinder \
        subjack \
        testdisk \
        testssl.sh \
        theharvester \
        trivy \
        trufflehog \
        uro \
        upx-ucl \
        wafw00f \
        wfuzz \
        whatweb \
        wordlists \
        wpscan \
        xxd \
        zaproxy \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# (a3) Best-effort apt packages (apt_unverified was empty across all plans,
#      kept as a resilient hook so one bad name never breaks the build).
# ---------------------------------------------------------------------------
RUN apt-get update && \
    for pkg in ; do \
        apt-get install -y --no-install-recommends "$pkg" || echo "skip $pkg"; \
    done; \
    rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# (b) Go tools -> installed to GOBIN=/usr/local/bin. Failures tolerated.
# ---------------------------------------------------------------------------
RUN set -eux; \
    for mod in \
        github.com/projectdiscovery/katana/cmd/katana@v1.7.0 \
        github.com/lc/gau/v2/cmd/gau@v2.2.4 \
        github.com/tomnomnom/waybackurls@v0.1.0 \
        github.com/tomnomnom/anew@v0.1.1 \
        github.com/tomnomnom/qsreplace@v0.0.3 \
        github.com/jaeles-project/jaeles@v0.0.0-20260620125341-d40305ffe42a \
        github.com/hahwul/dalfox/v2@v2.13.0 \
    ; do \
        go install "$mod" || echo "WARN: go install failed for $mod"; \
    done; \
    rm -rf /root/go/pkg /root/.cache/go-build

# ---------------------------------------------------------------------------
# (c) pipx tools (PEP-668-safe isolated CLIs -> /usr/local/bin).
#     Some target the newest python; a few upstreams are archived (kube-hunter)
#     so those are best-effort, core cloud scanners stay strict.
# ---------------------------------------------------------------------------
RUN set -eux; \
    pipx install "prowler==3.11.3"         || echo "WARN: prowler pipx install failed"; \
    pipx install "ScoutSuite==5.14.0"      || echo "WARN: ScoutSuite pipx install failed"; \
    pipx install "checkov==3.3.11"         || echo "WARN: checkov pipx install failed"; \
    pipx install "volatility3==2.28.0"     || echo "WARN: volatility3 pipx install failed"; \
    pipx install "social-analyzer==0.45"   || echo "WARN: social-analyzer pipx install failed"; \
    pipx install "shodan==1.31.0"          || echo "WARN: shodan pipx install failed"; \
    pipx install "censys==2.2.19"          || echo "WARN: censys pipx install failed"; \
    pipx install "kube-hunter==0.6.8"      || echo "WARN: kube-hunter pipx install failed (archived upstream)"

# ---------------------------------------------------------------------------
# (d) gem tools
# ---------------------------------------------------------------------------
RUN gem install --no-document one_gadget zsteg || echo "WARN: gem install failed"

# ---------------------------------------------------------------------------
# (e) git_build / prebuilt-binary tools (from the verified per-category plans)
# ---------------------------------------------------------------------------

# --- Network: rustscan (prebuilt .deb, amd64) ---
RUN set -eux; \
    curl -sSL -o /tmp/rustscan.deb.zip https://github.com/bee-san/RustScan/releases/download/2.4.1/rustscan.deb.zip && \
    unzip -o -j /tmp/rustscan.deb.zip 'rustscan_2.4.1-1_amd64.deb' -d /tmp && \
    dpkg -i /tmp/rustscan_2.4.1-1_amd64.deb && \
    rm -f /tmp/rustscan.deb.zip /tmp/rustscan_2.4.1-1_amd64.deb || echo "WARN: rustscan install failed"

# --- Web: x8 (prebuilt static binary) ---
RUN set -eux; \
    curl -fsSL -o /tmp/x8.gz "https://github.com/Sh1Yo/x8/releases/download/${X8_TAG}/x86_64-linux-x8.gz" && \
    gunzip -f /tmp/x8.gz && \
    install -m 0755 /tmp/x8 /usr/local/bin/x8 && \
    rm -f /tmp/x8.gz /tmp/x8 || echo "WARN: x8 install failed"

# --- Web: jwt_tool (git + dedicated venv + wrapper) ---
RUN set -eux; \
    git clone https://github.com/ticarpi/jwt_tool /opt/jwt_tool && \
    git -C /opt/jwt_tool checkout -q ${JWT_TOOL_REF} && \
    python3 -m venv /opt/jwt_tool/venv && \
    /opt/jwt_tool/venv/bin/pip install --no-cache-dir -r /opt/jwt_tool/requirements.txt && \
    printf '#!/bin/sh\nexec /opt/jwt_tool/venv/bin/python /opt/jwt_tool/jwt_tool.py "$@"\n' > /usr/local/bin/jwt_tool && \
    chmod +x /usr/local/bin/jwt_tool || echo "WARN: jwt_tool install failed"

# --- Web: NoSQLMap + tplmap (python2 tools) ---
RUN set -eux; \
    ( \
      git clone https://github.com/codingo/NoSQLMap /opt/NoSQLMap && \
      git -C /opt/NoSQLMap checkout -q ${NOSQLMAP_REF} && \
      curl -fsSL https://bootstrap.pypa.io/pip/2.7/get-pip.py -o /tmp/get-pip2.py && \
      python2 /tmp/get-pip2.py && \
      (python2 -m pip install --no-cache-dir -r /opt/NoSQLMap/requirements.txt || true) && \
      printf '#!/bin/sh\ncd /opt/NoSQLMap && exec python2 nosqlmap.py "$@"\n' > /usr/local/bin/nosqlmap && \
      chmod +x /usr/local/bin/nosqlmap && \
      git clone https://github.com/epinna/tplmap /opt/tplmap && \
      git -C /opt/tplmap checkout -q ${TPLMAP_REF} && \
      printf '#!/bin/sh\nexec python2 /opt/tplmap/tplmap.py "$@"\n' > /usr/local/bin/tplmap && \
      chmod +x /usr/local/bin/tplmap \
    ) || echo "WARN: nosqlmap/tplmap install failed"; \
    rm -f /tmp/get-pip2.py

# --- Binary: pwndbg (official self-contained .deb, bundles portable gdb) ---
RUN set -eux; \
    wget -O /tmp/pwndbg.deb https://github.com/pwndbg/pwndbg/releases/download/2026.07.29/pwndbg_2026.07.29_amd64.deb && \
    apt-get update && apt-get install -y /tmp/pwndbg.deb && \
    rm -f /tmp/pwndbg.deb && rm -rf /var/lib/apt/lists/* || echo "WARN: pwndbg install failed"

# --- Binary: outguess (source build; not in apt). It bundles a 1998 jpeg-6b
#     that needs pre-C23 semantics: Kali's gcc defaults to C23 where `foo()`
#     means `foo(void)`, breaking the old K&R prototypes -> build with
#     -std=gnu17 (which also allows pnm.c's C99 for-loops) + relaxed warnings.
#     --with-generic-jconfig uses the bundled jpeg. Best-effort. ---
RUN set -eux; \
    apt-get update && apt-get install -y --no-install-recommends \
        autoconf automake libtool libjpeg-dev && rm -rf /var/lib/apt/lists/*; \
    rm -rf /tmp/outguess; \
    # NB: `export` CFLAGS (not a `CFLAGS=... ./configure` prefix) so it reaches
    # `make` and the bundled jpeg-6b-steg sub-make — that subdir has its own
    # Makefile and would otherwise compile without -std=gnu17 and fail.
    ( git clone https://github.com/resurrecting-open-source-projects/outguess /tmp/outguess && \
      git -C /tmp/outguess checkout -q ${OUTGUESS_REF} && \
      cd /tmp/outguess && ./autogen.sh && \
      export CFLAGS="-std=gnu17 -fcommon -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -Wno-error" && \
      ./configure --with-generic-jconfig && \
      make && make install && ldconfig && cd / && rm -rf /tmp/outguess ) \
    || echo "WARN: outguess build failed"

# --- Binary: pwninit (prebuilt x86_64 glibc binary; needs patchelf at runtime) ---
RUN set -eux; \
    wget -O /usr/local/bin/pwninit https://github.com/io12/pwninit/releases/download/3.3.3/pwninit && \
    chmod +x /usr/local/bin/pwninit || echo "WARN: pwninit install failed"

# --- Binary: libc-database (server hard-codes /opt/libc-database + ./find/./dump/./download) ---
RUN set -eux; \
    ( git clone https://github.com/niklasb/libc-database /opt/libc-database && \
      git -C /opt/libc-database checkout -q ${LIBC_DATABASE_REF} ) \
    || echo "WARN: libc-database clone failed"

# --- Cloud: helm / opa / kube-bench / terrascan (prebuilt release binaries) ---
RUN set -eux; \
    curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz" -o /tmp/helm.tgz && \
    tar -xzf /tmp/helm.tgz -C /tmp && install -m0755 /tmp/linux-amd64/helm /usr/local/bin/helm && \
    rm -rf /tmp/helm.tgz /tmp/linux-amd64 || echo "WARN: helm install failed"; \
    curl -fsSL "https://github.com/open-policy-agent/opa/releases/download/${OPA_VERSION}/opa_linux_amd64_static" -o /usr/local/bin/opa && \
    chmod 0755 /usr/local/bin/opa || echo "WARN: opa install failed"; \
    curl -fsSL "https://github.com/aquasecurity/kube-bench/releases/download/v${KUBE_BENCH_VERSION}/kube-bench_${KUBE_BENCH_VERSION}_linux_amd64.tar.gz" -o /tmp/kb.tgz && \
    mkdir -p /etc/kube-bench && tar -xzf /tmp/kb.tgz -C /tmp && \
    install -m0755 /tmp/kube-bench /usr/local/bin/kube-bench && cp -r /tmp/cfg /etc/kube-bench/cfg && \
    rm -rf /tmp/kb.tgz /tmp/kube-bench /tmp/cfg || echo "WARN: kube-bench install failed"; \
    curl -fsSL "https://github.com/tenable/terrascan/releases/download/v${TERRASCAN_VERSION}/terrascan_${TERRASCAN_VERSION}_Linux_x86_64.tar.gz" -o /tmp/ts.tgz && \
    tar -xzf /tmp/ts.tgz -C /tmp terrascan && install -m0755 /tmp/terrascan /usr/local/bin/terrascan && \
    rm -f /tmp/ts.tgz /tmp/terrascan || echo "WARN: terrascan install failed"

# --- Cloud: docker-bench-security (shell script) ---
RUN set -eux; \
    git clone https://github.com/docker/docker-bench-security.git /opt/docker-bench-security && \
    git -C /opt/docker-bench-security checkout -q ${DOCKER_BENCH_REF} && \
    ln -sf /opt/docker-bench-security/docker-bench-security.sh /usr/local/bin/docker-bench-security \
    || echo "WARN: docker-bench-security install failed"

# --- Cloud: cloudmapper (archived; own venv, best-effort) ---
RUN set -eux; \
    apt-get update && apt-get install -y --no-install-recommends \
        autoconf libjq-dev libtool libxml2-dev libxslt1-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*; \
    git clone https://github.com/duo-labs/cloudmapper.git /opt/cloudmapper && \
    git -C /opt/cloudmapper checkout -q ${CLOUDMAPPER_REF} && \
    python3 -m venv /opt/cloudmapper/venv && \
    /opt/cloudmapper/venv/bin/pip install --no-cache-dir -r /opt/cloudmapper/requirements.txt && \
    ln -sf /opt/cloudmapper/venv/bin/python /usr/local/bin/cloudmapper-python \
    || echo "WARN: cloudmapper install failed (archived upstream, best-effort)"

# --- OSINT: aquatone (prebuilt binary; reuses system chromium at runtime) ---
RUN set -eux; \
    curl -fsSL -o /tmp/aquatone.zip https://github.com/michenriksen/aquatone/releases/download/v1.7.0/aquatone_linux_amd64_1.7.0.zip && \
    unzip -o /tmp/aquatone.zip -d /tmp/aquatone && \
    install -m0755 /tmp/aquatone/aquatone /usr/local/bin/aquatone && \
    rm -rf /tmp/aquatone /tmp/aquatone.zip || echo "WARN: aquatone install failed"

# ---------------------------------------------------------------------------
# HexStrike application: cloned at build time and pinned to HEXSTRIKE_REF, then
# the STREAMABLE_HTTP-aware hexstrike_mcp.py is overlaid below. Override
# HEXSTRIKE_REPO/HEXSTRIKE_REF to build a fork or a different commit.
# ---------------------------------------------------------------------------
RUN git clone ${HEXSTRIKE_REPO} /opt/hexstrike-ai && \
    git -C /opt/hexstrike-ai checkout -q ${HEXSTRIKE_REF}

# ---------------------------------------------------------------------------
# /opt/hexstrike-venv : server + mcp client (built with python3.13 so the
# angr/pwntools C-extension stack resolves cp313 wheels; build-essential +
# python3.13-dev present for any sdist fallback). Resolver was verified
# conflict-free via pip --dry-run (bcrypt==4.0.1 pin holds).
# ---------------------------------------------------------------------------
RUN python3.13 -m venv /opt/hexstrike-venv && \
    /opt/hexstrike-venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/hexstrike-venv/bin/pip install --no-cache-dir -r /opt/hexstrike-ai/requirements.txt

# ---------------------------------------------------------------------------
# /opt/mcpo-venv : mcpo only (mcp version conflicts with hexstrike's fastmcp,
# hence a separate venv). Uses default python3 (>=3.11 satisfied).
#
# Pin mcp==1.29.0 (must stay <2): mcpo 0.0.20 does `from
# mcp.client.streamable_http import streamablehttp_client`, which the mcp 2.x
# SDK removed/renamed. Left unpinned, pip resolves mcp 2.x and mcpo crashes on
# import at startup. Bump both together and re-test the streamable-http path.
# ---------------------------------------------------------------------------
RUN python3 -m venv /opt/mcpo-venv && \
    /opt/mcpo-venv/bin/pip install --upgrade pip && \
    /opt/mcpo-venv/bin/pip install --no-cache-dir "mcp==1.29.0" "mcpo==0.0.20"

# ---------------------------------------------------------------------------
# (f) Extra tools HexStrike's /health probes by exact command name
#     (`which <name>`). These apt packages provide tools the server expects:
#       aircrack-ng -> airmon-ng/airodump-ng/aireplay-ng/aircrack-ng
#       exploitdb   -> searchsploit    | tshark/tcpdump -> wireless/pcap
#       plus dotdotpwn, xsser, httpie, hashcat-utils, autopsy, kismet.
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        aircrack-ng \
        autopsy \
        dotdotpwn \
        exploitdb \
        hashcat-utils \
        httpie \
        kismet \
        tcpdump \
        tshark \
        xsser \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# (g) Compatibility symlinks: HexStrike probes/invokes specific command names
#     that differ from the packaged binary names. Map probe-name -> real bin.
#     Runs last so every target already exists (venvs, pipx, gem, apt, git).
# ---------------------------------------------------------------------------
RUN set -eux; \
    link() { if [ -n "$2" ] && [ -e "$2" ]; then ln -sf "$2" "/usr/local/bin/$1"; else echo "WARN: $1 -> '$2' missing"; fi; }; \
    # The venvs ship the Python `httpx` client CLI, which sits first on PATH and
    # shadows ProjectDiscovery's httpx-toolkit (the tool HexStrike actually wants).
    # Drop the venv scripts (libraries stay) and point `httpx` at httpx-toolkit.
    rm -f /opt/hexstrike-venv/bin/httpx /opt/mcpo-venv/bin/httpx; \
    link httpx           /usr/bin/httpx-toolkit; \
    link bulk-extractor  /usr/bin/bulk_extractor; \
    link ropgadget       "$(command -v ROPgadget || true)"; \
    link scout-suite     /usr/local/bin/scout; \
    link shodan-cli      /usr/local/bin/shodan; \
    link censys-cli      /usr/local/bin/censys; \
    link one-gadget      /usr/local/bin/one_gadget; \
    link pwntools        /opt/hexstrike-venv/bin/pwn; \
    link volatility3     /usr/local/bin/vol; \
    link metasploit      /usr/bin/msfconsole; \
    link ophcrack        /usr/bin/ophcrack-cli; \
    link exploit-db      /usr/bin/searchsploit; \
    link jwt-analyzer    /usr/local/bin/jwt_tool; \
    link hashcat-utils   /usr/lib/hashcat-utils/combinator.bin; \
    link sleuthkit       "$(command -v fls || true)"; \
    link libc-database   /opt/libc-database/find

# ---------------------------------------------------------------------------
# (h) VPN egress: Mullvad WireGuard + policy-routing tooling. When
#     MULLVAD_ACCOUNT is set at runtime, entrypoint routes ALL container
#     outbound traffic through the tunnel while keeping the published mcpo
#     port reachable. (iproute2 is already present from the base; iptables +
#     wireguard-tools are the additions. Needs a host wireguard kernel module
#     and --cap-add=NET_ADMIN at run time.)
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        wireguard-tools iptables iproute2 \
    && rm -rf /var/lib/apt/lists/*
COPY contrib/docker/vpn-up.sh /usr/local/bin/vpn-up.sh
RUN chmod +x /usr/local/bin/vpn-up.sh

# ---------------------------------------------------------------------------
# Overlay the STREAMABLE_HTTP-aware hexstrike_mcp.py (this repo's root copy,
# carrying the transport patch) over the build-time upstream clone, which only
# speaks stdio. Runtime script only -> this late COPY keeps the expensive
# tool/venv layers cached. NOTE: the build context is the repo root, so this
# path is repo-root-relative (see contrib/docker/README.md).
# ---------------------------------------------------------------------------
COPY hexstrike_mcp.py /opt/hexstrike-ai/hexstrike_mcp.py

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
COPY contrib/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000 8888

# Mode-agnostic: the Flask backend /health must be 200 (a dead backend makes
# every tool 500 even while the front-end serves), AND the exposed port must be
# answering — mcpo (/docs) or the streamable-http MCP server (/mcp) both reply
# there, so a plain connect check (any HTTP status) works for both transports.
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8888/health >/dev/null \
        && curl -s -o /dev/null http://127.0.0.1:8000/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]
