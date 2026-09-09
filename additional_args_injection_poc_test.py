import os
import sys
import tempfile
import time
import unittest

sys.argv = ["hexstrike_server.py"]

import hexstrike_server


class TestAdditionalArgsInjection(unittest.TestCase):
    """additional_args is a client-supplied string of extra CLI flags that
    is appended to the shell=True command with no sanitization at all,
    across every /api/tools/* endpoint that accepts it (97 endpoints). A
    target/url fix (quoting one field) does not close this: an attacker
    who cannot inject via 'target' can still inject via 'additional_args'
    on the same endpoint, including the two endpoints PR #264 fixed.
    """

    def setUp(self):
        self.marker_path = os.path.join(tempfile.gettempdir(), "hexstrike_additional_args_marker")
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

    def test_nmap_additional_args_injection_blocked(self):
        injected = f"-sn; touch {self.marker_path} #"
        resp = self.client.post(
            "/api/tools/nmap",
            json={"target": "127.0.0.1", "additional_args": injected, "use_recovery": False},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            self._marker_created(timeout=2),
            "shell metacharacters in 'additional_args' must not execute as a separate command",
        )

    def test_gobuster_additional_args_injection_blocked(self):
        injected = f"-t 1; touch {self.marker_path} #"
        resp = self.client.post(
            "/api/tools/gobuster",
            json={"url": "http://127.0.0.1", "mode": "dir", "additional_args": injected, "use_recovery": False},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            self._marker_created(timeout=2),
            "shell metacharacters in 'additional_args' must not execute as a separate command",
        )

    def test_nmap_legitimate_additional_args_still_applies(self):
        resp = self.client.post(
            "/api/tools/nmap",
            json={"target": "127.0.0.1", "scan_type": "-sn", "additional_args": "-T4 -Pn", "use_recovery": False},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertTrue(body.get("success"), f"legitimate scan should still succeed: {body}")


if __name__ == "__main__":
    unittest.main()
