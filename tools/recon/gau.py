"""
GAU (GetAllURLs) tool implementation for fetching URLs from multiple sources
"""
from typing import Dict, Any, List
from tools.base import BaseTool
import re
from urllib.parse import urlparse, parse_qs


class GAUTool(BaseTool):
    """GAU - Fetch known URLs from AlienVault's OTX, Wayback Machine, Common Crawl, and URLScan"""

    def __init__(self):
        super().__init__("GAU (GetAllURLs)", "gau")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build gau command with comprehensive options

        Args:
            target: Target domain to fetch URLs
            params: Dictionary containing:
                - include_subs: Include subdomains (default: False)
                - providers: Specific providers to use (wayback,otx,commoncrawl,urlscan)
                - blacklist: Extensions to blacklist (e.g., "png,jpg,gif")
                - threads: Number of threads for crawling
                - from_date: Fetch URLs from this date onwards (YYYYMM format)
                - to_date: Fetch URLs up to this date (YYYYMM format)
                - max_retries: Maximum number of retries for failed requests
                - timeout: HTTP timeout in seconds
                - additional_args: Additional command-line arguments

        Returns:
            List of command arguments
        """
        cmd_parts = ["gau"]

        # Include subdomains
        if params.get("include_subs", False):
            cmd_parts.append("--subs")

        # Providers
        if params.get("providers"):
            cmd_parts.extend(["--providers", params["providers"]])

        # Blacklist extensions
        if params.get("blacklist"):
            cmd_parts.extend(["--blacklist", params["blacklist"]])

        # Threads
        if params.get("threads"):
            cmd_parts.extend(["--threads", str(params["threads"])])

        # Date range
        if params.get("from_date"):
            cmd_parts.extend(["--from", params["from_date"]])
        if params.get("to_date"):
            cmd_parts.extend(["--to", params["to_date"]])

        # Max retries
        if params.get("max_retries"):
            cmd_parts.extend(["--retries", str(params["max_retries"])])

        # Timeout
        if params.get("timeout"):
            cmd_parts.extend(["--timeout", str(params["timeout"])])

        # JSON output for better parsing
        cmd_parts.append("--json")

        # Additional arguments
        additional_args = params.get("additional_args", "")
        if additional_args:
            cmd_parts.extend(additional_args.split())

        # Target domain (must be last)
        cmd_parts.append(target)

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse gau output to extract and categorize URLs

        Args:
            stdout: Command standard output
            stderr: Command standard error
            returncode: Command return code

        Returns:
            Dictionary containing:
                - urls: List of all discovered URLs
                - url_count: Total number of URLs
                - unique_urls: List of unique URLs
                - unique_count: Number of unique URLs
                - urls_with_params: URLs containing query parameters
                - param_count: Number of URLs with parameters
                - parameters: Unique parameter names discovered
                - urls_by_source: URLs categorized by source (wayback, otx, etc.)
                - urls_by_extension: URLs categorized by file extension
                - interesting_urls: URLs that might be of special interest
                - subdomains: List of discovered subdomains
                - raw_output: Original stdout
                - stderr: Original stderr
                - returncode: Command return code
        """
        urls = []
        unique_urls = set()
        urls_with_params = []
        parameters = set()
        urls_by_source = {}
        urls_by_extension = {}
        interesting_urls = []
        subdomains = set()

        # Interesting patterns
        interesting_patterns = [
            r'admin', r'login', r'config', r'backup', r'\.env', r'\.git',
            r'api', r'debug', r'test', r'\.sql', r'\.db', r'upload',
            r'password', r'secret', r'key', r'token', r'auth', r'swagger',
            r'graphql', r'phpinfo', r'install', r'setup'
        ]

        # Interesting parameters
        interesting_param_names = [
            'id', 'file', 'path', 'url', 'redirect', 'next', 'callback',
            'cmd', 'exec', 'query', 'search', 'email', 'password', 'token',
            'api_key', 'secret', 'auth', 'session'
        ]

        for line in stdout.split('\n'):
            line = line.strip()
            if not line:
                continue

            # GAU with --json outputs JSON per line, but we'll also handle plain URLs
            url = line
            source = "unknown"

            # Try to parse as JSON
            try:
                import json
                data = json.loads(line)
                url = data.get('url', '')
                source = data.get('source', 'unknown')
            except:
                # Not JSON, treat as plain URL
                if not line.startswith('http'):
                    continue

            if not url:
                continue

            urls.append(url)
            unique_urls.add(url)

            # Categorize by source
            if source not in urls_by_source:
                urls_by_source[source] = []
            urls_by_source[source].append(url)

            try:
                parsed = urlparse(url)

                # Extract subdomain
                if parsed.netloc:
                    subdomains.add(parsed.netloc)

                # Check for parameters
                if parsed.query:
                    urls_with_params.append(url)
                    query_params = parse_qs(parsed.query)
                    for param_name in query_params.keys():
                        parameters.add(param_name)

                        # Check for interesting parameters
                        if param_name.lower() in interesting_param_names:
                            interesting_urls.append({
                                'url': url,
                                'reason': f'Interesting parameter: {param_name}'
                            })

                # Categorize by extension
                path = parsed.path
                if '.' in path:
                    ext = '.' + path.split('.')[-1].lower()
                    if ext not in urls_by_extension:
                        urls_by_extension[ext] = []
                    urls_by_extension[ext].append(url)

                # Check for interesting patterns
                url_lower = url.lower()
                for pattern in interesting_patterns:
                    if re.search(pattern, url_lower):
                        if url not in [u['url'] for u in interesting_urls]:
                            interesting_urls.append({
                                'url': url,
                                'reason': f'Matches pattern: {pattern}'
                            })
                        break

            except Exception:
                # Skip malformed URLs
                continue

        # Get extension statistics
        extension_stats = {ext: len(url_list) for ext, url_list in urls_by_extension.items()}
        extension_stats = dict(sorted(extension_stats.items(), key=lambda x: x[1], reverse=True))

        # Get source statistics
        source_stats = {src: len(url_list) for src, url_list in urls_by_source.items()}

        return {
            "urls": urls,
            "url_count": len(urls),
            "unique_urls": list(unique_urls),
            "unique_count": len(unique_urls),
            "urls_with_params": urls_with_params,
            "param_count": len(urls_with_params),
            "parameters": sorted(list(parameters)),
            "parameter_count": len(parameters),
            "urls_by_source": urls_by_source,
            "source_stats": source_stats,
            "urls_by_extension": urls_by_extension,
            "extension_stats": extension_stats,
            "interesting_urls": interesting_urls,
            "interesting_count": len(interesting_urls),
            "subdomains": sorted(list(subdomains)),
            "subdomain_count": len(subdomains),
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
