#!/usr/bin/env bash
# Пути Eva/Mac для полноценных forensics-модулей (source перед прогонами)
# Использование: source scripts/forensics-env-mac.sh

EVA_STORAGE="${EVA_STORAGE:-/Volumes/Eva/mufasaai-storage}"
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_LOCAL_ROOT="$(cd "${_SCRIPT_DIR}/.." && pwd)"

HEXSTRIKE_ROOT="${HEXSTRIKE_ROOT:-${EVA_STORAGE}/hexstrike-ai}"
if [[ ! -d "$HEXSTRIKE_ROOT" ]]; then
  HEXSTRIKE_ROOT="$_LOCAL_ROOT"
fi
export HEXSTRIKE_ROOT

export HEXSTRIKE_MODE="${HEXSTRIKE_MODE:-forensics}"

export TRX_DRAINER_REPO="${TRX_DRAINER_REPO:-${EVA_STORAGE}/TRX-Drainer-Tool}"
export EVM_DRAINER_REPO="${EVM_DRAINER_REPO:-${EVA_STORAGE}/evm-drainer}"
export APETERMINAL_REPO="${APETERMINAL_REPO:-${EVA_STORAGE}/apeterminal-main}"
export SOLANA_DRAINER_REPO="${SOLANA_DRAINER_REPO:-${EVA_STORAGE}/Solana-Drainer-Tool}"
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
# Eva-пути часто отсутствуют на cloud — fallback на artifacts/intel
_repo_or_intel TRX_DRAINER_REPO "$TRX_DRAINER_REPO" "artifacts/intel/TRX-Drainer-Tool"
_repo_or_intel EVM_DRAINER_REPO "$EVM_DRAINER_REPO" "artifacts/intel/evm-drainer"
_repo_or_intel APETERMINAL_REPO "$APETERMINAL_REPO" "artifacts/intel/apeterminal-main"
_repo_or_intel SOLANA_DRAINER_REPO "$SOLANA_DRAINER_REPO" "artifacts/intel/Solana-Drainer-Tool"
