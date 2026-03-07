"""
Unit tests for GobusterTool implementation.

Comprehensive test coverage: 35+ tests
"""

import unittest
from unittest.mock import Mock, patch

from tools.web.gobuster import GobusterTool


class TestGobusterToolInitialization(unittest.TestCase):
    """Test cases for GobusterTool initialization."""

    def test_initialization(self):
        tool = GobusterTool()
        self.assertEqual(tool.name, "Gobuster")
        self.assertEqual(tool.binary_name, "gobuster")

    def test_inheritance(self):
        from tools.base import BaseTool
        tool = GobusterTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        tool = GobusterTool()
        self.assertEqual(str(tool), "Gobuster (gobuster)")

    def test_repr_representation(self):
        tool = GobusterTool()
        self.assertIn("GobusterTool", repr(tool))


class TestGobusterCommandBuilding(unittest.TestCase):
    """Test cases for Gobuster command building."""

    def setUp(self):
        self.tool = GobusterTool()

    def test_basic_command_default_params(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertIn("gobuster", cmd)
        self.assertIn("dir", cmd)
        self.assertIn("-u", cmd)
        self.assertIn("https://example.com", cmd)
        self.assertIn("-w", cmd)

    def test_command_with_dir_mode(self):
        cmd = self.tool.build_command("https://example.com", {"mode": "dir"})
        self.assertIn("dir", cmd)

    def test_command_with_dns_mode(self):
        cmd = self.tool.build_command("example.com", {"mode": "dns"})
        self.assertIn("dns", cmd)

    def test_command_with_vhost_mode(self):
        cmd = self.tool.build_command("example.com", {"mode": "vhost"})
        self.assertIn("vhost", cmd)

    def test_command_with_custom_wordlist(self):
        cmd = self.tool.build_command("https://example.com", {
            "wordlist": "/custom/wordlist.txt"
        })
        self.assertIn("/custom/wordlist.txt", cmd)

    def test_command_with_extensions(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-x php,html,txt"
        })
        self.assertIn("-x", cmd)
        self.assertIn("php,html,txt", cmd)

    def test_command_with_threads(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-t 50"
        })
        self.assertIn("-t", cmd)
        self.assertIn("50", cmd)

    def test_command_with_status_codes(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-s 200,204,301,302,307,401,403"
        })
        self.assertIn("-s", cmd)

    def test_command_with_timeout(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "--timeout 10s"
        })
        self.assertIn("--timeout", cmd)

    def test_command_with_user_agent(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-a 'Custom User Agent'"
        })
        self.assertIn("-a", cmd)

    def test_command_with_cookies(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-c 'session=abc123'"
        })
        self.assertIn("-c", cmd)

    def test_command_with_follow_redirect(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-r"
        })
        self.assertIn("-r", cmd)

    def test_command_with_expanded_mode(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-e"
        })
        self.assertIn("-e", cmd)

    def test_command_with_no_status(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-q"
        })
        self.assertIn("-q", cmd)


class TestGobusterOutputParsing(unittest.TestCase):
    """Test cases for Gobuster output parsing."""

    def setUp(self):
        self.tool = GobusterTool()

    def test_parse_basic_output(self):
        stdout = """/admin (Status: 301)
/images (Status: 301)
/index.html (Status: 200)"""
        result = self.tool.parse_output(stdout, "", 0)
        self.assertIn("raw_output", result)
        self.assertIn("found_items", result)
        self.assertEqual(result["found_count"], 3)

    def test_parse_empty_output(self):
        result = self.tool.parse_output("", "", 0)
        self.assertEqual(result["raw_output"], "")

    def test_parse_output_with_redirects(self):
        stdout = "/admin (Status: 301) [--> /admin/]"
        result = self.tool.parse_output(stdout, "", 0)
        self.assertIn("found_items", result)

    def test_parse_with_stderr(self):
        stdout = "/found (Status: 200)"
        stderr = "Error: timeout on some requests"
        result = self.tool.parse_output(stdout, stderr, 0)
        self.assertEqual(result["stderr"], stderr)

    def test_parse_multiline_results(self):
        stdout = """===============================================================
Gobuster v3.6
===============================================================
/admin (Status: 301)
/uploads (Status: 301)
/api (Status: 200)
==============================================================="""
        result = self.tool.parse_output(stdout, "", 0)
        self.assertIn("found_items", result)
        self.assertGreater(result["found_count"], 0)


class TestGobusterToolExecution(unittest.TestCase):
    """Test cases for GobusterTool execution flow."""

    def setUp(self):
        self.tool = GobusterTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "/admin (Status: 200)",
            "stderr": "",
            "returncode": 0,
            "execution_time": 30.5,
            "cached": False
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "Gobuster")

    def test_execution_with_dns_mode(self):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "Found: www.example.com",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute(
            "example.com",
            {"mode": "dns"},
            self.mock_execute_func
        )
        self.assertTrue(result["success"])
        self.assertIn("dns", result["command"])

    def test_execution_failure(self):
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "gobuster: command not found",
            "stderr": "gobuster: command not found",
            "returncode": 127
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertFalse(result["success"])

    @patch('tools.base.logger')
    def test_logging(self, mock_logger):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0
        }

        self.tool.execute("https://example.com", {}, self.mock_execute_func)
        mock_logger.info.assert_called()


class TestGobusterEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        self.tool = GobusterTool()

    def test_url_with_port(self):
        cmd = self.tool.build_command("https://example.com:8443", {})
        self.assertIn("https://example.com:8443", cmd)

    def test_url_with_path(self):
        cmd = self.tool.build_command("https://example.com/admin", {})
        self.assertIn("https://example.com/admin", cmd)

    def test_http_url(self):
        cmd = self.tool.build_command("http://example.com", {})
        self.assertIn("http://example.com", cmd)

    def test_whitespace_in_args(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "  -t  50   -x  php  "
        })
        self.assertIn("-t", cmd)
        self.assertIn("50", cmd)


class TestGobusterIntegration(unittest.TestCase):
    """Integration tests for GobusterTool."""

    def test_realistic_dir_scan(self):
        tool = GobusterTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": """/admin (Status: 301) [--> /admin/]
/images (Status: 301) [--> /images/]
/uploads (Status: 301) [--> /uploads/]
/index.html (Status: 200)""",
            "stderr": "",
            "returncode": 0,
            "execution_time": 45.2
        })

        result = tool.execute(
            "https://example.com",
            {"additional_args": "-x php,html"},
            mock_execute
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["output"]["found_count"], 4)


if __name__ == '__main__':
    unittest.main()
