"""
Unit tests for BaseTool abstract class and SimpleCommandTool.

Tests cover:
- Abstract class behavior
- Parameter validation
- Command execution flow
- Error handling
- Output parsing
- SimpleCommandTool functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

from tools.base import BaseTool, SimpleCommandTool


class ConcreteTool(BaseTool):
    """Concrete implementation of BaseTool for testing."""

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """Build a simple test command."""
        cmd = [self.binary_name]
        if params.get('flag'):
            cmd.append(params['flag'])
        cmd.append(target)
        return cmd


class ValidatingTool(BaseTool):
    """Tool with custom validation for testing."""

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        return [self.binary_name, target]

    def validate_params(self, params: Dict[str, Any]) -> None:
        """Custom validation that requires 'required_param'."""
        if 'required_param' not in params:
            raise ValueError("required_param is missing")
        if params.get('invalid_value') == 'bad':
            raise ValueError("invalid_value cannot be 'bad'")


class CustomParsingTool(BaseTool):
    """Tool with custom output parsing for testing."""

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        return [self.binary_name, target]

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """Custom parser that extracts lines."""
        return {
            "lines": stdout.split('\n'),
            "line_count": len(stdout.split('\n')),
            "has_errors": bool(stderr),
            "returncode": returncode
        }


class TestBaseTool(unittest.TestCase):
    """Test cases for BaseTool abstract class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseTool cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            BaseTool("TestTool")

    def test_initialization_with_name_only(self):
        """Test tool initialization with just a name."""
        tool = ConcreteTool("TestTool")
        self.assertEqual(tool.name, "TestTool")
        self.assertEqual(tool.binary_name, "testtool")

    def test_initialization_with_binary_name(self):
        """Test tool initialization with explicit binary name."""
        tool = ConcreteTool("TestTool", binary_name="custom-binary")
        self.assertEqual(tool.name, "TestTool")
        self.assertEqual(tool.binary_name, "custom-binary")

    def test_str_representation(self):
        """Test string representation of tool."""
        tool = ConcreteTool("TestTool", binary_name="test-bin")
        self.assertEqual(str(tool), "TestTool (test-bin)")

    def test_repr_representation(self):
        """Test developer representation of tool."""
        tool = ConcreteTool("TestTool")
        self.assertIn("ConcreteTool", repr(tool))
        self.assertIn("TestTool", repr(tool))

    def test_build_command_must_be_implemented(self):
        """Test that build_command must be implemented by subclasses."""
        # This is tested by the abstract class mechanism
        # Attempting to create a class without build_command will fail
        with self.assertRaises(TypeError):
            class IncompleteTool(BaseTool):
                pass
            IncompleteTool("test")

    def test_default_parse_output(self):
        """Test default parse_output returns raw output."""
        tool = ConcreteTool("TestTool")
        result = tool.parse_output("test output", "test error", 0)

        self.assertEqual(result["raw_output"], "test output")
        self.assertEqual(result["stderr"], "test error")
        self.assertEqual(result["returncode"], 0)

    def test_default_validate_params(self):
        """Test default validate_params does nothing."""
        tool = ConcreteTool("TestTool")
        # Should not raise any exception
        tool.validate_params({})
        tool.validate_params({"any": "params"})


