#!/bin/bash
# OSINT Framework - Ubuntu Installation Script
set -e

echo "=== OSINT Framework Installation (Ubuntu) ==="

if [ "$EUID" -ne 0 ]; then 
   echo "Please run as root"
   exit 1
fi

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3 python3-pip git curl nginx

# Create application directory
mkdir -p /opt/osint
cd /opt/osint

# Copy framework
SOURCE_DIR="/home/phoenix0/Documents/1/hexstrike-ai"
if [ -d "$SOURCE_DIR" ]; then
    cp -r $SOURCE_DIR/osint-framework .
    cp -r $SOURCE_DIR/osint-tools .
fi

# Create virtual environment
cd osint-framework
python3 -m venv osint-env
./osint-env/bin/pip install -r requirements.txt

# Create data directory
mkdir -p /var/lib/osint
chown -R $(whoami):$(whoami) /var/lib/osint 2>/dev/null || true

# Setup systemd services
if [ -d "/home/phoenix0/Documents/1/hexstrike-ai/deploy/self-hosted/systemd" ]; then
    cp /home/phoenix0/Documents/1/hexstrike-ai/deploy/self-hosted/systemd/osint-api.service /etc/systemd/system/ 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true
fi

echo "Installation complete!"
echo "Run: systemctl start osint-api"