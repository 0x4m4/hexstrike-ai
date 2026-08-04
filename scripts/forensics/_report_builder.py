#!/usr/bin/env python3
"""Shared forensics report builder — attack_chain, network_iocs, on-chain enrichment."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

DESKTOP = Path.home() / "Desktop" / "on-chain-forensics" / "artifacts"
FORENSICS_OUT = ROOT / "artifacts" / "forensics"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_instruction(name: str) -> str:
    path = ROOT / "src" / "hexstrike" / "instructions" / name
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def load_ioc(filename: str) -> dict[str, Any]:
    path = ROOT / "artifacts" / filename
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def get_orchestrator():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from hexstrike_orchestrator import HexStrikeOrchestrator  # noqa: WPS433

    return HexStrikeOrchestrator()


def enrich_addresses(addresses: list[str], *, limit: int = 8) -> list[dict[str, Any]]:
    if not addresses:
        return []
    try:
        orch = get_orchestrator()
    except Exception as exc:  # noqa: BLE001
        return [{"error": str(exc), "addresses_requested": addresses[:limit]}]

    results: list[dict[str, Any]] = []
    for addr in addresses[:limit]:
        if not addr.startswith("0x") or len(addr) != 42:
            continue
        try:
            results.append(orch.run_analyze(addr))
        except Exception as exc:  # noqa: BLE001
            results.append({"address": addr, "error": str(exc)})
    return results


def enrich_hosts(hosts: list[str]) -> dict[str, Any]:
    enriched: dict[str, Any] = {"hosts": hosts, "dns": [], "http": []}
    if not hosts:
        return enriched
    import socket
    from urllib.request import Request, urlopen

    for host in hosts[:8]:
        entry: dict[str, Any] = {"host": host}
        try:
            entry["resolved_ips"] = list({ai[4][0] for ai in socket.getaddrinfo(host, None)})
        except OSError as exc:
            entry["dns_error"] = str(exc)
        enriched["dns"].append(entry)
        for scheme in ("https", "http"):
            try:
                req = Request(f"{scheme}://{host}/", headers={"User-Agent": "HexStrike-Forensics/1.0"})
                with urlopen(req, timeout=5) as resp:
                    enriched["http"].append({
                        "url": f"{scheme}://{host}/",
                        "status": resp.status,
                        "server": resp.headers.get("Server"),
                    })
                    break
            except Exception:
                continue
    return enriched


def build_attack_chain(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"step": i + 1, **s} for i, s in enumerate(steps)]


def publish_complete(bus_source: str, payload: dict[str, Any]) -> None:
    try:
        from hexstrike.bus.context_bus import ContextBus  # noqa: WPS433

        bus = ContextBus()
        skill_name = bus_source.replace("_analyzer", "")

        def _log(event) -> None:
            print(f"[bus] {event.topic} ← {event.source}")

        bus.subscribe("*", _log)
        bus.publish(f"skill.{skill_name}.complete", payload, source=bus_source)
    except Exception:
        pass


def finalize_report(
    *,
    module: str,
    instruction_file: str,
    ioc: dict[str, Any],
    report_builder: Callable[[dict[str, Any]], dict[str, Any]],
    bus_source: str,
    out_name: str,
    onchain_addresses: list[str] | None = None,
    network_hosts: list[str] | None = None,
) -> dict[str, Any]:
    prompt = load_instruction(instruction_file)
    body = report_builder(ioc)
    body.setdefault("generated_at", utc_now())

    hosts = network_hosts or []
    c2 = ioc.get("network_iocs", {}).get("c2_host")
    if c2:
        hosts = list(dict.fromkeys([c2, *hosts]))
    hosts.extend(ioc.get("network_iocs", {}).get("hosts", []))
    hosts = list(dict.fromkeys(h for h in hosts if h))[:10]

    addrs = onchain_addresses or []
    addrs.extend(ioc.get("onchain_iocs", {}).get("addresses", []))
    addrs.extend(ioc.get("onchain_iocs", {}).get("sink_addresses", []))
    addrs.extend(ioc.get("claim_contracts_correlated", []))
    addrs.extend(ioc.get("spenders_correlated", []))
    fee = ioc.get("onchain_iocs", {}).get("fee_wallet")
    if fee:
        addrs.insert(0, fee)
    addrs = list(dict.fromkeys(a.lower() if a.startswith("0x") else a for a in addrs if a))[:12]

    if hosts:
        body["network_iocs_enriched"] = enrich_hosts(hosts)
    if addrs:
        body["onchain_analysis"] = enrich_addresses(addrs)

    envelope = {
        "instruction_loaded": instruction_file,
        "instruction_bytes": len(prompt),
        "report": body,
        "generated_at": utc_now(),
    }

    FORENSICS_OUT.mkdir(parents=True, exist_ok=True)
    out_path = FORENSICS_OUT / out_name
    text = json.dumps(envelope, indent=2, ensure_ascii=False) + "\n"
    out_path.write_text(text, encoding="utf-8")
    try:
        DESKTOP.mkdir(parents=True, exist_ok=True)
        (DESKTOP / out_name).write_text(text, encoding="utf-8")
    except OSError:
        pass

    publish_complete(bus_source, envelope)
    return envelope
