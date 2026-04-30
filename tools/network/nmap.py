"""
Nmap Tool Implementation
Network port scanner
"""

from typing import Dict, List, Any
from ..base import BaseTool


class NmapTool(BaseTool):
    """
    Nmap network scanner tool.

    Supports various scan types and port specifications.

    Example usage:
        tool = NmapTool()
        result = tool.execute('192.168.1.1', {
            'scan_type': '-sV',
            'ports': '80,443',
            'additional_args': '-O'
        }, execute_command)
    """

    def __init__(self):
        """Initialize Nmap tool."""
        super().__init__("Nmap", "nmap")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build nmap command with scan options.

        Args:
            target: Target IP address, hostname, or network
            params: Dictionary containing:
                - scan_type: Scan type flag (default: '-sV')
                - ports: Port specification (e.g., '80,443', '1-1000')
                - additional_args: Additional nmap arguments

        Returns:
            List of command arguments

        Example:
            >>> tool.build_command('example.com', {'scan_type': '-sS', 'ports': '80,443'})
            ['nmap', '-sS', '-p', '80,443', 'example.com']
        """
        cmd_parts = [self.binary_name]

        # Add scan type (default to service version detection)
        scan_type = params.get('scan_type', '-sV')
        cmd_parts.append(scan_type)

        # Add port specification if provided
        ports = params.get('ports', '')
        if ports:
            cmd_parts.extend(['-p', ports])

        # Add any additional arguments
        additional_args = params.get('additional_args', '')
        if additional_args:
            cmd_parts.extend(additional_args.split())

        # Add target last
        cmd_parts.append(target)

        return cmd_parts

    def validate_params(self, params: Dict[str, Any]) -> None:
        """
        Validate nmap parameters.

        Args:
            params: Parameters to validate

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate scan type if provided
        scan_type = params.get('scan_type', '-sV')
        valid_scan_types = [
            '-sS', '-sT', '-sU', '-sV', '-sA', '-sW', '-sM',
            '-sN', '-sF', '-sX', '-sO', '-sY', '-sZ'
        ]

        if scan_type and not any(scan_type.startswith(st) for st in valid_scan_types):
            # Allow it but log a warning - nmap has many scan types
            pass

        # Validate ports format if provided (basic validation)
        ports = params.get('ports', '')
        if ports:
            # Basic check - should contain only digits, commas, hyphens
            if not all(c.isdigit() or c in ',-' for c in ports):
                raise ValueError(f"Invalid port specification: {ports}")

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse nmap output.

        Note: This is a basic implementation that returns raw output.
        For advanced parsing, consider using python-nmap or custom parser.

        Args:
            stdout: Nmap standard output
            stderr: Nmap standard error
            returncode: Process return code

        Returns:
            Dictionary containing parsed results
        """
        # Basic parsing - extract key information
        result = {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }

        # Try to extract basic information
        lines = stdout.split('\n')

        # Extract host information
        for line in lines:
            if 'Nmap scan report for' in line:
                result['scan_target'] = line.split('Nmap scan report for ')[-1].strip()
                break

        # Count open ports
        open_ports = []
        for line in lines:
            if '/tcp' in line and 'open' in line:
                parts = line.split()
                if parts:
                    port_info = parts[0]
                    if '/' in port_info:
                        port_num = port_info.split('/')[0]
                        open_ports.append(port_num)

        if open_ports:
            result['open_ports'] = open_ports
            result['open_ports_count'] = len(open_ports)

        return result
