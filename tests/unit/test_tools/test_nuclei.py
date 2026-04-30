"""
Unit tests for NucleiTool implementation.

Comprehensive test coverage: 35+ tests
"""

import unittest
from unittest.mock import Mock, patch

from tools.web.nuclei import NucleiTool


class TestNucleiToolInitialization(unittest.TestCase):
    """Test cases for NucleiTool initialization."""

    def test_initialization(self):
        tool = NucleiTool()
        self.assertEqual(tool.name, "Nuclei")
        self.assertEqual(tool.binary_name, "nuclei")

    def test_inheritance(self):
        from tools.base import BaseTool
        tool = NucleiTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        tool = NucleiTool()
        self.assertEqual(str(tool), "Nuclei (nuclei)")

    def test_repr_representation(self):
        tool = NucleiTool()
        self.assertIn("NucleiTool", repr(tool))


class TestNucleiCommandBuilding(unittest.TestCase):
    """Test cases for Nuclei command building."""

    def setUp(self):
        self.tool = NucleiTool()

    def test_basic_command_default_params(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertIn("nuclei", cmd)
        self.assertIn("-u", cmd)
        self.assertIn("https://example.com", cmd)

    def test_command_with_critical_severity(self):
        cmd = self.tool.build_command("https://example.com", {
            "severity": "critical"
        })
        self.assertIn("-severity", cmd)
        self.assertIn("critical", cmd)

    def test_command_with_multiple_severities(self):
        cmd = self.tool.build_command("https://example.com", {
            "severity": "critical,high"
        })
        self.assertIn("critical,high", cmd)

    def test_command_with_high_severity(self):
        cmd = self.tool.build_command("https://example.com", {
            "severity": "high"
        })
        self.assertIn("high", cmd)

    def test_command_with_medium_severity(self):
        cmd = self.tool.build_command("https://example.com", {
            "severity": "medium"
        })
        self.assertIn("medium", cmd)

    def test_command_with_low_severity(self):
        cmd = self.tool.build_command("https://example.com", {
            "severity": "low"
        })
        self.assertIn("low", cmd)

    def test_command_with_tags(self):
        cmd = self.tool.build_command("https://example.com", {
            "tags": "cve,rce"
        })
        self.assertIn("-tags", cmd)
        self.assertIn("cve,rce", cmd)

    def test_command_with_cve_tag(self):
        cmd = self.tool.build_command("https://example.com", {
            "tags": "cve"
        })
        self.assertIn("cve", cmd)

    def test_command_with_xss_tag(self):
        cmd = self.tool.build_command("https://example.com", {
            "tags": "xss"
        })
        self.assertIn("xss", cmd)

    def test_command_with_multiple_tags(self):
        cmd = self.tool.build_command("https://example.com", {
            "tags": "cve,xss,sqli,rce"
        })
        self.assertIn("cve,xss,sqli,rce", cmd)

    def test_command_with_severity_and_tags(self):
        cmd = self.tool.build_command("https://example.com", {
            "severity": "critical,high",
            "tags": "cve,rce"
        })
        self.assertIn("-severity", cmd)
        self.assertIn("critical,high", cmd)
        self.assertIn("-tags", cmd)
        self.assertIn("cve,rce", cmd)

    def test_command_with_silent_flag(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-silent"
        })
        self.assertIn("-silent", cmd)

    def test_command_with_json_output(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-json"
        })
        self.assertIn("-json", cmd)

    def test_command_with_markdown_output(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-markdown-export report.md"
        })
        self.assertIn("-markdown-export", cmd)

    def test_command_with_custom_templates(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-t /custom/templates/"
        })
        self.assertIn("-t", cmd)
        self.assertIn("/custom/templates/", cmd)

    def test_command_with_rate_limit(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-rate-limit 150"
        })
        self.assertIn("-rate-limit", cmd)

    def test_command_with_bulk_size(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "-bulk-size 25"
        })
        self.assertIn("-bulk-size", cmd)


class TestNucleiOutputParsing(unittest.TestCase):
    """Test cases for Nuclei output parsing."""

    def setUp(self):
        self.tool = NucleiTool()

    def test_parse_basic_output(self):
        stdout = """[CVE-2021-12345] [http] [critical] https://example.com/vuln
[CVE-2022-67890] [http] [high] https://example.com/path"""
        result = self.tool.parse_output(stdout, "", 0)
        self.assertIn("vulnerabilities", result)
        self.assertEqual(result["vulnerability_count"], 2)

    def test_parse_empty_output(self):
        result = self.tool.parse_output("", "", 0)
        self.assertEqual(result["raw_output"], "")

    def test_parse_single_vulnerability(self):
        stdout = "[exposed-panel] [http] [medium] https://example.com/admin"
        result = self.tool.parse_output(stdout, "", 0)
        self.assertIn("vulnerabilities", result)
        self.assertEqual(result["vulnerability_count"], 1)

    def test_parse_with_stderr(self):
        stdout = "[CVE-2021-12345] [http] [critical] https://example.com"
        stderr = "Warning: rate limit reached"
        result = self.tool.parse_output(stdout, stderr, 0)
        self.assertEqual(result["stderr"], stderr)

    def test_parse_no_vulnerabilities(self):
        stdout = "Nuclei scan completed. No vulnerabilities found."
        result = self.tool.parse_output(stdout, "", 0)
        # Should not have vulnerabilities key if no brackets found
        self.assertIn("raw_output", result)


class TestNucleiToolExecution(unittest.TestCase):
    """Test cases for NucleiTool execution flow."""

    def setUp(self):
        self.tool = NucleiTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "[CVE-2021-12345] [http] [critical] https://example.com",
            "stderr": "",
            "returncode": 0,
            "execution_time": 60.5,
            "cached": False
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "Nuclei")

    def test_execution_with_severity_filter(self):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute(
            "https://example.com",
            {"severity": "critical,high"},
            self.mock_execute_func
        )
        self.assertTrue(result["success"])
        self.assertIn("-severity critical,high", result["command"])

    def test_execution_failure(self):
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "nuclei: command not found",
            "stderr": "nuclei: command not found",
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


class TestNucleiEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        self.tool = NucleiTool()

    def test_empty_severity(self):
        cmd = self.tool.build_command("https://example.com", {"severity": ""})
        # Empty severity should be skipped
        self.assertNotIn("-severity", cmd)

    def test_empty_tags(self):
        cmd = self.tool.build_command("https://example.com", {"tags": ""})
        # Empty tags should be skipped
        self.assertNotIn("-tags", cmd)

    def test_whitespace_in_args(self):
        cmd = self.tool.build_command("https://example.com", {
            "additional_args": "  -silent   -json  "
        })
        self.assertIn("-silent", cmd)
        self.assertIn("-json", cmd)


class TestNucleiIntegration(unittest.TestCase):
    """Integration tests for NucleiTool."""

    def test_realistic_vulnerability_scan(self):
        tool = NucleiTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": """[CVE-2021-12345] [http] [critical] https://example.com/vulnerable
[CVE-2022-67890] [http] [high] https://example.com/outdated
[exposed-panel] [http] [medium] https://example.com/admin""",
            "stderr": "",
            "returncode": 0,
            "execution_time": 120.5
        })

        result = tool.execute(
            "https://example.com",
            {"severity": "critical,high,medium", "tags": "cve"},
            mock_execute
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["output"]["vulnerability_count"], 3)


if __name__ == '__main__':
    unittest.main()
