"""
Pytest configuration and shared fixtures for HexStrike tests

This module provides:
- Flask test client fixtures
- Mock subprocess execution
- Sample tool output fixtures
- Database/cache mocking
- Common test data
"""

import json
import os
import sys
import tempfile
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask

# Add parent directory to path to import HexStrike modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================================
# PYTEST CONFIGURATION HOOKS
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings"""
    # Register custom markers
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "requires_tools: Tests requiring external tools")
    config.addinivalue_line("markers", "requires_network: Tests requiring network")


def pytest_collection_modifyitems(config, items):
    """Modify test items during collection"""
    # Automatically mark tests based on their location
    for item in items:
        # Mark tests in unit/ directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        # Mark tests in integration/ directory
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


# ============================================================================
# FLASK APPLICATION FIXTURES
# ============================================================================

@pytest.fixture
def app():
    """Create and configure a Flask test application"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['JSON_SORT_KEYS'] = False
    app.config['SECRET_KEY'] = 'test-secret-key'
    return app


@pytest.fixture
def client(app):
    """Create a Flask test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a Flask CLI test runner"""
    return app.test_cli_runner()


# ============================================================================
# SUBPROCESS & COMMAND EXECUTION MOCKING
# ============================================================================

@pytest.fixture
def mock_subprocess():
    """Mock subprocess execution to prevent actual tool execution"""
    with patch('subprocess.Popen') as mock_popen, \
         patch('subprocess.run') as mock_run:

        # Configure Popen mock
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b"mock output", b"")
        process_mock.poll.return_value = 0
        process_mock.wait.return_value = 0
        process_mock.stdout = MagicMock()
        process_mock.stderr = MagicMock()
        process_mock.stdout.readline = MagicMock(return_value='')
        process_mock.stderr.readline = MagicMock(return_value='')

        mock_popen.return_value = process_mock

        # Configure run mock
        run_result = MagicMock()
        run_result.returncode = 0
        run_result.stdout = b"mock output"
        run_result.stderr = b""
        mock_run.return_value = run_result

        yield {
            'popen': mock_popen,
            'run': mock_run,
            'process': process_mock,
            'result': run_result
        }


@pytest.fixture
def mock_tool_execution():
    """Mock external security tool execution with configurable responses"""

    class MockToolExecutor:
        """Helper class for mocking tool execution"""

        def __init__(self):
            self.call_count = 0
            self.calls = []
            self.responses = {}

        def add_response(self, tool_name: str, stdout: str = "", stderr: str = "",
                        returncode: int = 0):
            """Add a mock response for a specific tool"""
            self.responses[tool_name] = {
                'stdout': stdout.encode() if isinstance(stdout, str) else stdout,
                'stderr': stderr.encode() if isinstance(stderr, str) else stderr,
                'returncode': returncode
            }

        def get_response(self, command: str):
            """Get mock response based on command"""
            # Extract tool name from command
            tool_name = command.split()[0] if command else ''

            # Return configured response or default
            if tool_name in self.responses:
                return self.responses[tool_name]

            # Default response
            return {
                'stdout': b"Mock tool output",
                'stderr': b"",
                'returncode': 0
            }

        def mock_popen(self, *args, **kwargs):
            """Mock Popen call"""
            self.call_count += 1
            command = args[0] if args else kwargs.get('args', [''])[0]
            self.calls.append(command)

            response = self.get_response(command if isinstance(command, str) else ' '.join(command))

            process = MagicMock()
            process.returncode = response['returncode']
            process.communicate.return_value = (response['stdout'], response['stderr'])
            process.poll.return_value = response['returncode']
            process.wait.return_value = response['returncode']

            return process

    executor = MockToolExecutor()

    with patch('subprocess.Popen', side_effect=executor.mock_popen):
        yield executor


# ============================================================================
# FILE SYSTEM & TEMP DIRECTORY FIXTURES
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_file():
    """Create a temporary file for testing"""
    fd, path = tempfile.mkstemp()
    yield path
    os.close(fd)
    if os.path.exists(path):
        os.unlink(path)


# ============================================================================
# TIME & DATETIME MOCKING
# ============================================================================

@pytest.fixture
def frozen_time():
    """Mock time.time() to return a fixed value"""
    fixed_time = 1234567890.0
    with patch('time.time', return_value=fixed_time):
        yield fixed_time


@pytest.fixture
def mock_datetime():
    """Mock datetime.datetime.now() to return a fixed value"""
    fixed_datetime = datetime(2024, 1, 1, 12, 0, 0)

    class MockDateTime:
        @classmethod
        def now(cls):
            return fixed_datetime

    with patch('datetime.datetime', MockDateTime):
        yield fixed_datetime


# ============================================================================
# NETWORK & HTTP MOCKING
# ============================================================================

