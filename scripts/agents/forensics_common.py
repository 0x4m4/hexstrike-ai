#!/usr/bin/env python3
"""Deep static extraction helpers for malware/contract forensics agents."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
DESKTOP_MIRROR = Path.home() / "Desktop" / "on-chain-forensics" / "artifacts"

ETH_ADDR = re.compile(r"0x[a-fA-F0-9]{40}")
SOL_ADDR = re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b")
URL = re.compile(r"https?://[^\s\"'<>]+")
HOST = re.compile(r"(?:https?://)?([a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,})")
TELEGRAM = re.compile(r"(?:t\.me/|telegram\.me/)([A-Za-z0-9_]{3,})", re.I)
DISCORD = re.compile(r"discord(?:app)?\.com/api/webhooks/\d+/[\w-]+")
GITHUB = re.compile(r"github\.com/([A-Za-z0-9_.-]+/[\w.-]+)")
WALLET_CONNECT = re.compile(r"walletconnect|WalletConnect|@walletconnect", re.I)
PERMIT_SELECTOR = re.compile(r"0xd505accf|signTypedData|Permit2|permit\(", re.I)
CREATE2 = re.compile(r"create2|CREATE2|0xf5|EIP-1167|minimal[_ ]proxy|cloneDeterministic", re.I)
ENV_SECRET = re.compile(r"(?:PRIVATE_KEY|SECRET|PRIVATEKEY|MNEMONIC|API_KEY)\s*[=:]\s*['\"]?[\w.-]+", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def output_path(name: str) -> Path:
    env = os.environ.get("OUTPUT")
    if env:
        p = Path(env)
        return p if p.is_absolute() else ROOT / p
    return ARTIFACTS / name


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    try:
        DESKTOP_MIRROR.mkdir(parents=True, exist_ok=True)
        (DESKTOP_MIRROR / path.name).write_text(text, encoding="utf-8")
    except OSError:
        pass


def repo_path(env_key: str, default_rel: str) -> Path:
    return Path(os.environ.get(env_key, str(ROOT / default_rel)))


def load_intel(name: str) -> dict[str, Any]:
    for base in (ARTIFACTS / "recon", ROOT / "docs" / "recon"):
        path = base / name
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return {}


def emit(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("success", True) else 1


def scan_tree(
    root: Path,
    *,
    max_files: int | None = None,
    patterns: dict[str, re.Pattern[str]] | None = None,
) -> dict[str, Any]:
    """Full recursive static scan — no artificial cap unless FORENSICS_MAX_FILES is set."""
    cap = max_files
    if cap is None:
        cap = int(os.environ.get("FORENSICS_MAX_FILES", "0")) or None

    if not root.is_dir():
        return {
            "root": str(root),
            "exists": False,
            "files_analyzed": 0,
            "addresses": [],
            "solana_addresses": [],
            "hosts": [],
            "urls": [],
            "telegram_handles": [],
            "discord_webhooks": [],
            "github_repos": [],
            "flagged_files": {},
            "loader_paths": [],
        }

    addresses: set[str] = set()
    sol_addresses: set[str] = set()
    hosts: set[str] = set()
    urls: set[str] = set()
    telegram: set[str] = set()
    discord: set[str] = set()
    github: set[str] = set()
    flagged: dict[str, list[str]] = {}
    loader_paths: list[str] = []
    files_analyzed = 0

    exts = {
        ".js", ".ts", ".tsx", ".jsx", ".py", ".go", ".sol", ".json", ".env",
        ".md", ".html", ".sh", ".rs", ".cpp", ".c", ".h", ".yaml", ".yml",
        ".toml", ".xml", ".php", ".rb", ".java", ".cs", ".exe", ".dll",
    }
    skip_dirs = {".git", "node_modules", "dist", "build", ".next", "__pycache__", "vendor"}

    pats = patterns or {
        "walletconnect": WALLET_CONNECT,
        "permit": PERMIT_SELECTOR,
        "create2": CREATE2,
        "env_secret": ENV_SECRET,
    }

    for path in root.rglob("*"):
        if cap and files_analyzed >= cap:
            break
        if not path.is_file():
            continue
        if path.suffix.lower() not in exts and path.suffix.lower() not in {".exe", ".dll"}:
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        files_analyzed += 1
        rel = str(path.relative_to(root))

        for m in ETH_ADDR.findall(text):
            addresses.add(m.lower())
        for m in SOL_ADDR.findall(text):
            if 32 <= len(m) <= 44:
                sol_addresses.add(m)
        for m in URL.findall(text):
            urls.add(m.rstrip(".,;)"))
            try:
                host = urlparse(m).netloc.lower()
                if host:
                    hosts.add(host)
            except Exception:
                pass
        for m in HOST.findall(text):
            if "." in m and not m.endswith(".local"):
                hosts.add(m.lower())
        for m in TELEGRAM.findall(text):
            telegram.add(m)
        for m in DISCORD.findall(text):
            discord.add(m)
        for m in GITHUB.findall(text):
            github.add(m.lower())

        hits = [k for k, rx in pats.items() if rx.search(text)]
        if hits:
            flagged[rel] = hits
        low = rel.lower()
        if any(x in low for x in ("loader", "inject", "dropper", "build", "dist", "release")):
            loader_paths.append(rel)

    c2_candidates = sorted(
        h for h in hosts
        if any(x in h for x in ("api.", "proxy", "hook", "c2", "panel", "bot."))
    )

    return {
        "root": str(root),
        "exists": True,
        "files_analyzed": files_analyzed,
        "addresses": sorted(addresses),
        "solana_addresses": sorted(sol_addresses),
        "hosts": sorted(hosts),
        "urls": sorted(urls)[:200],
        "telegram_handles": sorted(telegram),
        "discord_webhooks": sorted(discord),
        "github_repos": sorted(github),
        "c2_candidates": c2_candidates,
        "flagged_files": flagged,
        "loader_paths": loader_paths[:50],
        "walletconnect_detected": any("walletconnect" in v for v in flagged.values()),
        "permit_detected": any("permit" in v for v in flagged.values()),
        "create2_detected": any("create2" in v for v in flagged.values()),
    }


def build_attack_chain(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"step": i + 1, **s} for i, s in enumerate(steps)]


def merge_scans(*scans: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "files_analyzed": 0,
        "addresses": set(),
        "solana_addresses": set(),
        "hosts": set(),
        "urls": set(),
        "telegram_handles": set(),
        "github_repos": set(),
        "flagged_files": {},
        "roots": [],
    }
    for s in scans:
        if not s.get("exists"):
            continue
        out["roots"].append(s.get("root"))
        out["files_analyzed"] += s.get("files_analyzed", 0)
        for k in ("addresses", "solana_addresses", "hosts", "urls", "telegram_handles", "github_repos"):
            out[k].update(s.get(k, []))
        out["flagged_files"].update(s.get("flagged_files", {}))
    return {
        "roots": out["roots"],
        "files_analyzed": out["files_analyzed"],
        "addresses": sorted(out["addresses"]),
        "solana_addresses": sorted(out["solana_addresses"]),
        "hosts": sorted(out["hosts"]),
        "urls": sorted(out["urls"])[:200],
        "telegram_handles": sorted(out["telegram_handles"]),
        "github_repos": sorted(out["github_repos"]),
        "flagged_files": out["flagged_files"],
    }
