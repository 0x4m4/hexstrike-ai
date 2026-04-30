"""
Dalfox Tool Implementation
XSS vulnerability scanner
"""

from typing import Dict, List, Any
from ..base import BaseTool


class DalfoxTool(BaseTool):
    """
    Dalfox XSS vulnerability scanner.

    Fast and powerful XSS scanner and parameter analysis tool.
    """

    def __init__(self):
        """Initialize Dalfox tool."""
        super().__init__("Dalfox", "dalfox")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build dalfox command with scan options.

        Args:
            target: Target URL
            params: Dictionary containing:
                - additional_args: Additional dalfox arguments

        Returns:
            List of command arguments
        """
        cmd_parts = [self.binary_name]

        # Dalfox uses 'url' subcommand
        cmd_parts.append('url')
        cmd_parts.append(target)

        # Add any additional arguments
        additional_args = params.get('additional_args', '')
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """Parse dalfox output."""
        return {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
