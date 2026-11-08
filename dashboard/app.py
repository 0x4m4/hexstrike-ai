#!/usr/bin/env python3
"""
HexStrike AI Command Center
----------------------------
A small local Flask dashboard that sits in front of the HexStrike AI
server (http://127.0.0.1:8888) and lets you browse all 151 tools, fill in
a generated form, run them, and see live output/process status - no MCP
client required.

Run:
    venv/bin/python dashboard/app.py
Then open http://127.0.0.1:9000
"""
import json
import logging
from pathlib import Path

import requests
from flask import Flask, jsonify, render_template, request

HEXSTRIKE_SERVER = "http://127.0.0.1:8888"
MANIFEST_PATH = Path(__file__).resolve().parent / "tools_manifest.json"
DASHBOARD_PORT = 9000

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hexstrike-dashboard")

app = Flask(__name__)

_manifest_cache = None


def load_manifest():
    global _manifest_cache
    if _manifest_cache is None:
        with open(MANIFEST_PATH) as f:
            _manifest_cache = json.load(f)
    return _manifest_cache


def find_tool(name):
    for t in load_manifest():
        if t["name"] == name:
            return t
    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/manifest")
def api_manifest():
    tools = load_manifest()
    categories = {}
    for t in tools:
        categories.setdefault(t["category"], []).append(t)
    return jsonify({"tools": tools, "categories": categories, "total": len(tools)})


@app.route("/api/health")
def api_health():
    try:
        r = requests.get(f"{HEXSTRIKE_SERVER}/health", timeout=5)
        return jsonify({"reachable": True, "status_code": r.status_code, "data": r.json()})
    except Exception as e:
        return jsonify({"reachable": False, "error": str(e)}), 200


@app.route("/api/processes")
def api_processes():
    try:
        r = requests.get(f"{HEXSTRIKE_SERVER}/api/processes/dashboard", timeout=5)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 200


@app.route("/api/run", methods=["POST"])
def api_run():
    body = request.get_json(force=True) or {}
    tool_name = body.get("tool")
    params = body.get("params", {})

    tool = find_tool(tool_name)
    if not tool:
        return jsonify({"success": False, "error": f"Unknown tool: {tool_name}"}), 404
    if tool["composite"] or not tool["route"]:
        return jsonify({
            "success": False,
            "error": f"'{tool_name}' is a composite workflow with no single server route; "
                     f"not supported for direct execution from this dashboard."
        }), 400

    route = tool["route"]
    for pp in tool.get("path_params", []):
        if pp not in params:
            return jsonify({"success": False, "error": f"Missing required path param: {pp}"}), 400
        route = route.replace("{" + pp + "}", str(params.pop(pp)))

    url = f"{HEXSTRIKE_SERVER}/{route}"
    logger.info("Running tool=%s -> %s %s params=%s", tool_name, tool["method"], url, params)

    try:
        if tool["method"] == "GET":
            r = requests.get(url, params=params, timeout=310)
        else:
            r = requests.post(url, json=params, timeout=310)
        try:
            data = r.json()
        except ValueError:
            data = {"raw": r.text}
        return jsonify({"success": True, "status_code": r.status_code, "result": data})
    except requests.exceptions.Timeout:
        return jsonify({"success": False, "error": "Request timed out (300s)"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200


@app.route("/api/process/<action>/<int:pid>", methods=["POST"])
def api_process_action(action, pid):
    route_map = {
        "terminate": "api/processes/terminate",
        "pause": "api/processes/pause",
        "resume": "api/processes/resume",
    }
    if action not in route_map:
        return jsonify({"success": False, "error": "Unknown action"}), 400
    try:
        r = requests.post(f"{HEXSTRIKE_SERVER}/{route_map[action]}/{pid}", json={}, timeout=10)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200


if __name__ == "__main__":
    logger.info("HexStrike Command Center starting on http://127.0.0.1:%d", DASHBOARD_PORT)
    logger.info("Proxying tool calls to HexStrike server at %s", HEXSTRIKE_SERVER)
    app.run(host="127.0.0.1", port=DASHBOARD_PORT, debug=False)
