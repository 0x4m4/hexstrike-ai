#!/usr/bin/env python3
"""
HexStrike Orchestration Engine
==============================

Adds a composable orchestration layer on top of the HexStrike API:

- Tool chains  : named, ordered sequences of API tool calls with template
                 parameter substitution ({target}, {param.X}, {steps.NAME.f})
- Skills       : reusable capability bundles (tool endpoints + guidance)
- Agents       : profiles that own skills and chains; may list subagents
                 they delegate to (for AI clients to drive)
- Workflows    : phased pipelines over chains with success gating, run in
                 the background and tracked by run id

Everything is data-driven: the defaults below can be extended or overridden
without code changes by dropping JSON files into ~/.hexstrike/orchestration/
({\"kind\": \"chain|skill|agent|workflow\", ...} per file).

The engine executes chain steps by calling this server's own public API
(/api/tools/<tool>), so orchestration is pure API composition and always
stays in sync with what the tools endpoints actually accept.
"""

import json
import os
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_BASE_URL = os.environ.get("HEXSTRIKE_API_URL", "http://127.0.0.1:8888")
STEP_TIMEOUT = int(os.environ.get("HEXSTRIKE_CHAIN_STEP_TIMEOUT", "300"))
OUTPUT_CAP = 4000          # chars of tool output kept per step in a run record
MAX_RUNS = 200             # finished runs kept for status queries
HEALTH_CACHE_TTL = 60

# ============================================================================
# DEFAULT TOOL CHAINS
# ============================================================================
# target_type tells callers what to pass: domain | url | ip | image | freeform
DEFAULT_TOOL_CHAINS: Dict[str, Dict[str, Any]] = {
    "recon-passive": {
        "description": "Passive reconnaissance: subdomain enumeration and "
                       "historical URL discovery. No direct traffic to the "
                       "target beyond passive source queries.",
        "target_type": "domain",
        "tags": ["recon", "passive"],
        "steps": [
            {"tool": "subfinder",
             "params": {"domain": "{target}", "silent": True, "all_sources": True}},
            {"tool": "gau",
             "params": {"domain": "{target}", "include_subs": True}},
            {"tool": "waybackurls",
             "params": {"domain": "{target}"}},
        ],
    },
    "port-scan": {
        "description": "Port discovery with rustscan followed by nmap service "
                       "and default-script detection on the same host.",
        "target_type": "ip",
        "tags": ["recon", "active", "network"],
        "steps": [
            {"tool": "rustscan",
             "params": {"target": "{target}", "batch_size": 450,
                        "timeout": 30}},
            {"tool": "nmap",
             "params": {"target": "{target}", "scan_type": "-sV",
                        "additional_args": "-T4 -Pn"}},
        ],
    },
    "web-content-discovery": {
        "description": "Content and directory discovery against a web server "
                       "using three independent brute-forcers.",
        "target_type": "url",
        "tags": ["web", "discovery"],
        "steps": [
            {"tool": "feroxbuster",
             "params": {"url": "{target}", "threads": 50}},
            {"tool": "gobuster",
             "params": {"url": "{target}", "mode": "dir"}},
            {"tool": "dirsearch",
             "params": {"url": "{target}"}},
        ],
    },
    "web-content-discovery-insecure": {
        "description": "Directory discovery tolerant of self-signed or untrusted "
                       "TLS certificates — local/lab targets only. dirsearch is "
                       "optional (it needs REQUESTS_CA_BUNDLE in the server env "
                       "since it has no cert-skip flag).",
        "target_type": "url",
        "tags": ["web", "discovery"],
        "steps": [
            {"tool": "feroxbuster",
             "params": {"url": "{target}", "threads": 50,
                        "additional_args": "--insecure"}},
            {"tool": "gobuster",
             "params": {"url": "{target}", "mode": "dir",
                        "additional_args": "-k"}},
            {"tool": "dirsearch",
             "params": {"url": "{target}"},
             "optional": True},
        ],
    },
    "vuln-scan": {
        "description": "WAF detection followed by template-based vulnerability "
                       "scanning (critical/high/medium severities).",
        "target_type": "url",
        "tags": ["vuln", "web"],
        "steps": [
            {"tool": "wafw00f",
             "params": {"target": "{target}"}},
            {"tool": "nuclei",
             "params": {"target": "{target}",
                        "severity": "critical,high,medium"}},
        ],
    },
    "web-audit": {
        "description": "Web server audit: nikto baseline, WordPress checks "
                       "and XSS scanning where applicable.",
        "target_type": "url",
        "tags": ["web", "audit"],
        "steps": [
            {"tool": "nikto", "params": {"target": "{target}"}},
            {"tool": "wpscan", "params": {"url": "{target}"}, "optional": True},
            {"tool": "dalfox", "params": {"url": "{target}"}, "optional": True},
        ],
    },
    "cve-hunt": {
        "description": "Focused nuclei scan over CVE templates "
                       "(critical and high).",
        "target_type": "url",
        "tags": ["vuln", "cve"],
        "steps": [
            {"tool": "nuclei",
             "params": {"target": "{target}", "tags": "cve",
                        "severity": "critical,high"}},
        ],
    },
    "container-audit": {
        "description": "Vulnerability audit of a container image or filesystem "
                       "with trivy (critical/high).",
        "target_type": "image",
        "tags": ["cloud", "container"],
        "steps": [
            {"tool": "trivy",
             "params": {"scan_type": "image", "target": "{target}",
                        "severity": "critical,high"}},
        ],
    },
    "credential-audit": {
        "description": "Single-service credential audit with hydra. Requires "
                       "extra params: username and password.",
        "target_type": "ip",
        "tags": ["creds", "active"],
        "requires_params": ["username", "password", "service"],
        "steps": [
            {"tool": "hydra",
             "params": {"target": "{target}", "service": "{param.service}",
                        "username": "{param.username}",
                        "password": "{param.password}"}},
        ],
    },
    "full-recon": {
        "description": "Full reconnaissance against a domain: passive "
                       "discovery followed by technology-aware nuclei scan.",
        "target_type": "domain",
        "tags": ["recon", "full"],
        "steps": [
            {"tool": "subfinder",
             "params": {"domain": "{target}", "silent": True, "all_sources": True}},
            {"tool": "gau", "params": {"domain": "{target}", "include_subs": True}},
            {"tool": "waybackurls", "params": {"domain": "{target}"}},
            {"tool": "nuclei", "params": {"target": "{target}", "tags": "tech"},
             "optional": True},
        ],
    },
}

