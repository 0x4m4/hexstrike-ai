"""
Unit tests for HttpxTool implementation.

Tests cover:
- Command building with pipe pattern
- Parameter validation
- Output parsing
- Error handling
- Integration with BaseTool
- Edge cases and boundary conditions

Comprehensive test coverage: 30+ tests
"""

import unittest
from unittest.mock import Mock, patch
from typing import Dict, Any

from tools.network.httpx import HttpxTool


class TestHttpxToolInitialization(unittest.TestCase):
    """Test cases for HttpxTool initialization."""

    def test_initialization(self):
        """Test HttpxTool initialization."""
        tool = HttpxTool()
        self.assertEqual(tool.name, "HTTPX")
        self.assertEqual(tool.binary_name, "httpx")

    def test_inheritance(self):
        """Test that HttpxTool inherits from BaseTool."""
        from tools.base import BaseTool
        tool = HttpxTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        """Test string representation."""
        tool = HttpxTool()
        self.assertEqual(str(tool), "HTTPX (httpx)")

    def test_repr_representation(self):
        """Test developer representation."""
        tool = HttpxTool()
        self.assertIn("HttpxTool", repr(tool))
        self.assertIn("HTTPX", repr(tool))


class TestHttpxCommandBuilding(unittest.TestCase):
    """Test cases for HTTPX command building."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = HttpxTool()

    def test_basic_command_default_params(self):
        """Test basic command with default parameters."""
        cmd = self.tool.build_command("example.com", {})
        # HTTPX uses echo pipe pattern
        self.assertIn("echo", cmd)
        self.assertIn("example.com", cmd)
        self.assertIn("|", cmd)
        self.assertIn("httpx", cmd)

    def test_command_uses_pipe_pattern(self):
        """Test that command uses echo | httpx pattern."""
        cmd = self.tool.build_command("example.com", {})
        self.assertEqual(cmd[0], "echo")
        self.assertEqual(cmd[1], "example.com")
        self.assertEqual(cmd[2], "|")
        self.assertEqual(cmd[3], "httpx")

    def test_command_with_default_additional_args(self):
        """Test command includes default tech-detect and status-code."""
        cmd = self.tool.build_command("example.com", {})
        self.assertIn("-tech-detect", cmd)
        self.assertIn("-status-code", cmd)

    def test_command_with_custom_additional_args(self):
        """Test command with custom additional arguments."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-silent -mc 200"
        })
        self.assertIn("-silent", cmd)
        self.assertIn("-mc", cmd)
        self.assertIn("200", cmd)

    def test_command_with_title_flag(self):
        """Test command with title extraction."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-title"
        })
        self.assertIn("-title", cmd)

    def test_command_with_content_length(self):
        """Test command with content length."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-content-length"
        })
        self.assertIn("-content-length", cmd)

    def test_command_with_status_code_filter(self):
        """Test command with status code matching."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-mc 200,301,302"
        })
        self.assertIn("-mc", cmd)
        self.assertIn("200,301,302", cmd)

    def test_command_with_threads(self):
        """Test command with thread specification."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-threads 50"
        })
        self.assertIn("-threads", cmd)
        self.assertIn("50", cmd)

    def test_command_with_timeout(self):
        """Test command with timeout."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-timeout 10"
        })
        self.assertIn("-timeout", cmd)
        self.assertIn("10", cmd)

    def test_command_with_follow_redirects(self):
        """Test command with follow redirects."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-follow-redirects"
        })
        self.assertIn("-follow-redirects", cmd)

    def test_command_with_json_output(self):
        """Test command with JSON output format."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-json"
        })
        self.assertIn("-json", cmd)

    def test_command_with_empty_additional_args(self):
        """Test command with explicitly empty additional_args."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": ""
        })
        # Should only have echo, target, pipe, httpx
        self.assertEqual(len(cmd), 4)

    def test_command_with_multiple_flags(self):
        """Test command with multiple flags."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-title -status-code -content-length -tech-detect"
        })
        self.assertIn("-title", cmd)
        self.assertIn("-status-code", cmd)
        self.assertIn("-content-length", cmd)
        self.assertIn("-tech-detect", cmd)


class TestHttpxTargetVariations(unittest.TestCase):
    """Test HTTPX with different target variations."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = HttpxTool()

    def test_domain_target(self):
        """Test with domain target."""
        cmd = self.tool.build_command("example.com", {})
        self.assertIn("example.com", cmd)

    def test_url_with_http(self):
        """Test with HTTP URL."""
        cmd = self.tool.build_command("http://example.com", {})
        self.assertIn("http://example.com", cmd)

    def test_url_with_https(self):
        """Test with HTTPS URL."""
        cmd = self.tool.build_command("https://example.com", {})
        self.assertIn("https://example.com", cmd)

    def test_url_with_port(self):
        """Test with URL and port."""
        cmd = self.tool.build_command("https://example.com:8443", {})
        self.assertIn("https://example.com:8443", cmd)

    def test_url_with_path(self):
        """Test with URL including path."""
        cmd = self.tool.build_command("https://example.com/admin", {})
        self.assertIn("https://example.com/admin", cmd)

    def test_ip_address_target(self):
        """Test with IP address."""
        cmd = self.tool.build_command("192.168.1.1", {})
        self.assertIn("192.168.1.1", cmd)

    def test_subdomain_target(self):
        """Test with subdomain."""
        cmd = self.tool.build_command("api.example.com", {})
        self.assertIn("api.example.com", cmd)