@pytest.fixture
def mock_requests():
    """Mock requests library for HTTP calls"""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post, \
         patch('requests.put') as mock_put, \
         patch('requests.delete') as mock_delete:

        # Configure default responses
        response = MagicMock()
        response.status_code = 200
        response.text = "Mock response"
        response.json.return_value = {"status": "success"}
        response.content = b"Mock response"

        mock_get.return_value = response
        mock_post.return_value = response
        mock_put.return_value = response
        mock_delete.return_value = response

        yield {
            'get': mock_get,
            'post': mock_post,
            'put': mock_put,
            'delete': mock_delete,
            'response': response
        }


# ============================================================================
# SYSTEM METRICS MOCKING
# ============================================================================

@pytest.fixture
def mock_psutil():
    """Mock psutil for system metrics"""
    with patch('psutil.cpu_percent', return_value=50.0), \
         patch('psutil.virtual_memory') as mock_mem, \
         patch('psutil.disk_usage') as mock_disk, \
         patch('psutil.net_io_counters') as mock_net:

        # Configure memory mock
        mem = MagicMock()
        mem.percent = 60.0
        mock_mem.return_value = mem

        # Configure disk mock
        disk = MagicMock()
        disk.percent = 70.0
        mock_disk.return_value = disk

        # Configure network mock
        net = MagicMock()
        net._asdict.return_value = {
            'bytes_sent': 1000,
            'bytes_recv': 2000
        }
        mock_net.return_value = net

        yield {
            'cpu': 50.0,
            'memory': mem,
            'disk': disk,
            'network': net
        }


# ============================================================================
# SAMPLE TOOL OUTPUT FIXTURES
# ============================================================================

@pytest.fixture
def sample_nmap_output():
    """Return sample nmap scan output"""
    return """Starting Nmap 7.94 ( https://nmap.org )
Nmap scan report for scanme.nmap.org (45.33.32.156)
Host is up (0.065s latency).
Not shown: 996 closed tcp ports (conn-refused)
PORT      STATE SERVICE
22/tcp    open  ssh
80/tcp    open  http
9929/tcp  open  nping-echo
31337/tcp open  Elite

Nmap done: 1 IP address (1 host up) scanned in 1.23 seconds
"""


@pytest.fixture
def sample_gobuster_output():
    """Return sample gobuster directory scan output"""
    return """===============================================================
Gobuster v3.6
by OJ Reeves (@TheColonial) & Christian Mehlmauer (@firefart)
===============================================================
[+] Url:                     http://example.com
[+] Method:                  GET
[+] Threads:                 10
[+] Wordlist:                /usr/share/wordlists/dirb/common.txt
[+] Status codes:            200,204,301,302,307,401,403
===============================================================
/admin                (Status: 301) [Size: 234] [--> http://example.com/admin/]
/images               (Status: 301) [Size: 235] [--> http://example.com/images/]
/index.html           (Status: 200) [Size: 10918]
/uploads              (Status: 301) [Size: 236] [--> http://example.com/uploads/]
===============================================================
"""


@pytest.fixture
def sample_sqlmap_output():
    """Return sample sqlmap vulnerability scan output"""
    return """[*] starting @ 12:34:56

[12:34:56] [INFO] testing connection to the target URL
[12:34:57] [INFO] testing if the target URL content is stable
[12:34:58] [INFO] target URL content is stable
[12:34:58] [INFO] testing if GET parameter 'id' is dynamic
[12:35:00] [INFO] GET parameter 'id' appears to be dynamic
[12:35:01] [INFO] heuristic (basic) test shows that GET parameter 'id' might be injectable
[12:35:02] [INFO] testing for SQL injection on GET parameter 'id'
[12:35:05] [INFO] GET parameter 'id' is vulnerable. Do you want to keep testing the others?

GET parameter 'id' is vulnerable:
    Type: boolean-based blind
    Title: AND boolean-based blind - WHERE or HAVING clause
    Payload: id=1 AND 1=1

[*] shutting down @ 12:35:06
"""


@pytest.fixture
def sample_nuclei_output():
    """Return sample nuclei vulnerability scan output"""
    return """[2024-01-01 12:00:00] [CVE-2021-12345] [http] [critical] http://example.com/vulnerable
[2024-01-01 12:00:01] [CVE-2022-67890] [http] [high] http://example.com/outdated
[2024-01-01 12:00:02] [exposed-panel] [http] [medium] http://example.com/admin
[2024-01-01 12:00:03] [ssl-weak-cipher] [network] [low] https://example.com:443
"""


