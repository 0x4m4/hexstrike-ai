FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by the Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libpcap-dev \
    build-essential \
    chromium \
    chromium-driver \
    nmap \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
# Skip heavy optional packages (angr, pwntools) to keep image lean
COPY requirements.txt .
RUN pip install --no-cache-dir \
    flask \
    requests \
    psutil \
    "mcp[cli]" \
    fastmcp \
    beautifulsoup4 \
    selenium \
    webdriver-manager \
    aiohttp \
    mitmproxy \
    || true

# Copy server script
COPY hexstrike_server.py .

EXPOSE 8888

ENV HEXSTRIKE_PORT=8888

CMD ["python3", "hexstrike_server.py"]
