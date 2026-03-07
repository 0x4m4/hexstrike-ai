"""
testssl.sh tool implementation for SSL/TLS testing
"""
from typing import Dict, Any, List
from tools.base import BaseTool
import re
import json


class TestSSLTool(BaseTool):
    """testssl.sh - Testing TLS/SSL encryption anywhere on any port"""

    def __init__(self):
        super().__init__("testssl.sh", "testssl")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build testssl command with comprehensive options

        Args:
            target: Target host:port to test
            params: Dictionary containing:
                - protocols: Test specific protocols (ssl2,ssl3,tls1,tls1_1,tls1_2,tls1_3)
                - ciphers: Test ciphers
                - server_defaults: Test server defaults
                - server_preference: Test server cipher order
                - vulnerabilities: Test for vulnerabilities (heartbleed, ccs, ticketbleed, etc.)
                - pfs: Test Perfect Forward Secrecy
                - header: Test security headers
                - each_cipher: Test each cipher individually
                - json: JSON output
                - severity: Set minimum severity (LOW, MEDIUM, HIGH, CRITICAL)
                - parallel: Parallel testing mode
                - additional_args: Additional command-line arguments

        Returns:
            List of command arguments
        """
        cmd_parts = ["testssl"]

        # Protocols
        if params.get("protocols"):
            for protocol in params["protocols"].split(','):
                cmd_parts.append(f"-{protocol}")
        else:
            # Default: test all protocols
            cmd_parts.append("-p")

        # Server defaults
        if params.get("server_defaults", True):
            cmd_parts.append("-S")

        # Server cipher order preference
        if params.get("server_preference", True):
            cmd_parts.append("-P")

        # Vulnerabilities
        if params.get("vulnerabilities", True):
            cmd_parts.append("-U")

        # Perfect Forward Secrecy
        if params.get("pfs", False):
            cmd_parts.append("-f")

        # Security headers
        if params.get("header", True):
            cmd_parts.append("-h")

        # Test each cipher
        if params.get("each_cipher", False):
            cmd_parts.append("-E")

        # Cipher tests
        if params.get("ciphers", False):
            cmd_parts.append("-e")

        # JSON output
        if params.get("json", True):
            cmd_parts.append("--json")

        # Severity
        if params.get("severity"):
            cmd_parts.extend(["--severity", params["severity"]])

        # Parallel testing
        if params.get("parallel", False):
            cmd_parts.append("--parallel")

        # Additional arguments
        additional_args = params.get("additional_args", "")
        if additional_args:
            cmd_parts.extend(additional_args.split())

        # Target
        cmd_parts.append(target)

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse testssl output to extract SSL/TLS security information

        Args:
            stdout: Command standard output
            stderr: Command standard error
            returncode: Command return code

        Returns:
            Dictionary containing:
                - vulnerabilities: List of discovered vulnerabilities
                - vulnerability_count: Number of vulnerabilities
                - protocols: Supported protocols
                - ciphers: Supported ciphers
                - server_preferences: Server configuration preferences
                - security_headers: Security header status
                - certificate_info: Certificate information
                - findings_by_severity: Findings categorized by severity
                - raw_output: Original stdout
                - stderr: Original stderr
                - returncode: Command return code
        """
        vulnerabilities = []
        protocols = {}
        ciphers = []
        server_preferences = {}
        security_headers = {}
        certificate_info = {}
        findings_by_severity = {
            'CRITICAL': [],
            'HIGH': [],
            'MEDIUM': [],
            'LOW': [],
            'INFO': []
        }

        # Try to parse JSON output
        json_data = None
        try:
            # testssl.sh outputs JSON objects, try to find and parse them
            for line in stdout.split('\n'):
                if line.strip().startswith('{'):
                    try:
                        json_data = json.loads(line)
                        break
                    except:
                        continue
        except:
            pass

        if json_data:
            # Parse JSON format
            for finding in json_data.get('scanResult', []):
                finding_id = finding.get('id', '')
                severity = finding.get('severity', 'INFO').upper()
                finding_text = finding.get('finding', '')

                if severity in findings_by_severity:
                    findings_by_severity[severity].append({
                        'id': finding_id,
                        'finding': finding_text,
                        'severity': severity
                    })

                # Categorize vulnerabilities (HIGH and CRITICAL)
                if severity in ['HIGH', 'CRITICAL']:
                    vulnerabilities.append({
                        'id': finding_id,
                        'finding': finding_text,
                        'severity': severity
                    })

        else:
            # Parse text output
            lines = stdout.split('\n')
            current_section = None

            for line in lines:
                line_stripped = line.strip()

                # Detect vulnerabilities
                vuln_patterns = [
                    r'(VULNERABLE|NOT ok|CRITICAL|HIGH)',
                    r'(Heartbleed|CCS|CRIME|BREACH|POODLE|FREAK|DROWN|LOGJAM|SWEET32|ROBOT)',
                ]

                for pattern in vuln_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        vulnerabilities.append({
                            'finding': line_stripped,
                            'severity': 'HIGH' if 'CRITICAL' not in line else 'CRITICAL'
                        })
                        break

                # Protocol support
                protocol_match = re.search(r'(SSLv2|SSLv3|TLS 1\.0|TLS 1\.1|TLS 1\.2|TLS 1\.3)\s+(.+)', line)
                if protocol_match:
                    protocol = protocol_match.group(1)
                    status = protocol_match.group(2)
                    protocols[protocol] = status

                # Certificate info
                if 'Certificate' in line or 'Subject' in line or 'Issuer' in line:
                    cert_match = re.search(r'([^:]+):\s+(.+)', line)
                    if cert_match:
                        cert_key = cert_match.group(1).strip()
                        cert_value = cert_match.group(2).strip()
                        certificate_info[cert_key] = cert_value

                # Security headers
                if 'Strict-Transport-Security' in line or 'Public-Key-Pins' in line or 'X-Frame-Options' in line:
                    header_match = re.search(r'([^:]+):\s+(.+)', line)
                    if header_match:
                        header_name = header_match.group(1).strip()
                        header_value = header_match.group(2).strip()
                        security_headers[header_name] = header_value

        # Count findings by severity
        severity_counts = {k: len(v) for k, v in findings_by_severity.items()}

        return {
            "vulnerabilities": vulnerabilities,
            "vulnerability_count": len(vulnerabilities),
            "protocols": protocols,
            "protocol_count": len(protocols),
            "ciphers": ciphers,
            "cipher_count": len(ciphers),
            "server_preferences": server_preferences,
            "security_headers": security_headers,
            "certificate_info": certificate_info,
            "findings_by_severity": findings_by_severity,
            "severity_counts": severity_counts,
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
