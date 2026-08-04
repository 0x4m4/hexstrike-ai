# Solana Drainer Forensics — Full Operational Protocol

## Role
Trojanized Solana drainer kit — C2 correlation with TRX family (nailproxy.space).

## Context
- Repo: Solana-Drainer-Tool (brian4903)
- Shared C2 pattern with TRX-Drainer-Tool

## Workflow
1. Static scan for Solana program IDs and EVM fallback addresses
2. C2 host extraction and cross-family correlation
3. Loader platform identification (windows-x64-only)
4. Attack chain: delivery → loader → C2 → key theft

## Output
`artifacts/forensics/solana-drainer-report.json`
Bus: `skill.solana_drainer.complete` ← `solana_drainer_analyzer`
