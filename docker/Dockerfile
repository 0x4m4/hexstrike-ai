# ==============================================================================
# HexStrike AI MCP Server v6.0 - Docker Image (Multi-stage Build)
# ==============================================================================
# Repository: https://github.com/0x4m4/hexstrike-ai
# License: MIT
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage A: Python 3.12 base (for Prowler and Pacu)
# ------------------------------------------------------------------------------
FROM docker.io/python:3.12-slim AS python312-base

# ------------------------------------------------------------------------------
# Stage B: CloudMapper builder (Python 3.10 + dedicated venv with pyjq)
# ------------------------------------------------------------------------------
FROM docker.io/python:3.10-slim AS cloudmapper-builder

ENV CM_VENV=/opt/venvs/cloudmapper
WORKDIR /opt/hexstrike

# Install build prerequisites and jq development libraries for pyjq
RUN set -euo pipefail; \
    apt-get update && apt-get install -y --no-install-recommends \
      build-essential autoconf automake libtool pkg-config \
      git curl ca-certificates \
      libjq-dev libonig-dev bison flex \
    && rm -rf /var/lib/apt/lists/*

# Create a dedicated virtual environment for CloudMapper
RUN python -m venv "$CM_VENV" \
 && "$CM_VENV/bin/pip" install --no-cache-dir -U pip setuptools wheel

# Fetch CloudMapper directly from upstream to avoid context COPY issues
RUN git clone --depth 1 https://github.com/duo-labs/cloudmapper.git /opt/hexstrike/tools/cloudmapper \
 && rm -rf /opt/hexstrike/tools/cloudmapper/.git

# Normalize requirement pins and install into the dedicated venv
RUN REQ=/opt/hexstrike/tools/cloudmapper/requirements.txt; \
  # Align matplotlib/numpy to versions compatible with Python 3.10
  sed -i \
    -e 's/^matplotlib==3\.4\.3$/matplotlib==3\.7\.5/' \
    -e 's/^numpy==1\.22\.0$/numpy>=1\.23/' \
    "$REQ"; \
  # Drop typed-ast (not supported on Python ≥ 3.10)
  sed -i '/^typed-ast==/d' "$REQ"; \
  # Optionally bump pyjq to a newer compatible version if pinned
  sed -i 's/^pyjq==2\.4\.0$/pyjq==2\.6\.0/' "$REQ"; \
  # Install all dependencies in the CloudMapper venv
  "$CM_VENV/bin/pip" install --no-cache-dir --prefer-binary -r "$REQ"

# ------------------------------------------------------------------------------
# Stage C: Node.js 18 builder for insomnia-inso (isolated runtime)
# ------------------------------------------------------------------------------
FROM docker.io/node:18-bullseye AS insomnia-node18-builder

ENV DEBIAN_FRONTEND=noninteractive \
    NPM_CONFIG_PREFIX=/opt/insomnia

RUN set -eu; \
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        python3 \
        python3-pip \
        python3-setuptools \
        libcurl4-openssl-dev \
        pkg-config \
        git \
        jq \
    && python3 -m pip install --no-cache-dir gyp-next

# Install insomnia CLI plus supporting reconnaissance tools (official releases)
RUN npm install -g --build-from-source insomnia-inso \
    && npm cache clean --force

RUN mkdir -p /opt/insomnia-artifacts/node18 && \
    cp -a /usr/local/bin /opt/insomnia-artifacts/node18/bin && \
    cp -a /usr/local/lib /opt/insomnia-artifacts/node18/lib && \
    cp -a /usr/local/include /opt/insomnia-artifacts/node18/include && \
    cp -a /usr/local/share /opt/insomnia-artifacts/node18/share && \
    cp -a /opt/insomnia /opt/insomnia-artifacts/insomnia

# ------------------------------------------------------------------------------
# Stage D: Final - Kali Linux + All Tools & Runtimes
# ------------------------------------------------------------------------------
FROM docker.io/kalilinux/kali-last-release:latest


ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /opt/hexstrike

# Copy Python 3.12 runtime from Stage A (needed by Prowler and Pacu)
COPY --from=python312-base /usr/local/ /usr/local/
RUN ln -sf /usr/local/lib/libpython3.12.so.1.0 /usr/local/lib/libpython3.12.so && \
    ldconfig

# ==============================================================================
# Phase 1: Base System Packages
# ==============================================================================
# - curl: data transfer utility for installers and health checks
# - wget: alternative download utility
# - git: distributed version control
# - ca-certificates: TLS certificate bundle for secure downloads
# - gnupg2: OpenPGP toolkit for repository keys
# - lsb-release: distribution release information
# - xz-utils: XZ compression utilities
# - httpie: user-friendly HTTP client
# - wordlists: common wordlists for security testing
# - p7zip-full: 7-Zip archiver
# - binutils: binary utilities
RUN set -euo pipefail; \
    apt-get update && apt-get install -y --no-install-recommends \
        apt-utils \
        curl \
        wget \
        git \
        gnupg2 \
        lsb-release \
        xz-utils \
        ca-certificates \
        wordlists \
        httpie \
        jq \
        unzip \
        p7zip-full \
        binutils \
        vim \
        nano

# ==============================================================================
# Phase 2: Language Runtimes and Build Tools
# ==============================================================================
# - node + npm: JavaScript runtime and package manager
# - default-jdk: Java Development Kit
# - ruby-full: Ruby language and standard toolchain
# - pipx: isolated Python CLI installer
RUN apt-get install -y --no-install-recommends \
        nodejs \
        npm \
        default-jdk \
        ruby-full \
        pipx \
        python3-venv \
        python3-pip \
        build-essential \
        python3-dev \
        g++

ENV PIPX_DEFAULT_PYTHON=/usr/bin/python3
ENV npm_config_python=/usr/bin/python3
ENV PYTHON=/usr/bin/python3

# ==============================================================================
# Phase 3: Python Virtual Environment
# ==============================================================================
ENV VIRTUAL_ENV=/opt/hexstrike/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN /usr/bin/python3 -m venv "$VIRTUAL_ENV" \
 && . "$VIRTUAL_ENV/bin/activate" \
 && pip install --no-cache-dir --upgrade pip setuptools wheel
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_NO_PYTHON_VERSION_WARNING=1
ENV PATH="${PATH}:/root/.local/bin"


# ==============================================================================
# Phase 4: Cloud & Container Security (Python CLIs)
# ==============================================================================
# - ansible: automation engine for configuration and orchestration
RUN apt-get install -y --no-install-recommends \
        ansible

# Install Python CLIs via pipx (official, isolated)
# - checkov: IaC security scanner for Terraform/CloudFormation/Kubernetes
# - prowler: multi-cloud security assessment and compliance checks
# - ScoutSuite: multi-cloud security auditing (AWS/Azure/GCP/Alibaba Cloud)
# - kube-hunter: Kubernetes penetration testing (active/passive)
# - shodan: official Shodan CLI
# - censys: official Censys CLI
RUN pipx install --pip-args="--no-cache-dir --prefer-binary" checkov     && \
    pipx install --python /usr/local/bin/python3.12 --pip-args="--no-cache-dir --prefer-binary" prowler     && \
    pipx install --pip-args="--no-cache-dir --prefer-binary" ScoutSuite  && \
    pipx install --pip-args="--no-cache-dir --prefer-binary" kube-hunter && \
    pipx install --pip-args="--no-cache-dir --prefer-binary" shodan      && \
    pipx install --pip-args="--no-cache-dir --prefer-binary" censys

# - terrascan: policy-as-code scanner for IaC
RUN url="$(curl -s https://api.github.com/repos/tenable/terrascan/releases/latest \
      | awk -F'"' '/browser_download_url/ && /Linux_[xX]86_64\.tar\.gz/ {print $4; exit}')"; \
    curl -fsSL "$url" -o /tmp/terrascan.tgz; \
    tar -C /tmp -xzf /tmp/terrascan.tgz terrascan; \
    install /tmp/terrascan /usr/local/bin/terrascan; \
    rm -f /tmp/terrascan /tmp/terrascan.tgz

# - OpenTofu: Terraform-compatible IaC tool (APT repository)
RUN install -d -m 0755 /etc/apt/keyrings && \
    curl -fsSL https://get.opentofu.org/opentofu.gpg | tee /etc/apt/keyrings/opentofu.gpg >/dev/null && \
    curl -fsSL https://packages.opentofu.org/opentofu/tofu/gpgkey | gpg --no-tty --batch --dearmor -o /etc/apt/keyrings/opentofu-repo.gpg && \
    chmod a+r /etc/apt/keyrings/opentofu.gpg /etc/apt/keyrings/opentofu-repo.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/opentofu.gpg,/etc/apt/keyrings/opentofu-repo.gpg] https://packages.opentofu.org/opentofu/tofu/any/ any main" > /etc/apt/sources.list.d/opentofu.list && \
    echo "deb-src [signed-by=/etc/apt/keyrings/opentofu.gpg,/etc/apt/keyrings/opentofu-repo.gpg] https://packages.opentofu.org/opentofu/tofu/any/ any main" >> /etc/apt/sources.list.d/opentofu.list && \
    apt-get update && apt-get install -y --no-install-recommends tofu && \
    ln -sf /usr/bin/tofu /usr/local/bin/terraform

# AWS CLI v2 official
RUN cd /tmp && \
    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip && \
    unzip -q awscliv2.zip && ./aws/install && \
    rm -rf /tmp/aws /tmp/awscliv2.zip

# ==============================================================================
# Phase 5: Network & Reconnaissance Tools
# ==============================================================================
# - nmap: network exploration and security auditing
# - masscan: high-speed port scanner
# - autorecon: automated network reconnaissance
# - amass: in-depth attack surface mapping and asset discovery
# - subfinder: passive subdomain enumeration
# - sublist3r: fast subdomain enumeration
# - fierce: DNS reconnaissance
# - dnsenum: DNS enumeration
# - dnsrecon: DNS reconnaissance
# - theharvester: OSINT for emails, hosts, and subdomains
# - whois: domain registration query client
# - dnsutils: DNS utilities (dig, nslookup, etc.)
# - bind9-host: DNS lookup utility
# - responder: LLMNR, NBT-NS, and MDNS poisoner
# - netexec: network authentication and execution toolkit
# - enum4linux: Windows/Samba enumeration
# - enum4linux-ng: Windows/Samba enumeration (next-gen)
# - nbtscan: NetBIOS name scanner
# - arp-scan: ARP network scanner
# - samba-common-bin: Samba client utilities
# - smbclient: SMB/CIFS client
# - iproute2: provides `ip` (route/addr) used by wrappers
# - iputils-ping: ICMP ping
# - net-tools: legacy ifconfig/netstat (diagnostics)
# - ethtool: NIC/link diagnostics
# - traceroute: routing diagnostics
RUN apt-get install -y --no-install-recommends \
        nmap \
        masscan \
        autorecon \
        amass \
        subfinder \
        sublist3r \
        fierce \
        dnsenum \
        dnsrecon \
        theharvester \
        whois \
        dnsutils \
        bind9-host \
        responder \
        netexec \
        enum4linux \
        enum4linux-ng \
        nbtscan \
        arp-scan \
        samba-common-bin \
        smbclient \
        iproute2 \
        iputils-ping \
        net-tools \
        ethtool \
        traceroute

# - rustscan: modern and fast port scanner
RUN tmp="$(mktemp -d)"; cd "$tmp"; \
  url="$(curl -fsSL https://api.github.com/repos/bee-san/RustScan/releases/latest \
         | jq -r '.assets[]?.browser_download_url | select(endswith("rustscan.deb.zip"))' | head -n1)"; \
  [ -n "$url" ] || { echo "rustscan.deb.zip asset not found in latest release"; exit 1; }; \
  curl -fsSL -o rustscan.deb.zip "$url"; \
  unzip -q rustscan.deb.zip; \
  deb="$(printf '%s\n' rustscan*.deb | head -n1)"; \
  dpkg -i "$deb" || apt-get -f install -y --no-install-recommends; \
  cd /; rm -rf "$tmp"

# ==============================================================================
# Phase 6: Web Application Security Tools
# ==============================================================================
# - gobuster: directory and DNS enumeration
# - feroxbuster: recursive content discovery
# - ffuf: fast web fuzzer
# - dotdotpwn: path traversal fuzzer
# - xsser: cross-site scripting framework
# - wfuzz: web application fuzzer
# - dirb: web content scanner
# - dirsearch: web path scanner
# - nikto: web server scanner
# - sqlmap: automated SQL injection tool
# - wpscan: WordPress security scanner
# - arjun: HTTP parameter discovery
# - paramspider: parameter miner
# - hakrawler: web endpoint crawler
# - wafw00f: WAF fingerprinting
# - whatweb: web technology fingerprinting
# - burpsuite: web security testing platform
# - zaproxy: OWASP ZAP scanner
RUN apt-get install -y --no-install-recommends \
        seclists \
        gobuster \
        feroxbuster \
        ffuf \
        dotdotpwn \
        xsser \
        wfuzz \
        dirb \
        dirsearch \
        nikto \
        sqlmap \
        wpscan \
        arjun \
        paramspider \
        hakrawler \
        wafw00f \
        whatweb \
        burpsuite \
        zaproxy

# dirsearch requirements
# - python3-requests-ntlm: NTLM authentication
# - defusedxml: XML bomb protection for Python stdlib modules
# - colorama: cross-platform terminal colors
RUN python3 -m pip install --no-cache-dir requests-ntlm defusedxml colorama

# - katana: next-generation web crawler and spider
RUN set -euo pipefail; \
  tmp="$(mktemp -d)"; cd "$tmp"; \
  j="$(curl -fsSL https://api.github.com/repos/projectdiscovery/katana/releases/latest)"; \
  tag="$(printf '%s' "$j" | jq -r '.tag_name')"; \
  asset="$(printf '%s' "$j" | jq -r '.assets[]?.name | select(test("^katana_[0-9.]+_linux_amd64\\.zip$"))' | head -n1)"; \
  [ -n "$asset" ] || { echo 'katana: linux_amd64 zip asset not found'; exit 1; }; \
  curl -fsSL -o "$asset" "https://github.com/projectdiscovery/katana/releases/download/${tag}/${asset}"; \
  unzip -p "$asset" "*/katana" > katana 2>/dev/null || unzip -p "$asset" "katana" > katana; \
  chmod 0755 katana; install -m 0755 katana /usr/local/bin/katana; \
  cd /; rm -rf "$tmp"

