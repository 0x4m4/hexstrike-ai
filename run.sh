#!/bin/bash
# Script to run HexStrike AI Server inside WSL
cd "$(dirname "$0")"
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi
python3 hexstrike_server.py
