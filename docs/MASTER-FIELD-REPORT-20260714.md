# Master Report — merged field probe (13 targets)

**Run:** `artifacts/field-runs/merged-full-20260714/`  
**Дата:** 2026-07-14  
**Время прогона:** ~20 сек (parallel=5, agent+deep-read)

---

## Топ приоритеты

| Приоритет | Роль | Адрес | BNB | Действие |
|-----------|------|-------|-----|----------|
| **высокий 4.6** | primary_sink_hub | `0xb80a582f…` | ~75 | ProxyAdmin + Safe 2/3, Slither impl |
| **средний 4.1** | authority | `0x730ea023…` | 0 | EIP-7702 delegator → impl audit |
| **средний 3.6** | infra_correlated | `0xcfc85f21…` | 0 | EIP-7702 + IP 51.250.97.223 |
| **средний 2.7** | eip7702_implementation | `0x314C01e7…` | 0 | **Slither #1 priority** (4 delegators) |
| **средний 2.7** | bridge_implementation | `0x5ab2790b…` | 0 | Slither + owner triage |
| **инфо 0.3** | usdt_treasury_source | `0x161ba15a…` | **~3914** | Upstream treasury OSINT |

---

## EIP-7702 — единый кластер (4 delegator → 1 impl)

```
0x314C01e758a7911e7339aa4F960C7749E8947775  (logic: ECDSA execute batch)
         ▲           ▲           ▲           ▲
         │           │           │           │
   authority    infra_corr   top_recip_1  top_recip_2
   0x730ea0…    0xcfc85f…    0x55ed7f…    0x3e0b65…
```

**Blast radius:** один bug в impl = 4 payment rails.

---

## Мост Rhino.fi (control plane)

```
Gnosis Safe 0x7af3828c… (2/3)
    └── ProxyAdmin 0xb8ee2cd0…
            └── Proxy 0xb80a582f… (74.77 BNB)
                    └── Implementation 0x5ab2790b…
                            owner() → 0xc38a2eb3… (EOA, triage)
```

---

## Поток USDT (hot wallet graph)

```
0x161ba15a… (treasury, 3914 BNB) ──1.1M USDT──► hot_wallet 0x4943F5E7…
                                                    │
                    ┌───────────────────────────────┼───────────────────────┐
                    ▼                               ▼                       ▼
              authority 22k                  infra 11.8k              top_recip 12k+
                    └──────────────► bridge hub 0xb80a582f… ◄──────────────┘
```

---

## Заблокировано

- **Slither/Mythril** — нужен `BSCSCAN_API_KEY`
- **eth_getLogs** wide range — ваш RPC `51.222.42.220:8545` + API v2

---

## Команды (Mac)

```bash
source .venv-audit/bin/activate
set -a && source .env && set +a
./scripts/run-field-batch.sh                    # 13 targets merged
./scripts/run-slither-mythril-audit.sh          # после API key
```

---

## Следующий sprint

1. Slither: `0x314C01e7…`, `0x5ab2790b…`, `0xb8ee2cd0…`
2. OSINT: `0x161ba15a…`, `0xc38a2eb3…`
3. Monitor: новые delegator на impl `0x314C01e7…`
