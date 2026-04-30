"""
Unit tests for NmapTool implementation.

Tests cover:
- Command building with various parameters
- Parameter validation
- Output parsing
- Error handling
- Integration with BaseTool
- All scan types and options
"""

import unittest
from unittest.mock import Mock, patch
from typing import Dict, Any

from tools.network.nmap import NmapTool


class TestNmapToolInitialization(unittest.TestCase):
    """Test cases for NmapTool initialization."""

    def test_initialization(self):
        """Test NmapTool initialization."""
        tool = NmapTool()
        self.assertEqual(tool.name, "Nmap")
        self.assertEqual(tool.binary_name, "nmap")

    def test_string_representation(self):
        """Test string representation."""
        tool = NmapTool()
        self.assertEqual(str(tool), "Nmap (nmap)")

    def test_repr_representation(self):
        """Test developer representation."""
        tool = NmapTool()
        self.assertIn("NmapTool", repr(tool))
        self.assertIn("Nmap", repr(tool))


class TestNmapCommandBuilding(unittest.TestCase):
    """Test cases for Nmap command building."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = NmapTool()

    def test_basic_command_default_scan(self):
        """Test basic command with default scan type."""
        cmd = self.tool.build_command("192.168.1.1", {})
        self.assertEqual(cmd, ["nmap", "-sV", "192.168.1.1"])

    def test_command_with_custom_scan_type(self):
        """Test command with custom scan type."""
        cmd = self.tool.build_command("192.168.1.1", {"scan_type": "-sS"})
        self.assertEqual(cmd, ["nmap", "-sS", "192.168.1.1"])

    def test_command_with_port_specification(self):
        """Test command with port specification."""
        cmd = self.tool.build_command("192.168.1.1", {
            "scan_type": "-sV",
            "ports": "80,443"
        })
        self.assertEqual(cmd, ["nmap", "-sV", "-p", "80,443", "192.168.1.1"])

    def test_command_with_port_range(self):
        """Test command with port range."""
        cmd = self.tool.build_command("192.168.1.1", {
            "ports": "1-1000"
        })
        self.assertEqual(cmd, ["nmap", "-sV", "-p", "1-1000", "192.168.1.1"])

    def test_command_with_multiple_ports(self):
        """Test command with multiple specific ports."""
        cmd = self.tool.build_command("example.com", {
            "scan_type": "-sT",
            "ports": "22,80,443,8080"
        })
        self.assertEqual(cmd, ["nmap", "-sT", "-p", "22,80,443,8080", "example.com"])

    def test_command_with_additional_args(self):
        """Test command with additional arguments."""
        cmd = self.tool.build_command("192.168.1.1", {
            "scan_type": "-sS",
            "additional_args": "-O -v"
        })
        self.assertEqual(cmd, ["nmap", "-sS", "-O", "-v", "192.168.1.1"])

    def test_command_with_all_parameters(self):
        """Test command with all parameters."""
        cmd = self.tool.build_command("192.168.1.0/24", {
            "scan_type": "-sV",
            "ports": "1-65535",
            "additional_args": "-O -T4 --version-intensity 5"
        })
        self.assertEqual(cmd, [
            "nmap", "-sV", "-p", "1-65535",
            "-O", "-T4", "--version-intensity", "5",
            "192.168.1.0/24"
        ])

    def test_command_hostname_target(self):
        """Test command with hostname target."""
        cmd = self.tool.build_command("example.com", {"scan_type": "-sV"})
        self.assertEqual(cmd, ["nmap", "-sV", "example.com"])

    def test_command_network_range(self):
        """Test command with network range."""
        cmd = self.tool.build_command("192.168.1.0/24", {})
        self.assertEqual(cmd, ["nmap", "-sV", "192.168.1.0/24"])

    def test_command_with_empty_additional_args(self):
        """Test command with empty additional_args."""
        cmd = self.tool.build_command("192.168.1.1", {
            "scan_type": "-sS",
            "additional_args": ""
        })
        self.assertEqual(cmd, ["nmap", "-sS", "192.168.1.1"])


class TestNmapScanTypes(unittest.TestCase):
    """Test various Nmap scan types."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = NmapTool()

    def test_syn_scan(self):
        """Test SYN scan (-sS)."""
        cmd = self.tool.build_command("target.com", {"scan_type": "-sS"})
        self.assertIn("-sS", cmd)

    def test_tcp_connect_scan(self):
        """Test TCP connect scan (-sT)."""
        cmd = self.tool.build_command("target.com", {"scan_type": "-sT"})
        self.assertIn("-sT", cmd)

    def test_udp_scan(self):
        """Test UDP scan (-sU)."""
        cmd = self.tool.build_command("target.com", {"scan_type": "-sU"})
        self.assertIn("-sU", cmd)

    def test_version_detection_scan(self):
        """Test version detection scan (-sV)."""
        cmd = self.tool.build_command("target.com", {"scan_type": "-sV"})
        self.assertIn("-sV", cmd)

    def test_ack_scan(self):
        """Test ACK scan (-sA)."""
        cmd = self.tool.build_command("target.com", {"scan_type": "-sA"})
        self.assertIn("-sA", cmd)

    def test_window_scan(self):
        """Test Window scan (-sW)."""
        cmd = self.tool.build_command("target.com", {"scan_type": "-sW"})
        self.assertIn("-sW", cmd)

    def test_maimon_scan(self):
        """Test Maimon scan (-sM)."""
        cmd = self.tool.build_command("target.com", {"scan_type": "-sM"})
        self.assertIn("-sM", cmd)

    def test_null_scan(self):
        """Test NULL scan (-sN)."""
        cmd = self.tool.build_command("target.com", {"scan_type": "-sN"})
        self.assertIn("-sN", cmd)

    def test_fin_scan(self):
        """Test FIN scan (-sF)."""
        cmd = self.tool.build_command("target.com", {"scan_type": "-sF"})
        self.assertIn("-sF", cmd)

    def test_xmas_scan(self):
        """Test Xmas scan (-sX)."""
        cmd = self.tool.build_command("target.com", {"scan_type": "-sX"})
        self.assertIn("-sX", cmd)


