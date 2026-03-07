"""
Hakrawler tool implementation for web crawling and endpoint discovery
"""
from typing import Dict, Any, List
from tools.base import BaseTool
import re
from urllib.parse import urlparse


class HakrawlerTool(BaseTool):
    """Hakrawler - Fast web crawler for gathering URLs and endpoints"""

    def __init__(self):
        super().__init__("Hakrawler", "hakrawler")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build hakrawler command with comprehensive options

        Args:
            target: Target URL to crawl
            params: Dictionary containing:
                - depth: Crawl depth (default: 2)
                - subs: Include subdomains
                - urls: Display URLs only
                - unique: Show unique URLs only
                - insecure: Accept invalid SSL certificates
                - headers: Custom headers (format: "Header: Value")
                - cookie: Cookie to use
                - auth: Basic auth credentials (format: "user:pass")
                - timeout: Request timeout in seconds
                - forms: Extract form data
                - js: Extract JS files
                - wayback: Include Wayback Machine results
                - robots: Parse robots.txt
                - sitemap: Parse sitemap.xml
                - additional_args: Additional command-line arguments

        Returns:
            List of command arguments
        """
        cmd_parts = ["hakrawler"]

        # Depth
        depth = params.get("depth", 2)
        cmd_parts.extend(["-d", str(depth)])

        # Include subdomains
        if params.get("subs", False):
            cmd_parts.append("-s")

        # URLs only
        if params.get("urls", True):
            cmd_parts.append("-u")

        # Unique URLs
        if params.get("unique", True):
            cmd_parts.append("-uniq")

        # Accept invalid SSL
        if params.get("insecure", False):
            cmd_parts.append("-insecure")

        # Custom headers
        if params.get("headers"):
            for header in params["headers"]:
                cmd_parts.extend(["-h", header])

        # Cookie
        if params.get("cookie"):
            cmd_parts.extend(["-cookie", params["cookie"]])

        # Basic auth
        if params.get("auth"):
            cmd_parts.extend(["-auth", params["auth"]])

        # Timeout
        if params.get("timeout"):
            cmd_parts.extend(["-t", str(params["timeout"])])

        # Extract forms
        if params.get("forms", False):
            cmd_parts.append("-forms")

        # Extract JS files
        if params.get("js", True):
            cmd_parts.append("-js")

        # Wayback Machine
        if params.get("wayback", False):
            cmd_parts.append("-wayback")

        # Parse robots.txt
        if params.get("robots", True):
            cmd_parts.append("-robots")

        # Parse sitemap.xml
        if params.get("sitemap", True):
            cmd_parts.append("-sitemap")

        # Additional arguments
        additional_args = params.get("additional_args", "")
        if additional_args:
            cmd_parts.extend(additional_args.split())

        # Target URL
        cmd_parts.extend(["-url", target])

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse hakrawler output to extract endpoints and resources

        Args:
            stdout: Command standard output
            stderr: Command standard error
            returncode: Command return code

        Returns:
            Dictionary containing:
                - urls: List of all discovered URLs
                - url_count: Total number of URLs
                - endpoints: List of API/endpoint paths
                - endpoint_count: Number of endpoints
                - js_files: List of JavaScript files
                - js_count: Number of JS files
                - forms: List of discovered forms
                - form_count: Number of forms
                - external_urls: URLs pointing to external domains
                - internal_urls: URLs within the same domain
                - interesting_endpoints: Potentially interesting endpoints
                - subdomains: Discovered subdomains
                - raw_output: Original stdout
                - stderr: Original stderr
                - returncode: Command return code
        """
        urls = []
        endpoints = []
        js_files = []
        forms = []
        external_urls = []
        internal_urls = []
        interesting_endpoints = []
        subdomains = set()

        # Patterns for different resource types
        js_pattern = r'\.js(\?.*)?$'
        api_patterns = [
            r'/api/', r'/v\d+/', r'/graphql', r'/rest/', r'/ajax/',
            r'/json', r'/xml', r'/endpoint'
        ]

        # Interesting endpoint patterns
        interesting_patterns = [
            r'admin', r'login', r'auth', r'api', r'config', r'debug',
            r'test', r'upload', r'download', r'delete', r'user', r'password',
            r'token', r'key', r'secret', r'backup', r'install', r'setup'
        ]

        target_domain = None

        for line in stdout.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Handle form data (starts with 'form')
            if line.startswith('form'):
                forms.append(line)
                continue

            # Handle URLs
            if line.startswith('http'):
                urls.append(line)

                try:
                    parsed = urlparse(line)

                    # Extract domain for internal/external classification
                    if not target_domain and parsed.netloc:
                        target_domain = parsed.netloc

                    # Subdomain extraction
                    if parsed.netloc:
                        subdomains.add(parsed.netloc)

                    # Classify as internal or external
                    if target_domain:
                        if target_domain in parsed.netloc:
                            internal_urls.append(line)
                        else:
                            external_urls.append(line)

                    # JavaScript file detection
                    if re.search(js_pattern, line, re.IGNORECASE):
                        js_files.append(line)

                    # API endpoint detection
                    path = parsed.path.lower()
                    for api_pattern in api_patterns:
                        if re.search(api_pattern, path):
                            endpoints.append(line)
                            break

                    # Interesting endpoint detection
                    line_lower = line.lower()
                    for pattern in interesting_patterns:
                        if re.search(pattern, line_lower):
                            interesting_endpoints.append({
                                'url': line,
                                'reason': f'Matches pattern: {pattern}'
                            })
                            break

                except Exception:
                    # Skip malformed URLs
                    continue

        return {
            "urls": urls,
            "url_count": len(urls),
            "endpoints": endpoints,
            "endpoint_count": len(endpoints),
            "js_files": js_files,
            "js_count": len(js_files),
            "forms": forms,
            "form_count": len(forms),
            "external_urls": external_urls,
            "external_count": len(external_urls),
            "internal_urls": internal_urls,
            "internal_count": len(internal_urls),
            "interesting_endpoints": interesting_endpoints,
            "interesting_count": len(interesting_endpoints),
            "subdomains": sorted(list(subdomains)),
            "subdomain_count": len(subdomains),
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
