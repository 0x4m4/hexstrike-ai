# ОТЧЁТ ОБ ИНЦИДЕНТЕ: ПОЛНАЯ КОМПРОМЕТАЦИЯ ИНФРАСТРУКТУРЫ

**Статус:** CRITICAL BREACH POST-MORTEM (worst-case planning document)  
**Идентификатор дела:** HEX-2026-07-12-TOTAL-COMPROMISE  
**Классификация:** APT / полный захват периметра (сценарий)  
**Режим HexStrike:** read-only forensics + defensive IR — без offensive exploit instructions  

---

## 0. Факт vs сценарий (важно)

| Параметр | **Факт (pentest 2026-07-08)** | **Worst-case (этот документ)** |
|----------|-------------------------------|--------------------------------|
| Jenkins RCE | ✅ доказан | ✅ предполагается |
| Open BSC RPC | ✅ доказан | ✅ предполагается |
| Private key hot wallet | ❌ **не получен** | ⚠️ **предполагается скомпрометирован** |
| Drain выполнен | ❌ **BLOCKED** | ⚠️ **возможен** |
| Payroll/OTC verdict | ✅ CLOSED (MEDIUM-HIGH) | N/A — смена контура выплат |

> Документ описывает **план реагирования**, если worst-case materialized.  
> Текущий live-статус: **инфраструктура exposed, ключи hot wallet не подтверждены как утечшие**.

---

## 1. Scope активов

| Актив | Значение |
|-------|----------|
| Hot wallet (TARGET) | `0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA` |
| Authority (EIP-7702) | `0x730ea0231808f42a20f8921ba7fbc788226768f5` |
| Bridge sink (Rhino.fi) | `0xb80a582fa430645a043bb4f6135321ee01005fef` |
| Infra-correlated wallet | `0xcfc85f21f5f01ab24d6b7a3b93ef097099ebde3a` |
| Jenkins | `51.250.97.223:8080` (Yandex Cloud) |
| BSC Geth RPC | `51.222.42.220:8545` (OVH) |
| Operator PoC (out of scope) | `0x85dB346BE1d9d5D8ec4F57acf0067FbE53a6E846` |

**Behavioral class (forensics):** Payment processor / Payroll disbursement rail — см. `artifacts/forensics/payroll-otc-verdict.md`

---

## 2. Attack Kill Chain (worst-case)

```
[Шаг 1: Recon]        Публичный Jenkins 51.250.97.223:8080 (CVE-2024-23897 class)
         │
         ▼
[Шаг 2: Exploit]      File read / Groovy RCE → .env, CI secrets, deploy vars
         │
         ▼
[Шаг 3: Lateral]      Pivot → internal 10.129.0.0/24, Gym API, cred hints
         │
         ▼
[Шаг 4: RPC abuse]    Open Geth 51.222.42.220:8545 → mempool intel, state reads
         │
         ▼
[Шаг 5: Signing]      Compromise isolated Signing Service → PRIVATE KEY exfil
         │
         ▼
[Шаг 6: Impact]       Unauthorized signed txs from 0x4943... → bridge/CEX exit
```

**Факт pentest:** цепочка остановлена на **Шаг 5** (ключ не получен).

---

## 3. Compromised Assets (worst-case matrix)

| Компонент | Worst-case статус | Следствие |
|-----------|-------------------|-----------|
| Private key `0x4943...` | **COMPROMISED** | Полная криптографическая власть над hot wallet |
| Jenkins credentials | **COMPROMISED** | Утечка repo tokens, deploy secrets, `.env` |
| Geth / RPC node | **FULL CONTROL** | Mempool manipulation, DoS, false balance reads |
| Signing service | **COMPROMISED** | Bot key exfil; txs вне легитимного софта |
| GitHub/GitLab tokens | **ASSUME BREACH** | Rotate all PATs tied to CI |
| Binance funding trail | **INFO LEAK** | KYC entity link exposed (LEA path) |

---

## 4. Incident Response Protocol

### 4.1 Containment — немедленно (0–4 ч)

| # | Действие | Mac (оператор) | Server / Cloud |
|---|----------|----------------|----------------|
| 1 | Isolate Jenkins host | — | Yandex console: **stop** VM `51.250.97.223` |
| 2 | Isolate Geth RPC host | — | OVH panel: **stop** or firewall **8545** |
| 3 | Revoke CI secrets | Rotate GitHub/GitLab PATs | `jenkins` credentials revoke |
| 4 | Revoke cloud API keys | — | Yandex/OVH IAM key rotation |
| 5 | Block outbound from signing svc | — | Network ACL deny egress (if identified) |
| 6 | Preserve evidence | Copy artifacts to air-gapped | Snapshot disks before power-off |

