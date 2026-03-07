"""
WhatWeb Tool Implementation
Web technology identification
"""

from typing import Dict, List, Any
from ..base import BaseTool


class WhatwebTool(BaseTool):
    """
    WhatWeb web technology identification tool.

    Identifies websites, including CMS, blogging platforms, statistic/analytics packages,
    JavaScript libraries, web servers, and embedded devices.
    """

    def __init__(self):
        """Initialize WhatWeb tool."""
        super().__init__("WhatWeb", "whatweb")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build whatweb command with scan options.

        Args:
            target: Target URL or domain
            params: Dictionary containing:
                - aggression: Aggression level 1-4 (default: 1)
                - additional_args: Additional whatweb arguments

        Returns:
            List of command arguments
        """
        cmd_parts = [self.binary_name]

        # Add aggression level
        aggression = params.get('aggression', '1')
        cmd_parts.extend(['-a', str(aggression)])

        # Add target
        cmd_parts.append(target)

        # Add any additional arguments
        additional_args = params.get('additional_args', '')
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """Parse whatweb output."""
        return {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
