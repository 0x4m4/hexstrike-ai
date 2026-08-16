import sys
import types
import unittest


def _stub_unused_mitmproxy_imports():
    """Keep this endpoint test independent of the optional proxy runtime."""
    if "mitmproxy" in sys.modules:
        return

    mitmproxy = types.ModuleType("mitmproxy")
    mitmproxy.__path__ = []
    mitmproxy.http = types.ModuleType("mitmproxy.http")

    tools = types.ModuleType("mitmproxy.tools")
    tools.__path__ = []
    dump = types.ModuleType("mitmproxy.tools.dump")
    dump.DumpMaster = type("DumpMaster", (), {})

    options = types.ModuleType("mitmproxy.options")
    options.Options = type("Options", (), {})

    sys.modules.update(
        {
            "mitmproxy": mitmproxy,
            "mitmproxy.http": mitmproxy.http,
            "mitmproxy.tools": tools,
            "mitmproxy.tools.dump": dump,
            "mitmproxy.options": options,
        }
    )


_stub_unused_mitmproxy_imports()

from hexstrike_server import app  # noqa: E402


class VisualSummaryReportTest(unittest.TestCase):
    def test_summary_report_returns_rendered_scan_counts(self):
        response = app.test_client().post(
            "/api/visual/summary-report",
            json={
                "target": "127.0.0.1",
                "execution_time": 1.25,
                "tools_used": ["nmap"],
                "vulnerabilities": [
                    {"severity": "critical"},
                    {"severity": "high"},
                    {"severity": "medium"},
                ],
            },
        )

        self.assertEqual(response.status_code, 200, response.get_json())
        payload = response.get_json()
        self.assertIs(payload["success"], True)
        self.assertIn("127.0.0.1", payload["summary_report"])
        self.assertIn("3 vulnerabilities", payload["summary_report"])


if __name__ == "__main__":
    unittest.main()
