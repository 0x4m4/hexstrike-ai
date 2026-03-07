"""
FFUF Tool Implementation
Fast web fuzzer
"""

from typing import Dict, List, Any
from ..base import BaseTool


class FfufTool(BaseTool):
    """
    FFUF web fuzzing tool.

    Fast web fuzzer for discovering hidden directories and files.
    """

    def __init__(self):
        """Initialize FFUF tool."""
        super().__init__("FFUF", "ffuf")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build ffuf command with scan options.

        Args:
            target: Target URL (should contain FUZZ placeholder)
            params: Dictionary containing:
                - wordlist: Path to wordlist file
                - additional_args: Additional ffuf arguments

        Returns:
            List of command arguments
        """
        cmd_parts = [self.binary_name]

        # Ensure target has FUZZ placeholder
        if 'FUZZ' not in target:
            target = target.rstrip('/') + '/FUZZ'

        # Add target URL
        cmd_parts.extend(['-u', target])

        # Add wordlist
        wordlist = params.get('wordlist', '/usr/share/wordlists/dirb/common.txt')
        cmd_parts.extend(['-w', wordlist])

        # Add any additional arguments
        additional_args = params.get('additional_args', '')
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """Parse ffuf output."""
        return {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
