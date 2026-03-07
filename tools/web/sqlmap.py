"""
SQLMap Tool Implementation
Automated SQL injection and database takeover tool
"""

from typing import Dict, List, Any
from ..base import BaseTool


class SQLMapTool(BaseTool):
    """
    SQLMap automated SQL injection tool.

    Supports various injection techniques and database enumeration.

    Example usage:
        tool = SQLMapTool()
        result = tool.execute('https://example.com/page?id=1', {
            'additional_args': '--batch --dbs'
        }, execute_command)
    """

    def __init__(self):
        """Initialize SQLMap tool."""
        super().__init__("SQLMap", "sqlmap")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build sqlmap command with scan options.

        Args:
            target: Target URL with parameters
            params: Dictionary containing:
                - additional_args: Additional sqlmap arguments (default: '--batch --random-agent')

        Returns:
            List of command arguments

        Example:
            >>> tool.build_command('example.com/page?id=1', {})
            ['sqlmap', '-u', 'example.com/page?id=1', '--batch', '--random-agent']
        """
        cmd_parts = [self.binary_name, '-u', target]

        # Add additional arguments (default includes batch mode and random agent)
        additional_args = params.get('additional_args', '--batch --random-agent')
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse sqlmap output.

        Args:
            stdout: SQLMap standard output
            stderr: SQLMap standard error
            returncode: Process return code

        Returns:
            Dictionary containing parsed results
        """
        result = {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }

        # Check for SQL injection vulnerabilities
        lines = stdout.split('\n')

        # Look for key indicators
        is_vulnerable = False
        databases = []
        injection_type = None

        for line in lines:
            if 'sqlmap identified the following injection' in line.lower():
                is_vulnerable = True
            if 'Type:' in line:
                injection_type = line.strip()
            if 'available databases' in line.lower():
                # Next lines might contain database names
                pass

        result['is_vulnerable'] = is_vulnerable
        if injection_type:
            result['injection_type'] = injection_type

        return result
