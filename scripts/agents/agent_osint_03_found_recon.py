#!/usr/bin/env python3
"""Agent-OSINT-03: passive recon on Shodan-found targets (RU/KZ + case infra)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from crypto_rpc_orchestrator import probe_node, score_node  # noqa: E402

DEFAULT_OUT = ROOT / "artifacts" / "found-targets-recon.json"
INFRA_OUT = ROOT / "artifacts" / "found-targets-infra.json"
HOT_WALLET = os.environ.get("TARGET_WALLET", "0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA")

SEEDS = {
    "hot_wallet": HOT_WALLET,
    "authority": "0x730ea0231808f42a20f8921ba7fbc788226768f5",
    "primary_sink_hub": "0xb80a582fa430645a043bb4f6135321ee01005fef",
}

# Always include case-linked infra
CASE_IPS = ["51.250.97.223", "51.222.42.220"]


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def collect_found_targets() -> list[dict]:
    seen: set[str] = set()
    targets: list[dict] = []

    def add(t: dict) -> None:
        ip = t.get("ip")
        if not ip or ip in seen:
            return
        seen.add(ip)
        targets.append(t)

    for ip in CASE_IPS:
        add({"ip": ip, "source": "case_infra", "priority": 1})

    for report_name in ("shodan-ru-report.json", "shodan-kz-report.json"):
        report = load_json(ROOT / "artifacts" / report_name)
        for t in report.get("high_risk") or []:
            add({**t, "source": f"high_risk:{report_name}", "priority": 1})
        for t in sorted(report.get("targets") or [], key=lambda x: x.get("risk_score", 0), reverse=True)[:8]:
            if t.get("risk_score", 0) > 0 or 8545 in (t.get("ports") or []) or 8080 in (t.get("ports") or []):
                add({**t, "source": f"ranked:{report_name}", "priority": 2})

    return targets


def ipinfo(ip: str) -> dict:
    try:
        with urllib.request.urlopen(f"https://ipinfo.io/{ip}/json", timeout=10) as r:
            return json.load(r)
    except Exception as e:
        return {"error": str(e)}


def internetdb(ip: str) -> dict:
    try:
        with urllib.request.urlopen(f"https://internetdb.shodan.io/{ip}", timeout=8) as r:
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


def whois_excerpt(ip: str, limit: int = 1500) -> str:
    try:
        out = subprocess.check_output(["whois", ip], text=True, stderr=subprocess.DEVNULL, timeout=15)
        return out[:limit]
    except Exception as e:
        return f"whois error: {e}"


def http_probe(url: str, method: str = "GET") -> dict:
    result = {"url": url, "method": method}
    try:
        req = urllib.request.Request(url, method=method, headers={"User-Agent": "HexStrike-FoundRecon/1.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            body = r.read(2048).decode("utf-8", errors="replace")
            result.update({"status": r.status, "headers": dict(r.headers), "body_snippet": body[:400]})
    except Exception as e:
        result["error"] = str(e)
    return result


def recon_target(target: dict) -> dict:
    ip = target["ip"]
    ports = set(target.get("ports") or [])
    idb = internetdb(ip)
    ports.update(idb.get("ports") or [])

    entry = {
        "ip": ip,
        "source": target.get("source"),
        "priority": target.get("priority", 3),
        "risk_flags": target.get("risk_flags") or [],
        "ports_known": sorted(ports),
        "ptr": ptr(ip),
        "ipinfo": ipinfo(ip),
        "internetdb": {k: idb.get(k) for k in ("ports", "vulns", "hostnames", "tags") if k in idb},
        "whois_excerpt": whois_excerpt(ip),
        "probes": {},
    }

    if 8080 in ports or "JENKINS_8080" in entry["risk_flags"] or ip == "51.250.97.223":
        entry["probes"]["jenkins_8080"] = {
            "head": http_probe(f"http://{ip}:8080/", "HEAD"),
            "get": http_probe(f"http://{ip}:8080/"),
        }

    if 8545 in ports or ip == "51.222.42.220":
        geo = entry["ipinfo"]
        probe = probe_node(
            {"ip": ip, "org": geo.get("org", "unknown"), "country": geo.get("country", "??")},
            port=8545,
            timeout=8.0,
        )
        entry["probes"]["geth_8545"] = {
            "reachable": probe.reachable,
            "client_version": probe.client_version,
            "chain_id": probe.chain_id,
            "risk_flags": probe.risk_flags,
            "rpc_modules": probe.rpc_modules,
            "score": score_node(probe),
        }

    if ip == "51.250.97.223":
        entry["wallet_correlation"] = {
            "hot_wallet": HOT_WALLET,
            "role": "signing_bot_jenkins_infra",
            "provider": "Yandex.Cloud",
            "lea_note": "Tenant identity via legal request to Yandex Cloud LLC",
        }

    return entry


def main() -> int:
    out_path = Path(os.environ.get("OUTPUT", str(DEFAULT_OUT)))
    infra_path = Path(os.environ.get("INFRA_OUTPUT", str(INFRA_OUT)))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    found = collect_found_targets()
    reconned = [recon_target(t) for t in found]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent": "Agent-OSINT-03",
        "task": "found-targets-recon",
        "mode": "read-only_passive",
        "seed_addresses": SEEDS,
        "targets_scanned": len(reconned),
        "targets": reconned,
        "summary": {
            "jenkins_exposed": sum(1 for t in reconned if t.get("probes", {}).get("jenkins_8080")),
            "geth_reachable": sum(1 for t in reconned if (t.get("probes", {}).get("geth_8545") or {}).get("reachable")),
            "with_cves": sum(1 for t in reconned if (t.get("internetdb", {}).get("vulns"))),
        },
    }

    infra = {
        "generated_at": report["generated_at"],
        "agent": "Agent-OSINT-03",
        "task": "found-targets-infra",
        "seed_addresses": SEEDS,
        "infra_targets": [
            {
                "ip": t["ip"],
                "ports": t.get("ports_known"),
                "ptr": t.get("ptr"),
                "ipinfo": t.get("ipinfo"),
                "risk_flags": t.get("risk_flags"),
                "source": t.get("source"),
            }
            for t in reconned
        ],
    }

    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    infra_path.write_text(json.dumps(infra, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "success": True,
        "output": str(out_path),
        "infra": str(infra_path),
        "targets": len(reconned),
        "summary": report["summary"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
