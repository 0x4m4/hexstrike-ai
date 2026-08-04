#!/usr/bin/env python3
"""Сводный отчёт по 3 прогонам — русский Markdown + JSON."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts"


def load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    session_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    runs = {
        "operator_lab": load_json(ART / "orchestrator" / "latest-operator-lab.json")
        or _find_run("operator-lab"),
        "field_targets": load_json(ART / "orchestrator" / "latest-field-targets.json")
        or _find_run("field-targets-5"),
        "forensics": load_json(ART / "forensics" / "session-summary.json"),
    }

    conclusion = load_json(ART / "sandbox" / "target-conclusion.json") or {}
    overall = conclusion.get("overall", {})

    forensics_fail = int(os.environ.get("PROGON_FAILED_COUNT", "0"))
    if forensics_fail == 0 and runs.get("forensics"):
        forensics_fail = runs.get("forensics", {}).get("failed", 0)

    ioc_files = sorted(ART.glob("*-iocs.json"))
    report_files = sorted((ART / "forensics").glob("*-report.json")) if (ART / "forensics").is_dir() else []

    md_lines = [
        f"# Сводный отчёт HexStrike — 3 прогона",
        f"",
        f"**Сессия:** {session_id}  ",
        f"**Режим:** forensics (read-only)  ",
        f"",
        f"## Прогон 1 — operator-lab",
        f"- Статус: {_status(runs.get('operator_lab'))}",
        f"- Run ID: {(runs.get('operator_lab') or {}).get('run_id', '—')}",
        f"- Назначение: аудит оператора, crypto-audit, чеклист",
        f"",
        f"## Прогон 2 — field-targets-5",
        f"- Статус: {_status(runs.get('field_targets'))}",
        f"- Run ID: {(runs.get('field_targets') or {}).get('run_id', '—')}",
        f"- Кошельков: {conclusion.get('wallet_count', 5)}",
        f"- Вердикт: **{overall.get('headline', '—')}**",
        f"- Риск: {overall.get('risk_posture', '—')} | Субъект: {overall.get('entity_status', '—')}",
        f"",
    ]
    for w in (conclusion.get("wallets") or [])[:5]:
        md_lines.append(f"  - {w.get('role')}: `{w.get('address')}` — {w.get('risk_level')}")

    md_lines.extend([
        f"",
        f"## Прогон 3 — run-all-forensics",
        f"- IOC файлов: {len(ioc_files)}",
        f"- Полных отчётов: {len(report_files)}",
        f"- Модулей failed: {forensics_fail}",
        f"",
        f"### Модули IOC",
    ])
    for p in ioc_files:
        md_lines.append(f"- `{p.name}`")
    md_lines.extend([
        f"",
        f"### Forensics reports",
    ])
    for p in report_files:
        md_lines.append(f"- `{p.name}`")

    md_lines.extend([
        f"",
        f"## Рекомендации",
    ])
    for a in (overall.get("priority_actions") or [])[:5]:
        md_lines.append(f"- {a}")

    md = "\n".join(md_lines) + "\n"
    out_md = ART / "forensics" / f"session-report-{session_id}.md"
    out_json = ART / "forensics" / "session-summary.json"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md, encoding="utf-8")

    summary = {
        "session_id": session_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs": {k: {"run_id": (v or {}).get("run_id"), "success": (v or {}).get("success")} for k, v in runs.items()},
        "field_conclusion": overall,
        "ioc_count": len(ioc_files),
        "report_count": len(report_files),
        "markdown": str(out_md.relative_to(ROOT)),
    }
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    desktop = Path.home() / "Desktop" / "on-chain-forensics" / "artifacts"
    try:
        desktop.mkdir(parents=True, exist_ok=True)
        (desktop / out_md.name).write_text(md, encoding="utf-8")
        (desktop / "session-summary.json").write_text(out_json.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError:
        pass

    print(md)
    print(f"\n[OK] {out_md}")
    return 0


def _status(run: dict | None) -> str:
    if not run:
        return "не найден"
    return "успех" if run.get("success") else "ошибка"


def _find_run(workflow: str) -> dict | None:
    orch = ART / "orchestrator"
    if not orch.is_dir():
        return None
    for path in sorted(orch.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.name.endswith("-findings.json") or path.name == "latest.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("workflow") == workflow:
                return data
        except json.JSONDecodeError:
            continue
    return None


if __name__ == "__main__":
    raise SystemExit(main())
