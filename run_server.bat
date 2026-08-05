@echo off
:: Windows batch file to run HexStrike AI Server in WSL Kali-Linux
wsl -d kali-linux -e bash -c "cd '/mnt/e/Project/AI PENTEST/hexstrike-ai' && chmod +x run.sh && ./run.sh"
