#!/usr/bin/env python3
"""Autonomous mempool monitor: master_context + RAG + unified indexer integration."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Bootstrap src/ package (production architecture)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from hexstrike.compat.bootstrap import bootstrap_paths
from hexstrike.instructions import load_instruction
from hexstrike.integrations.rpc_client import StealthRpcClient

bootstrap_paths()

import requests

from context_utils import load_master_context
from api_auth import api_headers, get_api_key, hexstrike_handshake, load_dotenv
from crypto_rpc_orchestrator import (
    iter_txpool_txs,
    load_config,
    normalize_addr,
    rpc_with_fallback,
)
from rag_core import (
    RagStorageError,
    index_false_positive,
    is_false_positive_pattern,
    search_history,
)

# Agent instruction protocol — base system prompt for monitor client
MONITOR_AGENT_ID = "core.monitor"
MONITOR_SYSTEM_PROMPT = load_instruction(MONITOR_AGENT_ID)

DEFAULT_CONFIG = ROOT / "config" / "rpc_config.json"
ALERTS_LOG = ROOT / "artifacts" / "alerts.log"
FEEDBACK_FILE = ROOT / "artifacts" / "alerts_feedback.txt"
DESKTOP_ALERT = Path.home() / "Desktop" / "on-chain-forensics" / "latest-alert.json"
EVA_ALERT = Path("/Volumes/Eva/alerts/latest-alert.json")
STATE_FILE = ROOT / "artifacts" / "monitor" / "autonomous_state.json"
PENDING_ACTION = ROOT / "artifacts" / "pending_action.json"

HOT_WALLET = normalize_addr(
    os.environ.get("TARGET_WALLET", "0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA")
)
HEARTBEAT_EVERY_POLLS = int(os.environ.get("MONITOR_HEARTBEAT_POLLS", "30"))
BLOCK_SCAN_EVERY_POLLS = int(os.environ.get("MONITOR_BLOCK_SCAN_POLLS", "60"))

# Known bridge/sink addresses from prior investigations
SINK_KEYWORDS = ("bridge", "rhino", "sink", "offramp", "swap")
HIGH_RISK_LABELS = ("bridge", "sink", "rhino", "hot_wallet", "authority")
ADDR_RE = re.compile(r"0x[a-fA-F0-9]{40}")

RECONNECT_DELAY = 5.0
INDEXER_COOLDOWN_SEC = 60
DEDUP_WINDOW_SEC = 20 * 60
IGNORE_RE = re.compile(r"^IGNORE:\s*(0x[a-fA-F0-9]{64})", re.IGNORECASE)

SEVERITY_INFO = "INFO"
SEVERITY_WARN = "WARN"
SEVERITY_CRITICAL = "CRITICAL"
LOGGED_SEVERITIES = frozenset({SEVERITY_WARN, SEVERITY_CRITICAL})


def load_feedback_ignored(state: dict[str, Any]) -> set[str]:
    """Parse alerts_feedback.txt for IGNORE tx hashes."""
    ignored = {h.lower() for h in state.get("feedback_ignored", [])}
    if not FEEDBACK_FILE.is_file():
        return ignored
    for line in FEEDBACK_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = IGNORE_RE.match(line)
        if match:
            ignored.add(match.group(1).lower())
    return ignored


def lookup_tx_in_alerts(tx_hash: str) -> dict[str, Any] | None:
    if not ALERTS_LOG.is_file():
        return None
    target = tx_hash.lower()
    for line in ALERTS_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (record.get("hash") or "").lower() == target:
            return record
    return None


def process_feedback_file(state: dict[str, Any]) -> dict[str, Any]:
    """Index new IGNORE entries into RAG as false_positive."""
    if not FEEDBACK_FILE.is_file():
        return state

    processed = set(state.get("feedback_processed", []))
    newly_indexed = 0

    for line in FEEDBACK_FILE.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if raw in processed:
            continue
        match = IGNORE_RE.match(raw)
        if not match:
            continue

        tx_hash = match.group(1).lower()
        note = raw.split("#", 1)[1].strip() if "#" in raw else ""
        alert = lookup_tx_in_alerts(tx_hash)
        frm = alert.get("from", "") if alert else ""
        to = alert.get("to", "") if alert else ""

        try:
            index_false_positive(tx_hash, frm, to, note or "operator ignore feedback")
            newly_indexed += 1
            processed.add(raw)
            print(f"[feedback] Indexed false_positive: {tx_hash}")
        except (RagStorageError, OSError, ImportError) as exc:
            print(f"[feedback] WARN — could not index {tx_hash}: {exc}")

    state["feedback_processed"] = list(processed)[-5000:]
    state["feedback_ignored"] = list(load_feedback_ignored(state))
    if newly_indexed:
        state["feedback_last_indexed"] = datetime.now(tz=timezone.utc).isoformat()
    return state


def resolve_hexstrike_api(cfg: dict[str, Any]) -> tuple[str, str]:
    """Resolve server URL and API key from config + environment."""
    load_dotenv()
    api_cfg = cfg.get("hexstrike_api", {})
    server = api_cfg.get("server", "http://127.0.0.1:8888")
    env_name = api_cfg.get("api_key_env", "HEXSTRIKE_API_KEY")
    api_key = api_cfg.get("api_key") or os.environ.get(env_name, "") or get_api_key()
    return server, api_key.strip()


def api_handshake(cfg: dict[str, Any]) -> dict[str, Any]:
    server, api_key = resolve_hexstrike_api(cfg)
    result = hexstrike_handshake(server, api_key)
    result["server"] = server
    return result


def fetch_context_via_api(cfg: dict[str, Any]) -> dict[str, Any] | None:
    server, api_key = resolve_hexstrike_api(cfg)
    headers = api_headers(api_key)
    if not headers:
        return None
    try:
        resp = requests.get(f"{server.rstrip('/')}/api/context/latest", headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        body = resp.json()
        return body.get("context") or body
    except requests.RequestException:
        return None


def extract_addresses(obj: Any, found: dict[str, set[str]] | None = None, label: str = "") -> dict[str, set[str]]:
    """Recursively collect Ethereum addresses from nested JSON."""
    if found is None:
        found = {"all": set(), "labeled": set()}

    if isinstance(obj, dict):
        for key, val in obj.items():
            key_lower = str(key).lower()
            child_label = key_lower if any(k in key_lower for k in HIGH_RISK_LABELS) else label
            if isinstance(val, str) and ADDR_RE.fullmatch(val):
                addr = normalize_addr(val)
                found["all"].add(addr)
                if child_label:
                    found["labeled"].add(addr)
            else:
                extract_addresses(val, found, child_label)
    elif isinstance(obj, list):
        for item in obj:
            extract_addresses(item, found, label)
    elif isinstance(obj, str):
        for match in ADDR_RE.findall(obj):
            found["all"].add(normalize_addr(match))

    return found


def load_watched_addresses(config: dict[str, Any]) -> dict[str, Any]:
    """Build watchlist from master_context.json + rpc_config monitoring targets."""
    watched: set[str] = set()
    sinks: set[str] = set()
    sources: list[str] = []

    ctx = fetch_context_via_api(config) or load_master_context()
    if ctx:
        sources.append("master_context.json")
        for entry in ctx.get("entries", []):
            data = entry.get("data", entry)
            extracted = extract_addresses(data)
            watched.update(extracted["all"])
            sinks.update(extracted["labeled"])

    mon = config.get("monitoring", {})
    for addr in mon.get("target_contracts", []):
        watched.add(normalize_addr(addr))
        sources.append("rpc_config.monitoring.target_contracts")

    # Explicit sinks from forensics knowledge base
    for addr in (
        "0xb80a582fa430645a043bb4f6135321ee01005fef",  # Rhino.fi
        "0x4943f5e7f4e450d48ae82026163ecde8a52c53da",  # hot wallet
        "0x730ea0231808f42a20f8921ba7fbc788226768f5",  # authority
    ):
        norm = normalize_addr(addr)
        watched.add(norm)
        sinks.add(norm)

    return {
        "watched": watched,
        "sinks": sinks,
        "sources": sources,
    }


def tx_context_hits(tx: dict[str, Any], watched: set[str]) -> list[str]:
    frm = normalize_addr(tx.get("from"))
    to = normalize_addr(tx.get("to"))
    hits = []
    if frm in watched:
        hits.append(f"from:{frm}")
    if to in watched:
        hits.append(f"to:{to}")
    return hits


def is_high_risk(tx: dict[str, Any], sinks: set[str]) -> tuple[bool, str]:
    frm = normalize_addr(tx.get("from"))
    to = normalize_addr(tx.get("to"))
    if to in sinks:
        return True, "interaction_with_known_sink"
    if frm in sinks:
        return True, "funds_from_known_sink"
    input_lower = (tx.get("input") or "").lower()
    if any(kw in input_lower for kw in SINK_KEYWORDS):
        return True, "calldata_bridge_keyword"
    return False, ""


def rag_lookup(tx: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    """Search RAG history; return hits and whether pattern looks unknown."""
    frm = tx.get("from", "")
    to = tx.get("to", "")
    query = (
        f"on-chain transaction from {frm} to {to} "
        f"bridge sink rhino offramp pattern history"
    )
    try:
        hits = search_history(query, top_k=3)
    except (RagStorageError, OSError, ImportError) as exc:
        return [], True

    if not hits:
        return [], True

    combined = " ".join(h.get("snippet", "") for h in hits).lower()
    frm_l = normalize_addr(frm)
    to_l = normalize_addr(to)
    known = frm_l in combined or to_l in combined or "rhino" in combined or "bridge" in combined
    # LanceDB cosine distance: lower = more similar
    best_score = min((h.get("score") or 1.0) for h in hits)
    unknown = not known or best_score > 0.85
    return hits, unknown


def pair_key(frm: str, to: str) -> str:
    return f"{normalize_addr(frm)}:{normalize_addr(to)}"


def prune_dedup_pairs(pairs: dict[str, float], now: float | None = None) -> dict[str, float]:
    """Drop from+to pairs older than DEDUP_WINDOW_SEC."""
    cutoff = (now or time.time()) - DEDUP_WINDOW_SEC
    return {key: ts for key, ts in pairs.items() if ts >= cutoff}


def is_deduped_pair(frm: str, to: str, pairs: dict[str, float]) -> bool:
    key = pair_key(frm, to)
    last_seen = pairs.get(key)
    if last_seen is None:
        return False
    return (time.time() - last_seen) < DEDUP_WINDOW_SEC


def record_dedup_pair(frm: str, to: str, pairs: dict[str, float]) -> dict[str, float]:
    pairs = prune_dedup_pairs(pairs)
    pairs[pair_key(frm, to)] = time.time()
    return pairs


def classify_severity(high_risk: bool, risk_reason: str, unknown_pattern: bool) -> str:
    if risk_reason == "interaction_with_known_sink":
        return SEVERITY_CRITICAL
    if high_risk and unknown_pattern:
        return SEVERITY_CRITICAL
    if high_risk or unknown_pattern:
        return SEVERITY_WARN
    return SEVERITY_INFO


def write_alert(alert: dict[str, Any]) -> None:
    severity = alert.get("severity", SEVERITY_WARN)
    payload = json.dumps(alert, indent=2, ensure_ascii=False) + "\n"

    if severity in LOGGED_SEVERITIES:
        ALERTS_LOG.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(alert, ensure_ascii=False)
        with ALERTS_LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

        DESKTOP_ALERT.parent.mkdir(parents=True, exist_ok=True)
        DESKTOP_ALERT.write_text(payload, encoding="utf-8")

        if EVA_ALERT.parent.parent.exists():
            EVA_ALERT.parent.mkdir(parents=True, exist_ok=True)
            EVA_ALERT.write_text(payload, encoding="utf-8")

        pending = {
            "status": "awaiting_operator_review",
            "created_at": alert.get("timestamp"),
            "alert_type": alert.get("alert_type"),
            "severity": severity,
            "message": alert.get("message"),
            "transaction": {
                "hash": alert.get("hash"),
                "from": alert.get("from"),
                "to": alert.get("to"),
                "value": alert.get("value"),
                "pool": alert.get("pool"),
            },
            "rag_context": alert.get("rag_hits", [])[:2],
            "recommended_actions": (
                [
                    "IR TRIGGER: verify hot wallet outflow authorization",
                    "If unauthorized: execute rescue owner protocol (INCIDENT-CONCLUSION.md)",
                    "Contain Jenkins/RPC/signing service immediately",
                ]
                if alert.get("ir_trigger")
                else [
                    "Review alert in artifacts/alerts.log",
                    "Cross-check RAG snippets against master_context.json",
                    "Manual decision required — no auto-broadcast",
                ]
            ),
        }
        PENDING_ACTION.write_text(json.dumps(pending, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def trigger_indexer() -> dict[str, Any]:
    script = ROOT / "scripts" / "unified_indexer.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def load_state() -> dict[str, Any]:
    if not STATE_FILE.is_file():
        return {"seen_hashes": [], "last_indexer_run": 0, "dedup_pairs": {}}
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"seen_hashes": [], "last_indexer_run": 0, "dedup_pairs": {}}
    state.setdefault("dedup_pairs", {})
    state["dedup_pairs"] = prune_dedup_pairs(state["dedup_pairs"])
    return state


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _tx_outflow_value_wei(tx: dict[str, Any]) -> int:
    raw = tx.get("value") or "0x0"
    if isinstance(raw, int):
        return max(raw, 0)
    if isinstance(raw, str):
        try:
            return int(raw, 16)
        except ValueError:
            return 0
    return 0


def _tx_has_contract_call(tx: dict[str, Any]) -> bool:
    inp = (tx.get("input") or "0x").strip().lower()
    return len(inp) > 2


def is_hot_wallet_outflow(tx: dict[str, Any]) -> bool:
    """Pending tx signed from hot wallet with value or contract call (IR trigger candidate)."""
    frm = normalize_addr(tx.get("from"))
    to = normalize_addr(tx.get("to"))
    if frm != HOT_WALLET:
        return False
    if not to or to == frm:
        return False
    return _tx_outflow_value_wei(tx) > 0 or _tx_has_contract_call(tx)


def process_transaction(
    tx: dict[str, Any],
    watched: set[str],
    sinks: set[str],
    rpc_url: str,
    ignored_hashes: set[str] | None = None,
) -> dict[str, Any] | None:
    tx_hash = (tx.get("hash") or "").lower()
    if ignored_hashes and tx_hash in ignored_hashes:
        return None

    if is_hot_wallet_outflow(tx):
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "alert_type": "HOT_WALLET_OUTFLOW",
            "severity": SEVERITY_CRITICAL,
            "ir_trigger": True,
            "message": (
                f"IR TRIGGER: pending outflow from hot wallet {HOT_WALLET} "
                f"-> {tx.get('to')} (review immediately; possible unauthorized signing)"
            ),
            "rpc": rpc_url,
            "pool": tx.get("pool", "pending"),
            "hash": tx.get("hash"),
            "from": tx.get("from"),
            "to": tx.get("to"),
            "value": tx.get("value"),
            "context_hits": [f"from:{HOT_WALLET}"],
            "high_risk": True,
            "risk_reason": "hot_wallet_pending_outflow",
            "unknown_pattern": True,
            "rag_hits": [],
        }

    hits = tx_context_hits(tx, watched)
    if not hits:
        return None

    fp_match, fp_hits = is_false_positive_pattern(
        tx_hash, tx.get("from", ""), tx.get("to", "")
    )
    if fp_match:
        print(f"[feedback] Suppressed alert (false_positive RAG): {tx_hash}")
        return None

    high_risk, risk_reason = is_high_risk(tx, sinks)
    rag_hits, unknown_pattern = rag_lookup(tx)

    if not (high_risk or unknown_pattern):
        return None

    alert_type = "HIGH_RISK_REPEAT" if rag_hits and not unknown_pattern else "HIGH_RISK_UNKNOWN"
    if high_risk and rag_hits and not unknown_pattern:
        message = (
            f"Pattern match: {tx.get('from')} -> {tx.get('to')} "
            f"matches prior documentation ({risk_reason})."
        )
    elif high_risk:
        message = f"HIGH RISK: {risk_reason} — {tx.get('from')} -> {tx.get('to')}"
    else:
        message = f"UNKNOWN pattern: {tx.get('from')} -> {tx.get('to')} — not in RAG history"

    severity = classify_severity(high_risk, risk_reason, unknown_pattern)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "alert_type": alert_type,
        "severity": severity,
        "message": message,
        "rpc": rpc_url,
        "pool": tx.get("pool"),
        "hash": tx.get("hash"),
        "from": tx.get("from"),
        "to": tx.get("to"),
        "value": tx.get("value"),
        "context_hits": hits,
        "high_risk": high_risk,
        "risk_reason": risk_reason,
        "unknown_pattern": unknown_pattern,
        "rag_hits": rag_hits,
    }


def _fetch_txpool(config_path: Path, endpoints: list[str], timeout: float) -> tuple[str, dict[str, Any]]:
    """Fetch txpool via stealth RPC (default) or legacy fallback."""
    if os.environ.get("HEXSTRIKE_STEALTH", "1") != "0":
        client = StealthRpcClient(config_path)
        return client.call("txpool_content", [], timeout=timeout)
    return rpc_with_fallback(endpoints, "txpool_content", [], timeout=timeout)


def _scan_latest_block_hot_outflows(
    config_path: Path, endpoints: list[str], timeout: float, seen_hashes: set[str]
) -> list[dict[str, Any]]:
    """Fallback: mined txs from hot wallet (Flashbots/private mempool blind spot)."""
    try:
        if os.environ.get("HEXSTRIKE_STEALTH", "1") != "0":
            client = StealthRpcClient(config_path)
            _, block_resp = client.call("eth_getBlockByNumber", ["latest", True], timeout=timeout)
        else:
            _, block_resp = rpc_with_fallback(
                endpoints, "eth_getBlockByNumber", ["latest", True], timeout=timeout
            )
        block = (block_resp.get("result") or {}) if isinstance(block_resp, dict) else {}
        out: list[dict[str, Any]] = []
        for tx in block.get("transactions") or []:
            if not isinstance(tx, dict):
                continue
            tx_hash = (tx.get("hash") or "").lower()
            if not tx_hash or tx_hash in seen_hashes:
                continue
            if normalize_addr(tx.get("from")) != HOT_WALLET:
                continue
            tx_copy = dict(tx)
            tx_copy["pool"] = "mined_latest_block"
            out.append(tx_copy)
        return out
    except Exception as exc:  # noqa: BLE001
        print(f"[block-scan] WARN: {exc}")
        return []


def run_monitor(
    config_path: Path,
    poll_interval: float = 1.0,
    timeout: float = 8.0,
    duration_seconds: int | None = None,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    endpoints = [cfg["primary"], *cfg.get("fallbacks", [])]
    poll_interval = float(cfg.get("monitoring", {}).get("poll_interval_seconds", poll_interval))

    handshake = api_handshake(cfg)
    if handshake.get("success"):
        print(f"[handshake] OK — {handshake['server']} (entries={handshake.get('data', {}).get('entry_count', '?')})")
    else:
        print(f"[handshake] WARN — {handshake.get('error')} (falling back to local context files)")

    watch = load_watched_addresses(cfg)
    watched = watch["watched"]
    sinks = watch["sinks"]

    state = load_state()
    state = process_feedback_file(state)
    ignored_hashes = load_feedback_ignored(state)
    seen_hashes: set[str] = set(state.get("seen_hashes", []))
    last_indexer_run = float(state.get("last_indexer_run", 0))
    dedup_pairs: dict[str, float] = dict(state.get("dedup_pairs", {}))

    print(f"[monitor] RPC primary: {cfg['primary']}")
    print(f"[agent] {MONITOR_AGENT_ID} instructions loaded ({len(MONITOR_SYSTEM_PROMPT)} bytes from monitor.md)")
    print(f"[monitor] Watching {len(watched)} addresses | sinks={len(sinks)}")
    print(f"[monitor] Context sources: {', '.join(watch['sources']) or 'rpc_config only'}")
    print(f"[monitor] Feedback ignores: {len(ignored_hashes)} tx hashes")
    print(f"[monitor] Alerts log: {ALERTS_LOG}")
    print(f"[monitor] Desktop alert: {DESKTOP_ALERT}")
    stealth_on = os.environ.get("HEXSTRIKE_STEALTH", "1") != "0"
    print(f"[monitor] Stealth transport: {'on' if stealth_on else 'off'}")
    print(f"[monitor] HOT_WALLET IR trigger: {HOT_WALLET}")
    print(f"[monitor] Heartbeat every {HEARTBEAT_EVERY_POLLS} polls | block-scan every {BLOCK_SCAN_EVERY_POLLS} polls")

    start = time.time()
    polls = 0
    alerts_count = 0
    dedup_skipped = 0
    txs_seen = 0
    active_rpc = cfg["primary"]

    while True:
        polls += 1
        state = process_feedback_file(state)
        ignored_hashes = load_feedback_ignored(state)

        poll_started = time.time()
        try:
            active_rpc, resp = _fetch_txpool(config_path, endpoints, timeout)
            content = resp.get("result") or {}
            poll_latency_ms = round((time.time() - poll_started) * 1000, 1)
        except Exception as exc:
            print(f"[warn] RPC error (poll {polls}): {exc} — reconnect in {RECONNECT_DELAY}s")
            time.sleep(RECONNECT_DELAY)
            if duration_seconds and time.time() - start >= duration_seconds:
                break
            continue

        if polls == 1 or polls % HEARTBEAT_EVERY_POLLS == 0:
            pending_n = sum(
                1 for _ in iter_txpool_txs(content)
            )
            print(
                f"[heartbeat] poll={polls} rpc={active_rpc} "
                f"latency_ms={poll_latency_ms} pending_txs={pending_n} "
                f"seen_total={txs_seen} alerts={alerts_count}"
            )

        block_txs: list[dict[str, Any]] = []
        if polls % BLOCK_SCAN_EVERY_POLLS == 0:
            block_txs = _scan_latest_block_hot_outflows(
                config_path, endpoints, timeout, seen_hashes
            )

        for tx in list(iter_txpool_txs(content)) + block_txs:
            tx_hash = tx.get("hash")
            if not tx_hash or tx_hash in seen_hashes:
                continue
            seen_hashes.add(tx_hash)
            txs_seen += 1

            alert = process_transaction(tx, watched, sinks, active_rpc, ignored_hashes)
            if not alert:
                continue

            if is_deduped_pair(alert.get("from", ""), alert.get("to", ""), dedup_pairs):
                dedup_skipped += 1
                print(f"[dedup] Skipped {tx_hash} — pair seen in last {DEDUP_WINDOW_SEC // 60}m")
                continue

            alerts_count += 1
            dedup_pairs = record_dedup_pair(alert.get("from", ""), alert.get("to", ""), dedup_pairs)
            write_alert(alert)
            print(f"[ALERT] [{alert.get('severity', '?')}] {alert['alert_type']} {tx_hash}")
            print(f"        {alert['message']}")
            if alert.get("rag_hits"):
                top = alert["rag_hits"][0]
                print(f"        RAG: {top.get('source_file')} (score={top.get('score')})")

            now = time.time()
            if now - last_indexer_run >= INDEXER_COOLDOWN_SEC:
                idx = trigger_indexer()
                last_indexer_run = now
                print(f"[indexer] unified_indexer exit={idx['returncode']}")

        if polls % 10 == 0:
            save_state({
                "seen_hashes": list(seen_hashes)[-10000:],
                "last_indexer_run": last_indexer_run,
                "last_poll": polls,
                "rpc": active_rpc,
                "dedup_pairs": prune_dedup_pairs(dedup_pairs),
                "feedback_processed": state.get("feedback_processed", []),
                "feedback_ignored": list(ignored_hashes),
            })

        if duration_seconds and time.time() - start >= duration_seconds:
            break
        time.sleep(poll_interval)

    save_state({
        "seen_hashes": list(seen_hashes)[-10000:],
        "last_indexer_run": last_indexer_run,
        "last_poll": polls,
        "rpc": active_rpc,
        "dedup_pairs": prune_dedup_pairs(dedup_pairs),
        "feedback_processed": state.get("feedback_processed", []),
        "feedback_ignored": list(ignored_hashes),
    })

    return {
        "polls": polls,
        "txs_seen": txs_seen,
        "alerts": alerts_count,
        "dedup_skipped": dedup_skipped,
        "duration_sec": round(time.time() - start, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Autonomous mempool monitor with RAG + unified context")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--duration", type=int, default=None, help="Run N seconds then exit (default: infinite)")
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()

    try:
        summary = run_monitor(
            Path(args.config),
            timeout=args.timeout,
            duration_seconds=args.duration,
        )
    except KeyboardInterrupt:
        print("\n[monitor] stopped by user")
        return 0

    print(json.dumps({"success": True, **summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
