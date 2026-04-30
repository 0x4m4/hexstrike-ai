"""
Mock utilities for HexStrike testing

This module provides comprehensive mocking utilities for:
- External security tool execution
- Subprocess calls
- Network requests
- File system operations
"""

import subprocess
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock


class MockSubprocessResult:
    """Mock subprocess.CompletedProcess result"""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout.encode() if isinstance(stdout, str) else stdout
        self.stderr = stderr.encode() if isinstance(stderr, str) else stderr
        self.args = []


class MockProcess:
    """Mock subprocess.Popen process"""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self.pid = 12345
        self.stdout = MagicMock()
        self.stderr = MagicMock()

        # Configure readline to return lines
        self.stdout.readline = MagicMock(return_value='')
        self.stderr.readline = MagicMock(return_value='')

    def communicate(self, timeout=None):
        """Mock communicate method"""
        stdout = self._stdout.encode() if isinstance(self._stdout, str) else self._stdout
        stderr = self._stderr.encode() if isinstance(self._stderr, str) else self._stderr
        return (stdout, stderr)

    def poll(self):
        """Mock poll method"""
        return self.returncode

    def wait(self, timeout=None):
        """Mock wait method"""
        return self.returncode

    def kill(self):
        """Mock kill method"""
        pass

    def terminate(self):
        """Mock terminate method"""
        pass


class ToolOutputMocker:
    """Helper class for mocking security tool outputs"""

    # Common tool outputs
    NMAP_OUTPUT = """Starting Nmap 7.94
Nmap scan report for {target}
Host is up (0.050s latency).
PORT    STATE SERVICE
22/tcp  open  ssh
80/tcp  open  http
443/tcp open  https

Nmap done: 1 IP address (1 host up) scanned in 2.45 seconds
"""

    GOBUSTER_OUTPUT = """===============================================================
Gobuster v3.6
===============================================================
[+] Url:                     {target}
[+] Threads:                 10
[+] Wordlist:                common.txt
===============================================================
/admin                (Status: 301)
/api                  (Status: 200)
/uploads              (Status: 403)
===============================================================
"""

    SQLMAP_OUTPUT = """[*] starting @ 12:00:00
[INFO] testing connection to the target URL
[INFO] testing if GET parameter 'id' is dynamic
[INFO] GET parameter 'id' appears to be dynamic
[INFO] GET parameter 'id' is vulnerable

GET parameter 'id' is vulnerable:
    Type: boolean-based blind
    Title: AND boolean-based blind
    Payload: id=1 AND 1=1

[*] shutting down
"""

    NIKTO_OUTPUT = """- Nikto v2.5.0
+ Target IP:          {target}
+ Target Port:        80
+ Server: Apache/2.4.41
+ The X-Frame-Options header is not present.
+ The X-XSS-Protection header is not defined.
+ /admin/: Admin login page found.
+ 1000 requests: 0 error(s) and 3 item(s) reported
"""

    NUCLEI_OUTPUT = """[CVE-2021-12345] [http] [critical] {target}/vuln
[exposed-panel] [http] [medium] {target}/admin
[ssl-weak-cipher] [network] [low] {target}:443
"""

    FEROXBUSTER_OUTPUT = """200      GET       10l       50w      500c {target}/index.html
301      GET        7l       20c      200c {target}/admin => /admin/
403      GET        7l       20c      150c {target}/uploads
200      GET       15l       75w      750c {target}/api
"""

    FFUF_OUTPUT = """admin                   [Status: 301, Size: 234, Words: 14, Lines: 8]
api                     [Status: 200, Size: 1024, Words: 50, Lines: 20]
uploads                 [Status: 403, Size: 150, Words: 10, Lines: 5]
"""

    HYDRA_OUTPUT = """Hydra v9.5 starting
[DATA] max 16 tasks per 1 server, overall 16 tasks
[DATA] attacking http-post-form://{target}/login
[80][http-post-form] host: {target}   login: admin   password: password123
1 of 1 target successfully completed, 1 valid password found
"""

    JOHN_OUTPUT = """Loaded 1 password hash (Raw-MD5 [MD5 128/128 SSE2 4x3])
password123      (user1)
1 password hash cracked, 0 left
"""

    WHATWEB_OUTPUT = """http://{target} [200 OK] Apache[2.4.41], Country[UNITED STATES][US],
Email[admin@example.com], HTML5, HTTPServer[Ubuntu Linux][Apache/2.4.41 (Ubuntu)],
IP[192.168.1.100], JQuery[3.6.0], Script, Title[Example Site], X-Powered-By[PHP/7.4.3]
"""

    WAFW00F_OUTPUT = """[*] Checking {target}
[+] The site {target} is behind Cloudflare (Cloudflare Inc.) WAF.
[~] Number of requests: 7
"""

    @classmethod
    def get_tool_output(cls, tool_name: str, target: str = "example.com", **kwargs) -> str:
        """Get mock output for a specific tool"""
        output_map = {
            'nmap': cls.NMAP_OUTPUT,
            'gobuster': cls.GOBUSTER_OUTPUT,
            'sqlmap': cls.SQLMAP_OUTPUT,
            'nikto': cls.NIKTO_OUTPUT,
            'nuclei': cls.NUCLEI_OUTPUT,
            'feroxbuster': cls.FEROXBUSTER_OUTPUT,
            'ffuf': cls.FFUF_OUTPUT,
            'hydra': cls.HYDRA_OUTPUT,
            'john': cls.JOHN_OUTPUT,
            'whatweb': cls.WHATWEB_OUTPUT,
            'wafw00f': cls.WAFW00F_OUTPUT,
        }

        template = output_map.get(tool_name.lower(), "Mock output for {tool_name}")
        return template.format(target=target, tool_name=tool_name, **kwargs)

    @classmethod
    def create_mock_process(cls, tool_name: str, target: str = "example.com",
                          returncode: int = 0, **kwargs) -> MockProcess:
        """Create a mock process with tool output"""
        output = cls.get_tool_output(tool_name, target, **kwargs)
        return MockProcess(returncode=returncode, stdout=output, stderr="")

    @classmethod
    def create_mock_result(cls, tool_name: str, target: str = "example.com",
                          returncode: int = 0, **kwargs) -> MockSubprocessResult:
        """Create a mock subprocess result with tool output"""
        output = cls.get_tool_output(tool_name, target, **kwargs)
        return MockSubprocessResult(returncode=returncode, stdout=output, stderr="")


