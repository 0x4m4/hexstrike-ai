#!/bin/bash
# OSINT Tools Installation Wrapper

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3.8+"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "osint-env" ] && [ -f "requirements.txt" ]; then
    echo "Installing Python dependencies..."
    python3 -m venv osint-env
    ./osint-env/bin/pip install -r requirements.txt
fi

# Run Python installer
if [ -d "osint-env" ]; then
    ./osint-env/bin/python install.py "$@"
else
    python3 install.py "$@"
fi