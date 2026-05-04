"""
Praetorian Tools Module - Comprehensive Security Testing Suite
Blueprint for HexStrike AI server

Integrates the full Praetorian open-source toolset:
  noseyparker  - Secrets scanning across files/git/GitHub
  titus        - High-performance secrets scanner with validation
  fingerprintx - Service fingerprinting (170+ protocols)
  brutus       - Fast credential testing (SSH/MySQL/MSSQL/RDP/etc.)
  nerva        - Service fingerprinting CLI (TCP/UDP/SCTP)
  hadrian      - API security testing (REST/GraphQL/gRPC)
  trajan       - CI/CD vulnerability detection (GitHub/GitLab/ADO)
  vespasian    - API discovery from captured traffic
  julius       - LLM service identification
  MCPHammer    - MCP security testing framework
  aurelian     - Cloud security reconnaissance (AWS/Azure/GCP)
  NTLMRecon    - NTLM endpoint discovery
  gokart       - Static analysis for Go code
  trident      - Automated password spraying
"""

import logging
import os
import shlex
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

GOPATH_BIN   = Path("/home/kali/gopath/bin")
MCPHAMMER_DIR = Path("/home/kali/hexstrike-ai/tools/mcphammer")
HEXSTRIKE_ENV_PYTHON = Path("/home/kali/hexstrike-ai/hexstrike-env/bin/python3")

praetorian_bp = Blueprint("praetorian", __name__, url_prefix="/api/praetorian")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: str, timeout: int = 300, env: dict = None) -> dict:
    run_env = (env or os.environ.copy())
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=timeout, env=run_env,
        )
        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "command": cmd,
            "timestamp": datetime.now().isoformat(),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timed out after {timeout}s",
                "command": cmd, "timestamp": datetime.now().isoformat()}
    except Exception as exc:
        return {"success": False, "error": str(exc),
                "command": cmd, "timestamp": datetime.now().isoformat()}


def _bin(name: str) -> str:
    return str(GOPATH_BIN / name)


# ---------------------------------------------------------------------------
# noseyparker - Secrets Scanner
# ---------------------------------------------------------------------------

