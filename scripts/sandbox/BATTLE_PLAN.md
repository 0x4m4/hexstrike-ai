# 🎯 HexStrike Red-Team Battle Plan

## Objective
Systematically extract and document **all bot vulnerabilities** before hardening deployment.

---

## Campaign Timeline

### **T-0: Recon Phase (5 min)**
```bash
./scripts/sandbox/run-step1.sh &   # start watching
# In another terminal:
./scripts/sandbox/set-balance.sh 0x70997970... 300000000000000000
# Observe: Does bot sign?
```

**Victory Condition**: Bot signs on low balance (baseline vulnerability confirmed).

---

### **T+5min: Rapid Offensive (15 min)**

#### Attack 1: Baseline Signing
- **Vector**: Direct low balance trigger
- **Expected**: Bot signs without guards
- **Metric**: ≥1 signed TX

#### Attack 2: Race Condition
- **Vector**: Oscillate balance 5× (low→high→low)
- **Expected**: Multiple signed TXs (no dedup)
- **Metric**: >1 signed TX detected

#### Attack 3: Front-Run Drain
- **Vector**: Drop balance, immediately zero it
- **Expected**: Bot signs but balance gone
- **Metric**: Signed + balance=0

#### Attack 4: Replay Rescue
- **Vector**: Re-broadcast same TX hash twice
- **Expected**: Second broadcast accepted (or fails gracefully)
- **Metric**: Replay rejection or success

#### Attack 5: TOCTOU Nonce Bump
- **Vector**: Bump nonce while rescue pending
- **Expected**: Bot gets nonce-too-low error or retries
- **Metric**: Error count or retry behavior

#### Attack 6: Compromised Funder
- **Vector**: Change FUNDER_ADDRESS to attacker wallet
- **Expected**: Bot sends rescue value to attacker
- **Metric**: Attacker balance increases

#### Attack 7: Hardening Defense
- **Vector**: Simulate RPC mismatch (proxy vs direct)
- **Expected**: Step 3 hardening blocks signing
- **Metric**: block_reason = "rpc_mismatch"

---

## Execution

### One-Command Battle
```bash
cd scripts/sandbox/redteam
./run-all.sh
```

Generates: `artifacts/sandbox/redteam-report.json`

### Real-Time Monitoring (3 terminals)

**Terminal 1**: Live bot events
```bash
make watch
```

**Terminal 2**: Live hardening alerts (if Step 3)
```bash
make alerts
```

**Terminal 3**: Run attacks
```bash
make battle-fast   # quick: 2 attacks
# OR
make battle        # full: 7 attacks
```

---

## Victory Scoring

| Attack | VULN_CONFIRMED | DEFENDED | INCONCLUSIVE |
|--------|----------------|----------|--------------|
| 01-baseline | ✅ exploit found | ❌ bot not ready | ❓ slow poll |
| 02-race-dup | ✅ no dedup | ❌ poll too slow | ❓ timing edge |
| 03-front-run | ✅ TOCTOU win | ❌ no gas | ❓ race lost |
| 04-replay | ✅ replayable | ❌ node rejects | ❓ data extract fail |
| 05-toctou | ✅ nonce race | ❌ error handling | ❓ timing |
| 06-funder | ✅ no allowlist | ❌ hardening blocks | ❓ hardening off |
| 07-hardening | ❌ blocks mismatch | ✅ defended | ❓ test issue |

### Post-Battle Summary
```bash
make logs
```

Output:
```
📋 Artifact logs:
  bot events: 42 lines
  rpc_interceptor: 0 lines
  anomaly_alerts: 12 lines

Full report:
{
  "runs": [
    {"scenario": "01-baseline-trigger", "outcome": "VULN_CONFIRMED", "detail": "..."},
    ...
  ]
}
```

---

## Hardening Verification (Post-Exploitation)

Once all 7 attacks are documented, enable Step 3:

```bash
./scripts/sandbox/run-step3-defensive.sh &
# Wait for "hardening enabled..."

# Re-run all attacks
cd redteam && for i in 0{1,2,3}; do
  ./$i-*.sh
done

# Compare: fewer VULN_CONFIRMED → hardening working
cat artifacts/sandbox/redteam-report.json | jq '.runs[] | select(.outcome | contains("VULN")) | .scenario'
```

**Hardening successful if**: Vulnerabilities drop from ≥4 to ≤1.

---

## Escalation Ladder

### Level 1: Single Bot (Current)
- 1 Anvil instance
- 1 dummy bot
- 7 sequential attacks
- **Runtime**: ~2 minutes

### Level 2: Concurrent Bots (Next)
- 3 bots racing each other
- Shared balance pool
- Dedup + replay detection
- **Runtime**: ~5 minutes

### Level 3: Network Stress (Advanced)
- 10+ bots on testnet RPC
- Proxy at 100 RPS
- Real gas costs
- Nonce contention
- **Runtime**: ~15 minutes

### Level 4: Hardware Attack (Future)
- Simulated network delays
- RPC latency injection
- Byzantine proxy responses
- **Runtime**: ~30 minutes

---

## Artifacts & Evidence

After battle, preserve:

```bash
# Evidence package
tar czf hexstrike-battle-$(date +%Y%m%d).tar.gz \
  artifacts/sandbox/{dummy-bot-events.jsonl,redteam-report.json,anomaly-alerts.jsonl}

# Analysis snapshot
python3 << 'PY'
import json, sys
report = json.load(open("artifacts/sandbox/redteam-report.json"))
for r in report["runs"]:
    print(f"{r['scenario']:30} → {r['outcome']:20} ({r.get('detail', '')[:60]})")
PY
```

---

## Success = Go Live

- [ ] All 7 attacks run without crash
- [ ] ≥4 vulnerabilities documented
- [ ] Baseline bot signs confirmed
- [ ] Hardening blocks ≥2 attack classes
- [ ] No race conditions in artifact logs
- [ ] Report JSON parses cleanly
- [ ] Team reviews battle report

Once checkboxes ✅, ready for **testnet deployment** (Step 2).

---

**Status**: 🔴 READY TO ENGAGE  
**Last Updated**: 2025-01-15  
**Next**: Monitor battle.log for victory conditions
