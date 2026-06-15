#!/usr/bin/env python3
"""
HexStrike + Local Ollama Agent
==============================

Drive HexStrike scans from a natural-language prompt using a LOCAL Ollama model.
The model plans which security tools to run (via tool-calling), the tools execute
through the HexStrike server (/api/command), and the model then TRIAGES the raw
output to reduce false positives and produce a concise report.

Design goals:
  * Local-only LLM (Ollama) -> no cloud calls
  * Real tool execution through HexStrike (nuclei, nikto, sqlmap, tech probe)
  * Authorization gate: active scans require --authorized and a target you may test
  * False-positive reduction via an explicit LLM triage pass over structured output

Usage:
  python3 hexstrike_ollama_agent.py \
      --authorized \
      --target http://testphp.vulnweb.com \
      --prompt "Find high/critical web vulns and filter false positives" \
      --model qwen2.5:14b

Add --deep to also run nikto + sqlmap (slower). Without --authorized only
passive analysis runs.
"""

import argparse
import json
import sys
import time
from typing import Any, Dict, List

import requests

DEFAULT_OLLAMA = "http://127.0.0.1:11434"
DEFAULT_HEXSTRIKE = "http://127.0.0.1:8888"
DEFAULT_MODEL = "qwen2.5:14b"

# Targets explicitly published/authorized for security-tool testing.
KNOWN_AUTHORIZED = (
    "testphp.vulnweb.com",
    "testhtml5.vulnweb.com",
    "testasp.vulnweb.com",
    "scanme.nmap.org",
    "127.0.0.1",
    "localhost",
)


def log(msg: str) -> None:
    print(f"[agent] {msg}", flush=True)


