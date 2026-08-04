"""Infrastructure trace — read-only deep OSINT (no CVE exploitation)."""

from __future__ import annotations

import json
import random
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from hexstrike.bus.context_bus import ContextBus
from hexstrike.core.stealth.transport import StealthConfig, StealthTransport
from hexstrike.integrations.rpc_client import StealthRpcClient
from hexstrike.paths import ARTIFACTS_DIR, RPC_CONFIG

JENKINS_CVE = "CVE-2024-23897"
JENKINS_PATHS_OF_INTEREST = [
    "/credentials.xml",
    "/config.xml",
    "/script",
    "/manage",
]


@dataclass
class InfraTracer:
    """Passive infrastructure mapping with stealth pacing — no exploit payloads."""

    bus: ContextBus
    stealth: StealthTransport = field(default_factory=lambda: StealthTransport(StealthConfig()))
    out_dir: Any = field(default_factory=lambda: ARTIFACTS_DIR / "infra-trace")

    def _pause(self) -> None:
        time.sleep(random.uniform(0.8, 2.5))

    def _http_probe(self, url: str, timeout: float = 6.0) -> dict[str, Any]:
        self._pause()
        headers_seen: dict[str, str] = {}
        body_snippet = ""
        status = None
        try:
            req = Request(url, headers={"User-Agent": random.choice(
                ("Mozilla/5.0", "curl/8.4.0", "HexStrike-Recon/1.0")
            )})
            with urlopen(req, timeout=timeout) as resp:
                status = resp.status
                for k, v in resp.headers.items():
                    headers_seen[k.lower()] = v
                raw = resp.read(4096)
                body_snippet = raw.decode("utf-8", errors="replace")[:800]
        except URLError as exc:
            return {"url": url, "error": str(exc), "headers": headers_seen}
        except Exception as exc:  # noqa: BLE001
            return {"url": url, "error": str(exc), "headers": headers_seen}

        proxy_hints = {
            k: v for k, v in headers_seen.items()
            if k.startswith("x-") or k in ("server", "via", "x-forwarded-for", "x-real-ip")
        }
        jenkins_markers = any(
            m in body_snippet.lower() or m in str(headers_seen).lower()
            for m in ("jenkins", "x-jenkins", "hudson", "credentials")
        )
        return {
            "url": url,
            "status": status,
            "headers": headers_seen,
            "proxy_hints": proxy_hints,
            "jenkins_suspected": jenkins_markers,
            "body_snippet": body_snippet[:400],
        }

    def probe_jenkins_surface(self, ip: str) -> dict[str, Any]:
        """Fingerprint Jenkins exposure without CVE file-read exploitation."""
        probes = []
        for scheme, port in (("http", 8080), ("https", 443)):
            base = f"{scheme}://{ip}:{port}"
            probes.append(self._http_probe(base))
            for path in ("/login", "/manage"):
                probes.append(self._http_probe(f"{base}{path}"))

        exposed = any(p.get("jenkins_suspected") for p in probes)
        cve_surface = {
            "cve_id": JENKINS_CVE,
            "exploitation": "NOT_PERFORMED",
            "reason": "Read-only OSINT policy — arbitrary file read requires authorized pentest scope",
            "paths_of_interest": JENKINS_PATHS_OF_INTEREST,
            "surface_exposed": exposed,
            "credential_file_access": False,
            "operator_gate": "mcp_execution_gate required for any credential retrieval",
        }
        self.bus.publish("skill.infra.jenkins", cve_surface, source="skill.recon_osint")
        return {"probes": probes, "cve_assessment": cve_surface}

    def probe_geth_peering(self, ip: str, port: int = 8545) -> dict[str, Any]:
        """Read-only Geth RPC — peer list and client info when modules allow."""
        url = f"http://{ip}:{port}"
        client = StealthRpcClient(RPC_CONFIG)
        results: dict[str, Any] = {"endpoint": url, "methods": {}}

        for method, params in (
            ("web3_clientVersion", []),
            ("eth_chainId", []),
            ("net_peerCount", []),
            ("admin_nodeInfo", []),
            ("admin_peers", []),
        ):
            self._pause()
            try:
                data = client.transport.rpc_call(url, method, params, timeout=8.0)
                results["methods"][method] = {
                    "ok": "result" in data and data.get("error") is None,
                    "result": data.get("result"),
                    "error": data.get("error"),
                }
            except Exception as exc:  # noqa: BLE001
                results["methods"][method] = {"ok": False, "error": str(exc)}

        peers_raw = results["methods"].get("admin_peers", {}).get("result")
        peer_ips: list[str] = []
        if isinstance(peers_raw, list):
            for peer in peers_raw:
                if isinstance(peer, dict):
                    addr = peer.get("network", {}).get("remoteAddress") or peer.get("enode", "")
                    peer_ips.append(str(addr))

        cluster_hint = len(peer_ips) > 1
        results["peer_ips"] = peer_ips
        results["cluster_hint"] = cluster_hint
        self.bus.publish(
            "skill.infra.peering",
            {"ip": ip, "peer_count": len(peer_ips), "cluster": cluster_hint},
            source="core.monitor",
        )
        return results

    def probe_reverse_proxy(self, ip: str) -> dict[str, Any]:
        """Collect Server / X-Forwarded-* headers for stealth tuning."""
        endpoints = [
            f"http://{ip}/",
            f"http://{ip}:8080/",
            f"https://{ip}/",
        ]
        collected = [self._http_probe(u) for u in endpoints]
        stealth_recommendations: list[str] = []
        for probe in collected:
            hints = probe.get("proxy_hints", {})
            server = hints.get("server", "")
            if "nginx" in server.lower():
                stealth_recommendations.append(
                    f"Match nginx front — set HEXSTRIKE_PROXY User-Agent pool to browser-like"
                )
            if "x-forwarded-for" in hints:
                stealth_recommendations.append(
                    "Upstream uses X-Forwarded-For — consider matching internal hop headers in core.stealth"
                )
        return {"probes": collected, "stealth_recommendations": stealth_recommendations}

    def trace(
        self,
        target_ip: str,
        *,
        mode: str = "deep-osint",
        wallet_address: str | None = None,
    ) -> dict[str, Any]:
        """Full infrastructure trace — passive only."""
        started = datetime.now(tz=timezone.utc).isoformat()
        self.out_dir.mkdir(parents=True, exist_ok=True)

        port_scan = []
        for port in (22, 80, 443, 8080, 8545, 8546, 30303):
            try:
                t0 = time.perf_counter()
                with socket.create_connection((target_ip, port), timeout=2.0):
                    port_scan.append({"port": port, "open": True, "latency_ms": round((time.perf_counter() - t0) * 1000, 1)})
            except OSError:
                port_scan.append({"port": port, "open": False})

        jenkins = self.probe_jenkins_surface(target_ip)
        peering = self.probe_geth_peering(target_ip)
        proxy = self.probe_reverse_proxy(target_ip)

        forensics_block: dict[str, Any] = {}
        if wallet_address:
            forensics_block = {"wallet": wallet_address, "note": "Correlate via orchestrator run_analyze"}

        report = {
            "operation": "trace-infra",
            "mode": mode,
            "target_ip": target_ip,
            "started_at": started,
            "finished_at": datetime.now(tz=timezone.utc).isoformat(),
            "policy": "read_only_osint_no_cve_exploit",
            "port_scan": port_scan,
            "jenkins": jenkins,
            "geth_peering": peering,
            "reverse_proxy": proxy,
            "forensics_correlation": forensics_block,
            "operator_watchlist": {
                "jenkins_credentials_found": False,
                "jenkins_config_found": False,
                "peer_cluster_detected": peering.get("cluster_hint", False),
                "proxy_headers_detected": any(
                    p.get("proxy_hints") for p in proxy.get("probes", [])
                ),
            },
        }
        self.bus.publish("skill.infra.complete", {"ip": target_ip}, source="skill.recon_osint")
        return report
