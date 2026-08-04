#!/usr/bin/env bash
# VPS paths for full forensics modules (source before runs on server)
# Usage: source scripts/forensics-env-vps.sh

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HEXSTRIKE_ROOT="$(cd "${_SCRIPT_DIR}/.." && pwd)"
export HEXSTRIKE_ROOT

DRAINER_INTEL="${DRAINER_INTEL:-/opt/drainer-intel}"

export HEXSTRIKE_MODE="${HEXSTRIKE_MODE:-forensics}"

export TRX_DRAINER_REPO="${TRX_DRAINER_REPO:-${DRAINER_INTEL}/TRX-Drainer-Tool}"
export EVM_DRAINER_REPO="${EVM_DRAINER_REPO:-${DRAINER_INTEL}/evm-drainer}"
export APETERMINAL_REPO="${APETERMINAL_REPO:-${DRAINER_INTEL}/apeterminal-main}"
export SOLANA_DRAINER_REPO="${SOLANA_DRAINER_REPO:-${DRAINER_INTEL}/Solana-Drainer-Tool}"
export VANILLA_INTEL_DIR="${VANILLA_INTEL_DIR:-${HEXSTRIKE_ROOT}/artifacts/recon/vanilla-drainer-intel}"

_default_create2="${APETERMINAL_REPO}:${EVM_DRAINER_REPO}:${HEXSTRIKE_ROOT}/artifacts"
export CREATE2_SCAN_ROOTS="${CREATE2_SCAN_ROOTS:-${_default_create2}}"

export FORENSICS_OUT="${FORENSICS_OUT:-${HEXSTRIKE_ROOT}/artifacts/forensics}"
export WALLETS_FILE="${WALLETS_FILE:-scripts/sandbox/field-targets-5.json}"

_repo_or_intel() {
  local var="$1" path="$2" intel="$3"
  if [[ ! -d "$path" && -d "${HEXSTRIKE_ROOT}/${intel}" ]]; then
    export "$var=${HEXSTRIKE_ROOT}/${intel}"
  fi
}

_repo_or_intel TRX_DRAINER_REPO "$TRX_DRAINER_REPO" "artifacts/intel/TRX-Drainer-Tool"
_repo_or_intel EVM_DRAINER_REPO "$EVM_DRAINER_REPO" "artifacts/intel/evm-drainer"
_repo_or_intel APETERMINAL_REPO "$APETERMINAL_REPO" "artifacts/intel/apeterminal-main"
_repo_or_intel SOLANA_DRAINER_REPO "$SOLANA_DRAINER_REPO" "artifacts/intel/Solana-Drainer-Tool"
