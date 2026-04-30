"""
Unit tests for MasscanTool implementation.

Tests cover:
- Command building with port ranges and rates
- Parameter validation
- Output parsing
- Error handling
- Integration with BaseTool
- Edge cases and boundary conditions

Comprehensive test coverage: 35+ tests
"""

import unittest
from unittest.mock import Mock, patch
from typing import Dict, Any

from tools.network.masscan import MasscanTool


class TestMasscanToolInitialization(unittest.TestCase):
    """Test cases for MasscanTool initialization."""

    def test_initialization(self):
        """Test MasscanTool initialization."""
        tool = MasscanTool()
        self.assertEqual(tool.name, "Masscan")
        self.assertEqual(tool.binary_name, "masscan")

    def test_inheritance(self):
        """Test that MasscanTool inherits from BaseTool."""
        from tools.base import BaseTool
        tool = MasscanTool()
        self.assertIsInstance(tool, BaseTool)

    def test_string_representation(self):
        """Test string representation."""
        tool = MasscanTool()
        self.assertEqual(str(tool), "Masscan (masscan)")

    def test_repr_representation(self):
        """Test developer representation."""
        tool = MasscanTool()
        self.assertIn("MasscanTool", repr(tool))
        self.assertIn("Masscan", repr(tool))


class TestMasscanCommandBuilding(unittest.TestCase):
    """Test cases for Masscan command building."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = MasscanTool()

    def test_basic_command_default_params(self):
        """Test basic command with default parameters."""
        cmd = self.tool.build_command("192.168.1.1", {})
        self.assertEqual(cmd, ["masscan", "192.168.1.1", "-p", "0-65535", "--rate", "1000"])

    def test_command_with_default_port_range(self):
        """Test command includes default full port range."""
        cmd = self.tool.build_command("192.168.1.1", {})
        self.assertIn("-p", cmd)
        self.assertIn("0-65535", cmd)

    def test_command_with_default_rate(self):
        """Test command includes default rate of 1000."""
        cmd = self.tool.build_command("192.168.1.1", {})
        self.assertIn("--rate", cmd)
        self.assertIn("1000", cmd)

    def test_command_with_custom_port_range(self):
        """Test command with custom port range."""
        cmd = self.tool.build_command("192.168.1.1", {
            "ports": "80,443"
        })
        self.assertIn("-p", cmd)
        self.assertIn("80,443", cmd)

    def test_command_with_single_port(self):
        """Test command with single port."""
        cmd = self.tool.build_command("192.168.1.1", {
            "ports": "80"
        })
        self.assertIn("80", cmd)

    def test_command_with_port_range(self):
        """Test command with port range."""
        cmd = self.tool.build_command("192.168.1.1", {
            "ports": "1-1000"
        })
        self.assertIn("1-1000", cmd)

    def test_command_with_custom_rate(self):
        """Test command with custom scan rate."""
        cmd = self.tool.build_command("192.168.1.1", {
            "rate": "10000"
        })
        self.assertIn("--rate", cmd)
        self.assertIn("10000", cmd)

    def test_command_with_integer_rate(self):
        """Test command with integer rate value."""
        cmd = self.tool.build_command("192.168.1.1", {
            "rate": 5000
        })
        self.assertIn("--rate", cmd)
        self.assertIn("5000", cmd)

    def test_command_with_low_rate(self):
        """Test command with low scan rate."""
        cmd = self.tool.build_command("192.168.1.1", {
            "rate": "100"
        })
        self.assertIn("100", cmd)

    def test_command_with_high_rate(self):
        """Test command with high scan rate."""
        cmd = self.tool.build_command("192.168.1.1", {
            "rate": "100000"
        })
        self.assertIn("100000", cmd)

    def test_command_with_additional_args(self):
        """Test command with additional arguments."""
        cmd = self.tool.build_command("192.168.1.1", {
            "additional_args": "-oJ output.json"
        })
        self.assertIn("-oJ", cmd)
        self.assertIn("output.json", cmd)

    def test_command_with_exclude(self):
        """Test command with exclude option."""
        cmd = self.tool.build_command("192.168.1.0/24", {
            "additional_args": "--exclude 192.168.1.1"
        })
        self.assertIn("--exclude", cmd)
        self.assertIn("192.168.1.1", cmd)

    def test_command_with_banner_grab(self):
        """Test command with banner grabbing."""
        cmd = self.tool.build_command("192.168.1.1", {
            "additional_args": "--banners"
        })
        self.assertIn("--banners", cmd)

    def test_command_order(self):
        """Test that command arguments are in correct order."""
        cmd = self.tool.build_command("192.168.1.1", {
            "ports": "80",
            "rate": "5000"
        })
        # target, -p, ports, --rate, rate
        self.assertEqual(cmd[0], "masscan")
        self.assertEqual(cmd[1], "192.168.1.1")
        self.assertEqual(cmd[2], "-p")
        self.assertEqual(cmd[3], "80")
        self.assertEqual(cmd[4], "--rate")
        self.assertEqual(cmd[5], "5000")


class TestMasscanTargetVariations(unittest.TestCase):
    """Test Masscan with different target variations."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = MasscanTool()

    def test_single_ip_target(self):
        """Test with single IP address."""
        cmd = self.tool.build_command("192.168.1.1", {})
        self.assertIn("192.168.1.1", cmd)

    def test_cidr_range_target(self):
        """Test with CIDR notation."""
        cmd = self.tool.build_command("192.168.1.0/24", {})
        self.assertIn("192.168.1.0/24", cmd)

    def test_large_cidr_range(self):
        """Test with large CIDR range."""
        cmd = self.tool.build_command("10.0.0.0/8", {})
        self.assertIn("10.0.0.0/8", cmd)

    def test_ip_range_notation(self):
        """Test with IP range notation."""
        cmd = self.tool.build_command("192.168.1.1-192.168.1.254", {})
        self.assertIn("192.168.1.1-192.168.1.254", cmd)

    def test_multiple_targets(self):
        """Test with multiple target IPs."""
        cmd = self.tool.build_command("192.168.1.1,192.168.1.2,192.168.1.3", {})
        self.assertIn("192.168.1.1,192.168.1.2,192.168.1.3", cmd)


