"""
Base Tool Abstraction Layer
Eliminates duplication in tool execution patterns
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """
    Abstract base class for all HexStrike security tools.

    This class provides a common interface for tool execution,
    eliminating the 66% code duplication found in execute_*_scan() functions.

    Subclasses must implement:
    - build_command(): Construct tool-specific command arguments
    - parse_output(): Parse tool-specific output (optional, defaults to raw output)
    """

    def __init__(self, name: str, binary_name: Optional[str] = None):
        """
        Initialize the tool.

        Args:
            name: Human-readable tool name (e.g., "Nmap Scanner")
            binary_name: Actual binary command (e.g., "nmap"). Defaults to lowercase name.
        """
        self.name = name
        self.binary_name = binary_name or name.lower()

    @abstractmethod
    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build the command arguments for this tool.

        Args:
            target: The target (IP, domain, URL, etc.)
            params: Tool-specific parameters from the request

        Returns:
            List of command arguments (e.g., ['nmap', '-sV', '192.168.1.1'])

        Example:
            >>> tool.build_command('example.com', {'scan_type': '-sV'})
            ['nmap', '-sV', 'example.com']
        """
        pass

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse tool output into structured data.

        Override this method to provide tool-specific parsing.
        Default implementation returns raw output.

        Args:
            stdout: Standard output from the tool
            stderr: Standard error from the tool
            returncode: Process return code

        Returns:
            Parsed output dictionary
        """
        return {
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }

    def validate_params(self, params: Dict[str, Any]) -> None:
        """
        Validate tool parameters before execution.

        Override this method to add parameter validation.
        Raise ValueError for invalid parameters.

        Args:
            params: Tool parameters to validate (used by subclasses)

        Raises:
            ValueError: If parameters are invalid
        """
        _ = params  # Acknowledged - subclasses override this
        pass

    def execute(self, target: str, params: Dict[str, Any],
                execute_func: callable, use_cache: bool = True) -> Dict[str, Any]:
        """
        Execute the tool with the given parameters.

        This is the main execution method that orchestrates:
        1. Parameter validation
        2. Command building
        3. Command execution
        4. Output parsing
        5. Error handling

        Args:
            target: The target to scan
            params: Tool parameters
            execute_func: The execute_command function from hexstrike_server
            use_cache: Whether to use caching

        Returns:
            Dictionary containing execution results:
            {
                "success": bool,
                "tool": str,
                "target": str,
                "command": str,
                "output": dict or str,
                "error": str (optional)
            }
        """
        try:
            # Validate parameters
            self.validate_params(params)

            # Build command
            cmd_parts = self.build_command(target, params)
            command = ' '.join(cmd_parts)

            logger.info(f"Executing {self.name}: {command}")

            # Execute command using the provided execute_command function
            result = execute_func(command, use_cache=use_cache)

            # Check if execution was successful
            if not result.get("success", False):
                return {
                    "success": False,
                    "tool": self.name,
                    "target": target,
                    "command": command,
                    "error": result.get("error", "Unknown execution error"),
                    "stderr": result.get("stderr", "")
                }

            # Parse output if execution was successful
            parsed_output = self.parse_output(
                result.get("stdout", ""),
                result.get("stderr", ""),
                result.get("returncode", 0)
            )

            return {
                "success": True,
                "tool": self.name,
                "target": target,
                "command": command,
                "output": parsed_output,
                "execution_time": result.get("execution_time", 0),
                "cached": result.get("cached", False)
            }

        except ValueError as e:
            # Parameter validation error
            logger.error(f"{self.name} parameter validation failed: {e}")
            return {
                "success": False,
                "tool": self.name,
                "target": target,
                "error": f"Parameter validation failed: {str(e)}"
            }

        except Exception as e:
            # Unexpected error
            logger.error(f"{self.name} execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "tool": self.name,
                "target": target,
                "error": str(e)
            }

    def __str__(self) -> str:
        """String representation of the tool."""
        return f"{self.name} ({self.binary_name})"

    def __repr__(self) -> str:
        """Developer representation of the tool."""
        return f"<{self.__class__.__name__}: {self.name}>"


class SimpleCommandTool(BaseTool):
    """
    Simplified base class for tools with basic command patterns.

    This class is useful for tools that follow the simple pattern:
    <binary> [options] <target>

    Example:
        class NiktoTool(SimpleCommandTool):
            def __init__(self):
                super().__init__("Nikto", target_flag="-h")
    """

    def __init__(self, name: str, binary_name: Optional[str] = None,
                 target_flag: Optional[str] = None):
        """
        Initialize a simple command tool.

        Args:
            name: Tool name
            binary_name: Binary command name
            target_flag: Flag to use before target (e.g., "-h", "-u", None)
        """
        super().__init__(name, binary_name)
        self.target_flag = target_flag

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build a simple command with optional target flag and additional args.

        Pattern: <binary> [additional_args] [target_flag] <target>
        """
        cmd_parts = [self.binary_name]

        # Add additional arguments if provided
        additional_args = params.get('additional_args', '')
        if additional_args:
            cmd_parts.extend(additional_args.split())

        # Add target with optional flag
        if self.target_flag:
            cmd_parts.extend([self.target_flag, target])
        else:
            cmd_parts.append(target)

        return cmd_parts
