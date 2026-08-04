#!/usr/bin/env python3
"""Agent-OSINT-03: passive infra-mapping (on-chain seeds → off-chain targets)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DEFAULT_OUT = os.path.join(ROOT, "artifacts/infra-targets.json")

SEEDS = {
    "hot_wallet": "0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA",
    "authority": "0x730ea0231808f42a20f8921ba7fbc788226768f5",
    "primary_sink_hub": "0xb80a582fa430645a043bb4f6135321ee01005fef",
}

KNOWN_IPS = ["51.222.42.220", "51.250.97.223"]


def ipinfo(ip: str) -> dict:
    try:
        with urllib.request.urlopen(f"https://ipinfo.io/{ip}/json", timeout=10) as r:
            return json.load(r)
    except Exception as e:
        return {"error": str(e)}


def ptr(ip: str) -> str | None:
    try:
        out = subprocess.check_output(["host", ip], text=True, stderr=subprocess.DEVNULL, timeout=8)
        if "pointer" in out:
            return out.split("pointer")[-1].strip().rstrip(".")
    except Exception:
        pass
    return None


def jenkins_fingerprint(ip: str) -> dict:
    url = f"http://{ip}:8080/"
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as r:
            headers = {k: v for k, v in r.headers.items()}
        return {"url": url, "status": r.status, "headers": headers}
    except Exception as e:
        return {"url": url, "error": str(e)}


def main() -> int:
    out_path = os.environ.get("OUTPUT", DEFAULT_OUT)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    infra = []
    for ip in KNOWN_IPS:
        entry = {"ip": ip, "ptr": ptr(ip), "ipinfo": ipinfo(ip)}
        if ip == "51.250.97.223":
            entry["jenkins_passive"] = jenkins_fingerprint(ip)
        infra.append(entry)

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent": "Agent-OSINT-03",
        "task": "infra-mapping",
        "mode": "read-only_passive",
        "seed_addresses": SEEDS,
        "infra_targets": infra,
        "github_dorking": "requires GITHUB_TOKEN for API code search",
        "ens_resolve": "n/a on BSC seeds",
    }

    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({"success": True, "output": out_path, "targets": len(infra)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
