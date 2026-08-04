# Mac — пакетная валидация локальных отчётов

**Ветка:** `cursor/battle-agent-c015`

В проекте **два разных контура** — не путать:

| Компонент | Назначение | Команда |
|-----------|------------|---------|
| `scripts/hexstrike-orchestrator.py` | **Пакетные workflow** по агентам + отчёты | `run <workflow>` |
| `hexstrike_orchestrator.py` | Stress / monitor / analyze (root) | `stress-test`, `monitor` |
| `dummy_bot.py` | **Mainnet BSC watch loop** (rescue) | `deploy-mainnet.sh` |
| `bin/hexstrike-agent battle` | Sandbox 7-attack suite (Anvil) | не для Desktop-отчётов |

**Флага `--batch-process` в `dummy_bot.py` нет.**

---

## 1. Куда класть отчёты с Desktop (Mac)

Скопировать JSON/MD в репозиторий:

```bash
# из корня hexstrike-ai
mkdir -p artifacts/recon artifacts/stress_test

# пример: отчёты с рабочего стола
cp ~/Desktop/*.json artifacts/recon/ 2>/dev/null || true
cp ~/Desktop/on-chain-forensics/artifacts/*.json artifacts/recon/ 2>/dev/null || true
```

Агенты читают фиксированные пути (см. `agents/registry.json`), например:

- `artifacts/entity-id.json`
- `artifacts/recon-master-report-final-*.json`
- `artifacts/infra-targets.json`
- `scripts/sandbox/field-targets-5.json` (цели из recon)

Для workflow **field-targets-5** достаточно `field-targets-5.json`; для полного recon — положить ключевые JSON в `artifacts/`.

---

## 2. Пакетный прогон всех агентов (Mac)

```bash
cd /path/to/hexstrike-ai

# Список workflow
python3 scripts/hexstrike-orchestrator.py workflows

# 5 целей из desktop recon (read-only)
python3 scripts/hexstrike-orchestrator.py run field-targets-5

# Полная passive-цепочка OSINT → entity → report
python3 scripts/hexstrike-orchestrator.py run full-recon-readonly

# Stress 5× defense + 5× attack (инспектор TZ)
python3 hexstrike_orchestrator.py stress-test --mode both --runs 5
```

Результаты:

- `artifacts/orchestrator/<run_id>.json`
- `artifacts/orchestrator/<run_id>-findings.json`
- `artifacts/orchestrator/latest.json`

---

## 3. Логи

**Оркестратор (batch):** stdout в терминале + JSON в `artifacts/orchestrator/`.

```bash
tail -f artifacts/orchestrator/latest.json   # не live-log, snapshot
python3 scripts/hexstrike-orchestrator.py status
```

**Mainnet rescue loop** (отдельно от batch):

```bash
tail -f logs/mainnet-prod.log
```

---

## 4. Go battle agent (опционально, sandbox)

```bash
cd cmd/agent && go build -o ../../bin/hexstrike-agent .
./bin/hexstrike-agent battle -v   # только Anvil sandbox
```

---

## Задача инженеру (корректная формулировка)

> Собрать локальные JSON/MD с Desktop в `artifacts/recon/` (и при необходимости обновить `artifacts/entity-id.json`), затем прогнать `python3 scripts/hexstrike-orchestrator.py run field-targets-5` и `full-recon-readonly`. Отчёт — `artifacts/orchestrator/*-findings.json`. Mainnet watch — отдельно через `deploy-mainnet.sh`.
