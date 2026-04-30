"""
DNSenum tool implementation for DNS enumeration and reconnaissance
"""
from typing import Dict, Any, List
from tools.base import BaseTool
import re


class DNSEnumTool(BaseTool):
    """DNSenum - Multithreaded perl script to enumerate DNS information"""

    def __init__(self):
        super().__init__("DNSenum", "dnsenum")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build dnsenum command with comprehensive options

        Args:
            target: Target domain to enumerate
            params: Dictionary containing:
                - threads: Number of threads for subdomain brute forcing
                - dnsserver: DNS server to use for queries
                - enum: Shortcut for --threads 5 -s 15 -w
                - noreverse: Skip reverse lookups
                - private: Show private IP addresses
                - subfile: File containing subdomain list
                - timeout: TCP and UDP timeout value
                - pages: Number of Google search pages to process
                - scrap: Number of results to process
                - additional_args: Additional command-line arguments

        Returns:
            List of command arguments
        """
        cmd_parts = ["dnsenum"]

        # Threads for subdomain brute forcing
        if params.get("threads"):
            cmd_parts.extend(["--threads", str(params["threads"])])

        # DNS server
        if params.get("dnsserver"):
            cmd_parts.extend(["--dnsserver", params["dnsserver"]])

        # Enum mode (shortcut)
        if params.get("enum", False):
            cmd_parts.append("--enum")

        # Skip reverse lookups
        if params.get("noreverse", False):
            cmd_parts.append("--noreverse")

        # Show private IPs
        if params.get("private", False):
            cmd_parts.append("--private")

        # Subdomain list file
        if params.get("subfile"):
            cmd_parts.extend(["-f", params["subfile"]])

        # Timeout
        if params.get("timeout"):
            cmd_parts.extend(["--timeout", str(params["timeout"])])

        # Google search pages
        if params.get("pages"):
            cmd_parts.extend(["-p", str(params["pages"])])

        # Results to scrape
        if params.get("scrap"):
            cmd_parts.extend(["-s", str(params["scrap"])])

        # Additional arguments
        additional_args = params.get("additional_args", "")
        if additional_args:
            cmd_parts.extend(additional_args.split())

        # Target domain
        cmd_parts.append(target)

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse dnsenum output to extract DNS information

        Args:
            stdout: Command standard output
            stderr: Command standard error
            returncode: Command return code

        Returns:
            Dictionary containing:
                - name_servers: List of name servers
                - mail_servers: List of mail servers
                - hosts: List of discovered hosts with IPs
                - subdomains: List of discovered subdomains
                - zone_transfer: Whether zone transfer was successful
                - dns_records: Dictionary of DNS records by type
                - ip_addresses: List of unique IP addresses
                - raw_output: Original stdout
                - stderr: Original stderr
                - returncode: Command return code
        """
        name_servers = []
        mail_servers = []
        hosts = []
        subdomains = []
        zone_transfer = False
        dns_records = {
            'A': [],
            'AAAA': [],
            'MX': [],
            'NS': [],
            'TXT': [],
            'CNAME': []
        }
        ip_addresses = set()

        lines = stdout.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Name servers
            if 'Name Servers:' in line or re.search(r'NS\s+[\w\.-]+', line):
                ns_match = re.search(r'([\w\.-]+)\s+\d+\.\d+\.\d+\.\d+', line)
                if ns_match:
                    name_servers.append(ns_match.group(1))
                    dns_records['NS'].append(line)

            # Mail servers
            if 'Mail (MX) Servers:' in line or re.search(r'MX\s+', line):
                mx_match = re.search(r'([\w\.-]+)\s+\d+\.\d+\.\d+\.\d+', line)
                if mx_match:
                    mail_servers.append(mx_match.group(1))
                    dns_records['MX'].append(line)

            # Zone transfer
            if 'Trying Zone Transfer' in line or 'Zone transfer successful' in line.lower():
                zone_transfer = True

            # Host entries with IP addresses
            ip_match = re.search(r'([\w\.-]+)\s+(\d+\.\d+\.\d+\.\d+)', line)
            if ip_match:
                hostname = ip_match.group(1)
                ip = ip_match.group(2)
                hosts.append({
                    'hostname': hostname,
                    'ip': ip
                })
                ip_addresses.add(ip)
                subdomains.append(hostname)

            # A records
            if re.search(r'\s+A\s+', line):
                dns_records['A'].append(line)

            # AAAA records
            if re.search(r'\s+AAAA\s+', line):
                dns_records['AAAA'].append(line)

            # CNAME records
            if re.search(r'\s+CNAME\s+', line):
                dns_records['CNAME'].append(line)

            # TXT records
            if re.search(r'\s+TXT\s+', line):
                dns_records['TXT'].append(line)

        return {
            "name_servers": name_servers,
            "ns_count": len(name_servers),
            "mail_servers": mail_servers,
            "mx_count": len(mail_servers),
            "hosts": hosts,
            "host_count": len(hosts),
            "subdomains": list(set(subdomains)),
            "subdomain_count": len(set(subdomains)),
            "zone_transfer": zone_transfer,
            "dns_records": dns_records,
            "ip_addresses": sorted(list(ip_addresses)),
            "ip_count": len(ip_addresses),
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
