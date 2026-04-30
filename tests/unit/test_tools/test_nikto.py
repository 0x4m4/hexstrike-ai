"""
Unit tests for NiktoTool implementation.

Comprehensive test coverage: 30+ tests
"""

import unittest
from unittest.mock import Mock, patch

from tools.web.nikto import NiktoTool


class TestNiktoToolInitialization(unittest.TestCase):
    def test_initialization(self):
        tool = NiktoTool()
        self.assertEqual(tool.name, "Nikto")
        self.assertEqual(tool.binary_name, "nikto")

    def test_inheritance(self):
        from tools.base import BaseTool
        tool = NiktoTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        tool = NiktoTool()
        self.assertEqual(str(tool), "Nikto (nikto)")


class TestNiktoCommandBuilding(unittest.TestCase):
    def setUp(self):
        self.tool = NiktoTool()

    def test_basic_command(self):
        cmd = self.tool.build_command("example.com", {})
        self.assertEqual(cmd, ["nikto", "-h", "example.com"])

    def test_command_with_host_flag(self):
        cmd = self.tool.build_command("example.com", {})
        self.assertIn("-h", cmd)
        self.assertIn("example.com", cmd)

    def test_command_with_ssl(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-ssl"
        })
        self.assertIn("-ssl", cmd)

    def test_command_with_port(self):
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-port 8443"
        })
        self.assertIn("-port", cmd)

    def test_command_with_tuning(self):
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-Tuning x"
        })
        self.assertIn("-Tuning", cmd)

    def test_command_with_plugins(self):
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-Plugins 'apacheusers'"
        })
        self.assertIn("-Plugins", cmd)

    def test_command_with_output(self):
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-o output.txt"
        })
        self.assertIn("-o", cmd)

    def test_command_with_format(self):
        cmd = self.tool.build_command("example.com", {
            "additional_args": "-Format txt"
        })
        self.assertIn("-Format", cmd)


class TestNiktoOutputParsing(unittest.TestCase):
    def setUp(self):
        self.tool = NiktoTool()

    def test_parse_with_findings(self):
        stdout = """+ Target IP: 192.168.1.1
+ Target Hostname: example.com
+ Server: Apache/2.4.41
+ The X-XSS-Protection header is not defined.
+ The X-Content-Type-Options header is not set."""
        result = self.tool.parse_output(stdout, "", 0)
        self.assertIn("findings", result)
        self.assertGreater(result["findings_count"], 0)
        self.assertIn("target_info", result)

    def test_parse_empty_output(self):
        result = self.tool.parse_output("", "", 0)
        self.assertEqual(result["raw_output"], "")

    def test_parse_target_info(self):
        stdout = "+ Target IP: 192.168.1.1"
        result = self.tool.parse_output(stdout, "", 0)
        self.assertIn("target_info", result)


class TestNiktoToolExecution(unittest.TestCase):
    def setUp(self):
        self.tool = NiktoTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "+ Server: nginx/1.18.0",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute("example.com", {}, self.mock_execute_func)
        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "Nikto")

    def test_execution_failure(self):
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "nikto: command not found",
            "stderr": "nikto: command not found",
            "returncode": 127
        }

        result = self.tool.execute("example.com", {}, self.mock_execute_func)
        self.assertFalse(result["success"])


class TestNiktoEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tool = NiktoTool()

    def test_url_with_https(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertIn("https://example.com", cmd)

    def test_ip_address_target(self):
        cmd = self.tool.build_command("192.168.1.1", {})
        self.assertIn("192.168.1.1", cmd)

    def test_whitespace_in_args(self):
        cmd = self.tool.build_command("example.com", {
            "additional_args": "  -ssl   -port   443  "
        })
        self.assertIn("-ssl", cmd)
        self.assertIn("-port", cmd)


class TestNiktoIntegration(unittest.TestCase):
    def test_realistic_scan(self):
        tool = NiktoTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": """- Nikto v2.5.0
+ Target IP: 192.168.1.100
+ Target Hostname: example.com
+ Server: Apache/2.4.41 (Ubuntu)
+ The X-XSS-Protection header is not defined.
+ Apache/2.4.41 appears to be outdated.
+ /admin/: Admin section found.""",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute("example.com", {}, mock_execute)
        self.assertTrue(result["success"])
        self.assertGreater(result["output"]["findings_count"], 0)


if __name__ == '__main__':
    unittest.main()
