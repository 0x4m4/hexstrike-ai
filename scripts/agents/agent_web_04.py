#!/usr/bin/env python3
"""Agent-Web-04: stealth recon — HTTP headers/fingerprint only (LotL, no nmap)."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DEFAULT_IN = os.path.join(ROOT, "artifacts/infra-targets.json")
DEFAULT_OUT = os.path.join(ROOT, "artifacts/web-recon.json")


def probe_url(url: str) -> dict:
    result = {"url": url}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HexStrike-Web04/1.0 (passive)"})
        with urllib.request.urlopen(req, timeout=12) as r:
            body = r.read(2048).decode("utf-8", errors="replace")
            result.update(
                {
                    "status": r.status,
                    "headers": dict(r.headers),
                    "body_snippet": body[:500],
                }
            )
    except Exception as e:
        result["error"] = str(e)
    return result


def main() -> int:
    in_path = os.environ.get("INPUT", DEFAULT_IN)
    out_path = os.environ.get("OUTPUT", DEFAULT_OUT)

    targets: list[str] = []
    port_map: dict[str, list[int]] = {}
    if os.path.isfile(in_path):
        with open(in_path) as f:
            data = json.load(f)
        for item in data.get("infra_targets", []):
            ip = item.get("ip")
            if ip:
                port_map[ip] = item.get("ports") or [8080]
                for port in port_map[ip]:
                    scheme = "https" if port == 443 else "http"
                    p = "" if port in (80, 443) else f":{port}"
                    targets.append(f"{scheme}://{ip}{p}/")
    else:
        targets = ["http://51.250.97.223:8080/"]

    seen = set()
    probes = []
    for url in targets:
        if url in seen:
            continue
        seen.add(url)
        probes.append(probe_url(url))

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent": "Agent-Web-04",
        "task": "stealth-recon",
        "mode": "lotl_passive",
        "constraints": ["no-nmap", "no-exploit", "no-bruteforce"],
        "input": in_path if os.path.isfile(in_path) else None,
        "probes": probes,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({"success": True, "output": out_path, "probes": len(probes)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