class TestBaseToolExecution(unittest.TestCase):
    """Test cases for BaseTool execute() method."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = ConcreteTool("TestTool", binary_name="testtool")
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        """Test successful tool execution."""
        # Mock successful execution
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "test output",
            "stderr": "",
            "returncode": 0,
            "execution_time": 1.5,
            "cached": False
        }

        result = self.tool.execute(
            "target.com",
            {"flag": "-v"},
            self.mock_execute_func
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "TestTool")
        self.assertEqual(result["target"], "target.com")
        self.assertEqual(result["command"], "testtool -v target.com")
        self.assertIn("output", result)
        self.assertEqual(result["execution_time"], 1.5)
        self.assertFalse(result["cached"])

    def test_execution_with_cache(self):
        """Test execution with caching enabled."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "cached output",
            "stderr": "",
            "returncode": 0,
            "cached": True
        }

        result = self.tool.execute(
            "target.com",
            {},
            self.mock_execute_func,
            use_cache=True
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["cached"])
        self.mock_execute_func.assert_called_once()

    def test_execution_without_cache(self):
        """Test execution with caching disabled."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "fresh output",
            "stderr": "",
            "returncode": 0,
            "cached": False
        }

        result = self.tool.execute(
            "target.com",
            {},
            self.mock_execute_func,
            use_cache=False
        )

        self.assertTrue(result["success"])
        # Check that use_cache=False was passed
        call_args = self.mock_execute_func.call_args
        self.assertEqual(call_args[1].get('use_cache'), False)

    def test_execution_command_failure(self):
        """Test execution when command fails."""
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "Command not found",
            "stderr": "testtool: command not found",
            "returncode": 127
        }

        result = self.tool.execute(
            "target.com",
            {},
            self.mock_execute_func
        )

        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Command not found")
        self.assertIn("stderr", result)

    def test_execution_with_validation_error(self):
        """Test execution with parameter validation failure."""
        validating_tool = ValidatingTool("ValidatingTool")

        # Missing required_param
        result = validating_tool.execute(
            "target.com",
            {},
            self.mock_execute_func
        )

        self.assertFalse(result["success"])
        self.assertIn("Parameter validation failed", result["error"])
        self.assertIn("required_param is missing", result["error"])

    def test_execution_with_invalid_param_value(self):
        """Test execution with invalid parameter value."""
        validating_tool = ValidatingTool("ValidatingTool")

        result = validating_tool.execute(
            "target.com",
            {"required_param": "ok", "invalid_value": "bad"},
            self.mock_execute_func
        )

        self.assertFalse(result["success"])
        self.assertIn("cannot be 'bad'", result["error"])

    def test_execution_with_exception(self):
        """Test execution when unexpected exception occurs."""
        self.mock_execute_func.side_effect = Exception("Unexpected error")

        result = self.tool.execute(
            "target.com",
            {},
            self.mock_execute_func
        )

        self.assertFalse(result["success"])
        self.assertIn("Unexpected error", result["error"])

    def test_custom_output_parsing(self):
        """Test execution with custom output parsing."""
        parsing_tool = CustomParsingTool("ParsingTool")

        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "line1\nline2\nline3",
            "stderr": "warning message",
            "returncode": 0
        }

        result = parsing_tool.execute(
            "target.com",
            {},
            self.mock_execute_func
        )

        self.assertTrue(result["success"])
        output = result["output"]
        self.assertEqual(output["line_count"], 3)
        self.assertTrue(output["has_errors"])
        self.assertEqual(len(output["lines"]), 3)

    @patch('tools.base.logger')
    def test_logging_on_success(self, mock_logger):
        """Test that successful execution logs appropriately."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "output",
            "stderr": "",
            "returncode": 0
        }

        self.tool.execute("target.com", {}, self.mock_execute_func)

        # Check that info log was called
        mock_logger.info.assert_called()
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn("Executing", log_message)
        self.assertIn("TestTool", log_message)

    @patch('tools.base.logger')
    def test_logging_on_validation_error(self, mock_logger):
        """Test that validation errors are logged."""
        validating_tool = ValidatingTool("ValidatingTool")

        validating_tool.execute("target.com", {}, self.mock_execute_func)

        # Check that error log was called
        mock_logger.error.assert_called()
        log_message = mock_logger.error.call_args[0][0]
        self.assertIn("validation failed", log_message)

    @patch('tools.base.logger')
    def test_logging_on_exception(self, mock_logger):
        """Test that exceptions are logged with traceback."""
        self.mock_execute_func.side_effect = RuntimeError("Test error")

        self.tool.execute("target.com", {}, self.mock_execute_func)

        # Check that error log was called with exc_info
        mock_logger.error.assert_called()
        self.assertTrue(mock_logger.error.call_args[1].get('exc_info'))


