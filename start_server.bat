@echo off
:: HexStrike AI - Windows Server Startup Script
:: Launches the Flask API server with correct Unicode settings for Windows.
:: Run this before starting Claude Code or any MCP client that uses HexStrike.

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

:: Resolve paths relative to this script's location
set SCRIPT_DIR=%~dp0
set VENV_PYTHON=%SCRIPT_DIR%hexstrike-env\Scripts\python.exe
set SERVER=%SCRIPT_DIR%hexstrike_server.py

echo Starting HexStrike AI Server on port 8888...
"%VENV_PYTHON%" -X utf8 "%SERVER%" %*
