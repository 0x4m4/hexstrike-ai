# Dockerfile for HexStrike AI MCP Swissknife
# -------------------------------------------------------------
FROM kalilinux/kali-last-release

# Section 1: OS Upgrade & Core Utilities
RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get -y install apt-utils curl wget gnupg2 lsb-release software-properties-common build-essential

# Section 2: Language Runtimes
RUN apt-get -y install python3 python3-pip python3-venv \
    golang \
    nodejs npm \
    default-jdk \
    ruby-full

# Section 3: Rust Installation (Official Installer)
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y && \
    export PATH="$PATH:/root/.cargo/bin"

# Section 4: Compilation Tools
RUN apt-get -y install gcc g++ make autoconf automake pkg-config

# Section 5: Security Tools (APT)
RUN apt-get -y install nmap masscan autorecon amass subfinder fierce dnsenum theharvester responder netexec enum4linux-ng gobuster feroxbuster ffuf dirb dirsearch nuclei nikto sqlmap wpscan arjun paramspider hakrawler wafw00f hydra john hashcat medusa patator evil-winrm hash-identifier ophcrack ghidra radare2 gdb binwalk checksec foremost steghide exiftool autopsy sleuthkit outguess testdisk scalpel bulk-extractor sherlock recon-ng maltego spiderfoot

# Section 6: Python Libraries

# Section 5b: Critical Tools via pip/npm/gem/go
# Rustscan
RUN /root/.cargo/bin/cargo install rustscan || true
# x8, katana, httpx, dalfox, jaeles, gau, waybackurls
RUN go install github.com/evilsocket/x8/cmd/x8@latest || true
RUN go install github.com/projectdiscovery/katana/cmd/katana@latest || true
RUN go install github.com/projectdiscovery/httpx/cmd/httpx@latest || true
RUN go install github.com/hahwul/dalfox@latest || true
RUN go install github.com/jaeles-project/jaeles@latest || true
RUN go install github.com/lc/gau@latest || true
RUN go install github.com/tomnomnom/waybackurls@latest || true
# ropgadget
RUN pip3 install ropgadget || true
# volatility3
RUN pip3 install volatility3 || true
# prowler, scout-suite, checkov, terrascan
RUN pip3 install prowler scout-suite checkov terrascan || true
# kube-hunter, kube-bench, docker-bench-security, falco
RUN pip3 install kube-hunter kube-bench docker-bench-security falco || true
# zsteg
RUN gem install zsteg || true
# social-analyzer, shodan-cli, censys-cli
RUN npm install -g social-analyzer shodan-cli censys-cli || true



COPY requirements.txt /opt/hexstrike/requirements.txt

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip3 install --upgrade pip setuptools wheel

RUN pip3 install -r /opt/hexstrike/requirements.txt

# Section 7: MCP Application
WORKDIR /opt/hexstrike/
COPY . /opt/hexstrike/

# Section 8: Expose Ports & Entrypoint
EXPOSE 8888

CMD ["python3", "hexstrike_server.py"]
