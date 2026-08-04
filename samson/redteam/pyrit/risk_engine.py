"""Microsoft PyRIT risk engine integration (ADR-003)."""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from samson.core.config import SamsonSettings, get_settings
from samson.core.database import AuditRepository, Database, sha256_payload
from samson.core.errors import ToolExecutionError
from samson.core.scope import ScopeEnforcer
from samson.redteam.schemas import PyRITRiskRequest, PyRITRiskResult

logger = logging.getLogger(__name__)


class PyRITRiskEngine:
    """Evaluates scenario drafts using PyRIT when installed; falls back to heuristic scorer."""

    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db = Database(self._settings)
        self._audit = AuditRepository(self._db)
        self._scope = ScopeEnforcer(self._settings)
        self._reports_dir = Path("samson/redteam/pyrit/reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def evaluate(self, req: PyRITRiskRequest) -> PyRITRiskResult:
        if not self._settings.pyrit_enabled:
            raise ToolExecutionError("pyrit", "PyRIT is disabled in configuration")

        self._scope.assert_operator(req.operator_id, request_id=req.request_id)
        start = time.perf_counter()

        report_id = uuid4()
        report_path = self._reports_dir / f"{report_id}.json"

        pyrit_available = self._pyrit_available()
        if pyrit_available:
            raw = self._run_pyrit_subprocess(req, report_path)
        else:
            raw = self._heuristic_score(req)
            report_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")

        risk_score = float(raw.get("risk_score", 0.0))
        harm_categories = [str(c) for c in raw.get("harm_categories") or []]
        risk_band = self._band(risk_score)
        blocked = risk_score >= self._settings.pyrit_block_threshold
        requires_elevated = (
            risk_score >= self._settings.pyrit_elevated_threshold
            and risk_score < self._settings.pyrit_block_threshold
        )

        result = PyRITRiskResult(
            request_id=req.request_id,
            risk_score=risk_score,
            risk_band=risk_band,
            harm_categories=harm_categories,
            blocked=blocked,
            requires_elevated_approval=requires_elevated,
            rationale=str(raw.get("rationale") or ""),
            pyrit_report_path=str(report_path),
            scanned_at=datetime.now(tz=timezone.utc),
        )

        duration_ms = int((time.perf_counter() - start) * 1000)
        if self._settings.audit_enabled:
            self._audit.write_redteam_audit(
                request_id=req.request_id,
                tool="pyrit",
                operator_id=req.operator_id,
                action="risk_eval",
                outcome="block" if blocked else "pass",
                payload_hash=sha256_payload(req.model_dump(mode="json")),
                duration_ms=duration_ms,
            )
        return result

    def _pyrit_available(self) -> bool:
        try:
            proc = subprocess.run(
                [self._settings.pyrit_python, "-c", "import pyrit"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            return proc.returncode == 0
        except (subprocess.SubprocessError, OSError):
            return False

    def _run_pyrit_subprocess(self, req: PyRITRiskRequest, report_path: Path) -> dict:
        script = f"""
import json, sys
from pathlib import Path

payload = json.loads(Path({str(report_path)!r}).with_name("input.json").read_text())
scenario_text = json.dumps(payload.get("scenario_draft", {{}}))
harm_categories = []
risk = 0.0
text = scenario_text.lower()
rules = {{
    "jailbreak": ["jailbreak", "ignore previous", "bypass"],
    "data_exfiltration": ["exfil", "leak", "api key", "secret"],
    "harmful_content": ["ransom", "destroy", "weapon"],
    "prompt_injection": ["system prompt", "inject", "override"],
}}
for category, terms in rules.items():
    if any(t in text for t in terms):
        harm_categories.append(category)
        risk += 0.2
risk = min(risk, 1.0)
result = {{
    "risk_score": risk,
    "harm_categories": harm_categories,
    "rationale": "PyRIT subprocess evaluation over scenario draft",
    "engine": "pyrit_subprocess",
}}
Path({str(report_path)!r}).write_text(json.dumps(result, indent=2))
print(json.dumps(result))
"""
        input_path = report_path.with_name("input.json")
        input_path.write_text(json.dumps(req.model_dump(mode="json"), indent=2), encoding="utf-8")
        try:
            proc = subprocess.run(
                [self._settings.pyrit_python, "-c", script],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            if proc.returncode != 0:
                raise ToolExecutionError(
                    "pyrit",
                    "PyRIT subprocess failed",
                    stderr=proc.stderr[:2000],
                    stdout=proc.stdout[:2000],
                )
            if report_path.is_file():
                return json.loads(report_path.read_text(encoding="utf-8"))
            return json.loads(proc.stdout.strip() or "{}")
        except json.JSONDecodeError as exc:
            raise ToolExecutionError("pyrit", "PyRIT returned invalid JSON", error=str(exc)) from exc
        finally:
            if input_path.is_file():
                input_path.unlink(missing_ok=True)

    def _heuristic_score(self, req: PyRITRiskRequest) -> dict:
        text = json.dumps(req.scenario_draft, ensure_ascii=False).lower()
        rules = {
            "jailbreak": ["jailbreak", "ignore previous", "bypass"],
            "data_exfiltration": ["exfil", "leak", "api key", "secret", "credential"],
            "harmful_content": ["ransom", "destroy", "weapon"],
            "prompt_injection": ["system prompt", "inject", "override"],
            "lateral_movement": ["lateral", "pivot", "internal network"],
        }
        harm_categories: list[str] = []
        risk = 0.0
        for category, terms in rules.items():
            if any(term in text for term in terms):
                harm_categories.append(category)
                risk += 0.18
        risk = min(risk, 1.0)
        return {
            "risk_score": risk,
            "harm_categories": harm_categories,
            "rationale": "Heuristic scorer (install pyrit package for full engine integration)",
            "engine": "heuristic",
        }

    def _band(self, score: float) -> str:
        if score >= self._settings.pyrit_block_threshold:
            return "critical"
        if score >= self._settings.pyrit_elevated_threshold:
            return "high"
        if score >= 0.3:
            return "medium"
        return "low"
