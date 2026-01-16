# Use Kali Linux as the base image
FROM kalilinux/kali-rolling

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Update and install Python, pip, and the security tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    # --- ADDED FOR COMPILING PYTHON PACKAGES ---
    build-essential \
    python3-dev \
    # -------------------------------------------
    python3 python3-pip python3-venv \
    git curl wget sudo gnupg2 ca-certificates \
    # Network & Recon
    nmap masscan amass subfinder nuclei dnsenum \
    # Web App Security
    gobuster dirb ffuf nikto sqlmap wpscan \
    # Password & Auth
    hydra john hashcat \
    # Binary Analysis
    gdb binwalk \
    # Browser requirements
    chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the repository files into the container
COPY . .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# Create a symlink for chromium so the AI agent finds it
RUN ln -s /usr/bin/chromium /usr/bin/google-chrome

# Expose the MCP server port
EXPOSE 8888

# Command to run the server
CMD ["python3", "hexstrike_server.py", "--port", "8888"]