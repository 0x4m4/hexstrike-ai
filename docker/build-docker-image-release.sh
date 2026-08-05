#!/bin/bash
# ==============================================================================
# File: build-docker-image-release.sh
# Description: Script to build the Docker image for HexStrike AI and capture logs with optimizations.

set -Eeuo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR/.."

IMAGE_TAG="hexstrike-ai:v6.0"
LOG_FILE="${BUILD_LOG:-build.log}"

echo "[+] Building image with docker | log: ${LOG_FILE}" >&2

# Enable BuildKit if Docker supports it; harmless if ignored.
export DOCKER_BUILDKIT=1

# Use --no-cache to avoid using cached layers and ensure a consistent build
# Use --pull to always attempt to pull a newer version of the base image if available
sudo docker build \
  --tag "${IMAGE_TAG}" \
  --no-cache --force-rm --squash --pull \
  --file docker/Dockerfile . \
  2>&1 | tee "${LOG_FILE}"
