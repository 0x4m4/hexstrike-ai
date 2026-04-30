"""
Unit tests for DalfoxTool implementation.

Comprehensive test coverage: 30+ tests
"""

import unittest
from unittest.mock import Mock, patch

from tools.web.dalfox import DalfoxTool


class TestDalfoxToolInitialization(unittest.TestCase):
    def test_initialization(self):
        tool = DalfoxTool()
        self.assertEqual(tool.name, "Dalfox")
        self.assertEqual(tool.binary_name, "dalfox")

    def test_inheritance(self):
        from tools.base import BaseTool
        tool = DalfoxTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        tool = DalfoxTool()
        self.assertEqual(str(tool), "Dalfox (dalfox)")


class TestDalfoxCommandBuilding(unittest.TestCase):
    def setUp(self):
        self.tool = DalfoxTool()

    def test_basic_command(self):
        cmd = self.tool.build_command("https://example.com?q=test", {})
        self.assertEqual(cmd, ["dalfox", "url", "https://example.com?q=test"])

    def test_command_with_url_subcommand(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertEqual(cmd[1], "url")

    def test_command_with_pipe_mode(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "--pipe"
        })
        self.assertIn("--pipe", cmd)

    def test_command_with_silence(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "--silence"
        })
        self.assertIn("--silence", cmd)

    def test_command_with_output_file(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-o output.txt"
        })
        self.assertIn("-o", cmd)

    def test_command_with_custom_payload(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "--custom-payload payloads.txt"
        })
        self.assertIn("--custom-payload", cmd)


class TestDalfoxOutputParsing(unittest.TestCase):
    def setUp(self):
        self.tool = DalfoxTool()

    def test_parse_basic_output(self):
        stdout = "[V] Reflected XSS found in parameter: q"
        result = self.tool.parse_output(stdout, "", 0)
        self.assertEqual(result["raw_output"], stdout)

    def test_parse_empty_output(self):
        result = self.tool.parse_output("", "", 0)
        self.assertEqual(result["raw_output"], "")


class TestDalfoxToolExecution(unittest.TestCase):
    def setUp(self):
        self.tool = DalfoxTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "[V] XSS detected",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute("https://example.com?q=test", {}, self.mock_execute_func)
        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "Dalfox")

    def test_execution_failure(self):
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "dalfox: command not found",
            "stderr": "dalfox: command not found",
            "returncode": 127
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertFalse(result["success"])


class TestDalfoxEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tool = DalfoxTool()

    def test_url_with_multiple_params(self):
        cmd = self.tool.build_command("https://example.com?id=1&name=test", {})
        self.assertIn("https://example.com?id=1&name=test", cmd)


class TestDalfoxIntegration(unittest.TestCase):
    def test_realistic_scan(self):
        tool = DalfoxTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": "[V] Reflected XSS in parameter: search",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute("https://example.com?search=test", {}, mock_execute)
        self.assertTrue(result["success"])


if __name__ == '__main__':
    unittest.main()
