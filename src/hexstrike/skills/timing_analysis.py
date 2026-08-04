"""skill.timing_analysis — RPC latency profiling for gas-war positioning."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Any

from hexstrike.bus.context_bus import ContextBus
from hexstrike.integrations.rpc_client import StealthRpcClient
from hexstrike.paths import RPC_CONFIG


@dataclass
class TimingAnalysisSkill:
    """Measure per-endpoint RPC delay to pick lowest-latency node for competitive txs."""

    bus: ContextBus
    config_path: Any = RPC_CONFIG
    samples: int = 3

    def profile_endpoints(self) -> list[dict[str, Any]]:
        client = StealthRpcClient(self.config_path)
        results: list[dict[str, Any]] = []

        for url in client.endpoints():
            latencies: list[float] = []
            ok = 0
            for _ in range(self.samples):
                t0 = time.perf_counter()
                try:
                    client.transport.rpc_call(url, "eth_chainId", [], timeout=6.0)
                    latencies.append((time.perf_counter() - t0) * 1000)
                    ok += 1
                except Exception:
                    continue

            entry = {
                "endpoint": url,
                "samples_ok": ok,
                "latency_ms_avg": round(statistics.mean(latencies), 2) if latencies else None,
                "latency_ms_p95": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 2) if latencies else None,
                "gas_war_rank": None,
            }
            results.append(entry)

        ranked = sorted(
            [r for r in results if r["latency_ms_avg"] is not None],
            key=lambda x: x["latency_ms_avg"],
        )
        for i, row in enumerate(ranked, start=1):
            row["gas_war_rank"] = i

        self.bus.publish(
            "skill.timing.profile",
            {"endpoints": len(results), "best": ranked[0]["endpoint"] if ranked else None},
            source="skill.timing_analysis",
        )
        return results

    def recommend_endpoint(self) -> dict[str, Any]:
        profile = self.profile_endpoints()
        best = next((p for p in profile if p.get("gas_war_rank") == 1), None)
        return best or {"error": "no_reachable_endpoints", "profile": profile}
