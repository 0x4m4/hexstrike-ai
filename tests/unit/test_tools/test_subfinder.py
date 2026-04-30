"""
Unit tests for SubfinderTool implementation.

Tests cover:
- Command building with various parameters
- Parameter validation
- Output parsing
- Error handling
- Integration with BaseTool
- Edge cases and boundary conditions

Comprehensive test coverage: 35+ tests
"""

import unittest
from unittest.mock import Mock, patch
from typing import Dict, Any

from tools.recon.subfinder import SubfinderTool


class TestSubfinderToolInitialization(unittest.TestCase):
    """Test cases for SubfinderTool initialization."""

    def test_initialization(self):
        """Test SubfinderTool initialization."""
        tool = SubfinderTool()
        self.assertEqual(tool.name, "Subfinder")
        self.assertEqual(tool.binary_name, "subfinder")

    def test_inheritance(self):
        """Test that SubfinderTool inherits from BaseTool."""
        from tools.base import BaseTool
        tool = SubfinderTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        """Test string representation."""
        tool = SubfinderTool()
        self.assertEqual(str(tool), "Subfinder (subfinder)")

    def test_repr_representation(self):
        """Test developer representation."""
        tool = SubfinderTool()
        self.assertIn("SubfinderTool", repr(tool))
        self.assertIn("Subfinder", repr(tool))


class TestSubfinderCommandBuilding(unittest.TestCase):
    """Test cases for Subfinder command building."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = SubfinderTool()

    def test_basic_command_default_params(self):
        """Test basic command with default parameters."""
        cmd = self.tool.build_command("example.com", {})
        self.assertEqual(cmd, ["subfinder", "-d", "example.com"])

    def test_command_with_domain_flag(self):
        """Test command includes -d flag for domain."""
        cmd = self.tool.build_command("testdomain.com", {})
        self.assertIn("-d", cmd)
        self.assertIn("testdomain.com", cmd)

    def test_command_with_silent_flag(self):
        """Test command with silent output flag."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-silent"
        })
        self.assertEqual(cmd, ["subfinder", "-d", "example.com", "-silent"])

    def test_command_with_recursive_flag(self):
        """Test command with recursive enumeration."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-recursive"
        })
        self.assertIn("-recursive", cmd)

    def test_command_with_output_file(self):
        """Test command with output file specification."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-o output.txt"
        })
        self.assertIn("-o", cmd)
        self.assertIn("output.txt", cmd)

    def test_command_with_json_output(self):
        """Test command with JSON output format."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-json"
        })
        self.assertIn("-json", cmd)

    def test_command_with_verbose_flag(self):
        """Test command with verbose output."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-v"
        })
        self.assertIn("-v", cmd)

    def test_command_with_sources_filter(self):
        """Test command with specific sources."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-sources crtsh,virustotal"
        })
        self.assertIn("-sources", cmd)
        self.assertIn("crtsh,virustotal", cmd)

    def test_command_with_exclude_sources(self):
        """Test command with excluded sources."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-exclude-sources shodan"
        })
        self.assertIn("-exclude-sources", cmd)
        self.assertIn("shodan", cmd)

    def test_command_with_multiple_additional_args(self):
        """Test command with multiple additional arguments."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-silent -recursive -timeout 30"
        })
        self.assertIn("-silent", cmd)
        self.assertIn("-recursive", cmd)
        self.assertIn("-timeout", cmd)
        self.assertIn("30", cmd)

    def test_command_with_empty_additional_args(self):
        """Test command with empty additional_args."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": ""
        })
        self.assertEqual(cmd, ["subfinder", "-d", "example.com"])

    def test_command_with_config_file(self):
        """Test command with configuration file."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-config /etc/subfinder/config.yaml"
        })
        self.assertIn("-config", cmd)
        self.assertIn("/etc/subfinder/config.yaml", cmd)

    def test_command_with_rate_limit(self):
        """Test command with rate limiting."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-rate-limit 150"
        })
        self.assertIn("-rate-limit", cmd)
        self.assertIn("150", cmd)

    def test_command_with_timeout(self):
        """Test command with timeout specification."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-timeout 60"
        })
        self.assertIn("-timeout", cmd)
        self.assertIn("60", cmd)

    def test_command_with_max_time(self):
        """Test command with maximum time limit."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-max-time 120"
        })
        self.assertIn("-max-time", cmd)
        self.assertIn("120", cmd)

    def test_command_order_preserved(self):
        """Test that command argument order is preserved."""
        cmd = self.tool.build_command("example.com", {})
        self.assertEqual(cmd[0], "subfinder")
        self.assertEqual(cmd[1], "-d")
        self.assertEqual(cmd[2], "example.com")


