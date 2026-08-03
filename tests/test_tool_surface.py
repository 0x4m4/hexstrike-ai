"""Unit tests for MCP tool surface trimming (#138)."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("hexstrike_mcp", ROOT / "hexstrike_mcp.py")
hexstrike_mcp = importlib.util.module_from_spec(SPEC)
sys.modules["hexstrike_mcp"] = hexstrike_mcp
SPEC.loader.exec_module(hexstrike_mcp)


def test_compact_description_first_line_only():
    doc = "Execute Nmap scan.\n\nArgs:\n    target: host\n"
    assert hexstrike_mcp._compact_description(doc) == "Execute Nmap scan."


def test_core_tier_exposes_subset():
    mcp = MagicMock()
    mcp._tool_manager._tools = {
        "nmap_scan": MagicMock(description="scan", parameters={"properties": {"target": {"description": "host"}}}),
        "prowler_scan": MagicMock(description="cloud", parameters={"properties": {}}),
        "server_health": MagicMock(description="health", parameters={"properties": {}}),
    }
    mcp._tool_manager.get_tool = lambda name: mcp._tool_manager._tools.get(name)
    mcp._tool_manager.remove_tool = lambda name: mcp._tool_manager._tools.pop(name, None)

    hexstrike_mcp.apply_tool_surface(mcp, "core", compact=True)

    assert "nmap_scan" in mcp._tool_manager._tools
    assert "server_health" in mcp._tool_manager._tools
    assert "prowler_scan" not in mcp._tool_manager._tools
    assert mcp._tool_manager._tools["nmap_scan"].description == "scan"
    assert "description" not in mcp._tool_manager._tools["nmap_scan"].parameters["properties"]["target"]


def test_full_tier_keeps_all_tools():
    mcp = MagicMock()
    mcp._tool_manager._tools = {"a": MagicMock(description="x", parameters={}), "b": MagicMock(description="y", parameters={})}
    mcp._tool_manager.get_tool = lambda name: mcp._tool_manager._tools.get(name)

    hexstrike_mcp.apply_tool_surface(mcp, "full", compact=False)

    assert len(mcp._tool_manager._tools) == 2
