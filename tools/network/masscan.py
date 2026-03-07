"""
Masscan Tool Implementation
High-speed port scanner
"""

from typing import Dict, List, Any
from ..base import BaseTool


class MasscanTool(BaseTool):
    """
    Masscan high-speed port scanner.

    Extremely fast port scanner capable of scanning the entire Internet.
    """

    def __init__(self):
        """Initialize Masscan tool."""
        super().__init__("Masscan", "masscan")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build masscan command with scan options.

        Args:
            target: Target IP or CIDR range
            params: Dictionary containing:
                - ports: Port range to scan (default: 0-65535)
                - rate: Scan rate (default: 1000)
                - additional_args: Additional masscan arguments

        Returns:
            List of command arguments
        """
        cmd_parts = [self.binary_name]

        # Add target
        cmd_parts.append(target)

        # Add port range
        ports = params.get('ports', '0-65535')
        cmd_parts.extend(['-p', ports])

        # Add scan rate
        rate = params.get('rate', '1000')
        cmd_parts.extend(['--rate', str(rate)])

        # Add any additional arguments
        additional_args = params.get('additional_args', '')
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """Parse masscan output."""
        return {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
