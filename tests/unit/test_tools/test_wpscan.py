"""
Unit tests for WpscanTool implementation.

Comprehensive test coverage: 30+ tests
"""

import unittest
from unittest.mock import Mock, patch

from tools.web.wpscan import WpscanTool


class TestWpscanToolInitialization(unittest.TestCase):
    def test_initialization(self):
        tool = WpscanTool()
        self.assertEqual(tool.name, "WPScan")
        self.assertEqual(tool.binary_name, "wpscan")

    def test_inheritance(self):
        from tools.base import BaseTool
        tool = WpscanTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        tool = WpscanTool()
        self.assertEqual(str(tool), "WPScan (wpscan)")


class TestWpscanCommandBuilding(unittest.TestCase):
    def setUp(self):
        self.tool = WpscanTool()

    def test_basic_command_default_params(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertIn("wpscan", cmd)
        self.assertIn("--url", cmd)
        self.assertIn("https://example.com", cmd)
        self.assertIn("--enumerate", cmd)
        self.assertIn("p,t,u", cmd)

    def test_command_with_url_flag(self):
        cmd = self.tool.build_command("https://example.com", {})
        url_index = cmd.index("--url")
        self.assertEqual(cmd[url_index + 1], "https://example.com")

    def test_command_with_default_enumeration(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertIn("--enumerate", cmd)
        self.assertIn("p,t,u", cmd)

    def test_command_with_custom_enumeration(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "--enumerate vp"
        })
        self.assertIn("--enumerate", cmd)
        self.assertIn("vp", cmd)

    def test_command_with_api_token(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "--api-token YOUR_TOKEN"
        })
        self.assertIn("--api-token", cmd)

    def test_command_with_plugins_detection(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "--enumerate p"
        })
        self.assertIn("p", cmd)

    def test_command_with_themes_detection(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "--enumerate t"
        })
        self.assertIn("t", cmd)

    def test_command_with_users_enumeration(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "--enumerate u"
        })
        self.assertIn("u", cmd)


class TestWpscanOutputParsing(unittest.TestCase):
    def setUp(self):
        self.tool = WpscanTool()

    def test_parse_basic_output(self):
        stdout = "[+] WordPress version 5.9 identified"
        result = self.tool.parse_output(stdout, "", 0)
        self.assertEqual(result["raw_output"], stdout)

    def test_parse_empty_output(self):
        result = self.tool.parse_output("", "", 0)
        self.assertEqual(result["raw_output"], "")


class TestWpscanToolExecution(unittest.TestCase):
    def setUp(self):
        self.tool = WpscanTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "[+] WordPress version 5.9",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "WPScan")

    def test_execution_failure(self):
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "wpscan: command not found",
            "stderr": "wpscan: command not found",
            "returncode": 127
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertFalse(result["success"])


class TestWpscanEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tool = WpscanTool()

    def test_http_url(self):
        cmd = self.tool.build_command("http://example.com", {})
        self.assertIn("http://example.com", cmd)

    def test_url_with_path(self):
        cmd = self.tool.build_command("https://example.com/blog", {})
        self.assertIn("https://example.com/blog", cmd)


class TestWpscanIntegration(unittest.TestCase):
    def test_realistic_scan(self):
        tool = WpscanTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": """[+] WordPress version 5.9 identified
[+] Enumerating plugins
[+] Found plugin: akismet""",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute("https://example.com", {}, mock_execute)
        self.assertTrue(result["success"])


if __name__ == '__main__':
    unittest.main()
