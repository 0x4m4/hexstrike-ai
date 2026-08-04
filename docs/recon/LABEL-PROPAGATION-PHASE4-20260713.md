# Label Propagation Phase-4 — 2026-07-13

**Agent:** OSINT-03 | **Targets:** 8 | **Public labels:** 2

## Entity verdict

- Hot wallet entity: **UNIDENTIFIED**
- Infra cluster: **hot_wallet_infra** (4 EIP-7702 delegates + shared impl)
- External: Rhino.fi (bridge), Binance (funder)

## Labels per target

| Role | Public label | Inferred role | Entity cluster |
|------|--------------|---------------|----------------|
| hot_wallet | — | multichain ops treasury (BSC USDT + Base USDC) | UNIDENTIFIED |
| authority | — | EIP-7702 authority delegate | hot_wallet_infra |
| sweep_router_primary | — | EIP-7702 sweep delegate #1 | hot_wallet_infra |
| sweep_router_secondary | — | EIP-7702 sweep delegate #2 | hot_wallet_infra |
| sweep_router_tertiary | — | EIP-7702 sweep delegate #3 | hot_wallet_infra |
| rhino_hub | Rhino.fi: Bridge | cross-chain bridge sink | Rhino.fi (protocol) |
| binance_funder | Binance Hot Wallet 11 | CEX hot wallet — primary funder | Binance |
| eip7702_implementation | — | EIP-7702 payment delegate implementation | hot_wallet_infra |

## Arkham manual review

- [hot_wallet](https://platform.arkhamintelligence.com/explorer/address/0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA)
- [authority](https://platform.arkhamintelligence.com/explorer/address/0x730ea0231808f42a20f8921ba7fbc788226768f5)
- [sweep_router_primary](https://platform.arkhamintelligence.com/explorer/address/0x55ed7fcd17b93fbcd5186cda01af6fed4ec78e08)

---
*Read-only passive OSINT — no API key required for URL generation.*
