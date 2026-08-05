# 🔐 Security Policy

## Reporting a Vulnerability

We take security reports seriously. If you discover a vulnerability in this project, please follow the steps below so we can address it responsibly.

### How to Report

Send your report to:

**Email:** security@hexstrike-ai.example.com  
**PGP key:** (optional) `0xYOURPGPFINGERPRINT`  

Include:

- A clear description of the issue.
- Steps to reproduce (exact code/commands).
- Impact and risk assessment.
- Any suggested mitigation or fix.

Your report will be acknowledged within **72 hours** and we aim to provide a resolution timeline shortly thereafter.

### What Not to Do

- Do not publicly disclose the vulnerability before it’s fixed.
- Do not exploit the vulnerability on systems you do not own or have permission to test.

---

## Supported Versions

We provide security fixes for the following branches:

| Version | Supported        |
|---------|------------------|
| `main`  | Yes              |
| `vX.Y`  | Yes (security only) |
| Older   | No               |

If your version is not listed, please upgrade.

---

## Security Response Process

Once a report is received:

1. We verify the issue and assign a severity level.
2. We may request more information from the reporter.
3. A fix is developed and merged into the supported branches.
4. A public advisory or GitHub Security Advisory is published.
5. Users are notified via repository release notes.

---

## Disclosure Policy

After a fix is released:

- We plan to publicly disclose the issue via the repository **Security Advisory** or release notes.
- If the reporting researcher wishes to remain anonymous, that will be respected.

---

## Security Tools & Practices

This project recommends but does *not enforce*:

- Enabling Dependabot alerts for dependency vulnerabilities.
- Using secret scanning and push protection in GitHub.
- Running code scanning (e.g., CodeQL) as part of CI.:contentReference[oaicite:1]{index=1}

---

## Acknowledgements

We thank all security researchers and contributors who help improve the trustworthiness of this project.

