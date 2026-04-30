"""
Jaeles tool implementation for automated security testing
"""
from typing import Dict, Any, List
from tools.base import BaseTool
import json


class JaelesTool(BaseTool):
    """Jaeles - The Swiss Army knife for automated Web Application Testing"""

    def __init__(self):
        super().__init__("Jaeles", "jaeles")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build jaeles command with comprehensive options

        Args:
            target: Target URL or file containing URLs
            params: Dictionary containing:
                - signatures: Signature selector (e.g., "sqli,rce,ssrf")
                - signs: Path to custom signature directory
                - scan: Scan mode (auto, quick, full)
                - passive: Passive mode (no active testing)
                - threads: Number of threads
                - timeout: HTTP timeout in seconds
                - retry: Number of retries
                - delay: Delay between requests
                - proxy: Proxy URL
                - headers: Custom headers
                - output: Output directory
                - json_output: JSON output file
                - verbose: Verbose output
                - additional_args: Additional command-line arguments

        Returns:
            List of command arguments
        """
        cmd_parts = ["jaeles", "scan"]

        # URL
        cmd_parts.extend(["-u", target])

        # Signatures
        if params.get("signatures"):
            cmd_parts.extend(["-s", params["signatures"]])

        # Custom signature path
        if params.get("signs"):
            cmd_parts.extend(["--signs", params["signs"]])

        # Scan mode
        if params.get("scan"):
            cmd_parts.extend(["--scan", params["scan"]])

        # Passive mode
        if params.get("passive", False):
            cmd_parts.append("--passive")

        # Threads
        threads = params.get("threads", 20)
        cmd_parts.extend(["-c", str(threads)])

        # Timeout
        if params.get("timeout"):
            cmd_parts.extend(["--timeout", str(params["timeout"])])

        # Retry
        if params.get("retry"):
            cmd_parts.extend(["--retry", str(params["retry"])])

        # Delay
        if params.get("delay"):
            cmd_parts.extend(["--delay", str(params["delay"])])

        # Proxy
        if params.get("proxy"):
            cmd_parts.extend(["--proxy", params["proxy"]])

        # Custom headers
        if params.get("headers"):
            headers = params["headers"] if isinstance(params["headers"], list) else [params["headers"]]
            for header in headers:
                cmd_parts.extend(["--header", header])

        # Output directory
        if params.get("output"):
            cmd_parts.extend(["-o", params["output"]])

        # JSON output
        if params.get("json_output"):
            cmd_parts.extend(["--json-output", params["json_output"]])

        # Verbose
        if params.get("verbose", False):
            cmd_parts.append("-v")

        # Additional arguments
        additional_args = params.get("additional_args", "")
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse jaeles output to extract vulnerability findings

        Args:
            stdout: Command standard output
            stderr: Command standard error
            returncode: Command return code

        Returns:
            Dictionary containing:
                - vulnerabilities: List of discovered vulnerabilities
                - vulnerability_count: Number of vulnerabilities
                - vulns_by_severity: Vulnerabilities categorized by severity
                - vulns_by_type: Vulnerabilities categorized by type
                - affected_urls: List of URLs with vulnerabilities
                - signatures_matched: Signatures that matched
                - raw_output: Original stdout
                - stderr: Original stderr
                - returncode: Command return code
        """
        vulnerabilities = []
        vulns_by_severity = {
            'CRITICAL': [],
            'HIGH': [],
            'MEDIUM': [],
            'LOW': [],
            'INFO': []
        }
        vulns_by_type = {}
        affected_urls = set()
        signatures_matched = set()

        # Parse output lines
        for line in stdout.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Try to parse as JSON
            try:
                vuln = json.loads(line)

                vuln_name = vuln.get('VulnName', vuln.get('name', 'Unknown'))
                severity = vuln.get('Severity', vuln.get('severity', 'INFO')).upper()
                url = vuln.get('URL', vuln.get('url', ''))
                signature = vuln.get('Sign', vuln.get('signature', ''))
                risk = vuln.get('Risk', vuln.get('risk', ''))

                vuln_info = {
                    'name': vuln_name,
                    'severity': severity,
                    'url': url,
                    'signature': signature,
                    'risk': risk
                }
                vulnerabilities.append(vuln_info)

                # Categorize by severity
                if severity in vulns_by_severity:
                    vulns_by_severity[severity].append(vuln_info)

                # Categorize by type
                vuln_type = vuln_name.split('-')[0] if '-' in vuln_name else vuln_name
                if vuln_type not in vulns_by_type:
                    vulns_by_type[vuln_type] = []
                vulns_by_type[vuln_type].append(vuln_info)

                # Track affected URLs and signatures
                if url:
                    affected_urls.add(url)
                if signature:
                    signatures_matched.add(signature)

            except json.JSONDecodeError:
                # Not JSON, try to parse plain text
                # Look for vulnerability indicators
                if any(indicator in line for indicator in ['[Vulnerable]', '[VULN]', 'Found:', 'Matched:']):
                    vulnerabilities.append({
                        'finding': line,
                        'severity': 'MEDIUM'
                    })

        # Get severity counts
        severity_counts = {k: len(v) for k, v in vulns_by_severity.items() if v}

        # Get type counts
        type_counts = {k: len(v) for k, v in vulns_by_type.items()}

        return {
            "vulnerabilities": vulnerabilities,
            "vulnerability_count": len(vulnerabilities),
            "vulns_by_severity": vulns_by_severity,
            "severity_counts": severity_counts,
            "vulns_by_type": vulns_by_type,
            "type_counts": type_counts,
            "affected_urls": sorted(list(affected_urls)),
            "affected_url_count": len(affected_urls),
            "signatures_matched": sorted(list(signatures_matched)),
            "signature_count": len(signatures_matched),
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
