#!/usr/bin/env python3
"""
HexStrike Orchestrator — dispatches tasks to registered agents.

Run on Mac/VPS separately from Cursor chat. Chat plans; orchestrator executes.

Examples:
  ./hexstrike-orchestrator run entity-id-pipeline
  ./hexstrike-orchestrator dispatch Agent-OSINT-03 entity-resolution
  ./hexstrike-orchestrator enqueue agents/queue/job.json
  ./hexstrike-orchestrator watch
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
REGISTRY = ROOT / "agents/registry.json"
WORKFLOWS = ROOT / "agents/workflows.json"
AGENT_RUNNER = ROOT / "scripts/hexstrike-agent.py"
QUEUE_DIR = ROOT / "agents/queue"
from hexstrike.agent_controller import AgentController

LOG_DIR = ROOT / "artifacts/orchestrator"
CONTROLLER = AgentController()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def log_run(record: dict) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    run_id = record.get("run_id", uuid.uuid4().hex[:12])
    path = LOG_DIR / f"{run_id}.json"
    with open(path, "w") as f:
        json.dump(record, f, indent=2)
    latest = LOG_DIR / "latest.json"
    with open(latest, "w") as f:
        json.dump(record, f, indent=2)
    return path


def task_constraints(agent: str, task: str) -> dict:
    reg = load_json(REGISTRY)
    return reg.get("agents", {}).get(agent, {}).get("tasks", {}).get(task, {})


def sandbox_enabled(env: dict) -> bool:
    val = env.get("HEXSTRIKE_SANDBOX", "").lower()
    return val in ("1", "true", "yes")


def enforce_task_policy(agent: str, task: str, env: dict) -> str | None:
    """Block offense/sandbox tasks when HEXSTRIKE_SANDBOX is not set."""
    if CONTROLLER.limits_disabled():
        env.setdefault("HEXSTRIKE_SANDBOX", "1")
        env.setdefault("DUAL_MODE_SANDBOX", "1")
        return None
    spec = task_constraints(agent, task)
    constraints = spec.get("constraints") or []
    if "sandbox-only" in constraints or "offense" in constraints:
        if not sandbox_enabled(env):
            return "Blocked: offense/sandbox task requires HEXSTRIKE_SANDBOX=1"
    return None


def run_agent(agent: str, task: str, env: dict | None = None, *, mode: str | None = None) -> dict:
    ok_auth, auth_msg = CONTROLLER.check_authorization()
    if not ok_auth:
        started = utc_now()
        return {
            "agent": agent,
            "task": task,
            "started_at": started,
            "finished_at": utc_now(),
            "exit_code": 3,
            "stdout": "",
            "stderr": f"Authorization blocked: {auth_msg}",
            "success": False,
            "blocked": True,
        }

    agent_key = f"{agent}:{task}"
    run_mode = mode or (env or {}).get("HEXSTRIKE_MODE") or os.environ.get("HEXSTRIKE_MODE")
    try:
        CONTROLLER.acquire(agent_key, mode=run_mode)
    except RuntimeError as exc:
        started = utc_now()
        return {
            "agent": agent,
            "task": task,
            "started_at": started,
            "finished_at": utc_now(),
            "exit_code": 4,
            "stdout": "",
            "stderr": str(exc),
            "success": False,
            "blocked": True,
        }

    proc_env = os.environ.copy()
    if env:
        proc_env.update({k.upper() if k.islower() else k: str(v) for k, v in env.items()})

    spec = task_constraints(agent, task)
    for k, v in (spec.get("env") or {}).items():
        proc_env[k.upper() if k.islower() else k] = str(v)

    blocked = enforce_task_policy(agent, task, proc_env)
    if blocked:
        started = utc_now()
        return {
            "agent": agent,
            "task": task,
            "started_at": started,
            "finished_at": utc_now(),
            "exit_code": 2,
            "stdout": "",
            "stderr": blocked,
            "success": False,
            "blocked": True,
        }

    cmd = [sys.executable, str(AGENT_RUNNER), "--agent", agent, "--task", task]
    started = utc_now()
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), env=proc_env, capture_output=True, text=True)
    finally:
        CONTROLLER.release(agent_key)
    return {
        "agent": agent,
        "task": task,
        "started_at": started,
        "finished_at": utc_now(),
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip()[-2000:],
        "stderr": proc.stderr.strip()[-2000:],
        "success": proc.returncode == 0,
    }


def task_output_path(agent: str, task: str) -> Path | None:
    reg = load_json(REGISTRY)
    spec = reg.get("agents", {}).get(agent, {}).get("tasks", {})
    if not isinstance(spec, dict) or task not in spec:
        return None
    out = spec[task].get("output")
    return (ROOT / out) if out else None


def parse_stdout_output(stdout: str) -> Path | None:
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("{") and "output" in line:
            try:
                data = json.loads(line)
                if data.get("output"):
                    return Path(data["output"])
            except json.JSONDecodeError:
                pass
    return None


def extract_highlights(path: Path, data: object) -> list[str]:
    lines: list[str] = []
    name = path.name
    if not isinstance(data, dict):
        return [f"{name}: (non-json artifact)"]

    if name == "entity-id.json":
        er = data.get("entity_resolution", {})
        lines.append(f"Entity: {er.get('status')} (confidence: {er.get('confidence')})")
        prim = data.get("methods", {}).get("first_funder_analysis", {}).get("primary_inflow", {})
        if prim:
            lines.append(f"Primary inflow: {prim.get('amount_usdt')} USDT from {prim.get('label', prim.get('from'))}")
        bs = data.get("methods", {}).get("blockscan_multichain", {})
        if bs.get("net_worth_usd"):
            lines.append(f"Multichain net worth: ${bs.get('net_worth_usd'):,.0f}")

    elif name == "multichain-cluster.json":
        nw = data.get("blockscan", {}).get("multichain_net_worth_usd")
        if nw:
            lines.append(f"Net worth: ${nw:,.0f}")
        alloc = data.get("portfolio_allocation", {})
        if alloc.get("base_usdc"):
            lines.append(f"BASE USDC: ${alloc['base_usdc'].get('usd', 0):,.0f}")
        if alloc.get("bsc_bsc_usd"):
            lines.append(f"BSC stable: ${alloc['bsc_bsc_usd'].get('usd', 0):,.0f}")
        er = data.get("entity_resolution_update", {})
        lines.append(f"Entity: {er.get('status')} — {er.get('new_evidence', '')[:120]}")

    elif name == "jenkins-cve-report.json":
        cves = data.get("cves_march_2023_advisory", [])
        lines.append(f"Jenkins {data.get('target', '?')}: {len(cves)} known CVEs")
        for c in cves[:3]:
            lines.append(f"  • {c.get('cve')} ({c.get('severity')}): {c.get('title', '')[:80]}")
        if len(cves) > 3:
            lines.append(f"  … +{len(cves) - 3} more (see report)")

    elif name == "target-recon-bundle.json":
        summary = data.get("summary", {})
        lines.append(summary.get("headline", f"{data.get('wallet_count', 0)} wallets"))
        for w in (data.get("wallets") or [])[:5]:
            v = w.get("verdict", {})
            live = w.get("live", {})
            lines.append(
                f"{w.get('role')}: risk={v.get('risk_level')} bal={live.get('balance_eth')} ETH nonce={live.get('nonce')}"
            )

    elif name == "target-conclusion.json":
        ov = data.get("overall", {})
        lines.append(f"Verdict: {ov.get('headline', '?')}")
        lines.append(f"Risk posture: {ov.get('risk_posture')} | Entity: {ov.get('entity_status')}")
        for c in (ov.get("conclusions") or [])[:4]:
            lines.append(c[:100])

    elif name == "target-profiles.json":
        lines.append(f"Wallets in catalog: {data.get('wallet_count', 0)}")
        for w in (data.get("wallets") or [])[:6]:
            lines.append(f"  {w.get('role')}: {w.get('address', '')[:12]}…")

    elif name == "target-recon-report.json":
        for chk in (data.get("checks") or []):
            lines.append(
                f"{chk.get('source')}: balance={chk.get('balance_wei')} nonce={chk.get('nonce')} chain={chk.get('chain_id')}"
            )
        lines.append(f"target: {data.get('target')}")

    elif name == "target-profile.json":
        pt = data.get("primary_target", {})
        lines.append(f"Hot wallet: {pt.get('address')} ({pt.get('chain')})")
        gs = pt.get("graph_summary", {})
        if gs.get("usdt_out_txs"):
            lines.append(f"USDT out txs (period): {gs.get('usdt_out_txs')}")
        rel = data.get("related_targets", {})
        if rel.get("authority"):
            lines.append(f"Authority: {rel.get('authority')}")

    elif name == "battle-report.json":
        s = data.get("summary", {})
        lines.append(f"Readiness: {s.get('readiness_score')}/100")
        lines.append(f"vuln={s.get('vuln_confirmed')} defended={s.get('defended')} inconclusive={s.get('inconclusive')}")

    elif name.startswith("report-") and "dual-mode" in str(path):
        lines.append(f"Mode: {data.get('mode')}")
        lines.append(f"Risks: {data.get('risk_count', 0)}")
        tools = data.get("tools_detected") or {}
        installed = [k for k, v in tools.items() if v]
        if installed:
            lines.append(f"Tools: {', '.join(installed)}")
        defense = data.get("defense", {})
        for rec in (defense.get("remediation_priority") or [])[:3]:
            lines.append(f"→ {rec}")

    elif name == "infra-targets.json":
        targets = data.get("infra_targets") or data.get("linked_ips") or []
        if isinstance(targets, list):
            for t in targets[:4]:
                if isinstance(t, dict):
                    ip = t.get("ip", t.get("id", "?"))
                    org = t.get("org", t.get("services", ""))
                    lines.append(f"Infra: {ip} {org}")

    elif name == "web-recon.json":
        for p in (data.get("probes") or [])[:3]:
            url = p.get("url")
            st = p.get("status", p.get("error", "?"))
            j = (p.get("headers") or {}).get("X-Jenkins")
            extra = f" Jenkins={j}" if j else ""
            lines.append(f"Probe {url}: {st}{extra}")

    else:
        # generic: top-level keys with scalar values
        for k, v in list(data.items())[:8]:
            if isinstance(v, (str, int, float, bool)) and k not in ("generated_at",):
                lines.append(f"{k}: {v}")

    return lines or [f"{name}: loaded ({len(json.dumps(data))} bytes)"]


def collect_findings(steps: list[dict]) -> dict:
    artifacts: dict[str, object] = {}
    highlights: list[dict] = []

    for step in steps:
        agent, task = step.get("agent"), step.get("task")
        paths: list[Path] = []
        p = task_output_path(agent, task) if agent and task else None
        if p:
            paths.append(p)
        sp = parse_stdout_output(step.get("stdout", ""))
        if sp and sp not in paths:
            paths.append(sp)

        for path in paths:
            if not path.is_file():
                highlights.append({"file": str(path), "missing": True, "lines": [f"MISSING: {path}"]})
                continue
            if path.suffix == ".json":
                try:
                    data = load_json(path)
                    artifacts[str(path.relative_to(ROOT))] = data
                    hl = extract_highlights(path, data)
                except Exception as e:
                    hl = [f"Error reading {path.name}: {e}"]
                    data = None
            elif path.suffix == ".md":
                text = path.read_text(encoding="utf-8", errors="replace")
                artifacts[str(path.relative_to(ROOT))] = {"_markdown_preview": text[:1500]}
                hl = [f"Markdown report: {path.name} ({len(text)} chars)"]
            else:
                hl = [f"File: {path.name}"]
            highlights.append({"file": str(path.relative_to(ROOT)), "agent": agent, "task": task, "lines": hl})

    return {"artifacts": artifacts, "highlights": highlights}


def print_findings_report(findings: dict, run_id: str) -> None:
    print("\n" + "=" * 60)
    print(f"FINDINGS REPORT — run {run_id}")
    print("=" * 60)
    for block in findings.get("highlights", []):
        print(f"\n📄 {block['file']}")
        if block.get("missing"):
            print("   ⚠️  artifact not found")
            continue
        if block.get("agent"):
            print(f"   ({block['agent']} / {block.get('task')})")
        for line in block.get("lines", []):
            print(f"   • {line}")
    print("\n" + "-" * 60)
    print(f"Full JSON bundle: artifacts/orchestrator/{run_id}-findings.json")
    print("=" * 60 + "\n")


def finalize_run(record: dict, print_all: bool = True) -> Path:
    steps = record.get("steps") or ([record["step"]] if record.get("step") else [])
    findings = collect_findings(steps)
    run_id = record["run_id"]
    bundle = {
        "run_id": run_id,
        "workflow": record.get("workflow"),
        "success": record.get("success"),
        "finished_at": record.get("finished_at"),
        "findings": findings,
    }
    out = LOG_DIR / f"{run_id}-findings.json"
    with open(out, "w") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)
    record["findings_path"] = str(out)
    log_run(record)
    if print_all:
        print_findings_report(findings, run_id)
    return out


def run_workflow(name: str, env: dict | None = None, print_all: bool = True) -> int:
    wf_data = load_json(WORKFLOWS)
    workflows = wf_data.get("workflows", {})
    if name not in workflows:
        print(json.dumps({"success": False, "error": f"Unknown workflow: {name}", "known": list(workflows)}))
        return 1

    wf = workflows[name]
    run_id = uuid.uuid4().hex[:12]
    steps_out: list[dict] = []
    completed: set[str] = set()
    step_env = dict(wf.get("env", {}))
    step_env.update(env or {})
    step_env["ORCHESTRATOR_RUN_ID"] = run_id
    step_env["ORCHESTRATOR_WORKFLOW"] = name

    mode = wf.get("mode") or os.environ.get("HEXSTRIKE_MODE")
    ok_auth, auth_msg = CONTROLLER.check_authorization()
    if not ok_auth:
        print(json.dumps({"success": False, "error": f"Authorization: {auth_msg}"}))
        return 3
    mode_prefix = f"mode={mode} " if mode else ""
    print(f"▶ {mode_prefix}workflow={name} run_id={run_id} steps={len(wf.get('steps', []))}")

    for i, step in enumerate(wf.get("steps", []), 1):
        agent = step["agent"]
        task = step["task"]
        dep = step.get("depends_on")
        optional = step.get("optional", False)

        if dep and dep not in completed:
            # depends_on matches prior task name
            pass  # sequential order already enforces deps

        print(f"  [{i}/{len(wf['steps'])}] {agent} / {task}")
        result = run_agent(agent, task, step_env, mode=mode)
        steps_out.append(result)
        completed.add(task)

        if not result["success"] and not optional:
            record = {
                "run_id": run_id,
                "type": "workflow",
                "workflow": name,
                "started_at": steps_out[0]["started_at"] if steps_out else utc_now(),
                "finished_at": utc_now(),
                "success": False,
                "failed_step": result,
                "steps": steps_out,
            }
            log_path = log_run(record)
            finalize_run(record, print_all=print_all)
            print(json.dumps({"success": False, "run_id": run_id, "log": str(log_path)}, indent=2))
            return 1

    record = {
        "run_id": run_id,
        "type": "workflow",
        "workflow": name,
        "description": wf.get("description"),
        "started_at": steps_out[0]["started_at"] if steps_out else utc_now(),
        "finished_at": utc_now(),
        "success": True,
        "steps": steps_out,
    }
    log_path = log_run(record)
    findings_path = finalize_run(record, print_all=print_all)
    print(json.dumps({
        "success": True,
        "run_id": run_id,
        "log": str(log_path),
        "findings": str(findings_path),
        "steps": len(steps_out),
    }, indent=2))
    return 0


def run_job(job: dict, print_all: bool = True) -> int:
    """Single job file: { "workflow": "..." } or { "agent": "...", "task": "..." }"""
    env = job.get("env", {})
    if "workflow" in job:
        return run_workflow(job["workflow"], env, print_all=print_all)
    if "agent" in job and "task" in job:
        result = run_agent(job["agent"], job["task"], env)
        record = {
            "run_id": uuid.uuid4().hex[:12],
            "type": "single",
            "success": result["success"],
            "step": result,
            "steps": [result],
            "finished_at": utc_now(),
        }
        finalize_run(record, print_all=print_all)
        return 0 if result["success"] else 1
    print(json.dumps({"success": False, "error": "Job needs workflow or agent+task"}))
    return 1


def watch_queue(poll_sec: float = 2.0) -> int:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    (QUEUE_DIR / "done").mkdir(exist_ok=True)
    (QUEUE_DIR / "failed").mkdir(exist_ok=True)
    print(f"Watching {QUEUE_DIR} (Ctrl+C to stop)")
    while True:
        for path in sorted(QUEUE_DIR.glob("*.json")):
            if path.parent.name != "queue":
                continue
            try:
                job = load_json(path)
                print(f"▶ job {path.name}")
                code = run_job(job)
                dest = QUEUE_DIR / ("done" if code == 0 else "failed") / path.name
                path.rename(dest)
            except Exception as e:
                print(f"✗ {path.name}: {e}")
                path.rename(QUEUE_DIR / "failed" / path.name)
        time.sleep(poll_sec)


def list_workflows() -> None:
    wf = load_json(WORKFLOWS).get("workflows", {})
    for name, spec in wf.items():
        n = len(spec.get("steps", []))
        print(f"{name:24} ({n} steps) — {spec.get('description', '')}")


VPS_RUN_ALL = ["vps-full-readonly"]


def run_all(env: dict | None = None, print_all: bool = True) -> int:
    """Run VPS-oriented workflow chain to completion."""
    print("=" * 60)
    print("HEXSTRIKE VPS FULL RUN")
    print("=" * 60)
    failed = 0
    for name in VPS_RUN_ALL:
        code = run_workflow(name, env, print_all=print_all)
        if code != 0:
            failed += 1
    print("\n" + "=" * 60)
    print(f"VPS RUN COMPLETE — workflows={len(VPS_RUN_ALL)} failed={failed}")
    master = ROOT / "artifacts" / "vps-master-report.json"
    if master.exists():
        print(f"Master report: {master}")
    print("=" * 60 + "\n")
    return 1 if failed else 0


def main() -> int:
    p = argparse.ArgumentParser(description="HexStrike Orchestrator — agent dispatcher")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("workflows", help="List workflows")

    run_p = sub.add_parser("run", help="Run a workflow")
    run_p.add_argument("workflow")
    run_p.add_argument("--target", help="Set TARGET env for agents")
    run_p.add_argument("--quiet", action="store_true", help="Skip findings summary on stdout")

    disp = sub.add_parser("dispatch", help="Run single agent task")
    disp.add_argument("agent")
    disp.add_argument("task")
    disp.add_argument("--target")
    disp.add_argument("--quiet", action="store_true")

    enq = sub.add_parser("enqueue", help="Copy job JSON into agents/queue/")
    enq.add_argument("job_file")

    sub.add_parser("watch", help="Process agents/queue/*.json")

    sub.add_parser("run-all", help="Run full VPS workflow chain (vps-full-readonly)")

    st = sub.add_parser("status", help="Show last orchestrator run")
    st.add_argument("--run-id")

    rep = sub.add_parser("report", help="Print all findings from a run")
    rep.add_argument("--run-id", help="Default: latest run")
    rep.add_argument("--json", action="store_true", help="Output raw findings JSON")

    args = p.parse_args()
    env = {}
    if getattr(args, "target", None):
        env["TARGET"] = args.target

    if args.cmd == "workflows":
        list_workflows()
        return 0
    if args.cmd == "run":
        return run_workflow(args.workflow, env or None, print_all=not args.quiet)
    if args.cmd == "dispatch":
        r = run_agent(args.agent, args.task, env or None)
        record = {
            "run_id": uuid.uuid4().hex[:12],
            "type": "dispatch",
            "success": r["success"],
            "step": r,
            "steps": [r],
            "finished_at": utc_now(),
        }
        finalize_run(record, print_all=not args.quiet)
        return 0 if r["success"] else 1
    if args.cmd == "enqueue":
        src = Path(args.job_file)
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        dest = QUEUE_DIR / src.name
        dest.write_bytes(src.read_bytes())
        print(json.dumps({"queued": str(dest)}))
        return 0
    if args.cmd == "watch":
        try:
            watch_queue()
        except KeyboardInterrupt:
            return 0
    if args.cmd == "run-all":
        return run_all(env or None, print_all=not getattr(args, "quiet", False))
    if args.cmd == "status":
        path = LOG_DIR / (f"{args.run_id}.json" if args.run_id else "latest.json")
        if not path.exists():
            print(json.dumps({"error": "no runs yet"}))
            return 1
        print(path.read_text())
        return 0
    if args.cmd == "report":
        run_id = args.run_id
        if not run_id:
            latest = load_json(LOG_DIR / "latest.json")
            run_id = latest.get("run_id")
        findings_path = LOG_DIR / f"{run_id}-findings.json"
        if not findings_path.exists():
            # rebuild from run log
            run_path = LOG_DIR / f"{run_id}.json"
            if not run_path.exists():
                print(json.dumps({"error": f"no run {run_id}"}))
                return 1
            record = load_json(run_path)
            finalize_run(record, print_all=False)
        bundle = load_json(findings_path)
        if args.json:
            print(json.dumps(bundle, indent=2, ensure_ascii=False))
        else:
            print_findings_report(bundle.get("findings", {}), run_id)
        return 0

    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
