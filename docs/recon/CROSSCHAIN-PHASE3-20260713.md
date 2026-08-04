# Cross-Chain Phase-3 — 2026-07-13

**Workflow:** `field-targets-7` | **Mode:** read-only multichain

## Live Balances

| Chain | Token | Balance |
|-------|-------|---------|
| BSC | USDT | **501,564.56** |
| Base | USDC | **703,490.17** |
| **Combined** | — | **$1,205,054.73** |
| Rhino hub (BSC) | USDT float | 1,683,792.69 |

## Activity

| Chain | Nonce |
|-------|-------|
| BSC | 67285 |
| Base | **70508** |

Base nonce significantly higher — parallel high-activity treasury rail.

## Architecture

```
BSC:  hot → EIP-7702 sweeps → impl → Rhino hub → cross-chain
Base: hot → USDC treasury (parallel rail, ~703,490.17 USDC)
```

## Correlation verdict

- Rhino.fi hub = BSC exit sink (confirmed Phase-2)
- Base USDC = parallel treasury, **not** direct CEX in sample window
- Entity: **UNIDENTIFIED**
- Combined stable exposure: **$1,205,054.73**

## Base USDC top outflows (sample)


## Next steps

1. Arkham multichain labels
2. Extended Base outflow trace
3. Rhino bridge BSC→Base event correlation

---
*Orchestrator agents: OSINT-03 + Battle-07 + Report-06*