# ---------------------------------------------------------------------------
# HexStrike tool wrappers (executed through the HexStrike server)
# ---------------------------------------------------------------------------
class HexStrike:
    def __init__(self, base_url: str, timeout: int = 600):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> Dict[str, Any]:
        r = requests.get(f"{self.base}/health", timeout=15)
        r.raise_for_status()
        return r.json()

    def command(self, command: str, use_cache: bool = True) -> Dict[str, Any]:
        """Run a shell command through HexStrike's process manager."""
        r = requests.post(
            f"{self.base}/api/command",
            json={"command": command, "use_cache": use_cache},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def analyze_target(self, target: str) -> Dict[str, Any]:
        r = requests.post(
            f"{self.base}/api/intelligence/analyze-target",
            json={"target": target},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()


def _truncate(text: str, limit: int = 6000) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]..."


# Each tool returns a compact dict the LLM can reason over.
def tool_analyze_target(hx: HexStrike, target: str, **_) -> Dict[str, Any]:
    data = hx.analyze_target(target)
    prof = data.get("target_profile", {})
    return {
        "target_type": prof.get("target_type"),
        "risk_level": prof.get("risk_level"),
        "attack_surface_score": prof.get("attack_surface_score"),
        "technologies": prof.get("technologies"),
        "ip_addresses": prof.get("ip_addresses"),
    }


def tool_tech_probe(hx: HexStrike, target: str, **_) -> Dict[str, Any]:
    res = hx.command(f"curl -s -I -L --max-time 20 {target}")
    return {"headers": _truncate(res.get("stdout", ""), 2000), "success": res.get("success")}


def tool_run_nuclei(hx: HexStrike, target: str, severity: str = "critical,high,medium", **_) -> Dict[str, Any]:
    # -j => JSONL findings on stdout (structured => better triage, fewer FPs)
    cmd = f"nuclei -u {target} -severity {severity} -j -no-color -stats -timeout 10"
    res = hx.command(cmd, use_cache=False)
    findings = []
    for line in (res.get("stdout") or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            j = json.loads(line)
        except Exception:
            continue
        info = j.get("info", {})
        findings.append({
            "template": j.get("template-id"),
            "name": info.get("name"),
            "severity": info.get("severity"),
            "matched_at": j.get("matched-at") or j.get("host"),
            "type": j.get("type"),
        })
    return {"count": len(findings), "findings": findings[:50], "success": res.get("success")}


def tool_run_nikto(hx: HexStrike, target: str, **_) -> Dict[str, Any]:
    res = hx.command(f"nikto -h {target} -maxtime 90s -ask no", use_cache=False)
    return {"output": _truncate(res.get("stdout", ""), 5000), "success": res.get("success")}


def tool_run_sqlmap(hx: HexStrike, target: str, **_) -> Dict[str, Any]:
    cmd = (
        f"sqlmap -u '{target}' --batch --smart --level=1 --risk=1 "
        f"--crawl=1 --random-agent --flush-session --disable-coloring"
    )
    res = hx.command(cmd, use_cache=False)
    out = res.get("stdout", "")
    injectable = "is vulnerable" in out.lower() or "sqlmap identified" in out.lower()
    return {"injectable": injectable, "output": _truncate(out, 5000), "success": res.get("success")}


TOOL_IMPL = {
    "analyze_target": tool_analyze_target,
    "tech_probe": tool_tech_probe,
    "run_nuclei": tool_run_nuclei,
    "run_nikto": tool_run_nikto,
    "run_sqlmap": tool_run_sqlmap,
}

# JSON-schema tool definitions advertised to Ollama.
def tool_specs(deep: bool) -> List[Dict[str, Any]]:
    specs = [
        {
            "type": "function",
            "function": {
                "name": "analyze_target",
                "description": "Profile the target (type, risk, technologies). Passive.",
                "parameters": {
                    "type": "object",
                    "properties": {"target": {"type": "string"}},
                    "required": ["target"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "tech_probe",
                "description": "Fetch HTTP response headers to fingerprint the server. Passive.",
                "parameters": {
                    "type": "object",
                    "properties": {"target": {"type": "string"}},
                    "required": ["target"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_nuclei",
                "description": "Run nuclei template-based vulnerability scan (structured JSON output).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string"},
                        "severity": {"type": "string", "description": "comma list e.g. critical,high"},
                    },
                    "required": ["target"],
                },
            },
        },
    ]
    if deep:
        specs += [
            {
                "type": "function",
                "function": {
                    "name": "run_nikto",
                    "description": "Run nikto web server misconfiguration scan (slower).",
                    "parameters": {
                        "type": "object",
                        "properties": {"target": {"type": "string"}},
                        "required": ["target"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_sqlmap",
                    "description": "Run sqlmap to confirm SQL injection (active exploitation, slower).",
                    "parameters": {
                        "type": "object",
                        "properties": {"target": {"type": "string"}},
                        "required": ["target"],
                    },
                },
            },
        ]
    return specs


# ---------------------------------------------------------------------------
# Ollama chat with tool-calling
# ---------------------------------------------------------------------------
class Ollama:
    def __init__(self, base_url: str, model: str):
        self.base = base_url.rstrip("/")
        self.model = model

    def chat(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"model": self.model, "messages": messages, "stream": False}
        if tools:
            payload["tools"] = tools
        r = requests.post(f"{self.base}/api/chat", json=payload, timeout=600)
        r.raise_for_status()
        return r.json()


SYSTEM_PROMPT = (
    "You are a penetration-testing orchestration agent. You may ONLY test the single "
    "authorized target provided by the user. Use the available tools to gather evidence, "
    "then produce a concise findings report. Prefer high-confidence, evidence-backed "
    "findings and explicitly flag anything likely to be a false positive. Always pass the "
    "exact authorized target to every tool. Do not invent findings."
)

TRIAGE_PROMPT = (
    "Below is the structured output collected from the security tools. Produce a final "
    "report with: (1) a one-line target summary, (2) CONFIRMED findings with severity and "
    "the evidence (matched URL/template), (3) LIKELY FALSE POSITIVES with the reason, and "
    "(4) recommended next steps. Be concise. Do not list a finding as confirmed without "
    "evidence from the tool output."
)


def run_agent(prompt: str, target: str, hx: HexStrike, llm: Ollama, deep: bool, max_iters: int) -> str:
    tools = tool_specs(deep)
    collected: Dict[str, Any] = {}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Authorized target: {target}\nTask: {prompt}"},
    ]

    # ---- Tool-calling loop -------------------------------------------------
    for i in range(max_iters):
        resp = llm.chat(messages, tools=tools)
        msg = resp.get("message", {}) or {}
        calls = msg.get("tool_calls") or []
        messages.append(msg)

        if not calls:
            # Model produced prose; stop the loop and move to triage.
            break

        for call in calls:
            fn = call.get("function", {})
            name = fn.get("name")
            args = fn.get("arguments")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            args = args or {}
            # Force the authorized target regardless of what the model passed.
            args["target"] = target

            impl = TOOL_IMPL.get(name)
            if not impl:
                result = {"error": f"unknown tool {name}"}
            else:
                log(f"iter {i+1}: running tool {name} ...")
                t0 = time.time()
                try:
                    result = impl(hx, **args)
                except Exception as e:  # keep the loop alive on tool error
                    result = {"error": str(e)}
                log(f"    {name} done in {time.time()-t0:.1f}s")
            collected[name] = result
            messages.append({"role": "tool", "name": name, "content": json.dumps(result)[:8000]})

    # ---- Deterministic safety net -----------------------------------------
    # Guarantee we actually scanned, even if the model under-called tools.
    if "analyze_target" not in collected:
        collected["analyze_target"] = tool_analyze_target(hx, target)
    if "run_nuclei" not in collected:
        log("safety-net: running nuclei (model did not call it)")
        collected["run_nuclei"] = tool_run_nuclei(hx, target)

    # ---- Triage pass (false-positive reduction) ---------------------------
    triage_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": TRIAGE_PROMPT + "\n\nTOOL OUTPUT (JSON):\n" + json.dumps(collected)[:18000]},
    ]
    final = llm.chat(triage_messages)
    return final.get("message", {}).get("content", "(no report produced)")


def main() -> int:
    ap = argparse.ArgumentParser(description="HexStrike + local Ollama pentest agent")
    ap.add_argument("--target", default="http://testphp.vulnweb.com")
    ap.add_argument("--prompt", default="Scan for high/critical web vulnerabilities and filter false positives.")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--ollama", default=DEFAULT_OLLAMA)
    ap.add_argument("--hexstrike", default=DEFAULT_HEXSTRIKE)
    ap.add_argument("--authorized", action="store_true", help="Confirm you are authorized to test the target")
    ap.add_argument("--deep", action="store_true", help="Also run nikto + sqlmap (slower, active)")
    ap.add_argument("--max-iters", type=int, default=6)
    args = ap.parse_args()

    hx = HexStrike(args.hexstrike)
    llm = Ollama(args.ollama, args.model)

    # Connectivity checks
    try:
        h = hx.health()
        log(f"HexStrike healthy: {h.get('total_tools_available')} tools available")
    except Exception as e:
        log(f"ERROR: cannot reach HexStrike at {args.hexstrike}: {e}")
        return 2

    # Authorization gate for ACTIVE scanning
    host = args.target.split("//")[-1].split("/")[0].split(":")[0]
    is_known = any(host == k or host.endswith(k) for k in KNOWN_AUTHORIZED)
    if not args.authorized and not is_known:
        log("Refusing active scan: target is not a known authorized test target and "
            "--authorized was not provided. Re-run with --authorized only if you have "
            "written permission to test this target.")
        # Passive analysis only
        prof = tool_analyze_target(hx, args.target)
        print(json.dumps({"passive_analysis": prof}, indent=2))
        return 0

    log(f"model={args.model}  target={args.target}  deep={args.deep}")
    report = run_agent(args.prompt, args.target, hx, llm, args.deep, args.max_iters)

    print("\n" + "=" * 70)
    print("FINAL REPORT")
    print("=" * 70)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
