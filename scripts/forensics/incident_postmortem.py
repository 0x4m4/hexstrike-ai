#!/usr/bin/env python3
"""Generate incident post-mortem JSON bundle (worst-case IR plan)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "forensics" / "incident-total-compromise.json"
CONCLUSION_MD = ROOT / "artifacts" / "forensics" / "incident-conclusion.md"
MD = ROOT / "docs" / "forensics" / "INCIDENT-TOTAL-COMPROMISE-POSTMORTEM.md"

HOT = "0x4943f5e7f4e450d48ae82026163ecde8a52c53da"

payload = {
    "case_id": "HEX-2026-07-12-TOTAL-COMPROMISE",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "document_type": "incident_post_mortem_worst_case",
    "mode": "defensive_ir",
    "actual_state": {
        "jenkins_rce_proven": True,
        "open_bsc_rpc_proven": True,
        "private_key_obtained": False,
        "drain_executed": False,
        "payroll_otc_verdict": "CLOSED_MEDIUM_HIGH",
    },
    "worst_case_assumption": {
        "private_key_compromised": True,
        "jenkins_credentials_compromised": True,
        "geth_node_control": True,
        "signing_service_compromised": True,
    },
    "target": HOT,
    "infra": {
        "jenkins": "51.250.97.223:8080",
        "geth_rpc": "51.222.42.220:8545",
    },
    "ir_phases": ["containment", "asset_rescue", "eradication", "recovery"],
    "verdict_actual": "Perimeter exposed; key not confirmed leaked; drain blocked",
    "verdict_worst_case": "Infrastructure unfit; keys burned; greenfield + new payout rail required",
    "conclusion": {
        "executive_summary": "Infrastructure critically exposed but not fully breached as of 2026-07-12. Hot wallet is payroll disbursement rail. Forensics CLOSED. Worst-case IR plan READY.",
        "actual_verdict": "Preventive containment required; no unauthorized withdrawal confirmed; private key not obtained.",
        "worst_case_verdict": "Total compromise: burn 0x4943..., greenfield rebuild, Vault signing, new payout rail.",
        "case_status_forensics": "CLOSED",
        "case_status_ir": "PREVENTIVE_MONITORING",
        "trigger_worst_case": ["unauthorized_signed_tx", "key_exfil_confirmed", "anomalous_outflow"],
    },
    "markdown_source": str(MD.relative_to(ROOT)),
    "related_artifacts": [
        "artifacts/forensics/hot-wallet-dossier.json",
        "artifacts/forensics/payroll-otc-verdict.json",
        "artifacts/entity-id.json",
        "artifacts/jenkins-cve-report.json",
    ],
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"success": True, "output": str(OUT)}, indent=2))
