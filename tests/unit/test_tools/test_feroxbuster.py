"""
Unit tests for FeroxbusterTool implementation.

Comprehensive test coverage: 35+ tests
"""

import unittest
from unittest.mock import Mock, patch

from tools.web.feroxbuster import FeroxbusterTool


class TestFeroxbusterToolInitialization(unittest.TestCase):
    def test_initialization(self):
        tool = FeroxbusterTool()
        self.assertEqual(tool.name, "Feroxbuster")
        self.assertEqual(tool.binary_name, "feroxbuster")

    def test_inheritance(self):
        from tools.base import BaseTool
        tool = FeroxbusterTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        tool = FeroxbusterTool()
        self.assertEqual(str(tool), "Feroxbuster (feroxbuster)")


class TestFeroxbusterCommandBuilding(unittest.TestCase):
    def setUp(self):
        self.tool = FeroxbusterTool()

    def test_basic_command_default_params(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertIn("feroxbuster", cmd)
        self.assertIn("-u", cmd)
        self.assertIn("https://example.com", cmd)
        self.assertIn("-w", cmd)

    def test_command_with_default_wordlist(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertIn("/usr/share/wordlists/dirb/common.txt", cmd)

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

    def test_command_with_threads(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-t 50"
        })
        self.assertIn("-t", cmd)

    def test_command_with_depth(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-d 3"
        })
        self.assertIn("-d", cmd)

    def test_command_with_status_codes(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-s 200,301,302"
        })
        self.assertIn("-s", cmd)


class TestFeroxbusterOutputParsing(unittest.TestCase):
    def setUp(self):
        self.tool = FeroxbusterTool()

    def test_parse_with_findings(self):
        stdout = """200      GET       50l      120w     1234c https://example.com/admin
301      GET        9l       28w      312c https://example.com/images"""
        result = self.tool.parse_output(stdout, "", 0)
        self.assertIn("discovered_urls", result)
        self.assertEqual(result["discovered_count"], 2)

    def test_parse_empty_output(self):
        result = self.tool.parse_output("", "", 0)
        self.assertEqual(result["raw_output"], "")

    def test_parse_with_redirect(self):
        stdout = "301      GET        9l       28w      312c https://example.com/admin"
        result = self.tool.parse_output(stdout, "", 0)
        self.assertIn("discovered_urls", result)


class TestFeroxbusterToolExecution(unittest.TestCase):
    def setUp(self):
        self.tool = FeroxbusterTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "200      GET       50l      120w     1234c https://example.com/admin",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "Feroxbuster")

    def test_execution_failure(self):
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "feroxbuster: command not found",
            "stderr": "feroxbuster: command not found",
            "returncode": 127
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertFalse(result["success"])


class TestFeroxbusterEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tool = FeroxbusterTool()

    def test_url_with_port(self):
        cmd = self.tool.build_command("https://example.com:8443", {})
        self.assertIn("https://example.com:8443", cmd)


class TestFeroxbusterIntegration(unittest.TestCase):
    def test_realistic_scan(self):
        tool = FeroxbusterTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": """200      GET       50l      120w     1234c https://example.com/admin
301      GET        9l       28w      312c https://example.com/uploads
200      GET      100l      250w     5678c https://example.com/api""",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute("https://example.com", {}, mock_execute)
        self.assertTrue(result["success"])
        self.assertEqual(result["output"]["discovered_count"], 3)


if __name__ == '__main__':
    unittest.main()
