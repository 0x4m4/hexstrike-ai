# Battle Stress Test Report — 5× Defense / 5× Attack

**Date:** 2026-07-11  
**Command:** `python3 ./hexstrike_orchestrator.py stress-test --mode both --runs 5 --monitor-duration 60`  
**Summary:** `artifacts/stress_test/battle_sessions_summary.json`

---

## Verdict: PASS

| Session | Runs | Avg Score | go test after load |
|---------|------|-----------|-------------------|
| Defense | 5/5 | **100.0** | PASS |
| Attack | 5/5 | **100.0** | PASS |

---

## Session 1: Defense

| Run | overall_score | #02 | #04 | #06 | pipeline | hot-path |
|-----|---------------|-----|-----|-----|----------|----------|
| 1 | 100.0 | DEFENDED | DEFENDED | DEFENDED | 6.15s | 67.6 ms |
| 2 | 100.0 | DEFENDED | DEFENDED | DEFENDED | 6.06s | 69.0 ms |
| 3 | 100.0 | DEFENDED | DEFENDED | DEFENDED | 6.08s | 65.6 ms |
| 4 | 100.0 | DEFENDED | DEFENDED | DEFENDED | 6.06s | 68.8 ms |
| 5 | 100.0 | DEFENDED | DEFENDED | DEFENDED | 6.10s | 74.0 ms |

- **Bus panics / concurrent map errors:** none (`bus.clean: true` all runs)
- **Pipeline avg:** ~6.1s (target 13.8s — within budget)
- **PrepareRescue hot-path avg:** ~69 ms

Reports: `test_report_defense_01.json` … `test_report_defense_05.json`

---

## Session 2: Attack

| Run | overall_score | stress KPI | amount_sim | fees1559 | entity_gate |
|-----|---------------|------------|------------|----------|-------------|
| 1–5 | 100.0 each | pass | pass | pass | pass |

- **Recon IP:** 51.250.97.223
- **Stress wall-clock:** ~44s/run (monitor cap 30s in attack mode)
- **Amount simulation:** stable on fork DRY_RUN

Reports: `test_report_attack_01.json` … `test_report_attack_05.json`

---

## Env

```
ALLOWED_FUNDERS=0x730ea0231808f42a20f8921ba7fbc788226768f5
ARKHAM_API_KEY=(not set — lab permissive mode)
```

---

## Next: P3

Ready to land `internal/relay/` (Puissant BSC + Flashbots ETH).
