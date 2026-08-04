#!/usr/bin/env python3
"""HexStrike-AI orchestrator — central dispatcher for modules, skills, and MCPs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from hexstrike.agent_manager import AgentManager
from hexstrike.bus.context_bus import ContextBus
from hexstrike.llm.provider import (
    LocalLlmProvider,
    LlmConfig,
    resolve_llm_config,
    write_env_llm_block,
)
from hexstrike.core.execution.broadcaster import ExecutionBroadcaster, SnipingProfile
from hexstrike.core.forensics.engine import ForensicsEngine
from hexstrike.core.monitor.mempool import MempoolMonitor, MonitorConfig
from hexstrike.core.stealth.transport import StealthConfig, StealthTransport
from hexstrike.core.vault.keystore import KeyVault
from hexstrike.mcp.execution_gate import ExecutionGateMcp
from hexstrike.mcp.github_bridge import GithubBridgeMcp
from hexstrike.mcp.rag_memory import RagMemoryMcp
from hexstrike.mcp.rpc_gateway import RpcGatewayMcp
from hexstrike.paths import MANIFEST_PATH, PENDING_ACTION, RPC_CONFIG
from hexstrike.skills.bytecode_deobfuscator import BytecodeDeobfuscatorSkill
from hexstrike.skills.chain_tracer import ChainTracerSkill
from hexstrike.skills.dedup_engine import DedupEngine
from hexstrike.skills.dual_mode_agent import DualModeAgent
from hexstrike.skills.recon_osint import ReconOsintSkill
from hexstrike.skills.timing_analysis import TimingAnalysisSkill
from hexstrike.instructions import load_instruction
from hexstrike.paths import (
    ALERTS_LOG as HS_ALERTS,
    PENDING_ACTION as HS_PENDING,
    RPC_CONFIG as HS_RPC_CONFIG,
)
from hexstrike.skills.vulnerability_scanner import VulnerabilityScanner

# Monitor agent system prompt (instruction protocol)
MONITOR_AGENT_ID = "core.monitor"
MONITOR_SYSTEM_PROMPT = load_instruction(MONITOR_AGENT_ID)


def _bootstrap_llm_env() -> LlmConfig:
    """Initialize LLM env vars without pointing OLLAMA_HOST at llama-server."""
    config = resolve_llm_config()
    os.environ.setdefault("LLM_PROVIDER", config.provider)
    os.environ.setdefault("LLM_BASE_URL", config.base_url)
    os.environ.setdefault("LLM_MODEL", config.model)
    os.environ.setdefault("LLAMA_SERVER_HOST", config.llama_host)
    # Always the Ollama daemon (:11434), never llama-server (:8080)
    os.environ.setdefault("OLLAMA_HOST", config.ollama_host)
    if config.bypass_tunnel:
        os.environ.setdefault("OLLAMA_BYPASS_TUNNEL", "true")
        # Do not overwrite OLLAMA_PUBLIC_BASE_URL with a local base_url
    return config


class HexStrikeOrchestrator:
    """Central dispatcher: recon → forensics → execution with ContextBus."""

    def __init__(self, config_path: Path = RPC_CONFIG) -> None:
        self.llm_config = _bootstrap_llm_env()
        self.llm = LocalLlmProvider(self.llm_config)
        self.bus = ContextBus()
        self.config_path = config_path

        self.stealth = StealthTransport(StealthConfig())
        self.monitor = MempoolMonitor(
            bus=self.bus,
            config=MonitorConfig(config_path=config_path, stealth_enabled=True),
        )
        self.forensics = ForensicsEngine(bus=self.bus)
        self.broadcaster = ExecutionBroadcaster(bus=self.bus, config_path=config_path, sniping=SnipingProfile())
        self.vault = KeyVault(bus=self.bus, prefer_ramdisk=True)

        self.rpc_mcp = RpcGatewayMcp(bus=self.bus, monitor=self.monitor)
        self.rag_mcp = RagMemoryMcp(bus=self.bus)
        self.execution_mcp = ExecutionGateMcp(bus=self.bus, broadcaster=self.broadcaster)
        self.github_mcp = GithubBridgeMcp(bus=self.bus)

        self.recon = ReconOsintSkill(bus=self.bus)
        self.chain_tracer = ChainTracerSkill(bus=self.bus, forensics=self.forensics)
        self.dedup = DedupEngine(bus=self.bus)
        self.timing = TimingAnalysisSkill(bus=self.bus, config_path=config_path)
        self.bytecode = BytecodeDeobfuscatorSkill(bus=self.bus, config_path=config_path)
        self.vuln_scanner = VulnerabilityScanner(bus=self.bus)
        self.dual_mode = DualModeAgent(bus=self.bus, llm=self.llm)

        self.agent_manager = AgentManager(
            bus=self.bus,
            mcp_registry={
                "mcp_rpc_gateway": self.rpc_mcp,
                "mcp_rag_memory": self.rag_mcp,
                "mcp_execution_gate": self.execution_mcp,
                "mcp_github_bridge": self.github_mcp,
            },
            module_registry={
                "core.monitor": self.monitor,
                "core.forensics": self.forensics,
                "core.execution": self.broadcaster,
                "skill.recon_osint": self.recon,
                "skill.timing_analysis": self.timing,
                "skill.dual_mode": self.dual_mode,
            },
        )
        self.agent_manager.initialize_all()

        self._wire_bus_logging()

    def _wire_bus_logging(self) -> None:
        def _log(event) -> None:
            if event.topic.startswith(("monitor.", "execution.", "mcp.execution.", "skill.")):
                print(f"[bus] {event.topic} ← {event.source}")

        self.bus.subscribe("*", _log)

    def health(self) -> dict[str, Any]:
        timing_best = self.timing.recommend_endpoint()
        llm_status = self.llm.status()
        llm_latency = self.llm.measure_hook_latency(probe="models")
        return {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "llm": {**llm_status, "hook_latency_ms": llm_latency.get("latency_ms")},
            "rpc": self.rpc_mcp.health(),
            "stealth": self.stealth.status(),
            "vault": self.vault.status(),
            "execution_gate": self.execution_mcp.status(),
            "dedup": self.dedup.snapshot(),
            "timing_best_rpc": timing_best.get("endpoint") if isinstance(timing_best, dict) else None,
            "forensics_entries": len((self.forensics.load_context() or {}).get("entries", [])),
        }

    def update_manifest(self) -> dict[str, Any]:
        manifest_path = MANIFEST_PATH
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        health = self.health()

        runtime = {
            "last_health_check": health["timestamp"],
            "rpc_status": health["rpc"].get("status"),
            "active_rpc": health["rpc"].get("active_rpc"),
            "stealth_enabled": health["stealth"].get("enabled"),
            "vault_backend": health["vault"].get("storage_backend"),
            "pending_action": health["execution_gate"].get("has_pending"),
            "dedup_pairs": health["dedup"].get("active_pairs"),
            "timing_best_rpc": health.get("timing_best_rpc"),
        }
        manifest["updated_at"] = health["timestamp"]
        manifest["runtime"] = runtime

        for layer in ("modules", "skills", "mcps"):
            for name, meta in manifest["layers"][layer].items():
                if meta.get("status") == "external":
                    continue
                meta["last_checked"] = health["timestamp"]

        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.bus.publish("orchestrator.manifest_updated", runtime, source="orchestrator")
        return manifest

    def run_health_suite(self) -> dict[str, Any]:
        script = ROOT / "scripts" / "health_check.sh"
        if script.is_file():
            proc = subprocess.run([str(script)], cwd=str(ROOT), capture_output=True, text=True)
            return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
        return self.health()

    def run_recon(self, limit: int = 3) -> list[dict[str, Any]]:
        return self.recon.scan_rpc_nodes(limit=limit)

    def run_timing(self) -> dict[str, Any]:
        return self.timing.recommend_endpoint()

    def run_bytecode(self, address: str) -> dict[str, Any]:
        return self.forensics.analyze_contract(address)

    def run_vuln_scan(self) -> dict[str, Any]:
        return self.vuln_scanner.run_full_scan()

    def run_dual_mode(
        self,
        contract: str,
        *,
        mode: str = "defense",
        poc_test: str | None = None,
    ) -> dict[str, Any]:
        """Dual-Mode audit: Slither/Mythril/Echidna + defense fixes or sandbox PoC."""
        return self.dual_mode.analyze(contract, mode=mode, poc_test=poc_test)

    def run_analyze(self, address: str) -> dict[str, Any]:
        """Instruction-driven forensics analysis (hot-wallet protocol)."""
        prompt = self.agent_manager.get_system_prompt("core.forensics")
        entity = self.forensics.resolve_entity(address)
        contract = self.forensics.analyze_contract(address)
        trace = self.chain_tracer.trace(address, depth=2)
        rag_hits = self.rag_mcp.search(f"address {address} rhino bridge hot wallet usdt")
        return {
            "address": address.lower(),
            "instruction_loaded": "forensics.md",
            "instruction_bytes": len(prompt),
            "entity": entity,
            "contract": contract,
            "trace": trace,
            "rag_hits": rag_hits[:3],
        }

    def run_monitor_loop(
        self,
        *,
        duration_seconds: int | None = None,
        delegate_legacy: bool = True,
    ) -> dict[str, Any]:
        if delegate_legacy:
            legacy = ROOT / "scripts" / "autonomous_monitor.py"
            if legacy.is_file():
                cmd = [sys.executable, str(legacy), "--config", str(self.config_path)]
                if duration_seconds:
                    cmd.extend(["--duration", str(duration_seconds)])
                proc = subprocess.run(cmd, cwd=str(ROOT))
                return {"mode": "legacy_monitor", "returncode": proc.returncode}

        alerts = 0
        dedup_skipped = 0
        txs = 0

        for tx in self.monitor.stream(duration_seconds=duration_seconds):
            txs += 1
            frm, to = tx.get("from", ""), tx.get("to", "")
            fp, _ = self.rag_mcp.is_false_positive(tx.get("hash", ""), frm, to)
            if fp:
                continue

            alert = {"hash": tx.get("hash"), "from": frm, "to": to, "severity": "WARN"}
            if self.dedup.filter_alert(alert) is None:
                dedup_skipped += 1
                continue

            entity = self.forensics.resolve_entity(to)
            if entity.get("labels"):
                alert["severity"] = "CRITICAL"

            self.execution_mcp.submit(
                {"hash": tx.get("hash"), "from": frm, "to": to, "value": tx.get("value")},
                reason="mempool_watch_hit",
                severity=alert["severity"],
            )
            alerts += 1

        return {"mode": "orchestrator", "txs": txs, "alerts": alerts, "dedup_skipped": dedup_skipped}

    def run_trace_infra(
        self,
        target_ip: str,
        *,
        mode: str = "deep-osint",
        output: Path | None = None,
        wallet_address: str | None = None,
    ) -> dict[str, Any]:
        from hexstrike.skills.infra_tracer import InfraTracer

        tracer = InfraTracer(bus=self.bus)
        report = tracer.trace(target_ip, mode=mode, wallet_address=wallet_address)

        if wallet_address:
            analysis = self.run_analyze(wallet_address)
            report["forensics_correlation"] = {
                "wallet": wallet_address,
                "entity": analysis.get("entity"),
                "labels": analysis.get("entity", {}).get("labels", []),
                "rag_hits": len(analysis.get("rag_hits", [])),
            }

        out_path = output or (ROOT / "artifacts" / "infra-trace-final.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report["output_path"] = str(out_path)
        self.bus.publish("orchestrator.trace_infra", {"ip": target_ip, "path": str(out_path)}, source="orchestrator")
        return report

    def run_vector_b(self, target_ip: str) -> dict[str, Any]:
        from hexstrike.skills.enode_crawl import EnodeCrawlSkill

        skill = EnodeCrawlSkill(bus=self.bus)
        return skill.crawl(target_ip)

    def run_vector_c(self, target_ip: str, wallet: str) -> dict[str, Any]:
        from hexstrike.skills.ip_forensics import IpForensicsSkill

        skill = IpForensicsSkill(bus=self.bus)
        return skill.run(target_ip, wallet, forensics_engine=self.forensics)

    def run_ops_vectors(
        self,
        target_ip: str,
        wallet: str,
        *,
        skip_vector_a: bool = True,
    ) -> dict[str, Any]:
        """Execute vectors B+C; Vector A requires authorized scope (not auto-run)."""
        report = {
            "operation": "ops_vectors",
            "target_ip": target_ip,
            "wallet": wallet,
            "vector_a": {
                "status": "SKIPPED",
                "reason": (
                    "CVE-2024-23897 file-read exploitation not executed — requires explicit "
                    "authorized pentest scope and mcp_execution_gate approval"
                ),
                "jenkins_version_observed": "2.375.3",
                "surface": "exposed_login_8080",
            },
            "vector_b": self.run_vector_b(target_ip),
            "vector_c": self.run_vector_c(target_ip, wallet),
        }
        out = ROOT / "artifacts" / "vector-ops-report.json"
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report["output_path"] = str(out)
        return report

    def status(self) -> dict[str, Any]:
        return {
            "version": "8.0.0",
            "llm_provider": self.llm.status(),
            "components": {
                "core.monitor": "active",
                "core.stealth": self.stealth.status(),
                "core.forensics": "active",
                "core.execution": "active",
                "core.vault": self.vault.status(),
            },
            "skills": [
                "skill.recon_osint",
                "skill.chain_tracer",
                "skill.timing_analysis",
                "skill.vulnerability_scanner",
                "skill.dedup_engine",
                "skill.bytecode_deobfuscator",
            ],
            "mcps": [
                "mcp_rpc_gateway",
                "mcp_rag_memory",
                "mcp_execution_gate",
                "mcp_github_bridge",
            ],
            "agents": self.agent_manager.status(),
            "pending_action": str(PENDING_ACTION),
            "manifest": str(MANIFEST_PATH),
        }


def main() -> int:
    from api_auth import load_dotenv

    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="HexStrike-AI orchestrator")
    parser.add_argument("--config", default=str(RPC_CONFIG))
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show component status")
    sub.add_parser("health", help="Run health checks and update manifest")
    sub.add_parser("manifest", help="Update project_manifest.json runtime section")

    sub.add_parser("agents", help="Show bound agents and instruction files")

    analyze_p = sub.add_parser("analyze", help="Forensics analysis on address (instruction-driven)")
    analyze_p.add_argument("address", help="Target address (0x...)")

    recon_p = sub.add_parser("recon", help="Passive RPC recon scan")
    recon_p.add_argument("--limit", type=int, default=3)

    sub.add_parser("timing", help="RPC latency profile for gas-war positioning")
    sub.add_parser("vuln-scan", help="Run vulnerability scanner")

    dm_p = sub.add_parser("dual-mode", help="Dual-Mode contract audit (defense/offense)")
    dm_p.add_argument("contract", help="Path to .sol file or Foundry project")
    dm_p.add_argument("--mode", choices=("defense", "offense", "forensics"), default="defense")
    dm_p.add_argument("--poc-test", default=None, help="Foundry test path for offense PoC")

    bc_p = sub.add_parser("bytecode", help="Analyze contract bytecode")
    bc_p.add_argument("address", help="Contract address (0x...)")

    mon_p = sub.add_parser("monitor", help="Run mempool monitor loop")
    mon_p.add_argument("--duration", type=int, default=None)
    mon_p.add_argument("--native", action="store_true", help="Use orchestrator native loop")

    stress_p = sub.add_parser("stress-test", help="Run HexStrike Stress Test (KPI evaluation)")
    stress_p.add_argument("--target", default="0xcfc85f21f5f01ab24d6b7a3b93ef097099ebde3a")
    stress_p.add_argument("--ip", default="51.250.97.223")
    stress_p.add_argument("--monitor-duration", type=int, default=45)
    stress_p.add_argument(
        "--mode",
        choices=("legacy", "defense", "attack", "both"),
        default="legacy",
        help="legacy=KPI agents; defense/attack/both=battle stress sessions (inspector TZ)",
    )
    stress_p.add_argument("--runs", type=int, default=5, help="Runs per session (defense/attack)")

    trace_p = sub.add_parser("trace-infra", help="Deep infrastructure OSINT trace (read-only)")
    trace_p.add_argument("--target-ip", required=True)
    trace_p.add_argument("--mode", default="deep-osint")
    trace_p.add_argument("--output", default="artifacts/infra-trace-final.json")
    trace_p.add_argument("--wallet", default="0xcfc85f21f5f01ab24d6b7a3b93ef097099ebde3a")

    ops_p = sub.add_parser("ops-vectors", help="Run vectors B+C (network + forensics); A skipped by policy")
    ops_p.add_argument("--target-ip", default="51.250.97.223")
    ops_p.add_argument("--wallet", default="0xcfc85f21f5f01ab24d6b7a3b93ef097099ebde3a")

    llm_p = sub.add_parser(
        "llm-handshake",
        help="Verify LLM hook + latency diagnostic (local/cloud; alias of: llm handshake)",
    )
    llm_p.add_argument("--probe", choices=("models", "chat", "both"), default="both")

    llm_cmd = sub.add_parser("llm", help="Local LLM connect / status / handshake (llama-server > ollama)")
    llm_sub = llm_cmd.add_subparsers(dest="llm_cmd")
    llm_sub.add_parser("connect", help="Detect running LLM, write .env, run defense handshake")
    llm_sub.add_parser("status", help="Show resolved provider + reachability")
    llm_hs = llm_sub.add_parser("handshake", help="Defense-prompted chat + latency probes")
    llm_hs.add_argument("--probe", choices=("models", "chat", "both"), default="both")

    args = parser.parse_args()

    # Lightweight LLM subcommands (no full orchestrator bootstrap required)
    if args.command == "llm":
        cfg = resolve_llm_config()
        provider = LocalLlmProvider(cfg)
        if args.llm_cmd == "status":
            st = provider.status()
            print(json.dumps(st, indent=2))
            return 0 if st.get("selected_provider_reachable") else 1
        if args.llm_cmd == "connect":
            env_path = ROOT / ".env"
            write_env_llm_block(env_path, cfg)
            # Re-resolve after writing auto-detect keys
            provider = LocalLlmProvider(resolve_llm_config())
            report = provider.handshake(probe="both")
            report["env_written"] = str(env_path)
            print(json.dumps(report, indent=2))
            return 0 if report.get("llm", {}).get("selected_provider_reachable") else 1
        if args.llm_cmd == "handshake":
            report = provider.handshake(probe=getattr(args, "probe", "both"))
            print(json.dumps(report, indent=2))
            return 0 if report.get("llm", {}).get("selected_provider_reachable") else 1
        print("usage: hexstrike_orchestrator.py llm {connect|status|handshake}", file=sys.stderr)
        return 2

    orch = HexStrikeOrchestrator(config_path=Path(args.config))

    if args.command == "status":
        print(json.dumps(orch.status(), indent=2))
        return 0
    if args.command == "health":
        result = orch.run_health_suite()
        orch.update_manifest()
        if isinstance(result, dict) and "stdout" in result:
            print(result.get("stdout", ""))
        else:
            print(json.dumps(result, indent=2))
        return 0
    if args.command == "manifest":
        print(json.dumps(orch.update_manifest(), indent=2))
        return 0
    if args.command == "agents":
        print(json.dumps(orch.agent_manager.status(), indent=2))
        return 0
    if args.command == "analyze":
        print(json.dumps(orch.run_analyze(args.address), indent=2))
        return 0
    if args.command == "recon":
        print(json.dumps(orch.run_recon(limit=args.limit), indent=2))
        return 0
    if args.command == "timing":
        print(json.dumps(orch.run_timing(), indent=2))
        return 0
    if args.command == "bytecode":
        print(json.dumps(orch.run_bytecode(args.address), indent=2))
        return 0
    if args.command == "vuln-scan":
        print(json.dumps(orch.run_vuln_scan(), indent=2))
        return 0
    if args.command == "dual-mode":
        print(json.dumps(orch.run_dual_mode(args.contract, mode=args.mode, poc_test=args.poc_test), indent=2))
        return 0
    if args.command == "monitor":
        result = orch.run_monitor_loop(
            duration_seconds=args.duration,
            delegate_legacy=not args.native,
        )
        orch.update_manifest()
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "stress-test":
        if args.mode in ("defense", "attack", "both"):
            cmd = [
                sys.executable,
                str(ROOT / "scripts" / "battle_stress_sessions.py"),
                "--mode", args.mode,
                "--runs", str(args.runs),
                "--ip", args.ip,
                "--monitor-duration", str(args.monitor_duration),
            ]
            return subprocess.call(cmd, cwd=str(ROOT))
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "stress_test.py"),
            "--target", args.target,
            "--ip", args.ip,
            "--monitor-duration", str(args.monitor_duration),
        ]
        return subprocess.call(cmd, cwd=str(ROOT))
    if args.command == "trace-infra":
        result = orch.run_trace_infra(
            args.target_ip,
            mode=args.mode,
            output=Path(args.output),
            wallet_address=args.wallet,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.command == "ops-vectors":
        result = orch.run_ops_vectors(args.target_ip, args.wallet)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.command == "llm-handshake":
        report = orch.llm.handshake(probe=args.probe)
        report["integration_mode"] = orch.llm_config.integration_mode
        print(json.dumps(report, indent=2))
        llm = report["llm"]
        ok = llm.get("selected_provider_reachable") or llm.get("endpoint_reachable")
        return 0 if ok else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