# - httpx: fast HTTP probing with technology detection
RUN set -euo pipefail; \
  tmp="$(mktemp -d)"; cd "$tmp"; \
  j="$(curl -fsSL https://api.github.com/repos/projectdiscovery/httpx/releases/latest)"; \
  tag="$(printf '%s' "$j" | jq -r '.tag_name')"; \
  asset="$(printf '%s' "$j" | jq -r '.assets[]?.name | select(test("^httpx_[0-9.]+_linux_amd64\\.zip$"))' | head -n1)"; \
  [ -n "$asset" ] || { echo 'httpx: linux_amd64 zip asset not found'; exit 1; }; \
  curl -fsSL -o "$asset" "https://github.com/projectdiscovery/httpx/releases/download/${tag}/${asset}"; \
  unzip -p "$asset" "*/httpx" > httpx 2>/dev/null || unzip -p "$asset" "httpx" > httpx; \
  chmod 0755 httpx; install -m 0755 httpx /usr/local/bin/httpx; \
  cd /; rm -rf "$tmp"

# - nuclei: template-driven vulnerability scanner
RUN set -euo pipefail; \
  tmp="$(mktemp -d)"; cd "$tmp"; \
  j="$(curl -fsSL https://api.github.com/repos/projectdiscovery/nuclei/releases/latest)"; \
  tag="$(printf '%s' "$j" | jq -r '.tag_name')"; \
  asset="$(printf '%s' "$j" | jq -r '.assets[]?.name | select(test("^nuclei_[0-9.]+_linux_amd64\\.zip$"))' | head -n1)"; \
  [ -n "$asset" ] || { echo 'nuclei: linux_amd64 zip asset not found'; exit 1; }; \
  curl -fsSL -o "$asset" "https://github.com/projectdiscovery/nuclei/releases/download/${tag}/${asset}"; \
  unzip -p "$asset" "*/nuclei" > nuclei 2>/dev/null || unzip -p "$asset" "nuclei" > nuclei; \
  chmod 0755 nuclei; install -m 0755 nuclei /usr/local/bin/nuclei; \
  cd /; rm -rf "$tmp"

