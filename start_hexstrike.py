#!/usr/bin/env python3
"""
HexStrike AI Startup Wrapper
============================
Auto-starts hexstrike_server.py if not running, then launches hexstrike_mcp.py.
Used as the MCP command in mcp.json so Kiro always has a running server.
"""

import os
import sys
import subprocess
import time
import requests
import argparse

SERVER_URL = "http://127.0.0.1:8888"
SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "hexstrike_server.py")
MCP_SCRIPT = os.path.join(os.path.dirname(__file__), "hexstrike_mcp.py")
STARTUP_TIMEOUT = 60  # seconds to wait for server to come up


def is_server_running(url: str = SERVER_URL, timeout: int = 2) -> bool:
    try:
        r = requests.get(f"{url}/health", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def kill_stale_server(port: int = 8888):
    """Kill any existing process listening on the server port."""
    import subprocess, sys
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                pid = int(parts[-1])
                if pid and pid != os.getpid():
                    try:
                        subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                                       capture_output=True, timeout=5)
                    except Exception:
                        pass
    except Exception:
        pass


def start_server():
    """Start hexstrike_server.py in background."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    proc = subprocess.Popen(
        [sys.executable, SERVER_SCRIPT],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    return proc


def wait_for_server(timeout: int = STARTUP_TIMEOUT) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_server_running():
            return True
        time.sleep(0.5)
    return False


def main():
    parser = argparse.ArgumentParser(description="HexStrike AI Startup Wrapper")
    parser.add_argument("--server", default=SERVER_URL)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--debug", action="store_true")
    args, extra = parser.parse_known_args()

    # Override server URL if passed
    server_url = args.server

    # 1. Check if server already up
    if not is_server_running(server_url):
        sys.stderr.write("[hexstrike-wrapper] Server not running, starting hexstrike_server.py...\n")
        kill_stale_server()  # clean up any zombie instances on port first
        start_server()
        if not wait_for_server():
            sys.stderr.write("[hexstrike-wrapper] ERROR: Server failed to start within timeout!\n")
            sys.exit(1)
        sys.stderr.write("[hexstrike-wrapper] Server is up.\n")
    else:
        sys.stderr.write("[hexstrike-wrapper] Server already running.\n")

    # 2. Launch MCP client — inherit stdin/stdout/stderr so Kiro can talk to it via stdio
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    mcp_args = [sys.executable, MCP_SCRIPT, "--server", server_url]
    if args.timeout:
        mcp_args += ["--timeout", str(args.timeout)]
    if args.debug:
        mcp_args += ["--debug"]

    # Use subprocess.run (not os.execve) — on Windows, os.execve breaks stdio inheritance
    result = subprocess.run(mcp_args, env=env)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
