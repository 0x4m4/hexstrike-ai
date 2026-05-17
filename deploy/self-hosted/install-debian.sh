#!/bin/bash
# OSINT Framework - Debian Installation Script
set -e

echo "=== OSINT Framework Installation (Debian) ==="

if [ "$EUID" -ne 0 ]; then 
   echo "Please run as root"
   exit 1
fi

apt update && apt upgrade -y
apt install -y python3 python3-pip git curl nginx

mkdir -p /opt/osint
echo "Debian installation complete - similar to Ubuntu"