# - dalfox: fast XSS scanner
RUN set -euo pipefail; \
  tmp="$(mktemp -d)"; cd "$tmp"; \
  j="$(curl -fsSL https://api.github.com/repos/hahwul/dalfox/releases/latest)"; \
  tag="$(printf '%s' "$j" | jq -r '.tag_name')"; \
  [ -n "$tag" ]; \
  asset="dalfox-linux-amd64.tar.gz"; \
  curl -fsSL -o "$asset" "https://github.com/hahwul/dalfox/releases/download/${tag}/${asset}"; \
  tar -xOzf "$asset" dalfox-linux-amd64 > dalfox; \
  install -m 0755 dalfox /usr/local/bin/dalfox; \
  cd /; rm -rf "$tmp"

# - jaeles: signature-based web vulnerability scanner
RUN set -euo pipefail; \
  tmp="$(mktemp -d)"; cd "$tmp"; \
  j="$(curl -fsSL https://api.github.com/repos/jaeles-project/jaeles/releases/latest)"; \
  tag="$(printf '%s' "$j" | jq -r '.tag_name')"; \
  asset="$(printf '%s' "$j" | jq -r '.assets[]?.name | select(test("^jaeles-.*-linux\\.zip$"))' | head -n1)"; \
  [ -n "$asset" ] || { echo 'jaeles: linux zip asset not found'; exit 1; }; \
  curl -fsSL -o "$asset" "https://github.com/jaeles-project/jaeles/releases/download/${tag}/${asset}"; \
  unzip -p "$asset" "*/jaeles" > jaeles 2>/dev/null || unzip -p "$asset" "jaeles" > jaeles; \
  chmod 0755 jaeles; install -m 0755 jaeles /usr/local/bin/jaeles; \
  cd /; rm -rf "$tmp"

