"""recon_osint — passive infrastructure mapping (Jenkins/IP/CVE scanning)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hexstrike.bus.context_bus import ContextBus
from hexstrike.paths import ARTIFACTS_DIR, ROOT

sys.path.insert(0, str(ROOT / "scripts"))
from crypto_rpc_orchestrator import GETH_NODES, probe_node  # noqa: E402


@dataclass
class ReconOsintSkill:
    """Passive RPC node reconnaissance and infra fingerprinting."""

    bus: ContextBus
    out_dir: Path = field(default_factory=lambda: ARTIFACTS_DIR / "recon")

    def scan_rpc_nodes(self, limit: int = 5, timeout: float = 6.0) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for node in GETH_NODES[:limit]:
            probe = probe_node(node, timeout=timeout)
            entry = {
                "ip": probe.ip,
                "org": probe.org,
                "country": probe.country,
                "reachable": probe.reachable,
                "latency_ms": probe.latency_ms,
                "risk_flags": probe.risk_flags,
                "client_version": probe.client_version,
            }
            results.append(entry)
            self.bus.publish("skill.recon.node", entry, source="recon_osint")

        report = {"nodes_scanned": len(results), "results": results}
        self.out_dir.mkdir(parents=True, exist_ok=True)
        out = self.out_dir / "rpc_recon.json"
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        self.bus.publish("skill.recon.complete", {"path": str(out)}, source="recon_osint")
        return results

    def fingerprint_host(self, host: str, ports: list[int] | None = None) -> dict[str, Any]:
        ports = ports or [8545, 8080, 443]
        payload = {
            "host": host,
            "ports": ports,
            "status": "passive_only",
            "note": "Extend with Shodan/CVE feeds via MCP integrations",
        }
        self.bus.publish("skill.recon.fingerprint", payload, source="recon_osint")
        return payload
