"""
Amass Tool Implementation
Subdomain enumeration and asset discovery
"""

from typing import Dict, List, Any
from ..base import BaseTool


class AmassTool(BaseTool):
    """
    Amass subdomain enumeration tool.

    Comprehensive attack surface mapping and asset discovery.
    """

    def __init__(self):
        """Initialize Amass tool."""
        super().__init__("Amass", "amass")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build amass command with scan options.

        Args:
            target: Target domain
            params: Dictionary containing:
                - additional_args: Additional amass arguments

        Returns:
            List of command arguments
        """
        cmd_parts = [self.binary_name]

        # Add enum subcommand
        cmd_parts.append('enum')

        # Add target domain
        cmd_parts.extend(['-d', target])

        # Add any additional arguments
        additional_args = params.get('additional_args', '')
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """Parse amass output."""
        return {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
