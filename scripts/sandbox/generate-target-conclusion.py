#!/usr/bin/env python3
"""Synthesize actionable conclusions across all scanned wallets (JSON + Markdown)."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts"
SANDBOX_ART = ART / "sandbox"
OUT_JSON = SANDBOX_ART / "target-conclusion.json"
OUT_MD = SANDBOX_ART / "target-conclusion.md"


def load(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def entity_block() -> dict:
    ent = load(ART / "entity-id.json") or {}
    er = ent.get("entity_resolution", {}) if isinstance(ent, dict) else {}
    return {
        "status": er.get("status", "UNKNOWN"),
        "confidence": er.get("confidence", "?"),
        "candidates": er.get("candidate_entities", [])[:3],
        "next_steps": er.get("next_passive_steps", [])[:5],
    }


def infra_verdict() -> str:
    infra = load(ART / "infra-targets.json") or {}
    if not isinstance(infra, dict):
        return ""
    biz = infra.get("onchain_to_offchain_links", {}).get("business_inference", {})
    return biz.get("verdict") or infra.get("scope_note", "")


def battle_summary() -> dict | None:
    br = load(SANDBOX_ART / "battle-report.json")
    if not isinstance(br, dict):
        return None
    s = br.get("summary", {})
    return {
        "readiness_score": s.get("readiness_score"),
        "vuln_confirmed": s.get("vuln_confirmed"),
        "defended": s.get("defended"),
        "inconclusive": s.get("inconclusive"),
    }


def wallet_conclusions(bundle: dict) -> list[dict]:
    out = []
    for w in bundle.get("wallets", []):
        v = w.get("verdict", {})
        live = w.get("live", {})
        out.append({
            "role": w.get("role"),
            "address": w.get("address"),
            "status": v.get("status"),
            "risk_level": v.get("risk_level"),
            "balance_eth": live.get("balance_eth"),
            "nonce": live.get("nonce"),
            "is_contract": live.get("is_contract"),
            "findings": v.get("findings", []),
            "recommended_action": v.get("recommended_action"),
        })
    return out


def overall_verdict(bundle: dict | None, entity: dict, battle: dict | None) -> dict:
    wallets = wallet_conclusions(bundle) if bundle else []
    high = [w for w in wallets if w.get("risk_level") == "high"]
    headline = bundle.get("summary", {}).get("headline") if bundle else "No multi-wallet recon bundle"

    conclusions = []
    if high:
        conclusions.append(f"{len(high)} wallet(s) flagged high-risk — prioritize hot_wallet monitoring")
    if entity.get("status") == "UNIDENTIFIED":
        conclusions.append("Entity still UNIDENTIFIED — OSINT APIs (Arkham/GitHub) required for attribution")
    iv = infra_verdict()
    if iv:
        conclusions.append(iv[:200])
    if battle:
        conclusions.append(
            f"Sandbox battle readiness {battle.get('readiness_score')}/100 "
            f"(vuln={battle.get('vuln_confirmed')} defended={battle.get('defended')})"
        )
    conclusions.append("All testing remained read-only — no mainnet exploit or drain")

    return {
        "headline": headline,
        "risk_posture": "elevated" if high else "monitoring",
        "entity_status": entity.get("status"),
        "entity_confidence": entity.get("confidence"),
        "conclusions": conclusions,
        "priority_actions": [
            "Run Arkham/Blockscan label propagation on top counterparties",
            "Enable GitHub token for infra dorking (currently 401)",
            "Fork-watch on hot_wallet before any authorized signing tests",
            "Responsible disclosure pack if infra owner identified",
        ],
    }


def render_markdown(data: dict) -> str:
    lines = [
        "# HexStrike Target Conclusions",
        "",
        f"**Generated:** {data['generated_at']}",
        f"**Orchestrator run:** {data.get('orchestrator_run_id', 'n/a')}",
        f"**Wallets scanned:** {data.get('wallet_count', 0)}",
        "",
        "## Overall verdict",
        "",
        f"**{data['overall']['headline']}**",
        "",
        f"- Risk posture: **{data['overall']['risk_posture']}**",
        f"- Entity: **{data['overall']['entity_status']}** (confidence: {data['overall']['entity_confidence']})",
        "",
        "### Key conclusions",
        "",
    ]
    for c in data["overall"]["conclusions"]:
        lines.append(f"- {c}")

    lines.extend(["", "## Per-wallet summary", "", "| Role | Address | Risk | Status | Balance (ETH) | Action |", "|------|---------|------|--------|---------------|--------|"])
    for w in data.get("wallets", []):
        addr = w["address"]
        short = f"{addr[:10]}…{addr[-6:]}"
        action = (w.get("recommended_action") or "")[:60]
        lines.append(
            f"| {w['role']} | `{short}` | {w.get('risk_level','?')} | {w.get('status','?')} | "
            f"{w.get('balance_eth','?')} | {action} |"
        )

    if data.get("entity", {}).get("candidates"):
        lines.extend(["", "## Entity candidates", ""])
        for c in data["entity"]["candidates"]:
            lines.append(f"- **{c.get('type')}** ({c.get('confidence')}): {c.get('evidence', '')[:120]}")

    if data.get("battle"):
        b = data["battle"]
        lines.extend([
            "",
            "## Sandbox battle (dummy/local)",
            "",
            f"- Readiness: **{b.get('readiness_score')}/100**",
            f"- Vulnerabilities: {b.get('vuln_confirmed')} | Defended: {b.get('defended')}",
        ])

    lines.extend(["", "## Priority next steps", ""])
    for i, a in enumerate(data["overall"].get("priority_actions", []), 1):
        lines.append(f"{i}. {a}")

    lines.extend(["", "---", "*Read-only defensive research — no unauthorized exploitation.*", ""])
    return "\n".join(lines)


def main() -> int:
    bundle = load(SANDBOX_ART / "target-recon-bundle.json")
    profiles = load(SANDBOX_ART / "target-profiles.json")
    entity = entity_block()
    battle = battle_summary()
    run_id = os.environ.get("ORCHESTRATOR_RUN_ID", "")

    if not bundle and not profiles:
        print("[FAIL] need target-recon-bundle.json or target-profiles.json", file=sys.stderr)
        return 1

    overall = overall_verdict(bundle, entity, battle)
    wallets = wallet_conclusions(bundle) if bundle else []

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "orchestrator_run_id": run_id or None,
        "wallet_count": len(wallets) or (profiles or {}).get("wallet_count", 0),
        "overall": overall,
        "wallets": wallets,
        "entity": entity,
        "battle": battle,
        "artifacts": {
            "profiles": str(SANDBOX_ART / "target-profiles.json"),
            "recon_bundle": str(SANDBOX_ART / "target-recon-bundle.json"),
            "conclusion_md": str(OUT_MD),
        },
    }

    SANDBOX_ART.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(data), encoding="utf-8")

    print(f"[OK] {OUT_JSON}")
    print(f"[OK] {OUT_MD}")
    print(f"VERDICT: {overall['headline']}")
    for c in overall["conclusions"][:4]:
        print(f"  • {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
