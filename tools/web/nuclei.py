"""
Nuclei Tool Implementation
Vulnerability scanner using community templates
"""

from typing import Dict, List, Any
from ..base import BaseTool


class NucleiTool(BaseTool):
    """
    Nuclei vulnerability scanner.

    Supports severity filtering, tag filtering, and template selection.

    Example usage:
        tool = NucleiTool()
        result = tool.execute('https://example.com', {
            'severity': 'critical,high',
            'tags': 'cve,rce',
            'additional_args': '-silent'
        }, execute_command)
    """

    def __init__(self):
        """Initialize Nuclei tool."""
        super().__init__("Nuclei", "nuclei")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build nuclei command with scan options.

        Args:
            target: Target URL or host
            params: Dictionary containing:
                - severity: Severity filter (e.g., 'critical,high')
                - tags: Template tags (e.g., 'cve,rce')
                - additional_args: Additional nuclei arguments

        Returns:
            List of command arguments

        Example:
            >>> tool.build_command('example.com', {'severity': 'critical'})
            ['nuclei', '-u', 'example.com', '-severity', 'critical']
        """
        cmd_parts = [self.binary_name, '-u', target]

        # Add severity filter if provided
        severity = params.get('severity', '')
        if severity:
            cmd_parts.extend(['-severity', severity])

        # Add tags filter if provided
        tags = params.get('tags', '')
        if tags:
            cmd_parts.extend(['-tags', tags])

        # Add any additional arguments
        additional_args = params.get('additional_args', '')
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse nuclei output.

        Args:
            stdout: Nuclei standard output
            stderr: Nuclei standard error
            returncode: Process return code

        Returns:
            Dictionary containing parsed results
        """
        result = {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }

        # Count vulnerabilities found
        lines = stdout.split('\n')
        vulnerabilities = []

        for line in lines:
            if line.strip() and '[' in line:
                # Basic parsing of nuclei output format
                vulnerabilities.append(line.strip())

        if vulnerabilities:
            result['vulnerabilities'] = vulnerabilities
            result['vulnerability_count'] = len(vulnerabilities)

        return result
