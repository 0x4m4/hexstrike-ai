"""chain_tracer — recipient depth analysis and entity resolution."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from hexstrike.bus.context_bus import ContextBus
from hexstrike.core.forensics.engine import ForensicsEngine
from hexstrike.paths import MASTER_CONTEXT, ROOT

sys_path = ROOT / "scripts"
import sys  # noqa: E402

sys.path.insert(0, str(sys_path))
from context_utils import load_master_context  # noqa: E402

ETH = re.compile(r"0x[a-fA-F0-9]{40}")


@dataclass
class ChainTracerSkill:
    """Multichain recipient depth traversal with entity labels."""

    bus: ContextBus
    forensics: ForensicsEngine
    max_depth: int = 3

    def _related_from_context(self, root: str, limit: int = 5) -> list[str]:
        root = root.lower()
        related: list[str] = []
        ctx = load_master_context(MASTER_CONTEXT) or {}
        for entry in ctx.get("entries", []):
            blob = json.dumps(entry.get("data", entry), default=str).lower()
            if root not in blob:
                continue
            for addr in ETH.findall(blob):
                a = addr.lower()
                if a != root and a not in related:
                    related.append(a)
                if len(related) >= limit:
                    return related
        return related

    def trace(self, root_address: str, depth: int | None = None) -> dict[str, Any]:
        depth = min(depth or self.max_depth, self.max_depth)
        entity = self.forensics.resolve_entity(root_address)
        graph: dict[str, Any] = {
            "root": root_address.lower(),
            "depth": depth,
            "nodes": [{**entity, "level": 0}],
            "edges": [],
            "gas_pattern_analysis": {
                "status": "heuristic",
                "note": "Cluster recipients by gas_price tier and nonce velocity",
            },
        }

        related = self._related_from_context(root_address, limit=depth * 2)
        for hop, addr in enumerate(related[:depth], start=1):
            hop_entity = self.forensics.resolve_entity(addr)
            node = {**hop_entity, "level": hop, "address": addr}
            graph["nodes"].append(node)
            graph["edges"].append({
                "from": root_address.lower(),
                "to": addr,
                "hop": hop,
                "source": "master_context",
            })

        if len(graph["nodes"]) == 1:
            for hop in range(1, depth + 1):
                node = {
                    "address": f"hop_{hop}_unresolved",
                    "level": hop,
                    "labels": ["pending_blockscout_worker"],
                }
                graph["nodes"].append(node)
                graph["edges"].append({"from": root_address.lower(), "to": node["address"], "hop": hop})

        self.bus.publish("skill.chain_tracer.result", graph, source="chain_tracer")
        return graph
