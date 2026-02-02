# Basis-Image mit Python und Pentesting-Tools
FROM kalilinux/kali-rolling

# System-Updates und Installation der Basis-Tools + Abhängigkeiten für mitmproxy
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    libffi-dev \
    libssl-dev \
    nmap \
    gobuster \
    nikto \
    sqlmap \
    curl \
    git \
    nuclei \
    && apt-get clean

# Arbeitsverzeichnis im Container
WORKDIR /app

# Core-Libs und die fehlenden Module installieren
# WICHTIG: mitmproxy hier hinzufügen
RUN pip3 install --no-cache-dir --break-system-packages \
    flask \
    requests \
    psutil \
    beautifulsoup4 \
    selenium \
    aiohttp \
    mcp \
    fastmcp \
    mitmproxy

# Kopiere deine Skripte in den Container
COPY hexstrike_server.py .
COPY hexstrike_mcp.py .
COPY hexstrike-ai-mcp.json .

# Exponiere den Port für den Server (8888) und den Proxy (8080)
EXPOSE 8888 8080

# Startbefehl
CMD ["python3", "hexstrike_server.py"]