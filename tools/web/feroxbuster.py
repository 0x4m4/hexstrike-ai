"""
Feroxbuster Tool Implementation
Fast content discovery tool written in Rust
"""

from typing import Dict, List, Any
from ..base import BaseTool


class FeroxbusterTool(BaseTool):
    """
    Feroxbuster fast content discovery tool.

    High-performance directory/file brute-forcing with recursion support.

    Example usage:
        tool = FeroxbusterTool()
        result = tool.execute('https://example.com', {
            'wordlist': '/usr/share/wordlists/dirb/common.txt',
            'additional_args': '-x php,html -t 50'
        }, execute_command)
    """

    def __init__(self):
        """Initialize Feroxbuster tool."""
        super().__init__("Feroxbuster", "feroxbuster")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build feroxbuster command with scan options.

        Args:
            target: Target URL
            params: Dictionary containing:
                - wordlist: Path to wordlist file (default: /usr/share/wordlists/dirb/common.txt)
                - additional_args: Additional feroxbuster arguments

        Returns:
            List of command arguments

        Example:
            >>> tool.build_command('example.com', {})
            ['feroxbuster', '-u', 'example.com', '-w', '/usr/share/wordlists/dirb/common.txt']
        """
        cmd_parts = [self.binary_name, '-u', target]

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
        Parse feroxbuster output.

        Args:
            stdout: Feroxbuster standard output
            stderr: Feroxbuster standard error
            returncode: Process return code

        Returns:
            Dictionary containing parsed results
        """
        result = {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }

        # Parse discovered URLs
        lines = stdout.split('\n')
        discovered_urls = []

        for line in lines:
            if line.strip() and ('200' in line or '301' in line or '302' in line):
                # Feroxbuster shows status codes for discovered resources
                discovered_urls.append(line.strip())

        if discovered_urls:
            result['discovered_urls'] = discovered_urls
            result['discovered_count'] = len(discovered_urls)

        return result
