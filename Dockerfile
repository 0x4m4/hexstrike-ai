# Use Kali Linux as base for all security tools
FROM kalilinux/kali-rolling:latest

# Set metadata
LABEL maintainer="jjtech23@yahoo.com"
LABEL description="HexStrike AI - AI-Powered Security Testing Platform"
LABEL version="6.0.0"

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Update and install system dependencies
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y \
    # Core utilities
    curl \
    wget \
    git \
    vim \
    net-tools \
    iputils-ping \
    dnsutils \
    # Python
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    # Build tools
    build-essential \
    gcc \
    g++ \
    make \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Network & Reconnaissance Tools
RUN apt-get update && apt-get install -y \
    nmap \
    masscan \
    rustscan \
    amass \
    subfinder \
    nuclei \
    fierce \
    dnsenum \
    theharvester \
    responder \
    netexec \
    enum4linux-ng \
    arp-scan \
    nbtscan \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Web Application Security Tools
RUN apt-get update && apt-get install -y \
    gobuster \
    feroxbuster \
    dirsearch \
    ffuf \
    dirb \
    httpx-toolkit \
    nikto \
    sqlmap \
    wpscan \
    arjun \
    wafw00f \
    wfuzz \
    zaproxy \
    xsser \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Password & Authentication Tools
RUN apt-get update && apt-get install -y \
    hydra \
    john \
    hashcat \
    medusa \
    crackmapexec \
    evil-winrm \
    ophcrack \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Binary Analysis & Reverse Engineering Tools
RUN apt-get update && apt-get install -y \
    gdb \
    gdb-peda \
    radare2 \
    ghidra \
    binwalk \
    checksec \
    objdump \
    binutils \
    strace \
    ltrace \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Forensics & CTF Tools
RUN apt-get update && apt-get install -y \
    volatility3 \
    foremost \
    steghide \
    exiftool \
    autopsy \
    sleuthkit \
    scalpel \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Wireless Tools
RUN apt-get update && apt-get install -y \
    aircrack-ng \
    reaver \
    kismet \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Exploitation Tools
RUN apt-get update && apt-get install -y \
    metasploit-framework \
    msfconsole \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install OSINT Tools
RUN apt-get update && apt-get install -y \
    recon-ng \
    maltego \
    sherlock \
    spiderfoot \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install additional tools via Go (if needed)
RUN apt-get update && apt-get install -y golang-go && \
    go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest && \
    go install github.com/projectdiscovery/httpx/cmd/httpx@latest && \
    go install github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest && \
    go install github.com/tomnomnom/waybackurls@latest && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Add Go binaries to PATH
ENV PATH="/root/go/bin:${PATH}"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Install additional Python packages for monitoring
RUN pip3 install --no-cache-dir --break-system-packages \
    prometheus-client \
    psutil \
    redis \
    psycopg2-binary

# Copy application files
COPY . .

# Create directories for results and configs
RUN mkdir -p /app/results /app/logs /app/configs

# Expose ports
EXPOSE 8888

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8888/health || exit 1

# Set entrypoint
ENTRYPOINT ["python3"]
CMD ["hexstrike_server.py", "--port", "8888"]