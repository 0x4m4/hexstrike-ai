# BrowserPod Security GUI for HexStrike AI

An in-browser, gated front-end for the HexStrike API. Zero install: serve this
page, boot a WASM Node.js sandbox in the tab, and drive the 150+ HexStrike
tools through an explicit propose → confirm gate.

## Why

HexStrike v6.0 exposes every tool as a plain HTTP POST. Any script, agent, or
drift-click can fire `nmap`/`sqlmap`/`hydra` against a target with no
second thought. This GUI keeps the power but inserts the missing human step:

1. **Propose** — pick a tool on the left, fill parameters, hit propose. Nothing executes.
2. **Confirm** — the pending proposal appears in the right panel. A human
   clicks *confirm & run* (or *cancel*). Only then does the request proxy to
   HexStrike.
3. **Sandbox** — the tab boots a real BrowserPod (WebAssembly) Node.js runtime,
   so tooling that runs inside the pod never touches your host.

## Run

```bash
# terminal 1 — the HexStrike API (v6.0)
python3 hexstrike_server.py --port 8888

# terminal 2 — this GUI (stdlib only, no pip install)
python3 browserpod/browserpod_gui.py --port 8000

# open
xdg-open http://127.0.0.1:8000/
```

## Layout

```
browserpod/
  browserpod_gui.py   # stdlib HTTP server: GUI + proxy + gate
  web/index.html      # the single-page GUI (BrowserPod terminal + palette)
```

## Security model

- `GATED_TOOLS` in `browserpod_gui.py` is the allow-list. A tool not listed is
  refused before anything happens.
- Proposals are single-use tokens held in memory; confirm/cancel pops them.
- The GUI proxies only `/api/*` — the HexStrike server itself stays
  unexposed.
- BrowserPod boots sandboxed; if no API key is present it boots with the
  public runtime.

MIT — contributed to HexStrike AI.