**HexStrike (read-only):** продолжить `autonomous_monitor.py` только до containment, затем **stop**.

### 4.2 Asset Rescue — легитимный владелец (4–24 ч)

> Только если **подтверждена** компрометация ключа и остаток ликвидности на hot wallet.

| Mac | Server |
|-----|--------|
| Создать **новый** cold wallet на чистом air-gapped/host device | **Не** использовать скомпрометированные hosts |
| Использовать **авторизованный** rescue pipeline (`dummy_bot.py` / hardened bot) с **новым** ключом funder | RPC только с **чистого** endpoint (не 51.222.42.220) |
| `gas_bump` ≥ +50% tip для competitive rescue | Monitor mempool с clean RPC |

**Запрещено:** rescue с ключами, хранившимися на Jenkins/Geth/signing host.

**Факт:** в pentest 2026-07-08 rescue **не требовался** — drain blocked.

### 4.3 Eradication & Recovery (1–7 дней)

1. **Burn address:** `0x4943...` **навсегда** исключить из ops; считать ключ публично скомпрометированным.
2. **Greenfield deployment:**
   - New VPS, clean OS images
   - Jenkins **only VPN**, no WAN `:8080`
   - HashiCorp Vault / cloud KMS — signing via API, raw key never on CI
   - RPC `:8545` bind `127.0.0.1` + auth proxy
3. **New hot wallet:** новый адрес + новый signing service + payroll rail migration.
4. **Forensics retention:** `artifacts/forensics/*`, pentest logs, chain of custody.

### 4.4 Recovery verification

| Check | Pass criteria |
|-------|---------------|
| Old hot wallet disabled | No new payroll txs from `0x4943...` |
| New signing path | HSM/Vault audit log only |
| RPC | No public JSON-RPC |
| Jenkins | CVE patched, auth + VPN |
| HexStrike monitor | Watches **new** addresses only |

---

## 5. Timeline (reference)

| UTC | Event | Source |
|-----|-------|--------|
| 2026-07-08 | Pentest: Jenkins RCE proven | PENTEST_FULL_REPORT |
| 2026-07-08 | Drain BLOCKED — no private key | PENTEST_FULL_REPORT |
| 2026-07-10 | Recon master: 5-wallet BSC set | TARGETS-REPORT |
| 2026-07-12 | Forensics 7/7 + hot-wallet dossier | session-report-20260712 |
| 2026-07-12 | Payroll/OTC case CLOSED | payroll-otc-verdict.md |
| 2026-07-12 | **This document** — worst-case IR plan | HEX-2026-07-12-TOTAL-COMPROMISE |

---

## 6. Evidence index

| Artifact | Path |
|----------|------|
| Hot wallet dossier | `artifacts/forensics/hot-wallet-dossier.md` |
| Payroll/OTC verdict | `artifacts/forensics/payroll-otc-verdict.md` |
| Entity resolution | `artifacts/entity-id.json` |
| Infra trace | `artifacts/infra-trace-final.json` |
| Jenkins CVE | `artifacts/jenkins-cve-report.json` |
| Exchange LEA pack | `artifacts/exchange-forensics/` |
| Pentest (authorized) | `docs/uploads/PENTEST_FULL_REPORT` (operator copy) |

---

## 7. ВЫВОД (Executive Conclusion)

### 7.1 Резюме для руководства

По результатам авторизованного pentest (2026-07-08), read-only forensics (2026-07-12) и моделирования сценария **Total Compromise** установлено следующее.

**Объект:** операционный hot wallet `0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA` — payroll/disbursement rail (~$2.1M multichain, ~977 recipients/day), не drainer/fraud kit.

**Фактическое состояние на 2026-07-12:**
- Периметр **скомпрометирован на уровне инфраструктуры** (Jenkins RCE, open BSC RPC, passive mempool intel).
- **Криптографический ущерб не materialized:** private key hot wallet **не получен**, несанкционированный drain **не выполнен**.
- Forensics pipeline **закрыт:** payroll/OTC hypothesis — **MEDIUM-HIGH**, case status — **CLOSED**.

**Worst-case (при эскалации до полной компрометации signing service):**
- Hot wallet и вся связанная CI/RPC инфраструктура считаются **totally compromised**.
- Операционный адрес `0x4943...` **подлежит выводу из эксплуатации** (burn).
- Обязателен **greenfield rebuild** + **резервный контур выплат**.

---

### 7.2 Выводы по направлениям

