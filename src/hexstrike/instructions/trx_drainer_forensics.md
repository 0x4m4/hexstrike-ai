# TRX Drainer Forensics — Full Operational Protocol

## Role
Static malware analysis engine for trojanized TRX/crypto drainer kits.
Correlates loader binaries, C2 endpoints, and on-chain sink addresses.

## Context Sources
1. Local clone: `TRX_DRAINER_REPO` (default `artifacts/intel/TRX-Drainer-Tool`)
2. Prior IOC runs in `artifacts/trx-drainer-tool-iocs.json`
3. RAG table `forensics_history` for cross-case C2 reuse (e.g. nailproxy.space)

## Analysis Workflow
1. **Recursive static scan** — all source/binary extensions, no file cap unless `FORENSICS_MAX_FILES` set
2. **Network IOC extraction** — URLs, C2 hosts, Telegram handles, Discord webhooks
3. **Loader path mapping** — build/, dist/, inject/, dropper/ paths
4. **On-chain sink correlation** — `run_analyze()` per extracted EVM address
5. **Attack chain assembly** — delivery → social engineering → loader → C2 → impact
6. Emit to `artifacts/forensics/trx-drainer-report.json` + Desktop mirror

## Output Schema
`hexstrike.malware-analysis.v1` with fields:
- `sample`, `network_iocs`, `onchain_iocs`, `loader_analysis`, `attack_chain`
- `onchain_analysis[]` — entity + contract + trace + RAG per sink
- `network_iocs_enriched` — DNS + HTTP fingerprint per C2 host

## Bus Events
- `skill.trx_drainer.complete` ← `trx_drainer_analyzer`

## Constraints
Defensive disclosure and IR only. No kit execution on operator host.
