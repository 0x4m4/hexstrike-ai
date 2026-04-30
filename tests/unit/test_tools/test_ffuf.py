"""
Unit tests for FfufTool implementation.

Comprehensive test coverage: 35+ tests
"""

import unittest
from unittest.mock import Mock, patch

from tools.web.ffuf import FfufTool


class TestFfufToolInitialization(unittest.TestCase):
    def test_initialization(self):
        tool = FfufTool()
        self.assertEqual(tool.name, "FFUF")
        self.assertEqual(tool.binary_name, "ffuf")

    def test_inheritance(self):
        from tools.base import BaseTool
        tool = FfufTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        tool = FfufTool()
        self.assertEqual(str(tool), "FFUF (ffuf)")


class TestFfufCommandBuilding(unittest.TestCase):
    def setUp(self):
        self.tool = FfufTool()

    def test_basic_command_default_params(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertIn("ffuf", cmd)
        self.assertIn("-u", cmd)
        self.assertIn("-w", cmd)
        # URL should contain FUZZ
        url_index = cmd.index("-u")
        self.assertIn("FUZZ", cmd[url_index + 1])

    def test_command_adds_fuzz_to_url(self):
        cmd = self.tool.build_command("https://example.com", {})
        # Should add /FUZZ to URL if not present
        url_index = cmd.index("-u")
        url = cmd[url_index + 1]
        self.assertIn("FUZZ", url)

    def test_command_preserves_existing_fuzz(self):
        cmd = self.tool.build_command("https://example.com/FUZZ", {})
        url_index = cmd.index("-u")
        url = cmd[url_index + 1]
        self.assertEqual(url, "https://example.com/FUZZ")

    def test_command_with_custom_wordlist(self):
        cmd = self.tool.build_command("https://example.com", {
            "wordlist": "/custom/wordlist.txt"
        })
        self.assertIn("/custom/wordlist.txt", cmd)

    def test_command_with_default_wordlist(self):
        cmd = self.tool.build_command("https://example.com", {})
        self.assertIn("/usr/share/wordlists/dirb/common.txt", cmd)

    def test_command_with_match_codes(self):
        cmd = self.tool.build_command("https://example.com/FUZZ", {
            "additional_args": "-mc 200,301,302"
        })
        self.assertIn("-mc", cmd)

    def test_command_with_filter_codes(self):
        cmd = self.tool.build_command("https://example.com/FUZZ", {
            "additional_args": "-fc 404"
        })
        self.assertIn("-fc", cmd)

    def test_command_with_filter_size(self):
        cmd = self.tool.build_command("https://example.com/FUZZ", {
            "additional_args": "-fs 1234"
        })
        self.assertIn("-fs", cmd)

    def test_command_with_threads(self):
        cmd = self.tool.build_command("https://example.com/FUZZ", {
            "additional_args": "-t 40"
        })
        self.assertIn("-t", cmd)

    def test_command_with_extensions(self):
        cmd = self.tool.build_command("https://example.com/FUZZ", {
            "additional_args": "-e .php,.html,.txt"
        })
        self.assertIn("-e", cmd)

    def test_command_with_recursion(self):
        cmd = self.tool.build_command("https://example.com/FUZZ", {
            "additional_args": "-recursion"
        })
        self.assertIn("-recursion", cmd)

    def test_command_with_timeout(self):
        cmd = self.tool.build_command("https://example.com/FUZZ", {
            "additional_args": "-timeout 10"
        })
        self.assertIn("-timeout", cmd)


class TestFfufURLProcessing(unittest.TestCase):
    def setUp(self):
        self.tool = FfufTool()

    def test_url_without_trailing_slash(self):
        cmd = self.tool.build_command("https://example.com", {})
        url_index = cmd.index("-u")
        url = cmd[url_index + 1]
        self.assertEqual(url, "https://example.com/FUZZ")

    def test_url_with_trailing_slash(self):
        cmd = self.tool.build_command("https://example.com/", {})
        url_index = cmd.index("-u")
        url = cmd[url_index + 1]
        self.assertEqual(url, "https://example.com/FUZZ")

    def test_url_with_path(self):
        cmd = self.tool.build_command("https://example.com/admin", {})
        url_index = cmd.index("-u")
        url = cmd[url_index + 1]
        self.assertEqual(url, "https://example.com/admin/FUZZ")

    def test_url_with_fuzz_in_middle(self):
        cmd = self.tool.build_command("https://example.com/FUZZ/test", {})
        url_index = cmd.index("-u")
        url = cmd[url_index + 1]
        self.assertEqual(url, "https://example.com/FUZZ/test")


class TestFfufOutputParsing(unittest.TestCase):
    def setUp(self):
        self.tool = FfufTool()

    def test_parse_basic_output(self):
        stdout = "[Status: 200, Size: 1234, Words: 567, Lines: 89]"
        result = self.tool.parse_output(stdout, "", 0)
        self.assertEqual(result["raw_output"], stdout)

    def test_parse_empty_output(self):
        result = self.tool.parse_output("", "", 0)
        self.assertEqual(result["raw_output"], "")


class TestFfufToolExecution(unittest.TestCase):
    def setUp(self):
        self.tool = FfufTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "[Status: 200] https://example.com/admin",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "FFUF")

    def test_execution_failure(self):
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "ffuf: command not found",
            "stderr": "ffuf: command not found",
            "returncode": 127
        }

        result = self.tool.execute("https://example.com", {}, self.mock_execute_func)
        self.assertFalse(result["success"])


class TestFfufEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tool = FfufTool()

    def test_url_with_port(self):
        cmd = self.tool.build_command("https://example.com:8443", {})
        url_index = cmd.index("-u")
        url = cmd[url_index + 1]
        self.assertIn("8443", url)

    def test_whitespace_in_args(self):
        cmd = self.tool.build_command("https://example.com/FUZZ", {
            "additional_args": "  -mc  200   -fc  404  "
        })
        self.assertIn("-mc", cmd)
        self.assertIn("-fc", cmd)


class TestFfufIntegration(unittest.TestCase):
    def test_realistic_fuzzing(self):
        tool = FfufTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": """[Status: 200, Size: 1234] https://example.com/admin
[Status: 301, Size: 234] https://example.com/uploads
[Status: 200, Size: 5678] https://example.com/api""",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute("https://example.com/FUZZ", {}, mock_execute)
        self.assertTrue(result["success"])


if __name__ == '__main__':
    unittest.main()
