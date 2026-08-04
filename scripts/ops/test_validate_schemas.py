#!/usr/bin/env python3
"""Negative/positive tests for GLOBAL GO evidence contracts."""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from validate_schemas import (
    IamAuditEvidence,
    KmsSmokeEvidence,
    PagingDrillEvidence,
    ShadowCanaryEvidence,
    validate_dir,
)


TS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TestContracts(unittest.TestCase):
    def test_kms_rejects_failed_sign(self) -> None:
        with self.assertRaises(Exception):
            KmsSmokeEvidence(
                backend="aws_kms",
                key_id="arn:aws:kms:us-east-1:1:key/x",
                sign_success=False,
                verify_success=True,
                latency_ms=10,
                timestamp=TS,
            )

    def test_shadow_rejects_drift(self) -> None:
        with self.assertRaises(Exception):
            ShadowCanaryEvidence(
                phase="shadow",
                duration_hours=24,
                tx_processed=10,
                drift_detected=True,
                scope_0_verified=True,
                allowlist_enforced=True,
            )

    def test_paging_rejects_sla_false(self) -> None:
        with self.assertRaises(Exception):
            PagingDrillEvidence(
                channel="pd",
                triggered_at=TS,
                acknowledged_by="op",
                ack_latency_sec=10,
                sla_met=False,
            )

    def test_validate_dir_pass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "kms_smoke.json").write_text(
                json.dumps(
                    {
                        "backend": "aws_kms",
                        "key_id": "arn:aws:kms:us-east-1:1:key/x",
                        "sign_success": True,
                        "verify_success": True,
                        "latency_ms": 100,
                        "timestamp": TS,
                    }
                )
            )
            (d / "iam_audit.json").write_text(
                json.dumps(
                    {
                        "role": "prod-rescue-signer",
                        "least_privilege_check": True,
                        "mfa_enforced": True,
                        "no_wildcard_actions": True,
                        "last_rotated": TS,
                    }
                )
            )
            (d / "paging_drill.json").write_text(
                json.dumps(
                    {
                        "channel": "pagerduty-prod",
                        "triggered_at": TS,
                        "acknowledged_by": "operator_01",
                        "ack_latency_sec": 45,
                        "sla_met": True,
                    }
                )
            )
            (d / "shadow_canary.json").write_text(
                json.dumps(
                    {
                        "phase": "shadow",
                        "duration_hours": 24,
                        "tx_processed": 100,
                        "drift_detected": False,
                        "scope_0_verified": True,
                        "allowlist_enforced": True,
                    }
                )
            )
            self.assertEqual(validate_dir(d), [])


if __name__ == "__main__":
    raise SystemExit(unittest.main())
