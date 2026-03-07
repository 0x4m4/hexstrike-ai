"""
Dirsearch tool implementation for directory and file discovery
"""
from typing import Dict, Any, List
from tools.base import BaseTool
import re


class DirsearchTool(BaseTool):
    """Dirsearch - Advanced directory and file brute-forcing tool"""

    def __init__(self):
        super().__init__("Dirsearch", "dirsearch")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build dirsearch command with comprehensive options

        Args:
            target: Target URL to scan
            params: Dictionary containing:
                - extensions: File extensions to search (e.g., "php,html,js")
                - wordlist: Custom wordlist path
                - threads: Number of threads (default: 30)
                - recursive: Enable recursive scanning
                - exclude_status: Status codes to exclude (e.g., "404,403")
                - timeout: Request timeout in seconds
                - delay: Delay between requests in milliseconds
                - random_agent: Use random user agent
                - follow_redirects: Follow redirects
                - additional_args: Additional command-line arguments

        Returns:
            List of command arguments
        """
        cmd_parts = ["dirsearch", "-u", target]

        # Extensions
        extensions = params.get("extensions", "php,html,js,txt")
        if extensions:
            cmd_parts.extend(["-e", extensions])

        # Wordlist
        if params.get("wordlist"):
            cmd_parts.extend(["-w", params["wordlist"]])

        # Threads
        threads = params.get("threads", 30)
        cmd_parts.extend(["-t", str(threads)])

        # Recursive scanning
        if params.get("recursive", False):
            cmd_parts.append("-r")
            if params.get("recursion_depth"):
                cmd_parts.extend(["--recursion-depth", str(params["recursion_depth"])])

        # Exclude status codes
        if params.get("exclude_status"):
            cmd_parts.extend(["-x", params["exclude_status"]])

        # Timeout
        if params.get("timeout"):
            cmd_parts.extend(["--timeout", str(params["timeout"])])

        # Delay
        if params.get("delay"):
            cmd_parts.extend(["--delay", str(params["delay"])])

        # Random user agent
        if params.get("random_agent", False):
            cmd_parts.append("--random-agent")

        # Follow redirects
        if params.get("follow_redirects", False):
            cmd_parts.append("--follow-redirects")

        # Output format (JSON for better parsing)
        cmd_parts.extend(["--format", "plain"])

        # Additional arguments
        additional_args = params.get("additional_args", "")
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse dirsearch output to extract discovered paths and status codes

        Args:
            stdout: Command standard output
            stderr: Command standard error
            returncode: Command return code

        Returns:
            Dictionary containing:
                - discovered_paths: List of discovered paths with details
                - path_count: Total number of discovered paths
                - status_code_summary: Count of paths per status code
                - interesting_files: Paths that might be of special interest
                - raw_output: Original stdout
                - stderr: Original stderr
                - returncode: Command return code
        """
        discovered_paths = []
        status_code_summary = {}
        interesting_files = []

        # Common interesting file extensions
        interesting_extensions = ['.config', '.backup', '.bak', '.old', '.sql',
                                 '.db', '.env', '.git', '.svn', '.zip', '.tar.gz']

        interesting_files_list = ['admin', 'login', 'config', 'backup', 'database',
                                 'phpinfo', 'test', 'debug', 'api', 'upload']

        # Parse output lines
        # Dirsearch format: [TIME] STATUS - SIZE - URL
        for line in stdout.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Match dirsearch output pattern
            # Example: [12:34:56] 200 -  1234B  - /admin/login.php
            match = re.search(r'\[[\d:]+\]\s+(\d+)\s+-\s+([\d\.]+[KMB]?)\s+-\s+(.+)', line)
            if match:
                status_code = match.group(1)
                size = match.group(2)
                path = match.group(3).strip()

                path_info = {
                    "path": path,
                    "status_code": int(status_code),
                    "size": size
                }
                discovered_paths.append(path_info)

                # Count status codes
                status_code_summary[status_code] = status_code_summary.get(status_code, 0) + 1

                # Check for interesting files
                path_lower = path.lower()
                if any(ext in path_lower for ext in interesting_extensions):
                    interesting_files.append(path_info)
                elif any(keyword in path_lower for keyword in interesting_files_list):
                    interesting_files.append(path_info)

        return {
            "discovered_paths": discovered_paths,
            "path_count": len(discovered_paths),
            "status_code_summary": status_code_summary,
            "interesting_files": interesting_files,
            "interesting_count": len(interesting_files),
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
