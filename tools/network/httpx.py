"""
HTTPX Tool Implementation
HTTP toolkit
"""

from typing import Dict, List, Any
from ..base import BaseTool


class HttpxTool(BaseTool):
    """
    HTTPX HTTP toolkit.

    Fast and multi-purpose HTTP toolkit for various tasks.
    """

    def __init__(self):
        """Initialize HTTPX tool."""
        super().__init__("HTTPX", "httpx")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build httpx command with scan options.

        Args:
            target: Target URL or domain
            params: Dictionary containing:
                - additional_args: Additional httpx arguments

        Returns:
            List of command arguments (using echo pipe pattern)
        """
        # HTTPX typically uses echo piping pattern
        additional_args = params.get('additional_args', '-tech-detect -status-code')

        # Handle None additional_args
        if additional_args is None:
            additional_args = '-tech-detect -status-code'

        # Return as shell command components that will be joined
        # Pattern: echo target | httpx args
        return ['echo', target, '|', 'httpx'] + additional_args.split()

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """Parse httpx output."""
        return {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
