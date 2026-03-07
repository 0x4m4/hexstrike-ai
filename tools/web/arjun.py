"""
Arjun Tool Implementation
HTTP parameter discovery
"""

from typing import Dict, List, Any
from ..base import BaseTool


class ArjunTool(BaseTool):
    """
    Arjun HTTP parameter discovery tool.

    Discovers hidden HTTP parameters in web applications.
    """

    def __init__(self):
        """Initialize Arjun tool."""
        super().__init__("Arjun", "arjun")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build arjun command with scan options.

        Args:
            target: Target URL
            params: Dictionary containing:
                - additional_args: Additional arjun arguments

        Returns:
            List of command arguments
        """
        cmd_parts = [self.binary_name]

        # Add target URL
        cmd_parts.extend(['-u', target])

        # Add any additional arguments
        additional_args = params.get('additional_args', '')
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """Parse arjun output."""
        return {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
