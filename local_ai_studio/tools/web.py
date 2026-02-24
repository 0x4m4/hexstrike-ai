"""
Web and API tools for research and data gathering.

Provides URL fetching, web scraping, and API call capabilities
with configurable URL filtering and response size limits.
"""

import json
from typing import Any, Optional
from urllib.parse import urlparse

from local_ai_studio.config import StudioConfig
from local_ai_studio.tools.executor import ToolDefinition


def _check_url_allowed(url: str, config: StudioConfig) -> Optional[str]:
    """Check if a URL is allowed by configuration. Returns error message or None."""
    web_cfg = config.get("tools.web", {})
    allow = web_cfg.get("allow_urls", ["*"])
    block = web_cfg.get("block_urls", [])

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    for pattern in block:
        if pattern in domain or pattern == url:
            return f"URL blocked by configuration: {url}"

    if "*" not in allow:
        if not any(pattern in domain for pattern in allow):
            return f"URL not in allowlist: {url}"

    return None


def create_web_fetch_tool(config: StudioConfig) -> ToolDefinition:
    def fetch_url(url: str, headers: Optional[dict] = None) -> str:
        error = _check_url_allowed(url, config)
        if error:
            return f"[Denied] {error}"
        try:
            import requests
            web_cfg = config.get("tools.web", {})
            timeout = web_cfg.get("timeout", 30)
            max_size = web_cfg.get("max_response_size_mb", 10) * 1024 * 1024

            resp = requests.get(
                url,
                headers=headers or {"User-Agent": "LocalAIStudio/1.0"},
                timeout=timeout,
                stream=True,
            )
            resp.raise_for_status()

            # Read with size limit
            content = resp.content[:max_size]
            content_type = resp.headers.get("content-type", "")

            if "json" in content_type:
                try:
                    return json.dumps(json.loads(content), indent=2)
                except json.JSONDecodeError:
                    pass

            if "html" in content_type:
                return _extract_text_from_html(content.decode("utf-8", errors="replace"))

            return content.decode("utf-8", errors="replace")

        except ImportError:
            return "[Error] requests library not installed"
        except Exception as e:
            return f"[Error] {type(e).__name__}: {e}"

    return ToolDefinition(
        name="web_fetch",
        description="Fetch content from a URL. HTML is converted to plain text.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "headers": {
                    "type": "object",
                    "description": "Optional HTTP headers",
                },
            },
            "required": ["url"],
        },
        handler=fetch_url,
        category="web",
    )


def create_api_call_tool(config: StudioConfig) -> ToolDefinition:
    def api_call(
        url: str,
        method: str = "GET",
        headers: Optional[dict] = None,
        body: Optional[str] = None,
    ) -> str:
        error = _check_url_allowed(url, config)
        if error:
            return f"[Denied] {error}"
        try:
            import requests
            web_cfg = config.get("tools.web", {})
            timeout = web_cfg.get("timeout", 30)

            kwargs: dict[str, Any] = {
                "headers": headers or {"Content-Type": "application/json"},
                "timeout": timeout,
            }
            if body and method.upper() in ("POST", "PUT", "PATCH"):
                kwargs["data"] = body

            resp = requests.request(method.upper(), url, **kwargs)

            result = {
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "body": resp.text[:50000],
            }
            return json.dumps(result, indent=2)

        except ImportError:
            return "[Error] requests library not installed"
        except Exception as e:
            return f"[Error] {type(e).__name__}: {e}"

    return ToolDefinition(
        name="api_call",
        description="Make an HTTP API call with configurable method, headers, and body.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "API endpoint URL"},
                "method": {
                    "type": "string",
                    "description": "HTTP method (GET, POST, PUT, DELETE, PATCH)",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                },
                "headers": {"type": "object", "description": "HTTP headers"},
                "body": {"type": "string", "description": "Request body (for POST/PUT/PATCH)"},
            },
            "required": ["url"],
        },
        handler=api_call,
        category="web",
    )


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Collapse multiple blank lines
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines[:500])
    except ImportError:
        # Fallback: strip tags with regex
        import re
        clean = re.sub(r"<[^>]+>", " ", html)
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()[:10000]


def register_web_tools(config: StudioConfig, executor) -> None:
    """Register all web tools with the executor."""
    executor.register(create_web_fetch_tool(config))
    executor.register(create_api_call_tool(config))
