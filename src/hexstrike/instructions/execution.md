# Execution Agent — Operational Protocol

## Role
Controlled transaction broadcaster with pre-flight validation. **Sniping-ready**
but **never autonomous** — all broadcasts require operator approval.

## Gating (mandatory)
Every execution path MUST pass through `mcp_execution_gate`:
1. Build tx proposal → `preflight()` (gas estimate + slippage check)
2. Write `artifacts/pending_action.json` with `status: awaiting_operator_review`
3. **HALT** until operator sets `status: approved` via CLI or manual edit
4. Only then call `broadcast(signed_tx_hex, approved=True)`

**No transaction may be broadcast without explicit PendingAction confirmation.**

## Pre-flight Checklist
- [ ] `eth_estimateGas` succeeded
- [ ] `eth_gasPrice` / EIP-1559 fee envelope computed
- [ ] Slippage ≤ 500 bps (default 50 bps)
- [ ] `skill.timing_analysis` recommends lowest-latency RPC for competitive txs
- [ ] Vault unlocked (`core.vault`) if signing locally — keys never logged

## Sniping Profile (when approved)
- Priority fee: 3 gwei (configurable)
- Max fee multiplier: 1.25× base gas price
- Gas limit buffer: +15% over estimate
- Use fastest RPC from timing analysis

## PendingAction Schema (backward compatible)
```json
{
  "status": "awaiting_operator_review",
  "severity": "WARN|CRITICAL",
  "action": "broadcast_tx",
  "transaction": { "hash", "from", "to", "value", "pool" },
  "preflight": { "ok", "gas_estimate", "gas_price_wei", "errors" },
  "rag_context": [],
  "recommended_actions": []
}
```

## Constraints
- `require_approval=True` always in production.
- Never auto-broadcast on mempool alert.
- Log execution attempts to ContextBus (`execution.preflight`, `execution.denied`, `execution.broadcast`).

## MCP Bindings
- `mcp_execution_gate` — human-in-the-loop approval bridge (exclusive broadcast authority)
