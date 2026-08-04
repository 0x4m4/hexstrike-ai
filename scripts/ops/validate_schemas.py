#!/usr/bin/env python3
"""Strict Pydantic contracts for GLOBAL GO evidence.

Any missing file or contract violation → exit 1 (fail-closed).
Semantic rules: success flags must be true, drift must be false, SLA met, etc.
Demo fixtures may validate structurally but are never GLOBAL-GO eligible
(see collect_artifacts.sh COLLECT_MODE=demo → verdict.json).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal

try:
    from pydantic import BaseModel, Field, ValidationError, field_validator
except ImportError:
    print(
        "pydantic required: pip install -r scripts/ops/requirements-ops.txt",
        file=sys.stderr,
    )
    raise SystemExit(2)


def _require_true(v: bool) -> bool:
    if v is not True:
        raise ValueError("must be true for GLOBAL GO contract")
    return v


def _require_false(v: bool) -> bool:
    if v is not False:
        raise ValueError("must be false for GLOBAL GO contract")
    return v


class KmsSmokeEvidence(BaseModel):
    backend: Literal["aws_kms", "gcp_kms"]
    key_id: str = Field(min_length=8)
    sign_success: bool
    verify_success: bool
    latency_ms: int = Field(ge=0, lt=1000)
    timestamp: datetime

    @field_validator("sign_success", "verify_success")
    @classmethod
    def _ok_flags(cls, v: bool) -> bool:
        return _require_true(v)


class IamAuditEvidence(BaseModel):
    role: str = Field(min_length=3)
    least_privilege_check: bool
    mfa_enforced: bool
    no_wildcard_actions: bool
    last_rotated: datetime

    @field_validator("least_privilege_check", "mfa_enforced", "no_wildcard_actions")
    @classmethod
    def _iam_flags(cls, v: bool) -> bool:
        return _require_true(v)


class PagingDrillEvidence(BaseModel):
    channel: str = Field(min_length=3)
    triggered_at: datetime
    acknowledged_by: str = Field(min_length=2)
    ack_latency_sec: int = Field(ge=0, lt=300)
    sla_met: bool

    @field_validator("sla_met")
    @classmethod
    def _sla(cls, v: bool) -> bool:
        return _require_true(v)


class ShadowCanaryEvidence(BaseModel):
    phase: Literal["shadow", "canary"]
    duration_hours: int = Field(ge=1)
    tx_processed: int = Field(gt=0)
    drift_detected: bool
    scope_0_verified: bool
    allowlist_enforced: bool

    @field_validator("drift_detected")
    @classmethod
    def _no_drift(cls, v: bool) -> bool:
        return _require_false(v)

    @field_validator("scope_0_verified", "allowlist_enforced")
    @classmethod
    def _scope_flags(cls, v: bool) -> bool:
        return _require_true(v)


SCHEMAS: dict[str, type[BaseModel]] = {
    "kms_smoke.json": KmsSmokeEvidence,
    "iam_audit.json": IamAuditEvidence,
    "paging_drill.json": PagingDrillEvidence,
    "shadow_canary.json": ShadowCanaryEvidence,
}


def validate_dir(evidence_dir: Path) -> list[str]:
    errors: list[str] = []
    for filename, schema in SCHEMAS.items():
        path = evidence_dir / filename
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            schema.model_validate(data)
            print(f"  [PASS] {filename}")
        except FileNotFoundError:
            errors.append(f"  [FAIL] {filename}: file not found")
        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"  [FAIL] {filename}: {exc}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("evidence_dir", type=Path, nargs="?", default=Path("docs/ops/evidence"))
    args = ap.parse_args()
    evidence_dir = args.evidence_dir
    if not evidence_dir.is_dir():
        print(f"evidence dir missing: {evidence_dir}", file=sys.stderr)
        return 1

    print(f"[*] Validating strict Pydantic contracts in {evidence_dir} ...")
    errors = validate_dir(evidence_dir)
    if errors:
        print("\nContract Violations:")
        print("\n".join(errors))
        return 1

    verdict_path = evidence_dir / "verdict.json"
    if verdict_path.exists():
        try:
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            verdict = {}
        if verdict.get("collect_mode") == "demo" or verdict.get("global_go_eligible") is False:
            print(
                "[!] Schemas PASS but collect_mode=demo / global_go_eligible=false "
                "→ GLOBAL GO remains BLOCKED (fail-closed)."
            )
            return 0
    print("[+] All evidence contracts PASS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