# - x8: fast XSS scanner
RUN set -euo pipefail; \
  tmp="$(mktemp -d)"; cd "$tmp"; \
  j="$(curl -fsSL https://api.github.com/repos/Sh1Yo/x8/releases/latest)"; \
  tag="$(printf '%s' "$j" | jq -r '.tag_name')"; \
  asset="$(printf '%s' "$j" | jq -r '.assets[]?.name | select(. == "x86_64-linux-x8.gz")' | head -n1)"; \
  [ -n "$asset" ] || { echo 'x8: x86_64-linux-x8.gz not found'; exit 1; }; \
  curl -fsSL -o "$asset" "https://github.com/Sh1Yo/x8/releases/download/${tag}/${asset}"; \
  gzip -dc "$asset" > x8; \
  chmod 0755 x8; install -m 0755 x8 /usr/local/bin/x8; \
  cd /; rm -rf "$tmp"

# - gau: URL discovery from AlienVault, Wayback Machine, Common Crawl, and URLScan.io
RUN set -euo pipefail; \
  tmp="$(mktemp -d)"; cd "$tmp"; \
  j="$(curl -fsSL https://api.github.com/repos/lc/gau/releases/latest)"; \
  tag="$(printf '%s' "$j" | jq -r '.tag_name')"; \
  asset="$(printf '%s' "$j" | jq -r '.assets[]?.name | select(test("^gau_[0-9.]+_linux_amd64\\.tar\\.gz$"))' | head -n1)"; \
  [ -n "$asset" ] || { echo 'gau: linux_amd64 tar.gz asset not found'; exit 1; }; \
  curl -fsSL -o "$asset" "https://github.com/lc/gau/releases/download/${tag}/${asset}"; \
  tar -xOzf "$asset" gau > gau; \
  install -m 0755 gau /usr/local/bin/gau; \
  cd /; rm -rf "$tmp"


# ==============================================================================
# Phase 7: Authentication & Password Security
# ==============================================================================
# - hydra: network login cracker
# - john: password cracker
# - hashcat: gpu-accelerated password recovery
# - medusa: parallel brute-forcer
# - patator: multi-purpose brute-forcer
# - evil-winrm: WinRM shell for Windows
# - hash-identifier: hash type identifier
# - hashid: hash algorithm identifier
# - ophcrack: Windows password cracker
# - hashcat-utils: companion utilities for hashcat
RUN apt-get install -y --no-install-recommends \
        hydra \
        john \
        hashcat \
        medusa \
        patator \
        evil-winrm \
        hash-identifier \
        hashid \
        ophcrack \
        hashcat-utils

# ==============================================================================
# Phase 8: Binary & Forensics Tools
# ==============================================================================
# - gdb: GNU debugger
# - radare2: reverse engineering framework
# - ghidra: software reverse engineering suite
# - binwalk: firmware analysis tool
# - checksec: binary security checks
# - foremost: file carving utility
# - steghide: steganography tool
# - exiftool: metadata extraction
# - ropper: ROP gadget finder
# - autopsy: digital forensics platform
# - sleuthkit: digital forensics toolkit
# - outguess: steganography analysis
# - testdisk: data recovery utility
# - scalpel: file carving utility
# - bulk-extractor: bulk data extractor for forensics
# - smbmap: SMB share enumerator
# - zbar-tools: barcode and QR decoding
# - apktool: Android APK analysis
# - android-tools-adb: Android Debug Bridge
# - xxd: hex dump utility
RUN apt-get install -y --no-install-recommends \
        gdb \
        radare2 \
        ghidra \
        binwalk \
        checksec \
        foremost \
        steghide \
        exiftool \
        ropper \
        autopsy \
        sleuthkit \
        outguess \
        testdisk \
        scalpel \
        bulk-extractor \
        smbmap \
        zbar-tools \
        apktool \
        android-tools-adb \
        xxd

