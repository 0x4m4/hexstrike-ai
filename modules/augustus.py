"""
Augustus Module - LLM Adversarial Security Testing
Blueprint for HexStrike AI server

Integrates github.com/praetorian-inc/augustus
210+ adversarial probes, 28 LLM providers, 90+ detectors, 31 buff transformations.
"""

import logging
import os
import shlex
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

AUGUSTUS_BIN = Path("/home/kali/gopath/bin/augustus")

augustus_bp = Blueprint("augustus", __name__, url_prefix="/api/augustus")


def _run(cmd: str, timeout: int = 600) -> dict:
    """Execute a shell command and return structured output."""
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
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
        return {
            "success": False,
            "error": f"Command timed out after {timeout}s",
            "command": cmd,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "command": cmd,
            "timestamp": datetime.now().isoformat(),
        }


def _build_scan_cmd(params: dict) -> str:
    """Build the augustus scan command from request parameters."""
    generator = params.get("generator", "")
    if not generator:
        raise ValueError("generator is required")

    cmd = f"{AUGUSTUS_BIN} scan {shlex.quote(generator)}"

    # Probe selection — mutually exclusive groups
    probes = params.get("probes", [])          # list of probe names
    probes_glob = params.get("probes_glob", "")
    run_all = params.get("all_probes", False)

    if run_all:
        cmd += " --all"
    elif probes_glob:
        cmd += f" --probes-glob {shlex.quote(probes_glob)}"
    elif probes:
        if isinstance(probes, str):
            probes = [p.strip() for p in probes.split(",")]
        for p in probes:
            cmd += f" --probe {shlex.quote(p)}"

    # Detector selection
    detectors = params.get("detectors", [])
    detectors_glob = params.get("detectors_glob", "")
    if detectors_glob:
        cmd += f" --detectors-glob {shlex.quote(detectors_glob)}"
    elif detectors:
        if isinstance(detectors, str):
            detectors = [d.strip() for d in detectors.split(",")]
        for d in detectors:
            cmd += f" --detector {shlex.quote(d)}"

    # Buff transformations
    buffs = params.get("buffs", [])
    buffs_glob = params.get("buffs_glob", "")
    if buffs_glob:
        cmd += f" --buffs-glob {shlex.quote(buffs_glob)}"
    elif buffs:
        if isinstance(buffs, str):
            buffs = [b.strip() for b in buffs.split(",")]
        for b in buffs:
            cmd += f" --buff {shlex.quote(b)}"

    # Harness
    harness = params.get("harness", "")
    if harness:
        cmd += f" --harness {shlex.quote(harness)}"

    # Inline generator config (JSON string)
    config_json = params.get("config", "")
    if config_json:
        cmd += f" --config {shlex.quote(config_json)}"

    # Config file path
    config_file = params.get("config_file", "")
    if config_file:
        cmd += f" --config-file {shlex.quote(config_file)}"

    # Output
    output_format = params.get("output_format", "json")
    cmd += f" --format {shlex.quote(output_format)}"

    output_path = params.get("output_path", "")
    if output_path:
        cmd += f" --output {shlex.quote(output_path)}"

    html_path = params.get("html_report", "")
    if html_path:
        cmd += f" --html {shlex.quote(html_path)}"

    # Execution controls
    concurrency = params.get("concurrency", 0)
    if concurrency and int(concurrency) > 0:
        cmd += f" --concurrency {int(concurrency)}"

    timeout_val = params.get("scan_timeout", "")
    if timeout_val:
        cmd += f" --timeout {shlex.quote(str(timeout_val))}"

    probe_timeout = params.get("probe_timeout", "")
    if probe_timeout:
        cmd += f" --probe-timeout {shlex.quote(str(probe_timeout))}"

    max_attempts = params.get("max_attempts", 0)
    if max_attempts and int(max_attempts) > 0:
        cmd += f" --max-attempts {int(max_attempts)}"

    if params.get("verbose", False):
        cmd += " --verbose"

    if params.get("debug", False):
        cmd += " --debug"

    # Passthrough extra args
    extra = params.get("additional_args", "")
    if extra:
        cmd += f" {extra}"

    return cmd


