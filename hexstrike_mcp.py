#!/usr/bin/env python3
"""
HexStrike AI MCP Client - Enhanced AI Agent Communication Interface

Enhanced with AI-Powered Intelligence & Automation
🚀 Bug Bounty | CTF | Red Team | Security Research

RECENT ENHANCEMENTS (v6.0):
✅ Complete color consistency with reddish hacker theme
✅ Enhanced visual output with consistent styling
✅ Improved error handling and recovery systems
✅ FastMCP integration for seamless AI communication
✅ 100+ security tools with intelligent parameter optimization
✅ Advanced logging with colored output and emojis

Architecture: MCP Client for AI agent communication with HexStrike server
Framework: FastMCP integration for tool orchestration
"""

import sys
import os
import argparse
import logging
from typing import Dict, Any, Optional
import requests
import time
from datetime import datetime

from mcp.server.fastmcp import FastMCP

class HexStrikeColors:
    """Enhanced color palette matching the server's ModernVisualEngine.COLORS"""

    # Basic colors (for backward compatibility)
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    # Core enhanced colors
    MATRIX_GREEN = '\033[38;5;46m'
    NEON_BLUE = '\033[38;5;51m'
    ELECTRIC_PURPLE = '\033[38;5;129m'
    CYBER_ORANGE = '\033[38;5;208m'
    HACKER_RED = '\033[38;5;196m'
    TERMINAL_GRAY = '\033[38;5;240m'
    BRIGHT_WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    # Enhanced reddish tones and highlighting colors
    BLOOD_RED = '\033[38;5;124m'
    CRIMSON = '\033[38;5;160m'
    DARK_RED = '\033[38;5;88m'
    FIRE_RED = '\033[38;5;202m'
    ROSE_RED = '\033[38;5;167m'
    BURGUNDY = '\033[38;5;52m'
    SCARLET = '\033[38;5;197m'
    RUBY = '\033[38;5;161m'

    # Highlighting colors
    HIGHLIGHT_RED = '\033[48;5;196m\033[38;5;15m'  # Red background, white text
    HIGHLIGHT_YELLOW = '\033[48;5;226m\033[38;5;16m'  # Yellow background, black text
    HIGHLIGHT_GREEN = '\033[48;5;46m\033[38;5;16m'  # Green background, black text
    HIGHLIGHT_BLUE = '\033[48;5;51m\033[38;5;16m'  # Blue background, black text
    HIGHLIGHT_PURPLE = '\033[48;5;129m\033[38;5;15m'  # Purple background, white text

    # Status colors with reddish tones
    SUCCESS = '\033[38;5;46m'  # Bright green
    WARNING = '\033[38;5;208m'  # Orange
    ERROR = '\033[38;5;196m'  # Bright red
    CRITICAL = '\033[48;5;196m\033[38;5;15m\033[1m'  # Red background, white bold text
    INFO = '\033[38;5;51m'  # Cyan
    DEBUG = '\033[38;5;240m'  # Gray

    # Vulnerability severity colors
    VULN_CRITICAL = '\033[48;5;124m\033[38;5;15m\033[1m'  # Dark red background
    VULN_HIGH = '\033[38;5;196m\033[1m'  # Bright red bold
    VULN_MEDIUM = '\033[38;5;208m\033[1m'  # Orange bold
    VULN_LOW = '\033[38;5;226m'  # Yellow
    VULN_INFO = '\033[38;5;51m'  # Cyan

    # Tool status colors
    TOOL_RUNNING = '\033[38;5;46m\033[5m'  # Blinking green
    TOOL_SUCCESS = '\033[38;5;46m\033[1m'  # Bold green
    TOOL_FAILED = '\033[38;5;196m\033[1m'  # Bold red
    TOOL_TIMEOUT = '\033[38;5;208m\033[1m'  # Bold orange
    TOOL_RECOVERY = '\033[38;5;129m\033[1m'  # Bold purple

# Backward compatibility alias
Colors = HexStrikeColors

class ColoredFormatter(logging.Formatter):
    """Enhanced formatter with colors and emojis for MCP client - matches server styling"""

    COLORS = {
        'DEBUG': HexStrikeColors.DEBUG,
        'INFO': HexStrikeColors.SUCCESS,
        'WARNING': HexStrikeColors.WARNING,
        'ERROR': HexStrikeColors.ERROR,
        'CRITICAL': HexStrikeColors.CRITICAL
    }

    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🔥'
    }

    def format(self, record):
        emoji = self.EMOJIS.get(record.levelname, '📝')
        color = self.COLORS.get(record.levelname, HexStrikeColors.BRIGHT_WHITE)

        # Add color and emoji to the message
        record.msg = f"{color}{emoji} {record.msg}{HexStrikeColors.RESET}"
        return super().format(record)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[🔥 HexStrike MCP] %(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)

