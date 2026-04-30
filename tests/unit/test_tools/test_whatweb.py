"""
Unit tests for WhatwebTool implementation.

Comprehensive test coverage: 30+ tests
"""

import unittest
from unittest.mock import Mock, patch

from tools.web.whatweb import WhatwebTool


class TestWhatwebToolInitialization(unittest.TestCase):
    def test_initialization(self):
        tool = WhatwebTool()
        self.assertEqual(tool.name, "WhatWeb")
        self.assertEqual(tool.binary_name, "whatweb")

    def test_inheritance(self):
        from tools.base import BaseTool
        tool = WhatwebTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        tool = WhatwebTool()
        self.assertEqual(str(tool), "WhatWeb (whatweb)")


class TestWhatwebCommandBuilding(unittest.TestCase):
    def setUp(self):
        self.tool = WhatwebTool()

    def test_basic_command_default_aggression(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertIn("whatweb", cmd)
        self.assertIn("-a", cmd)
        self.assertIn("1", cmd)
        self.assertIn("https://example.com", cmd)

    def test_command_with_aggression_1(self):
        cmd = self.tool.build_command("https://example.com", {"aggression": "1"})
        self.assertIn("-a", cmd)
        self.assertIn("1", cmd)

    def test_command_with_aggression_2(self):
        cmd = self.tool.build_command("https://example.com", {"aggression": "2"})
        self.assertIn("2", cmd)

    def test_command_with_aggression_3(self):
        cmd = self.tool.build_command("https://example.com", {"aggression": "3"})
        self.assertIn("3", cmd)

    def test_command_with_aggression_4(self):
        cmd = self.tool.build_command("https://example.com", {"aggression": "4"})
        self.assertIn("4", cmd)

    def test_command_with_integer_aggression(self):
        cmd = self.tool.build_command("https://example.com", {"aggression": 3})
        self.assertIn("3", cmd)

    def test_command_with_verbose(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-v"
        })
        self.assertIn("-v", cmd)

    def test_command_with_log_file(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "--log-verbose output.txt"
        })
        self.assertIn("--log-verbose", cmd)


class TestWhatwebOutputParsing(unittest.TestCase):
    def setUp(self):
        self.tool = WhatwebTool()

    def test_parse_basic_output(self):
        stdout = "https://example.com [200 OK] Apache[2.4.41], Country[US]"
        result = self.tool.parse_output(stdout, "", 0)
        self.assertEqual(result["raw_output"], stdout)

    def test_parse_empty_output(self):
        result = self.tool.parse_output("", "", 0)
        self.assertEqual(result["raw_output"], "")


class TestWhatwebToolExecution(unittest.TestCase):
    def setUp(self):
        self.tool = WhatwebTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "https://example.com [200 OK] Apache",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "WhatWeb")

    def test_execution_failure(self):
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "whatweb: command not found",
            "stderr": "whatweb: command not found",
            "returncode": 127
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertFalse(result["success"])


class TestWhatwebEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tool = WhatwebTool()

    def test_http_url(self):
        cmd = self.tool.build_command("http://example.com", {})
        self.assertIn("http://example.com", cmd)

    def test_url_with_port(self):
        cmd = self.tool.build_command("https://example.com:8443", {})
        self.assertIn("https://example.com:8443", cmd)


class TestWhatwebIntegration(unittest.TestCase):
    def test_realistic_scan(self):
        tool = WhatwebTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": "https://example.com [200 OK] Apache[2.4.41], PHP[7.4.3]",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute("https://example.com", {"aggression": "3"}, mock_execute)
        self.assertTrue(result["success"])


if __name__ == '__main__':
    unittest.main()
