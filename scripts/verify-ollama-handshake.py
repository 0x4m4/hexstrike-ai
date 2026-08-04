#!/usr/bin/env python3
"""Verify Ollama model availability and HexStrike API handshake."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
HEXSTRIKE_URL = os.getenv("HEXSTRIKE_URL", "http://127.0.0.1:8888")
MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:1.5b")


def _http_json(method: str, url: str, payload: dict | None = None, timeout: int = 20) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}


def check_ollama() -> dict:
    result = {"ok": False, "model": MODEL, "details": {}}
    try:
        tags = _http_json("GET", f"{OLLAMA_URL}/api/tags")
        models = [item.get("name", "") for item in tags.get("models", [])]
        result["details"]["models"] = models
        if not any(MODEL in name for name in models):
            result["details"]["error"] = f"Model '{MODEL}' not found"
            return result

        response = _http_json(
            "POST",
            f"{OLLAMA_URL}/api/generate",
            {
                "model": MODEL,
                "prompt": "Reply with one word: READY",
                "stream": False,
                "options": {"num_predict": 8},
            },
            timeout=60,
        )
        result["details"]["sample"] = (response.get("response") or "").strip()[:120]
        result["ok"] = bool(result["details"]["sample"])
        return result
    except urllib.error.URLError as exc:
        result["details"]["error"] = str(exc)
        return result


def check_hexstrike() -> dict:
    result = {"ok": False, "endpoint": f"{HEXSTRIKE_URL}/health"}
    try:
        health = _http_json("GET", result["endpoint"], timeout=10)
        result["ok"] = health.get("status") == "healthy"
        result["details"] = {
            "status": health.get("status"),
            "version": health.get("version"),
            "tools_available": health.get("total_tools_available"),
        }
        return result
    except urllib.error.URLError as exc:
        result["details"] = {"error": str(exc)}
        return result


def main() -> int:
    report = {
        "ollama": check_ollama(),
        "hexstrike": check_hexstrike(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report["hexstrike"]["ok"]:
        return 0
    if not report["ollama"]["ok"]:
        print("WARN: Ollama handshake failed or unavailable; continuing in degraded mode", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
