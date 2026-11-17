"""Regression tests for the httpx integration (issue #77).

Covers the two reported bugs plus the health-check false positive:

* the probe endpoint must use ``-u`` for a single target and ``-l`` only
  for an existing file of targets (ProjectDiscovery ``-l`` expects a file);
* binary resolution must reject the Python ``httpx`` CLI (which ``which
  httpx`` still finds) and only accept a binary whose ``-version``
  succeeds and reports a ``vX.Y.Z`` version.

Stdlib-only so these run without importing ``hexstrike_server``.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hexstrike_httpx import (  # noqa: E402
    INSTALL_HINT,
    build_httpx_command,
    find_projectdiscovery_httpx,
    is_projectdiscovery_httpx,
)


def _completed(returncode, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["httpx", "-version"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class BuildHttpxCommandTests(unittest.TestCase):
    def test_single_target_uses_u_not_l(self):
        cmd = build_httpx_command(
            "/home/user/go/bin/httpx", "http://127.0.0.1:8888",
            threads=50, probe=True, tech_detect=True, status_code=True,
        )
        self.assertIn("-u http://127.0.0.1:8888", cmd)
        self.assertNotIn("-l ", cmd)
        self.assertIn("-t 50", cmd)
        self.assertIn("-probe", cmd)
        self.assertIn("-tech-detect", cmd)
        self.assertIn("-sc", cmd)

    def test_existing_target_file_uses_l(self):
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False) as tmp:
            tmp.write("http://127.0.0.1:8888\n")
            path = tmp.name
        try:
            cmd = build_httpx_command("/usr/local/bin/httpx", path)
            self.assertIn(f"-l {path}", cmd)
            self.assertNotIn("-u ", cmd)
        finally:
            os.unlink(path)

    def test_nonexistent_path_is_treated_as_single_target(self):
        cmd = build_httpx_command("/usr/local/bin/httpx", "example.com")
        self.assertIn("-u example.com", cmd)
        self.assertNotIn("-l ", cmd)

    def test_optional_flags_off_by_default(self):
        cmd = build_httpx_command("/usr/local/bin/httpx", "example.com")
        self.assertIn("-probe", cmd)  # probe defaults on, as before
        self.assertNotIn("-tech-detect", cmd)
        self.assertNotIn("-sc", cmd)
        self.assertNotIn("-cl", cmd)
        self.assertNotIn("-title", cmd)
        self.assertNotIn("-server", cmd)


class IsProjectDiscoveryHttpxTests(unittest.TestCase):
    def test_pd_httpx_version_output_accepted(self):
        with mock.patch("hexstrike_httpx.subprocess.run",
                         return_value=_completed(0, stdout="v1.7.1\n")):
            self.assertTrue(is_projectdiscovery_httpx("/usr/local/bin/httpx"))

    def test_pd_httpx_banner_with_version_accepted(self):
        with mock.patch("hexstrike_httpx.subprocess.run",
                         return_value=_completed(
                             0, stdout="Current Version: v1.7.1\n")):
            self.assertTrue(is_projectdiscovery_httpx("/usr/local/bin/httpx"))

    def test_python_httpx_cli_rejected(self):
        # `httpx -version` on the Python CLI: rc=2, "No such option '-e'."
        with mock.patch("hexstrike_httpx.subprocess.run",
                         return_value=_completed(
                             2, stderr="Usage: httpx [OPTIONS] URL\n\n"
                                      "Error: No such option '-e'.")):
            self.assertFalse(is_projectdiscovery_httpx("/venv/bin/httpx"))

    def test_missing_binary_rejected(self):
        with mock.patch("hexstrike_httpx.subprocess.run",
                         side_effect=OSError("No such file")):
            self.assertFalse(is_projectdiscovery_httpx("/nonexistent/httpx"))

    def test_version_output_without_version_number_rejected(self):
        with mock.patch("hexstrike_httpx.subprocess.run",
                         return_value=_completed(0, stdout="httpx\n")):
            self.assertFalse(is_projectdiscovery_httpx("/usr/local/bin/httpx"))


class FindProjectDiscoveryHttpxTests(unittest.TestCase):
    def _mock_run(self, pd_paths):
        """Fake subprocess.run: -version succeeds only for pd_paths."""
        def fake_run(argv, **kwargs):
            binary = argv[0]
            if binary == "go":
                return _completed(0, stdout="/home/user/go\n")
            if binary in pd_paths:
                return _completed(0, stdout="v1.7.1\n")
            return _completed(2, stderr="No such option '-e'.")
        return fake_run

    def test_path_python_cli_rejected_go_bin_accepted(self):
        # `which httpx` finds the Python CLI; ~/go/bin/httpx is the real one.
        with mock.patch.dict(os.environ, {}, clear=False), \
             mock.patch("hexstrike_httpx.shutil.which",
                        return_value="/venv/bin/httpx"), \
             mock.patch("hexstrike_httpx.subprocess.run",
                        side_effect=self._mock_run({"/home/user/go/bin/httpx"})), \
             mock.patch("hexstrike_httpx.os.path.isfile",
                        return_value=True):
            with mock.patch.dict(os.environ, {"GOPATH": "/home/user/go"}):
                self.assertEqual(
                    find_projectdiscovery_httpx(), "/home/user/go/bin/httpx")

    def test_no_pd_binary_anywhere_returns_none(self):
        with mock.patch("hexstrike_httpx.shutil.which",
                        return_value="/venv/bin/httpx"), \
             mock.patch("hexstrike_httpx.subprocess.run",
                        side_effect=self._mock_run(set())), \
             mock.patch("hexstrike_httpx.os.path.isfile",
                        return_value=True):
            with mock.patch.dict(os.environ, {"GOPATH": "/home/user/go"},
                                 clear=False):
                self.assertIsNone(find_projectdiscovery_httpx())

    def test_env_override_is_used_when_valid(self):
        with mock.patch("hexstrike_httpx.shutil.which",
                        return_value="/venv/bin/httpx"), \
             mock.patch("hexstrike_httpx.subprocess.run",
                        side_effect=self._mock_run({"/opt/pd/httpx"})), \
             mock.patch("hexstrike_httpx.os.path.isfile",
                        return_value=True):
            with mock.patch.dict(
                    os.environ, {"HEXSTRIKE_HTTPX_BINARY": "/opt/pd/httpx"}):
                self.assertEqual(
                    find_projectdiscovery_httpx(), "/opt/pd/httpx")

    def test_install_hint_names_the_right_tool(self):
        self.assertIn("ProjectDiscovery", INSTALL_HINT)
        self.assertIn("go install", INSTALL_HINT)
        self.assertIn("HEXSTRIKE_HTTPX_BINARY", INSTALL_HINT)


if __name__ == "__main__":
    unittest.main()
