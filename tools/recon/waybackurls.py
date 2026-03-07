"""
Waybackurls tool implementation for fetching URLs from web archives
"""
from typing import Dict, Any, List
from tools.base import BaseTool
import re
from urllib.parse import urlparse


class WaybackURLsTool(BaseTool):
    """Waybackurls - Fetch all URLs that the Wayback Machine knows about for a domain"""

    def __init__(self):
        super().__init__("Wayback URLs", "waybackurls")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build waybackurls command with comprehensive options

        Args:
            target: Target domain to fetch archived URLs
            params: Dictionary containing:
                - get_versions: Fetch all versions of URLs (default: False)
                - no_subs: Don't include subdomains (default: False)
                - dates: Include timestamps in output
                - additional_args: Additional command-line arguments

        Returns:
            List of command arguments
        """
        # waybackurls reads from stdin, so we need to echo the domain
        cmd_parts = ["echo", target, "|", "waybackurls"]

        # Get all versions
        if params.get("get_versions", False):
            cmd_parts.append("--get-versions")

        # No subdomains
        if params.get("no_subs", False):
            cmd_parts.append("--no-subs")

        # Include dates
        if params.get("dates", False):
            cmd_parts.append("--dates")

        # Additional arguments
        additional_args = params.get("additional_args", "")
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse waybackurls output to extract and categorize URLs

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
                - urls_by_extension: URLs categorized by file extension
                - urls_by_path_depth: URLs categorized by path depth
                - interesting_urls: URLs that might be of special interest
                - subdomains: List of discovered subdomains
                - raw_output: Original stdout
                - stderr: Original stderr
                - returncode: Command return code
        """
        urls = []
        unique_urls = set()
        urls_by_extension = {}
        urls_by_path_depth = {}
        interesting_urls = []
        subdomains = set()

        # Interesting patterns
        interesting_patterns = [
            r'admin', r'login', r'config', r'backup', r'\.env', r'\.git',
            r'api', r'debug', r'test', r'\.sql', r'\.db', r'upload',
            r'password', r'secret', r'key', r'token', r'auth'
        ]

        # Interesting extensions
        interesting_extensions = [
            '.sql', '.db', '.backup', '.bak', '.old', '.config', '.env',
            '.git', '.svn', '.zip', '.tar', '.gz', '.rar', '.7z'
        ]

        for line in stdout.split('\n'):
            line = line.strip()
            if not line or not line.startswith('http'):
                continue

            urls.append(line)
            unique_urls.add(line)

            try:
                parsed = urlparse(line)

                # Extract subdomain
                if parsed.netloc:
                    subdomains.add(parsed.netloc)

                # Categorize by extension
                path = parsed.path
                if '.' in path:
                    ext = '.' + path.split('.')[-1].lower()
                    if ext not in urls_by_extension:
                        urls_by_extension[ext] = []
                    urls_by_extension[ext].append(line)

                # Categorize by path depth
                path_depth = len([p for p in path.split('/') if p])
                depth_key = f"depth_{path_depth}"
                if depth_key not in urls_by_path_depth:
                    urls_by_path_depth[depth_key] = []
                urls_by_path_depth[depth_key].append(line)

                # Check for interesting URLs
                line_lower = line.lower()
                for pattern in interesting_patterns:
                    if re.search(pattern, line_lower):
                        interesting_urls.append({
                            'url': line,
                            'reason': f'Matches pattern: {pattern}'
                        })
                        break

                # Check for interesting extensions
                for ext in interesting_extensions:
                    if line_lower.endswith(ext):
                        interesting_urls.append({
                            'url': line,
                            'reason': f'Interesting extension: {ext}'
                        })
                        break

            except Exception:
                # Skip malformed URLs
                continue

        # Get extension statistics
        extension_stats = {ext: len(url_list) for ext, url_list in urls_by_extension.items()}
        extension_stats = dict(sorted(extension_stats.items(), key=lambda x: x[1], reverse=True))

        return {
            "urls": urls,
            "url_count": len(urls),
            "unique_urls": list(unique_urls),
            "unique_count": len(unique_urls),
            "urls_by_extension": urls_by_extension,
            "extension_stats": extension_stats,
            "urls_by_path_depth": urls_by_path_depth,
            "interesting_urls": interesting_urls,
            "interesting_count": len(interesting_urls),
            "subdomains": sorted(list(subdomains)),
            "subdomain_count": len(subdomains),
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
