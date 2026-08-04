#!/usr/bin/env python3
"""Agent-OSINT-03: passive label propagation for field targets (Arkham + explorer tags)."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILES = ROOT / "artifacts" / "sandbox" / "target-profiles.json"
OUT_JSON = ROOT / "docs" / "recon" / "LABEL-PROPAGATION-PHASE4-20260713.json"
OUT_MD = ROOT / "docs" / "recon" / "LABEL-PROPAGATION-PHASE4-20260713.md"

KNOWN_LABELS = {
    "0x4943f5e7f4e450d48ae82026163ecde8a52c53da": {
        "public_tag": None,
        "inferred_role": "multichain ops treasury (BSC USDT + Base USDC)",
        "entity": "UNIDENTIFIED",
    },
    "0x730ea0231808f42a20f8921ba7fbc788226768f5": {
        "public_tag": None,
        "inferred_role": "EIP-7702 authority delegate",
        "entity": "hot_wallet_infra",
    },
    "0x55ed7fcd17b93fbcd5186cda01af6fed4ec78e08": {
        "public_tag": None,
        "inferred_role": "EIP-7702 sweep delegate #1",
        "entity": "hot_wallet_infra",
    },
    "0x3e0b65c9c31e9593e2b357be6eecd28bef6da03e": {
        "public_tag": None,
        "inferred_role": "EIP-7702 sweep delegate #2",
        "entity": "hot_wallet_infra",
    },
    "0x3a8b628934f9db7999499905bbf767331266b5b5": {
        "public_tag": None,
        "inferred_role": "EIP-7702 sweep delegate #3",
        "entity": "hot_wallet_infra",
    },
    "0xb80a582fa430645a043bb4f6135321ee01005fef": {
        "public_tag": "Rhino.fi: Bridge",
        "inferred_role": "cross-chain bridge sink",
        "entity": "Rhino.fi (protocol)",
    },
    "0x161ba15a5f335c9f06bb5bbb0a9ce14076fbb645": {
        "public_tag": "Binance Hot Wallet 11",
        "inferred_role": "CEX hot wallet — primary funder",
        "entity": "Binance",
    },
    "0x314c01e758a7911e7339aa4f960c7749e8947775": {
        "public_tag": None,
        "inferred_role": "EIP-7702 payment delegate implementation",
        "entity": "hot_wallet_infra",
    },
    "0x4848489f0b2bedd788c696e2d79b6b69d7484848": {
        "public_tag": "48Club Puissant Builder",
        "inferred_role": "MEV validator (separate infra)",
        "entity": "48Club",
    },
}


def fetch_bscscan_name_tag(address: str) -> str | None:
    """Passive HTML scrape for public BscScan name tag (read-only)."""
    url = f"https://bscscan.com/address/{address}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HexStrike-OSINT/1.0 (read-only)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode(errors="ignore")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    m = re.search(r'<title>\s*(.+?)\s*\|\s*BscScan', html, re.I)
    if not m:
        return None
    title = m.group(1).strip()
    if "Address" in title and len(title) < 30:
        return None
    return title if title != address else None


def load_profiles() -> list[dict]:
    if not PROFILES.is_file():
        return []
    return json.loads(PROFILES.read_text()).get("wallets", [])


def main() -> int:
    wallets = load_profiles()
    if not wallets:
        print("[FAIL] target-profiles.json missing — run generate-target-profile first", file=sys.stderr)
        return 1

    entries: list[dict] = []
    labeled_public = 0
    for w in wallets:
        addr = w["address"]
        key = addr.lower()
        known = KNOWN_LABELS.get(key, {})
        bsc_tag = fetch_bscscan_name_tag(addr) if w.get("chain_id") in (56, 0) or w.get("chain") == "BSC" else None
        public = bsc_tag or known.get("public_tag") or w.get("labels", {}).get("bscscan_label")
        if public:
            labeled_public += 1
        entries.append({
            "role": w.get("role"),
            "address": addr,
            "chain": w.get("chain"),
            "public_label": public,
            "inferred_role": known.get("inferred_role") or w.get("labels", {}).get("classification"),
            "entity_cluster": known.get("entity"),
            "arkham_url": f"https://platform.arkhamintelligence.com/explorer/address/{addr}",
            "blockscan_url": f"https://blockscan.com/address/{addr}",
            "basescan_url": f"https://basescan.org/address/{addr}" if w.get("role") == "hot_wallet" or "base" in w.get("role", "") else None,
            "bscscan_url": f"https://bscscan.com/address/{addr}",
            "label_source": "bscscan_html" if bsc_tag else ("artifact" if known.get("public_tag") else "inferred"),
        })

    entity_clusters = {}
    for e in entries:
        cluster = e.get("entity_cluster") or "unknown"
        entity_clusters.setdefault(cluster, []).append(e["role"])

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent": "Agent-OSINT-03",
        "task": "arkham-label-propagate",
        "mode": "read-only_passive",
        "target_count": len(entries),
        "public_labels_found": labeled_public,
        "entity_resolution": {
            "status": "UNIDENTIFIED",
            "confidence": "low",
            "hot_wallet_entity": None,
            "infra_cluster": "hot_wallet_infra (4 EIP-7702 delegates + shared impl)",
            "external_protocols": ["Rhino.fi", "Binance"],
            "separate_infra": ["48Club Puissant (not correlated)"],
        },
        "labels": entries,
        "entity_clusters": entity_clusters,
        "arkham_manual_required": True,
        "arkham_note": "No ARKHAM_API_KEY in env — UI lookup URLs generated per target",
        "next_steps": [
            "Manual Arkham UI review for hot_wallet cluster naming",
            "GitHub token for address dorking",
            "Extended outflow trace on unlabeled top recipients",
        ],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    md = f"""# Label Propagation Phase-4 — 2026-07-13

**Agent:** OSINT-03 | **Targets:** {len(entries)} | **Public labels:** {labeled_public}

## Entity verdict

- Hot wallet entity: **UNIDENTIFIED**
- Infra cluster: **hot_wallet_infra** (4 EIP-7702 delegates + shared impl)
- External: Rhino.fi (bridge), Binance (funder)

## Labels per target

| Role | Public label | Inferred role | Entity cluster |
|------|--------------|---------------|----------------|
"""
    for e in entries:
        md += f"| {e['role']} | {e.get('public_label') or '—'} | {e.get('inferred_role') or '—'} | {e.get('entity_cluster') or '—'} |\n"

    md += """
## Arkham manual review

"""
    for e in entries[:3]:
        md += f"- [{e['role']}]({e['arkham_url']})\n"

    md += "\n---\n*Read-only passive OSINT — no API key required for URL generation.*\n"
    OUT_MD.write_text(md, encoding="utf-8")

    print(f"[OK] {OUT_JSON}")
    print(f"[OK] targets={len(entries)} public_labels={labeled_public}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
