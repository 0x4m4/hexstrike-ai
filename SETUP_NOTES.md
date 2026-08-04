# HexStrike AI — Local Setup & Run Notes

Environment configuration and verified workflow for this machine (macOS).

## Environment

- Repo: `/Users/sudhagars/hexstrike-ai`
- Python venv: `hexstrike-env` (Python 3.12)
  - Python 3.14 was avoided because `unicorn` (pulled in by `angr`/`pwntools`) fails to build.
- Runtime dependencies installed from: `requirements.runtime.txt`
  - This is `requirements.txt` minus `pwntools`, `angr`, `bcrypt`, which require `unicorn`/CMake builds that do not complete in this setup. Core server + MCP + web/recon functionality is unaffected.
- Extra: `httpx[cli]` installed in the venv (HexStrike's `httpx` tool calls the Python HTTPX CLI).

## Install (reproduce)

```bash
cd /Users/sudhagars/hexstrike-ai
python3.12 -m venv hexstrike-env
./hexstrike-env/bin/python -m pip install --upgrade pip setuptools wheel
./hexstrike-env/bin/python -m pip install -r requirements.runtime.txt
```

## External security tools (installed via Homebrew)

Installed / verified available:
`nmap`, `gobuster`, `ffuf`, `nikto`, `sqlmap`, `hydra`, `john`, `hashcat`,
`masscan`, `rustscan`, `amass`, `subfinder`, `nuclei`, `feroxbuster`, `dalfox`

Health snapshot after install: `total_tools_available = 24`, essential `7/8`.

### Not available via Homebrew formula (optional follow-ups)
- `dirb` — no brew formula (essential gap).
- `wpscan` — RubyGem requires Ruby >= 3.2 (system Ruby is 2.6).
- `dirsearch`, `arjun` — install via `pip` if needed.
- `wfuzz`, `wafw00f` — install via `pip`/source if needed.

## Run the server

```bash
cd /Users/sudhagars/hexstrike-ai
./hexstrike-env/bin/python hexstrike_server.py
# health check
curl http://127.0.0.1:8888/health
```

## Verified automated workflow (100% execution success)

Single reliable mapped tool (`nuclei`) selected via the decision engine:

```bash
curl -sS -X POST http://127.0.0.1:8888/api/intelligence/smart-scan \
  -H 'Content-Type: application/json' \
  -d '{"target":"http://127.0.0.1:8000","objective":"stealth","max_tools":1}'
# => execution_summary.success_rate = 100.0
```

## Known caveats for scan profiles

- `nmap-advanced` is selectable for host targets but is NOT in the smart-scan
  execution map, so it is skipped (counts as failed). Avoid relying on it.
- `nmap` expects a host/IP, not an `http://` URL.
- Tools missing on this host (`wpscan`, etc.) will fail a smart-scan run; keep
  `max_tools`/`objective` scoped to installed, mapped tools for clean runs.