| Направление | Вывод |
|-------------|-------|
| **Attack surface** | Критический: публичный Jenkins + открытый JSON-RPC создают сквозной путь к signing layer |
| **Business impact (actual)** | Exposure ~$2.1M treasury **без** подтверждённой кражи; reputational + regulatory risk при утечке KYC trail (Binance funding) |
| **Business impact (worst-case)** | Total loss hot wallet liquidity + останов payroll rail + incident response costs |
| **Root cause** | Отсутствие network segmentation, secrets in CI, signing key proximity to compromised hosts |
| **Attribution** | Legal entity **UNIDENTIFIED**; behavioral class — payment processor / payroll |
| **Containment status** | **NOT EXECUTED** (preventive phase); IR plan **READY** |

---

### 7.3 Матрица решений (Disposition)

| Сценарий | Решение | Срок |
|----------|---------|------|
| **Actual (сейчас)** | Превентивный hardening: закрыть Jenkins WAN, RPC auth, rotate CI secrets | 0–72 ч |
| **Actual (сейчас)** | Продолжить read-only monitor hot wallet (`autonomous_monitor.py`) | ongoing |
| **Worst-case trigger** | Power-off `51.250.97.223` + `51.222.42.220`, revoke all tokens | немедленно |
| **Worst-case trigger** | Asset rescue → cold wallet (только легитимный владелец, clean RPC) | 4–24 ч |
| **Worst-case trigger** | Burn `0x4943...`, greenfield + Vault signing + new hot wallet | 1–7 дней |

**Trigger worst-case IR:** любое из событий — unauthorized signed tx с `0x4943...`, confirmed key exfil, anomalous outflow > threshold.

---

### 7.4 Итоговый вердикт (формулировка для инцидент-лога)

**При фактическом состоянии (2026-07-12):**

> Инфраструктура crypto-ops **критически exposed**, но **не признана fully breached**. Hot wallet классифицирован как **payroll disbursement rail**. Private key **не подтверждён как скомпрометированный**. Несанкционированный вывод средств **не зафиксирован**. Дело forensics — **закрыто**. Требуется **превентивный containment** до наступления worst-case.

**При сценарии Total Compromise:**

> Инфраструктура **признана непригодной** к дальнейшей эксплуатации. Криптографические ключи hot wallet **считаются скомпрометированными**. Адрес `0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA` **исключается** из операционного цикла. Выполнить containment → asset rescue (при наличии ликвидности) → greenfield deployment → миграция payroll rail на новый контур.

---

### 7.5 Обязательные действия (Action Items)

| Priority | Action | Owner | Mac | Server |
|----------|--------|-------|-----|--------|
| P0 | Закрыть Jenkins `:8080` из WAN | Infra | — | Yandex console |
| P0 | Закрыть/авторизовать RPC `:8545` | Infra | — | OVH firewall |
| P1 | Rotate Jenkins + GitHub/GitLab secrets | SecOps | PAT revoke | CI credential purge |
| P1 | Vault/KMS для signing (raw key off CI) | Eng | design | deploy |
| P2 | Continuous mempool monitor hot wallet | HexStrike | `autonomous_monitor.py` | `autonomous_monitor.py` |
| P2 | Responsible disclosure Jenkins CVE pack | SecOps | `jenkins-cve-report.json` | same |

---

### 7.6 Статус дела

| Поле | Значение |
|------|----------|
| Case ID | `HEX-2026-07-12-TOTAL-COMPROMISE` |
| Forensics phase | **CLOSED** |
| IR phase (actual) | **PREVENTIVE / MONITORING** |
| IR phase (worst-case plan) | **DOCUMENTED — READY** |
| Next review | При первом unauthorized tx или key exfil alert |

---

### 7.7 Подпись (placeholder)

| Роль | ФИО | Дата | Подпись |
|------|-----|------|---------|
| Incident Commander | _______________ | 2026-07-12 | _______ |
| Forensics Lead | HexStrike Agent | 2026-07-12 | auto |
| Client Representative | _______________ | _________ | _______ |

---

## 8. Команды HexStrike (defensive)

### Mac
```bash
cd /Volumes/Eva/mufasaai-storage/hexstrike-ai
cat artifacts/forensics/payroll-otc-verdict.md
cat docs/forensics/INCIDENT-TOTAL-COMPROMISE-POSTMORTEM.md
bash scripts/run-hot-wallet-ops.sh
```

### Server
```bash
cd /opt/hexstrike-ai
cat docs/forensics/INCIDENT-TOTAL-COMPROMISE-POSTMORTEM.md
cat artifacts/forensics/payroll-otc-verdict.md
systemctl stop hexstrike-orchestrator   # при реальном containment
```

---

*HexStrike defensive IR — read-only forensics, remediation guidance only.*