@praetorian_bp.route("/noseyparker/scan", methods=["POST"])
def noseyparker_scan():
    """
    Scan files, directories, or git repos for secrets using noseyparker.

    Body fields:
      targets (list|str): Paths, URLs, or git repo URLs to scan (required)
      datastore (str): Path to datastore directory (default: /tmp/np-datastore)
      git_url (str): Single git repo URL to scan
      github_user (str): GitHub username to scan all repos
      github_org (str): GitHub org to scan all repos
      output_format (str): text | json | jsonl (default: json)
      rules (str): Custom rules file path
      ignore (list): Paths to ignore
      additional_args (str): Extra noseyparker arguments
    """
    try:
        p = request.json or {}
        targets = p.get("targets", [])
        datastore = p.get("datastore", "/tmp/np-datastore")
        git_url = p.get("git_url", "")
        github_user = p.get("github_user", "")
        github_org = p.get("github_org", "")
        output_format = p.get("output_format", "json")

        cmd = f"{_bin('noseyparker')} scan --datastore {shlex.quote(datastore)}"

        if git_url:
            cmd += f" --git-url {shlex.quote(git_url)}"
        if github_user:
            cmd += f" --github-user {shlex.quote(github_user)}"
        if github_org:
            cmd += f" --github-org {shlex.quote(github_org)}"
        if p.get("rules"):
            cmd += f" --rules {shlex.quote(p['rules'])}"
        for ign in (p.get("ignore") or []):
            cmd += f" --ignore {shlex.quote(ign)}"
        if isinstance(targets, str):
            targets = [targets]
        for t in targets:
            cmd += f" {shlex.quote(t)}"
        if p.get("additional_args"):
            cmd += f" {p['additional_args']}"

        logger.info(f"🔍 noseyparker scan started")
        scan_result = _run(cmd, timeout=600)

        # Run report after scan
        report_cmd = (f"{_bin('noseyparker')} report --datastore {shlex.quote(datastore)}"
                      f" --format {shlex.quote(output_format)}")
        report_result = _run(report_cmd, timeout=60)

        return jsonify({
            "scan": scan_result,
            "report": report_result,
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as exc:
        logger.error(f"💥 noseyparker error: {exc}")
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# titus - High-Performance Secrets Scanner
# ---------------------------------------------------------------------------

@praetorian_bp.route("/titus/scan", methods=["POST"])
def titus_scan():
    """
    Scan for secrets using titus with optional API validation.

    Body fields:
      path (str): File or directory path to scan (required)
      git (bool): Include git history in scan
      validate (bool): Validate secrets against live APIs
      output_format (str): json | sarif (default: json)
      extract (str): Extraction mode e.g. "all"
      additional_args (str): Extra titus arguments
    """
    try:
        p = request.json or {}
        path = p.get("path", "")
        if not path:
            return jsonify({"error": "path is required"}), 400

        cmd = f"{_bin('titus')} scan {shlex.quote(path)}"
        if p.get("git"):
            cmd += " --git"
        if p.get("validate"):
            cmd += " --validate"
        if p.get("output_format"):
            cmd += f" --format {shlex.quote(p['output_format'])}"
        if p.get("extract"):
            cmd += f" --extract={shlex.quote(p['extract'])}"
        if p.get("additional_args"):
            cmd += f" {p['additional_args']}"

        logger.info(f"🔑 titus scan: {path}")
        return jsonify(_run(cmd, timeout=300))
    except Exception as exc:
        logger.error(f"💥 titus error: {exc}")
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# fingerprintx - Service Fingerprinting
# ---------------------------------------------------------------------------

@praetorian_bp.route("/fingerprintx/scan", methods=["POST"])
def fingerprintx_scan():
    """
    Fingerprint services on open ports using fingerprintx.

    Body fields:
      targets (list|str): host:port targets (required)
      targets_file (str): File path with one host:port per line
      udp (bool): Include UDP scanning
      fast (bool): Fast mode
      timeout_ms (int): Timeout in milliseconds
      output_format (str): json (default) or text
      additional_args (str): Extra fingerprintx arguments
    """
    try:
        p = request.json or {}
        targets = p.get("targets", [])
        targets_file = p.get("targets_file", "")

        if not targets and not targets_file:
            return jsonify({"error": "targets or targets_file is required"}), 400

        cmd = f"{_bin('fingerprintx')}"
        if p.get("output_format", "json") == "json":
            cmd += " --json"
        if p.get("udp"):
            cmd += " -U"
        if p.get("fast"):
            cmd += " -f"
        if p.get("timeout_ms"):
            cmd += f" -w {int(p['timeout_ms'])}"
        if targets_file:
            cmd += f" -l {shlex.quote(targets_file)}"
        if isinstance(targets, str):
            targets = [t.strip() for t in targets.split(",")]
        for t in targets:
            cmd += f" -t {shlex.quote(t)}"
        if p.get("additional_args"):
            cmd += f" {p['additional_args']}"

        logger.info(f"🔭 fingerprintx scan: {targets or targets_file}")
        return jsonify(_run(cmd, timeout=300))
    except Exception as exc:
        logger.error(f"💥 fingerprintx error: {exc}")
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# brutus - Credential Testing
# ---------------------------------------------------------------------------

@praetorian_bp.route("/brutus/scan", methods=["POST"])
def brutus_scan():
    """
    Test credentials against network services using brutus.

    Body fields:
      target (str): Target host (required)
      protocol (str): Protocol — ssh/mysql/mssql/rdp/ftp/smtp/pop3/imap/ldap (required)
      username (str): Single username
      username_file (str): File with usernames
      password (str): Single password
      password_file (str): File with passwords
      threads (int): Concurrent threads
      json_output (bool): Output as JSON (default true)
      additional_args (str): Extra brutus arguments
    """
    try:
        p = request.json or {}
        target = p.get("target", "")
        protocol = p.get("protocol", "")
        if not target or not protocol:
            return jsonify({"error": "target and protocol are required"}), 400

        cmd = f"{_bin('brutus')} --target {shlex.quote(target)} --protocol {shlex.quote(protocol)}"
        if p.get("username"):
            cmd += f" -u {shlex.quote(p['username'])}"
        if p.get("username_file"):
            cmd += f" -U {shlex.quote(p['username_file'])}"
        if p.get("password"):
            cmd += f" -p {shlex.quote(p['password'])}"
        if p.get("password_file"):
            cmd += f" -P {shlex.quote(p['password_file'])}"
        if p.get("threads"):
            cmd += f" -t {int(p['threads'])}"
        if p.get("json_output", True):
            cmd += " --json"
        if p.get("additional_args"):
            cmd += f" {p['additional_args']}"

        logger.info(f"🔐 brutus credential test: {target} ({protocol})")
        return jsonify(_run(cmd, timeout=600))
    except Exception as exc:
        logger.error(f"💥 brutus error: {exc}")
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# nerva - Service Fingerprinting CLI
# ---------------------------------------------------------------------------

@praetorian_bp.route("/nerva/scan", methods=["POST"])
def nerva_scan():
    """
    Fingerprint services using nerva (170+ TCP/UDP/SCTP protocols).

    Body fields:
      targets (list|str): host:port targets (required)
      targets_file (str): File with targets
      udp (bool): UDP mode
      sctp (bool): SCTP mode
      output_format (str): json | csv (default: json)
      timeout_ms (int): Timeout in milliseconds
      workers (int): Concurrent workers
      misconfigs (bool): Check for misconfigurations
      additional_args (str): Extra nerva arguments
    """
    try:
        p = request.json or {}
        targets = p.get("targets", [])
        targets_file = p.get("targets_file", "")
        if not targets and not targets_file:
            return jsonify({"error": "targets or targets_file is required"}), 400

        cmd = f"{_bin('nerva')}"
        if p.get("output_format", "json") == "json":
            cmd += " --json"
        elif p.get("output_format") == "csv":
            cmd += " --csv"
        if p.get("udp"):
            cmd += " -U"
        if p.get("sctp"):
            cmd += " -S"
        if p.get("timeout_ms"):
            cmd += f" -w {int(p['timeout_ms'])}"
        if p.get("workers"):
            cmd += f" -W {int(p['workers'])}"
        if p.get("misconfigs"):
            cmd += " --misconfigs"
        if targets_file:
            cmd += f" -l {shlex.quote(targets_file)}"
        if isinstance(targets, str):
            targets = [t.strip() for t in targets.split(",")]
        for t in targets:
            cmd += f" -t {shlex.quote(t)}"
        if p.get("additional_args"):
            cmd += f" {p['additional_args']}"

        logger.info(f"🔭 nerva fingerprint: {targets or targets_file}")
        return jsonify(_run(cmd, timeout=300))
    except Exception as exc:
        logger.error(f"💥 nerva error: {exc}")
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# hadrian - API Security Testing
# ---------------------------------------------------------------------------

@praetorian_bp.route("/hadrian/test", methods=["POST"])
def hadrian_test():
    """
    Test API security for REST, GraphQL, or gRPC using hadrian.

    Body fields:
      api_type (str): rest | graphql | grpc (required)
      api_url (str): Target API URL (required)
      roles_file (str): YAML roles/auth config file
      auth_file (str): Auth configuration file
      output_format (str): json (default)
      dry_run (bool): Show tests without executing
      llm_provider (str): openai | anthropic (for AI-assisted testing)
      proxy (str): HTTP proxy URL
      additional_args (str): Extra hadrian arguments
    """
    try:
        p = request.json or {}
        api_type = p.get("api_type", "")
        api_url = p.get("api_url", "")
        if not api_type or not api_url:
            return jsonify({"error": "api_type and api_url are required"}), 400

        cmd = f"{_bin('hadrian')} test {shlex.quote(api_type)} --api {shlex.quote(api_url)}"
        if p.get("roles_file"):
            cmd += f" --roles {shlex.quote(p['roles_file'])}"
        if p.get("auth_file"):
            cmd += f" --auth {shlex.quote(p['auth_file'])}"
        if p.get("output_format", "json") == "json":
            cmd += " --output json"
        if p.get("dry_run"):
            cmd += " --dry-run"
        if p.get("llm_provider"):
            cmd += f" --llm-provider {shlex.quote(p['llm_provider'])}"
        if p.get("proxy"):
            cmd += f" --proxy {shlex.quote(p['proxy'])}"
        if p.get("additional_args"):
            cmd += f" {p['additional_args']}"

        logger.info(f"🌐 hadrian API test: {api_type} {api_url}")
        return jsonify(_run(cmd, timeout=600))
    except Exception as exc:
        logger.error(f"💥 hadrian error: {exc}")
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# trajan - CI/CD Vulnerability Detection
# ---------------------------------------------------------------------------

@praetorian_bp.route("/trajan/scan", methods=["POST"])
def trajan_scan():
    """
    Scan CI/CD pipelines for vulnerabilities using trajan.

    Body fields:
      platform (str): github | gitlab | ado (required)
      repo (str): owner/repo for GitHub repo scan
      org (str): Organization name for full org scan
      group (str): GitLab group name
      output_format (str): json (default)
      additional_args (str): Extra trajan arguments

    Env vars (set before starting server):
      GITHUB_TOKEN, GITLAB_TOKEN, ADO_TOKEN
    """
    try:
        p = request.json or {}
        platform = p.get("platform", "")
        if not platform:
            return jsonify({"error": "platform is required (github/gitlab/ado)"}), 400

        cmd = f"{_bin('trajan')} {shlex.quote(platform)} scan"
        if p.get("repo"):
            cmd += f" --repo {shlex.quote(p['repo'])}"
        if p.get("org"):
            cmd += f" --org {shlex.quote(p['org'])}"
        if p.get("group"):
            cmd += f" --group {shlex.quote(p['group'])}"
        if p.get("output_format", "json") == "json":
            cmd += " -o json"
        if p.get("additional_args"):
            cmd += f" {p['additional_args']}"

        logger.info(f"🔧 trajan CI/CD scan: {platform} {p.get('repo') or p.get('org', '')}")
        return jsonify(_run(cmd, timeout=300))
    except Exception as exc:
        logger.error(f"💥 trajan error: {exc}")
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# vespasian - API Discovery
# ---------------------------------------------------------------------------

@praetorian_bp.route("/vespasian/scan", methods=["POST"])
def vespasian_scan():
    """
    Discover and map API attack surface using vespasian.

    Body fields:
      url (str): Target URL to crawl (required for scan/crawl mode)
      mode (str): scan | crawl | import | generate (default: scan)
      api_type (str): rest | graphql | wsdl
      output (str): Output file path
      auth_headers (list): Auth headers e.g. ["Authorization: Bearer token"]
      probe (bool): Active probe discovered endpoints
      proxy (str): HTTP proxy URL
      import_format (str): burp | har | mitmproxy (for import mode)
      import_file (str): File to import
      additional_args (str): Extra vespasian arguments
    """
    try:
        p = request.json or {}
        mode = p.get("mode", "scan")
        url = p.get("url", "")

        cmd = f"{_bin('vespasian')} {shlex.quote(mode)}"

        if mode in ("scan", "crawl"):
            if not url:
                return jsonify({"error": "url is required for scan/crawl mode"}), 400
            cmd += f" {shlex.quote(url)}"
        elif mode == "import":
            import_format = p.get("import_format", "")
            import_file = p.get("import_file", "")
            if not import_format or not import_file:
                return jsonify({"error": "import_format and import_file are required for import mode"}), 400
            cmd += f" {shlex.quote(import_format)} {shlex.quote(import_file)}"

        if p.get("api_type"):
            cmd += f" --api-type {shlex.quote(p['api_type'])}"
        if p.get("output"):
            cmd += f" -o {shlex.quote(p['output'])}"
        for h in (p.get("auth_headers") or []):
            cmd += f" -H {shlex.quote(h)}"
        if p.get("probe"):
            cmd += " --probe"
        if p.get("proxy"):
            cmd += f" --proxy {shlex.quote(p['proxy'])}"
        if p.get("additional_args"):
            cmd += f" {p['additional_args']}"

        logger.info(f"🕸️ vespasian API discovery: {mode} {url}")
        return jsonify(_run(cmd, timeout=600))
    except Exception as exc:
        logger.error(f"💥 vespasian error: {exc}")
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# julius - LLM Service Identification
# ---------------------------------------------------------------------------

@praetorian_bp.route("/julius/probe", methods=["POST"])
def julius_probe():
    """
    Identify LLM services on open ports using julius.

    Body fields:
      targets (list|str): host:port targets (required)
      targets_file (str): File with one host:port per line
      output_format (str): table | json | jsonl (default: json)
      concurrency (int): Concurrent probes (default 10)
      timeout (int): Timeout in seconds
      verbose (bool): Verbose output
      additional_args (str): Extra julius arguments
    """
    try:
        p = request.json or {}
        targets = p.get("targets", [])
        targets_file = p.get("targets_file", "")
        if not targets and not targets_file:
            return jsonify({"error": "targets or targets_file is required"}), 400

        cmd = f"{_bin('julius')} probe"
        if p.get("output_format", "json") in ("json", "jsonl"):
            cmd += f" -o {shlex.quote(p.get('output_format', 'json'))}"
        if p.get("concurrency"):
            cmd += f" -c {int(p['concurrency'])}"
        if p.get("timeout"):
            cmd += f" -t {int(p['timeout'])}"
        if p.get("verbose"):
            cmd += " -v"
        if targets_file:
            cmd += f" -f {shlex.quote(targets_file)}"
        if isinstance(targets, str):
            targets = [t.strip() for t in targets.split(",")]
        for t in targets:
            cmd += f" {shlex.quote(t)}"
        if p.get("additional_args"):
            cmd += f" {p['additional_args']}"

        logger.info(f"🤖 julius LLM probe: {targets or targets_file}")
        return jsonify(_run(cmd, timeout=300))
    except Exception as exc:
        logger.error(f"💥 julius error: {exc}")
        return jsonify({"error": str(exc)}), 500


@praetorian_bp.route("/julius/list", methods=["GET"])
def julius_list():
    """List available julius probes."""
    return jsonify(_run(f"{_bin('julius')} list", timeout=15))


# ---------------------------------------------------------------------------
# MCPHammer - MCP Security Testing
# ---------------------------------------------------------------------------

@praetorian_bp.route("/mcphammer/run", methods=["POST"])
def mcphammer_run():
    """
    Run the MCPHammer MCP security testing framework.

    Body fields:
      config_server_url (str): MCP server URL to test (required)
      port (int): MCPHammer listener port (default 3000)
      additional_args (str): Extra MCPHammer arguments
    """
    try:
        p = request.json or {}
        config_server_url = p.get("config_server_url", "")
        port = p.get("port", 3000)

        mcphammer_script = MCPHAMMER_DIR / "MCPHammer.py"
        if not mcphammer_script.exists():
            return jsonify({"error": "MCPHammer not found at expected path"}), 500

        cmd = f"{HEXSTRIKE_ENV_PYTHON} {mcphammer_script} --port {int(port)}"
        if config_server_url:
            cmd += f" --config-server-url {shlex.quote(config_server_url)}"
        if p.get("additional_args"):
            cmd += f" {p['additional_args']}"

        logger.info(f"🔨 MCPHammer: testing {config_server_url or 'localhost'}")
        return jsonify(_run(cmd, timeout=120))
    except Exception as exc:
        logger.error(f"💥 MCPHammer error: {exc}")
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# aurelian - Cloud Security Reconnaissance
# ---------------------------------------------------------------------------

@praetorian_bp.route("/aurelian/recon", methods=["POST"])
def aurelian_recon():
    """
    Perform cloud security reconnaissance using aurelian.

    Body fields:
      cloud (str): aws | azure | gcp (required)
      module (str): Recon module e.g. whoami, find-secrets, public-resources, graph (required)
      neo4j_uri (str): Neo4j URI for graph module
      output_format (str): json (default)
      additional_args (str): Extra aurelian arguments

    Env vars (set before starting server):
      AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN
      AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID
      GOOGLE_APPLICATION_CREDENTIALS
    """
    try:
        p = request.json or {}
        cloud = p.get("cloud", "")
        module = p.get("module", "")
        if not cloud or not module:
            return jsonify({"error": "cloud and module are required"}), 400

        cmd = f"{_bin('aurelian')} {shlex.quote(cloud)} recon {shlex.quote(module)}"
        if p.get("neo4j_uri"):
            cmd += f" --neo4j-uri {shlex.quote(p['neo4j_uri'])}"
        if p.get("output_format", "json") == "json":
            cmd += " --output json"
        if p.get("additional_args"):
            cmd += f" {p['additional_args']}"

        logger.info(f"☁️  aurelian recon: {cloud} {module}")
        return jsonify(_run(cmd, timeout=300))
    except Exception as exc:
        logger.error(f"💥 aurelian error: {exc}")
        return jsonify({"error": str(exc)}), 500


@praetorian_bp.route("/aurelian/list-modules", methods=["GET"])
def aurelian_list_modules():
    """List all available aurelian recon modules."""
    cloud = request.args.get("cloud", "aws")
    return jsonify(_run(f"{_bin('aurelian')} {shlex.quote(cloud)} list-modules", timeout=15))


# ---------------------------------------------------------------------------
# NTLMRecon - NTLM Endpoint Discovery
# ---------------------------------------------------------------------------

@praetorian_bp.route("/ntlmrecon/scan", methods=["POST"])
def ntlmrecon_scan():
    """
    Discover NTLM-enabled HTTP endpoints using NTLMRecon.

    Body fields:
      target (str): Target URL (required)
      host_header (str): Custom Host header override
      json_output (bool): Output as JSON (default true)
      debug (bool): Enable debug output
      additional_args (str): Extra NTLMRecon arguments
    """
    try:
        p = request.json or {}
        target = p.get("target", "")
        if not target:
            return jsonify({"error": "target is required"}), 400

        cmd = f"{_bin('NTLMRecon')} -t {shlex.quote(target)}"
        if p.get("json_output", True):
            cmd += " -o json"
        if p.get("host_header"):
            cmd += f" -H {shlex.quote(p['host_header'])}"
        if p.get("debug"):
            cmd += " -debug"
        if p.get("additional_args"):
            cmd += f" {p['additional_args']}"

        logger.info(f"🔍 NTLMRecon: {target}")
        return jsonify(_run(cmd, timeout=120))
    except Exception as exc:
        logger.error(f"💥 NTLMRecon error: {exc}")
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# gokart - Go Static Analysis
# ---------------------------------------------------------------------------

@praetorian_bp.route("/gokart/scan", methods=["POST"])
def gokart_scan():
    """
    Run static security analysis on Go code using gokart.

    Body fields:
      path (str): Path to Go package or module (required)
      output_format (str): json | sarif | csv (default: json)
      verbose (bool): Verbose output
      additional_args (str): Extra gokart arguments
    """
    try:
        p = request.json or {}
        path = p.get("path", "")
        if not path:
            return jsonify({"error": "path is required"}), 400

        cmd = f"{_bin('gokart')} scan {shlex.quote(path)}"
        fmt = p.get("output_format", "json")
        if fmt == "json":
            cmd += " -j"
        elif fmt == "sarif":
            cmd += " -s"
        elif fmt == "csv":
            cmd += " -c"
        if p.get("verbose"):
            cmd += " -v"
        if p.get("additional_args"):
            cmd += f" {p['additional_args']}"

        logger.info(f"📊 gokart scan: {path}")
        return jsonify(_run(cmd, timeout=300))
    except Exception as exc:
        logger.error(f"💥 gokart error: {exc}")
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# trident - Password Spraying
# ---------------------------------------------------------------------------

@praetorian_bp.route("/trident/spray", methods=["POST"])
def trident_spray():
    """
    Run automated password spraying using trident.

    Body fields:
      username_file (str): Path to usernames file (required)
      password_file (str): Path to passwords file (required)
      auth_provider (str): okta | o365 | adfs etc. (required)
      interval (str): Spray interval e.g. "30m"
      window (str): Spray window e.g. "8h"
      config_file (str): Path to trident config file
      additional_args (str): Extra trident-client arguments

    Env vars:
      TRIDENT_CLIENT_ID, TRIDENT_CLIENT_SECRET, TRIDENT_SERVER_URL
    """
    try:
        p = request.json or {}
        username_file = p.get("username_file", "")
        password_file = p.get("password_file", "")
        auth_provider = p.get("auth_provider", "")
        if not username_file or not password_file or not auth_provider:
            return jsonify({"error": "username_file, password_file, and auth_provider are required"}), 400

        cmd = f"{_bin('trident-client')} campaign"
        cmd += f" -u {shlex.quote(username_file)}"
        cmd += f" -p {shlex.quote(password_file)}"
        cmd += f" -a {shlex.quote(auth_provider)}"
        if p.get("interval"):
            cmd += f" -i {shlex.quote(p['interval'])}"
        if p.get("window"):
            cmd += f" -w {shlex.quote(p['window'])}"
        if p.get("config_file"):
            cmd += f" --config {shlex.quote(p['config_file'])}"
        if p.get("additional_args"):
            cmd += f" {p['additional_args']}"

        logger.info(f"🔑 trident spray: {auth_provider}")
        return jsonify(_run(cmd, timeout=3600))
    except Exception as exc:
        logger.error(f"💥 trident error: {exc}")
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Health / version endpoint
# ---------------------------------------------------------------------------

@praetorian_bp.route("/status", methods=["GET"])
def praetorian_status():
    """Return installed versions of all Praetorian tools."""
    tools = {
        "noseyparker": f"{_bin('noseyparker')} --version",
        "titus":        f"{_bin('titus')} --version",
        "fingerprintx": f"{_bin('fingerprintx')} --version",
        "brutus":       f"{_bin('brutus')} --version",
        "nerva":        f"{_bin('nerva')} --version",
        "hadrian":      f"{_bin('hadrian')} --version",
        "trajan":       f"{_bin('trajan')} --version",
        "vespasian":    f"{_bin('vespasian')} version",
        "julius":       f"{_bin('julius')} --version",
        "aurelian":     f"{_bin('aurelian')} --version",
        "NTLMRecon":    f"{_bin('NTLMRecon')} --version",
        "gokart":       f"{_bin('gokart')} --version",
        "trident":      f"{_bin('trident-client')} --version",
        "pius":         f"{_bin('pius')} --version",
        "augustus":     f"{_bin('augustus')} version",
    }
    status = {}
    for name, cmd in tools.items():
        r = _run(cmd, timeout=5)
        out = (r.get("stdout") or r.get("stderr") or "").strip().splitlines()
        status[name] = {"installed": r["returncode"] in (0, 1, 2), "version": out[0] if out else "unknown"}
    return jsonify({"tools": status, "timestamp": datetime.now().isoformat()})