class TestMasscanPortSpecifications(unittest.TestCase):
    """Test Masscan with various port specifications."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = MasscanTool()

    def test_common_ports(self):
        """Test with common web ports."""
        cmd = self.tool.build_command("192.168.1.1", {
            "ports": "80,443,8080,8443"
        })
        self.assertIn("80,443,8080,8443", cmd)

    def test_port_range_low(self):
        """Test with low port range."""
        cmd = self.tool.build_command("192.168.1.1", {
            "ports": "1-1024"
        })
        self.assertIn("1-1024", cmd)

    def test_mixed_ports_and_ranges(self):
        """Test with mixed individual ports and ranges."""
        cmd = self.tool.build_command("192.168.1.1", {
            "ports": "22,80,443,8000-9000"
        })
        self.assertIn("22,80,443,8000-9000", cmd)

    def test_top_ports(self):
        """Test with top 100 ports."""
        cmd = self.tool.build_command("192.168.1.1", {
            "additional_args": "--top-ports 100"
        })
        self.assertIn("--top-ports", cmd)
        self.assertIn("100", cmd)


class TestMasscanOutputParsing(unittest.TestCase):
    """Test cases for Masscan output parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = MasscanTool()

    def test_parse_basic_output(self):
        """Test parsing basic masscan output."""
        stdout = """Discovered open port 80/tcp on 192.168.1.1
Discovered open port 443/tcp on 192.168.1.1"""
        result = self.tool.parse_output(stdout, "", 0)

        self.assertIn("raw_output", result)
        self.assertEqual(result["raw_output"], stdout)
        self.assertEqual(result["returncode"], 0)

    def test_parse_empty_output(self):
        """Test parsing empty output."""
        result = self.tool.parse_output("", "", 0)

        self.assertEqual(result["raw_output"], "")
        self.assertEqual(result["stderr"], "")
        self.assertEqual(result["returncode"], 0)

    def test_parse_output_with_stderr(self):
        """Test parsing with stderr messages."""
        stdout = "Discovered open port 80/tcp on 192.168.1.1"
        stderr = "Warning: rate too high"

        result = self.tool.parse_output(stdout, stderr, 0)

        self.assertEqual(result["stderr"], stderr)
        self.assertIn("raw_output", result)

    def test_parse_large_scan_output(self):
        """Test parsing large scan with many results."""
        lines = [f"Discovered open port {i}/tcp on 192.168.1.1" for i in range(100)]
        stdout = "\n".join(lines)

        result = self.tool.parse_output(stdout, "", 0)
        self.assertIn("raw_output", result)

    def test_parse_with_nonzero_returncode(self):
        """Test parsing with non-zero return code."""
        result = self.tool.parse_output("", "Error: permission denied", 1)

        self.assertEqual(result["returncode"], 1)
        self.assertIn("stderr", result)


