#!/usr/bin/env python3
"""Build read-only hot wallet dossier — on-chain trace + entity + infra correlation."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

HOT = os.environ.get(
    "TARGET_WALLET",
    "0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA",
).lower()
OUT_JSON = ROOT / "artifacts" / "forensics" / "hot-wallet-dossier.json"
OUT_MD = ROOT / "artifacts" / "forensics" / "hot-wallet-dossier.md"
TARGET_FILE = ROOT / "scripts" / "sandbox" / "hot-wallet-target.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def analyze() -> dict[str, Any]:
    from hexstrike_orchestrator import HexStrikeOrchestrator

    orch = HexStrikeOrchestrator()
    core = orch.run_analyze(HOT)
    trace = orch.forensics.trace_recipient_depth(HOT, depth=3)
    return {"core_analysis": core, "trace_depth_3": trace}


def related_artifacts() -> dict[str, Any]:
    names = [
        "entity-id.json",
        "infra-targets.json",
        "infra-trace-final.json",
        "web-recon.json",
        "multichain-cluster.json",
        "hot-wallet-onchain-graph.json",
    ]
    out: dict[str, Any] = {}
    for name in names:
        data = load_json(ROOT / "artifacts" / name)
        if data is None:
            continue
        blob = json.dumps(data, default=str)
        if HOT[2:] in blob.lower() or HOT in blob.lower():
            out[name] = data
    return out


def build_md(dossier: dict[str, Any]) -> str:
    target = dossier.get("target", {})
    entity = (
        dossier.get("analysis", {})
        .get("core_analysis", {})
        .get("entity", {})
    )
    labels = entity.get("labels") or ["UNIDENTIFIED"]
    trace = dossier.get("analysis", {}).get("trace_depth_3", {})
    nodes = len(trace.get("graph", {}).get("nodes", []))

    lines = [
        "# Hot Wallet Dossier (read-only)",
        "",
        f"**Address:** `{HOT}`",
        f"**Generated:** {dossier.get('generated_at')}",
        f"**Mode:** defensive forensics — no signing, no drain",
        "",
        "## Target profile",
        f"- Risk: **{target.get('labels', {}).get('risk', 'high')}**",
        f"- Multichain USD (snapshot): {target.get('labels', {}).get('multichain_net_usd', 'n/a')}",
        f"- Signing: {target.get('context', {}).get('signing', 'unknown')}",
        "",
        "## Entity",
        f"- Labels: {', '.join(labels)}",
        f"- Sources: {', '.join(entity.get('sources') or []) or 'none'}",
        "",
        "## On-chain trace (depth 3)",
        f"- Graph nodes: {nodes}",
        f"- Status: {trace.get('status', 'unknown')}",
        "",
        "## Linked infra (from recon)",
    ]
    for item in target.get("linked_infra", []):
        lines.append(f"- `{item.get('ip')}` — {item.get('org')} / {item.get('service')}")
    lines.extend([
        "",
        "## Counterparties (priority)",
        f"- Authority: `{target.get('context', {}).get('authority')}`",
        f"- Sink hub: `{target.get('context', {}).get('primary_sink')}`",
        f"- Infra wallet: `{target.get('context', {}).get('infra_correlated')}`",
        "",
        "## Next passive steps",
        "- Arkham label propagation on top 20 counterparties",
        "- Mempool watch via `autonomous_monitor.py` (read-only)",
        "- Fork sim on Anvil before any authorized signing test",
        "- Responsible disclosure if infra owner confirmed",
        "",
        "## Out of scope",
        f"- Operator PoC wallet: `{target.get('out_of_scope', {}).get('operator_proof_wallet')}`",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    target_spec = load_json(TARGET_FILE) or {}
    primary = target_spec.get("primary_target", {})

    dossier: dict[str, Any] = {
        "generated_at": utc_now(),
        "mode": "read-only",
        "target_address": HOT,
        "target": primary,
        "analysis": {},
        "related_artifacts": [],
        "constraints": [
            "no_private_key_access",
            "no_drain_scenarios",
            "passive_on_chain_only",
        ],
    }

    try:
        dossier["analysis"] = analyze()
    except Exception as exc:  # noqa: BLE001
        dossier["analysis_error"] = str(exc)

    related = related_artifacts()
    dossier["related_artifacts"] = list(related.keys())
    dossier["related_snapshot"] = {
        k: related[k] for k in list(related.keys())[:3]
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(dossier, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(build_md(dossier), encoding="utf-8")

    print(json.dumps({"success": True, "json": str(OUT_JSON), "md": str(OUT_MD)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
