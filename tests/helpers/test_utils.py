"""
Test utility functions for HexStrike testing

Provides helper functions for:
- Assertion helpers
- Test data generation
- Output parsing
- Comparison utilities
"""

import json
import re
from typing import Any, Dict, List, Optional


class OutputParser:
    """Helper class for parsing security tool outputs"""

    @staticmethod
    def parse_nmap_ports(output: str) -> List[int]:
        """Parse open ports from nmap output"""
        ports = []
        for line in output.split('\n'):
            match = re.match(r'(\d+)/tcp\s+open', line)
            if match:
                ports.append(int(match.group(1)))
        return ports

    @staticmethod
    def parse_nmap_services(output: str) -> Dict[int, str]:
        """Parse services from nmap output"""
        services = {}
        for line in output.split('\n'):
            match = re.match(r'(\d+)/tcp\s+open\s+(\w+)', line)
            if match:
                port = int(match.group(1))
                service = match.group(2)
                services[port] = service
        return services

    @staticmethod
    def parse_gobuster_paths(output: str) -> List[str]:
        """Parse found paths from gobuster output"""
        paths = []
        for line in output.split('\n'):
            match = re.match(r'(/\S+)\s+\(Status: \d+\)', line)
            if match:
                paths.append(match.group(1))
        return paths

    @staticmethod
    def parse_nuclei_vulns(output: str) -> List[Dict[str, str]]:
        """Parse vulnerabilities from nuclei output"""
        vulns = []
        for line in output.split('\n'):
            match = re.match(r'\[([\w-]+)\]\s+\[([\w]+)\]\s+\[([\w]+)\]\s+(.+)', line)
            if match:
                vulns.append({
                    'id': match.group(1),
                    'protocol': match.group(2),
                    'severity': match.group(3),
                    'url': match.group(4)
                })
        return vulns

    @staticmethod
    def parse_sqlmap_injection(output: str) -> Optional[Dict[str, str]]:
        """Parse SQL injection details from sqlmap output"""
        if 'is vulnerable' not in output:
            return None

        injection_type = None
        parameter = None

        for line in output.split('\n'):
            if 'Type:' in line:
                injection_type = line.split('Type:')[1].strip()
            elif 'Parameter:' in line:
                parameter = line.split('Parameter:')[1].strip()
            elif "parameter '" in line and "is vulnerable" in line:
                match = re.search(r"parameter '(\w+)' is vulnerable", line)
                if match:
                    parameter = match.group(1)

        return {
            'vulnerable': True,
            'type': injection_type,
            'parameter': parameter
        }

    @staticmethod
    def count_severity_levels(output: str) -> Dict[str, int]:
        """Count vulnerabilities by severity level"""
        severities = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}

        for severity in severities.keys():
            severities[severity] = output.lower().count(f'[{severity}]')

        return severities


class AssertionHelpers:
    """Custom assertion helpers for security testing"""

    @staticmethod
    def assert_has_ports(output: str, expected_ports: List[int]):
        """Assert that output contains expected ports"""
        found_ports = OutputParser.parse_nmap_ports(output)
        missing_ports = set(expected_ports) - set(found_ports)

        assert not missing_ports, \
            f"Missing expected ports: {missing_ports}. Found: {found_ports}"

    @staticmethod
    def assert_has_service(output: str, port: int, expected_service: str):
        """Assert that a specific service is detected on a port"""
        services = OutputParser.parse_nmap_services(output)

        assert port in services, \
            f"Port {port} not found in output. Available ports: {list(services.keys())}"

        assert services[port] == expected_service, \
            f"Expected service '{expected_service}' on port {port}, got '{services[port]}'"

    @staticmethod
    def assert_has_vulnerability(output: str, vuln_id: str):
        """Assert that output contains a specific vulnerability"""
        assert vuln_id in output, \
            f"Vulnerability {vuln_id} not found in output"

    @staticmethod
    def assert_severity_count(output: str, severity: str, min_count: int):
        """Assert minimum number of vulnerabilities at severity level"""
        counts = OutputParser.count_severity_levels(output)
        actual_count = counts.get(severity.lower(), 0)

        assert actual_count >= min_count, \
            f"Expected at least {min_count} {severity} vulnerabilities, found {actual_count}"

    @staticmethod
    def assert_command_success(result: Dict[str, Any]):
        """Assert that a command execution was successful"""
        assert result.get('success', False), \
            f"Command failed: {result.get('error', 'Unknown error')}"

        assert result.get('returncode', -1) == 0, \
            f"Command returned non-zero exit code: {result.get('returncode')}"

    @staticmethod
    def assert_valid_json(output: str):
        """Assert that output is valid JSON"""
        try:
            json.loads(output)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Output is not valid JSON: {e}")

    @staticmethod
    def assert_contains_all(text: str, expected_strings: List[str]):
        """Assert that text contains all expected strings"""
        missing = [s for s in expected_strings if s not in text]

        assert not missing, \
            f"Missing expected strings: {missing}"

    @staticmethod
    def assert_matches_pattern(text: str, pattern: str):
        """Assert that text matches a regex pattern"""
        assert re.search(pattern, text), \
            f"Text does not match pattern: {pattern}"


