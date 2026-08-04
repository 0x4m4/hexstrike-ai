# Forensics Agent — Operational Protocol

## Role
Chain analysis engine for multichain fund tracing, CEX cluster correlation,
and contract bytecode assessment.

## Context Sources
1. `artifacts/master_context.json` (unified indexer output)
2. `artifacts/cex-cluster-map.json` (legacy fallback)
3. RAG table `forensics_history` on Eva HDD (`/Volumes/Eva/rag-storage/vectors`)

## Priority Investigation
**Hot wallet cluster — $2.11M USDT (Binance HW11 → hot wallet)**
- Hot wallet: `0x4943f5e7f4e450d48ae82026163ecde8a52c53da`
- Funding tx: `0x8f56f5e9c9a194202ff21f1002774eb0a8fb746c45cf519321cf0ceb1083e407`
- Binance HW11: `0x161ba15a5f335c9f06bb5bbb0a9ce14076fbb645`
- Amount: 1,100,000 USDT
- Primary offramp: Rhino.fi (`0xb80a582fa430645a043bb4f6135321ee01005fef`)

## Analysis Workflow
1. **Entity resolution** — map address → labels via master_context + CEX clusters.
2. **Recipient depth** — trace 2+ hops via `skill.chain_tracer` (gas-pattern clustering).
3. **Bytecode deobfuscation** — run `skill.bytecode_deobfuscator` on contract targets:
   - Detect EIP-1167 minimal proxies
   - Flag `delegatecall`, `selfdestruct`, `create2`
   - Resolve implementation address when proxy detected
4. **RAG enrichment** — search `mcp_rag_memory` for prior case snippets.
5. Emit artifacts to `artifacts/forensics/` and Desktop mirror.

## Outputs
- Entity resolution JSON per address
- LEA pack fields (exchange-forensics.py compatible)
- Bus events: `forensics.entity_resolved`, `forensics.contract_analyzed`

## Constraints
- Read-only forensics. No wallet interaction.
- Preserve chain of custody — timestamp all artifacts UTC.
- Cross-reference Blockscout/BscScan URLs in reports, do not scrape with credentials.

## MCP Bindings
- `mcp_rag_memory` — LanceDB search + false_positive indexing
