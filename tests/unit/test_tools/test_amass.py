"""
Unit tests for AmassTool implementation.

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

from tools.recon.amass import AmassTool


class TestAmassToolInitialization(unittest.TestCase):
    """Test cases for AmassTool initialization."""

    def test_initialization(self):
        """Test AmassTool initialization."""
        tool = AmassTool()
        self.assertEqual(tool.name, "Amass")
        self.assertEqual(tool.binary_name, "amass")

    def test_inheritance(self):
        """Test that AmassTool inherits from BaseTool."""
        from tools.base import BaseTool
        tool = AmassTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        """Test string representation."""
        tool = AmassTool()
        self.assertEqual(str(tool), "Amass (amass)")

    def test_repr_representation(self):
        """Test developer representation."""
        tool = AmassTool()
        self.assertIn("AmassTool", repr(tool))
        self.assertIn("Amass", repr(tool))


class TestAmassCommandBuilding(unittest.TestCase):
    """Test cases for Amass command building."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = AmassTool()

    def test_basic_command_default_params(self):
        """Test basic command with default parameters."""
        cmd = self.tool.build_command("example.com", {})
        self.assertEqual(cmd, ["amass", "enum", "-d", "example.com"])

    def test_command_includes_enum_subcommand(self):
        """Test that command includes enum subcommand."""
        cmd = self.tool.build_command("example.com", {})
        self.assertIn("enum", cmd)
        self.assertEqual(cmd[1], "enum")

    def test_command_with_target_domain(self):
        """Test command includes target domain with -d flag."""
        cmd = self.tool.build_command("testdomain.com", {})
        self.assertIn("-d", cmd)
        self.assertIn("testdomain.com", cmd)

    def test_command_with_additional_args_passive(self):
        """Test command with passive enumeration flag."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-passive"
        })
        self.assertEqual(cmd, ["amass", "enum", "-d", "example.com", "-passive"])

    def test_command_with_additional_args_active(self):
        """Test command with active enumeration flag."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-active"
        })
        self.assertIn("-active", cmd)

    def test_command_with_brute_force(self):
        """Test command with brute force option."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-brute"
        })
        self.assertIn("-brute", cmd)

    def test_command_with_output_format(self):
        """Test command with JSON output format."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-json output.json"
        })
        self.assertIn("-json", cmd)
        self.assertIn("output.json", cmd)

    def test_command_with_multiple_additional_args(self):
        """Test command with multiple additional arguments."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-passive -timeout 30 -max-depth 3"
        })
        self.assertIn("-passive", cmd)
        self.assertIn("-timeout", cmd)
        self.assertIn("30", cmd)
        self.assertIn("-max-depth", cmd)
        self.assertIn("3", cmd)

    def test_command_with_empty_additional_args(self):
        """Test command with empty additional_args."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": ""
        })
        self.assertEqual(cmd, ["amass", "enum", "-d", "example.com"])

    def test_command_with_config_file(self):
        """Test command with configuration file."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-config /etc/amass/config.ini"
        })
        self.assertIn("-config", cmd)
        self.assertIn("/etc/amass/config.ini", cmd)

    def test_command_with_wordlist(self):
        """Test command with custom wordlist."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-w /path/to/wordlist.txt"
        })
        self.assertIn("-w", cmd)
        self.assertIn("/path/to/wordlist.txt", cmd)

    def test_command_with_data_source(self):
        """Test command with specific data sources."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-src virustotal,crtsh"
        })
        self.assertIn("-src", cmd)
        self.assertIn("virustotal,crtsh", cmd)

    def test_command_order_preserved(self):
        """Test that command argument order is preserved."""
        cmd = self.tool.build_command("example.com", {})
        # Should be: amass enum -d domain
        self.assertEqual(cmd[0], "amass")
        self.assertEqual(cmd[1], "enum")
        self.assertEqual(cmd[2], "-d")
        self.assertEqual(cmd[3], "example.com")


class TestAmassTargetVariations(unittest.TestCase):
    """Test Amass with different target variations."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = AmassTool()

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