class TestSubfinderTargetVariations(unittest.TestCase):
    """Test Subfinder with different target variations."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = SubfinderTool()

    def test_single_word_domain(self):
        """Test with single word domain."""
        cmd = self.tool.build_command("example.com", {})
        self.assertIn("example.com", cmd)

    def test_subdomain_target(self):
        """Test with subdomain as target."""
        cmd = self.tool.build_command("sub.example.com", {})
        self.assertIn("sub.example.com", cmd)

    def test_deep_subdomain_target(self):
        """Test with deep subdomain."""
        cmd = self.tool.build_command("deep.sub.example.com", {})
        self.assertIn("deep.sub.example.com", cmd)

    def test_domain_with_hyphen(self):
        """Test domain with hyphen."""
        cmd = self.tool.build_command("my-domain.com", {})
        self.assertIn("my-domain.com", cmd)

    def test_domain_with_numbers(self):
        """Test domain with numbers."""
        cmd = self.tool.build_command("example123.com", {})
        self.assertIn("example123.com", cmd)

    def test_long_tld(self):
        """Test domain with longer TLD."""
        cmd = self.tool.build_command("example.co.uk", {})
        self.assertIn("example.co.uk", cmd)

    def test_new_gtld(self):
        """Test with new gTLD."""
        cmd = self.tool.build_command("example.tech", {})
        self.assertIn("example.tech", cmd)

    def test_edu_domain(self):
        """Test with .edu domain."""
        cmd = self.tool.build_command("university.edu", {})
        self.assertIn("university.edu", cmd)


class TestSubfinderOutputParsing(unittest.TestCase):
    """Test cases for Subfinder output parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = SubfinderTool()

    def test_parse_basic_output(self):
        """Test parsing basic subfinder output."""
        stdout = "sub1.example.com\nsub2.example.com\nsub3.example.com"
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
        stdout = "sub.example.com"
        stderr = "Warning: Some sources failed"

        result = self.tool.parse_output(stdout, stderr, 0)

        self.assertEqual(result["stderr"], stderr)
        self.assertIn("raw_output", result)

    def test_parse_multiline_output(self):
        """Test parsing multiline subdomain output."""
        stdout = """sub1.example.com
sub2.example.com
sub3.example.com
www.example.com
mail.example.com"""

        result = self.tool.parse_output(stdout, "", 0)
        self.assertEqual(result["raw_output"], stdout)

    def test_parse_with_nonzero_returncode(self):
        """Test parsing with non-zero return code."""
        result = self.tool.parse_output("", "Error: timeout", 1)

        self.assertEqual(result["returncode"], 1)
        self.assertIn("stderr", result)

    def test_parse_large_output(self):
        """Test parsing large output with many subdomains."""
        subdomains = [f"sub{i}.example.com" for i in range(500)]
        stdout = "\n".join(subdomains)

        result = self.tool.parse_output(stdout, "", 0)
        self.assertIn("raw_output", result)
        self.assertEqual(result["raw_output"], stdout)

    def test_parse_output_preserves_content(self):
        """Test that parsing preserves exact output content."""
        stdout = "  sub.example.com  \n  another.example.com  "
        result = self.tool.parse_output(stdout, "", 0)
        self.assertEqual(result["raw_output"], stdout)

    def test_parse_json_output(self):
        """Test parsing JSON formatted output."""
        stdout = '{"host":"sub.example.com","source":"crtsh"}'
        result = self.tool.parse_output(stdout, "", 0)
        self.assertEqual(result["raw_output"], stdout)