class TestMasscanToolExecution(unittest.TestCase):
    """Test cases for MasscanTool execution flow."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = MasscanTool()
        self.mock_execute_func = Mock()

    def test_successful_execution(self):
        """Test successful masscan execution."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "Discovered open port 80/tcp on 192.168.1.1",
            "stderr": "",
            "returncode": 0,
            "execution_time": 45.5,
            "cached": False
        }

        result = self.tool.execute("192.168.1.1", {}, self.mock_execute_func)

        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "Masscan")
        self.assertEqual(result["target"], "192.168.1.1")
        self.assertIn("masscan", result["command"])

    def test_execution_with_custom_rate(self):
        """Test execution with custom rate."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "output",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute(
            "192.168.1.0/24",
            {"ports": "80,443", "rate": "10000"},
            self.mock_execute_func
        )

        self.assertTrue(result["success"])
        self.assertIn("--rate 10000", result["command"])
        self.assertIn("-p 80,443", result["command"])

    def test_execution_failure(self):
        """Test handling of execution failure."""
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "masscan: permission denied",
            "stderr": "masscan: need root privileges",
            "returncode": 1
        }

        result = self.tool.execute("192.168.1.1", {}, self.mock_execute_func)

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_execution_with_cache(self):
        """Test execution with caching."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "cached scan results",
            "stderr": "",
            "returncode": 0,
            "cached": True
        }

        result = self.tool.execute(
            "192.168.1.1",
            {},
            self.mock_execute_func,
            use_cache=True
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["cached"])

    @patch('tools.base.logger')
    def test_logging_during_execution(self, mock_logger):
        """Test that execution is logged."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "output",
            "stderr": "",
            "returncode": 0
        }

        self.tool.execute("192.168.1.1", {}, self.mock_execute_func)

        mock_logger.info.assert_called()
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn("Executing", log_message)
        self.assertIn("Masscan", log_message)


class TestMasscanEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = MasscanTool()

    def test_rate_as_string(self):
        """Test rate parameter as string."""
        cmd = self.tool.build_command("192.168.1.1", {"rate": "5000"})
        self.assertIn("5000", cmd)

    def test_rate_as_integer(self):
        """Test rate parameter as integer."""
        cmd = self.tool.build_command("192.168.1.1", {"rate": 5000})
        self.assertIn("5000", cmd)

    def test_very_high_rate(self):
        """Test with very high scan rate."""
        cmd = self.tool.build_command("192.168.1.1", {"rate": 1000000})
        self.assertIn("1000000", cmd)

    def test_whitespace_in_additional_args(self):
        """Test with extra whitespace in additional_args."""
        cmd = self.tool.build_command("192.168.1.1", {
            "additional_args": "  --banners   -oJ   output.json  "
        })
        self.assertIn("--banners", cmd)
        self.assertIn("-oJ", cmd)


class TestMasscanIntegration(unittest.TestCase):
    """Integration tests for MasscanTool."""

    def test_realistic_network_scan(self):
        """Test realistic network scanning scenario."""
        tool = MasscanTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": """Discovered open port 22/tcp on 192.168.1.10
Discovered open port 80/tcp on 192.168.1.10
Discovered open port 443/tcp on 192.168.1.10
Discovered open port 3306/tcp on 192.168.1.11""",
            "stderr": "",
            "returncode": 0,
            "execution_time": 12.3,
            "cached": False
        })

        result = tool.execute(
            "192.168.1.0/24",
            {"ports": "22,80,443,3306", "rate": "5000"},
            mock_execute
        )

        self.assertTrue(result["success"])
        self.assertIn("Discovered", result["output"]["raw_output"])


if __name__ == '__main__':
    unittest.main()
