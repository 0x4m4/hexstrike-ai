# Issue #002 — `/api/command` cannot find tools in `/usr/sbin` / `/usr/local/sbin` under minimal-PATH launchers

- **Severity:** High (core `/api/command` tool silently fails for many security tools)
- **Component:** `hexstrike_server.py` — `EnhancedCommandExecutor.execute()` / `execute_command()`
- **Affected:** every tool installed under `/usr/sbin` or `/usr/local/sbin` (e.g. the entire `aircrack-ng` suite: `airmon-ng`, `airodump-ng`, `aireplay-ng`; also `tcpdump`, `nmap` on some distros, `tshark`/`dumpcap` setuid, etc.)
- **Status:** Fixed in this repo (see patch below)

## Summary

`/api/command` executes commands with `subprocess.Popen(command, shell=True, ...)` and
**inherits the parent process's `PATH` verbatim** (no `env=` argument). When the server is
launched by a service manager that sets a minimal `PATH` (e.g. a systemd unit with only
`/usr/bin:/bin`), any tool installed in `/usr/sbin` or `/usr/local/sbin` fails with
`command not found`, **even though `/health` reports the tool as `available`**.

This creates a silent inconsistency: `GET /health` → `tools_status: {"aircrack-ng": true, ...}`
(advertising the tool as usable), while `POST /api/command` → `airmon-ng: command not found`.

## Reproduction

Launch the server under a minimal-PATH environment (this is exactly how a typical
systemd user unit is configured):

```ini
# hexstrike-api.service
[Service]
Environment=PATH=/usr/bin:/bin
ExecStart=/usr/bin/python3 /home/user/Projects/hexstrike-ai/hexstrike_server.py
```

Then:

```bash
curl -s -X POST http://localhost:8888/api/health | jq '.tools_status.aircrack_ng'   # true
curl -s -X POST http://localhost:8888/api/command \
  -H "Content-Type: application/json" \
  -d '{"command":"airmon-ng start wlan1"}'
# Before fix: {"success": false, "stderr": "sh: 1: airmon-ng: not found", ...}
```

Working workaround (proves the cause): use the absolute path:
```bash
-d '{"command":"/usr/sbin/airmon-ng start wlan1"}'   # works
```

## Root cause

`EnhancedCommandExecutor.execute()` (~line 6876):

```python
self.process = subprocess.Popen(
    self.command,
    shell=True,            # /bin/sh -c "<command>"  -> PATH lookup
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
    # NOTE: no env= argument -> inherits parent PATH as-is
)
```

The health-check code resolves tools with `shutil.which()` / absolute-path probing that
does not depend on `PATH`, so it reports them as available; but the actual execution path
depends on `PATH` and breaks under minimal-PATH launchers.

This was observed in the field: the HexStrike systemd user unit (`hexstrike-api.service`)
shipped with `Environment=PATH=/usr/bin:/bin:/usr/local/bin:/usr/local/sbin:/home/user/.local/bin`
— `/usr/sbin` was missing, so the entire aircrack-ng suite (which the MCP server advertises
as 150 wireless/pentest tools) was unreachable through `/api/command`.

## Fix

Augment `PATH` at module import so common security-tool directories are always present,
regardless of how the server is launched. Added near the API configuration block at the
top of `hexstrike_server.py`:

```python
# Ensure common security-tool locations are on PATH so commands executed via
# /api/command resolve regardless of how the server was launched (e.g. under a
# systemd unit with a minimal PATH). Many tools (aircrack-ng suite, nmap,
# tcpdump, ...) live in /usr/sbin or /usr/local/sbin.
for _sbin in ("/usr/sbin", "/usr/local/sbin", "/sbin", "/usr/local/bin"):
    if _sbin not in os.environ.get("PATH", "").split(":"):
        os.environ["PATH"] = os.environ.get("PATH", "") + ":" + _sbin
```

This is the minimal, least-invasive fix (a single import-time augmentation).
A more defensive alternative would be to pass an explicit `env=` to `subprocess.Popen`
that includes these directories — but the import-time fix also benefits any other
subprocess calls in the codebase that rely on `PATH` lookup.

## Verification

After the fix and a service restart, inside the backend:

```bash
curl -s -X POST http://localhost:8888/api/command \
  -H "Content-Type: application/json" -d '{"command":"which airodump-ng airmon-ng aircrack-ng"}'
# /usr/sbin/airodump-ng
# /usr/sbin/airmon-ng
# /usr/bin/aircrack-ng
```

## Related (not fixed here)

The deeper consistency issue — `/health` advertising tools as available that `/api/command`
then cannot run — is worth a follow-up: `tools_status` should reflect executability under the
*same* `PATH` that `execute_command` uses. Out of scope for this patch.

## Recommendation for service-unit authors

Even with this fix, systemd unit files for `hexstrike-api.service` should include `sbin`
directories explicitly:

```ini
Environment=PATH=/usr/bin:/bin:/usr/sbin:/usr/local/sbin:/usr/local/bin
```
