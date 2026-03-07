"""
Gobuster Tool Implementation
Directory and file brute-forcing tool
"""

from typing import Dict, List, Any
from ..base import BaseTool


class GobusterTool(BaseTool):
    """
    Gobuster directory/file/DNS brute-forcing tool.

    Supports multiple modes (dir, dns, vhost) and wordlist selection.

    Example usage:
        tool = GobusterTool()
        result = tool.execute('https://example.com', {
            'mode': 'dir',
            'wordlist': '/usr/share/wordlists/dirb/common.txt',
            'additional_args': '-x php,html'
        }, execute_command)
    """

    def __init__(self):
        """Initialize Gobuster tool."""
        super().__init__("Gobuster", "gobuster")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build gobuster command with scan options.

        Args:
            target: Target URL or domain
            params: Dictionary containing:
                - mode: Scan mode (dir, dns, vhost) (default: 'dir')
                - wordlist: Path to wordlist file (default: /usr/share/wordlists/dirb/common.txt)
                - additional_args: Additional gobuster arguments

        Returns:
            List of command arguments

        Example:
            >>> tool.build_command('example.com', {'mode': 'dir'})
            ['gobuster', 'dir', '-u', 'example.com', '-w', '/usr/share/wordlists/dirb/common.txt']
        """
        cmd_parts = [self.binary_name]

        # Add mode (dir, dns, vhost)
        mode = params.get('mode', 'dir')
        cmd_parts.append(mode)

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
        """
        Parse gobuster output.

        Args:
            stdout: Gobuster standard output
            stderr: Gobuster standard error
            returncode: Process return code

        Returns:
            Dictionary containing parsed results
        """
        result = {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }

        # Parse found directories/files
        lines = stdout.split('\n')
        found_items = []

        for line in lines:
            if line.strip() and ('Status:' in line or '/' in line):
                # Gobuster output format typically includes status codes
                found_items.append(line.strip())

        if found_items:
            result['found_items'] = found_items
            result['found_count'] = len(found_items)

        return result
