#!/usr/bin/env python3
"""Unit tests for critical alert paging (no external network)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

SANDBOX = Path(__file__).resolve().parent
sys.path.insert(0, str(SANDBOX))

import alert_paging  # noqa: E402


class TestAlertPaging(unittest.TestCase):
    def test_should_page_respects_env(self) -> None:
        os.environ.pop("ALERT_PAGING_ENABLED", None)
        os.environ.pop("ALERT_WEBHOOK_URL", None)
        self.assertFalse(
            alert_paging.should_page({"severity": "critical", "type": "rpc_mismatch"})
        )
        os.environ["ALERT_PAGING_ENABLED"] = "true"
        os.environ["ALERT_WEBHOOK_URL"] = "http://127.0.0.1:9/hook"
        self.assertTrue(
            alert_paging.should_page({"severity": "critical", "type": "rpc_mismatch"})
        )
        self.assertTrue(alert_paging.should_page({"type": "BLOCK_COMPROMISED_FUNDER"}))

    def test_page_alert_posts_json(self) -> None:
        got: dict = {}

        class H(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                n = int(self.headers.get("Content-Length", "0"))
                got["body"] = json.loads(self.rfile.read(n))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")

            def log_message(self, *args):
                return

        srv = HTTPServer(("127.0.0.1", 0), H)
        Thread(target=srv.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{srv.server_port}/hook"
        os.environ["ALERT_PAGING_ENABLED"] = "true"
        os.environ["ALERT_WEBHOOK_URL"] = url
        with tempfile.TemporaryDirectory() as td:
            alert_paging.PAGE_LOG = Path(td) / "paging.jsonl"
            rec = alert_paging.page_alert(
                {"type": "paging_drill", "severity": "critical", "detail": "x"}
            )
        srv.shutdown()
        self.assertTrue(rec["ok"])
        self.assertIn("paging_drill", got["body"]["text"])


if __name__ == "__main__":
    raise SystemExit(unittest.main())
