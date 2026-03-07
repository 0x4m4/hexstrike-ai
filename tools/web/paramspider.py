"""
ParamSpider tool implementation for parameter mining and discovery
"""
from typing import Dict, Any, List
from tools.base import BaseTool
import re
from urllib.parse import urlparse, parse_qs


class ParamSpiderTool(BaseTool):
    """ParamSpider - Mining parameters from dark corners of web archives"""

    def __init__(self):
        super().__init__("ParamSpider", "paramspider")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build paramspider command with comprehensive options

        Args:
            target: Target domain to mine parameters from
            params: Dictionary containing:
                - level: Crawl level depth (default: 2)
                - exclude: Extensions to exclude (e.g., "png,jpg,gif")
                - output: Output file path
                - placeholder: Placeholder for parameter values
                - stream: Stream mode for real-time results
                - additional_args: Additional command-line arguments

        Returns:
            List of command arguments
        """
        cmd_parts = ["paramspider", "-d", target]

        # Level (crawl depth)
        level = params.get("level", 2)
        cmd_parts.extend(["-l", str(level)])

        # Exclude extensions
        if params.get("exclude"):
            cmd_parts.extend(["--exclude", params["exclude"]])

        # Output file
        if params.get("output"):
            cmd_parts.extend(["-o", params["output"]])

        # Placeholder for parameter values
        if params.get("placeholder"):
            cmd_parts.extend(["--placeholder", params["placeholder"]])

        # Stream mode
        if params.get("stream", False):
            cmd_parts.append("-s")

        # Additional arguments
        additional_args = params.get("additional_args", "")
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse paramspider output to extract discovered parameters and URLs

        Args:
            stdout: Command standard output
            stderr: Command standard error
            returncode: Command return code

        Returns:
            Dictionary containing:
                - parameters: List of discovered unique parameters
                - parameter_count: Total number of unique parameters
                - urls_with_params: List of URLs containing parameters
                - url_count: Total number of URLs discovered
                - parameter_frequency: Dictionary of parameter names and their occurrence count
                - interesting_params: Parameters that might be of special interest
                - raw_output: Original stdout
                - stderr: Original stderr
                - returncode: Command return code
        """
        parameters = set()
        urls_with_params = []
        parameter_frequency = {}

        # Interesting parameter names that might indicate vulnerabilities
        interesting_param_names = [
            'id', 'user', 'admin', 'debug', 'test', 'file', 'path', 'url', 'redirect',
            'next', 'callback', 'return', 'page', 'template', 'theme', 'lang', 'locale',
            'cmd', 'exec', 'command', 'query', 'search', 'keyword', 'email', 'password',
            'token', 'api', 'key', 'secret', 'auth', 'session', 'cookie'
        ]

        interesting_params = []

        # Parse URLs from output
        for line in stdout.split('\n'):
            line = line.strip()
            if not line or not line.startswith('http'):
                continue

            urls_with_params.append(line)

            # Parse URL to extract parameters
            try:
                parsed_url = urlparse(line)
                query_params = parse_qs(parsed_url.query)

                for param_name in query_params.keys():
                    parameters.add(param_name)

                    # Count parameter frequency
                    parameter_frequency[param_name] = parameter_frequency.get(param_name, 0) + 1

                    # Check if parameter is interesting
                    if param_name.lower() in interesting_param_names:
                        if param_name not in [p['parameter'] for p in interesting_params]:
                            interesting_params.append({
                                'parameter': param_name,
                                'url': line,
                                'reason': 'Common vulnerable parameter name'
                            })

            except Exception as e:
                # Skip malformed URLs
                continue

        # Sort parameters alphabetically
        sorted_parameters = sorted(list(parameters))

        # Sort parameter frequency by count (descending)
        sorted_frequency = dict(sorted(parameter_frequency.items(),
                                      key=lambda x: x[1], reverse=True))

        return {
            "parameters": sorted_parameters,
            "parameter_count": len(parameters),
            "urls_with_params": urls_with_params,
            "url_count": len(urls_with_params),
            "parameter_frequency": sorted_frequency,
            "interesting_params": interesting_params,
            "interesting_count": len(interesting_params),
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