# ============================================================================
# DEFAULT SKILLS
# ============================================================================
DEFAULT_SKILLS: Dict[str, Dict[str, Any]] = {
    "network-recon": {
        "description": "Network reconnaissance: host discovery, port scanning, "
                       "service enumeration and share/user mapping.",
        "objective": "Map the attack surface of an IP range: live hosts, open "
                     "ports, services with versions, SMB/AD exposure.",
        "tool_endpoints": ["nmap", "rustscan", "masscan", "autorecon", "nbtscan",
                           "arp-scan", "enum4linux-ng", "enum4linux", "smbmap",
                           "netexec", "rpcclient", "responder"],
        "recommended_chains": ["port-scan", "recon-passive"],
        "instructions": (
            "1. Start with the port-scan chain for speed, follow up with "
            "targeted nmap service scans (-sV -sC) on interesting ports.\n"
            "2. For SMB/NetBIOS exposure use enum4linux-ng, smbmap and "
            "netexec; for AD environments add responder on the local side.\n"
            "3. Never run disruptive scans (masscan at high rate, hydra) "
            "without explicit approval and rate limits."
        ),
    },
    "web-application-security": {
        "description": "Web application testing: content discovery, WAF "
                       "detection, vulnerability scanning, XSS and CMS audits.",
        "objective": "Find exploitable web vulnerabilities: exposed paths, "
                     "known CVEs, injection points, misconfigurations.",
        "tool_endpoints": ["gobuster", "feroxbuster", "ffuf", "dirsearch",
                           "nikto", "nuclei", "wpscan", "sqlmap", "dalfox",
                           "wafw00f", "katana", "xsser", "wfuzz", "arjun",
                           "paramspider", "hakrawler", "httpx"],
        "recommended_chains": ["web-content-discovery", "web-audit", "vuln-scan"],
        "instructions": (
            "1. Identify the target URL and probe with wafw00f first; adjust "
            "evasion if a WAF answers.\n"
            "2. Content discovery (feroxbuster/gobuster) usually yields the "
            "highest-value leads; feed interesting paths to nuclei.\n"
            "3. Use sqlmap only on parameters you have confirmed are "
            "reflected/processed server-side; dalfox/xsser for XSS candidates.\n"
            "4. WordPress targets: wpscan with --enumerate."
        ),
    },
    "vulnerability-assessment": {
        "description": "Broad vulnerability assessment and CVE intelligence: "
                       "template scanning, exploit availability, severity "
                       "triage.",
        "objective": "Produce a severity-ranked list of confirmed "
                     "vulnerabilities with matching public exploits.",
        "tool_endpoints": ["nuclei", "nikto", "searchsploit", "msfvenom",
                           "metasploit", "trivy", "terrascan", "checkov"],
        "recommended_chains": ["vuln-scan", "cve-hunt", "container-audit"],
        "instructions": (
            "1. Run vuln-scan, then triage findings by severity and "
            "exploitability (searchsploit / Metasploit module availability).\n"
            "2. For images/infra use container-audit (trivy) and the cloud "
            "audit tools (checkov, terrascan, scout-suite, prowler).\n"
            "3. Report each finding with evidence, severity and the shortest "
            "remediation path."
        ),
    },
    "osint-intelligence": {
        "description": "Open-source intelligence: passive subdomain and URL "
                       "discovery, people/leak lookups, metadata extraction.",
        "objective": "Collect externally visible intelligence about an "
                     "organization or person without touching target systems.",
        "tool_endpoints": ["subfinder", "amass", "gau", "waybackurls",
                           "exiftool", "dnsenum", "fierce"],
        "recommended_chains": ["recon-passive"],
        "instructions": (
            "1. Start passive (subfinder/amass/gau/waybackurls) before any "
            "active probing.\n"
            "2. Historical URLs frequently leak forgotten endpoints and "
            "credentials; review gau/waybackurls output carefully.\n"
            "3. Respect rate limits of passive sources; stay within the "
            "passive scope unless explicitly authorized for active checks."
        ),
    },
    "binary-exploitation": {
        "description": "Binary exploitation and reverse engineering: "
                       "protections, gadgets, libc resolution, exploit "
                       "scaffolding.",
        "objective": "Turn a local binary into a working exploit: identify "
                     "protections, leak/overwrite strategy, ROP chain.",
        "tool_endpoints": ["checksec", "strings",
                           "objdump", "radare2", "ghidra", "gdb", "gdb-peda",
                           "ropgadget", "ropper", "one-gadget", "libc-database",
                           "pwninit", "pwntools", "angr", "x8"],
        "recommended_chains": [],
        "instructions": (
            "1. checksec first; then strings/objdump for quick wins, "
            "radare2/ghidra/gdb for deeper RE.\n"
            "2. For libc-dependent exploits use pwninit + libc-database to "
            "resolve the exact libc and one-gadget candidates.\n"
            "3. Build the exploit with pwntools; keep payloads ASLR-safe "
            "unless a leak is available."
        ),
    },
    "cloud-container-security": {
        "description": "Cloud and container posture: image scanning, "
                       "Kubernetes benchmarks, cloud provider audits.",
        "objective": "Assess cloud/container security posture and surface "
                     "misconfigurations with clear remediation.",
        "tool_endpoints": ["trivy", "kube-bench", "kube-hunter", "checkov",
                           "terrascan", "scout-suite", "prowler",
                           "docker-bench-security", "cloudmapper", "clair"],
        "recommended_chains": ["container-audit"],
        "instructions": (
            "1. Images: container-audit (trivy). Clusters: kube-bench "
            "(CIS) + kube-hunter (offensive view). Hosts: docker-bench.\n"
            "2. Cloud accounts: scout-suite (multi-cloud) or prowler "
            "(AWS-focused); results need credentials configured.\n"
            "3. Rank findings by real exposure (internet-facing, privilege "
            "escalation paths) rather than raw counts."
        ),
    },
}