# Apply colored formatter
for handler in logging.getLogger().handlers:
    handler.setFormatter(ColoredFormatter(
        "[🔥 HexStrike MCP] %(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_HEXSTRIKE_SERVER = "http://127.0.0.1:8888"  # Default HexStrike server URL
DEFAULT_REQUEST_TIMEOUT = 300  # 5 minutes default timeout for API requests
MAX_RETRIES = 3  # Maximum number of retries for connection attempts

class HexStrikeClient:
    """Enhanced client for communicating with the HexStrike AI API Server"""

    def __init__(self, server_url: str, timeout: int = DEFAULT_REQUEST_TIMEOUT):
        """
        Initialize the HexStrike AI Client

        Args:
            server_url: URL of the HexStrike AI API Server
            timeout: Request timeout in seconds
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

        # Try to connect to server with retries
        connected = False
        for i in range(MAX_RETRIES):
            try:
                logger.info(f"🔗 Attempting to connect to HexStrike AI API at {server_url} (attempt {i+1}/{MAX_RETRIES})")
                # First try a direct connection test before using the health endpoint
                try:
                    test_response = self.session.get(f"{self.server_url}/health", timeout=5)
                    test_response.raise_for_status()
                    health_check = test_response.json()
                    connected = True
                    logger.info(f"🎯 Successfully connected to HexStrike AI API Server at {server_url}")
                    logger.info(f"🏥 Server health status: {health_check.get('status', 'unknown')}")
                    logger.info(f"📊 Server version: {health_check.get('version', 'unknown')}")
                    break
                except requests.exceptions.ConnectionError:
                    logger.warning(f"🔌 Connection refused to {server_url}. Make sure the HexStrike AI server is running.")
                    time.sleep(2)  # Wait before retrying
                except Exception as e:
                    logger.warning(f"⚠️  Connection test failed: {str(e)}")
                    time.sleep(2)  # Wait before retrying
            except Exception as e:
                logger.warning(f"❌ Connection attempt {i+1} failed: {str(e)}")
                time.sleep(2)  # Wait before retrying

        if not connected:
            error_msg = f"Failed to establish connection to HexStrike AI API Server at {server_url} after {MAX_RETRIES} attempts"
            logger.error(error_msg)
            # We'll continue anyway to allow the MCP server to start, but tools will likely fail

    def safe_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform a GET request with optional query parameters.

        Args:
            endpoint: API endpoint path (without leading slash)
            params: Optional query parameters

        Returns:
            Response data as dictionary
        """
        if params is None:
            params = {}

        url = f"{self.server_url}/{endpoint}"

        try:
            logger.debug(f"📡 GET {url} with params: {params}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"🚫 Request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}", "success": False}
        except Exception as e:
            logger.error(f"💥 Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}", "success": False}

    def safe_post(self, endpoint: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a POST request with JSON data.

        Args:
            endpoint: API endpoint path (without leading slash)
            json_data: JSON data to send

        Returns:
            Response data as dictionary
        """
        url = f"{self.server_url}/{endpoint}"

        try:
            logger.debug(f"📡 POST {url} with data: {json_data}")
            response = self.session.post(url, json=json_data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"🚫 Request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}", "success": False}
        except Exception as e:
            logger.error(f"💥 Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}", "success": False}

    def execute_command(self, command: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Execute a generic command on the HexStrike server

        Args:
            command: Command to execute
            use_cache: Whether to use caching for this command

        Returns:
            Command execution results
        """
        return self.safe_post("api/command", {"command": command, "use_cache": use_cache})

    def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the HexStrike AI API Server

        Returns:
            Health status information
        """
        return self.safe_get("health")

def setup_mcp_server(hexstrike_client: HexStrikeClient) -> FastMCP:
    """
    Set up the MCP server with all enhanced tool functions

    Args:
        hexstrike_client: Initialized HexStrikeClient

    Returns:
        Configured FastMCP instance
    """
    mcp = FastMCP("hexstrike-ai-mcp")

    # ============================================================================
    # CORE NETWORK SCANNING TOOLS
    # ============================================================================

    @mcp.tool()
    def nmap_scan(target: str, scan_type: str = "-sV", ports: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute an enhanced Nmap scan against a target with real-time logging.

        Args:
            target: The IP address or hostname to scan
            scan_type: Scan type (e.g., -sV for version detection, -sC for scripts)
            ports: Comma-separated list of ports or port ranges
            additional_args: Additional Nmap arguments

        Returns:
            Scan results with enhanced telemetry
        """
        data = {
            "target": target,
            "scan_type": scan_type,
            "ports": ports,
            "additional_args": additional_args
        }
        logger.info(f"{HexStrikeColors.FIRE_RED}🔍 Initiating Nmap scan: {target}{HexStrikeColors.RESET}")

        # Use enhanced error handling by default
        data["use_recovery"] = True
        result = hexstrike_client.safe_post("api/tools/nmap", data)

        if result.get("success"):
            logger.info(f"{HexStrikeColors.SUCCESS}✅ Nmap scan completed successfully for {target}{HexStrikeColors.RESET}")

            # Check for recovery information
            if result.get("recovery_info", {}).get("recovery_applied"):
                recovery_info = result["recovery_info"]
                attempts = recovery_info.get("attempts_made", 1)
                logger.info(f"{HexStrikeColors.HIGHLIGHT_YELLOW} Recovery applied: {attempts} attempts made {HexStrikeColors.RESET}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ Nmap scan failed for {target}{HexStrikeColors.RESET}")

            # Check for human escalation
            if result.get("human_escalation"):
                logger.error(f"{HexStrikeColors.CRITICAL} HUMAN ESCALATION REQUIRED {HexStrikeColors.RESET}")

        return result

    @mcp.tool()
    def gobuster_scan(url: str, mode: str = "dir", wordlist: str = "/usr/share/wordlists/dirb/common.txt", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Gobuster to find directories, DNS subdomains, or virtual hosts with enhanced logging.

        Args:
            url: The target URL
            mode: Scan mode (dir, dns, fuzz, vhost)
            wordlist: Path to wordlist file
            additional_args: Additional Gobuster arguments

        Returns:
            Scan results with enhanced telemetry
        """
        data = {
            "url": url,
            "mode": mode,
            "wordlist": wordlist,
            "additional_args": additional_args
        }
        logger.info(f"{HexStrikeColors.CRIMSON}📁 Starting Gobuster {mode} scan: {url}{HexStrikeColors.RESET}")

        # Use enhanced error handling by default
        data["use_recovery"] = True
        result = hexstrike_client.safe_post("api/tools/gobuster", data)

        if result.get("success"):
            logger.info(f"{HexStrikeColors.SUCCESS}✅ Gobuster scan completed for {url}{HexStrikeColors.RESET}")

            # Check for recovery information
            if result.get("recovery_info", {}).get("recovery_applied"):
                recovery_info = result["recovery_info"]
                attempts = recovery_info.get("attempts_made", 1)
                logger.info(f"{HexStrikeColors.HIGHLIGHT_YELLOW} Recovery applied: {attempts} attempts made {HexStrikeColors.RESET}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ Gobuster scan failed for {url}{HexStrikeColors.RESET}")

            # Check for alternative tool suggestion
            if result.get("alternative_tool_suggested"):
                alt_tool = result["alternative_tool_suggested"]
                logger.info(f"{HexStrikeColors.HIGHLIGHT_BLUE} Alternative tool suggested: {alt_tool} {HexStrikeColors.RESET}")

        return result

    @mcp.tool()
    def nuclei_scan(target: str, severity: str = "", tags: str = "", template: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Nuclei vulnerability scanner with enhanced logging and real-time progress.

        Args:
            target: The target URL or IP
            severity: Filter by severity (critical,high,medium,low,info)
            tags: Filter by tags (e.g. cve,rce,lfi)
            template: Custom template path
            additional_args: Additional Nuclei arguments

        Returns:
            Scan results with discovered vulnerabilities and telemetry
        """
        data = {
            "target": target,
            "severity": severity,
            "tags": tags,
            "template": template,
            "additional_args": additional_args
        }
        logger.info(f"{HexStrikeColors.BLOOD_RED}🔬 Starting Nuclei vulnerability scan: {target}{HexStrikeColors.RESET}")

        # Use enhanced error handling by default
        data["use_recovery"] = True
        result = hexstrike_client.safe_post("api/tools/nuclei", data)

        if result.get("success"):
            logger.info(f"{HexStrikeColors.SUCCESS}✅ Nuclei scan completed for {target}{HexStrikeColors.RESET}")

            # Enhanced vulnerability reporting
            if result.get("stdout") and "CRITICAL" in result["stdout"]:
                logger.warning(f"{HexStrikeColors.CRITICAL} CRITICAL vulnerabilities detected! {HexStrikeColors.RESET}")
            elif result.get("stdout") and "HIGH" in result["stdout"]:
                logger.warning(f"{HexStrikeColors.FIRE_RED} HIGH severity vulnerabilities found! {HexStrikeColors.RESET}")

            # Check for recovery information
            if result.get("recovery_info", {}).get("recovery_applied"):
                recovery_info = result["recovery_info"]
                attempts = recovery_info.get("attempts_made", 1)
                logger.info(f"{HexStrikeColors.HIGHLIGHT_YELLOW} Recovery applied: {attempts} attempts made {HexStrikeColors.RESET}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ Nuclei scan failed for {target}{HexStrikeColors.RESET}")

        return result

    # ============================================================================
    # CLOUD SECURITY TOOLS
    # ============================================================================

    @mcp.tool()
    def prowler_scan(provider: str = "aws", profile: str = "default", region: str = "", checks: str = "", output_dir: str = "/tmp/prowler_output", output_format: str = "json", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Prowler for comprehensive cloud security assessment.

        Args:
            provider: Cloud provider (aws, azure, gcp)
            profile: AWS profile to use
            region: Specific region to scan
            checks: Specific checks to run
            output_dir: Directory to save results
            output_format: Output format (json, csv, html)
            additional_args: Additional Prowler arguments

        Returns:
            Cloud security assessment results
        """
        data = {
            "provider": provider,
            "profile": profile,
            "region": region,
            "checks": checks,
            "output_dir": output_dir,
            "output_format": output_format,
            "additional_args": additional_args
        }
        logger.info(f"☁️  Starting Prowler {provider} security assessment")
        result = hexstrike_client.safe_post("api/tools/prowler", data)
        if result.get("success"):
            logger.info(f"✅ Prowler assessment completed")
        else:
            logger.error(f"❌ Prowler assessment failed")
        return result

    @mcp.tool()
    def trivy_scan(scan_type: str = "image", target: str = "", output_format: str = "json", severity: str = "", output_file: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Trivy for container and filesystem vulnerability scanning.

        Args:
            scan_type: Type of scan (image, fs, repo, config)
            target: Target to scan (image name, directory, repository)
            output_format: Output format (json, table, sarif)
            severity: Severity filter (UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL)
            output_file: File to save results
            additional_args: Additional Trivy arguments

        Returns:
            Vulnerability scan results
        """
        data = {
            "scan_type": scan_type,
            "target": target,
            "output_format": output_format,
            "severity": severity,
            "output_file": output_file,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Trivy {scan_type} scan: {target}")
        result = hexstrike_client.safe_post("api/tools/trivy", data)
        if result.get("success"):
            logger.info(f"✅ Trivy scan completed for {target}")
        else:
            logger.error(f"❌ Trivy scan failed for {target}")
        return result

    # ============================================================================
    # ENHANCED CLOUD AND CONTAINER SECURITY TOOLS (v6.0)
    # ============================================================================

    @mcp.tool()
    def scout_suite_assessment(provider: str = "aws", profile: str = "default",
                              report_dir: str = "/tmp/scout-suite", services: str = "",
                              exceptions: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Scout Suite for multi-cloud security assessment.

        Args:
            provider: Cloud provider (aws, azure, gcp, aliyun, oci)
            profile: AWS profile to use
            report_dir: Directory to save reports
            services: Specific services to assess
            exceptions: Exceptions file path
            additional_args: Additional Scout Suite arguments

        Returns:
            Multi-cloud security assessment results
        """
        data = {
            "provider": provider,
            "profile": profile,
            "report_dir": report_dir,
            "services": services,
            "exceptions": exceptions,
            "additional_args": additional_args
        }
        logger.info(f"☁️  Starting Scout Suite {provider} assessment")
        result = hexstrike_client.safe_post("api/tools/scout-suite", data)
        if result.get("success"):
            logger.info(f"✅ Scout Suite assessment completed")
        else:
            logger.error(f"❌ Scout Suite assessment failed")
        return result

    @mcp.tool()
    def cloudmapper_analysis(action: str = "collect", account: str = "",
                            config: str = "config.json", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute CloudMapper for AWS network visualization and security analysis.

        Args:
            action: Action to perform (collect, prepare, webserver, find_admins, etc.)
            account: AWS account to analyze
            config: Configuration file path
            additional_args: Additional CloudMapper arguments

        Returns:
            AWS network visualization and security analysis results
        """
        data = {
            "action": action,
            "account": account,
            "config": config,
            "additional_args": additional_args
        }
        logger.info(f"☁️  Starting CloudMapper {action}")
        result = hexstrike_client.safe_post("api/tools/cloudmapper", data)
        if result.get("success"):
            logger.info(f"✅ CloudMapper {action} completed")
        else:
            logger.error(f"❌ CloudMapper {action} failed")
        return result

    @mcp.tool()
    def pacu_exploitation(session_name: str = "hexstrike_session", modules: str = "",
                         data_services: str = "", regions: str = "",
                         additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Pacu for AWS exploitation framework.

        Args:
            session_name: Pacu session name
            modules: Comma-separated list of modules to run
            data_services: Data services to enumerate
            regions: AWS regions to target
            additional_args: Additional Pacu arguments

        Returns:
            AWS exploitation framework results
        """
        data = {
            "session_name": session_name,
            "modules": modules,
            "data_services": data_services,
            "regions": regions,
            "additional_args": additional_args
        }
        logger.info(f"☁️  Starting Pacu AWS exploitation")
        result = hexstrike_client.safe_post("api/tools/pacu", data)
        if result.get("success"):
            logger.info(f"✅ Pacu exploitation completed")
        else:
            logger.error(f"❌ Pacu exploitation failed")
        return result

    @mcp.tool()
    def kube_hunter_scan(target: str = "", remote: str = "", cidr: str = "",
                        interface: str = "", active: bool = False, report: str = "json",
                        additional_args: str = "") -> Dict[str, Any]:
        """
        Execute kube-hunter for Kubernetes penetration testing.

        Args:
            target: Specific target to scan
            remote: Remote target to scan
            cidr: CIDR range to scan
            interface: Network interface to scan
            active: Enable active hunting (potentially harmful)
            report: Report format (json, yaml)
            additional_args: Additional kube-hunter arguments

        Returns:
            Kubernetes penetration testing results
        """
        data = {
            "target": target,
            "remote": remote,
            "cidr": cidr,
            "interface": interface,
            "active": active,
            "report": report,
            "additional_args": additional_args
        }
        logger.info(f"☁️  Starting kube-hunter Kubernetes scan")
        result = hexstrike_client.safe_post("api/tools/kube-hunter", data)
        if result.get("success"):
            logger.info(f"✅ kube-hunter scan completed")
        else:
            logger.error(f"❌ kube-hunter scan failed")
        return result

    @mcp.tool()
    def kube_bench_cis(targets: str = "", version: str = "", config_dir: str = "",
                      output_format: str = "json", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute kube-bench for CIS Kubernetes benchmark checks.

        Args:
            targets: Targets to check (master, node, etcd, policies)
            version: Kubernetes version
            config_dir: Configuration directory
            output_format: Output format (json, yaml)
            additional_args: Additional kube-bench arguments

        Returns:
            CIS Kubernetes benchmark results
        """
        data = {
            "targets": targets,
            "version": version,
            "config_dir": config_dir,
            "output_format": output_format,
            "additional_args": additional_args
        }
        logger.info(f"☁️  Starting kube-bench CIS benchmark")
        result = hexstrike_client.safe_post("api/tools/kube-bench", data)
        if result.get("success"):
            logger.info(f"✅ kube-bench benchmark completed")
        else:
            logger.error(f"❌ kube-bench benchmark failed")
        return result

    @mcp.tool()
    def docker_bench_security_scan(checks: str = "", exclude: str = "",
                                  output_file: str = "/tmp/docker-bench-results.json",
                                  additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Docker Bench for Security for Docker security assessment.

        Args:
            checks: Specific checks to run
            exclude: Checks to exclude
            output_file: Output file path
            additional_args: Additional Docker Bench arguments

        Returns:
            Docker security assessment results
        """
        data = {
            "checks": checks,
            "exclude": exclude,
            "output_file": output_file,
            "additional_args": additional_args
        }
        logger.info(f"🐳 Starting Docker Bench Security assessment")
        result = hexstrike_client.safe_post("api/tools/docker-bench-security", data)
        if result.get("success"):
            logger.info(f"✅ Docker Bench Security completed")
        else:
            logger.error(f"❌ Docker Bench Security failed")
        return result

    @mcp.tool()
    def clair_vulnerability_scan(image: str, config: str = "/etc/clair/config.yaml",
                                output_format: str = "json", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Clair for container vulnerability analysis.

        Args:
            image: Container image to scan
            config: Clair configuration file
            output_format: Output format (json, yaml)
            additional_args: Additional Clair arguments

        Returns:
            Container vulnerability analysis results
        """
        data = {
            "image": image,
            "config": config,
            "output_format": output_format,
            "additional_args": additional_args
        }
        logger.info(f"🐳 Starting Clair vulnerability scan: {image}")
        result = hexstrike_client.safe_post("api/tools/clair", data)
        if result.get("success"):
            logger.info(f"✅ Clair scan completed for {image}")
        else:
            logger.error(f"❌ Clair scan failed for {image}")
        return result

    @mcp.tool()
    def falco_runtime_monitoring(config_file: str = "/etc/falco/falco.yaml",
                                rules_file: str = "", output_format: str = "json",
                                duration: int = 60, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Falco for runtime security monitoring.

        Args:
            config_file: Falco configuration file
            rules_file: Custom rules file
            output_format: Output format (json, text)
            duration: Monitoring duration in seconds
            additional_args: Additional Falco arguments

        Returns:
            Runtime security monitoring results
        """
        data = {
            "config_file": config_file,
            "rules_file": rules_file,
            "output_format": output_format,
            "duration": duration,
            "additional_args": additional_args
        }
        logger.info(f"🛡️  Starting Falco runtime monitoring for {duration}s")
        result = hexstrike_client.safe_post("api/tools/falco", data)
        if result.get("success"):
            logger.info(f"✅ Falco monitoring completed")
        else:
            logger.error(f"❌ Falco monitoring failed")
        return result

    @mcp.tool()
    def checkov_iac_scan(directory: str = ".", framework: str = "", check: str = "",
                        skip_check: str = "", output_format: str = "json",
                        additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Checkov for infrastructure as code security scanning.

        Args:
            directory: Directory to scan
            framework: Framework to scan (terraform, cloudformation, kubernetes, etc.)
            check: Specific check to run
            skip_check: Check to skip
            output_format: Output format (json, yaml, cli)
            additional_args: Additional Checkov arguments

        Returns:
            Infrastructure as code security scanning results
        """
        data = {
            "directory": directory,
            "framework": framework,
            "check": check,
            "skip_check": skip_check,
            "output_format": output_format,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Checkov IaC scan: {directory}")
        result = hexstrike_client.safe_post("api/tools/checkov", data)
        if result.get("success"):
            logger.info(f"✅ Checkov scan completed")
        else:
            logger.error(f"❌ Checkov scan failed")
        return result

    @mcp.tool()
    def terrascan_iac_scan(scan_type: str = "all", iac_dir: str = ".",
                          policy_type: str = "", output_format: str = "json",
                          severity: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Terrascan for infrastructure as code security scanning.

        Args:
            scan_type: Type of scan (all, terraform, k8s, etc.)
            iac_dir: Infrastructure as code directory
            policy_type: Policy type to use
            output_format: Output format (json, yaml, xml)
            severity: Severity filter (high, medium, low)
            additional_args: Additional Terrascan arguments

        Returns:
            Infrastructure as code security scanning results
        """
        data = {
            "scan_type": scan_type,
            "iac_dir": iac_dir,
            "policy_type": policy_type,
            "output_format": output_format,
            "severity": severity,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Terrascan IaC scan: {iac_dir}")
        result = hexstrike_client.safe_post("api/tools/terrascan", data)
        if result.get("success"):
            logger.info(f"✅ Terrascan scan completed")
        else:
            logger.error(f"❌ Terrascan scan failed")
        return result

    # ============================================================================
    # FILE OPERATIONS & PAYLOAD GENERATION
    # ============================================================================

    @mcp.tool()
    def create_file(filename: str, content: str, binary: bool = False) -> Dict[str, Any]:
        """
        Create a file with specified content on the HexStrike server.

        Args:
            filename: Name of the file to create
            content: Content to write to the file
            binary: Whether the content is binary data

        Returns:
            File creation results
        """
        data = {
            "filename": filename,
            "content": content,
            "binary": binary
        }
        logger.info(f"📄 Creating file: {filename}")
        result = hexstrike_client.safe_post("api/files/create", data)
        if result.get("success"):
            logger.info(f"✅ File created successfully: {filename}")
        else:
            logger.error(f"❌ Failed to create file: {filename}")
        return result

    @mcp.tool()
    def modify_file(filename: str, content: str, append: bool = False) -> Dict[str, Any]:
        """
        Modify an existing file on the HexStrike server.

        Args:
            filename: Name of the file to modify
            content: Content to write or append
            append: Whether to append to the file (True) or overwrite (False)

        Returns:
            File modification results
        """
        data = {
            "filename": filename,
            "content": content,
            "append": append
        }
        logger.info(f"✏️  Modifying file: {filename}")
        result = hexstrike_client.safe_post("api/files/modify", data)
        if result.get("success"):
            logger.info(f"✅ File modified successfully: {filename}")
        else:
            logger.error(f"❌ Failed to modify file: {filename}")
        return result

    @mcp.tool()
    def delete_file(filename: str) -> Dict[str, Any]:
        """
        Delete a file or directory on the HexStrike server.

        Args:
            filename: Name of the file or directory to delete

        Returns:
            File deletion results
        """
        data = {
            "filename": filename
        }
        logger.info(f"🗑️  Deleting file: {filename}")
        result = hexstrike_client.safe_post("api/files/delete", data)
        if result.get("success"):
            logger.info(f"✅ File deleted successfully: {filename}")
        else:
            logger.error(f"❌ Failed to delete file: {filename}")
        return result

    @mcp.tool()
    def list_files(directory: str = ".") -> Dict[str, Any]:
        """
        List files in a directory on the HexStrike server.

        Args:
            directory: Directory to list (relative to server's base directory)

        Returns:
            Directory listing results
        """
        logger.info(f"📂 Listing files in directory: {directory}")
        result = hexstrike_client.safe_get("api/files/list", {"directory": directory})
        if result.get("success"):
            file_count = len(result.get("files", []))
            logger.info(f"✅ Listed {file_count} files in {directory}")
        else:
            logger.error(f"❌ Failed to list files in {directory}")
        return result

    @mcp.tool()
    def generate_payload(payload_type: str = "buffer", size: int = 1024, pattern: str = "A", filename: str = "") -> Dict[str, Any]:
        """
        Generate large payloads for testing and exploitation.

        Args:
            payload_type: Type of payload (buffer, cyclic, random)
            size: Size of the payload in bytes
            pattern: Pattern to use for buffer payloads
            filename: Custom filename (auto-generated if empty)

        Returns:
            Payload generation results
        """
        data = {
            "type": payload_type,
            "size": size,
            "pattern": pattern
        }
        if filename:
            data["filename"] = filename

        logger.info(f"🎯 Generating {payload_type} payload: {size} bytes")
        result = hexstrike_client.safe_post("api/payloads/generate", data)
        if result.get("success"):
            logger.info(f"✅ Payload generated successfully")
        else:
            logger.error(f"❌ Failed to generate payload")
        return result

    # ============================================================================
    # PYTHON ENVIRONMENT MANAGEMENT
    # ============================================================================

    @mcp.tool()
    def install_python_package(package: str, env_name: str = "default") -> Dict[str, Any]:
        """
        Install a Python package in a virtual environment on the HexStrike server.

        Args:
            package: Name of the Python package to install
            env_name: Name of the virtual environment

        Returns:
            Package installation results
        """
        data = {
            "package": package,
            "env_name": env_name
        }
        logger.info(f"📦 Installing Python package: {package} in env {env_name}")
        result = hexstrike_client.safe_post("api/python/install", data)
        if result.get("success"):
            logger.info(f"✅ Package {package} installed successfully")
        else:
            logger.error(f"❌ Failed to install package {package}")
        return result

    @mcp.tool()
    def execute_python_script(script: str, env_name: str = "default", filename: str = "") -> Dict[str, Any]:
        """
        Execute a Python script in a virtual environment on the HexStrike server.

        Args:
            script: Python script content to execute
            env_name: Name of the virtual environment
            filename: Custom script filename (auto-generated if empty)

        Returns:
            Script execution results
        """
        data = {
            "script": script,
            "env_name": env_name
        }
        if filename:
            data["filename"] = filename

        logger.info(f"🐍 Executing Python script in env {env_name}")
        result = hexstrike_client.safe_post("api/python/execute", data)
        if result.get("success"):
            logger.info(f"✅ Python script executed successfully")
        else:
            logger.error(f"❌ Python script execution failed")
        return result

    # ============================================================================
    # ADDITIONAL SECURITY TOOLS FROM ORIGINAL IMPLEMENTATION
    # ============================================================================

    @mcp.tool()
    def dirb_scan(url: str, wordlist: str = "/usr/share/wordlists/dirb/common.txt", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Dirb for directory brute forcing with enhanced logging.

        Args:
            url: The target URL
            wordlist: Path to wordlist file
            additional_args: Additional Dirb arguments

        Returns:
            Scan results with enhanced telemetry
        """
        data = {
            "url": url,
            "wordlist": wordlist,
            "additional_args": additional_args
        }
        logger.info(f"📁 Starting Dirb scan: {url}")
        result = hexstrike_client.safe_post("api/tools/dirb", data)
        if result.get("success"):
            logger.info(f"✅ Dirb scan completed for {url}")
        else:
            logger.error(f"❌ Dirb scan failed for {url}")
        return result

    @mcp.tool()
    def nikto_scan(target: str, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Nikto web vulnerability scanner with enhanced logging.

        Args:
            target: The target URL or IP
            additional_args: Additional Nikto arguments

        Returns:
            Scan results with discovered vulnerabilities
        """
        data = {
            "target": target,
            "additional_args": additional_args
        }
        logger.info(f"🔬 Starting Nikto scan: {target}")
        result = hexstrike_client.safe_post("api/tools/nikto", data)
        if result.get("success"):
            logger.info(f"✅ Nikto scan completed for {target}")
        else:
            logger.error(f"❌ Nikto scan failed for {target}")
        return result

    @mcp.tool()
    def sqlmap_scan(url: str, data: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute SQLMap for SQL injection testing with enhanced logging.

        Args:
            url: The target URL
            data: POST data for testing
            additional_args: Additional SQLMap arguments

        Returns:
            SQL injection test results
        """
        data_payload = {
            "url": url,
            "data": data,
            "additional_args": additional_args
        }
        logger.info(f"💉 Starting SQLMap scan: {url}")
        result = hexstrike_client.safe_post("api/tools/sqlmap", data_payload)
        if result.get("success"):
            logger.info(f"✅ SQLMap scan completed for {url}")
        else:
            logger.error(f"❌ SQLMap scan failed for {url}")
        return result

    @mcp.tool()
    def metasploit_run(module: str, options: Dict[str, Any] = {}) -> Dict[str, Any]:
        """
        Execute a Metasploit module with enhanced logging.

        Args:
            module: The Metasploit module to use
            options: Dictionary of module options

        Returns:
            Metasploit execution results
        """
        data = {
            "module": module,
            "options": options
        }
        logger.info(f"🚀 Starting Metasploit module: {module}")
        result = hexstrike_client.safe_post("api/tools/metasploit", data)
        if result.get("success"):
            logger.info(f"✅ Metasploit module completed: {module}")
        else:
            logger.error(f"❌ Metasploit module failed: {module}")
        return result

    @mcp.tool()
    def hydra_attack(
        target: str,
        service: str,
        username: str = "",
        username_file: str = "",
        password: str = "",
        password_file: str = "",
        additional_args: str = ""
    ) -> Dict[str, Any]:
        """
        Execute Hydra for password brute forcing with enhanced logging.

        Args:
            target: The target IP or hostname
            service: The service to attack (ssh, ftp, http, etc.)
            username: Single username to test
            username_file: File containing usernames
            password: Single password to test
            password_file: File containing passwords
            additional_args: Additional Hydra arguments

        Returns:
            Brute force attack results
        """
        data = {
            "target": target,
            "service": service,
            "username": username,
            "username_file": username_file,
            "password": password,
            "password_file": password_file,
            "additional_args": additional_args
        }
        logger.info(f"🔑 Starting Hydra attack: {target}:{service}")
        result = hexstrike_client.safe_post("api/tools/hydra", data)
        if result.get("success"):
            logger.info(f"✅ Hydra attack completed for {target}")
        else:
            logger.error(f"❌ Hydra attack failed for {target}")
        return result

    @mcp.tool()
    def john_crack(
        hash_file: str,
        wordlist: str = "/usr/share/wordlists/rockyou.txt",
        format_type: str = "",
        additional_args: str = ""
    ) -> Dict[str, Any]:
        """
        Execute John the Ripper for password cracking with enhanced logging.

        Args:
            hash_file: File containing password hashes
            wordlist: Wordlist file to use
            format_type: Hash format type
            additional_args: Additional John arguments

        Returns:
            Password cracking results
        """
        data = {
            "hash_file": hash_file,
            "wordlist": wordlist,
            "format": format_type,
            "additional_args": additional_args
        }
        logger.info(f"🔐 Starting John the Ripper: {hash_file}")
        result = hexstrike_client.safe_post("api/tools/john", data)
        if result.get("success"):
            logger.info(f"✅ John the Ripper completed")
        else:
            logger.error(f"❌ John the Ripper failed")
        return result

    @mcp.tool()
    def wpscan_analyze(url: str, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute WPScan for WordPress vulnerability scanning with enhanced logging.

        Args:
            url: The WordPress site URL
            additional_args: Additional WPScan arguments

        Returns:
            WordPress vulnerability scan results
        """
        data = {
            "url": url,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting WPScan: {url}")
        result = hexstrike_client.safe_post("api/tools/wpscan", data)
        if result.get("success"):
            logger.info(f"✅ WPScan completed for {url}")
        else:
            logger.error(f"❌ WPScan failed for {url}")
        return result

    @mcp.tool()
    def enum4linux_scan(target: str, additional_args: str = "-a") -> Dict[str, Any]:
        """
        Execute Enum4linux for SMB enumeration with enhanced logging.

        Args:
            target: The target IP address
            additional_args: Additional Enum4linux arguments

        Returns:
            SMB enumeration results
        """
        data = {
            "target": target,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Enum4linux: {target}")
        result = hexstrike_client.safe_post("api/tools/enum4linux", data)
        if result.get("success"):
            logger.info(f"✅ Enum4linux completed for {target}")
        else:
            logger.error(f"❌ Enum4linux failed for {target}")
        return result

    @mcp.tool()
    def ffuf_scan(url: str, wordlist: str = "/usr/share/wordlists/dirb/common.txt", mode: str = "directory", match_codes: str = "200,204,301,302,307,401,403", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute FFuf for web fuzzing with enhanced logging.

        Args:
            url: The target URL
            wordlist: Wordlist file to use
            mode: Fuzzing mode (directory, vhost, parameter)
            match_codes: HTTP status codes to match
            additional_args: Additional FFuf arguments

        Returns:
            Web fuzzing results
        """
        data = {
            "url": url,
            "wordlist": wordlist,
            "mode": mode,
            "match_codes": match_codes,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting FFuf {mode} fuzzing: {url}")
        result = hexstrike_client.safe_post("api/tools/ffuf", data)
        if result.get("success"):
            logger.info(f"✅ FFuf fuzzing completed for {url}")
        else:
            logger.error(f"❌ FFuf fuzzing failed for {url}")
        return result

    @mcp.tool()
    def netexec_scan(target: str, protocol: str = "smb", username: str = "", password: str = "", hash_value: str = "", module: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute NetExec (formerly CrackMapExec) for network enumeration with enhanced logging.

        Args:
            target: The target IP or network
            protocol: Protocol to use (smb, ssh, winrm, etc.)
            username: Username for authentication
            password: Password for authentication
            hash_value: Hash for pass-the-hash attacks
            module: NetExec module to execute
            additional_args: Additional NetExec arguments

        Returns:
            Network enumeration results
        """
        data = {
            "target": target,
            "protocol": protocol,
            "username": username,
            "password": password,
            "hash": hash_value,
            "module": module,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting NetExec {protocol} scan: {target}")
        result = hexstrike_client.safe_post("api/tools/netexec", data)
        if result.get("success"):
            logger.info(f"✅ NetExec scan completed for {target}")
        else:
            logger.error(f"❌ NetExec scan failed for {target}")
        return result

    @mcp.tool()
    def amass_scan(domain: str, mode: str = "enum", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Amass for subdomain enumeration with enhanced logging.

        Args:
            domain: The target domain
            mode: Amass mode (enum, intel, viz)
            additional_args: Additional Amass arguments

        Returns:
            Subdomain enumeration results
        """
        data = {
            "domain": domain,
            "mode": mode,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Amass {mode}: {domain}")
        result = hexstrike_client.safe_post("api/tools/amass", data)
        if result.get("success"):
            logger.info(f"✅ Amass completed for {domain}")
        else:
            logger.error(f"❌ Amass failed for {domain}")
        return result

    @mcp.tool()
    def hashcat_crack(hash_file: str, hash_type: str, attack_mode: str = "0", wordlist: str = "/usr/share/wordlists/rockyou.txt", mask: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Hashcat for advanced password cracking with enhanced logging.

        Args:
            hash_file: File containing password hashes
            hash_type: Hash type number for Hashcat
            attack_mode: Attack mode (0=dict, 1=combo, 3=mask, etc.)
            wordlist: Wordlist file for dictionary attacks
            mask: Mask for mask attacks
            additional_args: Additional Hashcat arguments

        Returns:
            Password cracking results
        """
        data = {
            "hash_file": hash_file,
            "hash_type": hash_type,
            "attack_mode": attack_mode,
            "wordlist": wordlist,
            "mask": mask,
            "additional_args": additional_args
        }
        logger.info(f"🔐 Starting Hashcat attack: mode {attack_mode}")
        result = hexstrike_client.safe_post("api/tools/hashcat", data)
        if result.get("success"):
            logger.info(f"✅ Hashcat attack completed")
        else:
            logger.error(f"❌ Hashcat attack failed")
        return result

    @mcp.tool()
    def subfinder_scan(domain: str, silent: bool = True, all_sources: bool = False, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Subfinder for passive subdomain enumeration with enhanced logging.

        Args:
            domain: The target domain
            silent: Run in silent mode
            all_sources: Use all sources
            additional_args: Additional Subfinder arguments

        Returns:
            Passive subdomain enumeration results
        """
        data = {
            "domain": domain,
            "silent": silent,
            "all_sources": all_sources,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Subfinder: {domain}")
        result = hexstrike_client.safe_post("api/tools/subfinder", data)
        if result.get("success"):
            logger.info(f"✅ Subfinder completed for {domain}")
        else:
            logger.error(f"❌ Subfinder failed for {domain}")
        return result

    @mcp.tool()
    def smbmap_scan(target: str, username: str = "", password: str = "", domain: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute SMBMap for SMB share enumeration with enhanced logging.

        Args:
            target: The target IP address
            username: Username for authentication
            password: Password for authentication
            domain: Domain for authentication
            additional_args: Additional SMBMap arguments

        Returns:
            SMB share enumeration results
        """
        data = {
            "target": target,
            "username": username,
            "password": password,
            "domain": domain,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting SMBMap: {target}")
        result = hexstrike_client.safe_post("api/tools/smbmap", data)
        if result.get("success"):
            logger.info(f"✅ SMBMap completed for {target}")
        else:
            logger.error(f"❌ SMBMap failed for {target}")
        return result

    # ============================================================================
    # ENHANCED NETWORK PENETRATION TESTING TOOLS (v6.0)
    # ============================================================================

    @mcp.tool()
    def rustscan_fast_scan(target: str, ports: str = "", ulimit: int = 5000,
                          batch_size: int = 4500, timeout: int = 1500,
                          scripts: bool = False, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Rustscan for ultra-fast port scanning with enhanced logging.

        Args:
            target: The target IP address or hostname
            ports: Specific ports to scan (e.g., "22,80,443")
            ulimit: File descriptor limit
            batch_size: Batch size for scanning
            timeout: Timeout in milliseconds
            scripts: Run Nmap scripts on discovered ports
            additional_args: Additional Rustscan arguments

        Returns:
            Ultra-fast port scanning results
        """
        data = {
            "target": target,
            "ports": ports,
            "ulimit": ulimit,
            "batch_size": batch_size,
            "timeout": timeout,
            "scripts": scripts,
            "additional_args": additional_args
        }
        logger.info(f"⚡ Starting Rustscan: {target}")
        result = hexstrike_client.safe_post("api/tools/rustscan", data)
        if result.get("success"):
            logger.info(f"✅ Rustscan completed for {target}")
        else:
            logger.error(f"❌ Rustscan failed for {target}")
        return result

    @mcp.tool()
    def masscan_high_speed(target: str, ports: str = "1-65535", rate: int = 1000,
                          interface: str = "", router_mac: str = "", source_ip: str = "",
                          banners: bool = False, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Masscan for high-speed Internet-scale port scanning with intelligent rate limiting.

        Args:
            target: The target IP address or CIDR range
            ports: Port range to scan
            rate: Packets per second rate
            interface: Network interface to use
            router_mac: Router MAC address
            source_ip: Source IP address
            banners: Enable banner grabbing
            additional_args: Additional Masscan arguments

        Returns:
            High-speed port scanning results with intelligent rate limiting
        """
        data = {
            "target": target,
            "ports": ports,
            "rate": rate,
            "interface": interface,
            "router_mac": router_mac,
            "source_ip": source_ip,
            "banners": banners,
            "additional_args": additional_args
        }
        logger.info(f"🚀 Starting Masscan: {target} at rate {rate}")
        result = hexstrike_client.safe_post("api/tools/masscan", data)
        if result.get("success"):
            logger.info(f"✅ Masscan completed for {target}")
        else:
            logger.error(f"❌ Masscan failed for {target}")
        return result

    @mcp.tool()
    def nmap_advanced_scan(target: str, scan_type: str = "-sS", ports: str = "",
                          timing: str = "T4", nse_scripts: str = "", os_detection: bool = False,
                          version_detection: bool = False, aggressive: bool = False,
                          stealth: bool = False, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute advanced Nmap scans with custom NSE scripts and optimized timing.

        Args:
            target: The target IP address or hostname
            scan_type: Nmap scan type (e.g., -sS, -sT, -sU)
            ports: Specific ports to scan
            timing: Timing template (T0-T5)
            nse_scripts: Custom NSE scripts to run
            os_detection: Enable OS detection
            version_detection: Enable version detection
            aggressive: Enable aggressive scanning
            stealth: Enable stealth mode
            additional_args: Additional Nmap arguments

        Returns:
            Advanced Nmap scanning results with custom NSE scripts
        """
        data = {
            "target": target,
            "scan_type": scan_type,
            "ports": ports,
            "timing": timing,
            "nse_scripts": nse_scripts,
            "os_detection": os_detection,
            "version_detection": version_detection,
            "aggressive": aggressive,
            "stealth": stealth,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Advanced Nmap: {target}")
        result = hexstrike_client.safe_post("api/tools/nmap-advanced", data)
        if result.get("success"):
            logger.info(f"✅ Advanced Nmap completed for {target}")
        else:
            logger.error(f"❌ Advanced Nmap failed for {target}")
        return result

    @mcp.tool()
    def autorecon_comprehensive(target: str, output_dir: str = "/tmp/autorecon",
                               port_scans: str = "top-100-ports", service_scans: str = "default",
                               heartbeat: int = 60, timeout: int = 300,
                               additional_args: str = "") -> Dict[str, Any]:
        """
        Execute AutoRecon for comprehensive automated reconnaissance.

        Args:
            target: The target IP address or hostname
            output_dir: Output directory for results
            port_scans: Port scan configuration
            service_scans: Service scan configuration
            heartbeat: Heartbeat interval in seconds
            timeout: Timeout for individual scans
            additional_args: Additional AutoRecon arguments

        Returns:
            Comprehensive automated reconnaissance results
        """
        data = {
            "target": target,
            "output_dir": output_dir,
            "port_scans": port_scans,
            "service_scans": service_scans,
            "heartbeat": heartbeat,
            "timeout": timeout,
            "additional_args": additional_args
        }
        logger.info(f"🔄 Starting AutoRecon: {target}")
        result = hexstrike_client.safe_post("api/tools/autorecon", data)
        if result.get("success"):
            logger.info(f"✅ AutoRecon completed for {target}")
        else:
            logger.error(f"❌ AutoRecon failed for {target}")
        return result

    @mcp.tool()
    def enum4linux_ng_advanced(target: str, username: str = "", password: str = "",
                               domain: str = "", shares: bool = True, users: bool = True,
                               groups: bool = True, policy: bool = True,
                               additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Enum4linux-ng for advanced SMB enumeration with enhanced logging.

        Args:
            target: The target IP address
            username: Username for authentication
            password: Password for authentication
            domain: Domain for authentication
            shares: Enumerate shares
            users: Enumerate users
            groups: Enumerate groups
            policy: Enumerate policies
            additional_args: Additional Enum4linux-ng arguments

        Returns:
            Advanced SMB enumeration results
        """
        data = {
            "target": target,
            "username": username,
            "password": password,
            "domain": domain,
            "shares": shares,
            "users": users,
            "groups": groups,
            "policy": policy,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Enum4linux-ng: {target}")
        result = hexstrike_client.safe_post("api/tools/enum4linux-ng", data)
        if result.get("success"):
            logger.info(f"✅ Enum4linux-ng completed for {target}")
        else:
            logger.error(f"❌ Enum4linux-ng failed for {target}")
        return result

    @mcp.tool()
    def rpcclient_enumeration(target: str, username: str = "", password: str = "",
                             domain: str = "", commands: str = "enumdomusers;enumdomgroups;querydominfo",
                             additional_args: str = "") -> Dict[str, Any]:
        """
        Execute rpcclient for RPC enumeration with enhanced logging.

        Args:
            target: The target IP address
            username: Username for authentication
            password: Password for authentication
            domain: Domain for authentication
            commands: Semicolon-separated RPC commands
            additional_args: Additional rpcclient arguments

        Returns:
            RPC enumeration results
        """
        data = {
            "target": target,
            "username": username,
            "password": password,
            "domain": domain,
            "commands": commands,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting rpcclient: {target}")
        result = hexstrike_client.safe_post("api/tools/rpcclient", data)
        if result.get("success"):
            logger.info(f"✅ rpcclient completed for {target}")
        else:
            logger.error(f"❌ rpcclient failed for {target}")
        return result

    @mcp.tool()
    def nbtscan_netbios(target: str, verbose: bool = False, timeout: int = 2,
                       additional_args: str = "") -> Dict[str, Any]:
        """
        Execute nbtscan for NetBIOS name scanning with enhanced logging.

        Args:
            target: The target IP address or range
            verbose: Enable verbose output
            timeout: Timeout in seconds
            additional_args: Additional nbtscan arguments

        Returns:
            NetBIOS name scanning results
        """
        data = {
            "target": target,
            "verbose": verbose,
            "timeout": timeout,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting nbtscan: {target}")
        result = hexstrike_client.safe_post("api/tools/nbtscan", data)
        if result.get("success"):
            logger.info(f"✅ nbtscan completed for {target}")
        else:
            logger.error(f"❌ nbtscan failed for {target}")
        return result

    @mcp.tool()
    def arp_scan_discovery(target: str = "", interface: str = "", local_network: bool = False,
                          timeout: int = 500, retry: int = 3, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute arp-scan for network discovery with enhanced logging.

        Args:
            target: The target IP range (if not using local_network)
            interface: Network interface to use
            local_network: Scan local network
            timeout: Timeout in milliseconds
            retry: Number of retries
            additional_args: Additional arp-scan arguments

        Returns:
            Network discovery results via ARP scanning
        """
        data = {
            "target": target,
            "interface": interface,
            "local_network": local_network,
            "timeout": timeout,
            "retry": retry,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting arp-scan: {target if target else 'local network'}")
        result = hexstrike_client.safe_post("api/tools/arp-scan", data)
        if result.get("success"):
            logger.info(f"✅ arp-scan completed")
        else:
            logger.error(f"❌ arp-scan failed")
        return result

    @mcp.tool()
    def responder_credential_harvest(interface: str = "eth0", analyze: bool = False,
                                   wpad: bool = True, force_wpad_auth: bool = False,
                                   fingerprint: bool = False, duration: int = 300,
                                   additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Responder for credential harvesting with enhanced logging.

        Args:
            interface: Network interface to use
            analyze: Analyze mode only
            wpad: Enable WPAD rogue proxy
            force_wpad_auth: Force WPAD authentication
            fingerprint: Fingerprint mode
            duration: Duration to run in seconds
            additional_args: Additional Responder arguments

        Returns:
            Credential harvesting results
        """
        data = {
            "interface": interface,
            "analyze": analyze,
            "wpad": wpad,
            "force_wpad_auth": force_wpad_auth,
            "fingerprint": fingerprint,
            "duration": duration,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Responder on interface: {interface}")
        result = hexstrike_client.safe_post("api/tools/responder", data)
        if result.get("success"):
            logger.info(f"✅ Responder completed")
        else:
            logger.error(f"❌ Responder failed")
        return result

    @mcp.tool()
    def volatility_analyze(memory_file: str, plugin: str, profile: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Volatility for memory forensics analysis with enhanced logging.

        Args:
            memory_file: Path to memory dump file
            plugin: Volatility plugin to use
            profile: Memory profile to use
            additional_args: Additional Volatility arguments

        Returns:
            Memory forensics analysis results
        """
        data = {
            "memory_file": memory_file,
            "plugin": plugin,
            "profile": profile,
            "additional_args": additional_args
        }
        logger.info(f"🧠 Starting Volatility analysis: {plugin}")
        result = hexstrike_client.safe_post("api/tools/volatility", data)
        if result.get("success"):
            logger.info(f"✅ Volatility analysis completed")
        else:
            logger.error(f"❌ Volatility analysis failed")
        return result

    @mcp.tool()
    def msfvenom_generate(payload: str, format_type: str = "", output_file: str = "", encoder: str = "", iterations: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute MSFVenom for payload generation with enhanced logging.

        Args:
            payload: The payload to generate
            format_type: Output format (exe, elf, raw, etc.)
            output_file: Output file path
            encoder: Encoder to use
            iterations: Number of encoding iterations
            additional_args: Additional MSFVenom arguments

        Returns:
            Payload generation results
        """
        data = {
            "payload": payload,
            "format": format_type,
            "output_file": output_file,
            "encoder": encoder,
            "iterations": iterations,
            "additional_args": additional_args
        }
        logger.info(f"🚀 Starting MSFVenom payload generation: {payload}")
        result = hexstrike_client.safe_post("api/tools/msfvenom", data)
        if result.get("success"):
            logger.info(f"✅ MSFVenom payload generated")
        else:
            logger.error(f"❌ MSFVenom payload generation failed")
        return result

    # ============================================================================
    # BINARY ANALYSIS & REVERSE ENGINEERING TOOLS
    # ============================================================================

    @mcp.tool()
    def gdb_analyze(binary: str, commands: str = "", script_file: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute GDB for binary analysis and debugging with enhanced logging.

        Args:
            binary: Path to the binary file
            commands: GDB commands to execute
            script_file: Path to GDB script file
            additional_args: Additional GDB arguments

        Returns:
            Binary analysis results
        """
        data = {
            "binary": binary,
            "commands": commands,
            "script_file": script_file,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting GDB analysis: {binary}")
        result = hexstrike_client.safe_post("api/tools/gdb", data)
        if result.get("success"):
            logger.info(f"✅ GDB analysis completed for {binary}")
        else:
            logger.error(f"❌ GDB analysis failed for {binary}")
        return result

    @mcp.tool()
    def radare2_analyze(binary: str, commands: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Radare2 for binary analysis and reverse engineering with enhanced logging.

        Args:
            binary: Path to the binary file
            commands: Radare2 commands to execute
            additional_args: Additional Radare2 arguments

        Returns:
            Binary analysis results
        """
        data = {
            "binary": binary,
            "commands": commands,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting Radare2 analysis: {binary}")
        result = hexstrike_client.safe_post("api/tools/radare2", data)
        if result.get("success"):
            logger.info(f"✅ Radare2 analysis completed for {binary}")
        else:
            logger.error(f"❌ Radare2 analysis failed for {binary}")
        return result

    @mcp.tool()
    def binwalk_analyze(file_path: str, extract: bool = False, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Binwalk for firmware and file analysis with enhanced logging.

        Args:
            file_path: Path to the file to analyze
            extract: Whether to extract discovered files
            additional_args: Additional Binwalk arguments

        Returns:
            Firmware analysis results
        """
        data = {
            "file_path": file_path,
            "extract": extract,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting Binwalk analysis: {file_path}")
        result = hexstrike_client.safe_post("api/tools/binwalk", data)
        if result.get("success"):
            logger.info(f"✅ Binwalk analysis completed for {file_path}")
        else:
            logger.error(f"❌ Binwalk analysis failed for {file_path}")
        return result

    @mcp.tool()
    def ropgadget_search(binary: str, gadget_type: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Search for ROP gadgets in a binary using ROPgadget with enhanced logging.

        Args:
            binary: Path to the binary file
            gadget_type: Type of gadgets to search for
            additional_args: Additional ROPgadget arguments

        Returns:
            ROP gadget search results
        """
        data = {
            "binary": binary,
            "gadget_type": gadget_type,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting ROPgadget search: {binary}")
        result = hexstrike_client.safe_post("api/tools/ropgadget", data)
        if result.get("success"):
            logger.info(f"✅ ROPgadget search completed for {binary}")
        else:
            logger.error(f"❌ ROPgadget search failed for {binary}")
        return result

    @mcp.tool()
    def checksec_analyze(binary: str) -> Dict[str, Any]:
        """
        Check security features of a binary with enhanced logging.

        Args:
            binary: Path to the binary file

        Returns:
            Security features analysis results
        """
        data = {
            "binary": binary
        }
        logger.info(f"🔧 Starting Checksec analysis: {binary}")
        result = hexstrike_client.safe_post("api/tools/checksec", data)
        if result.get("success"):
            logger.info(f"✅ Checksec analysis completed for {binary}")
        else:
            logger.error(f"❌ Checksec analysis failed for {binary}")
        return result

    @mcp.tool()
    def xxd_hexdump(file_path: str, offset: str = "0", length: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Create a hex dump of a file using xxd with enhanced logging.

        Args:
            file_path: Path to the file
            offset: Offset to start reading from
            length: Number of bytes to read
            additional_args: Additional xxd arguments

        Returns:
            Hex dump results
        """
        data = {
            "file_path": file_path,
            "offset": offset,
            "length": length,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting XXD hex dump: {file_path}")
        result = hexstrike_client.safe_post("api/tools/xxd", data)
        if result.get("success"):
            logger.info(f"✅ XXD hex dump completed for {file_path}")
        else:
            logger.error(f"❌ XXD hex dump failed for {file_path}")
        return result

    @mcp.tool()
    def strings_extract(file_path: str, min_len: int = 4, additional_args: str = "") -> Dict[str, Any]:
        """
        Extract strings from a binary file with enhanced logging.

        Args:
            file_path: Path to the file
            min_len: Minimum string length
            additional_args: Additional strings arguments

        Returns:
            String extraction results
        """
        data = {
            "file_path": file_path,
            "min_len": min_len,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting Strings extraction: {file_path}")
        result = hexstrike_client.safe_post("api/tools/strings", data)
        if result.get("success"):
            logger.info(f"✅ Strings extraction completed for {file_path}")
        else:
            logger.error(f"❌ Strings extraction failed for {file_path}")
        return result

    @mcp.tool()
    def objdump_analyze(binary: str, disassemble: bool = True, additional_args: str = "") -> Dict[str, Any]:
        """
        Analyze a binary using objdump with enhanced logging.

        Args:
            binary: Path to the binary file
            disassemble: Whether to disassemble the binary
            additional_args: Additional objdump arguments

        Returns:
            Binary analysis results
        """
        data = {
            "binary": binary,
            "disassemble": disassemble,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting Objdump analysis: {binary}")
        result = hexstrike_client.safe_post("api/tools/objdump", data)
        if result.get("success"):
            logger.info(f"✅ Objdump analysis completed for {binary}")
        else:
            logger.error(f"❌ Objdump analysis failed for {binary}")
        return result

    # ============================================================================
    # ENHANCED BINARY ANALYSIS AND EXPLOITATION FRAMEWORK (v6.0)
    # ============================================================================

    @mcp.tool()
    def ghidra_analysis(binary: str, project_name: str = "hexstrike_analysis",
                       script_file: str = "", analysis_timeout: int = 300,
                       output_format: str = "xml", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Ghidra for advanced binary analysis and reverse engineering.

        Args:
            binary: Path to the binary file
            project_name: Ghidra project name
            script_file: Custom Ghidra script to run
            analysis_timeout: Analysis timeout in seconds
            output_format: Output format (xml, json)
            additional_args: Additional Ghidra arguments

        Returns:
            Advanced binary analysis results from Ghidra
        """
        data = {
            "binary": binary,
            "project_name": project_name,
            "script_file": script_file,
            "analysis_timeout": analysis_timeout,
            "output_format": output_format,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting Ghidra analysis: {binary}")
        result = hexstrike_client.safe_post("api/tools/ghidra", data)
        if result.get("success"):
            logger.info(f"✅ Ghidra analysis completed for {binary}")
        else:
            logger.error(f"❌ Ghidra analysis failed for {binary}")
        return result

    @mcp.tool()
    def pwntools_exploit(script_content: str = "", target_binary: str = "",
                        target_host: str = "", target_port: int = 0,
                        exploit_type: str = "local", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Pwntools for exploit development and automation.

        Args:
            script_content: Python script content using pwntools
            target_binary: Local binary to exploit
            target_host: Remote host to connect to
            target_port: Remote port to connect to
            exploit_type: Type of exploit (local, remote, format_string, rop)
            additional_args: Additional arguments

        Returns:
            Exploit execution results
        """
        data = {
            "script_content": script_content,
            "target_binary": target_binary,
            "target_host": target_host,
            "target_port": target_port,
            "exploit_type": exploit_type,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting Pwntools exploit: {exploit_type}")
        result = hexstrike_client.safe_post("api/tools/pwntools", data)
        if result.get("success"):
            logger.info(f"✅ Pwntools exploit completed")
        else:
            logger.error(f"❌ Pwntools exploit failed")
        return result

    @mcp.tool()
    def one_gadget_search(libc_path: str, level: int = 1, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute one_gadget to find one-shot RCE gadgets in libc.

        Args:
            libc_path: Path to libc binary
            level: Constraint level (0, 1, 2)
            additional_args: Additional one_gadget arguments

        Returns:
            One-shot RCE gadget search results
        """
        data = {
            "libc_path": libc_path,
            "level": level,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting one_gadget analysis: {libc_path}")
        result = hexstrike_client.safe_post("api/tools/one-gadget", data)
        if result.get("success"):
            logger.info(f"✅ one_gadget analysis completed")
        else:
            logger.error(f"❌ one_gadget analysis failed")
        return result

    @mcp.tool()
    def libc_database_lookup(action: str = "find", symbols: str = "",
                            libc_id: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute libc-database for libc identification and offset lookup.

        Args:
            action: Action to perform (find, dump, download)
            symbols: Symbols with offsets for find action (format: "symbol1:offset1 symbol2:offset2")
            libc_id: Libc ID for dump/download actions
            additional_args: Additional arguments

        Returns:
            Libc database lookup results
        """
        data = {
            "action": action,
            "symbols": symbols,
            "libc_id": libc_id,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting libc-database {action}: {symbols or libc_id}")
        result = hexstrike_client.safe_post("api/tools/libc-database", data)
        if result.get("success"):
            logger.info(f"✅ libc-database {action} completed")
        else:
            logger.error(f"❌ libc-database {action} failed")
        return result

    @mcp.tool()
    def gdb_peda_debug(binary: str = "", commands: str = "", attach_pid: int = 0,
                      core_file: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute GDB with PEDA for enhanced debugging and exploitation.

        Args:
            binary: Binary to debug
            commands: GDB commands to execute
            attach_pid: Process ID to attach to
            core_file: Core dump file to analyze
            additional_args: Additional GDB arguments

        Returns:
            Enhanced debugging results with PEDA
        """
        data = {
            "binary": binary,
            "commands": commands,
            "attach_pid": attach_pid,
            "core_file": core_file,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting GDB-PEDA analysis: {binary or f'PID {attach_pid}' or core_file}")
        result = hexstrike_client.safe_post("api/tools/gdb-peda", data)
        if result.get("success"):
            logger.info(f"✅ GDB-PEDA analysis completed")
        else:
            logger.error(f"❌ GDB-PEDA analysis failed")
        return result

    @mcp.tool()
    def angr_symbolic_execution(binary: str, script_content: str = "",
                               find_address: str = "", avoid_addresses: str = "",
                               analysis_type: str = "symbolic", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute angr for symbolic execution and binary analysis.

        Args:
            binary: Binary to analyze
            script_content: Custom angr script content
            find_address: Address to find during symbolic execution
            avoid_addresses: Comma-separated addresses to avoid
            analysis_type: Type of analysis (symbolic, cfg, static)
            additional_args: Additional arguments

        Returns:
            Symbolic execution and binary analysis results
        """
        data = {
            "binary": binary,
            "script_content": script_content,
            "find_address": find_address,
            "avoid_addresses": avoid_addresses,
            "analysis_type": analysis_type,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting angr analysis: {binary}")
        result = hexstrike_client.safe_post("api/tools/angr", data)
        if result.get("success"):
            logger.info(f"✅ angr analysis completed")
        else:
            logger.error(f"❌ angr analysis failed")
        return result

    @mcp.tool()
    def ropper_gadget_search(binary: str, gadget_type: str = "rop", quality: int = 1,
                            arch: str = "", search_string: str = "",
                            additional_args: str = "") -> Dict[str, Any]:
        """
        Execute ropper for advanced ROP/JOP gadget searching.

        Args:
            binary: Binary to search for gadgets
            gadget_type: Type of gadgets (rop, jop, sys, all)
            quality: Gadget quality level (1-5)
            arch: Target architecture (x86, x86_64, arm, etc.)
            search_string: Specific gadget pattern to search for
            additional_args: Additional ropper arguments

        Returns:
            Advanced ROP/JOP gadget search results
        """
        data = {
            "binary": binary,
            "gadget_type": gadget_type,
            "quality": quality,
            "arch": arch,
            "search_string": search_string,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting ropper analysis: {binary}")
        result = hexstrike_client.safe_post("api/tools/ropper", data)
        if result.get("success"):
            logger.info(f"✅ ropper analysis completed")
        else:
            logger.error(f"❌ ropper analysis failed")
        return result

    @mcp.tool()
    def pwninit_setup(binary: str, libc: str = "", ld: str = "",
                     template_type: str = "python", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute pwninit for CTF binary exploitation setup.

        Args:
            binary: Binary file to set up
            libc: Libc file to use
            ld: Loader file to use
            template_type: Template type (python, c)
            additional_args: Additional pwninit arguments

        Returns:
            CTF binary exploitation setup results
        """
        data = {
            "binary": binary,
            "libc": libc,
            "ld": ld,
            "template_type": template_type,
            "additional_args": additional_args
        }
        logger.info(f"🔧 Starting pwninit setup: {binary}")
        result = hexstrike_client.safe_post("api/tools/pwninit", data)
        if result.get("success"):
            logger.info(f"✅ pwninit setup completed")
        else:
            logger.error(f"❌ pwninit setup failed")
        return result

    @mcp.tool()
    def feroxbuster_scan(url: str, wordlist: str = "/usr/share/wordlists/dirb/common.txt", threads: int = 10, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Feroxbuster for recursive content discovery with enhanced logging.

        Args:
            url: The target URL
            wordlist: Wordlist file to use
            threads: Number of threads
            additional_args: Additional Feroxbuster arguments

        Returns:
            Content discovery results
        """
        data = {
            "url": url,
            "wordlist": wordlist,
            "threads": threads,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Feroxbuster scan: {url}")
        result = hexstrike_client.safe_post("api/tools/feroxbuster", data)
        if result.get("success"):
            logger.info(f"✅ Feroxbuster scan completed for {url}")
        else:
            logger.error(f"❌ Feroxbuster scan failed for {url}")
        return result

    @mcp.tool()
    def dotdotpwn_scan(target: str, module: str = "http", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute DotDotPwn for directory traversal testing with enhanced logging.

        Args:
            target: The target hostname or IP
            module: Module to use (http, ftp, tftp, etc.)
            additional_args: Additional DotDotPwn arguments

        Returns:
            Directory traversal test results
        """
        data = {
            "target": target,
            "module": module,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting DotDotPwn scan: {target}")
        result = hexstrike_client.safe_post("api/tools/dotdotpwn", data)
        if result.get("success"):
            logger.info(f"✅ DotDotPwn scan completed for {target}")
        else:
            logger.error(f"❌ DotDotPwn scan failed for {target}")
        return result

    @mcp.tool()
    def xsser_scan(url: str, params: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute XSSer for XSS vulnerability testing with enhanced logging.

        Args:
            url: The target URL
            params: Parameters to test
            additional_args: Additional XSSer arguments

        Returns:
            XSS vulnerability test results
        """
        data = {
            "url": url,
            "params": params,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting XSSer scan: {url}")
        result = hexstrike_client.safe_post("api/tools/xsser", data)
        if result.get("success"):
            logger.info(f"✅ XSSer scan completed for {url}")
        else:
            logger.error(f"❌ XSSer scan failed for {url}")
        return result

    @mcp.tool()
    def wfuzz_scan(url: str, wordlist: str = "/usr/share/wordlists/dirb/common.txt", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Wfuzz for web application fuzzing with enhanced logging.

        Args:
            url: The target URL (use FUZZ where you want to inject payloads)
            wordlist: Wordlist file to use
            additional_args: Additional Wfuzz arguments

        Returns:
            Web application fuzzing results
        """
        data = {
            "url": url,
            "wordlist": wordlist,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Wfuzz scan: {url}")
        result = hexstrike_client.safe_post("api/tools/wfuzz", data)
        if result.get("success"):
            logger.info(f"✅ Wfuzz scan completed for {url}")
        else:
            logger.error(f"❌ Wfuzz scan failed for {url}")
        return result

    # ============================================================================
    # ENHANCED WEB APPLICATION SECURITY TOOLS (v6.0)
    # ============================================================================

    @mcp.tool()
    def dirsearch_scan(url: str, extensions: str = "php,html,js,txt,xml,json",
                      wordlist: str = "/usr/share/wordlists/dirsearch/common.txt",
                      threads: int = 30, recursive: bool = False, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Dirsearch for advanced directory and file discovery with enhanced logging.

        Args:
            url: The target URL
            extensions: File extensions to search for
            wordlist: Wordlist file to use
            threads: Number of threads to use
            recursive: Enable recursive scanning
            additional_args: Additional Dirsearch arguments

        Returns:
            Advanced directory discovery results
        """
        data = {
            "url": url,
            "extensions": extensions,
            "wordlist": wordlist,
            "threads": threads,
            "recursive": recursive,
            "additional_args": additional_args
        }
        logger.info(f"📁 Starting Dirsearch scan: {url}")
        result = hexstrike_client.safe_post("api/tools/dirsearch", data)
        if result.get("success"):
            logger.info(f"✅ Dirsearch scan completed for {url}")
        else:
            logger.error(f"❌ Dirsearch scan failed for {url}")
        return result

    @mcp.tool()
    def katana_crawl(url: str, depth: int = 3, js_crawl: bool = True,
                    form_extraction: bool = True, output_format: str = "json",
                    additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Katana for next-generation crawling and spidering with enhanced logging.

        Args:
            url: The target URL to crawl
            depth: Crawling depth
            js_crawl: Enable JavaScript crawling
            form_extraction: Enable form extraction
            output_format: Output format (json, txt)
            additional_args: Additional Katana arguments

        Returns:
            Advanced web crawling results with endpoints and forms
        """
        data = {
            "url": url,
            "depth": depth,
            "js_crawl": js_crawl,
            "form_extraction": form_extraction,
            "output_format": output_format,
            "additional_args": additional_args
        }
        logger.info(f"⚔️  Starting Katana crawl: {url}")
        result = hexstrike_client.safe_post("api/tools/katana", data)
        if result.get("success"):
            logger.info(f"✅ Katana crawl completed for {url}")
        else:
            logger.error(f"❌ Katana crawl failed for {url}")
        return result

    @mcp.tool()
    def gau_discovery(domain: str, providers: str = "wayback,commoncrawl,otx,urlscan",
                     include_subs: bool = True, blacklist: str = "png,jpg,gif,jpeg,swf,woff,svg,pdf,css,ico",
                     additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Gau (Get All URLs) for URL discovery from multiple sources with enhanced logging.

        Args:
            domain: The target domain
            providers: Data providers to use
            include_subs: Include subdomains
            blacklist: File extensions to blacklist
            additional_args: Additional Gau arguments

        Returns:
            Comprehensive URL discovery results from multiple sources
        """
        data = {
            "domain": domain,
            "providers": providers,
            "include_subs": include_subs,
            "blacklist": blacklist,
            "additional_args": additional_args
        }
        logger.info(f"📡 Starting Gau URL discovery: {domain}")
        result = hexstrike_client.safe_post("api/tools/gau", data)
        if result.get("success"):
            logger.info(f"✅ Gau URL discovery completed for {domain}")
        else:
            logger.error(f"❌ Gau URL discovery failed for {domain}")
        return result

    @mcp.tool()
    def waybackurls_discovery(domain: str, get_versions: bool = False,
                             no_subs: bool = False, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Waybackurls for historical URL discovery with enhanced logging.

        Args:
            domain: The target domain
            get_versions: Get all versions of URLs
            no_subs: Don't include subdomains
            additional_args: Additional Waybackurls arguments

        Returns:
            Historical URL discovery results from Wayback Machine
        """
        data = {
            "domain": domain,
            "get_versions": get_versions,
            "no_subs": no_subs,
            "additional_args": additional_args
        }
        logger.info(f"🕰️  Starting Waybackurls discovery: {domain}")
        result = hexstrike_client.safe_post("api/tools/waybackurls", data)
        if result.get("success"):
            logger.info(f"✅ Waybackurls discovery completed for {domain}")
        else:
            logger.error(f"❌ Waybackurls discovery failed for {domain}")
        return result

    @mcp.tool()
    def arjun_parameter_discovery(url: str, method: str = "GET", wordlist: str = "",
                                 delay: int = 0, threads: int = 25, stable: bool = False,
                                 additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Arjun for HTTP parameter discovery with enhanced logging.

        Args:
            url: The target URL
            method: HTTP method to use
            wordlist: Custom wordlist file
            delay: Delay between requests
            threads: Number of threads
            stable: Use stable mode
            additional_args: Additional Arjun arguments

        Returns:
            HTTP parameter discovery results
        """
        data = {
            "url": url,
            "method": method,
            "wordlist": wordlist,
            "delay": delay,
            "threads": threads,
            "stable": stable,
            "additional_args": additional_args
        }
        logger.info(f"🎯 Starting Arjun parameter discovery: {url}")
        result = hexstrike_client.safe_post("api/tools/arjun", data)
        if result.get("success"):
            logger.info(f"✅ Arjun parameter discovery completed for {url}")
        else:
            logger.error(f"❌ Arjun parameter discovery failed for {url}")
        return result

    @mcp.tool()
    def paramspider_mining(domain: str, level: int = 2,
                          exclude: str = "png,jpg,gif,jpeg,swf,woff,svg,pdf,css,ico",
                          output: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute ParamSpider for parameter mining from web archives with enhanced logging.

        Args:
            domain: The target domain
            level: Mining level depth
            exclude: File extensions to exclude
            output: Output file path
            additional_args: Additional ParamSpider arguments

        Returns:
            Parameter mining results from web archives
        """
        data = {
            "domain": domain,
            "level": level,
            "exclude": exclude,
            "output": output,
            "additional_args": additional_args
        }
        logger.info(f"🕷️  Starting ParamSpider mining: {domain}")
        result = hexstrike_client.safe_post("api/tools/paramspider", data)
        if result.get("success"):
            logger.info(f"✅ ParamSpider mining completed for {domain}")
        else:
            logger.error(f"❌ ParamSpider mining failed for {domain}")
        return result

    @mcp.tool()
    def x8_parameter_discovery(url: str, wordlist: str = "/usr/share/wordlists/x8/params.txt",
                              method: str = "GET", body: str = "", headers: str = "",
                              additional_args: str = "") -> Dict[str, Any]:
        """
        Execute x8 for hidden parameter discovery with enhanced logging.

        Args:
            url: The target URL
            wordlist: Parameter wordlist
            method: HTTP method
            body: Request body
            headers: Custom headers
            additional_args: Additional x8 arguments

        Returns:
            Hidden parameter discovery results
        """
        data = {
            "url": url,
            "wordlist": wordlist,
            "method": method,
            "body": body,
            "headers": headers,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting x8 parameter discovery: {url}")
        result = hexstrike_client.safe_post("api/tools/x8", data)
        if result.get("success"):
            logger.info(f"✅ x8 parameter discovery completed for {url}")
        else:
            logger.error(f"❌ x8 parameter discovery failed for {url}")
        return result

    @mcp.tool()
    def jaeles_vulnerability_scan(url: str, signatures: str = "", config: str = "",
                                 threads: int = 20, timeout: int = 20,
                                 additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Jaeles for advanced vulnerability scanning with custom signatures.

        Args:
            url: The target URL
            signatures: Custom signature path
            config: Configuration file
            threads: Number of threads
            timeout: Request timeout
            additional_args: Additional Jaeles arguments

        Returns:
            Advanced vulnerability scanning results with custom signatures
        """
        data = {
            "url": url,
            "signatures": signatures,
            "config": config,
            "threads": threads,
            "timeout": timeout,
            "additional_args": additional_args
        }
        logger.info(f"🔬 Starting Jaeles vulnerability scan: {url}")
        result = hexstrike_client.safe_post("api/tools/jaeles", data)
        if result.get("success"):
            logger.info(f"✅ Jaeles vulnerability scan completed for {url}")
        else:
            logger.error(f"❌ Jaeles vulnerability scan failed for {url}")
        return result

    @mcp.tool()
    def dalfox_xss_scan(url: str, pipe_mode: bool = False, blind: bool = False,
                       mining_dom: bool = True, mining_dict: bool = True,
                       custom_payload: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Dalfox for advanced XSS vulnerability scanning with enhanced logging.

        Args:
            url: The target URL
            pipe_mode: Use pipe mode for input
            blind: Enable blind XSS testing
            mining_dom: Enable DOM mining
            mining_dict: Enable dictionary mining
            custom_payload: Custom XSS payload
            additional_args: Additional Dalfox arguments

        Returns:
            Advanced XSS vulnerability scanning results
        """
        data = {
            "url": url,
            "pipe_mode": pipe_mode,
            "blind": blind,
            "mining_dom": mining_dom,
            "mining_dict": mining_dict,
            "custom_payload": custom_payload,
            "additional_args": additional_args
        }
        logger.info(f"🎯 Starting Dalfox XSS scan: {url if url else 'pipe mode'}")
        result = hexstrike_client.safe_post("api/tools/dalfox", data)
        if result.get("success"):
            logger.info(f"✅ Dalfox XSS scan completed")
        else:
            logger.error(f"❌ Dalfox XSS scan failed")
        return result

    @mcp.tool()
    def httpx_probe(target: str, probe: bool = True, tech_detect: bool = False,
                   status_code: bool = False, content_length: bool = False,
                   title: bool = False, web_server: bool = False, threads: int = 50,
                   additional_args: str = "") -> Dict[str, Any]:
        """
        Execute httpx for fast HTTP probing and technology detection.

        Args:
            target: Target file or single URL
            probe: Enable probing
            tech_detect: Enable technology detection
            status_code: Show status codes
            content_length: Show content length
            title: Show page titles
            web_server: Show web server
            threads: Number of threads
            additional_args: Additional httpx arguments

        Returns:
            Fast HTTP probing results with technology detection
        """
        data = {
            "target": target,
            "probe": probe,
            "tech_detect": tech_detect,
            "status_code": status_code,
            "content_length": content_length,
            "title": title,
            "web_server": web_server,
            "threads": threads,
            "additional_args": additional_args
        }
        logger.info(f"🌍 Starting httpx probe: {target}")
        result = hexstrike_client.safe_post("api/tools/httpx", data)
        if result.get("success"):
            logger.info(f"✅ httpx probe completed for {target}")
        else:
            logger.error(f"❌ httpx probe failed for {target}")
        return result

    @mcp.tool()
    def anew_data_processing(input_data: str, output_file: str = "",
                            additional_args: str = "") -> Dict[str, Any]:
        """
        Execute anew for appending new lines to files (useful for data processing).

        Args:
            input_data: Input data to process
            output_file: Output file path
            additional_args: Additional anew arguments

        Returns:
            Data processing results with unique line filtering
        """
        data = {
            "input_data": input_data,
            "output_file": output_file,
            "additional_args": additional_args
        }
        logger.info("📝 Starting anew data processing")
        result = hexstrike_client.safe_post("api/tools/anew", data)
        if result.get("success"):
            logger.info("✅ anew data processing completed")
        else:
            logger.error("❌ anew data processing failed")
        return result

    @mcp.tool()
    def qsreplace_parameter_replacement(urls: str, replacement: str = "FUZZ",
                                       additional_args: str = "") -> Dict[str, Any]:
        """
        Execute qsreplace for query string parameter replacement.

        Args:
            urls: URLs to process
            replacement: Replacement string for parameters
            additional_args: Additional qsreplace arguments

        Returns:
            Parameter replacement results for fuzzing
        """
        data = {
            "urls": urls,
            "replacement": replacement,
            "additional_args": additional_args
        }
        logger.info("🔄 Starting qsreplace parameter replacement")
        result = hexstrike_client.safe_post("api/tools/qsreplace", data)
        if result.get("success"):
            logger.info("✅ qsreplace parameter replacement completed")
        else:
            logger.error("❌ qsreplace parameter replacement failed")
        return result

    @mcp.tool()
    def uro_url_filtering(urls: str, whitelist: str = "", blacklist: str = "",
                         additional_args: str = "") -> Dict[str, Any]:
        """
        Execute uro for filtering out similar URLs.

        Args:
            urls: URLs to filter
            whitelist: Whitelist patterns
            blacklist: Blacklist patterns
            additional_args: Additional uro arguments

        Returns:
            Filtered URL results with duplicates removed
        """
        data = {
            "urls": urls,
            "whitelist": whitelist,
            "blacklist": blacklist,
            "additional_args": additional_args
        }
        logger.info("🔍 Starting uro URL filtering")
        result = hexstrike_client.safe_post("api/tools/uro", data)
        if result.get("success"):
            logger.info("✅ uro URL filtering completed")
        else:
            logger.error("❌ uro URL filtering failed")
        return result

    # ============================================================================
    # AI-POWERED PAYLOAD GENERATION (v5.0 ENHANCEMENT)
    # ============================================================================

    @mcp.tool()
    def ai_generate_payload(attack_type: str, complexity: str = "basic", technology: str = "", url: str = "") -> Dict[str, Any]:
        """
        Generate AI-powered contextual payloads for security testing.

        Args:
            attack_type: Type of attack (xss, sqli, lfi, cmd_injection, ssti, xxe)
            complexity: Complexity level (basic, advanced, bypass)
            technology: Target technology (php, asp, jsp, python, nodejs)
            url: Target URL for context

        Returns:
            Contextual payloads with risk assessment and test cases
        """
        data = {
            "attack_type": attack_type,
            "complexity": complexity,
            "technology": technology,
            "url": url
        }
        logger.info(f"🤖 Generating AI payloads for {attack_type} attack")
        result = hexstrike_client.safe_post("api/ai/generate_payload", data)

        if result.get("success"):
            payload_data = result.get("ai_payload_generation", {})
            count = payload_data.get("payload_count", 0)
            logger.info(f"✅ Generated {count} contextual {attack_type} payloads")

            # Log some example payloads for user awareness
            payloads = payload_data.get("payloads", [])
            if payloads:
                logger.info("🎯 Sample payloads generated:")
                for i, payload_info in enumerate(payloads[:3]):  # Show first 3
                    risk = payload_info.get("risk_level", "UNKNOWN")
                    context = payload_info.get("context", "basic")
                    logger.info(f"   ├─ [{risk}] {context}: {payload_info['payload'][:50]}...")
        else:
            logger.error("❌ AI payload generation failed")

        return result

    @mcp.tool()
    def ai_test_payload(payload: str, target_url: str, method: str = "GET") -> Dict[str, Any]:
        """
        Test generated payload against target with AI analysis.

        Args:
            payload: The payload to test
            target_url: Target URL to test against
            method: HTTP method (GET, POST)

        Returns:
            Test results with AI analysis and vulnerability assessment
        """
        data = {
            "payload": payload,
            "target_url": target_url,
            "method": method
        }
        logger.info(f"🧪 Testing AI payload against {target_url}")
        result = hexstrike_client.safe_post("api/ai/test_payload", data)

        if result.get("success"):
            analysis = result.get("ai_analysis", {})
            potential_vuln = analysis.get("potential_vulnerability", False)
            logger.info(f"🔍 Payload test completed | Vulnerability detected: {potential_vuln}")

            if potential_vuln:
                logger.warning("⚠️  Potential vulnerability found! Review the response carefully.")
            else:
                logger.info("✅ No obvious vulnerability indicators detected")
        else:
            logger.error("❌ Payload testing failed")

        return result

    @mcp.tool()
    def ai_generate_attack_suite(target_url: str, attack_types: str = "xss,sqli,lfi") -> Dict[str, Any]:
        """
        Generate comprehensive attack suite with multiple payload types.

        Args:
            target_url: Target URL for testing
            attack_types: Comma-separated list of attack types

        Returns:
            Comprehensive attack suite with multiple payload types
        """
        attack_list = [attack.strip() for attack in attack_types.split(",")]
        results = {
            "target_url": target_url,
            "attack_types": attack_list,
            "payload_suites": {},
            "summary": {
                "total_payloads": 0,
                "high_risk_payloads": 0,
                "test_cases": 0
            }
        }

        logger.info(f"🚀 Generating comprehensive attack suite for {target_url}")
        logger.info(f"🎯 Attack types: {', '.join(attack_list)}")

        for attack_type in attack_list:
            logger.info(f"🤖 Generating {attack_type} payloads...")

            # Generate payloads for this attack type
            payload_result = self.ai_generate_payload(attack_type, "advanced", "", target_url)

            if payload_result.get("success"):
                payload_data = payload_result.get("ai_payload_generation", {})
                results["payload_suites"][attack_type] = payload_data

                # Update summary
                results["summary"]["total_payloads"] += payload_data.get("payload_count", 0)
                results["summary"]["test_cases"] += len(payload_data.get("test_cases", []))

                # Count high-risk payloads
                for payload_info in payload_data.get("payloads", []):
                    if payload_info.get("risk_level") == "HIGH":
                        results["summary"]["high_risk_payloads"] += 1

        logger.info(f"✅ Attack suite generated:")
        logger.info(f"   ├─ Total payloads: {results['summary']['total_payloads']}")
        logger.info(f"   ├─ High-risk payloads: {results['summary']['high_risk_payloads']}")
        logger.info(f"   └─ Test cases: {results['summary']['test_cases']}")

        return {
            "success": True,
            "attack_suite": results,
            "timestamp": time.time()
        }

    # ============================================================================
    # ADVANCED API TESTING TOOLS (v5.0 ENHANCEMENT)
    # ============================================================================

    @mcp.tool()
    def api_fuzzer(base_url: str, endpoints: str = "", methods: str = "GET,POST,PUT,DELETE", wordlist: str = "/usr/share/wordlists/api/api-endpoints.txt") -> Dict[str, Any]:
        """
        Advanced API endpoint fuzzing with intelligent parameter discovery.

        Args:
            base_url: Base URL of the API
            endpoints: Comma-separated list of specific endpoints to test
            methods: HTTP methods to test (comma-separated)
            wordlist: Wordlist for endpoint discovery

        Returns:
            API fuzzing results with endpoint discovery and vulnerability assessment
        """
        data = {
            "base_url": base_url,
            "endpoints": [e.strip() for e in endpoints.split(",") if e.strip()] if endpoints else [],
            "methods": [m.strip() for m in methods.split(",")],
            "wordlist": wordlist
        }

        logger.info(f"🔍 Starting API fuzzing: {base_url}")
        result = hexstrike_client.safe_post("api/tools/api_fuzzer", data)

        if result.get("success"):
            fuzzing_type = result.get("fuzzing_type", "unknown")
            if fuzzing_type == "endpoint_testing":
                endpoint_count = len(result.get("results", []))
                logger.info(f"✅ API endpoint testing completed: {endpoint_count} endpoints tested")
            else:
                logger.info(f"✅ API endpoint discovery completed")
        else:
            logger.error("❌ API fuzzing failed")

        return result

    @mcp.tool()
    def graphql_scanner(endpoint: str, introspection: bool = True, query_depth: int = 10, test_mutations: bool = True) -> Dict[str, Any]:
        """
        Advanced GraphQL security scanning and introspection.

        Args:
            endpoint: GraphQL endpoint URL
            introspection: Test introspection queries
            query_depth: Maximum query depth to test
            test_mutations: Test mutation operations

        Returns:
            GraphQL security scan results with vulnerability assessment
        """
        data = {
            "endpoint": endpoint,
            "introspection": introspection,
            "query_depth": query_depth,
            "test_mutations": test_mutations
        }

        logger.info(f"🔍 Starting GraphQL security scan: {endpoint}")
        result = hexstrike_client.safe_post("api/tools/graphql_scanner", data)

        if result.get("success"):
            scan_results = result.get("graphql_scan_results", {})
            vuln_count = len(scan_results.get("vulnerabilities", []))
            tests_count = len(scan_results.get("tests_performed", []))

            logger.info(f"✅ GraphQL scan completed: {tests_count} tests, {vuln_count} vulnerabilities")

            if vuln_count > 0:
                logger.warning(f"⚠️  Found {vuln_count} GraphQL vulnerabilities!")
                for vuln in scan_results.get("vulnerabilities", [])[:3]:  # Show first 3
                    severity = vuln.get("severity", "UNKNOWN")
                    vuln_type = vuln.get("type", "unknown")
                    logger.warning(f"   ├─ [{severity}] {vuln_type}")
        else:
            logger.error("❌ GraphQL scanning failed")

        return result

    @mcp.tool()
    def jwt_analyzer(jwt_token: str, target_url: str = "") -> Dict[str, Any]:
        """
        Advanced JWT token analysis and vulnerability testing.

        Args:
            jwt_token: JWT token to analyze
            target_url: Optional target URL for testing token manipulation

        Returns:
            JWT analysis results with vulnerability assessment and attack vectors
        """
        data = {
            "jwt_token": jwt_token,
            "target_url": target_url
        }

        logger.info(f"🔍 Starting JWT security analysis")
        result = hexstrike_client.safe_post("api/tools/jwt_analyzer", data)

        if result.get("success"):
            analysis = result.get("jwt_analysis_results", {})
            vuln_count = len(analysis.get("vulnerabilities", []))
            algorithm = analysis.get("token_info", {}).get("algorithm", "unknown")

            logger.info(f"✅ JWT analysis completed: {vuln_count} vulnerabilities found")
            logger.info(f"🔐 Token algorithm: {algorithm}")

            if vuln_count > 0:
                logger.warning(f"⚠️  Found {vuln_count} JWT vulnerabilities!")
                for vuln in analysis.get("vulnerabilities", [])[:3]:  # Show first 3
                    severity = vuln.get("severity", "UNKNOWN")
                    vuln_type = vuln.get("type", "unknown")
                    logger.warning(f"   ├─ [{severity}] {vuln_type}")
        else:
            logger.error("❌ JWT analysis failed")

        return result

    @mcp.tool()
    def api_schema_analyzer(schema_url: str, schema_type: str = "openapi") -> Dict[str, Any]:
        """
        Analyze API schemas and identify potential security issues.

        Args:
            schema_url: URL to the API schema (OpenAPI/Swagger/GraphQL)
            schema_type: Type of schema (openapi, swagger, graphql)

        Returns:
            Schema analysis results with security issues and recommendations
        """
        data = {
            "schema_url": schema_url,
            "schema_type": schema_type
        }

        logger.info(f"🔍 Starting API schema analysis: {schema_url}")
        result = hexstrike_client.safe_post("api/tools/api_schema_analyzer", data)

        if result.get("success"):
            analysis = result.get("schema_analysis_results", {})
            endpoint_count = len(analysis.get("endpoints_found", []))
            issue_count = len(analysis.get("security_issues", []))

            logger.info(f"✅ Schema analysis completed: {endpoint_count} endpoints, {issue_count} issues")

            if issue_count > 0:
                logger.warning(f"⚠️  Found {issue_count} security issues in schema!")
                for issue in analysis.get("security_issues", [])[:3]:  # Show first 3
                    severity = issue.get("severity", "UNKNOWN")
                    issue_type = issue.get("issue", "unknown")
                    logger.warning(f"   ├─ [{severity}] {issue_type}")

            if endpoint_count > 0:
                logger.info(f"📊 Discovered endpoints:")
                for endpoint in analysis.get("endpoints_found", [])[:5]:  # Show first 5
                    method = endpoint.get("method", "GET")
                    path = endpoint.get("path", "/")
                    logger.info(f"   ├─ {method} {path}")
        else:
            logger.error("❌ Schema analysis failed")

        return result

    @mcp.tool()
    def comprehensive_api_audit(base_url: str, schema_url: str = "", jwt_token: str = "", graphql_endpoint: str = "") -> Dict[str, Any]:
        """
        Comprehensive API security audit combining multiple testing techniques.

        Args:
            base_url: Base URL of the API
            schema_url: Optional API schema URL
            jwt_token: Optional JWT token for analysis
            graphql_endpoint: Optional GraphQL endpoint

        Returns:
            Comprehensive audit results with all API security tests
        """
        audit_results = {
            "base_url": base_url,
            "audit_timestamp": time.time(),
            "tests_performed": [],
            "total_vulnerabilities": 0,
            "summary": {},
            "recommendations": []
        }

        logger.info(f"🚀 Starting comprehensive API security audit: {base_url}")

        # 1. API Endpoint Fuzzing
        logger.info("🔍 Phase 1: API endpoint discovery and fuzzing")
        fuzz_result = self.api_fuzzer(base_url)
        if fuzz_result.get("success"):
            audit_results["tests_performed"].append("api_fuzzing")
            audit_results["api_fuzzing"] = fuzz_result

        # 2. Schema Analysis (if provided)
        if schema_url:
            logger.info("🔍 Phase 2: API schema analysis")
            schema_result = self.api_schema_analyzer(schema_url)
            if schema_result.get("success"):
                audit_results["tests_performed"].append("schema_analysis")
                audit_results["schema_analysis"] = schema_result

                schema_data = schema_result.get("schema_analysis_results", {})
                audit_results["total_vulnerabilities"] += len(schema_data.get("security_issues", []))

        # 3. JWT Analysis (if provided)
        if jwt_token:
            logger.info("🔍 Phase 3: JWT token analysis")
            jwt_result = self.jwt_analyzer(jwt_token, base_url)
            if jwt_result.get("success"):
                audit_results["tests_performed"].append("jwt_analysis")
                audit_results["jwt_analysis"] = jwt_result

                jwt_data = jwt_result.get("jwt_analysis_results", {})
                audit_results["total_vulnerabilities"] += len(jwt_data.get("vulnerabilities", []))

        # 4. GraphQL Testing (if provided)
        if graphql_endpoint:
            logger.info("🔍 Phase 4: GraphQL security scanning")
            graphql_result = self.graphql_scanner(graphql_endpoint)
            if graphql_result.get("success"):
                audit_results["tests_performed"].append("graphql_scanning")
                audit_results["graphql_scanning"] = graphql_result

                graphql_data = graphql_result.get("graphql_scan_results", {})
                audit_results["total_vulnerabilities"] += len(graphql_data.get("vulnerabilities", []))

        # Generate comprehensive recommendations
        audit_results["recommendations"] = [
            "Implement proper authentication and authorization",
            "Use HTTPS for all API communications",
            "Validate and sanitize all input parameters",
            "Implement rate limiting and request throttling",
            "Add comprehensive logging and monitoring",
            "Regular security testing and code reviews",
            "Keep API documentation updated and secure",
            "Implement proper error handling"
        ]

        # Summary
        audit_results["summary"] = {
            "tests_performed": len(audit_results["tests_performed"]),
            "total_vulnerabilities": audit_results["total_vulnerabilities"],
            "audit_coverage": "comprehensive" if len(audit_results["tests_performed"]) >= 3 else "partial"
        }

        logger.info(f"✅ Comprehensive API audit completed:")
        logger.info(f"   ├─ Tests performed: {audit_results['summary']['tests_performed']}")
        logger.info(f"   ├─ Total vulnerabilities: {audit_results['summary']['total_vulnerabilities']}")
        logger.info(f"   └─ Coverage: {audit_results['summary']['audit_coverage']}")

        return {
            "success": True,
            "comprehensive_audit": audit_results
        }

    # ============================================================================
    # ADVANCED CTF TOOLS (v5.0 ENHANCEMENT)
    # ============================================================================

    @mcp.tool()
    def volatility3_analyze(memory_file: str, plugin: str, output_file: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Volatility3 for advanced memory forensics with enhanced logging.

        Args:
            memory_file: Path to memory dump file
            plugin: Volatility3 plugin to execute
            output_file: Output file path
            additional_args: Additional Volatility3 arguments

        Returns:
            Advanced memory forensics results
        """
        data = {
            "memory_file": memory_file,
            "plugin": plugin,
            "output_file": output_file,
            "additional_args": additional_args
        }
        logger.info(f"🧠 Starting Volatility3 analysis: {plugin}")
        result = hexstrike_client.safe_post("api/tools/volatility3", data)
        if result.get("success"):
            logger.info(f"✅ Volatility3 analysis completed")
        else:
            logger.error(f"❌ Volatility3 analysis failed")
        return result

    @mcp.tool()
    def foremost_carving(input_file: str, output_dir: str = "/tmp/foremost_output", file_types: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Foremost for file carving with enhanced logging.

        Args:
            input_file: Input file or device to carve
            output_dir: Output directory for carved files
            file_types: File types to carve (jpg,gif,png,etc.)
            additional_args: Additional Foremost arguments

        Returns:
            File carving results
        """
        data = {
            "input_file": input_file,
            "output_dir": output_dir,
            "file_types": file_types,
            "additional_args": additional_args
        }
        logger.info(f"📁 Starting Foremost file carving: {input_file}")
        result = hexstrike_client.safe_post("api/tools/foremost", data)
        if result.get("success"):
            logger.info(f"✅ Foremost carving completed")
        else:
            logger.error(f"❌ Foremost carving failed")
        return result

    @mcp.tool()
    def steghide_analysis(action: str, cover_file: str, embed_file: str = "", passphrase: str = "", output_file: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Steghide for steganography analysis with enhanced logging.

        Args:
            action: Action to perform (extract, embed, info)
            cover_file: Cover file for steganography
            embed_file: File to embed (for embed action)
            passphrase: Passphrase for steganography
            output_file: Output file path
            additional_args: Additional Steghide arguments

        Returns:
            Steganography analysis results
        """
        data = {
            "action": action,
            "cover_file": cover_file,
            "embed_file": embed_file,
            "passphrase": passphrase,
            "output_file": output_file,
            "additional_args": additional_args
        }
        logger.info(f"🖼️ Starting Steghide {action}: {cover_file}")
        result = hexstrike_client.safe_post("api/tools/steghide", data)
        if result.get("success"):
            logger.info(f"✅ Steghide {action} completed")
        else:
            logger.error(f"❌ Steghide {action} failed")
        return result

    @mcp.tool()
    def exiftool_extract(file_path: str, output_format: str = "", tags: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute ExifTool for metadata extraction with enhanced logging.

        Args:
            file_path: Path to file for metadata extraction
            output_format: Output format (json, xml, csv)
            tags: Specific tags to extract
            additional_args: Additional ExifTool arguments

        Returns:
            Metadata extraction results
        """
        data = {
            "file_path": file_path,
            "output_format": output_format,
            "tags": tags,
            "additional_args": additional_args
        }
        logger.info(f"📷 Starting ExifTool analysis: {file_path}")
        result = hexstrike_client.safe_post("api/tools/exiftool", data)
        if result.get("success"):
            logger.info(f"✅ ExifTool analysis completed")
        else:
            logger.error(f"❌ ExifTool analysis failed")
        return result

    @mcp.tool()
    def hashpump_attack(signature: str, data: str, key_length: str, append_data: str, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute HashPump for hash length extension attacks with enhanced logging.

        Args:
            signature: Original hash signature
            data: Original data
            key_length: Length of secret key
            append_data: Data to append
            additional_args: Additional HashPump arguments

        Returns:
            Hash length extension attack results
        """
        data = {
            "signature": signature,
            "data": data,
            "key_length": key_length,
            "append_data": append_data,
            "additional_args": additional_args
        }
        logger.info(f"🔐 Starting HashPump attack")
        result = hexstrike_client.safe_post("api/tools/hashpump", data)
        if result.get("success"):
            logger.info(f"✅ HashPump attack completed")
        else:
            logger.error(f"❌ HashPump attack failed")
        return result

    # ============================================================================
    # BUG BOUNTY RECONNAISSANCE TOOLS (v5.0 ENHANCEMENT)
    # ============================================================================

    @mcp.tool()
    def hakrawler_crawl(url: str, depth: int = 2, forms: bool = True, robots: bool = True, sitemap: bool = True, wayback: bool = False, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Hakrawler for web endpoint discovery with enhanced logging.

        Note: Uses standard Kali Linux hakrawler (hakluke/hakrawler) with parameter mapping:
        - url: Piped via echo to stdin (not -url flag)
        - depth: Mapped to -d flag (not -depth)
        - forms: Mapped to -s flag for showing sources
        - robots/sitemap/wayback: Mapped to -subs for subdomain inclusion
        - Always includes -u for unique URLs

        Args:
            url: Target URL to crawl
            depth: Crawling depth (mapped to -d)
            forms: Include forms in crawling (mapped to -s)
            robots: Check robots.txt (mapped to -subs)
            sitemap: Check sitemap.xml (mapped to -subs)
            wayback: Use Wayback Machine (mapped to -subs)
            additional_args: Additional Hakrawler arguments

        Returns:
            Web endpoint discovery results
        """
        data = {
            "url": url,
            "depth": depth,
            "forms": forms,
            "robots": robots,
            "sitemap": sitemap,
            "wayback": wayback,
            "additional_args": additional_args
        }
        logger.info(f"🕷️ Starting Hakrawler crawling: {url}")
        result = hexstrike_client.safe_post("api/tools/hakrawler", data)
        if result.get("success"):
            logger.info(f"✅ Hakrawler crawling completed")
        else:
            logger.error(f"❌ Hakrawler crawling failed")
        return result

    @mcp.tool()
    def httpx_probe(targets: str = "", target_file: str = "", ports: str = "", methods: str = "GET", status_code: str = "", content_length: bool = False, output_file: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute HTTPx for HTTP probing with enhanced logging.

        Args:
            targets: Target URLs or IPs
            target_file: File containing targets
            ports: Ports to probe
            methods: HTTP methods to use
            status_code: Filter by status code
            content_length: Show content length
            output_file: Output file path
            additional_args: Additional HTTPx arguments

        Returns:
            HTTP probing results
        """
        data = {
            "targets": targets,
            "target_file": target_file,
            "ports": ports,
            "methods": methods,
            "status_code": status_code,
            "content_length": content_length,
            "output_file": output_file,
            "additional_args": additional_args
        }
        logger.info(f"🌐 Starting HTTPx probing")
        result = hexstrike_client.safe_post("api/tools/httpx", data)
        if result.get("success"):
            logger.info(f"✅ HTTPx probing completed")
        else:
            logger.error(f"❌ HTTPx probing failed")
        return result

    @mcp.tool()
    def paramspider_discovery(domain: str, exclude: str = "", output_file: str = "", level: int = 2, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute ParamSpider for parameter discovery with enhanced logging.

        Args:
            domain: Target domain
            exclude: Extensions to exclude
            output_file: Output file path
            level: Crawling level
            additional_args: Additional ParamSpider arguments

        Returns:
            Parameter discovery results
        """
        data = {
            "domain": domain,
            "exclude": exclude,
            "output_file": output_file,
            "level": level,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting ParamSpider discovery: {domain}")
        result = hexstrike_client.safe_post("api/tools/paramspider", data)
        if result.get("success"):
            logger.info(f"✅ ParamSpider discovery completed")
        else:
            logger.error(f"❌ ParamSpider discovery failed")
        return result

    # ============================================================================
    # ADVANCED WEB SECURITY TOOLS CONTINUED
    # ============================================================================

    @mcp.tool()
    def burpsuite_scan(project_file: str = "", config_file: str = "", target: str = "", headless: bool = False, scan_type: str = "", scan_config: str = "", output_file: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Burp Suite with enhanced logging.

        Args:
            project_file: Burp project file path
            config_file: Burp configuration file path
            target: Target URL
            headless: Run in headless mode
            scan_type: Type of scan to perform
            scan_config: Scan configuration
            output_file: Output file path
            additional_args: Additional Burp Suite arguments

        Returns:
            Burp Suite scan results
        """
        data = {
            "project_file": project_file,
            "config_file": config_file,
            "target": target,
            "headless": headless,
            "scan_type": scan_type,
            "scan_config": scan_config,
            "output_file": output_file,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Burp Suite scan")
        result = hexstrike_client.safe_post("api/tools/burpsuite", data)
        if result.get("success"):
            logger.info(f"✅ Burp Suite scan completed")
        else:
            logger.error(f"❌ Burp Suite scan failed")
        return result

    @mcp.tool()
    def zap_scan(target: str = "", scan_type: str = "baseline", api_key: str = "", daemon: bool = False, port: str = "8090", host: str = "0.0.0.0", format_type: str = "xml", output_file: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute OWASP ZAP with enhanced logging.

        Args:
            target: Target URL
            scan_type: Type of scan (baseline, full, api)
            api_key: ZAP API key
            daemon: Run in daemon mode
            port: Port for ZAP daemon
            host: Host for ZAP daemon
            format_type: Output format (xml, json, html)
            output_file: Output file path
            additional_args: Additional ZAP arguments

        Returns:
            ZAP scan results
        """
        data = {
            "target": target,
            "scan_type": scan_type,
            "api_key": api_key,
            "daemon": daemon,
            "port": port,
            "host": host,
            "format": format_type,
            "output_file": output_file,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting ZAP scan: {target}")
        result = hexstrike_client.safe_post("api/tools/zap", data)
        if result.get("success"):
            logger.info(f"✅ ZAP scan completed for {target}")
        else:
            logger.error(f"❌ ZAP scan failed for {target}")
        return result

    @mcp.tool()
    def arjun_scan(url: str, method: str = "GET", data: str = "", headers: str = "", timeout: str = "", output_file: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute Arjun for parameter discovery with enhanced logging.

        Args:
            url: Target URL
            method: HTTP method (GET, POST, etc.)
            data: POST data for testing
            headers: Custom headers
            timeout: Request timeout
            output_file: Output file path
            additional_args: Additional Arjun arguments

        Returns:
            Parameter discovery results
        """
        data = {
            "url": url,
            "method": method,
            "data": data,
            "headers": headers,
            "timeout": timeout,
            "output_file": output_file,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Arjun parameter discovery: {url}")
        result = hexstrike_client.safe_post("api/tools/arjun", data)
        if result.get("success"):
            logger.info(f"✅ Arjun completed for {url}")
        else:
            logger.error(f"❌ Arjun failed for {url}")
        return result

    @mcp.tool()
    def wafw00f_scan(target: str, additional_args: str = "") -> Dict[str, Any]:
        """
        Execute wafw00f to identify and fingerprint WAF products with enhanced logging.

        Args:
            target: Target URL or IP
            additional_args: Additional wafw00f arguments

        Returns:
            WAF detection results
        """
        data = {
            "target": target,
            "additional_args": additional_args
        }
        logger.info(f"🛡️ Starting Wafw00f WAF detection: {target}")
        result = hexstrike_client.safe_post("api/tools/wafw00f", data)
        if result.get("success"):
            logger.info(f"✅ Wafw00f completed for {target}")
        else:
            logger.error(f"❌ Wafw00f failed for {target}")
        return result

    @mcp.tool()
    def fierce_scan(domain: str, dns_server: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute fierce for DNS reconnaissance with enhanced logging.

        Args:
            domain: Target domain
            dns_server: DNS server to use
            additional_args: Additional fierce arguments

        Returns:
            DNS reconnaissance results
        """
        data = {
            "domain": domain,
            "dns_server": dns_server,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting Fierce DNS recon: {domain}")
        result = hexstrike_client.safe_post("api/tools/fierce", data)
        if result.get("success"):
            logger.info(f"✅ Fierce completed for {domain}")
        else:
            logger.error(f"❌ Fierce failed for {domain}")
        return result

    @mcp.tool()
    def dnsenum_scan(domain: str, dns_server: str = "", wordlist: str = "", additional_args: str = "") -> Dict[str, Any]:
        """
        Execute dnsenum for DNS enumeration with enhanced logging.

        Args:
            domain: Target domain
            dns_server: DNS server to use
            wordlist: Wordlist for brute forcing
            additional_args: Additional dnsenum arguments

        Returns:
            DNS enumeration results
        """
        data = {
            "domain": domain,
            "dns_server": dns_server,
            "wordlist": wordlist,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting DNSenum: {domain}")
        result = hexstrike_client.safe_post("api/tools/dnsenum", data)
        if result.get("success"):
            logger.info(f"✅ DNSenum completed for {domain}")
        else:
            logger.error(f"❌ DNSenum failed for {domain}")
        return result

    @mcp.tool()
    def autorecon_scan(
        target: str = "",
        target_file: str = "",
        ports: str = "",
        output_dir: str = "",
        max_scans: str = "",
        max_port_scans: str = "",
        heartbeat: str = "",
        timeout: str = "",
        target_timeout: str = "",
        config_file: str = "",
        global_file: str = "",
        plugins_dir: str = "",
        add_plugins_dir: str = "",
        tags: str = "",
        exclude_tags: str = "",
        port_scans: str = "",
        service_scans: str = "",
        reports: str = "",
        single_target: bool = False,
        only_scans_dir: bool = False,
        no_port_dirs: bool = False,
        nmap: str = "",
        nmap_append: str = "",
        proxychains: bool = False,
        disable_sanity_checks: bool = False,
        disable_keyboard_control: bool = False,
        force_services: str = "",
        accessible: bool = False,
        verbose: int = 0,
        curl_path: str = "",
        dirbuster_tool: str = "",
        dirbuster_wordlist: str = "",
        dirbuster_threads: str = "",
        dirbuster_ext: str = "",
        onesixtyone_community_strings: str = "",
        global_username_wordlist: str = "",
        global_password_wordlist: str = "",
        global_domain: str = "",
        additional_args: str = ""
    ) -> Dict[str, Any]:
        """
        Execute AutoRecon for comprehensive target enumeration with full parameter support.

        Args:
            target: Single target to scan
            target_file: File containing multiple targets
            ports: Specific ports to scan
            output_dir: Output directory
            max_scans: Maximum number of concurrent scans
            max_port_scans: Maximum number of concurrent port scans
            heartbeat: Heartbeat interval
            timeout: Global timeout
            target_timeout: Per-target timeout
            config_file: Configuration file path
            global_file: Global configuration file
            plugins_dir: Plugins directory
            add_plugins_dir: Additional plugins directory
            tags: Plugin tags to include
            exclude_tags: Plugin tags to exclude
            port_scans: Port scan plugins to run
            service_scans: Service scan plugins to run
            reports: Report plugins to run
            single_target: Use single target directory structure
            only_scans_dir: Only create scans directory
            no_port_dirs: Don't create port directories
            nmap: Custom nmap command
            nmap_append: Arguments to append to nmap
            proxychains: Use proxychains
            disable_sanity_checks: Disable sanity checks
            disable_keyboard_control: Disable keyboard control
            force_services: Force service detection
            accessible: Enable accessible output
            verbose: Verbosity level (0-3)
            curl_path: Custom curl path
            dirbuster_tool: Directory busting tool
            dirbuster_wordlist: Directory busting wordlist
            dirbuster_threads: Directory busting threads
            dirbuster_ext: Directory busting extensions
            onesixtyone_community_strings: SNMP community strings
            global_username_wordlist: Global username wordlist
            global_password_wordlist: Global password wordlist
            global_domain: Global domain
            additional_args: Additional AutoRecon arguments

        Returns:
            Comprehensive enumeration results with full configurability
        """
        data = {
            "target": target,
            "target_file": target_file,
            "ports": ports,
            "output_dir": output_dir,
            "max_scans": max_scans,
            "max_port_scans": max_port_scans,
            "heartbeat": heartbeat,
            "timeout": timeout,
            "target_timeout": target_timeout,
            "config_file": config_file,
            "global_file": global_file,
            "plugins_dir": plugins_dir,
            "add_plugins_dir": add_plugins_dir,
            "tags": tags,
            "exclude_tags": exclude_tags,
            "port_scans": port_scans,
            "service_scans": service_scans,
            "reports": reports,
            "single_target": single_target,
            "only_scans_dir": only_scans_dir,
            "no_port_dirs": no_port_dirs,
            "nmap": nmap,
            "nmap_append": nmap_append,
            "proxychains": proxychains,
            "disable_sanity_checks": disable_sanity_checks,
            "disable_keyboard_control": disable_keyboard_control,
            "force_services": force_services,
            "accessible": accessible,
            "verbose": verbose,
            "curl_path": curl_path,
            "dirbuster_tool": dirbuster_tool,
            "dirbuster_wordlist": dirbuster_wordlist,
            "dirbuster_threads": dirbuster_threads,
            "dirbuster_ext": dirbuster_ext,
            "onesixtyone_community_strings": onesixtyone_community_strings,
            "global_username_wordlist": global_username_wordlist,
            "global_password_wordlist": global_password_wordlist,
            "global_domain": global_domain,
            "additional_args": additional_args
        }
        logger.info(f"🔍 Starting AutoRecon comprehensive enumeration: {target}")
        result = hexstrike_client.safe_post("api/tools/autorecon", data)
        if result.get("success"):
            logger.info(f"✅ AutoRecon comprehensive enumeration completed for {target}")
        else:
            logger.error(f"❌ AutoRecon failed for {target}")
        return result

    # ============================================================================
    # SYSTEM MONITORING & TELEMETRY
    # ============================================================================

    @mcp.tool()
    def server_health() -> Dict[str, Any]:
        """
        Check the health status of the HexStrike AI server.

        Returns:
            Server health information with tool availability and telemetry
        """
        logger.info(f"🏥 Checking HexStrike AI server health")
        result = hexstrike_client.check_health()
        if result.get("status") == "healthy":
            logger.info(f"✅ Server is healthy - {result.get('total_tools_available', 0)} tools available")
        else:
            logger.warning(f"⚠️  Server health check returned: {result.get('status', 'unknown')}")
        return result

    @mcp.tool()
    def get_cache_stats() -> Dict[str, Any]:
        """
        Get cache statistics from the HexStrike AI server.

        Returns:
            Cache performance statistics
        """
        logger.info(f"💾 Getting cache statistics")
        result = hexstrike_client.safe_get("api/cache/stats")
        if "hit_rate" in result:
            logger.info(f"📊 Cache hit rate: {result.get('hit_rate', 'unknown')}")
        return result

    @mcp.tool()
    def clear_cache() -> Dict[str, Any]:
        """
        Clear the cache on the HexStrike AI server.

        Returns:
            Cache clear operation results
        """
        logger.info(f"🧹 Clearing server cache")
        result = hexstrike_client.safe_post("api/cache/clear", {})
        if result.get("success"):
            logger.info(f"✅ Cache cleared successfully")
        else:
            logger.error(f"❌ Failed to clear cache")
        return result

    @mcp.tool()
    def get_telemetry() -> Dict[str, Any]:
        """
        Get system telemetry from the HexStrike AI server.

        Returns:
            System performance and usage telemetry
        """
        logger.info(f"📈 Getting system telemetry")
        result = hexstrike_client.safe_get("api/telemetry")
        if "commands_executed" in result:
            logger.info(f"📊 Commands executed: {result.get('commands_executed', 0)}")
        return result

    # ============================================================================
    # PROCESS MANAGEMENT TOOLS (v5.0 ENHANCEMENT)
    # ============================================================================

    @mcp.tool()
    def list_active_processes() -> Dict[str, Any]:
        """
        List all active processes on the HexStrike AI server.

        Returns:
            List of active processes with their status and progress
        """
        logger.info("📊 Listing active processes")
        result = hexstrike_client.safe_get("api/processes/list")
        if result.get("success"):
            logger.info(f"✅ Found {result.get('total_count', 0)} active processes")
        else:
            logger.error("❌ Failed to list processes")
        return result

    @mcp.tool()
    def get_process_status(pid: int) -> Dict[str, Any]:
        """
        Get the status of a specific process.

        Args:
            pid: Process ID to check

        Returns:
            Process status information including progress and runtime
        """
        logger.info(f"🔍 Checking status of process {pid}")
        result = hexstrike_client.safe_get(f"api/processes/status/{pid}")
        if result.get("success"):
            logger.info(f"✅ Process {pid} status retrieved")
        else:
            logger.error(f"❌ Process {pid} not found or error occurred")
        return result

    @mcp.tool()
    def terminate_process(pid: int) -> Dict[str, Any]:
        """
        Terminate a specific running process.

        Args:
            pid: Process ID to terminate

        Returns:
            Success status of the termination operation
        """
        logger.info(f"🛑 Terminating process {pid}")
        result = hexstrike_client.safe_post(f"api/processes/terminate/{pid}", {})
        if result.get("success"):
            logger.info(f"✅ Process {pid} terminated successfully")
        else:
            logger.error(f"❌ Failed to terminate process {pid}")
        return result

    @mcp.tool()
    def pause_process(pid: int) -> Dict[str, Any]:
        """
        Pause a specific running process.

        Args:
            pid: Process ID to pause

        Returns:
            Success status of the pause operation
        """
        logger.info(f"⏸️ Pausing process {pid}")
        result = hexstrike_client.safe_post(f"api/processes/pause/{pid}", {})
        if result.get("success"):
            logger.info(f"✅ Process {pid} paused successfully")
        else:
            logger.error(f"❌ Failed to pause process {pid}")
        return result

    @mcp.tool()
    def resume_process(pid: int) -> Dict[str, Any]:
        """
        Resume a paused process.

        Args:
            pid: Process ID to resume

        Returns:
            Success status of the resume operation
        """
        logger.info(f"▶️ Resuming process {pid}")
        result = hexstrike_client.safe_post(f"api/processes/resume/{pid}", {})
        if result.get("success"):
            logger.info(f"✅ Process {pid} resumed successfully")
        else:
            logger.error(f"❌ Failed to resume process {pid}")
        return result

    @mcp.tool()
    def get_process_dashboard() -> Dict[str, Any]:
        """
        Get enhanced process dashboard with visual status indicators.

        Returns:
            Real-time dashboard with progress bars, system metrics, and process status
        """
        logger.info("📊 Getting process dashboard")
        result = hexstrike_client.safe_get("api/processes/dashboard")
        if result.get("success", True) and "total_processes" in result:
            total = result.get("total_processes", 0)
            logger.info(f"✅ Dashboard retrieved: {total} active processes")

            # Log visual summary for better UX
            if total > 0:
                logger.info("📈 Active Processes Summary:")
                for proc in result.get("processes", [])[:3]:  # Show first 3
                    logger.info(f"   ├─ PID {proc['pid']}: {proc['progress_bar']} {proc['progress_percent']}")
        else:
            logger.error("❌ Failed to get process dashboard")
        return result

    @mcp.tool()
    def execute_command(command: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Execute an arbitrary command on the HexStrike AI server with enhanced logging.

        Args:
            command: The command to execute
            use_cache: Whether to use caching for this command

        Returns:
            Command execution results with enhanced telemetry
        """
        try:
            logger.info(f"⚡ Executing command: {command}")
            result = hexstrike_client.execute_command(command, use_cache)
            if "error" in result:
                logger.error(f"❌ Command failed: {result['error']}")
                return {
                    "success": False,
                    "error": result["error"],
                    "stdout": "",
                    "stderr": f"Error executing command: {result['error']}"
                }

            if result.get("success"):
                execution_time = result.get("execution_time", 0)
                logger.info(f"✅ Command completed successfully in {execution_time:.2f}s")
            else:
                logger.warning(f"⚠️  Command completed with errors")

            return result
        except Exception as e:
            logger.error(f"💥 Error executing command '{command}': {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": f"Error executing command: {str(e)}"
            }

    # ============================================================================
    # ADVANCED VULNERABILITY INTELLIGENCE MCP TOOLS (v6.0 ENHANCEMENT)
    # ============================================================================

    @mcp.tool()
    def monitor_cve_feeds(hours: int = 24, severity_filter: str = "HIGH,CRITICAL", keywords: str = "") -> Dict[str, Any]:
        """
        Monitor CVE databases for new vulnerabilities with AI analysis.

        Args:
            hours: Hours to look back for new CVEs (default: 24)
            severity_filter: Filter by CVSS severity - comma-separated values (LOW,MEDIUM,HIGH,CRITICAL,ALL)
            keywords: Filter CVEs by keywords in description (comma-separated)

        Returns:
            Latest CVEs with exploitability analysis and threat intelligence

        Example:
            monitor_cve_feeds(48, "CRITICAL", "remote code execution")
        """
        data = {
            "hours": hours,
            "severity_filter": severity_filter,
            "keywords": keywords
        }
        logger.info(f"🔍 Monitoring CVE feeds for last {hours} hours | Severity: {severity_filter}")
        result = hexstrike_client.safe_post("api/vuln-intel/cve-monitor", data)

        if result.get("success"):
            cve_count = len(result.get("cve_monitoring", {}).get("cves", []))
            exploit_analysis_count = len(result.get("exploitability_analysis", []))
            logger.info(f"✅ Found {cve_count} CVEs with {exploit_analysis_count} exploitability analyses")

        return result

    @mcp.tool()
    def generate_exploit_from_cve(cve_id: str, target_os: str = "", target_arch: str = "x64", exploit_type: str = "poc", evasion_level: str = "none") -> Dict[str, Any]:
        """
        Generate working exploits from CVE information using AI-powered analysis.

        Args:
            cve_id: CVE identifier (e.g., CVE-2024-1234)
            target_os: Target operating system (windows, linux, macos, any)
            target_arch: Target architecture (x86, x64, arm, any)
            exploit_type: Type of exploit to generate (poc, weaponized, stealth)
            evasion_level: Evasion sophistication (none, basic, advanced)

        Returns:
            Generated exploit code with testing instructions and evasion techniques

        Example:
            generate_exploit_from_cve("CVE-2024-1234", "linux", "x64", "weaponized", "advanced")
        """
        data = {
            "cve_id": cve_id,
            "target_os": target_os,
            "target_arch": target_arch,
            "exploit_type": exploit_type,
            "evasion_level": evasion_level
        }
        logger.info(f"🤖 Generating {exploit_type} exploit for {cve_id} | Target: {target_os} {target_arch}")
        result = hexstrike_client.safe_post("api/vuln-intel/exploit-generate", data)

        if result.get("success"):
            cve_analysis = result.get("cve_analysis", {})
            exploit_gen = result.get("exploit_generation", {})
            exploitability = cve_analysis.get("exploitability_level", "UNKNOWN")
            exploit_success = exploit_gen.get("success", False)

            logger.info(f"📊 CVE Analysis: {exploitability} exploitability")
            logger.info(f"🎯 Exploit Generation: {'SUCCESS' if exploit_success else 'FAILED'}")

        return result

    @mcp.tool()
    def discover_attack_chains(target_software: str, attack_depth: int = 3, include_zero_days: bool = False) -> Dict[str, Any]:
        """
        Discover multi-stage attack chains for target software with vulnerability correlation.

        Args:
            target_software: Target software/system (e.g., "Apache HTTP Server", "Windows Server 2019")
            attack_depth: Maximum number of stages in attack chain (1-5)
            include_zero_days: Include potential zero-day vulnerabilities in analysis

        Returns:
            Attack chains with vulnerability combinations, success probabilities, and exploit availability

        Example:
            discover_attack_chains("Apache HTTP Server 2.4", 4, True)
        """
        data = {
            "target_software": target_software,
            "attack_depth": min(max(attack_depth, 1), 5),  # Clamp between 1-5
            "include_zero_days": include_zero_days
        }
        logger.info(f"🔗 Discovering attack chains for {target_software} | Depth: {attack_depth} | Zero-days: {include_zero_days}")
        result = hexstrike_client.safe_post("api/vuln-intel/attack-chains", data)

        if result.get("success"):
            chains = result.get("attack_chain_discovery", {}).get("attack_chains", [])
            enhanced_chains = result.get("attack_chain_discovery", {}).get("enhanced_chains", [])

            logger.info(f"📊 Found {len(chains)} attack chains")
            if enhanced_chains:
                logger.info(f"🎯 Enhanced {len(enhanced_chains)} chains with exploit analysis")

        return result

    @mcp.tool()
    def research_zero_day_opportunities(target_software: str, analysis_depth: str = "standard", source_code_url: str = "") -> Dict[str, Any]:
        """
        Automated zero-day vulnerability research using AI analysis and pattern recognition.

        Args:
            target_software: Software to research for vulnerabilities (e.g., "nginx", "OpenSSL")
            analysis_depth: Depth of analysis (quick, standard, comprehensive)
            source_code_url: URL to source code repository for enhanced analysis

        Returns:
            Potential vulnerability areas with exploitation feasibility and research recommendations

        Example:
            research_zero_day_opportunities("nginx 1.20", "comprehensive", "https://github.com/nginx/nginx")
        """
        if analysis_depth not in ["quick", "standard", "comprehensive"]:
            analysis_depth = "standard"

        data = {
            "target_software": target_software,
            "analysis_depth": analysis_depth,
            "source_code_url": source_code_url
        }
        logger.info(f"🔬 Researching zero-day opportunities in {target_software} | Depth: {analysis_depth}")
        result = hexstrike_client.safe_post("api/vuln-intel/zero-day-research", data)

        if result.get("success"):
            research = result.get("zero_day_research", {})
            potential_vulns = len(research.get("potential_vulnerabilities", []))
            risk_score = research.get("risk_assessment", {}).get("risk_score", 0)

            logger.info(f"📊 Found {potential_vulns} potential vulnerability areas")
            logger.info(f"🎯 Risk Score: {risk_score}/100")

        return result

    @mcp.tool()
    def correlate_threat_intelligence(indicators: str, timeframe: str = "30d", sources: str = "all") -> Dict[str, Any]:
        """
        Correlate threat intelligence across multiple sources with advanced analysis.

        Args:
            indicators: Comma-separated IOCs (IPs, domains, hashes, CVEs, etc.)
            timeframe: Time window for correlation (7d, 30d, 90d, 1y)
            sources: Intelligence sources to query (cve, exploit-db, github, twitter, all)

        Returns:
            Correlated threat intelligence with attribution, timeline, and threat scoring

        Example:
            correlate_threat_intelligence("CVE-2024-1234,192.168.1.100,malware.exe", "90d", "all")
        """
        # Validate timeframe
        valid_timeframes = ["7d", "30d", "90d", "1y"]
        if timeframe not in valid_timeframes:
            timeframe = "30d"

        # Parse indicators
        indicator_list = [i.strip() for i in indicators.split(",") if i.strip()]

        if not indicator_list:
            logger.error("❌ No valid indicators provided")
            return {"success": False, "error": "No valid indicators provided"}

        data = {
            "indicators": indicator_list,
            "timeframe": timeframe,
            "sources": sources
        }
        logger.info(f"🧠 Correlating threat intelligence for {len(indicator_list)} indicators | Timeframe: {timeframe}")
        result = hexstrike_client.safe_post("api/vuln-intel/threat-feeds", data)

        if result.get("success"):
            threat_intel = result.get("threat_intelligence", {})
            correlations = len(threat_intel.get("correlations", []))
            threat_score = threat_intel.get("threat_score", 0)

            logger.info(f"📊 Found {correlations} threat correlations")
            logger.info(f"🎯 Overall Threat Score: {threat_score:.1f}/100")

        return result

    @mcp.tool()
    def advanced_payload_generation(attack_type: str, target_context: str = "", evasion_level: str = "standard", custom_constraints: str = "") -> Dict[str, Any]:
        """
        Generate advanced payloads with AI-powered evasion techniques and contextual adaptation.

        Args:
            attack_type: Type of attack (rce, privilege_escalation, persistence, exfiltration, xss, sqli)
            target_context: Target environment details (OS, software versions, security controls)
            evasion_level: Evasion sophistication (basic, standard, advanced, nation-state)
            custom_constraints: Custom payload constraints (size limits, character restrictions, etc.)

        Returns:
            Advanced payloads with multiple evasion techniques and deployment instructions

        Example:
            advanced_payload_generation("rce", "Windows 11 + Defender + AppLocker", "nation-state", "max_size:256,no_quotes")
        """
        valid_attack_types = ["rce", "privilege_escalation", "persistence", "exfiltration", "xss", "sqli", "lfi", "ssrf"]
        valid_evasion_levels = ["basic", "standard", "advanced", "nation-state"]

        if attack_type not in valid_attack_types:
            attack_type = "rce"

        if evasion_level not in valid_evasion_levels:
            evasion_level = "standard"

        data = {
            "attack_type": attack_type,
            "target_context": target_context,
            "evasion_level": evasion_level,
            "custom_constraints": custom_constraints
        }
        logger.info(f"🎯 Generating advanced {attack_type} payload | Evasion: {evasion_level}")
        if target_context:
            logger.info(f"🎯 Target Context: {target_context}")

        result = hexstrike_client.safe_post("api/ai/advanced-payload-generation", data)

        if result.get("success"):
            payload_gen = result.get("advanced_payload_generation", {})
            payload_count = payload_gen.get("payload_count", 0)
            evasion_applied = payload_gen.get("evasion_level", "none")

            logger.info(f"📊 Generated {payload_count} advanced payloads")
            logger.info(f"🛡️ Evasion Level Applied: {evasion_applied}")

        return result

    @mcp.tool()
    def vulnerability_intelligence_dashboard() -> Dict[str, Any]:
        """
        Get a comprehensive vulnerability intelligence dashboard with latest threats and trends.

        Returns:
            Dashboard with latest CVEs, trending vulnerabilities, exploit availability, and threat landscape

        Example:
            vulnerability_intelligence_dashboard()
        """
        logger.info("📊 Generating vulnerability intelligence dashboard")

        # Get latest critical CVEs
        latest_cves = hexstrike_client.safe_post("api/vuln-intel/cve-monitor", {
            "hours": 24,
            "severity_filter": "CRITICAL",
            "keywords": ""
        })

        # Get trending attack types
        trending_research = hexstrike_client.safe_post("api/vuln-intel/zero-day-research", {
            "target_software": "web applications",
            "analysis_depth": "quick"
        })

        # Compile dashboard
        dashboard = {
            "timestamp": time.time(),
            "latest_critical_cves": latest_cves.get("cve_monitoring", {}).get("cves", [])[:5],
            "threat_landscape": {
                "high_risk_software": ["Apache HTTP Server", "Microsoft Exchange", "VMware vCenter", "Fortinet FortiOS"],
                "trending_attack_vectors": ["Supply chain attacks", "Cloud misconfigurations", "Zero-day exploits", "AI-powered attacks"],
                "active_threat_groups": ["APT29", "Lazarus Group", "FIN7", "REvil"],
            },
            "exploit_intelligence": {
                "new_public_exploits": "Simulated data - check exploit-db for real data",
                "weaponized_exploits": "Monitor threat intelligence feeds",
                "exploit_kits": "Track underground markets"
            },
            "recommendations": [
                "Prioritize patching for critical CVEs discovered in last 24h",
                "Monitor for zero-day activity in trending attack vectors",
                "Implement advanced threat detection for active threat groups",
                "Review security controls against nation-state level attacks"
            ]
        }

        logger.info("✅ Vulnerability intelligence dashboard generated")
        return {
            "success": True,
            "dashboard": dashboard
        }

    @mcp.tool()
    def threat_hunting_assistant(target_environment: str, threat_indicators: str = "", hunt_focus: str = "general") -> Dict[str, Any]:
        """
        AI-powered threat hunting assistant with vulnerability correlation and attack simulation.

        Args:
            target_environment: Environment to hunt in (e.g., "Windows Domain", "Cloud Infrastructure")
            threat_indicators: Known IOCs or suspicious indicators to investigate
            hunt_focus: Focus area (general, apt, ransomware, insider_threat, supply_chain)

        Returns:
            Threat hunting playbook with detection queries, IOCs, and investigation steps

        Example:
            threat_hunting_assistant("Windows Domain", "suspicious_process.exe,192.168.1.100", "apt")
        """
        valid_hunt_focus = ["general", "apt", "ransomware", "insider_threat", "supply_chain"]
        if hunt_focus not in valid_hunt_focus:
            hunt_focus = "general"

        logger.info(f"🔍 Generating threat hunting playbook for {target_environment} | Focus: {hunt_focus}")

        # Parse indicators if provided
        indicators = [i.strip() for i in threat_indicators.split(",") if i.strip()] if threat_indicators else []

        # Generate hunting playbook
        hunting_playbook = {
            "target_environment": target_environment,
            "hunt_focus": hunt_focus,
            "indicators_analyzed": indicators,
            "detection_queries": [],
            "investigation_steps": [],
            "threat_scenarios": [],
            "mitigation_strategies": []
        }

        # Environment-specific detection queries
        if "windows" in target_environment.lower():
            hunting_playbook["detection_queries"] = [
                "Get-WinEvent | Where-Object {$_.Id -eq 4688 -and $_.Message -like '*suspicious*'}",
                "Get-Process | Where-Object {$_.ProcessName -notin @('explorer.exe', 'svchost.exe')}",
                "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                "Get-NetTCPConnection | Where-Object {$_.State -eq 'Established' -and $_.RemoteAddress -notlike '10.*'}"
            ]
        elif "cloud" in target_environment.lower():
            hunting_playbook["detection_queries"] = [
                "CloudTrail logs for unusual API calls",
                "Failed authentication attempts from unknown IPs",
                "Privilege escalation events",
                "Data exfiltration indicators"
            ]

        # Focus-specific threat scenarios
        focus_scenarios = {
            "apt": [
                "Spear phishing with weaponized documents",
                "Living-off-the-land techniques",
                "Lateral movement via stolen credentials",
                "Data staging and exfiltration"
            ],
            "ransomware": [
                "Initial access via RDP/VPN",
                "Privilege escalation and persistence",
                "Shadow copy deletion",
                "Encryption and ransom note deployment"
            ],
            "insider_threat": [
                "Unusual data access patterns",
                "After-hours activity",
                "Large data downloads",
                "Access to sensitive systems"
            ]
        }

        hunting_playbook["threat_scenarios"] = focus_scenarios.get(hunt_focus, [
            "Unauthorized access attempts",
            "Suspicious process execution",
            "Network anomalies",
            "Data access violations"
        ])

        # Investigation steps
        hunting_playbook["investigation_steps"] = [
            "1. Validate initial indicators and expand IOC list",
            "2. Run detection queries and analyze results",
            "3. Correlate events across multiple data sources",
            "4. Identify affected systems and user accounts",
            "5. Assess scope and impact of potential compromise",
            "6. Implement containment measures if threat confirmed",
            "7. Document findings and update detection rules"
        ]

        # Correlate with vulnerability intelligence if indicators provided
        if indicators:
            logger.info(f"🧠 Correlating {len(indicators)} indicators with threat intelligence")
            correlation_result = correlate_threat_intelligence(",".join(indicators), "30d", "all")

            if correlation_result.get("success"):
                hunting_playbook["threat_correlation"] = correlation_result.get("threat_intelligence", {})

        logger.info("✅ Threat hunting playbook generated")
        return {
            "success": True,
            "hunting_playbook": hunting_playbook
        }

    # ============================================================================
    # ENHANCED VISUAL OUTPUT TOOLS
    # ============================================================================

    @mcp.tool()
    def get_live_dashboard() -> Dict[str, Any]:
        """
        Get a beautiful live dashboard showing all active processes with enhanced visual formatting.

        Returns:
            Live dashboard with visual process monitoring and system metrics
        """
        logger.info("📊 Fetching live process dashboard")
        result = hexstrike_client.safe_get("api/processes/dashboard")
        if result.get("success", True):
            logger.info("✅ Live dashboard retrieved successfully")
        else:
            logger.error("❌ Failed to retrieve live dashboard")
        return result

    @mcp.tool()
    def create_vulnerability_report(vulnerabilities: str, target: str = "", scan_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Create a beautiful vulnerability report with severity-based styling and visual indicators.

        Args:
            vulnerabilities: JSON string containing vulnerability data
            target: Target that was scanned
            scan_type: Type of scan performed

        Returns:
            Formatted vulnerability report with visual enhancements
        """
        import json

        try:
            # Parse vulnerabilities if provided as JSON string
            if isinstance(vulnerabilities, str):
                vuln_data = json.loads(vulnerabilities)
            else:
                vuln_data = vulnerabilities

            logger.info(f"📋 Creating vulnerability report for {len(vuln_data)} findings")

            # Create individual vulnerability cards
            vulnerability_cards = []
            for vuln in vuln_data:
                card_result = hexstrike_client.safe_post("api/visual/vulnerability-card", vuln)
                if card_result.get("success"):
                    vulnerability_cards.append(card_result.get("vulnerability_card", ""))

            # Create summary report
            summary_data = {
                "target": target,
                "vulnerabilities": vuln_data,
                "tools_used": [scan_type],
                "execution_time": 0
            }

            summary_result = hexstrike_client.safe_post("api/visual/summary-report", summary_data)

            logger.info("✅ Vulnerability report created successfully")
            return {
                "success": True,
                "vulnerability_cards": vulnerability_cards,
                "summary_report": summary_result.get("summary_report", ""),
                "total_vulnerabilities": len(vuln_data),
                "timestamp": summary_result.get("timestamp", "")
            }

        except Exception as e:
            logger.error(f"❌ Failed to create vulnerability report: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def format_tool_output_visual(tool_name: str, output: str, success: bool = True) -> Dict[str, Any]:
        """
        Format tool output with beautiful visual styling, syntax highlighting, and structure.

        Args:
            tool_name: Name of the security tool
            output: Raw output from the tool
            success: Whether the tool execution was successful

        Returns:
            Beautifully formatted tool output with visual enhancements
        """
        logger.info(f"🎨 Formatting output for {tool_name}")

        data = {
            "tool": tool_name,
            "output": output,
            "success": success
        }

        result = hexstrike_client.safe_post("api/visual/tool-output", data)
        if result.get("success"):
            logger.info(f"✅ Tool output formatted successfully for {tool_name}")
        else:
            logger.error(f"❌ Failed to format tool output for {tool_name}")

        return result

    @mcp.tool()
    def create_scan_summary(target: str, tools_used: str, vulnerabilities_found: int = 0,
                           execution_time: float = 0.0, findings: str = "") -> Dict[str, Any]:
        """
        Create a comprehensive scan summary report with beautiful visual formatting.

        Args:
            target: Target that was scanned
            tools_used: Comma-separated list of tools used
            vulnerabilities_found: Number of vulnerabilities discovered
            execution_time: Total execution time in seconds
            findings: Additional findings or notes

        Returns:
            Beautiful scan summary report with visual enhancements
        """
        logger.info(f"📊 Creating scan summary for {target}")

        tools_list = [tool.strip() for tool in tools_used.split(",")]

        summary_data = {
            "target": target,
            "tools_used": tools_list,
            "execution_time": execution_time,
            "vulnerabilities": [{"severity": "info"}] * vulnerabilities_found,  # Mock data for count
            "findings": findings
        }

        result = hexstrike_client.safe_post("api/visual/summary-report", summary_data)
        if result.get("success"):
            logger.info("✅ Scan summary created successfully")
        else:
            logger.error("❌ Failed to create scan summary")

        return result

    @mcp.tool()
    def display_system_metrics() -> Dict[str, Any]:
        """
        Display current system metrics and performance indicators with visual formatting.

        Returns:
            System metrics with beautiful visual presentation
        """
        logger.info("📈 Fetching system metrics")

        # Get telemetry data
        telemetry_result = hexstrike_client.safe_get("api/telemetry")

        if telemetry_result.get("success", True):
            logger.info("✅ System metrics retrieved successfully")

            # Format the metrics for better display
            metrics = telemetry_result.get("system_metrics", {})
            stats = {
                "cpu_percent": metrics.get("cpu_percent", 0),
                "memory_percent": metrics.get("memory_percent", 0),
                "disk_usage": metrics.get("disk_usage", 0),
                "uptime_seconds": telemetry_result.get("uptime_seconds", 0),
                "commands_executed": telemetry_result.get("commands_executed", 0),
                "success_rate": telemetry_result.get("success_rate", "0%")
            }

            return {
                "success": True,
                "metrics": stats,
                "formatted_display": f"""
🖥️  System Performance Metrics:
├─ CPU Usage: {stats['cpu_percent']:.1f}%
├─ Memory Usage: {stats['memory_percent']:.1f}%
├─ Disk Usage: {stats['disk_usage']:.1f}%
├─ Uptime: {stats['uptime_seconds']:.0f}s
├─ Commands Executed: {stats['commands_executed']}
└─ Success Rate: {stats['success_rate']}
""",
                "timestamp": telemetry_result.get("timestamp", "")
            }
        else:
            logger.error("❌ Failed to retrieve system metrics")
            return telemetry_result

    # ============================================================================
    # INTELLIGENT DECISION ENGINE TOOLS
    # ============================================================================

    @mcp.tool()
    def analyze_target_intelligence(target: str) -> Dict[str, Any]:
        """
        Analyze target using AI-powered intelligence to create comprehensive profile.

        Args:
            target: Target URL, IP address, or domain to analyze

        Returns:
            Comprehensive target profile with technology detection, risk assessment, and recommendations
        """
        logger.info(f"🧠 Analyzing target intelligence for: {target}")

        data = {"target": target}
        result = hexstrike_client.safe_post("api/intelligence/analyze-target", data)

        if result.get("success"):
            profile = result.get("target_profile", {})
            logger.info(f"✅ Target analysis completed - Type: {profile.get('target_type')}, Risk: {profile.get('risk_level')}")
        else:
            logger.error(f"❌ Target analysis failed for {target}")

        return result

    @mcp.tool()
    def select_optimal_tools_ai(target: str, objective: str = "comprehensive") -> Dict[str, Any]:
        """
        Use AI to select optimal security tools based on target analysis and testing objective.

        Args:
            target: Target to analyze
            objective: Testing objective - "comprehensive", "quick", or "stealth"

        Returns:
            AI-selected optimal tools with effectiveness ratings and target profile
        """
        logger.info(f"🎯 Selecting optimal tools for {target} with objective: {objective}")

        data = {
            "target": target,
            "objective": objective
        }
        result = hexstrike_client.safe_post("api/intelligence/select-tools", data)

        if result.get("success"):
            tools = result.get("selected_tools", [])
            logger.info(f"✅ AI selected {len(tools)} optimal tools: {', '.join(tools[:3])}{'...' if len(tools) > 3 else ''}")
        else:
            logger.error(f"❌ Tool selection failed for {target}")

        return result

    @mcp.tool()
    def optimize_tool_parameters_ai(target: str, tool: str, context: str = "{}") -> Dict[str, Any]:
        """
        Use AI to optimize tool parameters based on target profile and context.

        Args:
            target: Target to test
            tool: Security tool to optimize
            context: JSON string with additional context (stealth, aggressive, etc.)

        Returns:
            AI-optimized parameters for maximum effectiveness
        """
        import json

        logger.info(f"⚙️  Optimizing parameters for {tool} against {target}")

        try:
            context_dict = json.loads(context) if context != "{}" else {}
        except:
            context_dict = {}

        data = {
            "target": target,
            "tool": tool,
            "context": context_dict
        }
        result = hexstrike_client.safe_post("api/intelligence/optimize-parameters", data)

        if result.get("success"):
            params = result.get("optimized_parameters", {})
            logger.info(f"✅ Parameters optimized for {tool} - {len(params)} parameters configured")
        else:
            logger.error(f"❌ Parameter optimization failed for {tool}")

        return result

    @mcp.tool()
    def create_attack_chain_ai(target: str, objective: str = "comprehensive") -> Dict[str, Any]:
        """
        Create an intelligent attack chain using AI-driven tool sequencing and optimization.

        Args:
            target: Target for the attack chain
            objective: Attack objective - "comprehensive", "quick", or "stealth"

        Returns:
            AI-generated attack chain with success probability and time estimates
        """
        logger.info(f"⚔️  Creating AI-driven attack chain for {target}")

        data = {
            "target": target,
            "objective": objective
        }
        result = hexstrike_client.safe_post("api/intelligence/create-attack-chain", data)

        if result.get("success"):
            chain = result.get("attack_chain", {})
            steps = len(chain.get("steps", []))
            success_prob = chain.get("success_probability", 0)
            estimated_time = chain.get("estimated_time", 0)

            logger.info(f"✅ Attack chain created - {steps} steps, {success_prob:.2f} success probability, ~{estimated_time}s")
        else:
            logger.error(f"❌ Attack chain creation failed for {target}")

        return result

    @mcp.tool()
    def intelligent_smart_scan(target: str, objective: str = "comprehensive", max_tools: int = 5) -> Dict[str, Any]:
        """
        Execute an intelligent scan using AI-driven tool selection and parameter optimization.

        Args:
            target: Target to scan
            objective: Scanning objective - "comprehensive", "quick", or "stealth"
            max_tools: Maximum number of tools to use

        Returns:
            Results from AI-optimized scanning with tool execution summary
        """
        logger.info(f"{HexStrikeColors.FIRE_RED}🚀 Starting intelligent smart scan for {target}{HexStrikeColors.RESET}")

        data = {
            "target": target,
            "objective": objective,
            "max_tools": max_tools
        }
        result = hexstrike_client.safe_post("api/intelligence/smart-scan", data)

        if result.get("success"):
            scan_results = result.get("scan_results", {})
            tools_executed = scan_results.get("tools_executed", [])
            execution_summary = scan_results.get("execution_summary", {})

            # Enhanced logging with detailed results
            logger.info(f"{HexStrikeColors.SUCCESS}✅ Intelligent scan completed for {target}{HexStrikeColors.RESET}")
            logger.info(f"{HexStrikeColors.CYBER_ORANGE}📊 Execution Summary:{HexStrikeColors.RESET}")
            logger.info(f"   • Tools executed: {execution_summary.get('successful_tools', 0)}/{execution_summary.get('total_tools', 0)}")
            logger.info(f"   • Success rate: {execution_summary.get('success_rate', 0):.1f}%")
            logger.info(f"   • Total vulnerabilities: {scan_results.get('total_vulnerabilities', 0)}")
            logger.info(f"   • Execution time: {execution_summary.get('total_execution_time', 0):.2f}s")

            # Log successful tools
            successful_tools = [t['tool'] for t in tools_executed if t.get('success')]
            if successful_tools:
                logger.info(f"{HexStrikeColors.HIGHLIGHT_GREEN} Successful tools: {', '.join(successful_tools)} {HexStrikeColors.RESET}")

            # Log failed tools
            failed_tools = [t['tool'] for t in tools_executed if not t.get('success')]
            if failed_tools:
                logger.warning(f"{HexStrikeColors.HIGHLIGHT_RED} Failed tools: {', '.join(failed_tools)} {HexStrikeColors.RESET}")

            # Log vulnerabilities found
            if scan_results.get('total_vulnerabilities', 0) > 0:
                logger.warning(f"{HexStrikeColors.VULN_HIGH}🚨 {scan_results['total_vulnerabilities']} vulnerabilities detected!{HexStrikeColors.RESET}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ Intelligent scan failed for {target}: {result.get('error', 'Unknown error')}{HexStrikeColors.RESET}")

        return result

    @mcp.tool()
    def detect_technologies_ai(target: str) -> Dict[str, Any]:
        """
        Use AI to detect technologies and provide technology-specific testing recommendations.

        Args:
            target: Target to analyze for technology detection

        Returns:
            Detected technologies with AI-generated testing recommendations
        """
        logger.info(f"🔍 Detecting technologies for {target}")

        data = {"target": target}
        result = hexstrike_client.safe_post("api/intelligence/technology-detection", data)

        if result.get("success"):
            technologies = result.get("detected_technologies", [])
            cms = result.get("cms_type")
            recommendations = result.get("technology_recommendations", {})

            tech_info = f"Technologies: {', '.join(technologies)}"
            if cms:
                tech_info += f", CMS: {cms}"

            logger.info(f"✅ Technology detection completed - {tech_info}")
            logger.info(f"📋 Generated {len(recommendations)} technology-specific recommendations")
        else:
            logger.error(f"❌ Technology detection failed for {target}")

        return result

    @mcp.tool()
    def ai_reconnaissance_workflow(target: str, depth: str = "standard") -> Dict[str, Any]:
        """
        Execute AI-driven reconnaissance workflow with intelligent tool chaining.

        Args:
            target: Target for reconnaissance
            depth: Reconnaissance depth - "surface", "standard", or "deep"

        Returns:
            Comprehensive reconnaissance results with AI-driven insights
        """
        logger.info(f"🕵️  Starting AI reconnaissance workflow for {target} (depth: {depth})")

        # First analyze the target
        analysis_result = hexstrike_client.safe_post("api/intelligence/analyze-target", {"target": target})

        if not analysis_result.get("success"):
            return analysis_result

        # Create attack chain for reconnaissance
        objective = "comprehensive" if depth == "deep" else "quick" if depth == "surface" else "comprehensive"
        chain_result = hexstrike_client.safe_post("api/intelligence/create-attack-chain", {
            "target": target,
            "objective": objective
        })

        if not chain_result.get("success"):
            return chain_result

        # Execute the reconnaissance
        scan_result = hexstrike_client.safe_post("api/intelligence/smart-scan", {
            "target": target,
            "objective": objective,
            "max_tools": 8 if depth == "deep" else 3 if depth == "surface" else 5
        })

        logger.info(f"✅ AI reconnaissance workflow completed for {target}")

        return {
            "success": True,
            "target": target,
            "depth": depth,
            "target_analysis": analysis_result.get("target_profile", {}),
            "attack_chain": chain_result.get("attack_chain", {}),
            "scan_results": scan_result.get("scan_results", {}),
            "timestamp": datetime.now().isoformat()
        }

    @mcp.tool()
    def ai_vulnerability_assessment(target: str, focus_areas: str = "all") -> Dict[str, Any]:
        """
        Perform AI-driven vulnerability assessment with intelligent prioritization.

        Args:
            target: Target for vulnerability assessment
            focus_areas: Comma-separated focus areas - "web", "network", "api", "all"

        Returns:
            Prioritized vulnerability assessment results with AI insights
        """
        logger.info(f"🔬 Starting AI vulnerability assessment for {target}")

        # Analyze target first
        analysis_result = hexstrike_client.safe_post("api/intelligence/analyze-target", {"target": target})

        if not analysis_result.get("success"):
            return analysis_result

        profile = analysis_result.get("target_profile", {})
        target_type = profile.get("target_type", "unknown")

        # Select tools based on focus areas and target type
        if focus_areas == "all":
            objective = "comprehensive"
        elif "web" in focus_areas and target_type == "web_application":
            objective = "comprehensive"
        elif "network" in focus_areas and target_type == "network_host":
            objective = "comprehensive"
        else:
            objective = "quick"

        # Execute vulnerability assessment
        scan_result = hexstrike_client.safe_post("api/intelligence/smart-scan", {
            "target": target,
            "objective": objective,
            "max_tools": 6
        })

        logger.info(f"✅ AI vulnerability assessment completed for {target}")

        return {
            "success": True,
            "target": target,
            "focus_areas": focus_areas,
            "target_analysis": profile,
            "vulnerability_scan": scan_result.get("scan_results", {}),
            "risk_assessment": {
                "risk_level": profile.get("risk_level", "unknown"),
                "attack_surface_score": profile.get("attack_surface_score", 0),
                "confidence_score": profile.get("confidence_score", 0)
            },
            "timestamp": datetime.now().isoformat()
        }

    # ============================================================================
    # BUG BOUNTY HUNTING SPECIALIZED WORKFLOWS
    # ============================================================================

    @mcp.tool()
    def bugbounty_reconnaissance_workflow(domain: str, scope: str = "", out_of_scope: str = "",
                                        program_type: str = "web") -> Dict[str, Any]:
        """
        Create comprehensive reconnaissance workflow for bug bounty hunting.

        Args:
            domain: Target domain for bug bounty
            scope: Comma-separated list of in-scope domains/IPs
            out_of_scope: Comma-separated list of out-of-scope domains/IPs
            program_type: Type of program (web, api, mobile, iot)

        Returns:
            Comprehensive reconnaissance workflow with phases and tools
        """
        data = {
            "domain": domain,
            "scope": scope.split(",") if scope else [],
            "out_of_scope": out_of_scope.split(",") if out_of_scope else [],
            "program_type": program_type
        }

        logger.info(f"🎯 Creating reconnaissance workflow for {domain}")
        result = hexstrike_client.safe_post("api/bugbounty/reconnaissance-workflow", data)

        if result.get("success"):
            workflow = result.get("workflow", {})
            logger.info(f"✅ Reconnaissance workflow created - {workflow.get('tools_count', 0)} tools, ~{workflow.get('estimated_time', 0)}s")
        else:
            logger.error(f"❌ Failed to create reconnaissance workflow for {domain}")

        return result

    @mcp.tool()
    def bugbounty_vulnerability_hunting(domain: str, priority_vulns: str = "rce,sqli,xss,idor,ssrf",
                                       bounty_range: str = "unknown") -> Dict[str, Any]:
        """
        Create vulnerability hunting workflow prioritized by impact and bounty potential.

        Args:
            domain: Target domain for bug bounty
            priority_vulns: Comma-separated list of priority vulnerability types
            bounty_range: Expected bounty range (low, medium, high, critical)

        Returns:
            Vulnerability hunting workflow prioritized by impact
        """
        data = {
            "domain": domain,
            "priority_vulns": priority_vulns.split(",") if priority_vulns else [],
            "bounty_range": bounty_range
        }

        logger.info(f"🎯 Creating vulnerability hunting workflow for {domain}")
        result = hexstrike_client.safe_post("api/bugbounty/vulnerability-hunting-workflow", data)

        if result.get("success"):
            workflow = result.get("workflow", {})
            logger.info(f"✅ Vulnerability hunting workflow created - Priority score: {workflow.get('priority_score', 0)}")
        else:
            logger.error(f"❌ Failed to create vulnerability hunting workflow for {domain}")

        return result

    @mcp.tool()
    def bugbounty_business_logic_testing(domain: str, program_type: str = "web") -> Dict[str, Any]:
        """
        Create business logic testing workflow for advanced bug bounty hunting.

        Args:
            domain: Target domain for bug bounty
            program_type: Type of program (web, api, mobile)

        Returns:
            Business logic testing workflow with manual and automated tests
        """
        data = {
            "domain": domain,
            "program_type": program_type
        }

        logger.info(f"🎯 Creating business logic testing workflow for {domain}")
        result = hexstrike_client.safe_post("api/bugbounty/business-logic-workflow", data)

        if result.get("success"):
            workflow = result.get("workflow", {})
            test_count = sum(len(category["tests"]) for category in workflow.get("business_logic_tests", []))
            logger.info(f"✅ Business logic testing workflow created - {test_count} tests")
        else:
            logger.error(f"❌ Failed to create business logic testing workflow for {domain}")

        return result

    @mcp.tool()
    def bugbounty_osint_gathering(domain: str) -> Dict[str, Any]:
        """
        Create OSINT (Open Source Intelligence) gathering workflow for bug bounty reconnaissance.

        Args:
            domain: Target domain for OSINT gathering

        Returns:
            OSINT gathering workflow with multiple intelligence phases
        """
        data = {"domain": domain}

        logger.info(f"🎯 Creating OSINT gathering workflow for {domain}")
        result = hexstrike_client.safe_post("api/bugbounty/osint-workflow", data)

        if result.get("success"):
            workflow = result.get("workflow", {})
            phases = len(workflow.get("osint_phases", []))
            logger.info(f"✅ OSINT workflow created - {phases} intelligence phases")
        else:
            logger.error(f"❌ Failed to create OSINT workflow for {domain}")

        return result

    @mcp.tool()
    def bugbounty_file_upload_testing(target_url: str) -> Dict[str, Any]:
        """
        Create file upload vulnerability testing workflow with bypass techniques.

        Args:
            target_url: Target URL with file upload functionality

        Returns:
            File upload testing workflow with malicious files and bypass techniques
        """
        data = {"target_url": target_url}

        logger.info(f"🎯 Creating file upload testing workflow for {target_url}")
        result = hexstrike_client.safe_post("api/bugbounty/file-upload-testing", data)

        if result.get("success"):
            workflow = result.get("workflow", {})
            phases = len(workflow.get("test_phases", []))
            logger.info(f"✅ File upload testing workflow created - {phases} test phases")
        else:
            logger.error(f"❌ Failed to create file upload testing workflow for {target_url}")

        return result

    @mcp.tool()
    def bugbounty_comprehensive_assessment(domain: str, scope: str = "",
                                         priority_vulns: str = "rce,sqli,xss,idor,ssrf",
                                         include_osint: bool = True,
                                         include_business_logic: bool = True) -> Dict[str, Any]:
        """
        Create comprehensive bug bounty assessment combining all specialized workflows.

        Args:
            domain: Target domain for bug bounty
            scope: Comma-separated list of in-scope domains/IPs
            priority_vulns: Comma-separated list of priority vulnerability types
            include_osint: Include OSINT gathering workflow
            include_business_logic: Include business logic testing workflow

        Returns:
            Comprehensive bug bounty assessment with all workflows and summary
        """
        data = {
            "domain": domain,
            "scope": scope.split(",") if scope else [],
            "priority_vulns": priority_vulns.split(",") if priority_vulns else [],
            "include_osint": include_osint,
            "include_business_logic": include_business_logic
        }

        logger.info(f"🎯 Creating comprehensive bug bounty assessment for {domain}")
        result = hexstrike_client.safe_post("api/bugbounty/comprehensive-assessment", data)

        if result.get("success"):
            assessment = result.get("assessment", {})
            summary = assessment.get("summary", {})
            logger.info(f"✅ Comprehensive assessment created - {summary.get('workflow_count', 0)} workflows, ~{summary.get('total_estimated_time', 0)}s")
        else:
            logger.error(f"❌ Failed to create comprehensive assessment for {domain}")

        return result

    @mcp.tool()
    def bugbounty_authentication_bypass_testing(target_url: str, auth_type: str = "form") -> Dict[str, Any]:
        """
        Create authentication bypass testing workflow for bug bounty hunting.

        Args:
            target_url: Target URL with authentication
            auth_type: Type of authentication (form, jwt, oauth, saml)

        Returns:
            Authentication bypass testing strategies and techniques
        """
        bypass_techniques = {
            "form": [
                {"technique": "SQL Injection", "payloads": ["admin'--", "' OR '1'='1'--"]},
                {"technique": "Default Credentials", "payloads": ["admin:admin", "admin:password"]},
                {"technique": "Password Reset", "description": "Test password reset token reuse and manipulation"},
                {"technique": "Session Fixation", "description": "Test session ID prediction and fixation"}
            ],
            "jwt": [
                {"technique": "Algorithm Confusion", "description": "Change RS256 to HS256"},
                {"technique": "None Algorithm", "description": "Set algorithm to 'none'"},
                {"technique": "Key Confusion", "description": "Use public key as HMAC secret"},
                {"technique": "Token Manipulation", "description": "Modify claims and resign token"}
            ],
            "oauth": [
                {"technique": "Redirect URI Manipulation", "description": "Test open redirect in redirect_uri"},
                {"technique": "State Parameter", "description": "Test CSRF via missing/weak state parameter"},
                {"technique": "Code Reuse", "description": "Test authorization code reuse"},
                {"technique": "Client Secret", "description": "Test for exposed client secrets"}
            ],
            "saml": [
                {"technique": "XML Signature Wrapping", "description": "Manipulate SAML assertions"},
                {"technique": "XML External Entity", "description": "Test XXE in SAML requests"},
                {"technique": "Replay Attacks", "description": "Test assertion replay"},
                {"technique": "Signature Bypass", "description": "Test signature validation bypass"}
            ]
        }

        workflow = {
            "target": target_url,
            "auth_type": auth_type,
            "bypass_techniques": bypass_techniques.get(auth_type, []),
            "testing_phases": [
                {"phase": "reconnaissance", "description": "Identify authentication mechanisms"},
                {"phase": "baseline_testing", "description": "Test normal authentication flow"},
                {"phase": "bypass_testing", "description": "Apply bypass techniques"},
                {"phase": "privilege_escalation", "description": "Test for privilege escalation"}
            ],
            "estimated_time": 240,
            "manual_testing_required": True
        }

        logger.info(f"🎯 Created authentication bypass testing workflow for {target_url}")

        return {
            "success": True,
            "workflow": workflow,
            "timestamp": datetime.now().isoformat()
        }

    # ============================================================================
    # ENHANCED HTTP TESTING FRAMEWORK & BROWSER AGENT (BURP SUITE ALTERNATIVE)
    # ============================================================================

    @mcp.tool()
    def http_framework_test(url: str, method: str = "GET", data: dict = {},
                           headers: dict = {}, cookies: dict = {}, action: str = "request") -> Dict[str, Any]:
        """
        Enhanced HTTP testing framework (Burp Suite alternative) for comprehensive web security testing.

        Args:
            url: Target URL to test
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            data: Request data/parameters
            headers: Custom headers
            cookies: Custom cookies
            action: Action to perform (request, spider, proxy_history, set_rules, set_scope, repeater, intruder)

        Returns:
            HTTP testing results with vulnerability analysis
        """
        data_payload = {
            "url": url,
            "method": method,
            "data": data,
            "headers": headers,
            "cookies": cookies,
            "action": action
        }

        logger.info(f"{HexStrikeColors.FIRE_RED}🔥 Starting HTTP Framework {action}: {url}{HexStrikeColors.RESET}")
        result = hexstrike_client.safe_post("api/tools/http-framework", data_payload)

        if result.get("success"):
            logger.info(f"{HexStrikeColors.SUCCESS}✅ HTTP Framework {action} completed for {url}{HexStrikeColors.RESET}")

            # Enhanced logging for vulnerabilities found
            if result.get("result", {}).get("vulnerabilities"):
                vuln_count = len(result["result"]["vulnerabilities"])
                logger.info(f"{HexStrikeColors.HIGHLIGHT_RED} Found {vuln_count} potential vulnerabilities {HexStrikeColors.RESET}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ HTTP Framework {action} failed for {url}{HexStrikeColors.RESET}")

        return result

    @mcp.tool()
    def browser_agent_inspect(url: str, headless: bool = True, wait_time: int = 5,
                             action: str = "navigate", proxy_port: int = None, active_tests: bool = False) -> Dict[str, Any]:
        """
        AI-powered browser agent for comprehensive web application inspection and security analysis.

        Args:
            url: Target URL to inspect
            headless: Run browser in headless mode
            wait_time: Time to wait after page load
            action: Action to perform (navigate, screenshot, close, status)
            proxy_port: Optional proxy port for request interception
            active_tests: Run lightweight active reflected XSS tests (safe GET-only)

        Returns:
            Browser inspection results with security analysis
        """
        data_payload = {
            "url": url,
            "headless": headless,
            "wait_time": wait_time,
            "action": action,
            "proxy_port": proxy_port,
            "active_tests": active_tests
        }

        logger.info(f"{HexStrikeColors.CRIMSON}🌐 Starting Browser Agent {action}: {url}{HexStrikeColors.RESET}")
        result = hexstrike_client.safe_post("api/tools/browser-agent", data_payload)

        if result.get("success"):
            logger.info(f"{HexStrikeColors.SUCCESS}✅ Browser Agent {action} completed for {url}{HexStrikeColors.RESET}")

            # Enhanced logging for security analysis
            if action == "navigate" and result.get("result", {}).get("security_analysis"):
                security_analysis = result["result"]["security_analysis"]
                issues_count = security_analysis.get("total_issues", 0)
                security_score = security_analysis.get("security_score", 0)

                if issues_count > 0:
                    logger.warning(f"{HexStrikeColors.HIGHLIGHT_YELLOW} Security Issues: {issues_count} | Score: {security_score}/100 {HexStrikeColors.RESET}")
                else:
                    logger.info(f"{HexStrikeColors.HIGHLIGHT_GREEN} No security issues found | Score: {security_score}/100 {HexStrikeColors.RESET}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ Browser Agent {action} failed for {url}{HexStrikeColors.RESET}")

        return result

    # ---------------- Additional HTTP Framework Tools (sync with server) ----------------
    @mcp.tool()
    def http_set_rules(rules: list) -> Dict[str, Any]:
        """Set match/replace rules used to rewrite parts of URL/query/headers/body before sending.
        Rule format: {'where':'url|query|headers|body','pattern':'regex','replacement':'string'}"""
        payload = {"action": "set_rules", "rules": rules}
        return hexstrike_client.safe_post("api/tools/http-framework", payload)

    @mcp.tool()
    def http_set_scope(host: str, include_subdomains: bool = True) -> Dict[str, Any]:
        """Define in-scope host (and optionally subdomains) so out-of-scope requests are skipped."""
        payload = {"action": "set_scope", "host": host, "include_subdomains": include_subdomains}
        return hexstrike_client.safe_post("api/tools/http-framework", payload)

    @mcp.tool()
    def http_repeater(request_spec: dict) -> Dict[str, Any]:
        """Send a crafted request (Burp Repeater equivalent). request_spec keys: url, method, headers, cookies, data."""
        payload = {"action": "repeater", "request": request_spec}
        return hexstrike_client.safe_post("api/tools/http-framework", payload)

    @mcp.tool()
    def http_intruder(url: str, method: str = "GET", location: str = "query", params: list = None,
                      payloads: list = None, base_data: dict = None, max_requests: int = 100) -> Dict[str, Any]:
        """Simple Intruder (sniper) fuzzing. Iterates payloads over each param individually.
        location: query|body|headers|cookie."""
        payload = {
            "action": "intruder",
            "url": url,
            "method": method,
            "location": location,
            "params": params or [],
            "payloads": payloads or [],
            "base_data": base_data or {},
            "max_requests": max_requests
        }
        return hexstrike_client.safe_post("api/tools/http-framework", payload)

    @mcp.tool()
    def burpsuite_alternative_scan(target: str, scan_type: str = "comprehensive",
                                  headless: bool = True, max_depth: int = 3,
                                  max_pages: int = 50) -> Dict[str, Any]:
        """
        Comprehensive Burp Suite alternative combining HTTP framework and browser agent for complete web security testing.

        Args:
            target: Target URL or domain to scan
            scan_type: Type of scan (comprehensive, spider, passive, active)
            headless: Run browser in headless mode
            max_depth: Maximum crawling depth
            max_pages: Maximum pages to analyze

        Returns:
            Comprehensive security assessment results
        """
        data_payload = {
            "target": target,
            "scan_type": scan_type,
            "headless": headless,
            "max_depth": max_depth,
            "max_pages": max_pages
        }

        logger.info(f"{HexStrikeColors.BLOOD_RED}🔥 Starting Burp Suite Alternative {scan_type} scan: {target}{HexStrikeColors.RESET}")
        result = hexstrike_client.safe_post("api/tools/burpsuite-alternative", data_payload)

        if result.get("success"):
            logger.info(f"{HexStrikeColors.SUCCESS}✅ Burp Suite Alternative scan completed for {target}{HexStrikeColors.RESET}")

            # Enhanced logging for comprehensive results
            if result.get("result", {}).get("summary"):
                summary = result["result"]["summary"]
                total_vulns = summary.get("total_vulnerabilities", 0)
                pages_analyzed = summary.get("pages_analyzed", 0)
                security_score = summary.get("security_score", 0)

                logger.info(f"{HexStrikeColors.HIGHLIGHT_BLUE} SCAN SUMMARY {HexStrikeColors.RESET}")
                logger.info(f"  📊 Pages Analyzed: {pages_analyzed}")
                logger.info(f"  🚨 Vulnerabilities: {total_vulns}")
                logger.info(f"  🛡️  Security Score: {security_score}/100")

                # Log vulnerability breakdown
                vuln_breakdown = summary.get("vulnerability_breakdown", {})
                for severity, count in vuln_breakdown.items():
                    if count > 0:
                        color = {
                                    'critical': HexStrikeColors.CRITICAL,
        'high': HexStrikeColors.FIRE_RED,
        'medium': HexStrikeColors.CYBER_ORANGE,
        'low': HexStrikeColors.YELLOW,
        'info': HexStrikeColors.INFO
    }.get(severity.lower(), HexStrikeColors.WHITE)

                        logger.info(f"  {color}{severity.upper()}: {count}{HexStrikeColors.RESET}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ Burp Suite Alternative scan failed for {target}{HexStrikeColors.RESET}")

        return result

    @mcp.tool()
    def error_handling_statistics() -> Dict[str, Any]:
        """
        Get intelligent error handling system statistics and recent error patterns.

        Returns:
            Error handling statistics and patterns
        """
        logger.info(f"{HexStrikeColors.ELECTRIC_PURPLE}📊 Retrieving error handling statistics{HexStrikeColors.RESET}")
        result = hexstrike_client.safe_get("api/error-handling/statistics")

        if result.get("success"):
            stats = result.get("statistics", {})
            total_errors = stats.get("total_errors", 0)
            recent_errors = stats.get("recent_errors_count", 0)

            logger.info(f"{HexStrikeColors.SUCCESS}✅ Error statistics retrieved{HexStrikeColors.RESET}")
            logger.info(f"  📈 Total Errors: {total_errors}")
            logger.info(f"  🕒 Recent Errors: {recent_errors}")

            # Log error breakdown by type
            error_counts = stats.get("error_counts_by_type", {})
            if error_counts:
                logger.info(f"{HexStrikeColors.HIGHLIGHT_BLUE} ERROR BREAKDOWN {HexStrikeColors.RESET}")
                for error_type, count in error_counts.items():
                                          logger.info(f"  {HexStrikeColors.FIRE_RED}{error_type}: {count}{HexStrikeColors.RESET}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ Failed to retrieve error statistics{HexStrikeColors.RESET}")

        return result

    @mcp.tool()
    def test_error_recovery(tool_name: str, error_type: str = "timeout",
                           target: str = "example.com") -> Dict[str, Any]:
        """
        Test the intelligent error recovery system with simulated failures.

        Args:
            tool_name: Name of tool to simulate error for
            error_type: Type of error to simulate (timeout, permission_denied, network_unreachable, etc.)
            target: Target for the simulated test

        Returns:
            Recovery strategy and system response
        """
        data_payload = {
            "tool_name": tool_name,
            "error_type": error_type,
            "target": target
        }

        logger.info(f"{HexStrikeColors.RUBY}🧪 Testing error recovery for {tool_name} with {error_type}{HexStrikeColors.RESET}")
        result = hexstrike_client.safe_post("api/error-handling/test-recovery", data_payload)

        if result.get("success"):
            recovery_strategy = result.get("recovery_strategy", {})
            action = recovery_strategy.get("action", "unknown")
            success_prob = recovery_strategy.get("success_probability", 0)

            logger.info(f"{HexStrikeColors.SUCCESS}✅ Error recovery test completed{HexStrikeColors.RESET}")
            logger.info(f"  🔧 Recovery Action: {action}")
            logger.info(f"  📊 Success Probability: {success_prob:.2%}")

            # Log alternative tools if available
            alternatives = result.get("alternative_tools", [])
            if alternatives:
                logger.info(f"  🔄 Alternative Tools: {', '.join(alternatives)}")
        else:
            logger.error(f"{HexStrikeColors.ERROR}❌ Error recovery test failed{HexStrikeColors.RESET}")

        return result

    return mcp

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the HexStrike AI MCP Client")
    parser.add_argument("--server", type=str, default=DEFAULT_HEXSTRIKE_SERVER,
                      help=f"HexStrike AI API server URL (default: {DEFAULT_HEXSTRIKE_SERVER})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_REQUEST_TIMEOUT,
                      help=f"Request timeout in seconds (default: {DEFAULT_REQUEST_TIMEOUT})")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()

def main():
    """Main entry point for the MCP server."""
    args = parse_args()

    # Configure logging based on debug flag
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("🔍 Debug logging enabled")

    # MCP compatibility: No banner output to avoid JSON parsing issues
    logger.info(f"🚀 Starting HexStrike AI MCP Client v6.0")
    logger.info(f"🔗 Connecting to: {args.server}")

    try:
        # Initialize the HexStrike AI client
        hexstrike_client = HexStrikeClient(args.server, args.timeout)

        # Check server health and log the result
        health = hexstrike_client.check_health()
        if "error" in health:
            logger.warning(f"⚠️  Unable to connect to HexStrike AI API server at {args.server}: {health['error']}")
            logger.warning("🚀 MCP server will start, but tool execution may fail")
        else:
            logger.info(f"🎯 Successfully connected to HexStrike AI API server at {args.server}")
            logger.info(f"🏥 Server health status: {health['status']}")
            logger.info(f"📊 Version: {health.get('version', 'unknown')}")
            if not health.get("all_essential_tools_available", False):
                logger.warning("⚠️  Not all essential tools are available on the HexStrike server")
                missing_tools = [tool for tool, available in health.get("tools_status", {}).items() if not available]
                if missing_tools:
                    logger.warning(f"❌ Missing tools: {', '.join(missing_tools[:5])}{'...' if len(missing_tools) > 5 else ''}")

        # Set up and run the MCP server
        mcp = setup_mcp_server(hexstrike_client)
        logger.info("🚀 Starting HexStrike AI MCP server")
        logger.info("🤖 Ready to serve AI agents with enhanced cybersecurity capabilities")
        mcp.run()
    except Exception as e:
        logger.error(f"💥 Error starting MCP server: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
