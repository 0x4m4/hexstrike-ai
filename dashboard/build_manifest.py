#!/usr/bin/env python3
"""
Builds tools_manifest.json by statically parsing ../hexstrike_mcp.py.

For every @mcp.tool() function we record its name, category (nearest
preceding ALL-CAPS comment header), parameters (name/type/default/required),
short description, and the HexStrike server API route + HTTP method it
forwards to. A handful of composite "AI workflow" tools don't forward to a
single route (they call several other tools internally) - those are kept in
the manifest with route=null and flagged "composite" so the dashboard can
grey out the Run button and explain why.
"""
import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tool_enrichment

SRC_PATH = Path(__file__).resolve().parent.parent / "hexstrike_mcp.py"

# Tools whose route can't be found by a simple literal-string regex because
# they build the path with an f-string path parameter, or call a differently
# named client method. Mapped by hand after inspecting the source.
MANUAL_ROUTES = {
    "server_health": {"route": "health", "method": "GET", "path_params": []},
    "get_process_status": {"route": "api/processes/status/{pid}", "method": "GET", "path_params": ["pid"]},
    "terminate_process": {"route": "api/processes/terminate/{pid}", "method": "POST", "path_params": ["pid"]},
    "pause_process": {"route": "api/processes/pause/{pid}", "method": "POST", "path_params": ["pid"]},
    "resume_process": {"route": "api/processes/resume/{pid}", "method": "POST", "path_params": ["pid"]},
    "execute_command": {"route": "api/command", "method": "POST", "path_params": []},
}
# Composite tools: pure client-side orchestration in hexstrike_mcp.py, no
# single server route to forward to.
COMPOSITE_TOOLS = {
    "ai_generate_attack_suite",
    "comprehensive_api_audit",
    "threat_hunting_assistant",
    "bugbounty_authentication_bypass_testing",
}


def is_mcp_tool_decorator(d):
    if isinstance(d, ast.Call):
        f = d.func
        if isinstance(f, ast.Attribute) and f.attr == "tool":
            if isinstance(f.value, ast.Name) and f.value.id == "mcp":
                return True
    return False


def default_repr(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def build_category_map(lines):
    category_by_line = {}
    last_header = "General"
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        bare = stripped.strip("#").strip()
        if stripped.startswith("#") and len(bare) > 5 and bare.isupper() and "=" not in stripped:
            last_header = bare.title()
        category_by_line[i] = last_header
    return category_by_line


def main():
    src = SRC_PATH.read_text()
    tree = ast.parse(src)
    lines = src.splitlines()
    category_by_line = build_category_map(lines)

    tools = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if not any(is_mcp_tool_decorator(d) for d in node.decorator_list):
            continue

        args = node.args
        all_args = args.args
        defaults = args.defaults
        n_no_default = len(all_args) - len(defaults)
        params = []
        for idx, a in enumerate(all_args):
            ann = ast.unparse(a.annotation) if a.annotation else "str"
            dflt = default_repr(defaults[idx - n_no_default]) if idx >= n_no_default else None
            required = idx < n_no_default
            params.append({"name": a.arg, "type": ann, "default": dflt, "required": required})

        body_src = ast.get_source_segment(src, node) or ""
        route, method, path_params = None, "POST", []
        if node.name in MANUAL_ROUTES:
            m = MANUAL_ROUTES[node.name]
            route, method, path_params = m["route"], m["method"], m["path_params"]
        else:
            m = re.search(r'["\'](api/[a-zA-Z0-9_\-/]+)["\']', body_src)
            if m:
                route = m.group(1)
                method = "POST" if "safe_post" in body_src else ("GET" if "safe_get" in body_src else "POST")

        composite = node.name in COMPOSITE_TOOLS or route is None

        doc = ast.get_docstring(node) or ""
        doc_first = doc.strip().split("\n")[0] if doc else ""
        category = category_by_line.get(node.lineno, "General")

        tools.append({
            "name": node.name,
            "category": category,
            "doc": doc_first,
            "params": params,
            "route": route,
            "method": method,
            "path_params": path_params,
            "composite": composite,
            "_docstring": doc,  # consumed by tool_enrichment.enrich(), stripped below
        })

    tools.sort(key=lambda t: (t["category"], t["name"]))

    docstring_by_name = {t["name"]: t.pop("_docstring") for t in tools}
    tool_enrichment.enrich(tools, docstring_by_name)
    out_path = Path(__file__).resolve().parent / "tools_manifest.json"
    out_path.write_text(json.dumps(tools, indent=2))
    print(f"Wrote {len(tools)} tools to {out_path}")
    composite_ct = sum(1 for t in tools if t["composite"])
    print(f"{composite_ct} composite/no-route tools: "
          + ", ".join(t["name"] for t in tools if t["composite"]))


if __name__ == "__main__":
    main()
