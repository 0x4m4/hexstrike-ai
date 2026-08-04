#!/usr/bin/env python3
"""Read-only Arkham API client (api.arkm.com). Defensive / IR use only."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_BASE = os.environ.get("ARKHAM_API_BASE", "https://api.arkm.com").rstrip("/")
DEFAULT_CHAIN = os.environ.get("ARKHAM_CHAIN", "bsc")
DEFAULT_CHAINS = os.environ.get("ARKHAM_CHAINS", "ethereum,bsc,polygon,base,arbitrum")


class ArkhamError(Exception):
    pass


def _api_key() -> str:
    return (os.environ.get("ARKHAM_API_KEY") or "").strip()


def _request(path: str, params: dict[str, str] | None = None, timeout: int = 15) -> dict[str, Any]:
    key = _api_key()
    if not key:
        raise ArkhamError("ARKHAM_API_KEY not set")

    query = f"?{urllib.parse.urlencode(params)}" if params else ""
    url = f"{DEFAULT_BASE}{path}{query}"
    req = urllib.request.Request(
        url,
        headers={"API-Key": key, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise ArkhamError(f"HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise ArkhamError(f"transport error: {e}") from e


def get_address_balances(address: str, chains: str | None = None) -> dict[str, Any]:
    """GET /balances/address/{address} — multichain token balances."""
    addr = address.lower().strip()
    params = {}
    if chains:
        params["chains"] = chains
    return _request(f"/balances/address/{addr}", params or None)


def get_credit_periods() -> list[dict[str, Any]]:
    """GET /analytics/credit-periods — last 12 billing periods of API credit usage."""
    payload = _request("/analytics/credit-periods")
    if isinstance(payload, list):
        return payload
    return payload.get("periods") or payload.get("data") or []


def health_check() -> tuple[bool, str]:
    """GET /health — lightweight availability probe (no API key)."""
    url = f"{DEFAULT_BASE}/health"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace").strip()
            return True, body or "ok"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return False, f"transport: {e}"


def get_address_enriched(address: str, chain: str | None = None) -> dict[str, Any]:
    """GET /intelligence/address_enriched/{address} — entity, label, tags."""
    addr = address.lower().strip()
    params = {
        "chain": chain or DEFAULT_CHAIN,
        "includeTags": "true",
        "includeEntityPredictions": "false",
        "includeClusters": "false",
    }
    return _request(f"/intelligence/address_enriched/{addr}", params)


def summarize_intel(payload: dict[str, Any]) -> dict[str, Any]:
    entity = payload.get("arkhamEntity") or {}
    label = payload.get("arkhamLabel") or {}
    tags = payload.get("tags") or []
    return {
        "address": payload.get("address"),
        "chain": payload.get("chain"),
        "entity_id": entity.get("id"),
        "entity_name": entity.get("name"),
        "entity_type": entity.get("type"),
        "label": label.get("name"),
        "contract": payload.get("contract"),
        "tag_count": len(tags),
        "tags": [t.get("name") or t.get("slug") for t in tags[:10]],
    }


def summarize_balances(payload: dict[str, Any]) -> dict[str, Any]:
    balances = payload.get("balances") or payload.get("data") or payload
    if isinstance(balances, list):
        top = sorted(
            balances,
            key=lambda x: float(x.get("usd") or x.get("usdValue") or 0),
            reverse=True,
        )[:10]
        return {
            "balance_count": len(balances),
            "top_holdings": [
                {
                    "symbol": b.get("symbol") or b.get("name"),
                    "usd": b.get("usd") or b.get("usdValue"),
                    "chain": b.get("chain"),
                }
                for b in top
            ],
        }
    return {"raw_keys": list(payload.keys()) if isinstance(payload, dict) else str(type(payload))}