class TestAmassOutputParsing(unittest.TestCase):
    """Test cases for Amass output parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = AmassTool()

    def test_parse_basic_output(self):
        """Test parsing basic amass output."""
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
        stderr = "Warning: API rate limit reached"

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
        subdomains = [f"sub{i}.example.com" for i in range(1000)]
        stdout = "\n".join(subdomains)

        result = self.tool.parse_output(stdout, "", 0)
        self.assertIn("raw_output", result)
        self.assertEqual(result["raw_output"], stdout)

    def test_parse_output_preserves_content(self):
        """Test that parsing preserves exact output content."""
        stdout = "  sub.example.com  \n  another.example.com  "
        result = self.tool.parse_output(stdout, "", 0)
        self.assertEqual(result["raw_output"], stdout)


class TestAmassToolExecution(unittest.TestCase):
    """Test cases for AmassTool execution flow."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = AmassTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        """Test successful amass execution."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "sub1.example.com\nsub2.example.com",
            "stderr": "",
            "returncode": 0,
            "execution_time": 15.5,
            "cached": False
        }

        result = self.tool.execute("example.com", {}, self.mock_execute_func)

        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "Amass")
        self.assertEqual(result["target"], "example.com")
        self.assertIn("amass enum", result["command"])
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
            {"additional_args": "-passive -timeout 60"},
            self.mock_execute_func
        )

        self.assertTrue(result["success"])
        self.assertIn("-passive", result["command"])
        self.assertIn("-timeout 60", result["command"])

    def test_execution_failure(self):
        """Test handling of execution failure."""
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "amass: command not found",
            "stderr": "amass: command not found",
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
        # Verify use_cache was passed to execute function
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

        # Command should be a string, not a list
        self.assertIsInstance(result["command"], str)
        self.assertIn("amass enum -d example.com", result["command"])

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
        self.assertIn("Amass", log_message)


class TestAmassEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = AmassTool()

    def test_empty_target(self):
        """Test with empty target string."""
        cmd = self.tool.build_command("", {})
        self.assertIn("", cmd)

    def test_none_in_params(self):
        """Test with None values in params."""
        cmd = self.tool.build_command("example.com", {"additional_args": None})
        # Should handle gracefully, None is falsy so should be skipped
        self.assertEqual(cmd, ["amass", "enum", "-d", "example.com"])

    def test_whitespace_in_additional_args(self):
        """Test with extra whitespace in additional_args."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": "  -passive   -timeout   30  "
        })
        # split() should handle extra whitespace
        self.assertIn("-passive", cmd)
        self.assertIn("-timeout", cmd)
        self.assertIn("30", cmd)

    def test_special_characters_in_domain(self):
        """Test domain with special characters."""
        cmd = self.tool.build_command("test-domain_123.example.com", {})
        self.assertIn("test-domain_123.example.com", cmd)

    def test_internationalized_domain(self):
        """Test with internationalized domain name (IDN)."""
        cmd = self.tool.build_command("münchen.de", {})
        self.assertIn("münchen.de", cmd)

    def test_very_long_domain(self):
        """Test with very long domain name."""
        long_domain = "very.long.subdomain.with.many.parts.example.com"
        cmd = self.tool.build_command(long_domain, {})
        self.assertIn(long_domain, cmd)

    def test_additional_args_with_quotes(self):
        """Test additional args containing quoted strings."""
        cmd = self.tool.build_command("example.com", {
            "additional_args": '-config "/path/with spaces/config.ini"'
        })
        self.assertIn("-config", cmd)


class TestAmassIntegration(unittest.TestCase):
    """Integration tests for AmassTool."""

    def test_realistic_passive_enumeration(self):
        """Test realistic passive enumeration scenario."""
        tool = AmassTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": """www.example.com
mail.example.com
ftp.example.com
blog.example.com
shop.example.com""",
            "stderr": "",
            "returncode": 0,
            "execution_time": 45.2,
            "cached": False
        })

        result = tool.execute(
            "example.com",
            {"additional_args": "-passive"},
            mock_execute
        )

        self.assertTrue(result["success"])
        self.assertIn("-passive", result["command"])
        self.assertIn("www.example.com", result["output"]["raw_output"])

    def test_realistic_active_enumeration(self):
        """Test realistic active enumeration scenario."""
        tool = AmassTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": "active enumeration output",
            "stderr": "",
            "returncode": 0,
            "execution_time": 120.5
        })

        result = tool.execute(
            "example.com",
            {"additional_args": "-active -brute"},
            mock_execute
        )

        self.assertTrue(result["success"])
        self.assertIn("-active", result["command"])
        self.assertIn("-brute", result["command"])

    def test_realistic_error_handling(self):
        """Test realistic error scenario."""
        tool = AmassTool()
        mock_execute = Mock(return_value={
            "success": False,
            "error": "Connection timeout",
            "stderr": "Error: unable to connect to data sources",
            "returncode": 1
        })

        result = tool.execute("example.com", {}, mock_execute)

        self.assertFalse(result["success"])
        self.assertIn("error", result)


if __name__ == '__main__':
    unittest.main()