# - ropgadget: ROP/JOP gadget finder
# - volatility3: memory forensics framework
# - uro: URL deduplication and normalization
# - pwntools: CTF and exploit development library
RUN pip install --no-cache-dir \
        ropgadget \
        volatility3 \
        uro \
        pwntools

# pwninit: CTF binary setup automation
RUN tmp="$(mktemp -d)"; cd "$tmp"; \
  json="$(curl -fsSL https://api.github.com/repos/io12/pwninit/releases/latest)"; \
  url="$(printf '%s\n' "$json" | jq -r '.assets[]?.browser_download_url' | grep -E '/pwninit($|[^/]*$)' | head -n1)"; \
  [ -n "$url" ] || { echo "No binary asset for pwninit latest"; exit 1; }; \
  curl -fsSL -o pwninit "$url"; \
  chmod +x pwninit; install -m 0755 pwninit /usr/local/bin/pwninit; \
  cd /; rm -rf "$tmp"

# - zsteg: PNG/BMP steganography detection
# - one_gadget: ROP gadget finder for glibc
RUN gem install --no-document zsteg one_gadget

# - hashpump: length extension attack helper (via hashpumpy CLI wrapper)
RUN pip install --no-cache-dir hashpumpy && \
    printf '%s\n' '#!/usr/bin/env python3' \
'import argparse' \
'from hashpumpy import hashpump' \
'parser = argparse.ArgumentParser()' \
'parser.add_argument("-s","--signature", required=True)' \
'parser.add_argument("-d","--data", required=True)' \
'parser.add_argument("-k","--key_length", type=int, required=True)' \
'parser.add_argument("-a","--append_data", required=True)' \
'args = parser.parse_args()' \
'new_sig, new_msg = hashpump(args.signature, args.data, args.append_data, args.key_length)' \
'print(new_sig)' \
'print(new_msg)' \
> /usr/local/bin/hashpump && chmod +x /usr/local/bin/hashpump

# ==============================================================================
# Phase 9: OSINT & Intelligence Tools
# ==============================================================================
# - exploitdb: exploit database search client
# - kismet: wireless network detector and sniffer
# - sherlock: username enumeration across sites
# - recon-ng: web reconnaissance framework
# - spiderfoot: automated OSINT platform
# - maltego: graphical link analysis
RUN apt-get install -y --no-install-recommends \
        exploitdb \
        kismet \
        sherlock \
        recon-ng \
        spiderfoot \
        maltego

# OSINT companion CLIs via npm (Node.js LTS runtime)
# - social-analyzer: social media analysis toolkit
# - pwned: have i been pwned? CLI
# - graphql-inspector: GraphQL diffing and audit utility
# - jwt-cracker: JSON Web Token cracking utility
# - graphql-playground-html: GraphQL playground HTML renderer
# - graphql-voyager: GraphQL schema visualization
# - newman: Postman CLI runner
RUN npm install -g \
        social-analyzer \
        pwned \
        graphql-inspector \
        jwt-cracker \
        graphql-playground-html \
        graphql-voyager \
        newman

# GitHub releases for tomnomnom tools
# - anew: append-only unique line filter
# - qsreplace: query string replacement
# - waybackurls: URL collection from Wayback Machine
# - assetfinder: subdomain discovery
RUN tmp="$(mktemp -d)"; cd "$tmp"; \
  for repo in tomnomnom/anew tomnomnom/qsreplace tomnomnom/waybackurls; do \
    name="${repo##*/}"; \
    json="$(curl -fsSL "https://api.github.com/repos/${repo}/releases/latest")"; \
    url="$(printf '%s' "$json" | jq -r '.assets[]?.browser_download_url' | grep -E -- '-linux-amd64($|.*\.(tgz|tar\.gz|zip)$)' | head -n1)"; \
    [ -n "$url" ] || { echo "No linux-amd64 asset for ${repo} latest"; exit 1; }; \
    file="${url##*/}"; curl -fsSL -o "$file" "$url"; \
    case "$file" in \
      *.tgz|*.tar.gz) tar -xzf "$file" ;; \
      *.zip) unzip -q "$file" ;; \
      *) : ;; \
    esac; \
    bin_path="$(find . -type f -perm -111 -name "${name}*" | head -n1)"; \
    [ -n "$bin_path" ] || bin_path="./$name"; \
    [ -f "$bin_path" ] || bin_path="$(find . -maxdepth 1 -type f -perm -111 | head -n1)"; \
    [ -n "$bin_path" ] || { echo "No executable found for ${repo}"; exit 1; }; \
    install -m 0755 "$bin_path" "/usr/local/bin/$name"; \
    rm -rf ./*; \
  done; \
  # assetfinder: /releases/latest may return 404 → use /releases (first item)
  repo="tomnomnom/assetfinder"; name="assetfinder"; \
  json="$(curl -fsSL "https://api.github.com/repos/${repo}/releases")"; \
  url="$(printf '%s' "$json" | jq -r '.[0].assets[]?.browser_download_url' | grep -E -- '-linux-amd64($|.*\.(tgz|tar\.gz|zip)$)' | head -n1)"; \
  [ -n "$url" ] || { echo "No linux-amd64 asset for ${repo}"; exit 1; }; \
  file="${url##*/}"; curl -fsSL -o "$file" "$url"; \
  case "$file" in \
    *.tgz|*.tar.gz) tar -xzf "$file" ;; \
    *.zip) unzip -q "$file" ;; \
    *) : ;; \
  esac; \
  bin_path="$(find . -type f -perm -111 -name "${name}*" | head -n1)"; \
  [ -n "$bin_path" ] || bin_path="./$name"; \
  [ -f "$bin_path" ] || bin_path="$(find . -maxdepth 1 -type f -perm -111 | head -n1)"; \
  [ -n "$bin_path" ] || { echo "No executable found for ${repo}"; exit 1; }; \
  install -m 0755 "$bin_path" "/usr/local/bin/$name"; \
  cd /; rm -rf "$tmp"

