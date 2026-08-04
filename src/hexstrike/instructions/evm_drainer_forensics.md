# EVM Drainer Forensics — Full Operational Protocol

## Role
Multichain EVM wallet drainer deploy kit analysis (nx_drainer family).
Correlates evm-drainer + apeterminal-main repos for sink addresses and deploy surface.

## Context Sources
1. `EVM_DRAINER_REPO`, `APETERMINAL_REPO`
2. `artifacts/evm-drainer-iocs.json`
3. GitHub operator intel: emmarktech org

## Analysis Workflow
1. **Dual-repo static scan** — merge addresses, hosts, flagged permit/create2 files
2. **Operator IOC mapping** — GitHub org, related repos, impersonation targets
3. **Multichain sink labeling** — run_analyze per sink (ETH, BSC, Polygon, etc.)
4. **Deploy kit detection** — apeterminal-main presence → Next.js/Vercel surface
5. **Attack chain** — kit acquisition → deployment → wallet connect → drain → cashout

## Chains Documented
ethereum, bsc, polygon, avalanche, fantom, optimism, arbitrum

## Output
`artifacts/forensics/evm-drainer-report.json`
Bus: `skill.evm_drainer.complete` ← `evm_drainer_analyzer`
