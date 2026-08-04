#!/usr/bin/env python3
"""Agent-OSINT-03: Shodan + passive OSINT by country (KZ / RU / …).

Read-only defensive IR — exposed Geth :8545, Jenkins, crypto RPC.
Set COUNTRY=RU or COUNTRY=KZ (default KZ). Requires SHODAN_API_KEY for live search.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from crypto_rpc_orchestrator import probe_node, score_node  # noqa: E402

COUNTRY_PROFILES: dict[str, dict[str, Any]] = {
    "KZ": {
        "name": "Kazakhstan",
        "tld": "kz",
        "asn_seeds": ["AS9198", "AS48503", "AS21299", "AS35104", "AS207704", "AS200590"],
        "org_queries": ['org:"PS Internet"', 'org:"Kar-Tel"'],
        "neighbor_countries": {"KZ", "RU", "KG", "UZ"},
        "output": "artifacts/shodan-kz-report.json",
        "task": "shodan-kz-scan",
    },
    "RU": {
        "name": "Russia",
        "tld": "ru",
        "asn_seeds": ["AS200350", "AS49505", "AS8359", "AS12389", "AS51659", "AS197695", "AS60476"],
        "org_queries": ['org:"Yandex"', 'org:"Selectel"', 'org:"Beget"'],
        "neighbor_countries": {"RU", "BY", "KZ", "UA"},
        "known_ips": ["51.250.97.223"],  # Yandex Jenkins — case infra
        "output": "artifacts/shodan-ru-report.json",
        "task": "shodan-ru-scan",
    },
}


def build_queries(country: str, org_queries: list[str]) -> list[str]:
    cc = country.upper()
    base = [
        f'country:"{cc}" port:8545',
        f'country:"{cc}" "Geth"',
        f'country:"{cc}" port:8545 "personal"',
        f'country:"{cc}" port:8545 ethereum',
        f'country:"{cc}" jenkins port:8080',
        f'country:"{cc}" port:8545 "txpool"',
        f'country:"{cc}" port:8545 "web3"',
        f'country:"{cc}" "JSON-RPC"',
        f'country:"{cc}" port:443 ssl ethereum',
        f'country:"{cc}" port:8546',
        f'country:"{cc}" port:8545 "eth_accounts"',
        f'country:"{cc}" "signing" ethereum',
    ]
    return base + [f'country:"{cc}" {q}' for q in org_queries]


def http_json(url: str, timeout: float = 12.0) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "HexStrike-OSINT/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def shodan_search(api_key: str, query: str, limit: int = 50) -> dict[str, Any]:
    params = urllib.parse.urlencode({"key": api_key, "query": query, "minify": "true"})
    url = f"https://api.shodan.io/shodan/host/search?{params}"
    try:
        data = http_json(url)
        matches = data.get("matches") or []
        return {"query": query, "total": data.get("total", 0), "matches": matches[:limit], "error": None}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:300]
        return {"query": query, "total": 0, "matches": [], "error": f"HTTP {exc.code}: {body}"}
    except Exception as exc:  # noqa: BLE001
        return {"query": query, "total": 0, "matches": [], "error": str(exc)}


def internetdb(ip: str) -> dict[str, Any]:
    try:
        return http_json(f"https://internetdb.shodan.io/{ip}", timeout=8.0)
    except Exception as exc:  # noqa: BLE001
        return {"ip": ip, "error": str(exc)}


def ripe_country_asns(country: str) -> list[str]:
    try:
        data = http_json(f"https://stat.ripe.net/data/country-resource-list/data.json?resource={country}")
        asns = data.get("data", {}).get("resources", {}).get("asn", []) or []
        return [f"AS{a}" if not str(a).upper().startswith("AS") else str(a).upper() for a in asns[:30]]
    except Exception:
        return []


def ripe_announced_ips(asn: str, max_ips: int = 5) -> list[str]:
    ips: list[str] = []
    try:
        asn_num = asn.upper().replace("AS", "")
        data = http_json(
            f"https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn_num}",
            timeout=10,
        )
        for entry in (data.get("data", {}).get("prefixes", []) or [])[:8]:
            prefix = entry.get("prefix", "")
            if not prefix or "/" not in prefix:
                continue
            base_ip = prefix.split("/")[0]
            if ":" not in base_ip and base_ip not in ips:
                ips.append(base_ip)
            if len(ips) >= max_ips:
                break
    except Exception:
        pass
    return ips


def crtsh_domains(tld: str, limit: int = 30) -> list[str]:
    domains: list[str] = []
    try:
        url = f"https://crt.sh/?q=%.{tld}&output=json"
        req = urllib.request.Request(url, headers={"User-Agent": "HexStrike-OSINT/1.0"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            rows = json.loads(resp.read().decode())
        seen: set[str] = set()
        for row in rows:
            for field in ("common_name", "name_value"):
                for part in (row.get(field) or "").split("\n"):
                    d = part.strip().lower().lstrip("*.")
                    if d.endswith(f".{tld}") and d not in seen and " " not in d:
                        seen.add(d)
                        domains.append(d)
                        if len(domains) >= limit:
                            return domains
    except Exception:
        pass
    return domains


def resolve_a(domain: str) -> list[str]:
    try:
        out = subprocess.check_output(["host", "-t", "A", domain], text=True, timeout=8, stderr=subprocess.DEVNULL)
        return list(dict.fromkeys(re.findall(r"has address (\d+\.\d+\.\d+\.\d+)", out)))
    except Exception:
        try:
            return list({addr[4][0] for addr in socket.getaddrinfo(domain, None, socket.AF_INET)})
        except Exception:
            return []


def ipinfo(ip: str) -> dict[str, Any]:
    try:
        return http_json(f"https://ipinfo.io/{ip}/json", timeout=8.0)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def extract_shodan_ips(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    targets: list[dict[str, Any]] = []
    for block in results:
        for m in block.get("matches") or []:
            ip = m.get("ip_str") or m.get("ip")
            if not ip or ip in seen:
                continue
            seen.add(ip)
            targets.append({
                "ip": ip,
                "ports": m.get("ports") or [],
                "org": m.get("org"),
                "hostnames": m.get("hostnames") or [],
                "product": m.get("product"),
                "vulns": list((m.get("vulns") or {}).keys()) if isinstance(m.get("vulns"), dict) else (m.get("vulns") or []),
                "tags": m.get("tags") or [],
                "source": "shodan_search",
                "query": block.get("query"),
            })
    return targets


def classify_risk(target: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    ports = set(target.get("ports") or [])
    if 8545 in ports:
        flags.append("ETH_RPC_8545")
    if 8080 in ports:
        flags.append("JENKINS_8080")
    if 22 in ports:
        flags.append("SSH_22")
    vulns = target.get("vulns") or []
    if vulns:
        flags.append(f"CVE_COUNT_{len(vulns)}")
    for f in (target.get("geth_probe") or {}).get("risk_flags") or []:
        flags.append(f)
    if any("PERSONAL" in f or "CRITICAL" in f for f in flags):
        flags.append("HIGH_RISK_SIGNING_EXPOSURE")
    return flags


def probe_geth_targets(targets: list[dict[str, Any]], country: str, timeout: float = 6.0) -> None:
    for t in targets:
        ports = set(t.get("ports") or [])
        if 8545 not in ports and "ETH_RPC_8545" not in t.get("risk_flags", []):
            continue
        result = probe_node(
            {"ip": t["ip"], "org": t.get("org") or "unknown", "country": t.get("country") or country},
            port=8545,
            timeout=timeout,
        )
        t["geth_probe"] = {
            "reachable": result.reachable,
            "client_version": result.client_version,
            "chain_id": result.chain_id,
            "risk_flags": result.risk_flags,
            "rpc_modules": result.rpc_modules,
            "score": score_node(result),
        }


def enrich_ip(candidate_ips: dict[str, dict[str, Any]], ip: str, source: str, **extra: Any) -> None:
    idb = internetdb(ip)
    geo = ipinfo(ip)
    entry = {
        "ip": ip,
        "ports": idb.get("ports") or [],
        "org": geo.get("org"),
        "country": geo.get("country"),
        "hostnames": idb.get("hostnames") or [],
        "vulns": idb.get("vulns") or [],
        "tags": idb.get("tags") or [],
        "source": source,
        **extra,
    }
    if ip in candidate_ips:
        candidate_ips[ip].update({k: v for k, v in entry.items() if v})
    else:
        candidate_ips[ip] = entry


def run_scan(country: str) -> dict[str, Any]:
    profile = COUNTRY_PROFILES[country]
    api_key = os.environ.get("SHODAN_API_KEY", "").strip()
    queries = build_queries(country, profile["org_queries"])
    out_path = Path(os.environ.get("OUTPUT", str(ROOT / profile["output"])))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent": "Agent-OSINT-03",
        "task": profile["task"],
        "mode": "read-only_passive",
        "country": country,
        "country_name": profile["name"],
        "shodan_api": bool(api_key),
        "queries": queries,
        "queries_planned": len(queries),
        "request_log": [],
        "targets": [],
        "high_risk": [],
        "notes": [],
    }

    candidate_ips: dict[str, dict[str, Any]] = {}
    shodan_blocks: list[dict[str, Any]] = []

    # Phase A: 12+ Shodan query slots
    for i, q in enumerate(queries, 1):
        if api_key:
            block = shodan_search(api_key, q)
            report["request_log"].append({
                "n": i, "type": "shodan_search", "query": q,
                "total": block.get("total"), "returned": len(block.get("matches") or []),
                "error": block.get("error"),
            })
            report["notes"].append(f"Shodan [{i}/{len(queries)}] '{q}': total={block.get('total')}")
        else:
            block = {"query": q, "total": 0, "matches": [], "error": "SHODAN_API_KEY missing"}
            report["request_log"].append({
                "n": i, "type": "shodan_search", "query": q, "total": 0, "returned": 0,
                "error": "SHODAN_API_KEY missing",
            })
        shodan_blocks.append(block)

    if not api_key:
        report["notes"].append(f"{len(queries)} Shodan slots logged (no API key). Passive batch running.")

    for t in extract_shodan_ips(shodan_blocks):
        candidate_ips[t["ip"]] = t

    # Phase B: known case IPs
    req_n = len(queries)
    for ip in profile.get("known_ips", []):
        req_n += 1
        enrich_ip(candidate_ips, ip, "known_case_ip")
        report["request_log"].append({"n": req_n, "type": "known_case_ip", "ip": ip})

    # Phase C: RIPEstat + InternetDB
    asns = ripe_country_asns(country) or profile["asn_seeds"]
    report["asns_sampled"] = asns[:15]
    req_n += 1
    report["request_log"].append({"n": req_n, "type": "ripestat_country", "resource": country, "asns": len(asns)})

    allowed = profile["neighbor_countries"]
    for asn in (profile["asn_seeds"] + asns)[:12]:
        req_n += 1
        prefix_ips = ripe_announced_ips(asn, max_ips=3)
        report["request_log"].append({"n": req_n, "type": "ripestat_prefixes", "asn": asn, "ips": len(prefix_ips)})
        for ip in prefix_ips:
            if ip in candidate_ips:
                continue
            req_n += 1
            enrich_ip(candidate_ips, ip, "ripe_internetdb", asn=asn)
            geo_country = candidate_ips[ip].get("country")
            report["request_log"].append({
                "n": req_n, "type": "internetdb+ipinfo", "ip": ip,
                "ports": candidate_ips[ip].get("ports"), "country": geo_country,
            })
            if geo_country not in allowed and geo_country is not None:
                del candidate_ips[ip]

    # Phase D: crt.sh TLD domains
    domains = crtsh_domains(profile["tld"], limit=20)
    report["domains_sampled"] = len(domains)
    for domain in domains[:15]:
        for ip in resolve_a(domain):
            req_n += 1
            if ip not in candidate_ips:
                enrich_ip(candidate_ips, ip, "crtsh_resolve", domains=[domain])
            else:
                candidate_ips[ip].setdefault("domains", []).append(domain)
            report["request_log"].append({"n": req_n, "type": "crtsh_resolve", "domain": domain, "ip": ip})

    targets = list(candidate_ips.values())
    for t in targets:
        t["risk_flags"] = classify_risk(t)
    probe_geth_targets(targets, country)
    for t in targets:
        t["risk_flags"] = classify_risk(t)
        t["risk_score"] = len(t["risk_flags"]) + (t.get("geth_probe") or {}).get("score", 0)

    targets.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
    report["targets"] = targets
    report["total_candidates"] = len(targets)
    report["geth_8545_candidates"] = sum(
        1 for t in targets if 8545 in (t.get("ports") or []) or (t.get("geth_probe") or {}).get("reachable")
    )
    report["high_risk"] = [
        {
            "ip": t["ip"], "ports": t.get("ports"), "risk_flags": t.get("risk_flags"),
            "org": t.get("org"), "source": t.get("source"), "geth_probe": t.get("geth_probe"),
        }
        for t in targets
        if any(f in (t.get("risk_flags") or []) for f in ("HIGH_RISK_SIGNING_EXPOSURE", "ETH_RPC_8545", "JENKINS_8080"))
        or (t.get("geth_probe") or {}).get("score", 0) >= 3
    ][:30]

    report["shodan_query_results"] = [
        {"query": b["query"], "total": b.get("total"), "error": b.get("error"), "returned": len(b.get("matches") or [])}
        for b in shodan_blocks
    ]
    report["requests_executed"] = len(report["request_log"])
    report["shodan_queries_executed"] = len(queries)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "output": str(out_path),
        "country": country,
        "total_candidates": report["total_candidates"],
        "high_risk_count": len(report["high_risk"]),
        "geth_8545": report["geth_8545_candidates"],
        "shodan_api": report["shodan_api"],
        "shodan_queries_executed": report["shodan_queries_executed"],
        "requests_executed": report["requests_executed"],
        "report": report,
    }


def main() -> int:
    country = os.environ.get("COUNTRY", os.environ.get("SHODAN_COUNTRY", "KZ")).upper()
    if country not in COUNTRY_PROFILES:
        print(json.dumps({"success": False, "error": f"Unknown COUNTRY={country}", "supported": list(COUNTRY_PROFILES)}))
        return 1
    result = run_scan(country)
    summary = {k: v for k, v in result.items() if k != "report"}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
