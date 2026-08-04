#!/usr/bin/env python3
"""
Read-only Geth JSON-RPC orchestrator for operator lab / threat intel.

Modes:
  probe    — assess 18 Shodan :8545 nodes (default)
  monitor  — mempool watch via config/rpc_config.json + optional CEX correlation
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from context_utils import get_cex_cluster_payload, load_master_context

DEFAULT_CONFIG = ROOT / "config" / "rpc_config.json"

# 18 Geth :8545 hosts — SHODAN_ОТЧЕТ_2026-07-08.md §4.3
GETH_NODES: list[dict[str, str]] = [
    {"ip": "104.198.118.132", "org": "Google LLC", "country": "JP"},
    {"ip": "116.63.128.247", "org": "Huawei Cloud", "country": "CN"},
    {"ip": "173.255.192.47", "org": "Linode", "country": "US"},
    {"ip": "39.102.208.23", "org": "Aliyun", "country": "CN"},
    {"ip": "39.105.28.172", "org": "Aliyun", "country": "CN"},
    {"ip": "45.33.17.6", "org": "Linode", "country": "US"},
    {"ip": "45.56.71.62", "org": "Linode", "country": "US"},
    {"ip": "45.79.180.119", "org": "Linode", "country": "US"},
    {"ip": "45.79.221.99", "org": "Linode", "country": "US"},
    {"ip": "45.79.252.32", "org": "Linode", "country": "US"},
    {"ip": "47.109.94.194", "org": "Aliyun", "country": "CN"},
    {"ip": "47.116.210.163", "org": "Aliyun", "country": "CN"},
    {"ip": "47.237.205.94", "org": "Alibaba Cloud", "country": "SG"},
    {"ip": "47.252.1.180", "org": "Alibaba Cloud", "country": "US"},
    {"ip": "49.0.253.51", "org": "Huawei Cloud", "country": "HK"},
    {"ip": "51.222.42.220", "org": "OVH", "country": "CA"},
    {"ip": "8.211.201.179", "org": "Alibaba Cloud", "country": "GB"},
    {"ip": "8.215.198.154", "org": "Alibaba Cloud", "country": "ID"},
]

READ_ONLY_PROBES: list[dict[str, Any]] = [
    {"method": "web3_clientVersion", "params": [], "tag": "client"},
    {"method": "eth_chainId", "params": [], "tag": "chain"},
    {"method": "eth_blockNumber", "params": [], "tag": "sync"},
    {"method": "net_version", "params": [], "tag": "network"},
    {"method": "net_peerCount", "params": [], "tag": "peers"},
    {"method": "txpool_status", "params": [], "tag": "mempool_status", "module": "txpool"},
    {"method": "txpool_content", "params": [], "tag": "mempool_content", "module": "txpool"},
    {"method": "eth_getLogs", "params": [{"fromBlock": "latest", "toBlock": "latest", "limit": 1}], "tag": "logs"},
]

# Presence-only checks — errors are expected on hardened nodes.
MODULE_PRESENCE_CHECKS: list[dict[str, str]] = [
    {"method": "personal_listAccounts", "module": "personal", "risk": "CRITICAL"},
    {"method": "admin_nodeInfo", "module": "admin", "risk": "HIGH"},
    {"method": "debug_traceBlockByNumber", "module": "debug", "risk": "MEDIUM"},
]


@dataclass
class ProbeResult:
    ip: str
    org: str
    country: str
    endpoint: str
    reachable: bool = False
    latency_ms: float | None = None
    client_version: str | None = None
    chain_id: str | None = None
    block_number: str | None = None
    peer_count: str | None = None
    rpc_modules: dict[str, str] = field(default_factory=dict)
    methods: dict[str, str] = field(default_factory=dict)
    filters: dict[str, str] = field(default_factory=dict)
    risk_flags: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def rpc_call(url: str, method: str, params: list[Any], timeout: float = 8.0) -> dict[str, Any]:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    resp = requests.post(url, json=payload, timeout=timeout, headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        return data
    return {"error": {"code": -32603, "message": f"non_object_response:{type(data).__name__}"}}


def probe_node(node: dict[str, str], port: int = 8545, timeout: float = 8.0) -> ProbeResult:
    ip = node["ip"]
    url = f"http://{ip}:{port}"
    result = ProbeResult(ip=ip, org=node["org"], country=node["country"], endpoint=url)

    try:
        t0 = time.perf_counter()
        modules_resp = rpc_call(url, "rpc_modules", [], timeout=timeout)
        result.latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        result.reachable = True

        modules_data = modules_resp.get("result")
        if isinstance(modules_data, dict):
            result.rpc_modules = {k: v for k, v in modules_data.items() if k != "rpc"}

        for probe in READ_ONLY_PROBES:
            mod = probe.get("module")
            if mod and mod not in result.rpc_modules:
                result.methods[probe["tag"]] = "module_absent"
                continue
            try:
                r = rpc_call(url, probe["method"], probe["params"], timeout=timeout)
                if r.get("error"):
                    err = r["error"] or {}
                    code = err.get("code", "?")
                    msg = str(err.get("message", ""))[:120]
                    result.methods[probe["tag"]] = f"error:{code}:{msg}"
                else:
                    val = r.get("result")
                    if probe["tag"] == "client":
                        result.client_version = str(val)[:200]
                    elif probe["tag"] == "chain":
                        result.chain_id = str(val)
                    elif probe["tag"] == "sync":
                        result.block_number = str(val)
                    elif probe["tag"] == "peers":
                        result.peer_count = str(val)
                    elif probe["tag"] == "mempool_content":
                        pending = (val or {}).get("pending", {}) if isinstance(val, dict) else {}
                        result.methods[probe["tag"]] = f"ok:accounts={len(pending)}"
                        result.risk_flags.append("TXPOOL_CONTENT")
                    elif probe["tag"] == "mempool_status":
                        result.methods[probe["tag"]] = f"ok:{val}"
                        result.risk_flags.append("TXPOOL_STATUS")
                    elif probe["tag"] == "logs":
                        count = len(val) if isinstance(val, list) else 0
                        result.methods[probe["tag"]] = f"ok:logs={count}"
                        result.risk_flags.append("ETH_GETLOGS")
                    else:
                        result.methods[probe["tag"]] = "ok"
            except Exception as exc:
                result.methods[probe["tag"]] = f"fail:{type(exc).__name__}"

        for check in MODULE_PRESENCE_CHECKS:
            mod = check["module"]
            if mod not in result.rpc_modules:
                result.methods[check["method"]] = "module_absent"
                continue
            try:
                params = ["latest", {"tracer": "callTracer"}] if check["method"] == "debug_traceBlockByNumber" else []
                r = rpc_call(url, check["method"], params, timeout=timeout)
                if r.get("error"):
                    err = r["error"] or {}
                    result.methods[check["method"]] = f"denied:{err.get('code')}"
                else:
                    result.methods[check["method"]] = "EXPOSED"
                    result.risk_flags.append(f"{check['risk']}:{mod.upper()}_EXPOSED")
            except Exception as exc:
                result.methods[check["method"]] = f"fail:{type(exc).__name__}"

        # Filter API — useful for orchestrator subscriptions (read-only)
        for label, create_method in [
            ("pending_tx_filter", "eth_newPendingTransactionFilter"),
            ("block_filter", "eth_newBlockFilter"),
        ]:
            try:
                r = rpc_call(url, create_method, [], timeout=timeout)
                if r.get("error"):
                    err = r["error"] or {}
                    result.filters[label] = f"denied:{err.get('code')}"
                    continue
                fid = r.get("result")
                result.filters[label] = f"ok:id={fid}"
                result.risk_flags.append("FILTER_CREATE")
                # One poll to verify eth_getFilterChanges
                ch = rpc_call(url, "eth_getFilterChanges", [fid], timeout=timeout)
                if ch.get("error"):
                    err = ch["error"] or {}
                    result.filters[f"{label}_changes"] = f"denied:{err.get('code')}"
                else:
                    changes = ch.get("result") or []
                    result.filters[f"{label}_changes"] = f"ok:count={len(changes)}"
                    result.risk_flags.append("FILTER_CHANGES")
                rpc_call(url, "eth_uninstallFilter", [fid], timeout=timeout)
            except Exception as exc:
                result.filters[label] = f"fail:{type(exc).__name__}"

    except requests.exceptions.ConnectTimeout:
        result.errors.append("connect_timeout")
    except requests.exceptions.ConnectionError:
        result.errors.append("connection_refused")
    except Exception as exc:
        result.errors.append(f"{type(exc).__name__}:{exc}")

    return result


def score_node(r: ProbeResult) -> int:
    score = 0
    if not r.reachable:
        return 0
    score += 10
    if "TXPOOL_CONTENT" in r.risk_flags:
        score += 40
    if "TXPOOL_STATUS" in r.risk_flags:
        score += 20
    if "FILTER_CHANGES" in r.risk_flags:
        score += 25
    if "ETH_GETLOGS" in r.risk_flags:
        score += 15
    if any("PERSONAL" in f for f in r.risk_flags):
        score += 50
    if any("ADMIN" in f for f in r.risk_flags):
        score += 30
    if r.peer_count:
        try:
            if int(r.peer_count, 16) > 10:
                score += 10
        except ValueError:
            pass
    return score


def run_orchestrator(output_dir: Path, workers: int = 6, timeout: float = 8.0) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    results: list[ProbeResult] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(probe_node, n, 8545, timeout): n for n in GETH_NODES}
        for fut in as_completed(futures):
            results.append(fut.result())

    ranked = sorted(results, key=score_node, reverse=True)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "SHODAN_ОТЧЕТ_2026-07-08.md §4.3",
        "mode": "read_only",
        "total_nodes": len(GETH_NODES),
        "reachable": sum(1 for r in results if r.reachable),
        "txpool_enabled": sum(1 for r in results if "TXPOOL_CONTENT" in r.risk_flags or "TXPOOL_STATUS" in r.risk_flags),
        "filter_enabled": sum(1 for r in results if "FILTER_CHANGES" in r.risk_flags),
        "personal_exposed": sum(1 for r in results if any("PERSONAL" in f for f in r.risk_flags)),
        "admin_exposed": sum(1 for r in results if any("ADMIN" in f for f in r.risk_flags)),
        "top_for_orchestrator": [
            {
                "ip": r.ip,
                "endpoint": r.endpoint,
                "score": score_node(r),
                "chain_id": r.chain_id,
                "client": r.client_version,
                "risk_flags": r.risk_flags,
                "latency_ms": r.latency_ms,
            }
            for r in ranked[:5]
            if r.reachable
        ],
        "nodes": [{**asdict(r), "orchestrator_score": score_node(r)} for r in ranked],
    }

    out_json = output_dir / f"geth_rpc_probe_{ts}.json"
    out_md = output_dir / f"geth_rpc_probe_{ts}.md"
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Geth JSON-RPC Probe Report (read-only)",
        "",
        f"**Generated:** {summary['generated_at']}",
        f"**Reachable:** {summary['reachable']}/{summary['total_nodes']}",
        "",
        "## Top nodes for orchestrator (mempool / filters / logs)",
        "",
        "| Score | IP | Chain | Latency | Flags |",
        "|-------|-----|-------|---------|-------|",
    ]
    for item in summary["top_for_orchestrator"]:
        flags = ", ".join(item["risk_flags"]) or "—"
        lines.append(
            f"| {item['score']} | `{item['ip']}:8545` | {item.get('chain_id', '?')} | "
            f"{item.get('latency_ms', '?')}ms | {flags} |"
        )
    lines += ["", "## Full results", ""]
    for r in ranked:
        status = "UP" if r.reachable else "DOWN"
        lines.append(f"### {r.ip} ({r.org}, {r.country}) — {status}")
        if r.reachable:
            lines.append(f"- Client: `{r.client_version}`")
            lines.append(f"- Modules: `{', '.join(sorted(r.rpc_modules)) or 'none'}`")
            lines.append(f"- Methods: `{json.dumps(r.methods, ensure_ascii=False)}`")
            lines.append(f"- Filters: `{json.dumps(r.filters, ensure_ascii=False)}`")
            lines.append(f"- Score: **{score_node(r)}**")
        else:
            lines.append(f"- Errors: {', '.join(r.errors)}")
        lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    summary["artifacts"] = {"json": str(out_json), "markdown": str(out_md)}
    return summary


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_addr(addr: str | None) -> str:
    if not addr:
        return ""
    return addr.lower().strip()


def load_cex_cluster_map(path: Path) -> dict[str, Any]:
    unified = get_cex_cluster_payload()
    if unified:
        deposits: set[str] = set()
        _collect_deposit_addresses(unified, deposits)
        source = "artifacts/master_context.json"
        ctx = load_master_context()
        if ctx:
            for entry in ctx.get("entries", []):
                if entry.get("data") is unified:
                    source = entry.get("_meta", {}).get("source_file", source)
                    break
        return {
            "loaded": True,
            "path": source,
            "clusters": unified,
            "deposit_addresses": deposits,
            "source": "unified_index",
        }

    if not path.is_file():
        return {"loaded": False, "path": str(path), "clusters": {}, "deposit_addresses": set()}
    data = json.loads(path.read_text(encoding="utf-8"))
    deposits: set[str] = set()
    clusters = data if isinstance(data, dict) else {}
    _collect_deposit_addresses(clusters, deposits)
    return {"loaded": True, "path": str(path), "clusters": clusters, "deposit_addresses": deposits, "source": "legacy_file"}


def _collect_deposit_addresses(clusters: dict[str, Any], deposits: set[str]) -> None:
    if "clusters" in clusters and isinstance(clusters["clusters"], list):
        for c in clusters["clusters"]:
            for a in c.get("addresses", c.get("deposit_addresses", [])):
                deposits.add(normalize_addr(a))
            if c.get("exchange"):
                for a in c.get("wallets", []):
                    deposits.add(normalize_addr(a))
    else:
        for key, val in clusters.items():
            if key in ("loaded", "path", "meta", "description", "_meta", "data"):
                continue
            if isinstance(val, list):
                for a in val:
                    deposits.add(normalize_addr(str(a)))
            elif isinstance(val, dict):
                for a in val.get("addresses", val.get("deposit_addresses", [])):
                    deposits.add(normalize_addr(str(a)))
                if val.get("address"):
                    deposits.add(normalize_addr(str(val["address"])))
        depth0 = clusters.get("depth0_hot_wallet", {})
        for hit in depth0.get("cex_direct_hits", {}).values():
            if isinstance(hit, dict) and hit.get("address"):
                deposits.add(normalize_addr(hit["address"]))


def rpc_with_fallback(endpoints: list[str], method: str, params: list[Any], timeout: float = 8.0) -> tuple[str, dict[str, Any]]:
    last_err: Exception | None = None
    for url in endpoints:
        try:
            return url, rpc_call(url, method, params, timeout=timeout)
        except Exception as exc:
            last_err = exc
            continue
    raise RuntimeError(f"all RPC endpoints failed: {last_err}")


def iter_txpool_txs(content: dict[str, Any]) -> Iterator[dict[str, Any]]:
    pending = content.get("pending") or {}
    queued = content.get("queued") or {}
    for pool_name, by_account in [("pending", pending), ("queued", queued)]:
        if not isinstance(by_account, dict):
            continue
        for _account, by_nonce in by_account.items():
            if not isinstance(by_nonce, dict):
                continue
            for _nonce, tx in by_nonce.items():
                if isinstance(tx, dict):
                    yield {"pool": pool_name, **tx}


def tx_touches_targets(tx: dict[str, Any], targets: set[str]) -> list[str]:
    hits: list[str] = []
    fields = [
        normalize_addr(tx.get("from")),
        normalize_addr(tx.get("to")),
    ]
    for addr in fields:
        if addr and addr in targets:
            hits.append(addr)
    # input calldata — contract interaction with target as `to` already covered
    return hits


def build_alert(
    tx: dict[str, Any],
    hits: list[str],
    cex_map: dict[str, Any],
    rpc_url: str,
) -> dict[str, Any]:
    frm = normalize_addr(tx.get("from"))
    to = normalize_addr(tx.get("to"))
    cex_hits: list[str] = []
    deposits = cex_map.get("deposit_addresses") or set()
    if deposits:
        if frm in deposits:
            cex_hits.append(f"from_cex:{frm}")
        if to in deposits:
            cex_hits.append(f"to_cex:{to}")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rpc": rpc_url,
        "pool": tx.get("pool"),
        "hash": tx.get("hash"),
        "from": tx.get("from"),
        "to": tx.get("to"),
        "value": tx.get("value"),
        "gas": tx.get("gas"),
        "gasPrice": tx.get("gasPrice") or tx.get("maxFeePerGas"),
        "input_prefix": (tx.get("input") or "")[:66],
        "target_hits": hits,
        "cex_hits": cex_hits,
        "alert_type": "CEX_CORRELATION" if cex_hits else "TARGET_MEMPOOL",
    }


def run_monitor(
    config_path: Path,
    output_dir: Path,
    duration_seconds: int | None = None,
    timeout: float = 8.0,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    endpoints = [cfg["primary"], *cfg.get("fallbacks", [])]
    mon = cfg.get("monitoring", {})
    targets = {normalize_addr(a) for a in mon.get("target_contracts", [])}
    interval = float(mon.get("poll_interval_seconds", 1))
    cex_rel = cfg.get("cex_cluster_map", "config/cex-cluster-map.json")
    cex_path = Path(cex_rel)
    if not cex_path.is_absolute():
        base = config_path.resolve().parent.parent
        cex_path = base / cex_rel

    cex_map = load_cex_cluster_map(cex_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    alerts_file = output_dir / "mempool_alerts.jsonl"
    state_file = output_dir / "monitor_state.json"

    seen_hashes: set[str] = set()
    if state_file.is_file():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            seen_hashes = set(state.get("seen_hashes", []))
        except json.JSONDecodeError:
            seen_hashes = set()

    print(f"🔗 Primary RPC: {cfg['primary']}")
    print(f"🎯 Targets: {', '.join(sorted(targets))}")
    print(f"📂 CEX map: {cex_path} — {'loaded' if cex_map['loaded'] else 'NOT FOUND'}")
    if cex_map["loaded"]:
        print(f"   Deposit addresses indexed: {len(cex_map['deposit_addresses'])}")
    print(f"⏱️  Poll interval: {interval}s | Alerts: {alerts_file}")
    if duration_seconds:
        print(f"🧪 Test run duration: {duration_seconds}s")

    start = time.time()
    polls = 0
    alerts_count = 0
    active_rpc = cfg["primary"]

    try:
        while True:
            polls += 1
            try:
                active_rpc, resp = rpc_with_fallback(endpoints, "txpool_content", [], timeout=timeout)
                content = resp.get("result") or {}
            except RuntimeError as exc:
                print(f"⚠️  poll {polls}: {exc}")
                time.sleep(interval)
                if duration_seconds and time.time() - start >= duration_seconds:
                    break
                continue

            for tx in iter_txpool_txs(content):
                tx_hash = tx.get("hash")
                if not tx_hash or tx_hash in seen_hashes:
                    continue
                hits = tx_touches_targets(tx, targets)
                alert = None
                if hits:
                    alert = build_alert(tx, hits, cex_map, active_rpc)
                elif cex_map["loaded"]:
                    frm = normalize_addr(tx.get("from"))
                    to = normalize_addr(tx.get("to"))
                    deposits = cex_map["deposit_addresses"]
                    if frm in targets or to in targets or frm in deposits or to in deposits:
                        alert = build_alert(tx, hits, cex_map, active_rpc)

                if alert:
                    seen_hashes.add(tx_hash)
                    alerts_count += 1
                    line = json.dumps(alert, ensure_ascii=False)
                    with alerts_file.open("a", encoding="utf-8") as fh:
                        fh.write(line + "\n")
                    tag = alert["alert_type"]
                    print(f"🚨 [{tag}] {tx_hash} from={alert['from']} to={alert['to']} hits={alert['target_hits']} cex={alert['cex_hits']}")

            if polls % 10 == 0:
                state_file.write_text(
                    json.dumps({"seen_hashes": list(seen_hashes)[-5000:], "last_poll": polls, "rpc": active_rpc}, indent=2),
                    encoding="utf-8",
                )

            if duration_seconds and time.time() - start >= duration_seconds:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n⏹️  Monitor stopped")

    summary = {
        "mode": "monitor",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": str(config_path),
        "primary": cfg["primary"],
        "polls": polls,
        "alerts": alerts_count,
        "cex_map_loaded": cex_map["loaded"],
        "cex_map_path": str(cex_path),
        "targets": list(targets),
        "artifacts": {"alerts": str(alerts_file), "state": str(state_file)},
    }
    summary_path = output_dir / "monitor_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Geth RPC orchestrator")
    sub = parser.add_subparsers(dest="mode")

    probe_p = sub.add_parser("probe", help="Probe 18 Shodan Geth nodes")
    probe_p.add_argument("--output", default="/workspace/artifacts/crypto-rpc")
    probe_p.add_argument("--workers", type=int, default=6)
    probe_p.add_argument("--timeout", type=float, default=8.0)

    mon_p = sub.add_parser("monitor", help="Mempool monitor via config/rpc_config.json")
    mon_p.add_argument("--config", default=str(DEFAULT_CONFIG))
    mon_p.add_argument("--output", default="/workspace/artifacts/crypto-rpc/monitor")
    mon_p.add_argument("--duration", type=int, default=None, help="Seconds to run (omit for continuous)")
    mon_p.add_argument("--timeout", type=float, default=8.0)

    args = parser.parse_args()
    mode = args.mode or "probe"

    if mode == "monitor":
        summary = run_monitor(Path(args.config), Path(args.output), args.duration, args.timeout)
        print(f"\n✅ Monitor done — polls={summary['polls']} alerts={summary['alerts']}")
        print(f"📁 {summary['artifacts']['alerts']}")
        return 0

    print(f"🔍 Probing {len(GETH_NODES)} Geth nodes (read-only)...")
    summary = run_orchestrator(Path(args.output), workers=args.workers, timeout=args.timeout)
    print(f"✅ Reachable: {summary['reachable']}/{summary['total_nodes']}")
    print(f"📊 txpool: {summary['txpool_enabled']} | filters: {summary['filter_enabled']}")
    print(f"⚠️  personal exposed: {summary['personal_exposed']} | admin exposed: {summary['admin_exposed']}")
    print("\n🏆 Top for orchestrator:")
    for item in summary["top_for_orchestrator"]:
        print(f"  [{item['score']}] {item['ip']}:8545 — {', '.join(item['risk_flags'])}")
    print(f"\n📁 Artifacts: {summary['artifacts']['json']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
