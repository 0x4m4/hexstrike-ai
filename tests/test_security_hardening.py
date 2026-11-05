"""Regression tests for the API server security hardening.

Run with: python3 -m unittest discover -s tests
(or: python3 -m pytest tests/test_security_hardening.py)

Heavy optional dependencies (selenium, mitmproxy, ...) are stubbed when not
installed so the server module can be imported in CI without them.
"""

import os
import runpy
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_PATH = REPO_ROOT / "hexstrike_server.py"
sys.path.insert(0, str(REPO_ROOT))


def _stub_module(name, **attrs):
    if name in sys.modules:
        return
    try:
        __import__(name)
        return
    except ImportError:
        pass
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module


class _Dummy:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return _Dummy()


def _install_stubs():
    _stub_module("psutil")
    _stub_module("bs4", BeautifulSoup=_Dummy)
    _stub_module("aiohttp")
    _stub_module("selenium", webdriver=_Dummy())
    for name in (
        "selenium.webdriver",
        "selenium.webdriver.chrome",
        "selenium.webdriver.chrome.options",
        "selenium.webdriver.common",
        "selenium.webdriver.common.by",
        "selenium.webdriver.support",
        "selenium.webdriver.support.ui",
        "selenium.webdriver.support.expected_conditions",
        "selenium.common",
        "selenium.common.exceptions",
    ):
        _stub_module(name)
    sys.modules["selenium.webdriver.chrome.options"].Options = _Dummy
    sys.modules["selenium.webdriver.common.by"].By = _Dummy
    sys.modules["selenium.webdriver.support.ui"].WebDriverWait = _Dummy
    sys.modules["selenium.common.exceptions"].TimeoutException = type("TimeoutException", (Exception,), {})
    sys.modules["selenium.common.exceptions"].WebDriverException = type("WebDriverException", (Exception,), {})
    _stub_module("mitmproxy", http=types.SimpleNamespace())
    _stub_module("mitmproxy.http", HTTPFlow=_Dummy)
    _stub_module("mitmproxy.tools")
    _stub_module("mitmproxy.tools.dump", DumpMaster=_Dummy)
    _stub_module("mitmproxy.options", Options=_Dummy)


_install_stubs()

import hexstrike_server as hs  # noqa: E402


