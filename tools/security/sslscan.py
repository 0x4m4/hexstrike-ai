"""
SSLScan tool implementation for SSL/TLS scanner
"""
from typing import Dict, Any, List
from tools.base import BaseTool
import re


class SSLScanTool(BaseTool):
    """SSLScan - Fast SSL/TLS scanner"""

    def __init__(self):
        super().__init__("SSLScan", "sslscan")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build sslscan command with comprehensive options

        Args:
            target: Target host:port to scan
            params: Dictionary containing:
                - xml: Output to XML file
                - no_failed: Hide failed ciphers
                - no_ciphersuites: Don't show supported ciphersuites
                - no_renegotiation: Don't check for TLS renegotiation
                - no_compression: Don't check for TLS compression
                - no_heartbleed: Don't check for Heartbleed
                - no_groups: Don't enumerate key exchange groups
                - show_certificate: Show full certificate
                - show_client_cas: Show trusted CAs for client auth
                - ipv4: Force IPv4
                - ipv6: Force IPv6
                - starttls: STARTTLS protocol (smtp, pop3, imap, ftp, xmpp)
                - additional_args: Additional command-line arguments

        Returns:
            List of command arguments
        """
        cmd_parts = ["sslscan"]

        # XML output
        if params.get("xml"):
            cmd_parts.extend(["--xml=" + params["xml"]])

        # Hide failed ciphers
        if params.get("no_failed", True):
            cmd_parts.append("--no-failed")

        # Don't show ciphersuites
        if params.get("no_ciphersuites", False):
            cmd_parts.append("--no-ciphersuites")

        # Don't check renegotiation
        if params.get("no_renegotiation", False):
            cmd_parts.append("--no-renegotiation")

        # Don't check compression
        if params.get("no_compression", False):
            cmd_parts.append("--no-compression")

        # Don't check Heartbleed
        if params.get("no_heartbleed", False):
            cmd_parts.append("--no-heartbleed")

        # Don't enumerate groups
        if params.get("no_groups", False):
            cmd_parts.append("--no-groups")

        # Show full certificate
        if params.get("show_certificate", True):
            cmd_parts.append("--show-certificate")

        # Show trusted CAs
        if params.get("show_client_cas", False):
            cmd_parts.append("--show-client-cas")

        # IPv4/IPv6
        if params.get("ipv4", False):
            cmd_parts.append("--ipv4")
        if params.get("ipv6", False):
            cmd_parts.append("--ipv6")

        # STARTTLS
        if params.get("starttls"):
            cmd_parts.extend(["--starttls-" + params["starttls"]])

        # Additional arguments
        additional_args = params.get("additional_args", "")
        if additional_args:
            cmd_parts.extend(additional_args.split())

        # Target
        cmd_parts.append(target)

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse sslscan output to extract SSL/TLS information

        Args:
            stdout: Command standard output
            stderr: Command standard error
            returncode: Command return code

        Returns:
            Dictionary containing:
                - supported_ciphers: List of supported ciphers with strength
                - cipher_count: Number of supported ciphers
                - protocols: Supported SSL/TLS protocols
                - vulnerabilities: List of discovered vulnerabilities
                - certificate: Certificate information
                - preferred_ciphers: Server's preferred ciphers per protocol
                - weak_ciphers: Ciphers with known weaknesses
                - security_issues: Security issues found
                - raw_output: Original stdout
                - stderr: Original stderr
                - returncode: Command return code
        """
        supported_ciphers = []
        protocols = {}
        vulnerabilities = []
        certificate = {}
        preferred_ciphers = {}
        weak_ciphers = []
        security_issues = []

        lines = stdout.split('\n')
        in_certificate_section = False

        for line in lines:
            line_stripped = line.strip()

            # Supported ciphers
            # Format: Accepted  TLSv1.2  256 bits  ECDHE-RSA-AES256-GCM-SHA384
            cipher_match = re.search(r'(Accepted|Preferred)\s+(SSLv[23]|TLSv[\d\.]+)\s+(\d+)\s+bits\s+(.+)', line)
            if cipher_match:
                status = cipher_match.group(1)
                protocol = cipher_match.group(2)
                bits = cipher_match.group(3)
                cipher = cipher_match.group(4).strip()

                cipher_info = {
                    'protocol': protocol,
                    'cipher': cipher,
                    'bits': int(bits),
                    'status': status
                }
                supported_ciphers.append(cipher_info)

                # Track preferred ciphers
                if status == 'Preferred':
                    preferred_ciphers[protocol] = cipher

                # Identify weak ciphers (< 128 bits or known weak algorithms)
                if int(bits) < 128 or any(weak in cipher.upper() for weak in ['DES', 'RC4', 'MD5', 'NULL', 'EXPORT', 'anon']):
                    weak_ciphers.append(cipher_info)

            # Protocol support
            # Format: SSLv2   disabled
            protocol_match = re.search(r'(SSLv[23]|TLSv[\d\.]+)\s+(enabled|disabled)', line)
            if protocol_match:
                protocol = protocol_match.group(1)
                status = protocol_match.group(2)
                protocols[protocol] = status

            # Vulnerabilities
            if 'vulnerable' in line.lower() or 'VULNERABLE' in line:
                vulnerabilities.append(line_stripped)

            # Heartbleed
            if 'Heartbleed' in line:
                if 'vulnerable' in line.lower():
                    vulnerabilities.append({
                        'name': 'Heartbleed',
                        'status': 'VULNERABLE',
                        'severity': 'CRITICAL'
                    })
                    security_issues.append('Heartbleed vulnerability detected')

            # TLS renegotiation
            if 'renegotiation' in line.lower():
                if 'insecure' in line.lower() or 'vulnerable' in line.lower():
                    vulnerabilities.append({
                        'name': 'Insecure Renegotiation',
                        'status': 'VULNERABLE',
                        'severity': 'MEDIUM'
                    })

            # TLS compression
            if 'compression' in line.lower():
                if 'enabled' in line.lower():
                    vulnerabilities.append({
                        'name': 'TLS Compression (CRIME)',
                        'status': 'ENABLED',
                        'severity': 'MEDIUM'
                    })

            # Certificate section
            if 'Subject:' in line or 'Issuer:' in line:
                in_certificate_section = True

            if in_certificate_section:
                cert_match = re.search(r'([^:]+):\s+(.+)', line)
                if cert_match:
                    cert_key = cert_match.group(1).strip()
                    cert_value = cert_match.group(2).strip()
                    certificate[cert_key] = cert_value

                # End of certificate section
                if line_stripped == '' and certificate:
                    in_certificate_section = False

        # Check for old SSL protocols
        if protocols.get('SSLv2') == 'enabled':
            security_issues.append('SSLv2 is enabled (deprecated and insecure)')
        if protocols.get('SSLv3') == 'enabled':
            security_issues.append('SSLv3 is enabled (POODLE vulnerability)')
        if protocols.get('TLSv1.0') == 'enabled':
            security_issues.append('TLSv1.0 is enabled (considered weak)')

        return {
            "supported_ciphers": supported_ciphers,
            "cipher_count": len(supported_ciphers),
            "protocols": protocols,
            "protocol_count": len(protocols),
            "vulnerabilities": vulnerabilities,
            "vulnerability_count": len(vulnerabilities),
            "certificate": certificate,
            "preferred_ciphers": preferred_ciphers,
            "weak_ciphers": weak_ciphers,
            "weak_cipher_count": len(weak_ciphers),
            "security_issues": security_issues,
            "issue_count": len(security_issues),
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
