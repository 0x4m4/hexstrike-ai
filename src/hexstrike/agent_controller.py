"""Agent controller — квоты, backpressure, authorization gate, mode bypass."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "orchestrator.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    # minimal fallback without PyYAML
    return {}


def _cpu_percent() -> float:
    try:
        import psutil  # type: ignore

        return float(psutil.cpu_percent(interval=0.1))
    except Exception:
        return 0.0


def _mem_percent() -> float:
    try:
        import psutil  # type: ignore

        return float(psutil.virtual_memory().percent)
    except Exception:
        return 0.0


@dataclass
class AgentController:
    """Управляемые лимиты: квоты + backpressure + authorization."""

    config_path: Path = DEFAULT_CONFIG
    _live: set[str] = field(default_factory=set)
    _queue: list[dict[str, Any]] = field(default_factory=list)

    @property
    def config(self) -> dict[str, Any]:
        if not hasattr(self, "_cfg"):
            self._cfg = _load_yaml(self.config_path)
        return self._cfg

    def limits_disabled(self) -> bool:
        if os.environ.get("HEXSTRIKE_LIMITS_DISABLED", "").lower() in ("1", "true", "yes"):
            return True
        return bool(self.config.get("limits", {}).get("disabled", False))

    def mode_bypasses_limit(self, mode: str | None) -> bool:
        if self.limits_disabled():
            return True
        mode = (mode or os.environ.get("HEXSTRIKE_MODE") or "defense").lower()
        unlimited = self.config.get("modes", {}).get("unlimited", ["defense", "validation"])
        return mode in [m.lower() for m in unlimited]

    def max_live(self) -> int:
        return int(self.config.get("agents", {}).get("max_live", 50))

    def backpressure(self) -> dict[str, Any]:
        return self.config.get("agents", {}).get("backpressure", {})

    def resource_pressure(self) -> bool:
        if self.limits_disabled():
            return False
        bp = self.backpressure()
        if not bp.get("enabled", True):
            return False
        cpu = _cpu_percent()
        mem = _mem_percent()
        return cpu >= float(bp.get("threshold_cpu", 80)) or mem >= float(bp.get("threshold_mem", 70))

    def assert_live_limit(self, mode: str | None = None) -> None:
        if self.mode_bypasses_limit(mode):
            return
        if len(self._live) < self.max_live():
            return
        bp = self.backpressure()
        if bp.get("enabled") and bp.get("strategy") == "queue":
            while len(self._live) >= self.max_live() or self.resource_pressure():
                time.sleep(float(bp.get("poll_interval_sec", 2)))
            return
        raise RuntimeError(f"max_live={self.max_live()} reached; backpressure={bp.get('strategy', 'reject')}")

    def acquire(self, agent_id: str, *, mode: str | None = None) -> None:
        self.assert_live_limit(mode)
        self._live.add(agent_id)

    def release(self, agent_id: str) -> None:
        self._live.discard(agent_id)

    def check_authorization(self, scope_path: Path | None = None) -> tuple[bool, str]:
        if self.limits_disabled():
            return True, "limits disabled — authorization gate open"
        auth = self.config.get("authorization", {})
        if not auth.get("require_signed_contracts"):
            return True, "authorization not required"

        valid_until = auth.get("valid_until")
        if valid_until:
            try:
                expiry = date.fromisoformat(str(valid_until))
                if date.today() > expiry:
                    return False, f"authorization expired ({valid_until})"
            except ValueError:
                pass

        scope = scope_path or ROOT / auth.get("scope_file", "scripts/sandbox/field-targets-5.json")
        if not scope.is_file():
            return False, f"scope file missing: {scope}"

        try:
            data = json.loads(scope.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return False, f"invalid scope JSON: {exc}"

        if not data.get("wallets"):
            return False, "scope has no wallets"

        # Metadata gate — полная ECDSA-проверка подписи SecurityCouncil вынесена в MCP rebuild
        meta = {
            "signed_by": auth.get("signed_by"),
            "signature_format": auth.get("signature_format"),
            "valid_until": valid_until,
            "scope_file": str(scope),
            "wallet_count": len(data.get("wallets", [])),
        }
        os.environ["HEXSTRIKE_SCOPE_META"] = json.dumps(meta)
        return True, "scope authorized"

    def authorization_metadata(self) -> dict[str, Any]:
        raw = os.environ.get("HEXSTRIKE_SCOPE_META")
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        auth = self.config.get("authorization", {})
        return {
            "signed_by": auth.get("signed_by"),
            "signature_format": auth.get("signature_format"),
            "valid_until": auth.get("valid_until"),
            "require_signed_contracts": auth.get("require_signed_contracts"),
        }

    def status(self) -> dict[str, Any]:
        return {
            "limits_disabled": self.limits_disabled(),
            "live_count": len(self._live),
            "max_live": self.max_live(),
            "queued": len(self._queue),
            "resource_pressure": self.resource_pressure(),
            "mode_bypass": self.mode_bypasses_limit(None),
        }
