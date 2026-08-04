# ApeTerminal Drainer Forensics — Full Operational Protocol

## Role
Next.js drainer impersonating friend.tech — operator attribution and sink mapping.

## Context
- Repo: emmarktech/apeterminal-main
- Deploy: Vercel / custom domain rotation
- Chains: ethereum-mainnet, BSC

## Workflow
1. Static scan Next.js pages/api routes for claim/drain logic
2. Extract WalletConnect hooks and sink addresses
3. Map friend.tech brand abuse indicators
4. On-chain analyze all sink addresses
5. Build attack_chain with domain rotation TTP

## Output
`artifacts/forensics/apeterminal-drainer-report.json`
Bus: `skill.apeterminal_drainer.complete` ← `apeterminal_drainer_analyzer`