# ============================================================================
# DEFAULT AGENTS (main + subagents)
# ============================================================================
DEFAULT_AGENTS: Dict[str, Dict[str, Any]] = {
    "recon-specialist": {
        "role": "Reconnaissance lead",
        "description": "Maps attack surface: subdomains, ports, services and "
                       "shares. Delegates detail work to subagents.",
        "system_prompt": (
            "You are a reconnaissance specialist. You enumerate before you "
            "assume: subdomains, then ports, then services, then shares. "
            "You stay passive as long as possible and clearly label every "
            "active step. You never exploit - you hand findings off."
        ),
        "skills": ["network-recon", "osint-intelligence"],
        "chains": ["recon-passive", "port-scan"],
        "subagents": ["subdomain-enumerator", "port-scanner"],
    },
    "web-vuln-hunter": {
        "role": "Web vulnerability hunter",
        "description": "Hunts web vulnerabilities: content discovery, WAF "
                       "awareness, template scanning, CMS and XSS checks.",
        "system_prompt": (
            "You are a web application vulnerability hunter. You work "
            "methodically: fingerprint, discover content, scan with templates, "
            "then validate anything promising manually. You never report an "
            "unvalidated finding as confirmed."
        ),
        "skills": ["web-application-security", "vulnerability-assessment"],
        "chains": ["web-content-discovery", "web-audit", "vuln-scan", "cve-hunt"],
        "subagents": ["content-discovery", "cve-scanner"],
    },
    "exploitation-specialist": {
        "role": "Exploitation / binary specialist",
        "description": "Validates exploitability: binary analysis, ROP, "
                       "public exploit adaptation (authorized testing only).",
        "system_prompt": (
            "You are a binary exploitation specialist. You prove "
            "exploitability safely: analyze, prototype, demonstrate impact "
            "with the least destructive proof possible, and document every "
            "step for reproduction."
        ),
        "skills": ["binary-exploitation", "vulnerability-assessment"],
        "chains": [],
        "subagents": [],
    },
    "reporting-analyst": {
        "role": "Findings triage and reporting",
        "description": "Aggregates orchestration runs, deduplicates findings "
                       "and produces severity-ranked summaries.",
        "system_prompt": (
            "You are a security reporting analyst. You turn raw scan output "
            "into a severity-ranked report: verified findings first, "
            "reproducible evidence, concise remediation per item."
        ),
        "skills": ["vulnerability-assessment"],
        "chains": [],
        "subagents": [],
    },
    # --- subagents (delegation targets for the agents above) ---
    "subdomain-enumerator": {
        "role": "Subagent: passive subdomain + URL discovery",
        "description": "Subagent of recon-specialist. Runs passive discovery "
                       "and returns the consolidated asset list.",
        "system_prompt": "Enumerate subdomains and historical URLs passively; "
                         "return a clean, deduplicated asset list.",
        "skills": ["osint-intelligence"],
        "chains": ["recon-passive"],
        "subagents": [],
    },
    "port-scanner": {
        "role": "Subagent: port and service scanning",
        "description": "Subagent of recon-specialist. Scans a host for open "
                       "ports and service versions.",
        "system_prompt": "Scan hosts for open ports and service versions; "
                         "return structured port/service findings.",
        "skills": ["network-recon"],
        "chains": ["port-scan"],
        "subagents": [],
    },
    "content-discovery": {
        "role": "Subagent: web content discovery",
        "description": "Subagent of web-vuln-hunter. Discovers hidden "
                       "content and returns interesting paths.",
        "system_prompt": "Discover hidden web content with multiple "
                         "brute-forcers; return deduplicated interesting paths.",
        "skills": ["web-application-security"],
        "chains": ["web-content-discovery"],
        "subagents": [],
    },
    "cve-scanner": {
        "role": "Subagent: template-based CVE scanning",
        "description": "Subagent of web-vuln-hunter. Runs nuclei CVE "
                       "templates and returns severity-ranked matches.",
        "system_prompt": "Run template-based CVE scans; return matches "
                         "ranked by severity with evidence.",
        "skills": ["vulnerability-assessment"],
        "chains": ["cve-hunt", "vuln-scan"],
        "subagents": [],
    },
}