class TestHttpxOutputParsing(unittest.TestCase):
    """Test cases for HTTPX output parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = HttpxTool()

    def test_parse_basic_output(self):
        """Test parsing basic httpx output."""
        stdout = "https://example.com [200] [Apache/2.4.41]"
        result = self.tool.parse_output(stdout, "", 0)

        self.assertIn("raw_output", result)
        self.assertEqual(result["raw_output"], stdout)
        self.assertEqual(result["returncode"], 0)

    def test_parse_empty_output(self):
        """Test parsing empty output."""
        result = self.tool.parse_output("", "", 0)

        self.assertEqual(result["raw_output"], "")
        self.assertEqual(result["stderr"], "")
        self.assertEqual(result["returncode"], 0)

    def test_parse_output_with_stderr(self):
        """Test parsing with stderr messages."""
        stdout = "https://example.com [200]"
        stderr = "Warning: DNS resolution slow"

        result = self.tool.parse_output(stdout, stderr, 0)

        self.assertEqual(result["stderr"], stderr)
        self.assertIn("raw_output", result)

    def test_parse_multiline_output(self):
        """Test parsing multiline output."""
        stdout = """https://example.com [200]
https://api.example.com [200]
https://www.example.com [301]"""

        result = self.tool.parse_output(stdout, "", 0)
        self.assertEqual(result["raw_output"], stdout)

    def test_parse_with_nonzero_returncode(self):
        """Test parsing with non-zero return code."""
        result = self.tool.parse_output("", "Error: timeout", 1)

        self.assertEqual(result["returncode"], 1)
        self.assertIn("stderr", result)

    def test_parse_json_output(self):
        """Test parsing JSON formatted output."""
        stdout = '{"url":"https://example.com","status_code":200}'
        result = self.tool.parse_output(stdout, "", 0)
        self.assertEqual(result["raw_output"], stdout)


class TestHttpxToolExecution(unittest.TestCase):
    """Test cases for HttpxTool execution flow."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = HttpxTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        """Test successful httpx execution."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "https://example.com [200]",
            "stderr": "",
            "returncode": 0,
            "execution_time": 2.5,
            "cached": False
        }

        result = self.tool.execute("example.com", {}, self.mock_execute_func)

        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "HTTPX")
        self.assertEqual(result["target"], "example.com")
        self.assertIn("echo example.com | httpx", result["command"])

    def test_execution_with_parameters(self):
        """Test execution with custom parameters."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "output",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute(
            "example.com",
            {"additional_args": "-silent -json"},
            self.mock_execute_func
        )

        self.assertTrue(result["success"])
        self.assertIn("-silent", result["command"])
        self.assertIn("-json", result["command"])

    def test_execution_failure(self):
        """Test handling of execution failure."""
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "httpx: command not found",
            "stderr": "httpx: command not found",
            "returncode": 127
        }

        result = self.tool.execute("example.com", {}, self.mock_execute_func)

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_execution_with_cache(self):
        """Test execution with caching."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "cached output",
            "stderr": "",
            "returncode": 0,
            "cached": True
        }

        result = self.tool.execute(
            "example.com",
            {},
            self.mock_execute_func,
            use_cache=True
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["cached"])

    @patch('tools.base.logger')
    def test_logging_during_execution(self, mock_logger):
        """Test that execution is logged."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "output",
            "stderr": "",
            "returncode": 0
        }

        self.tool.execute("example.com", {}, self.mock_execute_func)

        mock_logger.info.assert_called()
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn("Executing", log_message)
        self.assertIn("HTTPX", log_message)


class TestHttpxEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = HttpxTool()

    def test_empty_target(self):
        """Test with empty target string."""
        cmd = self.tool.build_command("", {})
        self.assertIn("", cmd)

    def test_none_in_params(self):
        """Test with None values in params."""
        cmd = self.tool.build_command("example.com", {"additional_args": None})
        # Should handle None gracefully, will use default args
        self.assertIn("echo", cmd)
        self.assertIn("example.com", cmd)
        self.assertIn("httpx", cmd)

    def test_whitespace_in_additional_args(self):
        """Test with extra whitespace in additional_args."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "  -silent   -json  "
        })
        self.assertIn("-silent", cmd)
        self.assertIn("-json", cmd)

    def test_special_characters_in_url(self):
        """Test URL with special characters."""
        cmd = self.tool.build_command("https://example.com/path?param=value", {})
        self.assertIn("https://example.com/path?param=value", cmd)


class TestHttpxIntegration(unittest.TestCase):
    """Integration tests for HttpxTool."""

    def test_realistic_probing(self):
        """Test realistic HTTP probing scenario."""
        tool = HttpxTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": """https://example.com [200] [Apache/2.4.41] [Example Domain]
https://www.example.com [301] [nginx/1.18.0]""",
            "stderr": "",
            "returncode": 0,
            "execution_time": 3.2,
            "cached": False
        })

        result = tool.execute("example.com", {}, mock_execute)

        self.assertTrue(result["success"])
        self.assertIn("200", result["output"]["raw_output"])


if __name__ == '__main__':
    unittest.main()
