"""Vector B — passive P2P / enode surface recon (no exploit)."""

from __future__ import annotations

import random
import socket
import time
from dataclasses import dataclass, field
from typing import Any

from hexstrike.bus.context_bus import ContextBus


@dataclass
class EnodeCrawlSkill:
    """Map devp2p surface on :30303 — connection probe only (full crawl needs devp2p stack)."""

    bus: ContextBus
    connect_timeout: float = 4.0

    def _pause(self) -> None:
        time.sleep(random.uniform(0.5, 1.5))

    def probe_p2p_port(self, ip: str, port: int = 30303) -> dict[str, Any]:
        self._pause()
        result: dict[str, Any] = {"ip": ip, "port": port, "protocol": "devp2p"}
        try:
            t0 = time.perf_counter()
            with socket.create_connection((ip, port), timeout=self.connect_timeout) as sock:
                sock.settimeout(2.0)
                result["tcp_open"] = True
                result["connect_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                try:
                    banner = sock.recv(1024)
                    result["initial_bytes_hex"] = banner[:64].hex() if banner else ""
                    result["banner_length"] = len(banner)
                except socket.timeout:
                    result["initial_bytes_hex"] = ""
                    result["note"] = "TCP open — devp2p handshake requires RLPx initiator (use geth devp2p tools for peer list)"
        except OSError as exc:
            result["tcp_open"] = False
            result["error"] = str(exc)

        self.bus.publish("skill.enode.probe", result, source="skill.enode_crawl")
        return result

    def crawl(self, ip: str, ports: list[int] | None = None) -> dict[str, Any]:
        ports = ports or [30303, 30304, 8545]
        probes = [self.probe_p2p_port(ip, p) for p in ports]
        cluster_hint = sum(1 for p in probes if p.get("tcp_open")) >= 2
        report = {
            "vector": "B_network_recon",
            "target_ip": ip,
            "policy": "passive_tcp_probe_no_rlpx_injection",
            "probes": probes,
            "cluster_hint": cluster_hint,
            "peer_ips_discovered": [],
            "limitation": (
                "Full enode peer list requires authorized devp2p dial (geth devp2p discv4). "
                "Not executed automatically to avoid IDS triggers."
            ),
            "next_steps": [
                "Run discv4 ping from authorized lab with rate limit",
                "Cross-reference discovered enodes with chain analytics",
            ],
        }
        self.bus.publish("skill.enode.crawl_complete", {"ip": ip}, source="skill.enode_crawl")
        return report