# Bundle isolated Node.js 18 runtime for insomnia-inso only
COPY --from=insomnia-node18-builder /opt/insomnia-artifacts/node18 /opt/insomnia-node18
COPY --from=insomnia-node18-builder /opt/insomnia-artifacts/insomnia /opt/insomnia

# ==============================================================================
# Phase 10: Wireless & Packet Analysis Tools
# ==============================================================================
# - wireshark: network protocol analyzer
# - tshark: terminal Wireshark analyzer
# - tcpdump: packet capture utility
# - aircrack-ng: 802.11 WEP/WPA cracking suite
RUN apt-get install -y --no-install-recommends \
        wireshark \
        tshark \
        tcpdump \
        aircrack-ng

# ==============================================================================
# Phase 11: Exploitation Frameworks
# ==============================================================================
# - metasploit-framework: penetration testing framework
RUN apt-get install -y --no-install-recommends \
        metasploit-framework

# ==============================================================================
# Phase 12: Runtime Security Agents
# ==============================================================================
# - falco: runtime threat detection for containers and hosts
RUN install -d -m 0755 /usr/share/keyrings && \
    curl -fsSL https://falco.org/repo/falcosecurity-packages.asc \
      | gpg --dearmor -o /usr/share/keyrings/falco-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/falco-archive-keyring.gpg] https://download.falco.org/packages/deb stable main" \
      > /etc/apt/sources.list.d/falcosecurity.list && \
    apt-get update -y && \
    mkdir -p /tmp/falco && cd /tmp/falco && \
    apt-get download falco && \
    dpkg-deb -x ./falco_*.deb / && \
    cd / && rm -rf /tmp/falco

# ==============================================================================
# Phase 13: Browser Agent Requirements
# ==============================================================================
# - chromium: headless-capable browser
# - chromium-driver: WebDriver for Chromium
RUN apt-get install -y --no-install-recommends \
      chromium \
      chromium-driver

# ==============================================================================
# Phase 14: Security Tool Repositories & Wrappers
# Bring CloudMapper code and its dedicated venv from the builder stage
COPY --from=cloudmapper-builder /opt/venvs/cloudmapper /opt/venvs/cloudmapper
COPY --from=cloudmapper-builder /opt/hexstrike/tools/cloudmapper /opt/hexstrike/tools/cloudmapper

# Install system deps for Pacu (cffi may require libffi); then install Pacu via pipx on Python 3.12
RUN apt-get install -y --no-install-recommends libffi-dev \
 && pipx install --python /usr/local/bin/python3.12 git+https://github.com/RhinoSecurityLabs/pacu.git

# Clone remaining tool repositories
RUN mkdir -p /opt/hexstrike/tools && \
    git clone --depth 1 https://github.com/ticarpi/jwt_tool.git /opt/hexstrike/tools/jwt_tool && \
    rm -rf /opt/hexstrike/tools/jwt_tool/.git && \
    git clone --depth 1 https://github.com/niklasb/libc-database.git /opt/hexstrike/tools/libc-database && \
    rm -rf /opt/hexstrike/tools/libc-database/.git && \
    git clone --depth 1 https://github.com/longld/peda.git /root/peda && \
    rm -rf /root/peda/.git && \
    mkdir -p /opt/stegsolve && \
    curl -fsSL -o /opt/stegsolve/stegsolve.jar https://github.com/Giotino/stegsolve/releases/download/v1.4/StegSolve-1.4.jar && \
    chmod 644 /opt/stegsolve/stegsolve.jar && \
    ln -s /opt/hexstrike/tools/libc-database /opt/libc-database && \
    ln -s /opt/hexstrike/tools/jwt_tool /opt/jwt_tool

RUN pip install --no-cache-dir -r /opt/hexstrike/tools/jwt_tool/requirements.txt

# ==============================================================================
# Phase 15: Cloud & Container Security Binaries
# ==============================================================================
# - trivy: container image vulnerability scanner
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
  | sh -s -- -b /usr/local/bin

# - docker-bench-security: Docker daemon configuration audit
RUN mkdir -p /opt/hexstrike/tools && \
    git clone --depth 1 https://github.com/docker/docker-bench-security.git /opt/hexstrike/tools/docker-bench-security && \
    rm -rf /opt/hexstrike/tools/docker-bench-security/.git && \
    printf '#!/bin/bash\nset -e\ncd /opt/hexstrike/tools/docker-bench-security\nexec ./docker-bench-security.sh "$@"\n' > /usr/local/bin/docker-bench-security && \
    chmod +x /usr/local/bin/docker-bench-security

