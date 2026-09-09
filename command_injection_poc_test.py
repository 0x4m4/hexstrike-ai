import os
import sys
import tempfile
import time
import unittest

sys.argv = ["hexstrike_server.py"]

import hexstrike_server


class TestNmapCommandInjection(unittest.TestCase):
    """The /api/tools/nmap and /api/tools/gobuster endpoints build a
    shell=True command by string interpolation. Before the fix, the
    client-supplied target/url/ports/wordlist parameters were interpolated
    with no escaping, so a target like '127.0.0.1; touch /tmp/x #' ran the
    appended command. safe_shell_arg() (shlex.quote) now wraps those values.
    """

    def setUp(self):
        self.marker_path = os.path.join(tempfile.gettempdir(), "hexstrike_poc_marker")
        if os.path.exists(self.marker_path):
            os.remove(self.marker_path)
        self.client = hexstrike_server.app.test_client()

    def tearDown(self):
        if os.path.exists(self.marker_path):
            os.remove(self.marker_path)

    def _marker_created(self, timeout=5):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if os.path.exists(self.marker_path):
                return True
            time.sleep(0.1)
        return False

    def test_nmap_target_injection_blocked(self):
        injected_target = f"127.0.0.1; touch {self.marker_path} #"
        resp = self.client.post(
            "/api/tools/nmap",
            json={"target": injected_target, "scan_type": "-sn", "use_recovery": False},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            self._marker_created(timeout=2),
            "shell metacharacters in 'target' must not execute as a separate command",
        )

    def test_gobuster_url_injection_blocked(self):
        injected_url = f"http://127.0.0.1; touch {self.marker_path} #"
        resp = self.client.post(
            "/api/tools/gobuster",
            json={"url": injected_url, "mode": "dir", "use_recovery": False},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            self._marker_created(timeout=2),
            "shell metacharacters in 'url' must not execute as a separate command",
        )

    def test_nmap_legitimate_target_still_scans(self):
        resp = self.client.post(
            "/api/tools/nmap",
            json={"target": "127.0.0.1", "scan_type": "-sn", "use_recovery": False},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertTrue(body.get("success"), f"legitimate scan should still succeed: {body}")


if __name__ == "__main__":
    unittest.main()
