"""Vector C — IP ↔ wallet forensics via WHOIS / ASN OSINT."""

from __future__ import annotations

import json
import subprocess
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from hexstrike.bus.context_bus import ContextBus
from hexstrike.paths import ARTIFACTS_DIR


@dataclass
class IpForensicsSkill:
    """Correlate infrastructure IP with wallet investigation artifacts (LEA-ready)."""

    bus: ContextBus

    def whois_lookup(self, ip: str) -> str:
        try:
            proc = subprocess.run(
                ["whois", ip],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return proc.stdout or proc.stderr or ""
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return f"whois unavailable: {exc}"

    def ipinfo_lookup(self, ip: str) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(f"https://ipinfo.io/{ip}/json", timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)}

    def correlate_wallet(
        self,
        ip: str,
        wallet: str,
        *,
        forensics_engine: Any | None = None,
    ) -> dict[str, Any]:
        whois_raw = self.whois_lookup(ip)
        ipinfo = self.ipinfo_lookup(ip)

        entity: dict[str, Any] = {}
        if forensics_engine:
            entity = forensics_engine.resolve_entity(wallet)

        org = ipinfo.get("org", "")
        is_yandex = "yandex" in org.lower() or "yandex" in whois_raw.lower()

        lea_pack = {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "type": "infrastructure_wallet_correlation",
            "target_ip": ip,
            "wallet_address": wallet.lower(),
            "hosting": {
                "provider": org or "unknown",
                "yandex_cloud_likely": is_yandex,
                "city": ipinfo.get("city"),
                "country": ipinfo.get("country"),
                "asn": org.split()[0] if org else None,
            },
            "wallet_entity": entity,
            "chain_of_custody_note": (
                "IP registration data must be requested from Yandex Cloud via legal process "
                "(Russian Federation operator). WHOIS shows ASN only, not tenant identity."
            ),
            "recommended_lea_actions": [
                "Preserve artifacts/infra-trace-final.json and this report",
                "Submit legal request to Yandex Cloud LLC for VM tenant billing identity",
                "Cross-reference Jenkins instance-identity key with internal case timeline",
                "Map wallet outflows (cex-cluster-map) against infra deployment dates",
            ],
        }

        self.bus.publish("skill.forensics.ip_wallet", lea_pack, source="skill.ip_forensics")
        return lea_pack

    def run(self, ip: str, wallet: str, forensics_engine: Any | None = None) -> dict[str, Any]:
        whois_raw = self.whois_lookup(ip)
        ipinfo = self.ipinfo_lookup(ip)
        correlation = self.correlate_wallet(ip, wallet, forensics_engine=forensics_engine)

        report = {
            "vector": "C_forensics_ip_wallet",
            "target_ip": ip,
            "wallet": wallet,
            "whois_excerpt": whois_raw[:2000],
            "ipinfo": ipinfo,
            "correlation": correlation,
        }

        out = ARTIFACTS_DIR / "vector-forensics-report.json"
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return report
