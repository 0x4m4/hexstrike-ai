"""
Katana Tool Implementation
Web crawler
"""

from typing import Dict, List, Any
from ..base import BaseTool


class KatanaTool(BaseTool):
    """
    Katana web crawling tool.

    Fast web crawler for discovering endpoints and URLs.
    """

    def __init__(self):
        """Initialize Katana tool."""
        super().__init__("Katana", "katana")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build katana command with scan options.

        Args:
            target: Target URL
            params: Dictionary containing:
                - additional_args: Additional katana arguments

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
        """Parse katana output."""
        return {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
