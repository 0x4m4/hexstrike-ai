#!/bin/bash
set -Eeuo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &>/dev/null && pwd )"

cd $SCRIPT_DIR

# create host-side folders used by docker-compose bind mounts
mkdir -p \
  "../logs" \
  "../data/trivy" \
  "../data/wpscan" \
  "../data/nuclei-templates" \
  "../data/amass" \
  "../data/msf" \
  "../data/postgres" \
  "../data/workspace" \

[ -f "../logs/hexstrike.log" ] || touch "../logs/hexstrike.log"

sudo docker-compose \
  -f "./docker-compose.yml" \
  up -d --force-recreate
