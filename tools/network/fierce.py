"""
Fierce tool implementation for DNS reconnaissance
"""
from typing import Dict, Any, List
from tools.base import BaseTool
import re


class FierceTool(BaseTool):
    """Fierce - DNS reconnaissance tool for locating non-contiguous IP space"""

    def __init__(self):
        super().__init__("Fierce", "fierce")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build fierce command with comprehensive options

        Args:
            target: Target domain to scan
            params: Dictionary containing:
                - dns_servers: DNS servers to use (comma-separated)
                - subdomains: Custom subdomain wordlist file
                - traverse: Number of IPs to traverse for each discovered IP
                - wide: Scan entire class C of discovered IPs
                - delay: Time to wait between lookups (seconds)
                - threads: Number of threads
                - range: IP range to scan
                - additional_args: Additional command-line arguments

        Returns:
            List of command arguments
        """
        cmd_parts = ["fierce", "--domain", target]

        # DNS servers
        if params.get("dns_servers"):
            cmd_parts.extend(["--dns-servers", params["dns_servers"]])

        # Custom subdomain list
        if params.get("subdomains"):
            cmd_parts.extend(["--subdomain-file", params["subdomains"]])

        # Traverse IPs
        if params.get("traverse"):
            cmd_parts.extend(["--traverse", str(params["traverse"])])

        # Wide scan
        if params.get("wide", False):
            cmd_parts.append("--wide")

        # Delay between lookups
        if params.get("delay"):
            cmd_parts.extend(["--delay", str(params["delay"])])

        # Threads
        if params.get("threads"):
            cmd_parts.extend(["--threads", str(params["threads"])])

        # IP range
        if params.get("range"):
            cmd_parts.extend(["--range", params["range"]])

        # Additional arguments
        additional_args = params.get("additional_args", "")
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse fierce output to extract DNS information

        Args:
            stdout: Command standard output
            stderr: Command standard error
            returncode: Command return code

        Returns:
            Dictionary containing:
                - subdomains: List of discovered subdomains with IPs
                - subdomain_count: Number of discovered subdomains
                - ip_addresses: List of unique IP addresses
                - ip_count: Number of unique IPs
                - nearby_hosts: Hosts found in nearby IP ranges
                - nearby_count: Number of nearby hosts
                - dns_servers: DNS servers used
                - ip_ranges: Discovered IP ranges
                - raw_output: Original stdout
                - stderr: Original stderr
                - returncode: Command return code
        """
        subdomains = []
        ip_addresses = set()
        nearby_hosts = []
        dns_servers = []
        ip_ranges = []

        lines = stdout.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # DNS servers
            if 'NS:' in line:
                ns_match = re.search(r'NS:\s+([\w\.-]+)', line)
                if ns_match:
                    dns_servers.append(ns_match.group(1))

            # Subdomain with IP
            # Format: subdomain.example.com - A: 1.2.3.4
            subdomain_match = re.search(r'^([\w\.-]+)\s+-\s+(?:A|AAAA):\s+([\d\.:a-fA-F]+)', line)
            if subdomain_match:
                subdomain = subdomain_match.group(1)
                ip = subdomain_match.group(2)
                subdomains.append({
                    'subdomain': subdomain,
                    'ip': ip
                })
                ip_addresses.add(ip)

            # Nearby hosts (found during IP traversal)
            if 'Nearby' in line or 'Found' in line:
                nearby_match = re.search(r'([\w\.-]+)\s+-\s+([\d\.]+)', line)
                if nearby_match:
                    nearby_hosts.append({
                        'hostname': nearby_match.group(1),
                        'ip': nearby_match.group(2)
                    })

            # IP ranges
            range_match = re.search(r'(\d+\.\d+\.\d+\.\d+/\d+)', line)
            if range_match:
                ip_ranges.append(range_match.group(1))

        return {
            "subdomains": subdomains,
            "subdomain_count": len(subdomains),
            "ip_addresses": sorted(list(ip_addresses)),
            "ip_count": len(ip_addresses),
            "nearby_hosts": nearby_hosts,
            "nearby_count": len(nearby_hosts),
            "dns_servers": dns_servers,
            "dns_server_count": len(dns_servers),
            "ip_ranges": list(set(ip_ranges)),
            "range_count": len(set(ip_ranges)),
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
