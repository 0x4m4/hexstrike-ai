# Отчёт: полевое тестирование HexStrike Battle Agent

**ID:** `field-agent-test-report-2026-07-11`  
**Дата:** 2026-07-11  
**Режим:** read-only / defensive  
**Агент:** Agent-Battle-07  
**Оркестратор:** `hexstrike-orchestrator`

---

## 1. Резюме

| Метрика | Значение |
|---------|----------|
| Статус кампании | **PASS** — все автоматические прогоны зелёные |
| Risk posture | **elevated** |
| Entity | **UNIDENTIFIED** (confidence: low) |
| Hot wallet risk | **high** |
| Battle readiness | **75/100** (vuln=5, defended=2) |
| Mainnet withdrawals | **0** — средства не выводились |

Проведено полевое read-only recon на **5 целях** из desktop-отчётов, **10×** стабильность pipeline, **120×** имитация малых/больших сумм на BSC fork (DRY_RUN), **20×** локальный gas-benchmark на Anvil.

---

## 2. Scope и ограничения

- Только **read-only** on-chain (BSC live + локальный fork).
- **DRY_RUN=true** на чужих адресах — без приватного ключа hot wallet.
- Подмена баланса только через `anvil_setBalance` на **локальном fork**, не на mainnet.
- Локальное подписание — только Anvil chain **31337**, тестовые ключи.
- Exploit / drain / unauthorized signing на BSC mainnet — **не выполнялись**.

---

## 3. Цели (5 шт.)

Источник: `scripts/sandbox/field-targets-5.json`

| # | Роль | Адрес | Отчёт-источник | Live BSC | Риск |
|---|------|-------|----------------|----------|------|
| 1 | hot_wallet | `0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA` | recon-master Phase A | 0.096 BNB, nonce 62832 | **high** |
| 2 | authority | `0x730ea0231808f42a20f8921ba7fbc788226768f5` | authority-contract-analysis | EIP-7702 delegated | medium |
| 3 | primary_sink_hub | `0xb80a582fa430645a043bb4f6135321ee01005fef` | infra-targets (Rhino.fi) | 79.6 BNB | medium |
| 4 | puissant_validator | `0x4848489f0b2bedd788c696e2d79b6b69d7484848` | recon-master Phase A | 67.76 BNB | low |
| 5 | infra_correlated_wallet | `0xcfc85f21f5f01ab24d6b7a3b93ef097099ebde3a` | vector-forensics | nonce 19 | low |

**Исключены:** `operator_local` (PoC-ключ оператора), остальные counterparties (ниже приоритет vs infra-корреляция).

**Оценка hot wallet (prior recon):** ~$2.11M multichain (BSC USDT + BASE USDC).

---

## 4. Методология тестов

### 4.1 Полевой pipeline (`field-targets-5`)

```bash
python3 scripts/hexstrike-orchestrator.py run field-targets-5
```

Шаги: profile → BSC fork setup → multi-wallet recon → conclusion → VPS master report.

**Run ID:** `be4466609169` — 5/5 шагов OK.

### 4.2 Стабильность pipeline (10 прогонов)

Workflow: `multi-wallet-conclusions` (12 кошельков).  
Скрипт: `run-field-benchmark.py`.

### 4.3 Имитация сумм (20× малые / 20× большие)

Скрипт: `run-amount-simulation-benchmark.py`  
Среда: BSC fork, chain_id=56, `DRY_RUN=true`.

| Категория | Баланс (ETH) | Ожидание | Прогонов |
|-----------|--------------|----------|----------|
| Малый — trigger | 0.3 | signed (dry-run) | 20 |
| Малый — boundary | 0.499 | signed (dry-run) | 20 |
| Малый — no gas | 0.001 | blocked_no_gas | 20 |
| Большой — boundary | 0.501 | none | 20 |
| Большой — idle | 10.0 | none | 20 |
| Большой — max | 100.0 | none | 20 |

Параметры: THRESHOLD=**0.5 ETH**, MIN_GAS=**0.01 ETH**, RESCUE_VALUE=**1.0 ETH** (симуляция, не broadcast).

### 4.4 Gas benchmark (локальный Anvil)

Скрипт: `run-withdraw-gas-benchmark.py` — 10×2 сценария.

| Сценарий | Баланс | Rescue tx | Результат |
|----------|--------|-----------|-----------|
| with_gas | 0.3 ETH | 0.001 ETH | signed (local) |
| without_gas | 0.001 ETH | — | blocked_no_gas |

### 4.5 Battle suite (локальный sandbox)

5 прогонов Go-агента: readiness **75/100** стабильно.

---

## 5. Результаты

### 5.1 Полевой прогон (5 целей)

```
5 wallets scanned — 5 active, 1 high-risk
Risk posture: elevated
Entity: UNIDENTIFIED
```

