"""
WPScan Tool Implementation
WordPress vulnerability scanner
"""

from typing import Dict, List, Any
from ..base import BaseTool


class WpscanTool(BaseTool):
    """
    WPScan WordPress vulnerability scanner.

    Detects WordPress vulnerabilities, plugins, themes, and users.
    """

    def __init__(self):
        """Initialize WPScan tool."""
        super().__init__("WPScan", "wpscan")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build wpscan command with scan options.

        Args:
            target: Target WordPress URL
            params: Dictionary containing:
                - additional_args: Additional wpscan arguments

        Returns:
            List of command arguments
        """
        cmd_parts = [self.binary_name]

        # Add target URL
        cmd_parts.extend(['--url', target])

        # Add any additional arguments (default: enumerate plugins, themes, users)
        additional_args = params.get('additional_args', '--enumerate p,t,u')
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """Parse wpscan output."""
        return {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