class TestAuth(unittest.TestCase):
    def setUp(self):
        self.client = hs.app.test_client()

    def test_loopback_detection(self):
        for host in ("127.0.0.1", "127.0.0.53", "::1", "localhost"):
            self.assertTrue(hs.is_loopback_host(host), host)
        for host in ("0.0.0.0", "192.168.1.10", "localhost.evil.example", ""):
            self.assertFalse(hs.is_loopback_host(host), host)

    def test_command_rejected_without_token(self):
        with mock.patch.object(hs, "API_TOKEN", "test-secret"):
            response = self.client.post("/api/command", json={"command": "echo should-not-run"})
            self.assertEqual(response.status_code, 401)

    def test_wrong_or_malformed_token_rejected(self):
        with mock.patch.object(hs, "API_TOKEN", "test-secret"):
            for value in ("Bearer wrong", "test-secret", "bearer test-secret", "Bearer é"):
                response = self.client.get("/health", headers={"Authorization": value})
                self.assertEqual(response.status_code, 401, value)

    def test_command_allowed_with_token(self):
        with mock.patch.object(hs, "API_TOKEN", "test-secret"):
            response = self.client.post(
                "/api/command",
                json={"command": "echo hexstrike-auth-ok", "use_cache": False},
                headers={"Authorization": "Bearer test-secret", "Host": "remote.example:8888"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("hexstrike-auth-ok", response.get_json().get("stdout", ""))

    def test_no_token_allows_only_loopback_host_header(self):
        """Without a token, a non-loopback Host (DNS rebinding) is refused."""
        with mock.patch.object(hs, "API_TOKEN", ""):
            for host in ("localhost:8888", "127.0.0.1:8888", "[::1]:8888"):
                self.assertEqual(self.client.get("/api/files/list", headers={"Host": host}).status_code, 200, host)
            for host in ("evil.example:8888", "192.168.1.5:8888", "127.0.0.1.evil.example"):
                response = self.client.post("/api/command", json={"command": "echo no"}, headers={"Host": host})
                self.assertEqual(response.status_code, 403, host)


class TestFileContainment(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name) / "base"
        self.manager = hs.FileOperationsManager(base_dir=str(base))

    def test_normal_file_roundtrip(self):
        self.assertTrue(self.manager.create_file("sub/ok.txt", "hello")["success"])
        self.assertTrue(self.manager.modify_file("sub/ok.txt", "!", append=True)["success"])
        self.assertTrue(self.manager.list_files("sub")["success"])
        self.assertTrue(self.manager.delete_file("sub")["success"])

    def test_dotdot_escape_blocked(self):
        result = self.manager.create_file("../escape.txt", "pwned")
        self.assertFalse(result["success"])
        self.assertFalse((Path(self.tmp.name) / "escape.txt").exists())

    def test_absolute_path_blocked(self):
        target = Path(self.tmp.name) / "absolute.txt"
        target.write_text("original")
        self.assertFalse(self.manager.create_file(str(target), "pwned")["success"])
        self.assertFalse(self.manager.modify_file(str(target), "pwned")["success"])
        self.assertEqual(target.read_text(), "original")

    def test_symlink_escape_blocked(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (self.manager.base_dir / "link").symlink_to(outside)
        self.assertFalse(self.manager.create_file("link/x.txt", "pwned")["success"])
        self.assertFalse((outside / "x.txt").exists())

    def test_delete_outside_base_blocked(self):
        outside = Path(self.tmp.name) / "outside.txt"
        outside.write_text("keep me")
        self.assertFalse(self.manager.delete_file("../outside.txt")["success"])
        self.assertTrue(outside.exists())

    def test_delete_base_dir_blocked(self):
        self.assertFalse(self.manager.delete_file(".")["success"])
        self.assertTrue(self.manager.base_dir.exists())

    def test_list_outside_base_blocked(self):
        self.assertFalse(self.manager.list_files("/etc")["success"])

    def test_venv_name_escape_blocked(self):
        envs = hs.PythonEnvironmentManager(base_dir=str(Path(self.tmp.name) / "envs"))
        for name in ("../escape", "/tmp/escape", "", "."):
            with self.assertRaises(ValueError, msg=name):
                envs.create_venv(name)
        self.assertFalse((Path(self.tmp.name) / "escape").exists())

    def test_python_execute_endpoint_refuses_escaping_filename(self):
        target = Path(self.tmp.name) / "planted.py"
        client = hs.app.test_client()
        with mock.patch.object(hs, "API_TOKEN", ""):
            response = client.post("/api/python/execute", headers={"Host": "localhost"},
                                   json={"script": "print(1)", "filename": str(target)})
        self.assertNotEqual(response.status_code, 200)
        self.assertFalse(target.exists())


class TestBrowserScheme(unittest.TestCase):
    def test_non_web_schemes_blocked(self):
        agent = hs.BrowserAgent()
        with mock.patch.object(agent, "setup_browser") as setup:
            for url in ("file:///etc/passwd", "javascript:alert(1)", "data:text/html,x", "chrome://settings", "/etc/passwd"):
                result = agent.navigate_and_inspect(url)
                self.assertFalse(result["success"], url)
                self.assertIn("scheme", result["error"])
            setup.assert_not_called()


class TestStartup(unittest.TestCase):
    """Run the module as __main__ with Flask.run patched to see what it binds."""

    def _start(self, argv, env):
        clean = {k: v for k, v in os.environ.items() if not k.startswith("HEXSTRIKE_")}
        clean.update(env)
        with mock.patch.dict(os.environ, clean, clear=True), \
                mock.patch.object(sys, "argv", [str(SERVER_PATH), *argv]), \
                mock.patch("flask.Flask.run") as run:
            try:
                runpy.run_path(str(SERVER_PATH), run_name="__main__")
                exit_code = None
            except SystemExit as exc:
                exit_code = exc.code
        return exit_code, run

    def test_default_binds_loopback(self):
        code, run = self._start([], {})
        self.assertIsNone(code)
        self.assertEqual(run.call_args.kwargs["host"], "127.0.0.1")

    def test_env_host_is_honoured(self):
        code, run = self._start([], {"HEXSTRIKE_HOST": "::1"})
        self.assertIsNone(code)
        self.assertEqual(run.call_args.kwargs["host"], "::1")

    def test_non_loopback_without_token_refused(self):
        for argv, env in ((["--host", "0.0.0.0"], {}), ([], {"HEXSTRIKE_HOST": "0.0.0.0"})):
            code, run = self._start(argv, env)
            self.assertEqual(code, 1)
            run.assert_not_called()

    def test_non_loopback_debug_refused(self):
        code, run = self._start(["--host", "0.0.0.0", "--debug"], {"HEXSTRIKE_API_TOKEN": "x"})
        self.assertEqual(code, 1)
        run.assert_not_called()

    def test_non_loopback_with_token_allowed(self):
        code, run = self._start(["--host", "0.0.0.0"], {"HEXSTRIKE_API_TOKEN": "x"})
        self.assertIsNone(code)
        self.assertEqual(run.call_args.kwargs["host"], "0.0.0.0")


class TestMcpClient(unittest.TestCase):
    def test_client_sends_bearer_token_from_env(self):
        for name in ("mcp", "mcp.server", "mcp.server.fastmcp"):
            _stub_module(name)
        sys.modules["mcp.server.fastmcp"].FastMCP = getattr(sys.modules["mcp.server.fastmcp"], "FastMCP", _Dummy)
        import hexstrike_mcp
        with mock.patch.dict(os.environ, {"HEXSTRIKE_API_TOKEN": "tok"}), \
                mock.patch.object(hexstrike_mcp, "MAX_RETRIES", 0):
            client = hexstrike_mcp.HexStrikeClient("http://127.0.0.1:1")
        self.assertEqual(client.session.headers.get("Authorization"), "Bearer tok")


if __name__ == "__main__":
    unittest.main()
