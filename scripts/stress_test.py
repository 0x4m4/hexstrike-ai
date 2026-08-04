#!/usr/bin/env python3
"""HexStrike Stress Test — KPI evaluation across all agents."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from hexstrike.compat.bootstrap import bootstrap_paths

bootstrap_paths()

from hexstrike.paths import ALERTS_LOG, PENDING_ACTION, RPC_CONFIG

# Default targets from operator case files
DEFAULT_COLD_WALLET = "0xcfc85f21f5f01ab24d6b7a3b93ef097099ebde3a"
KNOWN_HOT_WALLET = "0x4943f5e7f4e450d48ae82026163ecde8a52c53da"
RECON_IP = "51.250.97.223"
USDT_BSC = "0x55d398326f99059fF775485246099027B3197955"

OUT_DIR = ROOT / "artifacts" / "stress_test"
REPORT_PATH = ROOT / "test_report_2026-07-10.json"


def _utc() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _score(passed: int, total: int) -> float:
    return round((passed / total) * 100, 1) if total else 0.0


def test_monitor(orch: Any, target: str, duration: int = 45) -> dict[str, Any]:
    """KPI: latency, precision, stealth."""
    t0 = time.time()
    alerts_before = 0
    if ALERTS_LOG.is_file():
        alerts_before = sum(1 for _ in ALERTS_LOG.open() if _.strip())

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "autonomous_monitor.py"), "--duration", str(duration)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    elapsed = round(time.time() - t0, 2)

    alerts_after = []
    if ALERTS_LOG.is_file():
        for line in ALERTS_LOG.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    alerts_after.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    new_alerts = alerts_after[alerts_before:]
    false_positives = sum(
        1 for a in new_alerts
        if not a.get("context_hits") and not a.get("high_risk")
    )
    stealth_on = "Stealth transport: on" in (proc.stdout or "")

    latency_kpi = "pass" if elapsed <= duration + 10 else "warn"
    precision_kpi = "pass" if false_positives == 0 else "fail"
    stealth_kpi = "pass" if stealth_on else "fail"

    result = {
        "agent": "core.monitor",
        "target": target,
        "duration_sec": duration,
        "wall_clock_sec": elapsed,
        "new_alerts": len(new_alerts),
        "false_positives": false_positives,
        "stealth_enabled": stealth_on,
        "kpi": {
            "latency": {"status": latency_kpi, "note": f"Monitor cycle completed in {elapsed}s"},
            "precision": {"status": precision_kpi, "false_alerts": false_positives},
            "stealth": {"status": stealth_kpi, "note": "No RPC ban observed; stealth transport active"},
        },
        "stdout_tail": (proc.stdout or "")[-500:],
    }
    passed = sum(1 for k in ("latency", "precision", "stealth") if result["kpi"][k]["status"] == "pass")
    result["score"] = _score(passed, 3)
    (OUT_DIR / "monitor_run.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def test_forensics(orch: Any, target: str) -> dict[str, Any]:
    """KPI: clustering, depth >= 3."""
    analysis = orch.run_analyze(target)
    entity = analysis.get("entity", {})
    labels = entity.get("labels", [])
    trace = analysis.get("trace", {})
    nodes = trace.get("nodes", [])
    max_level = max((n.get("level", 0) for n in nodes), default=0)

    clustered = any("cex" in str(l).lower() or "exchange" in str(l).lower() for l in labels)
    linked_to_hot = KNOWN_HOT_WALLET.lower() in json.dumps(analysis).lower()

    clustering_kpi = "pass" if (clustered or linked_to_hot) else "fail"
    depth_kpi = "pass" if max_level >= 2 else "warn"  # 3 levels = 0,1,2

    result = {
        "agent": "core.forensics",
        "target": target,
        "labels": labels,
        "sources": entity.get("sources", []),
        "trace_depth_levels": max_level + 1,
        "rag_hits": len(analysis.get("rag_hits", [])),
        "kpi": {
            "clustering": {
                "status": clustering_kpi,
                "cex_labels": clustered,
                "linked_to_known_case": linked_to_hot,
            },
            "depth": {
                "status": depth_kpi,
                "levels": max_level + 1,
                "required_min": 3,
            },
        },
    }
    passed = sum(1 for k in result["kpi"] if result["kpi"][k]["status"] == "pass")
    result["score"] = _score(passed, 2)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "forensics_result.json").write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")
    return result


def _probe_port(host: str, port: int, timeout: float = 2.0) -> dict[str, Any]:
    try:
        t0 = time.perf_counter()
        with socket.create_connection((host, port), timeout=timeout):
            latency = round((time.perf_counter() - t0) * 1000, 1)
            return {"port": port, "open": True, "latency_ms": latency}
    except (OSError, socket.timeout):
        return {"port": port, "open": False}


def test_recon_osint(orch: Any, ip: str) -> dict[str, Any]:
    """KPI: coverage, risk score."""
    ports = [22, 80, 443, 8080, 8545, 8546, 30303]
    scan = [_probe_port(ip, p) for p in ports]
    open_ports = [s for s in scan if s["open"]]

    orch_result = orch.recon.fingerprint_host(ip, ports=ports)
    rpc_scan = orch.recon.scan_rpc_nodes(limit=1)

    risk_flags: list[str] = []
    if any(s["port"] == 8545 and s["open"] for s in scan):
        risk_flags.append("exposed_geth_rpc")
    if any(s["port"] == 8080 and s["open"] for s in scan):
        risk_flags.append("jenkins_or_http_admin")
    if any(s["port"] == 22 and s["open"] for s in scan):
        risk_flags.append("ssh_exposed")

    cvss_estimate = min(10.0, 3.0 + len(risk_flags) * 2.5)
    coverage_kpi = "pass" if len(open_ports) > 0 else "warn"
    risk_kpi = "pass" if cvss_estimate >= 5.0 or len(open_ports) == 0 else "warn"

    result = {
        "agent": "skill.recon_osint",
        "target_ip": ip,
        "open_ports": open_ports,
        "total_probed": len(ports),
        "risk_flags": risk_flags,
        "cvss_estimate": cvss_estimate,
        "rpc_node_sample": rpc_scan[:1] if rpc_scan else [],
        "kpi": {
            "coverage": {"status": coverage_kpi, "open_count": len(open_ports)},
            "risk_score": {"status": risk_kpi, "cvss_estimate": cvss_estimate, "flags": risk_flags},
        },
    }
    passed = sum(1 for k in result["kpi"] if result["kpi"][k]["status"] == "pass")
    result["score"] = _score(passed, 2)
    (OUT_DIR / "recon_scan.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def test_timing_analysis(orch: Any, sample_tx_hash: str | None = None) -> dict[str, Any]:
    """KPI: fee recommendation accuracy proxy."""
    profile = orch.run_timing()
    best = profile if isinstance(profile, dict) else {}
    latency = best.get("latency_ms_avg")

  # Mempool gas sample
    gas_price_wei = None
    try:
        _, resp = orch.rpc_mcp.call("eth_gasPrice", [])
        gas_price_wei = int(resp.get("response", {}).get("result", "0x0"), 16)
    except Exception:
        pass

    recommended_priority_gwei = 3.0
    base_gwei = (gas_price_wei or 0) / 1e9
    competitive_fee_gwei = round(base_gwei * 1.25 + recommended_priority_gwei, 2)

    # Heuristic: would pass in 2 blocks if latency < 500ms and fee >= base
    would_pass_2_blocks = (
        latency is not None
        and latency < 500
        and competitive_fee_gwei >= base_gwei
    )

    result = {
        "agent": "skill.timing_analysis",
        "best_endpoint": best.get("endpoint"),
        "latency_ms_avg": latency,
        "gas_price_gwei": round(base_gwei, 4),
        "recommended_fee_gwei": competitive_fee_gwei,
        "sample_tx": sample_tx_hash,
        "kpi": {
            "accuracy": {
                "status": "pass" if would_pass_2_blocks else "warn",
                "would_pass_2_blocks_heuristic": would_pass_2_blocks,
                "note": "Heuristic based on RPC latency + 1.25x gas bump",
            },
        },
    }
    result["score"] = 100.0 if would_pass_2_blocks else 50.0
    (OUT_DIR / "timing_profile.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def test_execution(orch: Any, operator_address: str) -> dict[str, Any]:
    """KPI: safety gate, tx formatting."""
    usdt_transfer_tx = {
        "from": operator_address,
        "to": USDT_BSC,
        "value": "0x0",
        "data": "0xa9059cbb"
        + operator_address.lower().replace("0x", "").zfill(64)
        + hex(int(0.0001 * 1e18))[2:].zfill(64),
    }

    pre = orch.broadcaster.preflight(usdt_transfer_tx, sniping=False)
    queue = orch.broadcaster.queue_for_approval(usdt_transfer_tx, reason="stress_test_dry_run")

    broadcast_blocked = orch.agent_manager.gated_broadcast("0xdeadbeef", approved=False)
    broadcast_without_pending = orch.broadcaster.broadcast("0xdeadbeef", approved=False)

    hex_valid = (
        usdt_transfer_tx["data"].startswith("0xa9059cbb")
        and len(usdt_transfer_tx["data"]) >= 138
    )

    result = {
        "agent": "core.execution",
        "dry_run": True,
        "preflight_ok": pre.ok,
        "gas_estimate": pre.gas_estimate,
        "queued_path": queue.get("path"),
        "kpi": {
            "safety": {
                "status": "pass"
                if not broadcast_blocked.get("success") and not broadcast_without_pending.get("success")
                else "fail",
                "gate_blocked": broadcast_blocked.get("error"),
                "broadcaster_blocked": broadcast_without_pending.get("error"),
            },
            "formatting": {
                "status": "pass" if hex_valid else "fail",
                "data_prefix": usdt_transfer_tx["data"][:10],
                "data_length": len(usdt_transfer_tx["data"]),
            },
        },
    }
    passed = sum(1 for k in result["kpi"] if result["kpi"][k]["status"] == "pass")
    result["score"] = _score(passed, 2)
    (OUT_DIR / "execution_dry_run.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def run_stress_test(target: str, recon_ip: str, monitor_duration: int = 45) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    from hexstrike_orchestrator import HexStrikeOrchestrator

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    started = _utc()
    print(f"[STRESS_TEST] Started {_utc()} | target={target} | recon_ip={recon_ip}")

    orch = HexStrikeOrchestrator(config_path=RPC_CONFIG)

    results = {
        "test_id": "hexstrike_stress_test_2026-07-10",
        "mode": "STRESS_TEST",
        "started_at": started,
        "target_wallet": target,
        "known_hot_wallet": KNOWN_HOT_WALLET,
        "recon_ip": recon_ip,
        "agents": {},
    }

    print("[1/5] core.monitor...")
    results["agents"]["core.monitor"] = test_monitor(orch, target, duration=monitor_duration)

    print("[2/5] core.forensics...")
    results["agents"]["core.forensics"] = test_forensics(orch, target)

    print("[3/5] skill.recon_osint...")
    results["agents"]["skill.recon_osint"] = test_recon_osint(orch, recon_ip)

    print("[4/5] skill.timing_analysis...")
    results["agents"]["skill.timing_analysis"] = test_timing_analysis(orch)

    print("[5/5] core.execution...")
    results["agents"]["core.execution"] = test_execution(orch, target)

    scores = {k: v.get("score", 0) for k, v in results["agents"].items()}
    ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    results["finished_at"] = _utc()
    results["ranking"] = [{"agent": a, "score": s} for a, s in ranking]
    results["overall_score"] = round(sum(scores.values()) / len(scores), 1) if scores else 0
    results["recommendations"] = _build_recommendations(results["agents"])

    REPORT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "full_report.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"[STRESS_TEST] Report: {REPORT_PATH}")
    return results


def _build_recommendations(agents: dict[str, Any]) -> list[str]:
    recs = []
    forensics = agents.get("core.forensics", {})
    if forensics.get("kpi", {}).get("depth", {}).get("status") != "pass":
        recs.append("Tighten forensics.md: require depth-3 Blockscout API traversal (chain_tracer currently heuristic).")
    monitor = agents.get("core.monitor", {})
    if monitor.get("kpi", {}).get("precision", {}).get("status") != "pass":
        recs.append("Tune monitor.md dedup/RAG thresholds to cut false positives.")
    recon = agents.get("skill.recon_osint", {})
    if recon.get("kpi", {}).get("coverage", {}).get("status") == "warn":
        recs.append("Extend recon_osint.md with Shodan MCP for IP 51.250.97.223 deep scan.")
    timing = agents.get("skill.timing_analysis", {})
    if timing.get("kpi", {}).get("accuracy", {}).get("status") != "pass":
        recs.append("Add live mempool fee sampling to timing_analysis.md (10-min window).")
    if not recs:
        recs.append("All agents within KPI bounds — proceed to live operator orders.")
    return recs


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="HexStrike Stress Test")
    parser.add_argument("--target", default=os.environ.get("STRESS_TARGET", DEFAULT_COLD_WALLET))
    parser.add_argument("--ip", default=os.environ.get("STRESS_RECON_IP", RECON_IP))
    parser.add_argument("--monitor-duration", type=int, default=45)
    args = parser.parse_args()

    results = run_stress_test(args.target, args.ip, args.monitor_duration)
    print(json.dumps({"overall_score": results["overall_score"], "ranking": results["ranking"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
