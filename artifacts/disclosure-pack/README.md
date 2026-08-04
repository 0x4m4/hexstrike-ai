# Responsible Disclosure Pack (Draft)

Generated for **Entity ID pending** — infrastructure correlated at LOW confidence.

## Artifacts

| File | Content |
|------|---------|
| `artifacts/entity-id.json` | Entity resolution (UNIDENTIFIED) |
| `artifacts/multichain-cluster.json` | Blockscan multichain ~$1.12M profile |
| `artifacts/jenkins-cve-report.json` | Jenkins 2.375.3 CVE list (no exploit) |
| `artifacts/defensive-audit-template.md` | Hardening checklist |
| `artifacts/infra-targets.json` | Passive infra map |

## Target wallet (public on-chain)

- Address: `0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA`
- Blockscan: https://blockscan.com/address/0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA
- Net worth (public UI): ~$1,122,486 — BASE USDC + BSC BSC-USD

## Infrastructure (unverified link to wallet owner)

- `51.250.97.223` — Jenkins 2.375.3 (Yandex Cloud, Moscow)
- `51.222.42.220` — Geth RPC read-only (OVH Canada)

## Recommended outreach (when entity identified)

1. `security@<domain>` or abuse contact for cloud provider
2. Attach **jenkins-cve-report.json** + **defensive-audit-template.md**
3. 90-day coordinated disclosure window
4. **Do not** include exploit PoC or credentials

## What we did NOT do

- Jenkins RCE / credential access
- Port scanning beyond prior passive headers
- Key extraction attempts

## Binance HW 11 funding trace

Requires **legal/exchange** channel — not OSINT. On-chain only confirms withdraw from labeled Binance hot wallet.