# ============================================================================
# DEFAULT WORKFLOWS
# ============================================================================
DEFAULT_WORKFLOWS: Dict[str, Dict[str, Any]] = {
    "full-pentest": {
        "description": "End-to-end pipeline against a domain: passive recon, "
                       "port discovery, web audit, vulnerability scan. Later "
                       "phases only run when earlier ones succeed.",
        "target_type": "domain",
        "phases": [
            {"name": "Passive Recon", "chain": "recon-passive", "gate": "always"},
            {"name": "Port Discovery", "chain": "port-scan", "gate": "on_success"},
            {"name": "Web Audit", "chain": "web-audit", "gate": "on_success"},
            {"name": "Vulnerability Scan", "chain": "vuln-scan", "gate": "on_success"},
        ],
    },
    "web-app-audit": {
        "description": "Web-focused pipeline: content discovery, web audit, "
                       "vulnerability scan.",
        "target_type": "url",
        "phases": [
            {"name": "Content Discovery", "chain": "web-content-discovery",
             "gate": "always"},
            {"name": "Web Audit", "chain": "web-audit", "gate": "on_success"},
            {"name": "Vulnerability Scan", "chain": "vuln-scan", "gate": "on_success"},
        ],
    },
    "quick-triage": {
        "description": "Fast triage against a URL: WAF detection followed by "
                       "critical/high vulnerability templates.",
        "target_type": "url",
        "phases": [
            {"name": "Vulnerability Scan", "chain": "vuln-scan", "gate": "always"},
        ],
    },
}

