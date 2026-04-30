"""
HexStrike Tools Module
Security tool integrations

Phase 2 Refactoring: Tool Abstraction Layer
This module eliminates 66% code duplication from execute_*_scan() functions.
"""

from .base import BaseTool, SimpleCommandTool

__all__ = [
    'BaseTool',
    'SimpleCommandTool'
]