class CommandExecutionMocker:
    """Mock command execution with customizable behavior"""

    def __init__(self):
        self.commands_executed = []
        self.responses = {}
        self.default_response = MockSubprocessResult()

    def add_response(self, command_pattern: str, returncode: int = 0,
                    stdout: str = "", stderr: str = ""):
        """Add a mock response for commands matching a pattern"""
        self.responses[command_pattern] = MockSubprocessResult(
            returncode=returncode,
            stdout=stdout,
            stderr=stderr
        )

    def mock_run(self, *args, **kwargs):
        """Mock subprocess.run"""
        command = args[0] if args else kwargs.get('args', [])
        self.commands_executed.append(command)

        # Find matching response
        command_str = ' '.join(command) if isinstance(command, list) else str(command)

        for pattern, response in self.responses.items():
            if pattern in command_str:
                return response

        return self.default_response

    def mock_popen(self, *args, **kwargs):
        """Mock subprocess.Popen"""
        command = args[0] if args else kwargs.get('args', [])
        self.commands_executed.append(command)

        # Find matching response
        command_str = ' '.join(command) if isinstance(command, list) else str(command)

        for pattern, response in self.responses.items():
            if pattern in command_str:
                return MockProcess(
                    returncode=response.returncode,
                    stdout=response.stdout.decode() if isinstance(response.stdout, bytes) else response.stdout,
                    stderr=response.stderr.decode() if isinstance(response.stderr, bytes) else response.stderr
                )

        return MockProcess()

    def get_executed_commands(self) -> List:
        """Get list of executed commands"""
        return self.commands_executed

    def reset(self):
        """Reset the mocker state"""
        self.commands_executed = []
        self.responses = {}


class NetworkMocker:
    """Mock network requests and responses"""

    def __init__(self):
        self.requests_made = []
        self.responses = {}
        self.default_response = {
            'status_code': 200,
            'text': 'Mock response',
            'content': b'Mock response',
            'json': {'status': 'success'}
        }

    def add_response(self, url_pattern: str, method: str = 'GET', **response_data):
        """Add a mock response for a URL pattern"""
        key = f"{method.upper()}:{url_pattern}"
        self.responses[key] = response_data

    def mock_request(self, method: str, url: str, **kwargs):
        """Mock a network request"""
        self.requests_made.append({
            'method': method,
            'url': url,
            'kwargs': kwargs
        })

        # Find matching response
        for pattern, response in self.responses.items():
            if pattern in f"{method.upper()}:{url}":
                mock_response = MagicMock()
                for key, value in response.items():
                    setattr(mock_response, key, value)
                return mock_response

        # Return default response
        mock_response = MagicMock()
        for key, value in self.default_response.items():
            setattr(mock_response, key, value)
        return mock_response


def create_mock_file_system(files: Dict[str, str]) -> Dict[str, Any]:
    """
    Create a mock file system for testing

    Args:
        files: Dictionary mapping file paths to content

    Returns:
        Mock file system with open, exists, and read operations
    """
    file_contents = files.copy()

    def mock_open(path, mode='r', **kwargs):
        """Mock file open operation"""
        if path in file_contents:
            mock_file = MagicMock()
            content = file_contents[path]

            if 'b' in mode:
                content = content.encode() if isinstance(content, str) else content
            else:
                content = content.decode() if isinstance(content, bytes) else content

            mock_file.read.return_value = content
            mock_file.__enter__.return_value = mock_file
            mock_file.__exit__.return_value = None
            return mock_file
        raise FileNotFoundError(f"File not found: {path}")

    def mock_exists(path):
        """Mock file existence check"""
        return path in file_contents

    return {
        'open': mock_open,
        'exists': mock_exists,
        'files': file_contents
    }
