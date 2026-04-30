"""
Subfinder Tool Implementation
Fast subdomain discovery
"""

from typing import Dict, List, Any
from ..base import BaseTool


class SubfinderTool(BaseTool):
    """
    Subfinder subdomain discovery tool.

    Fast passive subdomain enumeration using multiple sources.
    """

    def __init__(self):
        """Initialize Subfinder tool."""
        super().__init__("Subfinder", "subfinder")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build subfinder command with scan options.

        Args:
            target: Target domain
            params: Dictionary containing:
                - additional_args: Additional subfinder arguments

        Returns:
            List of command arguments
        """
        cmd_parts = [self.binary_name]

        # Add target domain
        cmd_parts.extend(['-d', target])

        # Add any additional arguments
        additional_args = params.get('additional_args', '')
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """Parse subfinder output."""
        return {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
