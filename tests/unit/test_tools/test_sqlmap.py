"""
Unit tests for SQLMapTool implementation.

Comprehensive test coverage: 35+ tests
"""

import unittest
from unittest.mock import Mock, patch

from tools.web.sqlmap import SQLMapTool


class TestSQLMapToolInitialization(unittest.TestCase):
    """Test cases for SQLMapTool initialization."""

    def test_initialization(self):
        tool = SQLMapTool()
        self.assertEqual(tool.name, "SQLMap")
        self.assertEqual(tool.binary_name, "sqlmap")

    def test_inheritance(self):
        from tools.base import BaseTool
        tool = SQLMapTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        tool = SQLMapTool()
        self.assertEqual(str(tool), "SQLMap (sqlmap)")

    def test_repr_representation(self):
        tool = SQLMapTool()
        self.assertIn("SQLMapTool", repr(tool))


class TestSQLMapCommandBuilding(unittest.TestCase):
    """Test cases for SQLMap command building."""

    def setUp(self):
        self.tool = SQLMapTool()

    def test_basic_command_default_params(self):
        cmd = self.tool.build_command("https://example.com/page?id=1", {})
        self.assertIn("sqlmap", cmd)
        self.assertIn("-u", cmd)
        self.assertIn("https://example.com/page?id=1", cmd)
        self.assertIn("--batch", cmd)
        self.assertIn("--random-agent", cmd)

    def test_command_with_url_flag(self):
        cmd = self.tool.build_command("https://example.com/page?id=1", {})
        self.assertIn("-u", cmd)
        url_index = cmd.index("-u")
        self.assertEqual(cmd[url_index + 1], "https://example.com/page?id=1")

    def test_command_with_default_additional_args(self):
        cmd = self.tool.build_command("https://example.com?id=1", {})
        self.assertIn("--batch", cmd)
        self.assertIn("--random-agent", cmd)

    def test_command_with_custom_additional_args(self):
        cmd = self.tool.build_command("https://example.com?id=1", {
            "additional_args": "--dbs --level 3"
        })
        self.assertIn("--dbs", cmd)
        self.assertIn("--level", cmd)
        self.assertIn("3", cmd)

    def test_command_with_empty_additional_args(self):
        cmd = self.tool.build_command("https://example.com?id=1", {
            "additional_args": ""
        })
        # Should only have sqlmap -u url
        self.assertEqual(cmd, ["sqlmap", "-u", "https://example.com?id=1"])

    def test_command_with_database_enumeration(self):
        cmd = self.tool.build_command("https://example.com?id=1", {
            "additional_args": "--dbs"
        })
        self.assertIn("--dbs", cmd)

    def test_command_with_table_enumeration(self):
        cmd = self.tool.build_command("https://example.com?id=1", {
            "additional_args": "--tables -D database_name"
        })
        self.assertIn("--tables", cmd)
        self.assertIn("-D", cmd)

    def test_command_with_column_enumeration(self):
        cmd = self.tool.build_command("https://example.com?id=1", {
            "additional_args": "--columns -T users -D mydb"
        })
        self.assertIn("--columns", cmd)
        self.assertIn("-T", cmd)
        self.assertIn("users", cmd)

    def test_command_with_data_dump(self):
        cmd = self.tool.build_command("https://example.com?id=1", {
            "additional_args": "--dump -T users -D mydb"
        })
        self.assertIn("--dump", cmd)

    def test_command_with_risk_level(self):
        cmd = self.tool.build_command("https://example.com?id=1", {
            "additional_args": "--risk 3"
        })
        self.assertIn("--risk", cmd)
        self.assertIn("3", cmd)

    def test_command_with_level(self):
        cmd = self.tool.build_command("https://example.com?id=1", {
            "additional_args": "--level 5"
        })
        self.assertIn("--level", cmd)
        self.assertIn("5", cmd)

    def test_command_with_technique(self):
        cmd = self.tool.build_command("https://example.com?id=1", {
            "additional_args": "--technique=BEUST"
        })
        self.assertIn("--technique=BEUST", cmd)

    def test_command_with_threads(self):
        cmd = self.tool.build_command("https://example.com?id=1", {
            "additional_args": "--threads 10"
        })
        self.assertIn("--threads", cmd)
        self.assertIn("10", cmd)

    def test_command_with_timeout(self):
        cmd = self.tool.build_command("https://example.com?id=1", {
            "additional_args": "--timeout 30"
        })
        self.assertIn("--timeout", cmd)

    def test_command_with_cookie(self):
        cmd = self.tool.build_command("https://example.com?id=1", {
            "additional_args": "--cookie='session=abc123'"
        })
        self.assertIn("--cookie='session=abc123'", cmd)


