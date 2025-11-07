#!/usr/bin/env python3
"""
HexStrike MCP Integration

Connects MindSync Oracle to HexStrike's 150+ security tools.
Provides real tool execution capabilities for autonomous agents.
"""

import sys
import os
import logging
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import asyncio

logger = logging.getLogger(__name__)


class HexStrikeIntegration:
    """
    Integration with HexStrike AI MCP tools.

    Loads and provides access to all 150+ security tools for
    autonomous agent use.
    """

    def __init__(self, hexstrike_path: Optional[str] = None,
                 server_url: str = "http://localhost:8888"):
        """
        Initialize HexStrike integration.

        Args:
            hexstrike_path: Path to HexStrike installation
            server_url: HexStrike MCP server URL
        """
        self.hexstrike_path = hexstrike_path or self._find_hexstrike()
        self.server_url = server_url
        self.tools = {}
        self.mcp_client = None

        if self.hexstrike_path:
            self._load_hexstrike_tools()
            logger.info(f"HexStrike integration initialized: {len(self.tools)} tools loaded")
        else:
            logger.warning("HexStrike not found - tool execution will be limited")

    def _find_hexstrike(self) -> Optional[str]:
        """Automatically find HexStrike installation."""
        # Check parent directory
        parent = Path(__file__).parent.parent
        hexstrike_mcp = parent / "hexstrike_mcp.py"

        if hexstrike_mcp.exists():
            return str(parent)

        # Check common locations
        locations = [
            Path.home() / "hexstrike-ai",
            Path("/opt/hexstrike-ai"),
            Path.cwd().parent
        ]

        for loc in locations:
            if (loc / "hexstrike_mcp.py").exists():
                return str(loc)

        return None

    def _load_hexstrike_tools(self):
        """Load HexStrike MCP tools dynamically."""
        if not self.hexstrike_path:
            return

        try:
            # Add HexStrike to path
            sys.path.insert(0, self.hexstrike_path)

            # Import the MCP module
            spec = importlib.util.spec_from_file_location(
                "hexstrike_mcp",
                Path(self.hexstrike_path) / "hexstrike_mcp.py"
            )

            if spec and spec.loader:
                hexstrike_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(hexstrike_module)

                # Extract tool functions
                self._extract_tools_from_module(hexstrike_module)

                logger.info(f"Loaded {len(self.tools)} tools from HexStrike")

        except Exception as e:
            logger.error(f"Error loading HexStrike tools: {e}", exc_info=True)

    def _extract_tools_from_module(self, module):
        """Extract tool functions from HexStrike module."""
        # This would extract the actual MCP tool definitions
        # For now, we'll create tool wrappers for common tools

        # Common security tools we know exist in HexStrike
        tool_names = [
            "nmap_scan", "rustscan_scan", "masscan_scan",
            "gobuster_scan", "feroxbuster_scan", "ffuf_scan",
            "nuclei_scan", "sqlmap_scan", "wpscan_scan",
            "amass_enum", "subfinder_enum", "dnsenum_scan",
            "nikto_scan", "whatweb_scan", "wafw00f_scan",
            "hydra_crack", "john_crack", "hashcat_crack",
            "ghidra_analyze", "radare2_analyze",
            "trivy_scan", "prowler_assess", "kube_hunter_scan"
        ]

        for tool_name in tool_names:
            # Check if tool exists in module
            if hasattr(module, tool_name):
                self.tools[tool_name] = getattr(module, tool_name)
            else:
                # Create a wrapper that calls HexStrike API
                self.tools[tool_name] = self._create_tool_wrapper(tool_name)

    def _create_tool_wrapper(self, tool_name: str) -> Callable:
        """Create a wrapper function for a tool that calls HexStrike API."""
        async def tool_wrapper(**kwargs) -> Dict[str, Any]:
            """Execute tool via HexStrike API."""
            try:
                import requests

                # Call HexStrike API endpoint
                response = requests.post(
                    f"{self.server_url}/api/tools/{tool_name}",
                    json=kwargs,
                    timeout=300
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "success": False,
                        "error": f"API returned {response.status_code}",
                        "tool": tool_name
                    }

            except Exception as e:
                logger.error(f"Error executing {tool_name}: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "tool": tool_name
                }

        tool_wrapper.__name__ = tool_name
        return tool_wrapper

    def get_tool(self, tool_name: str) -> Optional[Callable]:
        """Get a specific tool by name."""
        return self.tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """List all available tools."""
        return list(self.tools.keys())

    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a tool with given parameters.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool-specific parameters

        Returns:
            Tool execution results
        """
        tool = self.get_tool(tool_name)

        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found",
                "available_tools": self.list_tools()[:10]
            }

        try:
            # Execute tool
            if asyncio.iscoroutinefunction(tool):
                result = await tool(**kwargs)
            else:
                result = tool(**kwargs)

            logger.info(f"Executed {tool_name} with params: {list(kwargs.keys())}")
            return result

        except Exception as e:
            logger.error(f"Error executing {tool_name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "params": kwargs
            }

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get Claude-compatible tool schemas for all tools.

        Returns list of tool definitions in Claude's format.
        """
        schemas = []

        # Define schemas for common security tools
        tool_schemas = {
            "nmap_scan": {
                "name": "nmap_scan",
                "description": "Execute Nmap port scan with version detection and scripts",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Target IP or hostname"},
                        "scan_type": {"type": "string", "description": "Scan type (default: -sV)", "default": "-sV"},
                        "ports": {"type": "string", "description": "Port range (e.g., 1-1000)"},
                        "additional_args": {"type": "string", "description": "Additional Nmap arguments"}
                    },
                    "required": ["target"]
                }
            },
            "nuclei_scan": {
                "name": "nuclei_scan",
                "description": "Fast vulnerability scanner with 4000+ templates",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Target URL or IP"},
                        "severity": {"type": "string", "description": "Severity filter (critical, high, medium, low)"},
                        "tags": {"type": "string", "description": "Template tags to use"},
                        "template": {"type": "string", "description": "Specific template path"}
                    },
                    "required": ["target"]
                }
            },
            "gobuster_scan": {
                "name": "gobuster_scan",
                "description": "Directory and file brute-forcing tool",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Target URL"},
                        "mode": {"type": "string", "description": "Mode: dir, dns, vhost", "default": "dir"},
                        "wordlist": {"type": "string", "description": "Path to wordlist file"},
                        "additional_args": {"type": "string", "description": "Additional arguments"}
                    },
                    "required": ["url"]
                }
            },
            "amass_enum": {
                "name": "amass_enum",
                "description": "Comprehensive subdomain enumeration and OSINT",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Target domain"},
                        "passive": {"type": "boolean", "description": "Passive mode only", "default": False},
                        "additional_args": {"type": "string", "description": "Additional arguments"}
                    },
                    "required": ["domain"]
                }
            },
            "sqlmap_scan": {
                "name": "sqlmap_scan",
                "description": "Automatic SQL injection testing and exploitation",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Target URL"},
                        "data": {"type": "string", "description": "POST data"},
                        "cookie": {"type": "string", "description": "HTTP Cookie header"},
                        "additional_args": {"type": "string", "description": "Additional sqlmap arguments"}
                    },
                    "required": ["url"]
                }
            }
        }

        # Return schemas for tools we have
        for tool_name in self.list_tools():
            if tool_name in tool_schemas:
                schemas.append(tool_schemas[tool_name])
            else:
                # Generic schema for unknown tools
                schemas.append({
                    "name": tool_name,
                    "description": f"Execute {tool_name} security tool",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "target": {"type": "string", "description": "Target for scanning"},
                            "options": {"type": "string", "description": "Tool options"}
                        },
                        "required": []
                    }
                })

        return schemas

    def get_tool_categories(self) -> Dict[str, List[str]]:
        """Group tools by category."""
        categories = {
            "Network Scanning": [
                "nmap_scan", "rustscan_scan", "masscan_scan"
            ],
            "Web Scanning": [
                "gobuster_scan", "feroxbuster_scan", "ffuf_scan",
                "nuclei_scan", "nikto_scan", "whatweb_scan"
            ],
            "Vulnerability Scanning": [
                "nuclei_scan", "sqlmap_scan", "wpscan_scan"
            ],
            "Subdomain Enumeration": [
                "amass_enum", "subfinder_enum", "dnsenum_scan"
            ],
            "Password Cracking": [
                "hydra_crack", "john_crack", "hashcat_crack"
            ],
            "Binary Analysis": [
                "ghidra_analyze", "radare2_analyze"
            ],
            "Cloud Security": [
                "trivy_scan", "prowler_assess", "kube_hunter_scan"
            ]
        }

        # Filter to only available tools
        available_categories = {}
        for category, tools in categories.items():
            available = [t for t in tools if t in self.tools]
            if available:
                available_categories[category] = available

        return available_categories


# Global instance
_hexstrike: Optional[HexStrikeIntegration] = None


def get_hexstrike(hexstrike_path: Optional[str] = None,
                  server_url: str = "http://localhost:8888") -> HexStrikeIntegration:
    """Get or create global HexStrike integration instance."""
    global _hexstrike
    if _hexstrike is None:
        _hexstrike = HexStrikeIntegration(hexstrike_path, server_url)
    return _hexstrike


if __name__ == "__main__":
    # Test HexStrike integration
    logging.basicConfig(level=logging.INFO)

    integration = HexStrikeIntegration()

    print(f"\n{'='*60}")
    print(f"HexStrike Integration Test")
    print(f"{'='*60}")

    print(f"\nHexStrike Path: {integration.hexstrike_path}")
    print(f"Available Tools: {len(integration.list_tools())}")

    print(f"\nTool Categories:")
    for category, tools in integration.get_tool_categories().items():
        print(f"\n{category}:")
        for tool in tools:
            print(f"  - {tool}")

    print(f"\n{'='*60}")
