#!/usr/bin/env python3
"""
HexStrike AI MCP Launcher
Ensures the hexstrike-server Docker container is running before starting the MCP client.
"""

import os
import sys
import subprocess
import time
import requests

CONTAINER_NAME = "hexstrike-server"
IMAGE_NAME = "hexstrike-ai"
SERVER_PORT = 8888
HEALTH_URL = f"http://127.0.0.1:{SERVER_PORT}/health"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_SCRIPT = os.path.join(SCRIPT_DIR, "hexstrike_mcp.py")
DOCKERFILE_DIR = SCRIPT_DIR

# Parse --server arg if provided, otherwise use default
server_url = f"http://127.0.0.1:{SERVER_PORT}"
for i, arg in enumerate(sys.argv[1:], 1):
    if arg == "--server" and i + 1 < len(sys.argv):
        server_url = sys.argv[i + 1]


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def container_running():
    result = run(["docker", "inspect", "--format", "{{.State.Running}}", CONTAINER_NAME])
    return result.returncode == 0 and result.stdout.strip() == "true"


def container_exists():
    result = run(["docker", "inspect", CONTAINER_NAME])
    return result.returncode == 0


def image_exists():
    result = run(["docker", "image", "inspect", IMAGE_NAME])
    return result.returncode == 0


def build_image():
    sys.stderr.write(f"[hexstrike-launcher] Building Docker image '{IMAGE_NAME}'...\n")
    result = subprocess.run(
        ["docker", "build", "-t", IMAGE_NAME, DOCKERFILE_DIR],
        stderr=sys.stderr
    )
    if result.returncode != 0:
        sys.stderr.write("[hexstrike-launcher] Docker build failed.\n")
        sys.exit(1)


def start_container():
    if container_exists():
        sys.stderr.write(f"[hexstrike-launcher] Starting existing container '{CONTAINER_NAME}'...\n")
        run(["docker", "start", CONTAINER_NAME])
    else:
        sys.stderr.write(f"[hexstrike-launcher] Creating and starting container '{CONTAINER_NAME}'...\n")
        result = run([
            "docker", "run", "-d",
            "--name", CONTAINER_NAME,
            "-p", f"{SERVER_PORT}:{SERVER_PORT}",
            IMAGE_NAME
        ])
        if result.returncode != 0:
            sys.stderr.write(f"[hexstrike-launcher] Failed to start container: {result.stderr}\n")
            sys.exit(1)


def wait_for_server(timeout=60):
    sys.stderr.write(f"[hexstrike-launcher] Waiting for server on {HEALTH_URL}...\n")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(HEALTH_URL, timeout=3)
            if r.status_code == 200:
                sys.stderr.write("[hexstrike-launcher] Server is ready.\n")
                return True
        except Exception:
            pass
        time.sleep(2)
    sys.stderr.write("[hexstrike-launcher] Warning: server did not respond in time, continuing anyway.\n")
    return False


def main():
    # Ensure image exists
    if not image_exists():
        build_image()

    # Ensure container is running
    if not container_running():
        start_container()
        wait_for_server()
    else:
        sys.stderr.write(f"[hexstrike-launcher] Container '{CONTAINER_NAME}' already running.\n")

    # Hand off to the MCP client - replace this process
    python = sys.executable
    args = [python, MCP_SCRIPT, "--server", server_url]
    sys.stderr.write(f"[hexstrike-launcher] Launching MCP client...\n")
    os.execv(python, args)


if __name__ == "__main__":
    main()
