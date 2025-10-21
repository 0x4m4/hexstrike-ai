#!/bin/bash
# ==============================================================================
# File: build-docker-image.sh
# Description: Script to build the Docker image for HexStrike AI and capture logs for development purpose.
set -Eeuo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &>/dev/null && pwd )"
cd "$SCRIPT_DIR/.."

IMAGE_TAG="hexstrike-ai:v6.0"
LOG_FILE="${BUILD_LOG:-logs/build.log}"

echo "[+] Building image with docker | log: ${LOG_FILE}" >&2

# Enable BuildKit if Docker supports it; harmless if ignored.
export DOCKER_BUILDKIT=1

sudo docker build \
  --tag "${IMAGE_TAG}" \
  --file docker/Dockerfile . \
  2>&1 | tee "${LOG_FILE}"
