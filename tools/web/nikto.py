"""
Nikto Tool Implementation
Web server scanner for security issues
"""

from typing import Dict, List, Any
from ..base import BaseTool


class NiktoTool(BaseTool):
    """
    Nikto web server scanner.

    Scans web servers for dangerous files, outdated software, and security issues.

    Example usage:
        tool = NiktoTool()
        result = tool.execute('https://example.com', {
            'additional_args': '-ssl'
        }, execute_command)
    """

    def __init__(self):
        """Initialize Nikto tool."""
        super().__init__("Nikto", "nikto")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build nikto command with scan options.

        Args:
            target: Target host or URL
            params: Dictionary containing:
                - additional_args: Additional nikto arguments

        Returns:
            List of command arguments

        Example:
            >>> tool.build_command('example.com', {})
            ['nikto', '-h', 'example.com']
        """
        cmd_parts = [self.binary_name, '-h', target]

        # Add any additional arguments
        additional_args = params.get('additional_args', '')
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse nikto output.

        Args:
            stdout: Nikto standard output
            stderr: Nikto standard error
            returncode: Process return code

        Returns:
            Dictionary containing parsed results
        """
        result = {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }

        # Parse findings
        lines = stdout.split('\n')
        findings = []
        target_info = None

        for line in lines:
            if '+ Target' in line:
                target_info = line.strip()
            elif line.strip().startswith('+') and len(line.strip()) > 2:
                # Nikto findings typically start with +
                findings.append(line.strip())

        if target_info:
            result['target_info'] = target_info

        if findings:
            result['findings'] = findings
            result['findings_count'] = len(findings)

        return result
