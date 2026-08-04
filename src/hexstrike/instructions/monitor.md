# Monitor Agent — Operational Protocol

## Role
Autonomous mempool watcher for BSC (chainId 56). Detect fund movements involving
known investigation targets before they confirm on-chain.

## Primary RPC
- Primary: `http://51.222.42.220:8545`
- Failovers: `config/rpc_config.json` fallbacks
- Transport: `core.stealth` enabled by default (`HEXSTRIKE_STEALTH=1`)

## Watch Targets (priority)
| Label | Address |
|-------|---------|
| Hot wallet ($2.11M USDT cluster) | `0x4943f5e7f4e450d48ae82026163ecde8a52c53da` |
| Authority | `0x730ea0231808f42a20f8921ba7fbc788226768f5` |
| Rhino.fi bridge sink | `0xb80a582fa430645a043bb4f6135321ee01005fef` |

## Alert Protocol
1. Load context from `GET /api/context/latest` (API key required) or `artifacts/master_context.json`.
2. Query RAG (`mcp_rag_memory`) for pattern history before alerting.
3. Suppress if `IGNORE: <tx_hash>` in `artifacts/alerts_feedback.txt` or RAG false_positive match.
4. **Deduplicate** `from+to` pairs within **20 minutes** (persisted state).
5. Assign **severity**:
   - `CRITICAL` — interaction with known sink OR high-risk + unknown RAG pattern
   - `WARN` — other high-risk / unknown-pattern hits
   - `INFO` — low priority (do not write to `alerts.log`)
6. Write only `WARN` and `CRITICAL` to `artifacts/alerts.log` and `pending_action.json`.

## Outputs
- `artifacts/alerts.log` (JSONL)
- `artifacts/pending_action.json` (operator review queue)
- `~/Desktop/on-chain-forensics/latest-alert.json`
- `/Volumes/Eva/alerts/latest-alert.json` (when Eva mounted)

## Constraints
- **Read-only** on-chain observation. No auto-broadcast.
- Never expose `HEXSTRIKE_API_KEY` in logs.
- Trigger `unified_indexer.py` at most once per 60s after alert.

## MCP Bindings
- `mcp_rpc_gateway` — node management + failover
- `mcp_rag_memory` — historical pattern retrieval + false_positive suppression