class TestNmapParameterValidation(unittest.TestCase):
    """Test cases for Nmap parameter validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = NmapTool()

    def test_valid_scan_type(self):
        """Test validation accepts valid scan types."""
        # Should not raise
        self.tool.validate_params({"scan_type": "-sS"})
        self.tool.validate_params({"scan_type": "-sV"})
        self.tool.validate_params({"scan_type": "-sT"})

    def test_valid_port_specification(self):
        """Test validation accepts valid port specifications."""
        # Should not raise
        self.tool.validate_params({"ports": "80"})
        self.tool.validate_params({"ports": "80,443"})
        self.tool.validate_params({"ports": "1-1000"})
        self.tool.validate_params({"ports": "22,80,443,8080"})
        self.tool.validate_params({"ports": "1-100,200-300"})

    def test_invalid_port_specification_letters(self):
        """Test validation rejects ports with invalid characters."""
        with self.assertRaises(ValueError) as context:
            self.tool.validate_params({"ports": "abc"})
        self.assertIn("Invalid port specification", str(context.exception))

    def test_invalid_port_specification_special_chars(self):
        """Test validation rejects ports with special characters."""
        with self.assertRaises(ValueError) as context:
            self.tool.validate_params({"ports": "80;443"})
        self.assertIn("Invalid port specification", str(context.exception))

    def test_invalid_port_specification_spaces(self):
        """Test validation rejects ports with spaces."""
        with self.assertRaises(ValueError) as context:
            self.tool.validate_params({"ports": "80 443"})
        self.assertIn("Invalid port specification", str(context.exception))

    def test_empty_params(self):
        """Test validation accepts empty parameters."""
        # Should not raise
        self.tool.validate_params({})

    def test_none_values(self):
        """Test validation handles None values."""
        # Should not raise
        self.tool.validate_params({"scan_type": None, "ports": None})


class TestNmapOutputParsing(unittest.TestCase):
    """Test cases for Nmap output parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = NmapTool()

    def test_parse_basic_output(self):
        """Test parsing basic nmap output."""
        stdout = """
Starting Nmap 7.80 ( https://nmap.org )
Nmap scan report for example.com (93.184.216.34)
Host is up (0.10s latency).

PORT    STATE SERVICE
22/tcp  open  ssh
80/tcp  open  http
443/tcp open  https

Nmap done: 1 IP address (1 host up) scanned in 5.23 seconds
"""
        result = self.tool.parse_output(stdout, "", 0)

        self.assertIn("raw_output", result)
        self.assertEqual(result["raw_output"], stdout)
        self.assertEqual(result["returncode"], 0)
        self.assertIn("scan_target", result)
        self.assertIn("example.com", result["scan_target"])

    def test_parse_open_ports(self):
        """Test parsing open ports from output."""
        stdout = """
Nmap scan report for 192.168.1.1
PORT    STATE SERVICE
22/tcp  open  ssh
80/tcp  open  http
443/tcp open  https
8080/tcp open  http-proxy
"""
        result = self.tool.parse_output(stdout, "", 0)

        self.assertIn("open_ports", result)
        self.assertEqual(result["open_ports"], ["22", "80", "443", "8080"])
        self.assertEqual(result["open_ports_count"], 4)

    def test_parse_no_open_ports(self):
        """Test parsing output with no open ports."""
        stdout = """
Nmap scan report for 192.168.1.1
All 1000 scanned ports on 192.168.1.1 are filtered
"""
        result = self.tool.parse_output(stdout, "", 0)

        self.assertNotIn("open_ports", result)
        self.assertIn("raw_output", result)

    def test_parse_with_stderr(self):
        """Test parsing with stderr messages."""
        stdout = "Nmap scan report for example.com"
        stderr = "Warning: Could not perform OS detection"

        result = self.tool.parse_output(stdout, stderr, 0)

        self.assertEqual(result["stderr"], stderr)
        self.assertIn("raw_output", result)

    def test_parse_nonzero_returncode(self):
        """Test parsing with non-zero return code."""
        result = self.tool.parse_output("", "Error: Unknown host", 1)

        self.assertEqual(result["returncode"], 1)
        self.assertIn("stderr", result)

    def test_parse_empty_output(self):
        """Test parsing empty output."""
        result = self.tool.parse_output("", "", 0)

        self.assertEqual(result["raw_output"], "")
        self.assertEqual(result["stderr"], "")
        self.assertEqual(result["returncode"], 0)

    def test_parse_complex_output(self):
        """Test parsing complex output with service versions."""
        stdout = """
Nmap scan report for webserver.example.com (192.168.1.10)
Host is up (0.0012s latency).
Not shown: 997 filtered ports
PORT    STATE SERVICE VERSION
22/tcp  open  ssh     OpenSSH 7.4 (protocol 2.0)
80/tcp  open  http    Apache httpd 2.4.6
443/tcp open  https   Apache httpd 2.4.6
"""
        result = self.tool.parse_output(stdout, "", 0)

        self.assertIn("open_ports", result)
        self.assertEqual(len(result["open_ports"]), 3)
        self.assertIn("22", result["open_ports"])
        self.assertIn("80", result["open_ports"])
        self.assertIn("443", result["open_ports"])

    def test_parse_udp_scan_output(self):
        """Test parsing UDP scan output."""
        stdout = """
Nmap scan report for target.com
PORT    STATE         SERVICE
53/udp  open          domain
123/udp open|filtered ntp
"""
        result = self.tool.parse_output(stdout, "", 0)

        # UDP scans use /udp, should not match /tcp pattern
        self.assertNotIn("open_ports", result)
        self.assertIn("raw_output", result)