class TestSimpleCommandTool(unittest.TestCase):
    """Test cases for SimpleCommandTool class."""

    def test_initialization_without_target_flag(self):
        """Test SimpleCommandTool without target flag."""
        tool = SimpleCommandTool("SimpleTool")
        self.assertEqual(tool.name, "SimpleTool")
        self.assertEqual(tool.binary_name, "simpletool")
        self.assertIsNone(tool.target_flag)

    def test_initialization_with_target_flag(self):
        """Test SimpleCommandTool with target flag."""
        tool = SimpleCommandTool("SimpleTool", target_flag="-h")
        self.assertEqual(tool.target_flag, "-h")

    def test_build_command_without_target_flag(self):
        """Test command building without target flag."""
        tool = SimpleCommandTool("SimpleTool", binary_name="simple")
        cmd = tool.build_command("example.com", {})

        self.assertEqual(cmd, ["simple", "example.com"])

    def test_build_command_with_target_flag(self):
        """Test command building with target flag."""
        tool = SimpleCommandTool("SimpleTool", binary_name="simple", target_flag="-h")
        cmd = tool.build_command("example.com", {})

        self.assertEqual(cmd, ["simple", "-h", "example.com"])

    def test_build_command_with_additional_args(self):
        """Test command building with additional arguments."""
        tool = SimpleCommandTool("SimpleTool", binary_name="simple", target_flag="-u")
        cmd = tool.build_command("example.com", {
            "additional_args": "-v -p 443"
        })

        self.assertEqual(cmd, ["simple", "-v", "-p", "443", "-u", "example.com"])

    def test_build_command_no_flag_with_args(self):
        """Test command building with args but no target flag."""
        tool = SimpleCommandTool("SimpleTool", binary_name="simple")
        cmd = tool.build_command("example.com", {
            "additional_args": "--verbose --timeout 30"
        })

        self.assertEqual(cmd, ["simple", "--verbose", "--timeout", "30", "example.com"])

    def test_empty_additional_args(self):
        """Test that empty additional_args are handled correctly."""
        tool = SimpleCommandTool("SimpleTool", binary_name="simple")
        cmd = tool.build_command("example.com", {"additional_args": ""})

        self.assertEqual(cmd, ["simple", "example.com"])

    def test_integration_with_execute(self):
        """Test SimpleCommandTool integration with execute method."""
        tool = SimpleCommandTool("SimpleTool", binary_name="simple", target_flag="-t")
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": "simple output",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute("target.com", {"additional_args": "-v"}, mock_execute)

        self.assertTrue(result["success"])
        self.assertEqual(result["command"], "simple -v -t target.com")


class TestBaseToolEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_empty_target(self):
        """Test execution with empty target."""
        tool = ConcreteTool("TestTool")
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute("", {}, mock_execute)
        self.assertTrue(result["success"])

    def test_empty_params(self):
        """Test execution with empty parameters."""
        tool = ConcreteTool("TestTool")
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute("target.com", {}, mock_execute)
        self.assertTrue(result["success"])

    def test_special_characters_in_target(self):
        """Test handling of special characters in target."""
        tool = ConcreteTool("TestTool")
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute("target-with_special.chars@test.com", {}, mock_execute)
        self.assertTrue(result["success"])
        self.assertIn("target-with_special.chars@test.com", result["command"])

    def test_multiline_output_parsing(self):
        """Test parsing of multiline output."""
        tool = ConcreteTool("TestTool")
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": "line1\nline2\nline3\n",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute("target.com", {}, mock_execute)
        self.assertEqual(result["output"]["raw_output"], "line1\nline2\nline3\n")

    def test_execution_result_without_optional_fields(self):
        """Test handling of execution result missing optional fields."""
        tool = ConcreteTool("TestTool")
        # Return minimal result without execution_time or cached
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": "output",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute("target.com", {}, mock_execute)
        self.assertTrue(result["success"])
        # Should default to 0 and False
        self.assertEqual(result["execution_time"], 0)
        self.assertFalse(result["cached"])

    def test_nonzero_returncode_but_success(self):
        """Test handling of non-zero return code with success flag."""
        tool = ConcreteTool("TestTool")
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": "output with warnings",
            "stderr": "warning messages",
            "returncode": 1
        })

        result = tool.execute("target.com", {}, mock_execute)
        self.assertTrue(result["success"])
        self.assertEqual(result["output"]["returncode"], 1)


if __name__ == '__main__':
    unittest.main()
