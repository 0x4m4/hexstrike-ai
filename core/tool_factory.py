"""
HexStrike AI - Tool Factory Module

This module provides factory functions for creating tool executors.

Functions:
    - create_tool_executor: Factory function to create tool executor from tool class
"""

from typing import Dict, Any


def create_tool_executor(tool_class, execute_command_func=None):
    """
    Factory function to create tool executor from tool class

    Args:
        tool_class: The tool class to instantiate
        execute_command_func: The execute_command function to use (optional, can be passed later)

    Returns:
        An executor function that takes (target, params) and returns execution results
    """
    def executor(target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        tool = tool_class()
        # Use the provided execute_command function
        # This will need to be passed when calling create_tool_executor
        return tool.execute(target, params, execute_command_func)
    return executor
