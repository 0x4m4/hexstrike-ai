#!/usr/bin/env python3
"""Agent-Report-06: consolidate artifacts + sandbox conclusions into master report."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts"
OUT = ART / "vps-master-report.json"

FORENSICS_IOC_ARTIFACTS = [
    "trx-drainer-tool-iocs.json",
    "evm-drainer-iocs.json",
    "apeterminal-main-iocs.json",
    "solana-drainer-tool-iocs.json",
    "vanilla-drainer-iocs.json",
    "permit-farming-eip2612-iocs.json",
    "create2-drainer-iocs.json",
]

FORENSICS_REPORTS = [
    "forensics/trx-drainer-report.json",
    "forensics/evm-drainer-report.json",
    "forensics/apeterminal-drainer-report.json",
    "forensics/solana-drainer-report.json",
    "forensics/vanilla-drainer-report.json",
    "forensics/permit-farming-report.json",
    "forensics/create2-drainer-report.json",
]

ARTIFACTS = [
    "infra-targets.json",
    "multichain-cluster.json",
    "entity-id.json",
    "web-recon.json",
    "jenkins-cve-report.json",
    "defensive-audit-template.md",
    "recon-master-report.json",
]

SANDBOX_ARTIFACTS = [
    "sandbox/target-profiles.json",
    "sandbox/target-recon-bundle.json",
    "sandbox/target-conclusion.json",
    "sandbox/battle-report.json",
]


def load(name: str) -> dict | str | None:
    path = ART / name
    if not path.exists():
        return None
    if name.endswith(".md"):
        return path.read_text()[:2000]
    with open(path) as f:
        return json.load(f)


def load_orchestrator_run() -> dict | None:
    run_id = os.environ.get("ORCHESTRATOR_RUN_ID")
    orch = ART / "orchestrator"
    if run_id:
        p = orch / f"{run_id}.json"
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    latest = orch / "latest.json"
    if latest.is_file():
        return json.loads(latest.read_text(encoding="utf-8"))
    return None


def highlights(data: dict, sandbox: dict) -> list[str]:
    lines: list[str] = []

    conc = sandbox.get("sandbox/target-conclusion.json")
    if isinstance(conc, dict):
        ov = conc.get("overall", {})
        lines.append(f"Conclusion: {ov.get('headline', '?')}")
        lines.append(f"Risk: {ov.get('risk_posture')} | Entity: {ov.get('entity_status')} ({ov.get('entity_confidence')})")
        for c in (ov.get("conclusions") or [])[:2]:
            lines.append(c[:120])

    bundle = sandbox.get("sandbox/target-recon-bundle.json")
    if isinstance(bundle, dict) and not conc:
        lines.append(bundle.get("summary", {}).get("headline", f"Wallets: {bundle.get('wallet_count')}"))

    battle = sandbox.get("sandbox/battle-report.json")
    if isinstance(battle, dict):
        s = battle.get("summary", {})
        lines.append(f"Battle readiness: {s.get('readiness_score')}/100")

    ent = data.get("entity-id.json") or {}
    if isinstance(ent, dict) and not conc:
        e = ent.get("entity_resolution") or {}
        if isinstance(e, dict):
            lines.append(f"Entity: {e.get('status', 'UNIDENTIFIED')} (confidence: {e.get('confidence', '?')})")

    jenkins = data.get("jenkins-cve-report.json") or {}
    if isinstance(jenkins, dict):
        cves = jenkins.get("cves_march_2023_advisory") or []
        ver = jenkins.get("target") or "Jenkins"
        lines.append(f"{ver}: {len(cves)} CVEs (passive)")

    ioc_count = sum(1 for n in FORENSICS_IOC_ARTIFACTS if data.get(n))
    if ioc_count:
        lines.append(f"Forensics IOC modules: {ioc_count}/{len(FORENSICS_IOC_ARTIFACTS)} present")

    return lines


def main() -> int:
    out_path = Path(os.environ.get("OUTPUT", OUT))
    bundled: dict = {}
    for name in ARTIFACTS + FORENSICS_IOC_ARTIFACTS + FORENSICS_REPORTS:
        bundled[name] = load(name)

    sandbox_bundled: dict = {}
    for name in SANDBOX_ARTIFACTS:
        sandbox_bundled[name] = load(name)

    orchestrator_run = load_orchestrator_run()
    conclusion_md = None
    md_path = ART / "sandbox" / "target-conclusion.md"
    if md_path.is_file():
        conclusion_md = md_path.read_text(encoding="utf-8")[:4000]

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent": "Agent-Report-06",
        "task": "generate-vps-master-report",
        "host": os.uname().nodename if hasattr(os, "uname") else "unknown",
        "mode": "read-only_passive",
        "orchestrator_run_id": os.environ.get("ORCHESTRATOR_RUN_ID") or (orchestrator_run or {}).get("run_id"),
        "orchestrator_workflow": os.environ.get("ORCHESTRATOR_WORKFLOW") or (orchestrator_run or {}).get("workflow"),
        "orchestrator_success": (orchestrator_run or {}).get("success"),
        "highlights": highlights(bundled, sandbox_bundled),
        "artifacts_present": [k for k, v in bundled.items() if v is not None],
        "artifacts_missing": [k for k, v in bundled.items() if v is None],
        "sandbox_present": [k for k, v in sandbox_bundled.items() if v is not None],
        "conclusion_markdown_preview": conclusion_md,
        "artifacts": {k: v for k, v in bundled.items() if v is not None and not k.endswith(".md")},
        "sandbox": {k: v for k, v in sandbox_bundled.items() if v is not None},
        "disclosure_pack": "artifacts/disclosure-pack/",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Wrote {out_path}")
    print("Highlights:")
    for h in report["highlights"]:
        print(f"  • {h}")
    if conclusion_md:
        print(f"Conclusion MD: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