| Кошелёк | Статус | Риск | Ключевой finding |
|---------|--------|------|------------------|
| hot_wallet | ACTIVE | high | nonce=62832, mass payout rail |
| authority | ACTIVE | medium | EIP-7702 delegation code |
| primary_sink_hub | ACTIVE | medium | Rhino.fi bridge contract |
| puissant_validator | ACTIVE | low | 48Club MEV, отдельная инфра |
| infra_correlated_wallet | ACTIVE | low | корреляция с 51.250.97.223 |

### 5.2 Стабильность field benchmark

| Метрика | Значение |
|---------|----------|
| Pass | **10/10** (100%) |
| Avg time | **13.8 s** |
| Hot wallet nonce drift | 62808 → 62811 (+3) |
| Verdict stable | **да** |

### 5.3 Имитация сумм (120 прогонов)

| Категория | Pass | Стабильность |
|-----------|------|--------------|
| Малые суммы (60 run) | **60/60** | 100% |
| Большие суммы (60 run) | **60/60** | 100% |
| **Итого** | **120/120** | avg **0.083 s**/run |

### 5.4 Withdraw gas benchmark

| Сценарий | Pass |
|----------|------|
| with_gas (0.3 ETH) | 10/10 |
| without_gas (0.001 ETH) | 10/10 |
| **Итого** | **20/20** |

### 5.5 Battle readiness

| Метрика | Значение |
|---------|----------|
| Score | 75/100 |
| VULN_CONFIRMED | 5 |
| DEFENDED | 2 |
| INCONCLUSIVE | 0 |

---

## 6. Анализ

### 6.1 Полевые тесты — что реально проверялось

- **Чтение** balance / nonce / code с BSC live RPC.
- **Fork-watch** с `DRY_RUN` — логика триггера без подписи на mainnet.
- **Не проверялось:** вывод USDT/BNB с hot wallet, суммы из отчётов (~$2.1M).

### 6.2 Имитация малых vs больших сумм

1. **< 0.5 ETH** → rescue trigger; при DRY_RUN → `signed` (would-sign).
2. **0.001 ETH** → trigger, но `blocked_no_gas` (< 0.01 ETH MIN_GAS).
3. **≥ 0.501 ETH** → бот idle (`none`), независимо от 10 или 100 ETH.
4. Граница **0.499 vs 0.501 ETH** — детерминированное поведение на 20/20 прогонах.

### 6.3 Закрытые векторы (в рамках тестов)

- RPC key extraction — CLOSED (read-only nodes).
- Allowance hot → operator — CLOSED (0).
- Unauthorized mainnet drain — NOT EXECUTED / NOT POSSIBLE без ключа.

### 6.4 Открытые векторы

- **#6** OSINT: кто контролирует hot wallet — UNIDENTIFIED.
- **#9** Infra/KMS оператора hot wallet.
- **#4** Jenkins/RDP 51.250.97.223 — recon only, exploitation вне scope.
- Entity attribution требует Arkham/GitHub API (401 без токена).

---

## 7. Рекомендации

1. **Мониторинг** hot_wallet outflows (passive, read-only).
2. **Arkham / Blockscan** — label propagation на top counterparties.
3. **GitHub token** — для infra dorking (сейчас 401).
4. **Fork-watch** перед любыми authorized signing tests.
5. **Hardening sandbox:** allowlist FUNDER, dedup rescue txs, Step-3 two-phase battle.
6. **Responsible disclosure** — если entity/infra owner идентифицирован пассивным OSINT.

---

## 8. Индекс артефактов

| Файл | Описание |
|------|----------|
| `artifacts/field-agent-test-report-2026-07-11.md` | Этот отчёт |
| `artifacts/field-agent-test-report-2026-07-11.json` | Machine-readable |
| `scripts/sandbox/field-targets-5.json` | 5 целей |
| `artifacts/sandbox/target-conclusion.json` | Вердикт field-targets-5 |
| `artifacts/sandbox/amount-simulation-benchmark.json` | 120 имитаций |
| `artifacts/sandbox/amount-simulation-analysis.md` | Анализ сумм |
| `artifacts/sandbox/field-runs-benchmark.json` | 10 полевых прогонов |
| `artifacts/sandbox/withdraw-gas-benchmark.json` | 20 gas-тестов |
| `artifacts/orchestrator/be4466609169-findings.json` | Orchestrator bundle |

---

## 9. Команды воспроизведения

```bash
# Полевой тест 5 целей
python3 scripts/hexstrike-orchestrator.py run field-targets-5

# Имитация сумм (20×6 сценариев)
python3 scripts/hexstrike-orchestrator.py run field-targets-5  # fork setup
python3 scripts/sandbox/run-amount-simulation-benchmark.py

# Полевой benchmark (10×)
python3 scripts/sandbox/run-field-benchmark.py

# Gas benchmark (локальный Anvil)
python3 scripts/sandbox/run-withdraw-gas-benchmark.py

# Battle suite
./bin/hexstrike-agent battle -v
```

---

*Отчёт сгенерирован автоматически на основе артефактов HexStrike. Все тесты оставались read-only; mainnet не затронут.*
