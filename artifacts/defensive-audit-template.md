# Defensive Audit Template — Crypto Ops Infrastructure

Generated: 2026-07-10 08:19 UTC  
Agent: Agent-Report-06  
Purpose: Responsible disclosure / owner hardening (no exploitation steps)

---

## Scope

| Asset | Observed | Notes |
|-------|----------|-------|
| Jenkins | 2.375.3 @ :8080 | Yandex Cloud; 403 unauthenticated |
| Geth JSON-RPC | :8545 | Co-located; RST from external IP (allowlist likely) |
| SSH | :22 | Open; ensure key-only + fail2ban |
| BSC node (OVH) | 51.222.42.220:8545 | Read-only; no `personal_*` |

---

## Jenkins Hardening

- [ ] Upgrade LTS **≥ 2.375.4** (prefer current LTS 2026)
- [ ] Bind `:8080` to VPN / internal IP only (not public Internet)
- [ ] Enforce SSO or strong MFA for admin accounts
- [ ] Disable anonymous read if enabled
- [ ] Audit installed plugins; remove unused
- [ ] Restrict update sites to `https://updates.jenkins.io/` only
- [ ] Set `java.io.tmpdir` to private directory (0700)
- [ ] Enable audit log / access log retention
- [ ] Secrets: migrate to Vault / Jenkins Credentials with folder ACLs
- [ ] No `.env`, keystores, or `credentials.xml` in job workspaces/git

**Known CVEs (2.375.3):** see `artifacts/jenkins-cve-report.json`

---

## Geth / RPC Hardening

- [ ] Never expose `personal_*`, `admin_*`, or unlock APIs
- [ ] Firewall `:8545` to application subnets only
- [ ] Run without wallet keys on node filesystem
- [ ] Use separate signer service (HSM / remote signer)
- [ ] Monitor for unexpected `eth_sendRawTransaction` sources
- [ ] Keep Geth patched; document version in inventory

---

## Key & Secret Management

- [ ] Hot wallet keys **not** on CI runners or Jenkins agents
- [ ] Use KMS/HSM with policy-based signing (session keys if AA)
- [ ] Rotate API keys (Binance, RPC providers, cloud) quarterly
- [ ] `proof-key.txt` / seed phrases offline only; never in repos
- [ ] Pre-commit hooks: gitleaks / trufflehog on all pipelines

---

## Network & Cloud (Yandex + OVH)

- [ ] Security groups: default deny inbound
- [ ] Split prod/staging VPCs
- [ ] Enable Cloud audit logs (Yandex Cloud Logging)
- [ ] RDAP/WHOIS ownership documented internally
- [ ] Incident contact on file for responsible disclosure

---

## On-chain Ops (if applicable)

- [ ] Document treasury wallet purpose (payroll vs bridge)
- [ ] Monitor large outflows (Rhino.fi / CEX paths)
- [ ] EIP-7702 delegation review quarterly
- [ ] No unlimited ERC20 approvals from treasury EOAs

---

## Disclosure Workflow

1. Identify entity (see `artifacts/entity-id.json`)
2. Send this checklist + CVE report to security@ or abuse contact
3. Offer 90-day coordinated remediation window
4. Do **not** exploit without written authorization

---

## References

- Jenkins Advisory 2023-03-08: https://www.jenkins.io/security/advisory/2023-03-08/
- OWASP CI/CD Security: https://owasp.org/www-project-top-10-ci-cd-security-risks/
