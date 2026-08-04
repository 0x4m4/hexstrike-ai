"""Shared API key auth helpers for HexStrike clients and server."""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
API_KEY_HEADER = "X-API-KEY"


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs from .env into os.environ (no overwrite)."""
    env_file = path or ENV_PATH
    if not env_file.is_file():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_api_key() -> str:
    load_dotenv()
    return os.environ.get("HEXSTRIKE_API_KEY", "").strip()


def api_headers(api_key: str | None = None) -> dict[str, str]:
    key = (api_key or get_api_key()).strip()
    if not key:
        return {}
    return {API_KEY_HEADER: key}


def validate_api_key(provided: str | None, expected: str | None = None) -> bool:
    expected_key = (expected or get_api_key()).strip()
    if not expected_key:
        return False
    if not provided:
        return False
    return secrets.compare_digest(provided.strip(), expected_key)


def hexstrike_handshake(server_url: str, api_key: str | None = None, timeout: float = 10.0) -> dict[str, Any]:
    """Verify API access to HexStrike server (GET /api/context/latest)."""
    base = server_url.rstrip("/")
    headers = api_headers(api_key)
    if not headers:
        return {"success": False, "error": "HEXSTRIKE_API_KEY not configured"}

    try:
        resp = requests.get(f"{base}/api/context/latest", headers=headers, timeout=timeout)
        if resp.status_code == 403:
            return {"success": False, "error": "Forbidden — invalid API key", "status": 403}
        resp.raise_for_status()
        data = resp.json()
        return {"success": True, "status": resp.status_code, "data": data}
    except requests.RequestException as exc:
        return {"success": False, "error": str(exc)}
