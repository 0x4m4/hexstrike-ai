# Dockerfile for HexStrike AI MCP Swissknife
# -------------------------------------------------------------
FROM kalilinux/kali-last-release

# Force IPv4-only DNS and apt retries for flaky mirrors
RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4 && \
    echo 'Acquire::Retries "3";' >> /etc/apt/apt.conf.d/99force-ipv4 && \
    echo 'precedence ::ffff:0:0/96 100' >> /etc/gai.conf

# Section 1: OS Upgrade & Core Utilities
RUN apt-get update -o Acquire::Retries=5 && apt full-upgrade -y && \
    apt-get -y install -o Acquire::Retries=5 apt-utils curl wget gnupg2 lsb-release software-properties-common build-essential wordlists git libjpeg-dev

# Section 2: Language Runtimes
RUN apt-get -y install python3 python3-pip python3-venv \
    golang \
    nodejs npm \
    default-jdk \
    ruby-full

# Section 3: Rust Installation (Official Installer)
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y

# Section 4: Compilation Tools
RUN apt-get -y install gcc g++ make autoconf automake pkg-config

# Section 5: Security Tools (APT)
RUN apt-get -y install \
    nmap masscan autorecon amass subfinder fierce dnsenum theharvester \
    responder netexec enum4linux-ng gobuster feroxbuster ffuf dirb dirsearch \
    nuclei nikto sqlmap wpscan arjun hakrawler wafw00f \
    hydra john hashcat medusa patator evil-winrm hash-identifier ophcrack \
    ghidra radare2 gdb binwalk checksec foremost steghide exiftool \
    autopsy sleuthkit testdisk scalpel bulk-extractor \
    sherlock recon-ng maltego spiderfoot arp-scan exploitdb getallurls \
    httpie kismet ropper && \
    rm -rf /var/lib/apt/lists/*

# Section 5b: outguess (removed from Kali repos, build from source)
RUN git clone https://github.com/resurrecting-open-source-projects/outguess.git /tmp/outguess && \
    cd /tmp/outguess && ./autogen.sh && ./configure --with-generic-jconfig && make && make install && \
    rm -rf /tmp/outguess || true

# Section 6: Set up Go/Rust/Cargo paths BEFORE tool installs
ENV GOPATH=/root/go \
    GOBIN=/usr/local/bin \
    PATH="/opt/venv/bin:/usr/local/bin:/root/go/bin:/root/.cargo/bin:${PATH}"

RUN go env -w GOBIN=/usr/local/bin

# Section 7: Cargo-based tools
RUN /root/.cargo/bin/cargo install rustscan pwninit || true

# Section 8: Go-based tools (each independent so one failure doesn't block others)
RUN go install github.com/projectdiscovery/katana/cmd/katana@latest || true
RUN go install github.com/projectdiscovery/httpx/cmd/httpx@latest || true
RUN go install github.com/hahwul/dalfox/v2@latest || true
RUN go install github.com/jaeles-project/jaeles@latest || true
RUN go install github.com/tomnomnom/waybackurls@latest || true
RUN go install github.com/tomnomnom/anew@latest || true
RUN go install github.com/tomnomnom/qsreplace@latest || true

RUN jaeles config init || true

# Section 9: Ruby/NPM tools
RUN gem install zsteg || true
RUN npm install -g social-analyzer shodan-cli censys-cli pwned || true

# Section 10: Python Virtual Environment & Dependencies
COPY requirements.txt /opt/hexstrike/requirements.txt

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip3 install --upgrade pip setuptools wheel && \
    pip3 install -r /opt/hexstrike/requirements.txt && \
    pip3 install "bcrypt<4.1" "passlib>=1.7.4" && \
    pip3 install ropgadget volatility3 ROPGadget pwntools || true

RUN pip3 install prowler scout-suite checkov terrascan || true
RUN pip3 install kube-hunter kube-bench docker-bench-security falco || true

# paramspider (not packaged in Kali, install via pip)
RUN pip3 install git+https://github.com/devanshbatham/ParamSpider.git || true

# Section 11: MCP Application
WORKDIR /opt/hexstrike/
COPY . /opt/hexstrike/

# Section 12: Healthcheck & Entrypoint
EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8888/health || exit 1

CMD ["python3", "hexstrike_server.py"]
