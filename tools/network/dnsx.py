"""
DNSx tool implementation for fast DNS toolkit and DNS resolution
"""
from typing import Dict, Any, List
from tools.base import BaseTool
import json


class DNSxTool(BaseTool):
    """DNSx - Fast and multi-purpose DNS toolkit"""

    def __init__(self):
        super().__init__("DNSx", "dnsx")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build dnsx command with comprehensive options

        Args:
            target: Target domain or list file to resolve
            params: Dictionary containing:
                - a: Query A records
                - aaaa: Query AAAA records
                - cname: Query CNAME records
                - mx: Query MX records
                - ns: Query NS records
                - txt: Query TXT records
                - ptr: Query PTR records
                - soa: Query SOA records
                - any: Query ALL DNS records
                - resp: Display response data
                - resp_only: Display response data only
                - resolver: Custom resolver file
                - threads: Number of concurrent threads
                - rate_limit: Rate limit in queries per second
                - retries: Number of retries for failed queries
                - wildcard_domain: Domain for wildcard check
                - silent: Silent mode
                - json: JSON output
                - additional_args: Additional command-line arguments

        Returns:
            List of command arguments
        """
        # dnsx reads from stdin by default, so we echo the target
        cmd_parts = ["echo", target, "|", "dnsx"]

        # Record types
        if params.get("a", False):
            cmd_parts.append("-a")
        if params.get("aaaa", False):
            cmd_parts.append("-aaaa")
        if params.get("cname", False):
            cmd_parts.append("-cname")
        if params.get("mx", False):
            cmd_parts.append("-mx")
        if params.get("ns", False):
            cmd_parts.append("-ns")
        if params.get("txt", False):
            cmd_parts.append("-txt")
        if params.get("ptr", False):
            cmd_parts.append("-ptr")
        if params.get("soa", False):
            cmd_parts.append("-soa")
        if params.get("any", False):
            cmd_parts.append("-any")

        # Response display
        if params.get("resp", False):
            cmd_parts.append("-resp")
        if params.get("resp_only", False):
            cmd_parts.append("-resp-only")

        # Custom resolver
        if params.get("resolver"):
            cmd_parts.extend(["-r", params["resolver"]])

        # Threads
        if params.get("threads"):
            cmd_parts.extend(["-t", str(params["threads"])])

        # Rate limit
        if params.get("rate_limit"):
            cmd_parts.extend(["-rl", str(params["rate_limit"])])

        # Retries
        if params.get("retries"):
            cmd_parts.extend(["-retry", str(params["retries"])])

        # Wildcard domain
        if params.get("wildcard_domain"):
            cmd_parts.extend(["-wd", params["wildcard_domain"]])

        # Silent mode
        if params.get("silent", True):
            cmd_parts.append("-silent")

        # JSON output
        if params.get("json", True):
            cmd_parts.append("-json")

        # Additional arguments
        additional_args = params.get("additional_args", "")
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse dnsx output to extract DNS resolution data

        Args:
            stdout: Command standard output
            stderr: Command standard error
            returncode: Command return code

        Returns:
            Dictionary containing:
                - records: List of DNS records
                - record_count: Total number of records
                - records_by_type: Records categorized by type
                - a_records: A record IPs
                - aaaa_records: AAAA record IPs
                - cname_records: CNAME records
                - mx_records: MX records
                - ns_records: NS records
                - txt_records: TXT records
                - raw_output: Original stdout
                - stderr: Original stderr
                - returncode: Command return code
        """
        records = []
        records_by_type = {
            'A': [],
            'AAAA': [],
            'CNAME': [],
            'MX': [],
            'NS': [],
            'TXT': [],
            'PTR': [],
            'SOA': []
        }

        a_records = []
        aaaa_records = []
        cname_records = []
        mx_records = []
        ns_records = []
        txt_records = []

        for line in stdout.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Try to parse as JSON
            try:
                record = json.loads(line)
                records.append(record)

                # Extract host and response
                host = record.get('host', '')
                record_type = record.get('type', '').upper()
                response = record.get('value', record.get('a', record.get('aaaa', '')))

                if record_type and response:
                    records_by_type[record_type].append({
                        'host': host,
                        'value': response
                    })

                # Categorize by type
                if 'a' in record and record['a']:
                    a_records.extend(record['a'] if isinstance(record['a'], list) else [record['a']])
                if 'aaaa' in record and record['aaaa']:
                    aaaa_records.extend(record['aaaa'] if isinstance(record['aaaa'], list) else [record['aaaa']])
                if 'cname' in record and record['cname']:
                    cname_records.extend(record['cname'] if isinstance(record['cname'], list) else [record['cname']])
                if 'mx' in record and record['mx']:
                    mx_records.extend(record['mx'] if isinstance(record['mx'], list) else [record['mx']])
                if 'ns' in record and record['ns']:
                    ns_records.extend(record['ns'] if isinstance(record['ns'], list) else [record['ns']])
                if 'txt' in record and record['txt']:
                    txt_records.extend(record['txt'] if isinstance(record['txt'], list) else [record['txt']])

            except json.JSONDecodeError:
                # Not JSON, parse as plain text
                # Format: domain [record_type] value
                if '[' in line and ']' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        host = parts[0]
                        record_type = parts[1].strip('[]').upper()
                        value = ' '.join(parts[2:])

                        records.append({
                            'host': host,
                            'type': record_type,
                            'value': value
                        })

                        if record_type in records_by_type:
                            records_by_type[record_type].append({
                                'host': host,
                                'value': value
                            })

        # Get statistics by type
        type_stats = {k: len(v) for k, v in records_by_type.items() if v}

        return {
            "records": records,
            "record_count": len(records),
            "records_by_type": records_by_type,
            "type_stats": type_stats,
            "a_records": list(set(a_records)),
            "a_count": len(set(a_records)),
            "aaaa_records": list(set(aaaa_records)),
            "aaaa_count": len(set(aaaa_records)),
            "cname_records": list(set(cname_records)),
            "cname_count": len(set(cname_records)),
            "mx_records": list(set(mx_records)),
            "mx_count": len(set(mx_records)),
            "ns_records": list(set(ns_records)),
            "ns_count": len(set(ns_records)),
            "txt_records": list(set(txt_records)),
            "txt_count": len(set(txt_records)),
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