@pytest.fixture
def sample_nikto_output():
    """Return sample nikto web scanner output"""
    return """- Nikto v2.5.0
---------------------------------------------------------------------------
+ Target IP:          192.168.1.100
+ Target Hostname:    example.com
+ Target Port:        80
+ Start Time:         2024-01-01 12:00:00
---------------------------------------------------------------------------
+ Server: Apache/2.4.41 (Ubuntu)
+ The anti-clickjacking X-Frame-Options header is not present.
+ The X-XSS-Protection header is not defined.
+ The X-Content-Type-Options header is not set.
+ Root page / redirects to: login.php
+ No CGI Directories found (use '-C all' to force check all possible dirs)
+ Apache/2.4.41 appears to be outdated (current is at least Apache/2.4.54).
+ Allowed HTTP Methods: GET, POST, OPTIONS, HEAD
+ /admin/: Admin login page/section found.
+ 8090 requests: 0 error(s) and 7 item(s) reported on remote host
+ End Time:           2024-01-01 12:05:00 (300 seconds)
---------------------------------------------------------------------------
"""


# ============================================================================
# SAMPLE VULNERABILITY DATA
# ============================================================================

@pytest.fixture
def sample_vulnerability_data():
    """Return sample vulnerability data for testing"""
    return {
        'critical': {
            'name': 'SQL Injection in login form',
            'severity': 'critical',
            'description': 'The login form is vulnerable to SQL injection attacks',
            'cvss_score': 9.8,
            'cve_id': 'CVE-2024-12345'
        },
        'high': {
            'name': 'Remote Code Execution',
            'severity': 'high',
            'description': 'Unauthenticated RCE via file upload',
            'cvss_score': 8.5,
            'cve_id': 'CVE-2024-67890'
        },
        'medium': {
            'name': 'Cross-Site Scripting (XSS)',
            'severity': 'medium',
            'description': 'Reflected XSS in search parameter',
            'cvss_score': 6.1,
            'cve_id': None
        },
        'low': {
            'name': 'Information Disclosure',
            'severity': 'low',
            'description': 'Server version exposed in headers',
            'cvss_score': 3.7,
            'cve_id': None
        }
    }


# ============================================================================
# CACHE & STORAGE FIXTURES
# ============================================================================

@pytest.fixture
def mock_cache():
    """Mock cache implementation for testing"""

    class MockCache:
        def __init__(self):
            self.storage = {}
            self.stats = {"hits": 0, "misses": 0, "evictions": 0}

        def get(self, key):
            if key in self.storage:
                self.stats["hits"] += 1
                return self.storage[key]
            self.stats["misses"] += 1
            return None

        def set(self, key, value):
            self.storage[key] = value

        def clear(self):
            self.storage.clear()

        def get_stats(self):
            total = self.stats["hits"] + self.stats["misses"]
            hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
            return {
                "size": len(self.storage),
                "hit_rate": f"{hit_rate:.1f}%",
                **self.stats
            }

    return MockCache()


# ============================================================================
# LOGGING & OUTPUT FIXTURES
# ============================================================================

@pytest.fixture
def capture_logs(caplog):
    """Fixture to capture and analyze log output"""
    import logging
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture
def suppress_output(monkeypatch):
    """Suppress stdout/stderr during tests"""
    import io
    monkeypatch.setattr('sys.stdout', io.StringIO())
    monkeypatch.setattr('sys.stderr', io.StringIO())


# ============================================================================
# COMMON TEST DATA
# ============================================================================

@pytest.fixture
def sample_target_data():
    """Return sample target data for testing"""
    return {
        'web_app': {
            'url': 'http://example.com',
            'type': 'web_application',
            'ports': [80, 443],
            'technologies': ['Apache', 'PHP', 'MySQL']
        },
        'network_host': {
            'ip': '192.168.1.100',
            'type': 'network_host',
            'hostname': 'target.local',
            'open_ports': [22, 80, 443, 3306]
        },
        'api': {
            'url': 'https://api.example.com',
            'type': 'api_endpoint',
            'version': 'v1',
            'auth': 'bearer_token'
        }
    }


@pytest.fixture
def sample_scan_results():
    """Return sample scan results for testing"""
    return {
        'nmap': {
            'tool': 'nmap',
            'target': '192.168.1.100',
            'open_ports': [22, 80, 443],
            'services': {
                22: 'ssh',
                80: 'http',
                443: 'https'
            },
            'duration': 12.34
        },
        'gobuster': {
            'tool': 'gobuster',
            'target': 'http://example.com',
            'found_paths': ['/admin', '/uploads', '/api'],
            'total_requests': 4615,
            'duration': 45.67
        },
        'sqlmap': {
            'tool': 'sqlmap',
            'target': 'http://example.com/login?id=1',
            'vulnerable': True,
            'injection_type': 'boolean-based blind',
            'parameter': 'id',
            'duration': 120.5
        }
    }
