# Basis-Image mit Python und Pentesting-Tools
FROM kalilinux/kali-rolling

# System-Updates und Installation der Basis-Tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nmap \
    gobuster \
    nikto \
    sqlmap \
    curl \
    git \
    && apt-get clean

# Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere die Abhängigkeiten (falls du eine requirements.txt hast, sonst überspringen wir das hier)
# Falls du eine hast: COPY requirements.txt .
# Da wir die Skripte direkt haben, installieren wir die Core-Libs:
RUN pip3 install --no-cache-dir --break-system-packages \
    flask \
    requests \
    psutil \
    beautifulsoup4 \
    selenium \
    aiohttp \
    mcp \
    fastmcp

# Kopiere deine Skripte in den Container
COPY hexstrike_server.py .
COPY hexstrike_mcp.py .
COPY hexstrike-ai-mcp.json .

# Exponiere den Port für den Server
EXPOSE 8888

# Startbefehl: Startet den HexStrike Server
CMD ["python3", "hexstrike_server.py"]