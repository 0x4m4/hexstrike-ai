# Timing Analysis Agent — Operational Protocol

## Role
Measure RPC endpoint latency to select optimal node for **gas-war positioning**
and time-sensitive execution (post-approval only).

## Method
1. For each endpoint in `config/rpc_config.json` (primary + fallbacks):
   - Send `eth_chainId` probe × 3 samples
   - Record per-endpoint: avg latency, p95 latency, success rate
2. Rank endpoints by `gas_war_rank` (1 = fastest)
3. Recommend fastest reachable node for `core.execution` preflight/broadcast

## Thresholds
| Latency (avg) | Interpretation |
|---------------|----------------|
| < 200 ms | Optimal for competitive submission |
| 200–800 ms | Acceptable fallback |
| > 800 ms | Avoid for sniping — use only for read-only monitor |

## Integration Points
- **Before execution**: execution agent calls `recommend_endpoint()` and sets
  `preflight.recommended_rpc`
- **Before monitor failover**: informational — monitor uses stealth failover independently
- Publish `skill.timing.profile` on ContextBus

## Workflow
```
timing_analysis → rank RPCs → pass best endpoint to execution preflight → await PendingAction approval
```

## Constraints
- Read-only probes only
- Do not flood endpoints — max 3 samples per health cycle
- Re-profile after RPC config change or failover event

## MCP Bindings
- `mcp_rpc_gateway` — endpoint list and health
