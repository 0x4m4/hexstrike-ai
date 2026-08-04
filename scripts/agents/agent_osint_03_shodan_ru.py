#!/usr/bin/env python3
"""Agent-OSINT-03: Shodan scan Russia — thin wrapper."""
import os
import sys

os.environ.setdefault("COUNTRY", "RU")
os.environ.setdefault("OUTPUT", os.path.join(os.path.dirname(__file__), "../../artifacts/shodan-ru-report.json"))

from agent_osint_03_shodan_country import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