class TestNmapToolExecution(unittest.TestCase):
    """Test cases for NmapTool execution flow."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = NmapTool()
        self.mock_execute_func = Mock()

    def test_successful_scan(self):
        """Test successful nmap scan execution."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "Nmap scan report for example.com\n80/tcp open http",
            "stderr": "",
            "returncode": 0,
            "execution_time": 2.5,
            "cached": False
        }

        result = self.tool.execute("example.com", {}, self.mock_execute_func)

        self.assertTrue(result["success"])
        self.assertEqual(result["tool"], "Nmap")
        self.assertEqual(result["target"], "example.com")
        self.assertIn("nmap", result["command"])
        self.assertIn("output", result)

    def test_scan_with_custom_parameters(self):
        """Test scan with custom parameters."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "Nmap output",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute(
            "192.168.1.1",
            {
                "scan_type": "-sS",
                "ports": "80,443",
                "additional_args": "-O"
            },
            self.mock_execute_func
        )

        self.assertTrue(result["success"])
        self.assertIn("-sS", result["command"])
        self.assertIn("-p 80,443", result["command"])
        self.assertIn("-O", result["command"])

    def test_scan_with_invalid_ports(self):
        """Test scan with invalid port specification."""
        result = self.tool.execute(
            "example.com",
            {"ports": "invalid"},
            self.mock_execute_func
        )

        self.assertFalse(result["success"])
        self.assertIn("Parameter validation failed", result["error"])

    def test_scan_execution_failure(self):
        """Test handling of scan execution failure."""
        self.mock_execute_func.return_value = {
            "success": False,
            "error": "nmap: command not found",
            "stderr": "nmap: command not found",
            "returncode": 127
        }

        result = self.tool.execute("example.com", {}, self.mock_execute_func)

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_scan_with_caching(self):
        """Test scan with caching enabled."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "cached output",
            "stderr": "",
            "returncode": 0,
            "cached": True
        }

        result = self.tool.execute(
            "example.com",
            {},
            self.mock_execute_func,
            use_cache=True
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["cached"])

    def test_scan_network_range(self):
        """Test scanning network range."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "Nmap scan report",
            "stderr": "",
            "returncode": 0
        }

        result = self.tool.execute(
            "192.168.1.0/24",
            {"scan_type": "-sn"},
            self.mock_execute_func
        )

        self.assertTrue(result["success"])
        self.assertIn("192.168.1.0/24", result["command"])

    @patch('tools.base.logger')
    def test_logging_during_execution(self, mock_logger):
        """Test that execution is logged."""
        self.mock_execute_func.return_value = {
            "success": True,
            "stdout": "output",
            "stderr": "",
            "returncode": 0
        }

        self.tool.execute("example.com", {}, self.mock_execute_func)

        mock_logger.info.assert_called()
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn("Executing", log_message)
        self.assertIn("Nmap", log_message)


class TestNmapEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = NmapTool()

    def test_target_with_special_characters(self):
        """Test target with special characters."""
        cmd = self.tool.build_command("sub-domain_test.example.com", {})
        self.assertIn("sub-domain_test.example.com", cmd)

    def test_ipv6_target(self):
        """Test IPv6 target."""
        cmd = self.tool.build_command("2001:db8::1", {})
        self.assertIn("2001:db8::1", cmd)

    def test_multiple_targets(self):
        """Test multiple targets (space-separated)."""
        cmd = self.tool.build_command("192.168.1.1 192.168.1.2", {})
        self.assertIn("192.168.1.1 192.168.1.2", cmd)

    def test_complex_port_range(self):
        """Test complex port range specification."""
        cmd = self.tool.build_command("target.com", {
            "ports": "1-1000,2000-3000,8080,8443"
        })
        self.assertIn("1-1000,2000-3000,8080,8443", cmd)

    def test_all_ports(self):
        """Test scanning all ports."""
        cmd = self.tool.build_command("target.com", {"ports": "1-65535"})
        self.assertIn("1-65535", cmd)

    def test_single_port(self):
        """Test scanning single port."""
        cmd = self.tool.build_command("target.com", {"ports": "80"})
        self.assertEqual(cmd, ["nmap", "-sV", "-p", "80", "target.com"])

    def test_timing_template(self):
        """Test with timing template."""
        cmd = self.tool.build_command("target.com", {
            "additional_args": "-T4"
        })
        self.assertIn("-T4", cmd)

    def test_output_format_args(self):
        """Test with output format arguments."""
        cmd = self.tool.build_command("target.com", {
            "additional_args": "-oN output.txt -oX output.xml"
        })
        self.assertIn("-oN", cmd)
        self.assertIn("output.txt", cmd)
        self.assertIn("-oX", cmd)
        self.assertIn("output.xml", cmd)


class TestNmapIntegration(unittest.TestCase):
    """Integration tests for NmapTool."""

    def test_realistic_service_scan(self):
        """Test realistic service version detection scan."""
        tool = NmapTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": """