_SEVERITY_RE = re.compile(r"\b(CRITICAL|HIGH|MEDIUM|LOW)\b")


class OrchestrationEngine:
    """Executes chains, agents and workflows; tracks runs in-memory."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.chains = {k: dict(v) for k, v in DEFAULT_TOOL_CHAINS.items()}
        self.skills = {k: dict(v) for k, v in DEFAULT_SKILLS.items()}
        self.agents = {k: dict(v) for k, v in DEFAULT_AGENTS.items()}
        self.workflows = {k: dict(v) for k, v in DEFAULT_WORKFLOWS.items()}
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._run_events: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        self._health: Optional[Dict[str, Any]] = None
        self._health_ts: float = 0.0
        self._load_overrides()

    # ------------------------------------------------------------------ data
    def _load_overrides(self) -> None:
        """Merge user-supplied JSON definitions from ~/.hexstrike/orchestration."""
        ovr_dir = os.path.expanduser("~/.hexstrike/orchestration")
        if not os.path.isdir(ovr_dir):
            return
        buckets = {"chain": self.chains, "skill": self.skills,
                   "agent": self.agents, "workflow": self.workflows}
        for fname in sorted(os.listdir(ovr_dir)):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(ovr_dir, fname)) as fh:
                    docs = json.load(fh)
                if isinstance(docs, dict):
                    docs = [docs]
                for doc in docs:
                    bucket = buckets.get(doc.get("kind"))
                    name = doc.get("name")
                    if bucket is not None and name:
                        doc.pop("kind", None)
                        bucket[name] = doc
            except Exception:
                continue

    def overview(self) -> Dict[str, Any]:
        return {
            "success": True,
            "tool_chains": {"count": len(self.chains),
                            "names": sorted(self.chains)},
            "skills": {"count": len(self.skills), "names": sorted(self.skills)},
            "agents": {"count": len(self.agents), "names": sorted(self.agents)},
            "workflows": {"count": len(self.workflows),
                          "names": sorted(self.workflows)},
            "active_runs": sum(1 for r in self._runs.values()
                               if r["status"] == "running"),
        }

    def list_chains(self) -> Dict[str, Any]:
        return {"success": True, "chains": [
            {"name": n, "description": c.get("description", ""),
             "target_type": c.get("target_type", "freeform"),
             "tags": c.get("tags", []), "steps": len(c.get("steps", [])),
             "requires_params": c.get("requires_params", [])}
            for n, c in sorted(self.chains.items())]}

    def get_chain(self, name: str) -> Dict[str, Any]:
        chain = self.chains.get(name)
        if not chain:
            return {"success": False, "error": f"Unknown tool chain: {name}",
                    "available": sorted(self.chains)}
        return {"success": True, "name": name, **chain}

    def list_skills(self) -> Dict[str, Any]:
        return {"success": True, "skills": [
            {"name": n, "description": s.get("description", ""),
             "recommended_chains": s.get("recommended_chains", []),
             "tool_count": len(s.get("tool_endpoints", []))}
            for n, s in sorted(self.skills.items())]}

    def get_skill(self, name: str) -> Dict[str, Any]:
        skill = self.skills.get(name)
        if not skill:
            return {"success": False, "error": f"Unknown skill: {name}",
                    "available": sorted(self.skills)}
        return {"success": True, "name": name, **skill}

    def list_agents(self) -> Dict[str, Any]:
        return {"success": True, "agents": [
            {"name": n, "role": a.get("role", ""),
             "description": a.get("description", ""),
             "skills": a.get("skills", []), "chains": a.get("chains", []),
             "subagents": a.get("subagents", []),
             "is_subagent": bool(a.get("subagents") is not None and
                                 not a.get("subagents") and
                                 a.get("role", "").startswith("Subagent"))}
            for n, a in sorted(self.agents.items())]}

    def get_agent(self, name: str) -> Dict[str, Any]:
        agent = self.agents.get(name)
        if not agent:
            return {"success": False, "error": f"Unknown agent: {name}",
                    "available": sorted(self.agents)}
        return {"success": True, "name": name, **agent}

    def list_workflows(self) -> Dict[str, Any]:
        return {"success": True, "workflows": [
            {"name": n, "description": w.get("description", ""),
             "target_type": w.get("target_type", "freeform"),
             "phases": [{"name": p.get("name"), "chain": p.get("chain"),
                         "gate": p.get("gate", "always")}
                        for p in w.get("phases", [])]}
            for n, w in sorted(self.workflows.items())]}

    def get_workflow(self, name: str) -> Dict[str, Any]:
        wf = self.workflows.get(name)
        if not wf:
            return {"success": False, "error": f"Unknown workflow: {name}",
                    "available": sorted(self.workflows)}
        return {"success": True, "name": name, **wf}

    # ------------------------------------------------------------- internals
    def _session(self, base_url: str) -> requests.Session:
        sess = requests.Session()
        if base_url.startswith("https://"):
            ca = os.environ.get("REQUESTS_CA_BUNDLE") or \
                os.environ.get("HEXSTRIKE_SSL_CERT") or \
                os.path.expanduser("~/.hexstrike/certs/server.crt")
            sess.verify = ca if os.path.isfile(ca) else False
        return sess

    def _tool_available(self, tool: str) -> Optional[bool]:
        """Best-effort availability from cached /health (None = unknown)."""
        now = time.time()
        if not self._health or now - self._health_ts > HEALTH_CACHE_TTL:
            try:
                r = requests.get(f"{self.base_url}/health", timeout=15,
                                 verify=self._session(self.base_url).verify)
                self._health = r.json()
                self._health_ts = now
            except Exception:
                return None
        status = (self._health or {}).get("tools_status", {})
        for key in (tool, tool.replace("_", "-"), tool.replace("-", "_")):
            if key in status:
                return bool(status[key])
        return None

    @staticmethod
    def _render(value: Any, ctx: Dict[str, Any]) -> Any:
        """Recursively substitute {target}, {param.X}, {steps.NAME[.field]}."""
        if isinstance(value, dict):
            return {k: OrchestrationEngine._render(v, ctx) for k, v in value.items()}
        if isinstance(value, list):
            return [OrchestrationEngine._render(v, ctx) for v in value]
        if not isinstance(value, str):
            return value
        out = value.replace("{target}", str(ctx.get("target", "")))

        def _param(m):
            return str(ctx.get("params", {}).get(m.group(1), m.group(0)))
        out = re.sub(r"\{param\.([A-Za-z0-9_]+)\}", _param, out)

        def _step(m):
            rec = ctx.get("steps", {}).get(m.group(1))
            if rec is None:
                return m.group(0)
            node: Any = rec.get("response", {})
            for part in (m.group(2) or "").split("."):
                if part:
                    if isinstance(node, dict):
                        node = node.get(part, "")
                    else:
                        return m.group(0)
            if isinstance(node, (dict, list)):
                node = json.dumps(node)
            return str(node)
        out = re.sub(r"\{steps\.([A-Za-z0-9_]+)(?:\.([A-Za-z0-9_.]+))?\}", _step, out)
        return out

    @staticmethod
    def _findings(output: str) -> Dict[str, int]:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for sev in _SEVERITY_RE.findall(output or ""):
            counts[sev.lower()] += 1
        return counts

    def _run_chain_sync(self, name: str, target: str, base_url: str,
                        extra_params: Optional[Dict[str, Any]] = None,
                        cancel_event: Optional[threading.Event] = None,
                        record: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        chain = self.chains[name]
        steps_out: List[Dict[str, Any]] = []
        ctx: Dict[str, Any] = {"target": target, "params": extra_params or {},
                               "steps": {}}
        sess = self._session(base_url)
        t0 = time.time()
        overall = "success"
        for i, step in enumerate(chain.get("steps", []), 1):
            tool = step.get("tool", "")
            if cancel_event is not None and cancel_event.is_set():
                overall = "cancelled"
                break
            available = self._tool_available(tool)
            if available is False:
                rec = {"step": i, "tool": tool, "status": "skipped",
                       "reason": "tool not installed"}
                steps_out.append(rec)
                if not step.get("optional"):
                    overall = "failed"
                    break
                continue
            params = self._render(step.get("params", {}), ctx)
            st0 = time.time()
            rec = {"step": i, "tool": tool,
                   "endpoint": f"/api/tools/{tool}", "params": params}
            try:
                resp = sess.post(f"{base_url}/api/tools/{tool}", json=params,
                                 timeout=STEP_TIMEOUT)
                rec["http_status"] = resp.status_code
                try:
                    body = resp.json()
                except Exception:
                    body = {"raw": resp.text[:OUTPUT_CAP]}
                rec["response"] = body
                rec["success"] = bool(body.get("success")) and resp.ok
                out = str(body.get("stdout") or body.get("output") or
                          body.get("error") or "")[:OUTPUT_CAP]
                rec["output"] = out
                rec["findings"] = self._findings(out)
                rec["status"] = "ok" if rec["success"] else "error"
                if not rec["success"] and not step.get("optional") \
                        and not step.get("continue_on_error"):
                    overall = "failed"
            except Exception as exc:
                rec.update({"status": "error", "success": False,
                            "error": str(exc)})
                if not step.get("optional") and not step.get("continue_on_error"):
                    overall = "failed"
            rec["duration_s"] = round(time.time() - st0, 2)
            steps_out.append(rec)
            ctx["steps"][tool] = rec
            if record is not None:
                record["steps"] = steps_out
            if overall == "failed":
                break
        if cancel_event is not None and cancel_event.is_set():
            overall = "cancelled"
        result = {
            "kind": "chain", "name": name, "target": target,
            "status": overall if overall != "success" or not steps_out else
                      ("partial" if any(s.get("status") != "ok" for s in steps_out)
                       else "success"),
            "started_at": t0, "finished_at": time.time(),
            "duration_s": round(time.time() - t0, 2),
            "steps": steps_out,
            "findings": self._aggregate_findings(steps_out),
        }
        return result

    @staticmethod
    def _aggregate_findings(steps: List[Dict[str, Any]]) -> Dict[str, int]:
        agg = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for s in steps:
            for k, v in (s.get("findings") or {}).items():
                agg[k] += v
        return agg

    # -------------------------------------------------------------- public
    def run_chain(self, name: str, target: str,
                  base_url: Optional[str] = None,
                  params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run a tool chain synchronously and return the full record."""
        if name not in self.chains:
            return self.get_chain(name)
        base = (base_url or self.base_url).rstrip("/")
        run_id = "chain-" + uuid.uuid4().hex[:12]
        record: Dict[str, Any] = {"id": run_id, "status": "running",
                                  "created_at": time.time()}
        with self._lock:
            self._runs[run_id] = record
        result = self._run_chain_sync(name, target, base, params, None, record)
        result["id"] = run_id
        record.update(result)
        self._evict_old_runs()
        return result

    def _pipeline(self, run_id: str, kind: str, name: str, target: str,
                  base: str, phases: List[Dict[str, Any]]) -> None:
        record = self._runs[run_id]
        cancel = self._run_events[run_id]
        t0 = time.time()
        phase_out: List[Dict[str, Any]] = []
        overall = "success"
        prev_ok = True
        for phase in phases:
            gate = phase.get("gate", "always")
            pname = phase.get("name") or phase.get("chain") or "?"
            if gate == "on_success" and not prev_ok:
                phase_out.append({"name": pname, "status": "skipped",
                                  "reason": "previous phase did not succeed"})
                prev_ok = False
                continue
            if cancel.is_set():
                overall = "cancelled"
                break
            chain_result = self._run_chain_sync(
                phase["chain"], target, base, None, cancel, record)
            phase_out.append({"name": pname, "chain": phase.get("chain"),
                              "gate": gate, "status": chain_result["status"],
                              "duration_s": chain_result["duration_s"],
                              "findings": chain_result["findings"],
                              "steps": chain_result["steps"]})
            prev_ok = chain_result["status"] in ("success", "partial")
            if chain_result["status"] == "cancelled":
                overall = "cancelled"
                break
            if not prev_ok and gate == "on_success":
                overall = "partial"
        agg = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for p in phase_out:
            for k, v in (p.get("findings") or {}).items():
                agg[k] += v
        statuses = [p["status"] for p in phase_out]
        if cancel.is_set() or "cancelled" in statuses:
            final_status = "cancelled"
        elif not statuses:
            final_status = overall
        elif all(s == "failed" for s in statuses):
            final_status = "failed"
        elif any(s != "success" for s in statuses):
            final_status = "partial"
        else:
            final_status = "success"
        with self._lock:
            record.update({
                "status": final_status,
                "phases": phase_out, "findings": agg,
                "finished_at": time.time(),
                "duration_s": round(time.time() - t0, 2),
            })
            self._run_events.pop(run_id, None)
        self._evict_old_runs()

    def start_workflow(self, name: str, target: str,
                       base_url: Optional[str] = None) -> Dict[str, Any]:
        wf = self.workflows.get(name)
        if not wf:
            return self.get_workflow(name)
        return self._start_pipeline("workflow", name, target,
                                    (base_url or self.base_url).rstrip("/"),
                                    wf.get("phases", []))

    def start_agent(self, name: str, target: str,
                    base_url: Optional[str] = None) -> Dict[str, Any]:
        agent = self.agents.get(name)
        if not agent:
            return self.get_agent(name)
        chains = agent.get("chains", [])
        if not chains:
            return {"success": False,
                    "error": f"Agent '{name}' has no runnable chains "
                             "(it is a delegation/reporting profile)"}
        phases = [{"name": c, "chain": c, "gate": "always"} for c in chains]
        return self._start_pipeline("agent", name, target,
                                    (base_url or self.base_url).rstrip("/"),
                                    phases)

    def _start_pipeline(self, kind: str, name: str, target: str,
                        base: str, phases: List[Dict[str, Any]]) -> Dict[str, Any]:
        run_id = f"{kind}-" + uuid.uuid4().hex[:12]
        record = {"id": run_id, "kind": kind, "name": name, "target": target,
                  "status": "running", "created_at": time.time(),
                  "phases": [], "findings": {}}
        event = threading.Event()
        with self._lock:
            self._runs[run_id] = record
            self._run_events[run_id] = event
        thread = threading.Thread(target=self._pipeline,
                                  args=(run_id, kind, name, target, base, phases),
                                  daemon=True)
        thread.start()
        return {"success": True, "run_id": run_id, "kind": kind, "name": name,
                "status": "running",
                "status_url": f"/api/orchestration/runs/{run_id}"}

    def get_run(self, run_id: str) -> Dict[str, Any]:
        record = self._runs.get(run_id)
        if record is None:
            return {"success": False, "error": f"Unknown run: {run_id}",
                    "active_runs": sorted(self._runs)[-10:]}
        return {"success": True, **record}

    def list_runs(self, limit: int = 20) -> Dict[str, Any]:
        recent = sorted(self._runs.values(),
                        key=lambda r: r.get("created_at", 0), reverse=True)
        return {"success": True, "runs": [
            {"id": r.get("id"), "kind": r.get("kind", "chain"),
             "name": r.get("name"), "target": r.get("target"),
             "status": r.get("status"), "created_at": r.get("created_at"),
             "duration_s": r.get("duration_s"),
             "findings": r.get("findings", {})}
            for r in recent[:limit]]}

    def cancel_run(self, run_id: str) -> Dict[str, Any]:
        event = self._run_events.get(run_id)
        record = self._runs.get(run_id)
        if record is None:
            return {"success": False, "error": f"Unknown run: {run_id}"}
        if event is None:
            return {"success": False,
                    "error": f"Run {run_id} is not cancellable "
                             f"(status: {record.get('status')})"}
        event.set()
        with self._lock:
            if record.get("status") == "running":
                record["status"] = "cancelling"
        return {"success": True, "run_id": run_id,
                "message": "cancellation requested"}

    def _evict_old_runs(self) -> None:
        with self._lock:
            if len(self._runs) <= MAX_RUNS:
                return
            finished = sorted((r for r in self._runs.values()
                               if r.get("status") != "running"),
                              key=lambda r: r.get("created_at", 0))
            for rec in finished[:len(self._runs) - MAX_RUNS]:
                self._runs.pop(rec.get("id"), None)