class TestDataGenerator:
    """Generate test data for various scenarios"""

    @staticmethod
    def generate_target_url(host: str = "example.com", scheme: str = "http",
                          port: Optional[int] = None, path: str = "") -> str:
        """Generate a target URL"""
        url = f"{scheme}://{host}"
        if port:
            url += f":{port}"
        url += path
        return url

    @staticmethod
    def generate_port_scan_result(open_ports: List[int],
                                 services: Optional[Dict[int, str]] = None) -> Dict:
        """Generate a port scan result"""
        if services is None:
            services = {
                22: 'ssh',
                80: 'http',
                443: 'https',
                3306: 'mysql',
                8080: 'http-proxy'
            }

        return {
            'open_ports': open_ports,
            'services': {port: services.get(port, 'unknown') for port in open_ports},
            'total_ports': len(open_ports)
        }

    @staticmethod
    def generate_vulnerability(severity: str = "medium",
                             name: str = "Test Vulnerability",
                             description: str = "Test description") -> Dict:
        """Generate a vulnerability entry"""
        cvss_scores = {
            'critical': 9.0,
            'high': 7.5,
            'medium': 5.0,
            'low': 3.0,
            'info': 0.0
        }

        return {
            'name': name,
            'severity': severity,
            'description': description,
            'cvss_score': cvss_scores.get(severity, 5.0),
            'discovered_at': '2024-01-01 12:00:00'
        }

    @staticmethod
    def generate_scan_report(tool: str, target: str,
                           findings: List[Dict]) -> Dict:
        """Generate a complete scan report"""
        return {
            'tool': tool,
            'target': target,
            'timestamp': '2024-01-01 12:00:00',
            'duration': 60.0,
            'findings': findings,
            'total_findings': len(findings),
            'success': True
        }

    @staticmethod
    def generate_command_result(command: str, success: bool = True,
                               stdout: str = "", stderr: str = "",
                               duration: float = 1.0) -> Dict:
        """Generate a command execution result"""
        return {
            'command': command,
            'success': success,
            'returncode': 0 if success else 1,
            'stdout': stdout,
            'stderr': stderr,
            'duration': duration,
            'timestamp': '2024-01-01 12:00:00'
        }


class ColorStripper:
    """Helper for removing ANSI color codes from output"""

    ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    @classmethod
    def strip_colors(cls, text: str) -> str:
        """Remove all ANSI color codes from text"""
        return cls.ANSI_ESCAPE_PATTERN.sub('', text)

    @classmethod
    def has_colors(cls, text: str) -> bool:
        """Check if text contains ANSI color codes"""
        return bool(cls.ANSI_ESCAPE_PATTERN.search(text))


class ComparisonHelpers:
    """Helpers for comparing complex data structures"""

    @staticmethod
    def dict_contains(actual: Dict, expected: Dict) -> bool:
        """Check if actual dict contains all keys/values from expected"""
        for key, value in expected.items():
            if key not in actual:
                return False
            if isinstance(value, dict):
                if not ComparisonHelpers.dict_contains(actual[key], value):
                    return False
            elif actual[key] != value:
                return False
        return True

    @staticmethod
    def lists_equal_unordered(list1: List, list2: List) -> bool:
        """Check if two lists contain same elements (order doesn't matter)"""
        return sorted(list1) == sorted(list2)

    @staticmethod
    def assert_dict_contains(actual: Dict, expected: Dict, path: str = ""):
        """Assert that actual contains all expected keys/values"""
        for key, value in expected.items():
            current_path = f"{path}.{key}" if path else key

            assert key in actual, \
                f"Missing key '{current_path}' in actual dict"

            if isinstance(value, dict):
                ComparisonHelpers.assert_dict_contains(
                    actual[key], value, current_path
                )
            else:
                assert actual[key] == value, \
                    f"Value mismatch at '{current_path}': expected {value}, got {actual[key]}"


def create_temp_config(config_data: Dict[str, Any]) -> str:
    """Create a temporary configuration file"""
    import tempfile
    import json

    fd, path = tempfile.mkstemp(suffix='.json')
    with open(path, 'w') as f:
        json.dump(config_data, f)

    return path


def wait_for_condition(condition_func, timeout: float = 5.0,
                       interval: float = 0.1) -> bool:
    """
    Wait for a condition to become true

    Args:
        condition_func: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Check interval in seconds

    Returns:
        True if condition met, False if timeout
    """
    import time

    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)

    return False
