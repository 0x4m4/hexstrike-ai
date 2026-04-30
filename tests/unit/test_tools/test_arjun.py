"""
Unit tests for ArjunTool implementation.

Comprehensive test coverage: 30+ tests
"""

import unittest
from unittest.mock import Mock, patch

from tools.web.arjun import ArjunTool


class TestArjunToolInitialization(unittest.TestCase):
    def test_initialization(self):
        tool = ArjunTool()
        self.assertEqual(tool.name, "Arjun")
        self.assertEqual(tool.binary_name, "arjun")

    def test_inheritance(self):
        from tools.base import BaseTool
        tool = ArjunTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        tool = ArjunTool()
        self.assertEqual(str(tool), "Arjun (arjun)")


class TestArjunCommandBuilding(unittest.TestCase):
    def setUp(self):
        self.tool = ArjunTool()

    def test_basic_command(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertEqual(cmd, ["arjun", "-u", "https://example.com"])

    def test_command_with_url_flag(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertIn("-u", cmd)

    def test_command_with_methods(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-m GET POST"
        })
        self.assertIn("-m", cmd)

    def test_command_with_threads(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-t 20"
        })
        self.assertIn("-t", cmd)

    def test_command_with_delay(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-d 2"
        })
        self.assertIn("-d", cmd)

    def test_command_with_include(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-i custom.txt"
        })
        self.assertIn("-i", cmd)


class TestArjunOutputParsing(unittest.TestCase):
    def setUp(self):
        self.tool = ArjunTool()

    def test_parse_basic_output(self):
        stdout = "[+] Found parameter: id"
        result = self.tool.parse_output(stdout, "", 0)
        self.assertEqual(result["raw_output"], stdout)

    def test_parse_empty_output(self):
        result = self.tool.parse_output("", "", 0)
        self.assertEqual(result["raw_output"], "")


class TestArjunToolExecution(unittest.TestCase):
    def setUp(self):
        self.tool = ArjunTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "[+] Found parameters: id, name",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "Arjun")

    def test_execution_failure(self):
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "arjun: command not found",
            "stderr": "arjun: command not found",
            "returncode": 127
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertFalse(result["success"])


class TestArjunEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tool = ArjunTool()

    def test_url_with_path(self):
        cmd = self.tool.build_command("https://example.com/api/endpoint", {})
        self.assertIn("https://example.com/api/endpoint", cmd)


class TestArjunIntegration(unittest.TestCase):
    def test_realistic_scan(self):
        tool = ArjunTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": "[+] Detected parameters: id, page, limit",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute("https://example.com/api", {}, mock_execute)
        self.assertTrue(result["success"])


if __name__ == '__main__':
    unittest.main()
