"""Load wallet targets from HexStrike artifacts for multi-wallet recon."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts"


@dataclass
class WalletTarget:
    role: str
    address: str
    chain: str = "BSC"
    chain_id: int = 56
    priority: int = 99
    labels: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    def normalized_address(self) -> str:
        return self.address.lower()

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "address": self.address,
            "chain": self.chain,
            "chain_id": self.chain_id,
            "priority": self.priority,
            "labels": self.labels,
            "context": self.context,
        }


def _load(name: str) -> dict[str, Any]:
    p = ART / name
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _addr_ok(addr: str | None) -> bool:
    if not addr or not isinstance(addr, str):
        return False
    a = addr.strip()
    return a.startswith("0x") and len(a) == 42


DEFAULT_FIELD_TARGETS = ROOT / "scripts" / "sandbox" / "field-targets-5.json"


def _wallets_only_env() -> bool:
    return os.environ.get("WALLETS_ONLY", "").lower() in ("1", "true", "yes")


def _resolve_wallets_file() -> Path | None:
    raw = os.environ.get("WALLETS_FILE", "").strip()
    if not raw:
        if os.environ.get("ORCHESTRATOR_WORKFLOW") == "field-targets-5":
            return DEFAULT_FIELD_TARGETS
        return None
    p = Path(raw)
    if not p.is_absolute():
        p = ROOT / p
    return p if p.is_file() else None


def _parse_wallet_items(items: list[Any]) -> list[WalletTarget]:
    out: list[WalletTarget] = []
    for item in items:
        if isinstance(item, str) and _addr_ok(item):
            out.append(WalletTarget(role="custom", address=item, priority=50))
        elif isinstance(item, dict) and _addr_ok(item.get("address")):
            out.append(
                WalletTarget(
                    role=item.get("role", "custom"),
                    address=item["address"],
                    chain=item.get("chain", "BSC"),
                    chain_id=int(item.get("chain_id", 56)),
                    priority=int(item.get("priority", 50)),
                    labels=item.get("labels", {}),
                    context=item.get("context", {}),
                )
            )
    return out


def load_wallets_file(path: Path) -> tuple[list[WalletTarget], bool]:
    """Return wallets from JSON file and whether catalog should be exclusive."""
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("wallets", data if isinstance(data, list) else [])
    exclusive = bool(data.get("exclusive", False)) or _wallets_only_env()
    return _parse_wallet_items(items), exclusive


def extra_wallets_from_env() -> list[WalletTarget]:
    raw = os.environ.get("TARGET_WALLETS", "")
    out: list[WalletTarget] = []
    for part in raw.split(","):
        part = part.strip()
        if not _addr_ok(part):
            continue
        out.append(WalletTarget(role="custom", address=part, priority=50))
    return out


def load_wallet_catalog() -> list[WalletTarget]:
    wallets_file = _resolve_wallets_file()
    file_wallets: list[WalletTarget] = []
    exclusive = False
    if wallets_file:
        file_wallets, exclusive = load_wallets_file(wallets_file)
        if exclusive and file_wallets:
            file_wallets.sort(key=lambda w: (w.priority, w.role))
            return file_wallets

    infra = _load("infra-targets.json")
    entity = _load("entity-id.json")
    graph = _load("hot-wallet-onchain-graph.json")
    authority = _load("authority-contract-analysis.json")

    seeds: dict[str, str] = infra.get("seed_addresses", {}) or {}
    wallets: list[WalletTarget] = []
    seen: set[str] = set()

    def add(role: str, address: str | None, priority: int, **ctx: Any) -> None:
        if not _addr_ok(address):
            return
        key = address.lower()  # type: ignore[union-attr]
        if key in seen:
            return
        seen.add(key)
        wallets.append(
            WalletTarget(
                role=role,
                address=address,  # type: ignore[arg-type]
                priority=priority,
                context=ctx,
            )
        )

    add("hot_wallet", seeds.get("hot_wallet") or entity.get("target") or graph.get("hot_wallet"), 1,
        graph_summary={
            "usdt_out_txs": graph.get("usdt_out_txs"),
            "net_usdt_period": graph.get("net_usdt_period"),
        })
    add("authority", seeds.get("authority") or authority.get("address"), 2,
        classification=authority.get("classification"),
        eip7702=authority.get("delegation", {}).get("type"))
    add("primary_sink_hub", seeds.get("primary_sink_hub"), 3,
        label=infra.get("onchain_to_offchain_links", {}).get("bscscan_public_label_hub"))
    add("operator_local", seeds.get("operator_local"), 4, note="operator-controlled")
    add("puissant_validator", seeds.get("puissant_validator"), 5)

    for i, dest in enumerate((graph.get("top_destinations") or [])[:8]):
        add(f"counterparty_{i+1}", dest.get("address"), 10 + i,
            total_usdt=dest.get("total_usdt"), label=dest.get("label"))

    entity_target = entity.get("target")
    if _addr_ok(entity_target):
        add("entity_primary", entity_target, 6)

    for w in extra_wallets_from_env():
        key = w.normalized_address()
        if key not in seen:
            seen.add(key)
            wallets.append(w)

    if wallets_file and file_wallets and not exclusive:
        for w in file_wallets:
            key = w.normalized_address()
            if key not in seen:
                seen.add(key)
                wallets.append(w)

    wallets.sort(key=lambda w: (w.priority, w.role))
    return wallets
