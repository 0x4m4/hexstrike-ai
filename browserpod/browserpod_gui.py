#!/usr/bin/env python3
"""browserpod_gui.py — BrowserPod security GUI server for HexStrike AI.

Runs a zero-dependency (stdlib-only) HTTP server that:

  * serves the BrowserPod security GUI at /
  * proxies /api/* to the HexStrike API server (hexstrike_server.py)
  * gates every security tool behind propose -> confirm (nothing executes
    until a human confirms the pending token)

Usage:
    python3 hexstrike_server.py --port 8888          # HexStrike API
    python3 browserpod_gui.py --port 8000            # this GUI (default)

Then open http://127.0.0.1:8000/ in any browser.

Requirements: Python 3.8+, BrowserPod runtime loaded from rt.browserpod.io.
No pip install needed for the GUI itself.

MIT License — contributed to HexStrike AI.
"""
import argparse
import json
import os
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HEXSTRIKE_URL = os.environ.get("HEXSTRIKE_URL", "http://127.0.0.1:8888")

GATED_TOOLS = {
    "nmap": ("/api/tools/nmap", "network scan"),
    "nuclei": ("/api/tools/nuclei", "vulnerability scan"),
    "gobuster": ("/api/tools/gobuster", "directory brute force"),
    "sqlmap": ("/api/tools/sqlmap", "sql injection testing"),
    "nikto": ("/api/tools/nikto", "web server scan"),
    "hydra": ("/api/tools/hydra", "password attack"),
    "metasploit": ("/api/tools/metasploit", "exploitation"),
    "nmap_intelligent": ("/api/intelligence/smart-scan", "intelligent recon"),
    "recon_workflow": ("/api/bugbounty/reconnaissance-workflow", "recon workflow"),
}

_pending = {}


class Handler(BaseHTTPRequestHandler):
    service_name = "hexstrike-browserpod"

    def log_message(self, fmt, *args):
        print(f"[browserpod-gui] {fmt % args}")

    def _send(self, body, status=200, ctype="application/json"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, status=200):
        self._send(json.dumps(data, indent=2, default=str), status)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not length:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def _hx(self, method, path, body=None):
        req = urllib.request.Request(HEXSTRIKE_URL + path, method=method)
        if body is not None:
            req.data = json.dumps(body).encode()
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                raw = r.read().decode()
                try:
                    return {"ok": True, "status": r.status, "result": json.loads(raw)}
                except Exception:
                    return {"ok": True, "status": r.status, "result": raw}
        except urllib.error.HTTPError as e:
            return {"ok": False, "status": e.code, "error": e.read().decode()[:800]}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            gui = Path(__file__).resolve().parent / "web" / "index.html"
            if gui.exists():
                self._send(gui.read_text(), 200, "text/html; charset=utf-8")
            else:
                self._json({"ok": False, "error": "GUI missing"})
            return

        if path == "/health":
            hx = self._hx("GET", "/health")
            return self._json({
                "ok": True,
                "service": "browserpod-gui",
                "hexstrike": bool(hx.get("ok") or hx.get("result")),
            })

        if path == "/api/tools":
            return self._json({
                "ok": True,
                "gated": sorted(GATED_TOOLS),
                "pending": [
                    {"token": t, "tool": r["tool"], "describe": r.get("describe", ""),
                     "params": r.get("params", {})}
                    for t, r in _pending.items()
                ],
            })

        if path.startswith("/api/hx/"):
            target = path[len("/api/hx"):]
            if parsed.query:
                target += "?" + parsed.query
            return self._json(self._hx("GET", target))

        self._json({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        body = self._read_json()

        if parsed.path == "/api/run":
            tool = body.get("tool", "")
            params = body.get("params", {})
            if tool not in GATED_TOOLS:
                return self._json({"ok": False, "error": f"tool '{tool}' not gated"})
            endpoint, describe = GATED_TOOLS[tool]
            run_token = uuid.uuid4().hex[:12]
            _pending[run_token] = {"tool": tool, "endpoint": endpoint, "params": params,
                                   "describe": describe}
            return self._json({
                "ok": True, "proposal": True,
                "token": run_token, "tool": tool, "describe": describe,
                "params": params,
                "note": "confirm with POST /api/run/confirm — nothing executed",
            })

        if parsed.path == "/api/run/confirm":
            run_token = body.get("token", "")
            rec = _pending.pop(run_token, None)
            if not rec:
                return self._json({"ok": False, "error": "unknown or expired token"})
            res = self._hx("POST", rec["endpoint"], rec["params"])
            return self._json({"ok": res.get("ok", False), "result": res, "tool": rec["tool"]})

        if parsed.path == "/api/run/cancel":
            run_token = body.get("token", "")
            _pending.pop(run_token, None)
            return self._json({"ok": True, "cancelled": bool(run_token)})

        if parsed.path.startswith("/api/hx/"):
            target = parsed.path[len("/api/hx"):]
            return self._json(self._hx("POST", target, body))

        self._json({"ok": False, "error": "not found"}, 404)


def main():
    global HEXSTRIKE_URL
    ap = argparse.ArgumentParser(description="BrowserPod GUI for HexStrike AI")
    ap.add_argument("--port", type=int, default=8000,
                    help="GUI port (default 8000)")
    ap.add_argument("--hexstrike-url", default=HEXSTRIKE_URL,
                    help="HexStrike API base URL (default %(default)s)")
    args = ap.parse_args()
    HEXSTRIKE_URL = args.hexstrike_url

    ThreadingHTTPServer.allow_reuse_address = True
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"[browserpod-gui] GUI on http://127.0.0.1:{args.port}/")
    print(f"[browserpod-gui] proxying HexStrike API at {HEXSTRIKE_URL}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
