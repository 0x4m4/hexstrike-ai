# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed — Dependency management migrated from `pip` to `uv`

HexStrike AI now uses [**uv**](https://docs.astral.sh/uv/) (the Rust-based Python
package & project manager from Astral) instead of `pip` + `requirements.txt`.

- Replaced `requirements.txt` with [`pyproject.toml`](./pyproject.toml)
  (PEP 621 project metadata) as the single source of truth for dependencies.
- Added a committed [`uv.lock`](./uv.lock) so installs are reproducible across
  machines, operating systems and CI (exact resolved versions pinned).
- Added a `dev` dependency group (`pytest`, `ruff`) under `[dependency-groups]`
  for contributors, installable with `uv sync --group dev`.
- Updated `README.md` so the **Installation**, **Start the Server**,
  **Development Setup** and **Troubleshooting** sections all use the `uv`
  workflow (`uv sync`, `uv run python ...`).
- Added a `.gitignore` covering Python artefacts, virtual environments and
  `uv` caches.

### Why `uv`

- **Speed**: 10–100× faster resolution and install than `pip`, thanks to the
  Rust implementation, parallel downloads and a shared global cache.
- **Reproducibility**: `uv.lock` guarantees the same resolved versions on every
  machine and in CI — no "works on my machine" dependency drift.
- **Single source of truth**: `pyproject.toml` (PEP 621) is the modern Python
  standard, removing the need to keep `requirements.txt` in sync by hand.
- **Built‑in virtualenv management**: `uv` auto‑creates and manages `.venv/`,
  so `python3 -m venv hexstrike-env && source .../activate` is no longer
  required (though `source .venv/bin/activate` still works for those who
  prefer it).
- **Tooling unified**: `uv` handles Python version management, venv creation,
  dependency installation and command execution (`uv run`) in one binary.

### Migration guide (for existing users)

If you previously used the `pip` workflow:

```bash
# 1. Install uv (once)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Remove the old virtual environment (optional but recommended)
rm -rf hexstrike-env

# 3. Sync dependencies — uv creates .venv/ automatically
uv sync

# 4. Run the server
uv run python hexstrike_server.py
```

No source code changes are required. The new flow is a faster, lockfile‑backed
replacement for the previous `pip install -r requirements.txt` step, and all
previously listed runtime dependencies are preserved with their original
version constraints.

### Backwards compatibility

- Same Python version range (≥ 3.10).
- All previously listed runtime dependencies are kept with identical version
  constraints (`flask`, `requests`, `psutil`, `fastmcp`, `beautifulsoup4`,
  `selenium`, `webdriver-manager`, `aiohttp`, `mitmproxy`, `pwntools`,
  `angr`, `bcrypt==4.0.1`).
- No application source code changes — the migration is tooling-only.

### Verification

- `uv lock` resolves cleanly: **175 packages** resolved.
- `uv sync` installs successfully and `hexstrike_server.py` boots and serves
  a healthy `/health` endpoint.
- README install/run/dev/troubleshooting blocks updated and validated.