Starting Nmap 7.80 ( https://nmap.org )
Nmap scan report for webserver.local (192.168.1.100)
Host is up (0.0010s latency).
Not shown: 997 closed ports
PORT    STATE SERVICE VERSION
22/tcp  open  ssh     OpenSSH 8.2p1 Ubuntu 4ubuntu0.1
80/tcp  open  http    nginx 1.18.0
443/tcp open  ssl/http nginx 1.18.0

Service detection performed. Please report any incorrect results.
Nmap done: 1 IP address (1 host up) scanned in 12.34 seconds
""",
            "stderr": "",
            "returncode": 0,
            "execution_time": 12.34,
            "cached": False
        })

        result = tool.execute(
            "192.168.1.100",
            {"scan_type": "-sV", "ports": "22,80,443"},
            mock_execute
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["output"]["open_ports_count"], 3)
        self.assertIn("22", result["output"]["open_ports"])
        self.assertIn("80", result["output"]["open_ports"])
        self.assertIn("443", result["output"]["open_ports"])

    def test_realistic_stealth_scan(self):
        """Test realistic SYN stealth scan."""
        tool = NmapTool()
        mock_execute = Mock(return_value={
            "success": True,
            "stdout": """
Nmap scan report for target.example.com
Host is up (0.050s latency).
PORT     STATE SERVICE
80/tcp   open  http
443/tcp  open  https
8080/tcp open  http-proxy

Nmap done: 1 IP address scanned
""",
            "stderr": "",
            "returncode": 0
        })

        result = tool.execute(
            "target.example.com",
            {
                "scan_type": "-sS",
                "ports": "80,443,8080",
                "additional_args": "-T4"
            },
            mock_execute
        )

        self.assertTrue(result["success"])
        self.assertIn("-sS", result["command"])
        self.assertIn("-T4", result["command"])
        self.assertEqual(result["output"]["open_ports_count"], 3)


if __name__ == '__main__':
    unittest.main()