# - clairctl: container vulnerability assessment CLI (amd64/arm64)
# NOTE: currently clariictl does not work without a running clair server + postgresql in separate containers
RUN arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) url="https://github.com/quay/clair/releases/latest/download/clairctl-linux-amd64";; \
      arm64) url="https://github.com/quay/clair/releases/latest/download/clairctl-linux-arm64";; \
      *) echo "unsupported arch for clairctl: $arch"; exit 1;; \
    esac; \
    curl -fsSL "$url" -o /usr/local/bin/clairctl; \
    chmod 0755 /usr/local/bin/clairctl; \
    /usr/local/bin/clairctl --version

# - kube-bench: CIS Kubernetes benchmark auditing
RUN tmp=$(mktemp -d); cd "$tmp"; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) suffix="amd64";; \
      arm64) suffix="arm64";; \
      *) echo "unsupported arch for kube-bench: $arch"; exit 1;; \
    esac; \
    tag=$(curl -fsSL https://api.github.com/repos/aquasecurity/kube-bench/releases/latest | jq -r '.tag_name'); \
    file="kube-bench_${tag#v}_linux_${suffix}.tar.gz"; \
    curl -fsSL -o kube-bench.tgz "https://github.com/aquasecurity/kube-bench/releases/download/${tag}/${file}"; \
    tar -xzf kube-bench.tgz; \
    install -m 0755 kube-bench /usr/local/bin/kube-bench; \
    cd /; rm -rf "$tmp"

# Kubernetes CLI
RUN set -euo pipefail; \
  arch="$(dpkg --print-architecture)"; case "$arch" in amd64) karch="amd64";; arm64) karch="arm64";; *) echo "unsupported arch for kubectl: $arch"; exit 1;; esac; \
  KVER="$(curl -fsSL https://dl.k8s.io/release/stable.txt)"; \
  curl -fsSLo /usr/local/bin/kubectl "https://dl.k8s.io/release/${KVER}/bin/linux/${karch}/kubectl"; \
  chmod 0755 /usr/local/bin/kubectl; \
  /usr/local/bin/kubectl version --client --output=yaml >/dev/null

# Install Docker CLI from official Docker repository to talk to host's Docker/Podman API socket 
# Note: necessary for kube-bench
RUN set -euo pipefail; \
  # Add Docker's official GPG key:
  install -m 0755 -d /etc/apt/keyrings; \
  curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc; \
  chmod a+r /etc/apt/keyrings/docker.asc; \
  # Add the repository to Apt sources:
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
    trixie stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null; \
  apt-get update; \
  # Install latest Docker CLI
  apt-get install -y --no-install-recommends docker-ce-cli;