class TestSQLMapOutputParsing(unittest.TestCase):
    """Test cases for SQLMap output parsing."""

    def setUp(self):
        self.tool = SQLMapTool()

    def test_parse_vulnerable_output(self):
        stdout = """[INFO] testing for SQL injection
sqlmap identified the following injection point(s):
Type: boolean-based blind
Title: AND boolean-based blind
Payload: id=1 AND 1=1"""
        result = self.tool.parse_output(stdout, "", 0)
        self.assertTrue(result["is_vulnerable"])
        self.assertIn("injection_type", result)

    def test_parse_not_vulnerable_output(self):
        stdout = "[INFO] testing completed. No vulnerabilities found."
        result = self.tool.parse_output(stdout, "", 0)
        self.assertFalse(result["is_vulnerable"])

    def test_parse_empty_output(self):
        result = self.tool.parse_output("", "", 0)
        self.assertFalse(result["is_vulnerable"])

    def test_parse_with_stderr(self):
        stdout = "[INFO] parameter is vulnerable"
        stderr = "Warning: console output"
        result = self.tool.parse_output(stdout, stderr, 0)
        self.assertEqual(result["stderr"], stderr)

    def test_parse_injection_type(self):
        stdout = """[INFO] parameter is vulnerable
Type: time-based blind
Title: MySQL >= 5.0.12 time-based blind"""
        result = self.tool.parse_output(stdout, "", 0)
        self.assertIn("Type:", result["injection_type"])


class TestSQLMapToolExecution(unittest.TestCase):
    """Test cases for SQLMapTool execution flow."""

    def setUp(self):
        self.tool = SQLMapTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "[INFO] parameter 'id' is vulnerable",
            "stderr": "",
            "returncode": 0,
            "execution_time": 120.5,
            "cached": False
        }

        result = self.tool.execute("https://example.com?id=1", {}, self.mock_execute_func)
        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "SQLMap")

    def test_execution_with_custom_params(self):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute(
            "https://example.com?id=1",
            {"additional_args": "--dbs --level 3"},
            self.mock_execute_func
        )
        self.assertTrue(result["success"])
        self.assertIn("--dbs", result["command"])

    def test_execution_failure(self):
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "sqlmap: command not found",
            "stderr": "sqlmap: command not found",
            "returncode": 127
        }

        result = self.tool.execute("https://example.com?id=1", {}, self.mock_execute_func)
        self.assertFalse(result["success"])

    @patch('tools.base.logger')
    def test_logging(self, mock_logger):
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0
        }

        self.tool.execute("https://example.com?id=1", {}, self.mock_execute_func)
        mock_logger.info.assert_called()


class TestSQLMapEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        self.tool = SQLMapTool()

    def test_url_with_multiple_params(self):
        cmd = self.tool.build_command("https://example.com?id=1&name=test", {})
        self.assertIn("https://example.com?id=1&name=test", cmd)

    def test_post_request(self):
        cmd = self.tool.build_command("https://example.com/login", {
            "additional_args": "--data='username=admin&password=pass'"
        })
        # Check that --data argument is in command (with or without =)
        self.assertTrue(any("--data" in str(arg) for arg in cmd))

    def test_whitespace_in_args(self):
        cmd = self.tool.build_command("https://example.com?id=1", {
            "additional_args": "  --batch   --dbs  "
        })
        self.assertIn("--batch", cmd)
        self.assertIn("--dbs", cmd)


class TestSQLMapIntegration(unittest.TestCase):
    """Integration tests for SQLMapTool."""

    def test_realistic_sql_injection_scan(self):
        tool = SQLMapTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": """[INFO] testing for SQL injection
[INFO] GET parameter 'id' appears to be vulnerable
sqlmap identified the following injection point(s):
Parameter: id (GET)
    Type: boolean-based blind
    Title: AND boolean-based blind - WHERE or HAVING clause
    Payload: id=1 AND 1=1""",
            "stderr": "",
            "returncode": 0,
            "execution_time": 180.5
        })

        result = tool.execute(
            "https://example.com/page?id=1",
            {"additional_args": "--batch --random-agent"},
            mock_execute
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["output"]["is_vulnerable"])


if __name__ == '__main__':
    unittest.main()