class TestSubfinderToolExecution(unittest.TestCase):
    """Test cases for SubfinderTool execution flow."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = SubfinderTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        """Test successful subfinder execution."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "sub1.example.com\nsub2.example.com",
            "stderr": "",
            "returncode": 0,
            "execution_time": 8.5,
            "cached": False
        }

        result = self.tool.execute("example.com", {}, self.mock_execute_func)

        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "Subfinder")
        self.assertEqual(result["target"], "example.com")
        self.assertIn("subfinder -d example.com", result["command"])
        self.assertIn("output", result)

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
            {"additional_args": "-silent -recursive"},
            self.mock_execute_func
        )

        self.assertTrue(result["success"])
        self.assertIn("-silent", result["command"])
        self.assertIn("-recursive", result["command"])

    def test_execution_failure(self):
        """Test handling of execution failure."""
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "subfinder: command not found",
            "stderr": "subfinder: command not found",
            "returncode": 127
        }

        result = self.tool.execute("example.com", {}, self.mock_execute_func)

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_execution_with_cache_enabled(self):
        """Test execution with caching enabled."""
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

    def test_execution_with_cache_disabled(self):
        """Test execution with caching disabled."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "fresh output",
            "stderr": "",
            "returncode": 0,
            "cached": False
        }

        result = self.tool.execute(
            "example.com",
            {},
            self.mock_execute_func,
            use_cache=False
        )

        self.assertTrue(result["success"])
        call_args = self.mock_execute_func.call_args
        self.assertEqual(call_args[1].get('use_cache'), False)

    def test_execution_command_string_format(self):
        """Test that execution command is properly formatted."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute("example.com", {}, self.mock_execute_func)

        self.assertIsInstance(result["command"], str)
        self.assertIn("subfinder -d example.com", result["command"])

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
        self.assertIn("Subfinder", log_message)

    def test_execution_with_json_output(self):
        """Test execution with JSON output format."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": '{"host":"sub.example.com"}',
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute(
            "example.com",
            {"additional_args": "-json"},
            self.mock_execute_func
        )

        self.assertTrue(result["success"])
        self.assertIn("-json", result["command"])


class TestSubfinderEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = SubfinderTool()

    def test_empty_target(self):
        """Test with empty target string."""
        cmd = self.tool.build_command("", {})
        self.assertIn("", cmd)

    def test_none_in_params(self):
        """Test with None values in params."""
        cmd = self.tool.build_command("example.com", {"additional_args": None})
        self.assertEqual(cmd, ["subfinder", "-d", "example.com"])

    def test_whitespace_in_additional_args(self):
        """Test with extra whitespace in additional_args."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "  -silent   -recursive  "
        })
        self.assertIn("-silent", cmd)
        self.assertIn("-recursive", cmd)

    def test_special_characters_in_domain(self):
        """Test domain with special characters."""
        cmd = self.tool.build_command("test-domain_123.example.com", {})
        self.assertIn("test-domain_123.example.com", cmd)

    def test_very_long_domain(self):
        """Test with very long domain name."""
        long_domain = "very.long.subdomain.with.many.parts.example.com"
        cmd = self.tool.build_command(long_domain, {})
        self.assertIn(long_domain, cmd)

    def test_additional_args_with_paths(self):
        """Test additional args with file paths."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-o /tmp/output.txt -config /etc/config.yaml"
        })
        self.assertIn("-o", cmd)
        self.assertIn("/tmp/output.txt", cmd)

    def test_mixed_case_domain(self):
        """Test with mixed case domain."""
        cmd = self.tool.build_command("Example.COM", {})
        self.assertIn("Example.COM", cmd)


class TestSubfinderIntegration(unittest.TestCase):
    """Integration tests for SubfinderTool."""

    def test_realistic_basic_enumeration(self):
        """Test realistic basic enumeration scenario."""
        tool = SubfinderTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": """www.example.com
mail.example.com
ftp.example.com
blog.example.com
shop.example.com
api.example.com""",
            "stderr": "",
            "returncode": 0,
            "execution_time": 12.3,
            "cached": False
        })

        result = tool.execute("example.com", {}, mock_execute)

        self.assertTrue(result["success"])
        self.assertIn("www.example.com", result["output"]["raw_output"])
        self.assertIn("api.example.com", result["output"]["raw_output"])

    def test_realistic_silent_mode(self):
        """Test realistic silent mode execution."""
        tool = SubfinderTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": "sub1.example.com\nsub2.example.com",
            "stderr": "",
            "returncode": 0,
            "execution_time": 8.7
        })

        result = tool.execute(
            "example.com",
            {"additional_args": "-silent"},
            mock_execute
        )

        self.assertTrue(result["success"])
        self.assertIn("-silent", result["command"])

    def test_realistic_error_handling(self):
        """Test realistic error scenario."""
        tool = SubfinderTool()
        mock_execute = Mock(return_value={
            "success": False,
            "error": "Network timeout",
            "stderr": "Error: failed to connect to sources",
            "returncode": 1
        })

        result = tool.execute("example.com", {}, mock_execute)

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_realistic_recursive_enumeration(self):
        """Test realistic recursive enumeration."""
        tool = SubfinderTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": "deep.sub.example.com\ndeeper.deep.sub.example.com",
            "stderr": "",
            "returncode": 0,
            "execution_time": 45.2
        })

        result = tool.execute(
            "example.com",
            {"additional_args": "-recursive"},
            mock_execute
        )

        self.assertTrue(result["success"])
        self.assertIn("-recursive", result["command"])


if __name__ == '__main__':
    unittest.main()
