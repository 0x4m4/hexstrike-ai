# Issue #001 — `/api/visual/*` routes call methods on the wrong class (500 errors)

- **Severity:** High (endpoints completely broken)
- **Component:** `hexstrike_server.py` — visual reporting API
- **Affected endpoints:** `POST /api/visual/vulnerability-card`, `POST /api/visual/summary-report`, `POST /api/visual/tool-output`
- **Status:** Fixed in this repo (see patch below)

## Summary

All three `/api/visual/*` routes raise `AttributeError` / `TypeError` on every call and
return `HTTP 500 {"error": "Server error: ..."}`. They reference methods on the
`ModernVisualEngine` class, but those methods are actually defined as `@staticmethod`s
on a **different** class — `CVEIntelligenceManager` (defined around line 5750).

`ModernVisualEngine` (class at line 105) has a similarly-named but **different** method,
`format_vulnerability_card` (note: `format_` not `render_`), which is not what these routes
intend to call.

## Reproduction

```bash
curl -s -X POST http://localhost:8888/api/visual/vulnerability-card \
  -H "Content-Type: application/json" \
  -d '{"title":"test","severity":"CRITICAL","description":"x"}'
# Before fix: {"error":"Server error: type object 'ModernVisualEngine' has no attribute 'render_vulnerability_card'"}
```

Backend log:
```
ERROR 💥 Error creating vulnerability card: type object 'ModernVisualEngine' has no attribute 'render_vulnerability_card'
ERROR 💥 Error creating summary report: 'ModernVisualEngine' object has no attribute 'create_summary_report'
ERROR 💥 Error formatting tool output: type object 'ModernVisualEngine' has no attribute 'format_tool_output'
```

## Root cause

| Route line | Code (before) | Actual method location |
|------------|---------------|------------------------|
| ~9476 | `ModernVisualEngine.render_vulnerability_card(data)` | `CVEIntelligenceManager.render_vulnerability_card` (~5810, `@staticmethod`) |
| ~9498 | `visual_engine = ModernVisualEngine()` then `visual_engine.create_summary_report(data)` | `CVEIntelligenceManager.create_summary_report` (~5929, `@staticmethod`) |
| ~9523 | `ModernVisualEngine.format_tool_output(tool, output, success)` | `CVEIntelligenceManager.format_tool_output` (~5890, `@staticmethod`) |

The methods exist; they were just attached to the wrong class in the route handlers
(likely a refactor where the CVE-intelligence visual helpers were moved into
`CVEIntelligenceManager` but the route call sites were not updated).

## Fix

In `hexstrike_server.py`, change the three call sites to reference `CVEIntelligenceManager`
(and drop the unnecessary `ModernVisualEngine()` instantiation in the summary-report route,
since the method is a `@staticmethod`):

```diff
-        # Create vulnerability card
-        card = ModernVisualEngine.render_vulnerability_card(data)
+        # Create vulnerability card (render_vulnerability_card is a staticmethod
+        # on CVEIntelligenceManager, not ModernVisualEngine)
+        card = CVEIntelligenceManager.render_vulnerability_card(data)
```

```diff
-        # Create summary report
-        visual_engine = ModernVisualEngine()
-        report = visual_engine.create_summary_report(data)
+        # Create summary report (create_summary_report is a staticmethod on
+        # CVEIntelligenceManager, not ModernVisualEngine)
+        report = CVEIntelligenceManager.create_summary_report(data)
```

```diff
-        # Format tool output
-        formatted_output = ModernVisualEngine.format_tool_output(tool, output, success)
+        # Format tool output (format_tool_output is a staticmethod on
+        # CVEIntelligenceManager, not ModernVisualEngine)
+        formatted_output = CVEIntelligenceManager.format_tool_output(tool, output, success)
```

## Verification

After applying the fix and restarting the service, all three endpoints return
`{"success": true, ...}` with the rendered ANSI card/report body.

## Impact

These endpoints are advertised by HexStrike as the primary way to produce visual
vulnerability cards and summary reports. Any MCP client / script calling them gets
a hard 500. The MCP `create_vulnerability_report`, `format_tool_output_visual`, and
`create_scan_summary` tools (which the MCP layer maps to these routes) are consequently
unusable.
