# Sweep Cluster Forensics — 2026-07-13

**Workflow:** `field-targets-6` | **Run:** `22cee3933a16` | **Mode:** read-only

## Key Finding

**Все три sweep-роутера — EIP-7702 delegated accounts с одним implementation:**

```
0x314C01e758a7911e7339aa4F960C7749E8947775
```

Bytecode всех sweep-контрактов: `0xef0100314c01e758a7911e7339aa4f960c7749e8947775`

Это тот же delegate, что у **authority** `0x730ea0231808f42a20f8921ba7fbc788226768f5`.

## Architecture

```
hot_wallet (0x4943F5...)
    │
    ├── sweep_primary   (0x55ed7fcd...) ─┐
    ├── sweep_secondary (0x3e0b65c9...) ─┼─► EIP-7702 impl (0x314C01e7...)
    ├── sweep_tertiary  (0x3a8b6289...) ─┤         │
    └── authority       (0x730ea023...) ──┘         ▼
                                          Rhino.fi hub (0xb80a582f...)
```

## Targets (field-targets-6)

| # | Роль | Адрес | BNB | Nonce | USDT от hot |
|---|------|-------|-----|-------|-------------|
| 1 | sweep_primary | `0x55ed7fcd17b93fbcd5186cda01af6fed4ec78e08` | 0 | 8 | 12,268 |
| 2 | sweep_secondary | `0x3e0b65c9c31e9593e2b357be6eecd28bef6da03e` | 0 | 3 | 9,758 |
| 3 | sweep_tertiary | `0x3a8b628934f9db7999499905bbf767331266b5b5` | 0 | 12 | 7,462 |
| 4 | eip7702_impl | `0x314C01e758a7911e7339aa4F960C7749E8947775` | 0 | 1 | — |
| 5 | Rhino.fi hub | `0xb80a582fa430645a043bb4f6135321ee01005fef` | 74.99 | 2 | sink |

## Verdict

- Sweep-контракты **не независимы** — единый signature-gated payment rail
- Баланс sweep-аккаунтов всегда **0** — pass-through routing
- Drain без authority signature — **закрыт**
- Entity hot wallet — **UNIDENTIFIED**

## Next Steps

1. Bytecode audit impl `0x314C01e7...` (signature validation)
2. Cross-chain trace Rhino.fi hub exits
3. Arkham label propagation на 4 delegated accounts
4. Monitor hot wallet на новые sweep deployments

Запуск: `python3 scripts/hexstrike-orchestrator.py run field-targets-6`

---
*Read-only defensive forensics — mainnet не затронут.*
