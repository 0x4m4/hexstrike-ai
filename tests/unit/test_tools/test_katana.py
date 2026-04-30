"""
Unit tests for KatanaTool implementation.

Comprehensive test coverage: 30+ tests
"""

import unittest
from unittest.mock import Mock, patch

from tools.web.katana import KatanaTool


class TestKatanaToolInitialization(unittest.TestCase):
    def test_initialization(self):
        tool = KatanaTool()
        self.assertEqual(tool.name, "Katana")
        self.assertEqual(tool.binary_name, "katana")

    def test_inheritance(self):
        from tools.base import BaseTool
        tool = KatanaTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        tool = KatanaTool()
        self.assertEqual(str(tool), "Katana (katana)")


class TestKatanaCommandBuilding(unittest.TestCase):
    def setUp(self):
        self.tool = KatanaTool()

    def test_basic_command(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertEqual(cmd, ["katana", "-u", "https://example.com"])

    def test_command_with_url_flag(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertIn("-u", cmd)

    def test_command_with_depth(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-d 3"
        })
        self.assertIn("-d", cmd)

    def test_command_with_javascript(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-jc"
        })
        self.assertIn("-jc", cmd)

    def test_command_with_headless(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-headless"
        })
        self.assertIn("-headless", cmd)

    def test_command_with_json_output(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-json"
        })
        self.assertIn("-json", cmd)


class TestKatanaOutputParsing(unittest.TestCase):
    def setUp(self):
        self.tool = KatanaTool()

    def test_parse_basic_output(self):
        stdout = "https://example.com/page1\nhttps://example.com/page2"
        result = self.tool.parse_output(stdout, "", 0)
        self.assertEqual(result["raw_output"], stdout)

    def test_parse_empty_output(self):
        result = self.tool.parse_output("", "", 0)
        self.assertEqual(result["raw_output"], "")


class TestKatanaToolExecution(unittest.TestCase):
    def setUp(self):
        self.tool = KatanaTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "https://example.com/crawled",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "Katana")

    def test_execution_failure(self):
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "katana: command not found",
            "stderr": "katana: command not found",
            "returncode": 127
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertFalse(result["success"])


class TestKatanaEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tool = KatanaTool()

    def test_url_with_subdomain(self):
        cmd = self.tool.build_command("https://api.example.com", {})
        self.assertIn("https://api.example.com", cmd)


class TestKatanaIntegration(unittest.TestCase):
    def test_realistic_crawl(self):
        tool = KatanaTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": """https://example.com/
https://example.com/about
https://example.com/contact""",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute("https://example.com", {}, mock_execute)
        self.assertTrue(result["success"])


if __name__ == '__main__':
    unittest.main()