# ==============================================================================
# Phase 16: MCP Entry Points & Minimal Wrappers
# ==============================================================================
RUN set -eu; \
    # CloudMapper wrapper: ensure execution via its dedicated venv
    printf '#!/bin/bash\n/opt/venvs/cloudmapper/bin/python /opt/hexstrike/tools/cloudmapper/cloudmapper.py "$@"\n' \
      > /usr/local/bin/cloudmapper && chmod +x /usr/local/bin/cloudmapper && \
    # Insomnia CLI wrapper: run with isolated Node 18 runtime
    printf '#!/bin/bash\nPATH=/opt/insomnia-node18/bin:$PATH NODE_PATH=/opt/insomnia/lib/node_modules exec /opt/insomnia/bin/inso "$@"\n' \
      > /usr/local/bin/insomnia && chmod +x /usr/local/bin/insomnia && \
    # StegSolve wrapper: run jar with Java
    printf '#!/bin/bash\nexec java -jar /opt/stegsolve/stegsolve.jar "$@"\n' \
      > /usr/local/bin/stegsolve && chmod +x /usr/local/bin/stegsolve && \
    # JWT analyzer convenience wrapper
    printf '#!/bin/bash\nexec python3 /opt/hexstrike/tools/jwt_tool/jwt_tool.py "$@"\n' \
      > /usr/local/bin/jwt-analyzer && chmod +x /usr/local/bin/jwt-analyzer && \
    # API schema analyzer helper (minimal, prints endpoints + verbs)
    printf '#!/usr/bin/env python3\nimport json,sys\nif len(sys.argv)<2:\n print("Usage: api-schema-analyzer <schema-file>"); sys.exit(1)\npath=sys.argv[1]\nwith open(path,"r",encoding="utf-8") as h:\n data=json.load(h)\npaths=data.get("paths",{})\nprint(f"Endpoints: {len(paths)}")\nfor route,methods in paths.items():\n verbs=\", \".join(m.upper() for m in methods.keys())\n print(f\"- {route}: {verbs}\")\n' \
      > /usr/local/bin/api-schema-analyzer && chmod +x /usr/local/bin/api-schema-analyzer && \
    # GraphQL helpers via npx
    printf '#!/bin/bash\nexec npx --yes graphql-playground-html "$@"\n' \
      > /usr/local/bin/graphql-playground && chmod +x /usr/local/bin/graphql-playground && \
    printf '#!/bin/bash\nexec npx --yes graphql-voyager "$@"\n' \
      > /usr/local/bin/graphql-voyager && chmod +x /usr/local/bin/graphql-voyager && \
    \
    printf '#!/usr/bin/env python3\nimport runpy,sys\nsys.argv=["patator"]+sys.argv[1:]\nrunpy.run_path("/usr/share/patator/patator.py", run_name="__main__")\n' \
      > /usr/local/bin/patator && chmod +x /usr/local/bin/patator && \
    printf '#!/usr/bin/env node\nconst r=require("child_process").execSync("npm root -g").toString().trim();require(r+"/social-analyzer/index.js");\n' \
      > /usr/local/bin/social-analyzer && chmod +x /usr/local/bin/social-analyzer && \
    \
    # hashcat-utils binary does not exist. Provide a real entry point the server checks
    printf '#!/bin/bash\n# This launcher exists because the Debian/Kali package "hashcat-utils" ships multiple executables (e.g., cap2hccapx),\n# but no single binary literally named "hashcat-utils". The server health check expects that name.\n# We delegate to a real tool from the suite so the check is truthful; if tools are missing, this fails naturally.\nexec cap2hccapx "$@"\n' \
      > /usr/local/bin/hashcat-utils && chmod +x /usr/local/bin/hashcat-utils && \
    \
    # Volatility name variants expected by the server
    printf '#!/bin/bash\nexec python3 -m volatility3 "$@"\n' \
      > /usr/local/bin/vol.py && chmod +x /usr/local/bin/vol.py && \
    printf '#!/bin/bash\nexec python3 -m volatility3 "$@"\n' \
      > /usr/local/bin/volatility && chmod +x /usr/local/bin/volatility && \
    ln -sf /opt/hexstrike/venv/bin/vol             /usr/local/bin/volatility3 && \
    ln -sf /opt/hexstrike/venv/bin/vol             /usr/local/bin/vol && \
    \
    # Compatibility aliases required by hexstrike_server.py ---
    ln -sf /usr/bin/searchsploit                   /usr/local/bin/exploit-db && \
    ln -sf /usr/local/bin/newman                   /usr/local/bin/postman && \
    ln -sf /usr/bin/http                           /usr/local/bin/httpie && \
    ln -sf /usr/local/bin/graphql-inspector        /usr/local/bin/graphql-scanner && \
    ln -sf /usr/bin/tsk_loaddb                     /usr/local/bin/sleuthkit && \
    ln -sf /usr/bin/msfconsole                     /usr/local/bin/metasploit && \
    ln -sf /usr/local/bin/pwned                    /usr/local/bin/have-i-been-pwned && \
    ln -sf /usr/local/bin/clairctl                 /usr/local/bin/clair && \
    ln -sf /usr/bin/bulk_extractor                 /usr/local/bin/bulk-extractor && \
    ln -sf /usr/local/bin/one_gadget               /usr/local/bin/one-gadget && \
    ln -sf /root/.local/bin/censys                 /usr/local/bin/censys-cli && \
    ln -sf /root/.local/bin/shodan                 /usr/local/bin/shodan-cli && \
    ln -sf /opt/hexstrike/tools/libc-database/find /usr/local/bin/libc-database && \
    ln -sf /opt/hexstrike/venv/bin/ROPgadget       /usr/local/bin/ropgadget && \
    ln -sf /opt/hexstrike/venv/bin/pwn             /usr/local/bin/pwntools && \
    ln -sf /root/.local/bin/scout                  /usr/local/bin/scout-suite && \
    ln -sf /usr/bin/evil-winrm                     /usr/local/bin/evil-winrm && \
    ln -sf /usr/bin/maltego                        /usr/local/bin/maltego && \
    ln -sf /usr/share/ghidra/support/analyzeHeadless /usr/local/bin/analyzeHeadless && \
    \
    # Wordlists position for dirsearch as expected by server and client
    mkdir -p /usr/share/wordlists/dirsearch /usr/share/wordlists/dirbuster && \
    ln -sf /usr/share/wordlists/dirb/common.txt /usr/share/wordlists/dirsearch/common.txt && \
    # Wordlists position for Gobuster/Feroxbuster as expected by server
    ln -sf /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
          /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt

# Provide fix ExportProgramScript.java avoiding Ghidra NullPointerException
COPY docker/files/ghidra/ExportProgramScript.java /usr/share/ghidra/Ghidra/Features/Base/ghidra_scripts/ExportProgramScript.java

# ==============================================================================
# Phase 17: Image Cleanup
# ==============================================================================
RUN apt-get clean && rm -rf /var/lib/apt/lists/* && \
    # Hide Message from Kali developers on login
    touch ~/.hushlogin

# ==============================================================================
# Phase 18: MCP Server and Runtime Configuration
# ==============================================================================
# Copy requirements.txt first for Docker layer caching optimization
COPY requirements.txt /opt/hexstrike/

# Install core Python dependencies into virtual environment
# Production WSGI server for better performance than Flask dev server
RUN pip install --no-cache-dir gunicorn -r /opt/hexstrike/requirements.txt

VOLUME ["/root/.cache/trivy", \
        "/root/.wpscan/db",   \
        "/root/.config/amass", \
        "/root/nuclei-templates", \
        "/root/.msf4", \
        "/workspace"]

# Copy server code at the end to leverage Docker layer caching
COPY hexstrike_server.py /opt/hexstrike/

# Expose MCP server port
EXPOSE 8888

# Copy optimized entrypoint that pre-warms local caches and starts the MCP server
COPY --chmod=0755 docker/config/entrypoint.sh docker/config/update-tools-databases.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh
CMD ["/usr/local/bin/entrypoint.sh"]
