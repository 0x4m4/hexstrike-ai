#!/usr/bin/env python3
"""Agent-Vuln-05: passive CVE correlation (no exploit)."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DEFAULT_OUT = os.path.join(ROOT, "artifacts/jenkins-cve-report.json")

# Jenkins 2.375.3 — confirmed advisory 2023-03-08 (affects <= 2.375.3)
MARCH_2023_CVES = [
    {
        "cve": "CVE-2023-27898",
        "security_id": "SECURITY-3037",
        "severity": "High",
        "title": "Stored XSS in plugin manager (plugin core dependency message)",
        "exploit_prereq": "Attacker-controlled update site or old metadata; auth typically required for admin flows",
        "fix_version_lts": "2.375.4",
        "advisory": "https://www.jenkins.io/security/advisory/2023-03-08/#SECURITY-3037",
    },
    {
        "cve": "CVE-2023-27899",
        "security_id": "SECURITY-2823",
        "severity": "High",
        "title": "Temporary plugin upload file insecure permissions (Linux shared /tmp)",
        "exploit_prereq": "Local filesystem access on controller",
        "fix_version_lts": "2.375.4",
        "advisory": "https://www.jenkins.io/security/advisory/2023-03-08/#SECURITY-2823",
    },
    {
        "cve": "CVE-2023-27900",
        "security_id": "SECURITY-3030",
        "severity": "Medium",
        "title": "DoS via Apache Commons FileUpload (MultipartFormDataParser)",
        "exploit_prereq": "Unauthenticated HTTP multipart endpoints",
        "fix_version_lts": "2.375.4",
        "upstream": "CVE-2023-24998",
        "advisory": "https://www.jenkins.io/security/advisory/2023-03-08/#SECURITY-3030",
    },
    {
        "cve": "CVE-2023-27901",
        "security_id": "SECURITY-3030",
        "severity": "Medium",
        "title": "DoS via Apache Commons FileUpload (StaplerRequest)",
        "exploit_prereq": "Unauthenticated HTTP multipart endpoints",
        "fix_version_lts": "2.375.4",
        "advisory": "https://www.jenkins.io/security/advisory/2023-03-08/#SECURITY-3030",
    },
    {
        "cve": "CVE-2023-27902",
        "security_id": "SECURITY-1807",
        "severity": "Medium",
        "title": "Workspace @tmp directories exposed via directory browser",
        "exploit_prereq": "Item/Workspace permission",
        "fix_version_lts": "2.375.4",
        "advisory": "https://www.jenkins.io/security/advisory/2023-03-08/#SECURITY-1807",
    },
    {
        "cve": "CVE-2023-27903",
        "security_id": "SECURITY-3058",
        "severity": "Low",
        "title": "CLI file parameter temp file insecure permissions",
        "exploit_prereq": "Local filesystem access + CLI build trigger",
        "fix_version_lts": "2.375.4",
        "advisory": "https://www.jenkins.io/security/advisory/2023-03-08/#SECURITY-3058",
    },
    {
        "cve": "CVE-2023-27904",
        "security_id": "SECURITY-2120",
        "severity": "Low",
        "title": "Information disclosure via agent connection error stack traces",
        "exploit_prereq": "Access to agent-related pages",
        "fix_version_lts": "2.375.4",
        "advisory": "https://www.jenkins.io/security/advisory/2023-03-08/#SECURITY-2120",
    },
]


def nvd_search(keyword: str, max_results: int = 5) -> list:
    url = (
        "https://services.nvd.nist.gov/rest/json/cves/2.0?"
        f"keywordSearch={urllib.request.quote(keyword)}&resultsPerPage={max_results}"
    )
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.load(r)
        out = []
        for v in data.get("vulnerabilities", []):
            c = v.get("cve", {})
            out.append({"id": c.get("id"), "published": c.get("published"), "description": (c.get("descriptions") or [{}])[0].get("value", "")[:200]})
        return out
    except Exception as e:
        return [{"error": str(e)}]


def main() -> int:
    out_path = os.environ.get("OUTPUT", DEFAULT_OUT)
    target = os.environ.get("TARGET", "Jenkins 2.375.3")
    observed = {
        "host": "51.250.97.223",
        "port": 8080,
        "fingerprint": {"X-Jenkins": "2.375.3", "X-Hudson": "1.395", "Server": "Jetty(10.0.12)"},
        "http_status_unauthenticated": 403,
    }

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent": "Agent-Vuln-05",
        "task": "passive-cve-check",
        "mode": "read-only_no_exploit",
        "target": target,
        "type": "web-server",
        "sources": [
            "https://www.jenkins.io/security/advisory/2023-03-08/",
            "https://nvd.nist.gov/",
            "https://cve.mitre.org/",
        ],
        "observed_instance": observed,
        "affected_confirmed": True,
        "fix_recommendation": {
            "minimum_lts": "2.375.4",
            "recommended_lts": "2.440.x or current Jenkins LTS (2026)",
            "note": "2.375.3 is ~3 years behind current LTS; additional CVEs likely apply — full upgrade required",
        },
        "cves_march_2023_advisory": MARCH_2023_CVES,
        "nvd_supplemental_keyword_jenkins_lts": nvd_search("Jenkins LTS 2.375"),
        "risk_summary": {
            "unauthenticated_rce_from_core_only": "NOT confirmed by March 2023 advisory alone",
            "primary_risks": [
                "DoS via crafted multipart uploads (CVE-2023-27900/27901)",
                "Stored XSS via malicious update site metadata (CVE-2023-27898) — niche preconditions",
                "Local privilege escalation if attacker already has filesystem access (CVE-2023-27899/27903)",
            ],
            "defensive_priority": "Upgrade Jenkins LTS; restrict 8080 to VPN; disable anonymous access; audit plugins",
        },
        "exploitation_status": "NOT PERFORMED — report for owner disclosure only",
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({"success": True, "output": out_path, "cve_count": len(MARCH_2023_CVES)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
