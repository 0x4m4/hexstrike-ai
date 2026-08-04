#!/usr/bin/env python3
"""Run a registered HexStrike agent task from agents/registry.json."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REGISTRY = os.path.join(ROOT, "agents/registry.json")


def load_registry() -> dict:
    with open(REGISTRY) as f:
        return json.load(f)


def list_agents(reg: dict) -> None:
    for name, cfg in reg.get("agents", {}).items():
        tasks = cfg.get("tasks")
        if isinstance(tasks, dict):
            task_names = ", ".join(tasks.keys())
        elif isinstance(tasks, list):
            task_names = ", ".join(tasks)
        else:
            task_names = str(tasks or "-")
        print(f"{name:22} [{cfg.get('role', '?')}] tasks: {task_names}")


def run_task(agent: str, task: str, output: str | None, extra: dict) -> int:
    reg = load_registry()
    agents = reg.get("agents", {})
    if agent not in agents:
        print(json.dumps({"success": False, "error": f"Unknown agent: {agent}", "known": list(agents)}))
        return 1

    cfg = agents[agent]
    tasks = cfg.get("tasks", {})
    if isinstance(tasks, list):
        print(json.dumps({"success": False, "error": f"Agent {agent} is orchestrator-only", "delegates": tasks}))
        return 1
    if task not in tasks:
        print(json.dumps({"success": False, "error": f"Unknown task {task}", "available": list(tasks.keys())}))
        return 1

    spec = tasks[task]
    script = spec.get("script")
    if not script:
        print(json.dumps({"success": False, "error": "Task has no script runner", "spec": spec}))
        return 1

    script_path = os.path.join(ROOT, script)
    if not os.path.isfile(script_path):
        print(json.dumps({"success": False, "error": f"Script missing: {script_path}"}))
        return 1

    env = os.environ.copy()
    out_file = output or spec.get("output")
    if out_file:
        env["OUTPUT"] = os.path.join(ROOT, out_file) if not os.path.isabs(out_file) else out_file
    if spec.get("input"):
        env["INPUT"] = os.path.join(ROOT, spec["input"])
    for k, v in (spec.get("env") or {}).items():
        env[k.upper() if k.islower() else k] = str(v)

    for k, v in extra.items():
        env[k.upper()] = str(v)
    env["HEXSTRIKE_TASK"] = task

    if script_path.endswith(".py"):
        cmd = [sys.executable, script_path, task]
    elif script_path.endswith(".sh"):
        cmd = ["bash", script_path]
    else:
        cmd = [script_path]

    print(f"→ {agent} / {task} via {script}")
    proc = subprocess.run(cmd, cwd=ROOT, env=env)
    return proc.returncode


def main() -> int:
    p = argparse.ArgumentParser(description="HexStrike agent runner")
    p.add_argument("--agent", help="Agent id, e.g. Agent-OSINT-03")
    p.add_argument("--task", help="Task name, e.g. infra-mapping")
    p.add_argument("--output", help="Override output artifact path")
    p.add_argument("--list", action="store_true", help="List registered agents")
    p.add_argument("--config", default=REGISTRY, help="Registry JSON path")
    args, rest = p.parse_known_args()

    registry_path = args.config

    if args.list or (not args.agent and not args.task):
        with open(registry_path) as f:
            list_agents(json.load(f))
        return 0

    if not args.agent or not args.task:
        p.error("--agent and --task required (or use --list)")

    extra = {}
    for i in range(0, len(rest) - 1, 2):
        if rest[i].startswith("--"):
            extra[rest[i].lstrip("-").replace("-", "_")] = rest[i + 1]

    with open(registry_path) as f:
        reg = json.load(f)
    # inline run with loaded registry
    agents = reg.get("agents", {})
    if args.agent not in agents:
        print(json.dumps({"success": False, "error": f"Unknown agent: {args.agent}", "known": list(agents)}))
        return 1
    cfg = agents[args.agent]
    tasks = cfg.get("tasks", {})
    if isinstance(tasks, list):
        print(json.dumps({"success": False, "error": f"Agent {args.agent} is orchestrator-only", "delegates": tasks}))
        return 1
    if args.task not in tasks:
        print(json.dumps({"success": False, "error": f"Unknown task {args.task}", "available": list(tasks.keys())}))
        return 1
    spec = tasks[args.task]
    script = spec.get("script")
    if not script:
        print(json.dumps({"success": False, "error": "Task has no script runner", "spec": spec}))
        return 1
    script_path = os.path.join(ROOT, script)
    if not os.path.isfile(script_path):
        print(json.dumps({"success": False, "error": f"Script missing: {script_path}"}))
        return 1
    env = os.environ.copy()
    out_file = args.output or spec.get("output")
    if out_file:
        env["OUTPUT"] = os.path.join(ROOT, out_file) if not os.path.isabs(out_file) else out_file
    if spec.get("input"):
        env["INPUT"] = os.path.join(ROOT, spec["input"])
    for k, v in (spec.get("env") or {}).items():
        env[k.upper() if k.islower() else k] = str(v)
    for k, v in extra.items():
        env[k.upper()] = str(v)
    env["HEXSTRIKE_TASK"] = args.task
    if script_path.endswith(".py"):
        cmd = [sys.executable, script_path, args.task]
    elif script_path.endswith(".sh"):
        cmd = ["bash", script_path]
    else:
        cmd = [script_path]
    print(f"→ {args.agent} / {args.task} via {script}")
    proc = subprocess.run(cmd, cwd=ROOT, env=env)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
