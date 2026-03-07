"""
x8 tool implementation for parameter discovery
"""
from typing import Dict, Any, List
from tools.base import BaseTool
import json


class X8Tool(BaseTool):
    """x8 - Hidden parameters discovery suite"""

    def __init__(self):
        super().__init__("x8", "x8")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build x8 command with comprehensive options

        Args:
            target: Target URL to test
            params: Dictionary containing:
                - wordlist: Path to wordlist file
                - method: HTTP method (GET, POST, PUT, DELETE, PATCH)
                - headers: Custom headers (format: "Header: Value")
                - body: Request body (for POST/PUT)
                - parameters: Known parameters (comma-separated)
                - parameter_template: Template for parameter value
                - max: Maximum parameters to find
                - disable_colors: Disable colored output
                - verbose: Verbose output
                - disable_cachebuster: Disable cache buster
                - encode: URL encode parameters
                - reflected_only: Only show reflected parameters
                - replay_proxy: Proxy for replaying requests
                - output: Output file
                - additional_args: Additional command-line arguments

        Returns:
            List of command arguments
        """
        cmd_parts = ["x8", "-u", target]

        # Wordlist
        wordlist = params.get("wordlist", "/usr/share/wordlists/x8/params.txt")
        cmd_parts.extend(["-w", wordlist])

        # HTTP method
        method = params.get("method", "GET")
        cmd_parts.extend(["-X", method])

        # Custom headers
        if params.get("headers"):
            headers = params["headers"] if isinstance(params["headers"], list) else [params["headers"]]
            for header in headers:
                cmd_parts.extend(["-H", header])

        # Request body
        if params.get("body"):
            cmd_parts.extend(["-b", params["body"]])

        # Known parameters
        if params.get("parameters"):
            cmd_parts.extend(["--parameters", params["parameters"]])

        # Parameter template
        if params.get("parameter_template"):
            cmd_parts.extend(["--parameter-template", params["parameter_template"]])

        # Max parameters
        if params.get("max"):
            cmd_parts.extend(["--max", str(params["max"])])

        # Disable colors
        if params.get("disable_colors", False):
            cmd_parts.append("--disable-colors")

        # Verbose
        if params.get("verbose", False):
            cmd_parts.append("-v")

        # Disable cache buster
        if params.get("disable_cachebuster", False):
            cmd_parts.append("--disable-cachebuster")

        # URL encode
        if params.get("encode", False):
            cmd_parts.append("--encode")

        # Reflected only
        if params.get("reflected_only", False):
            cmd_parts.append("--reflected-only")

        # Replay proxy
        if params.get("replay_proxy"):
            cmd_parts.extend(["--replay-proxy", params["replay_proxy"]])

        # Output file
        if params.get("output"):
            cmd_parts.extend(["-o", params["output"]])

        # JSON output for better parsing
        cmd_parts.append("--json")

        # Additional arguments
        additional_args = params.get("additional_args", "")
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse x8 output to extract discovered parameters

        Args:
            stdout: Command standard output
            stderr: Command standard error
            returncode: Command return code

        Returns:
            Dictionary containing:
                - parameters: List of discovered parameters
                - parameter_count: Number of discovered parameters
                - reflected_parameters: Parameters that reflect in response
                - get_parameters: Parameters found via GET
                - post_parameters: Parameters found via POST
                - json_parameters: Parameters found in JSON body
                - interesting_parameters: Parameters that might be exploitable
                - raw_output: Original stdout
                - stderr: Original stderr
                - returncode: Command return code
        """
        parameters = []
        reflected_parameters = []
        get_parameters = []
        post_parameters = []
        json_parameters = []
        interesting_parameters = []

        # Interesting parameter names that might indicate vulnerabilities
        interesting_names = [
            'id', 'user', 'admin', 'debug', 'test', 'file', 'path', 'url',
            'redirect', 'next', 'callback', 'return', 'cmd', 'exec', 'command',
            'query', 'search', 'email', 'password', 'token', 'api', 'key',
            'secret', 'auth', 'session', 'cookie', 'upload', 'download'
        ]

        # Try to parse JSON output
        for line in stdout.split('\n'):
            line = line.strip()
            if not line:
                continue

            try:
                # x8 with --json outputs one parameter per line as JSON
                param_data = json.loads(line)

                param_name = param_data.get('parameter', param_data.get('name', ''))
                param_type = param_data.get('type', 'unknown')
                is_reflected = param_data.get('reflected', False)

                if param_name:
                    param_info = {
                        'name': param_name,
                        'type': param_type,
                        'reflected': is_reflected
                    }
                    parameters.append(param_info)

                    # Categorize by type
                    if param_type.upper() == 'GET':
                        get_parameters.append(param_name)
                    elif param_type.upper() == 'POST':
                        post_parameters.append(param_name)
                    elif param_type.upper() == 'JSON':
                        json_parameters.append(param_name)

                    # Track reflected parameters
                    if is_reflected:
                        reflected_parameters.append(param_name)

                    # Check if interesting
                    if param_name.lower() in interesting_names:
                        interesting_parameters.append({
                            'name': param_name,
                            'type': param_type,
                            'reflected': is_reflected,
                            'reason': 'Common vulnerable parameter name'
                        })

            except json.JSONDecodeError:
                # Not JSON, try to parse plain text
                # Format: [TYPE] parameter_name (reflected)
                if '[' in line and ']' in line:
                    import re
                    match = re.search(r'\[(\w+)\]\s+(\w+)(\s+\(reflected\))?', line)
                    if match:
                        param_type = match.group(1)
                        param_name = match.group(2)
                        is_reflected = match.group(3) is not None

                        param_info = {
                            'name': param_name,
                            'type': param_type,
                            'reflected': is_reflected
                        }
                        parameters.append(param_info)

                        if is_reflected:
                            reflected_parameters.append(param_name)

                        if param_name.lower() in interesting_names:
                            interesting_parameters.append({
                                'name': param_name,
                                'type': param_type,
                                'reflected': is_reflected,
                                'reason': 'Common vulnerable parameter name'
                            })

        return {
            "parameters": parameters,
            "parameter_count": len(parameters),
            "reflected_parameters": reflected_parameters,
            "reflected_count": len(reflected_parameters),
            "get_parameters": get_parameters,
            "get_count": len(get_parameters),
            "post_parameters": post_parameters,
            "post_count": len(post_parameters),
            "json_parameters": json_parameters,
            "json_count": len(json_parameters),
            "interesting_parameters": interesting_parameters,
            "interesting_count": len(interesting_parameters),
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