@augustus_bp.route("/scan", methods=["POST"])
def scan():
    """
    Run adversarial probes against a target LLM provider.

    Required body fields:
      generator (str): Provider identifier e.g. "openai.OpenAI", "anthropic.Anthropic"

    Optional probe selection (pick one):
      probes (list|str): Probe names or comma-separated string
      probes_glob (str): Glob pattern e.g. "dan.*,jailbreak.*"
      all_probes (bool): Run all 172 probes

    Optional detector selection:
      detectors (list|str): Detector names
      detectors_glob (str): Glob pattern

    Optional buff transformations:
      buffs (list|str): Buff names
      buffs_glob (str): Glob pattern

    Execution controls:
      harness (str): probewise.Probewise | batch.Batch | agentwise.Agentwise
      concurrency (int): Max concurrent probes (default 10)
      scan_timeout (str): Overall timeout e.g. "30m"
      probe_timeout (str): Per-probe timeout e.g. "5m"
      max_attempts (int): Retry count

    Output:
      output_format (str): json | table | jsonl (default: json)
      output_path (str): Write JSONL results to file path
      html_report (str): Write HTML report to file path
      verbose (bool): Enable verbose logging
      debug (bool): Enable debug logging

    Auth (pass via JSON or set env vars before starting server):
      config (str): Inline JSON generator config
      config_file (str): Path to YAML config file
    """
    try:
        params = request.json or {}
        if not params.get("generator"):
            return jsonify({"error": "generator is required"}), 400

        cmd = _build_scan_cmd(params)
        logger.info(f"🔬 Augustus scan: {params['generator']}")

        # Set API keys from request body into env if provided
        env = os.environ.copy()
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "COHERE_API_KEY",
                    "GROQ_API_KEY", "MISTRAL_API_KEY", "GOOGLE_API_KEY"):
            if params.get(key):
                env[key] = params[key]

        proc_timeout = 600
        ts = params.get("scan_timeout", "")
        if ts and ts.endswith("m"):
            try:
                proc_timeout = int(ts[:-1]) * 60 + 30
            except ValueError:
                pass

        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True,
                text=True, timeout=proc_timeout, env=env,
            )
            result = {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "command": cmd,
                "generator": params["generator"],
                "timestamp": datetime.now().isoformat(),
            }
        except subprocess.TimeoutExpired:
            result = {
                "success": False,
                "error": f"Scan timed out after {proc_timeout}s",
                "command": cmd,
                "timestamp": datetime.now().isoformat(),
            }

        logger.info(f"📊 Augustus scan completed: returncode={result.get('returncode')}")
        return jsonify(result)

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as exc:
        logger.error(f"💥 Augustus scan error: {exc}")
        return jsonify({"error": f"Server error: {exc}"}), 500


@augustus_bp.route("/scan-all", methods=["POST"])
def scan_all():
    """
    Run ALL 172 probes against a target LLM provider.

    Required body fields:
      generator (str): Provider identifier

    Optional controls same as /scan (concurrency, timeout, output_format, etc.)
    NOTE: This runs all probes and can take a very long time.
    """
    try:
        params = request.json or {}
        if not params.get("generator"):
            return jsonify({"error": "generator is required"}), 400

        params["all_probes"] = True
        cmd = _build_scan_cmd(params)
        logger.info(f"🔬 Augustus full scan (all probes): {params['generator']}")

        env = os.environ.copy()
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "COHERE_API_KEY"):
            if params.get(key):
                env[key] = params[key]

        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True,
                text=True, timeout=3600, env=env,
            )
            result = {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "command": cmd,
                "generator": params["generator"],
                "timestamp": datetime.now().isoformat(),
            }
        except subprocess.TimeoutExpired:
            result = {
                "success": False,
                "error": "Full scan timed out after 3600s",
                "command": cmd,
                "timestamp": datetime.now().isoformat(),
            }

        logger.info(f"📊 Augustus full scan completed: returncode={result.get('returncode')}")
        return jsonify(result)

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as exc:
        logger.error(f"💥 Augustus scan-all error: {exc}")
        return jsonify({"error": f"Server error: {exc}"}), 500


@augustus_bp.route("/multi-turn", methods=["POST"])
def multi_turn():
    """
    Run a multi-turn adversarial attack strategy against a target LLM.

    Required body fields:
      generator (str): Provider identifier
      strategy (str): crescendo.Crescendo | goat.Goat | dan.DAN_Jailbreak (default: crescendo.Crescendo)

    Optional:
      Same output/control flags as /scan
    """
    try:
        params = request.json or {}
        if not params.get("generator"):
            return jsonify({"error": "generator is required"}), 400

        strategy = params.get("strategy", "crescendo.Crescendo")
        params["probes"] = [strategy]

        cmd = _build_scan_cmd(params)
        logger.info(f"🎯 Augustus multi-turn ({strategy}): {params['generator']}")

        env = os.environ.copy()
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "COHERE_API_KEY"):
            if params.get(key):
                env[key] = params[key]

        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True,
                text=True, timeout=900, env=env,
            )
            result = {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "command": cmd,
                "generator": params["generator"],
                "strategy": strategy,
                "timestamp": datetime.now().isoformat(),
            }
        except subprocess.TimeoutExpired:
            result = {
                "success": False,
                "error": "Multi-turn attack timed out after 900s",
                "command": cmd,
                "timestamp": datetime.now().isoformat(),
            }

        logger.info(f"📊 Augustus multi-turn completed: returncode={result.get('returncode')}")
        return jsonify(result)

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as exc:
        logger.error(f"💥 Augustus multi-turn error: {exc}")
        return jsonify({"error": f"Server error: {exc}"}), 500


@augustus_bp.route("/list", methods=["GET"])
def list_capabilities():
    """
    List all registered Augustus probes, detectors, buffs, and harnesses.

    Optional query param:
      filter (str): "probes" | "detectors" | "buffs" | "harnesses" — return only that section
    """
    try:
        result = _run(f"{AUGUSTUS_BIN} list", timeout=30)
        filt = request.args.get("filter", "")
        if filt and result.get("success"):
            lines = result["stdout"].splitlines()
            section, collecting, out = "", False, []
            for line in lines:
                low = line.lower()
                if filt.lower() in low and "(" in low:
                    collecting = True
                    section = line
                    out.append(line)
                elif collecting:
                    if line.strip() == "" and out:
                        break
                    out.append(line)
            result["filtered"] = "\n".join(out)
            result["filter"] = filt
        return jsonify(result)
    except Exception as exc:
        logger.error(f"💥 Augustus list error: {exc}")
        return jsonify({"error": f"Server error: {exc}"}), 500


@augustus_bp.route("/version", methods=["GET"])
def version():
    """Return the installed Augustus version."""
    try:
        result = _run(f"{AUGUSTUS_BIN} version", timeout=10)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
