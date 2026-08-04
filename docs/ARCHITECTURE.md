# HexStrike Evolution: Dummy → Hardened Agent

| Field | Value |
| --- | --- |
| Document | `docs/ARCHITECTURE.md` |
| Status | Living architecture (defense-in-depth) |
| Scope | Local Anvil rescue-bot lab → hardened bot + Go battle agent |
| Related | `docs/architecture/001-core-specification.md` (Samson production core) |
| Posture | **Risk-reduced architecture** — not “full protection” |

This document describes the **three-layer defense-in-depth** path from a vulnerable dummy bot to a hardened signing agent under adversarial tests. It is intentionally honest about gaps: Step 3 reduces risk; it does **not** claim complete protection.

---

## Threat Model & Assumptions

### Assets

| Asset | Why it matters |
| --- | --- |
| Hot-wallet private key / signer | Direct fund movement |
| Rescue / diversion destination | Attacker can redirect value |
| Nonce + pending TX pool | Replay / race surface |
| RPC truth (chain state) | Guards decide from this data |
| Alert + audit logs | Detection and forensics |

### Adversaries (lab)

1. **Proxy tamperer** — falsifies `eth_getBalance` / RPC responses on `:8546`.
2. **Mempool racer** — front-runs or bumps nonce around rescue TX.
3. **Compromised funder / destination** — controls where “rescue” value lands.
4. **Host / CI compromise** — reads keys from env or runner disk (out of band for Step 3).

### Assumptions (must hold for guards to help)

1. **Direct RPC** (`:8545` Anvil / trusted upstream) is not attacker-controlled.
2. Bot process can reach direct RPC independently of the proxy path.
3. Lab keys are Anvil defaults / ephemeral — never production mainnet keys.
4. Host OS, CI runner, and signer isolation are **out of scope** for Step 3 guards (see Known Gaps).

### Abuse cases

| Use case | Abuse case |
| --- | --- |
| Poll balance via proxy | Proxy returns fake low balance → false rescue |
| Sign rescue on threshold | Race: drain between check and broadcast |
| Replay rescue TX | Resubmit signed payload / duplicate nonce path |
| Fund recovery destination | Attacker-controlled funder/destination receives value |

---

## Trust Boundaries

```text
┌──────────────────────────────────────────────────────────────┐
│ TRUSTED (lab assumption)                                     │
│  • Anvil / direct RPC :8545 (truth source)                   │
│  • Guard decision code in hardened bot                       │
│  • Local alert/event logs written by bot                     │
└────────────────────────────▲─────────────────────────────────┘
                             │ direct RPC (out-of-band from proxy)
┌────────────────────────────┴─────────────────────────────────┐
│ UNTRUSTED                                                    │
│  • RPC interceptor / proxy :8546                             │
│  • Any operator-facing RPC path shared with attackers        │
│  • Mempool / peer network (race, front-run)                  │
│  • Destination / funder addresses until allowlisted          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ OUT OF BAND / SEPARATE TRUST DOMAIN                          │
│  • Host OS, shell, filesystem                                │
│  • CI runner + GitHub Actions secrets                        │
│  • Signer: AWS/GCP KMS SDK (SIGNER_BACKEND=kms) or remote   │
└──────────────────────────────────────────────────────────────┘
```

| Component | Trust | Notes |
| --- | --- | --- |
| Direct RPC `:8545` | Trusted (lab) | Truth source for G1/G3 |
| Proxy `:8546` | **Untrusted** | Logging only; may be tampered |
| Hardened bot process | Trusted code, untrusted host | Host compromise bypasses guards |
| Signer / key material | High-value | Must be isolated in production |
| CI runner | Untrusted for keys | Never inject mainnet keys into battle CI |

Crossing from untrusted proxy data into a sign decision **requires** G1 + G3 direct-RPC verification.

---

## Evolution Overview (ASCII)

```
╔════════════════════════════════════════════════════════════════════════════════╗
║         HEXSTRIKE EVOLUTION: DUMMY → HARDENED AGENT                            ║
║              Defense-in-depth / Risk-reduced architecture                        ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

### Step 1 — Dummy bot (vulnerable baseline)

```
Anvil :8545  →  DUMMY BOT (poll every 10s)
                  if balance < 0.5 ETH → SIGN & SEND (no checks)
```

Attacks that succeed: `01`…`06` (all `VULN`).

### Step 2 — RPC interceptor (monitoring only)

```
Anvil :8545 ← pass-through ← PROXY :8546 ← DUMMY BOT
```

Same six attacks still succeed. Gain: detectability via `rpc-interceptor.jsonl`.

### Step 3 — Defensive hardening (**risk-reduced**, not full protection)

```
Anvil :8545 (direct truth)
   ├─ G1 RPC mismatch check
   ├─ G2 anomaly check
   └─ G3 pre-sign verify
Proxy :8546 remains untrusted read path for polling only.
```

---

## Attack Status Matrix (authoritative)

| Test | Step 1 | Step 2 | Step 3 | Guard | Status notes |
| --- | --- | --- | --- | --- | --- |
| 01 Baseline Trigger | VULN | VULN | DEFENDED | G3 | Direct-RPC re-check before sign |
| 02 Race Duplicate | VULN | VULN | DEFENDED* | G1 (+ dedup backlog) | Proxy tamper path blocked; see Known Gaps for pure race |
| 03 Front-run Drain | VULN | VULN | DEFENDED* | G3 | Reduced; verify→sign→broadcast window remains |
| 04 Replay Rescue TX | VULN | VULN | DEFENDED* | G2 | Anomaly / nonce signals; not cryptographic replay protection |
| 05 TOCTOU Nonce | VULN | VULN | **PARTIAL** | G2 | Detects some races; full mitigation in § TOCTOU |
| 06 Compromised Funder | VULN | VULN | **DEFENDED*** | Allowlist + `GO_LIVE_GATES` / Go `destAllow[destination]` | **DEFENDED*** (risk-reduced under lab model): hardened path blocks funder/destination ∉ allowlist; legacy bot w/o gates remains VULN (battle baseline) |
| 07 Hardening Blocks | N/A | N/A | TEST | G1–G3 | Meta-test that guards fire |

\* **DEFENDED*** means **risk-reduced under the lab threat model**, not production-complete. Step 3 / DEFENDED* never alone authorize a production value path.

**Attack #06 — Compromised funder:** status is **`DEFENDED*` (risk-reduced under lab model)** on the hardened path (`ALLOWED_FUNDERS` / `ALLOWED_DESTINATIONS` + `GO_LIVE_GATES=true` / Go `RequireAllowlist` + `destAllow[destination]`). Do not mark `#06` as open/missing allowlist. Legacy dummy bot without gates remains VULN by design (battle baseline).

---

## Guard Specifications (G1 / G2 / G3)

Contract format for each guard: inputs → thresholds → decision → fail mode → FP handling.

### G1 — RPC mismatch check

| Field | Spec |
| --- | --- |
| Purpose | Detect proxy tampering vs direct truth |
| Inputs | `primary_balance` (proxy), `direct_balance` (direct RPC), `MAX_DELTA_WEI` |
| Threshold | Block if `abs(primary - direct) > MAX_DELTA_WEI` (lab default: `0`) |
| Pass | Continue to G2 |
| Fail | `block_signing` + alert `rpc_mismatch` |
| Fail-closed / fail-open | **Fail-closed** if direct RPC error → treat as `direct_rpc_unavailable` |
| False positives | Transient RPC skew; mitigate with short re-poll (≤2) before block; still fail-closed if unresolved |
| Does not cover | Destination allowlist, host key theft, mempool front-run after sign |

### G2 — Anomaly check

| Field | Spec |
| --- | --- |
| Purpose | Detect balance drop without corresponding on-chain activity |
| Inputs | `current_balance`, `current_nonce`, `last_balance`, `last_nonce` |
| Threshold | Block if `current_balance < last_balance` **and** `current_nonce == last_nonce` |
| Pass | Continue to G3 |
| Fail | `block_signing` + alert `anomaly_no_onchain_activity` |
| Fail-closed / fail-open | **Fail-closed** on missing prior state for first sample after restart (optional warm-up: allow N=1 observe-only) |
| False positives | External credit/debit from allowed ops; maintain allowlisted self-nonce bumps |
| Does not cover | Compromised destination; TOCTOU after this check |

### G3 — Pre-sign verify

| Field | Spec |
| --- | --- |
| Purpose | Final direct-RPC confirmation that rescue threshold still holds |
| Inputs | `direct_balance`, `RESCUE_THRESHOLD_WEI` |
| Threshold | Sign only if `direct_balance < RESCUE_THRESHOLD_WEI`; else block (false trigger) |
| Pass | Proceed to sign path (still subject to TOCTOU controls) |
| Fail | `block_signing` + alert `false_trigger_proxy` / threshold mismatch |
| Fail-closed / fail-open | **Fail-closed** on direct RPC error |
| False positives | Legitimate rapid drain below threshold — acceptable (prefer miss-sign over false-sign) |
| Does not cover | Post-sign / pre-broadcast races; funder allowlist |

### Combined decision

```text
trigger (proxy poll) → G1 → G2 → G3 → (TOCTOU controls) → sign → (recheck) → broadcast
ANY guard fail ⇒ BLOCK (fail-closed)
```

---

## TOCTOU Mitigation (verify-then-sign race window)

Problem: even with G1–G3, time passes between **verify** and **broadcast**. Attackers can drain, bump nonce, or front-run inside that window (tests `03`, `05`).

### Required controls (target state)

| Control | Behavior |
| --- | --- |
| Tx intent hash | Hash canonical `{to, value, data, chainId, nonce}` before sign; bind alerts to intent |
| Nonce reservation / lock | Process-local (lab) or distributed lock; no second sign for same nonce |
| Short validity window | Intent expires in `T_valid` (e.g. 2–5s lab; tighter in prod) |
| Post-sign recheck | Re-read direct balance + nonce **after** sign, **before** broadcast; abort if drift |
| Single-flight rescue | Mutex around entire rescue critical section |

### Minimal acceptable path (until full controls land)

1. Hold rescue mutex.  
2. G1 → G2 → G3.  
3. Reserve nonce.  
4. Sign.  
5. Direct-RPC recheck (balance + nonce).  
6. Broadcast or drop.  
7. Release mutex.

Status today: **PARTIAL → improving** — Go hot path wires `SecureSignRescue` (intent claim, nonce lock, TxSigner, post-sign recheck). Residual verify→broadcast race and ops soak remain; not production-complete.

---

## Scoring Model v2 (readiness)

Legacy model (`+10` defended / `+5` vuln / `-20` inconclusive) can **mask critical risk**. v2 adds hard blockers.

### Additive score (0–100)

| Event | Points |
| --- | --- |
| Attack DEFENDED | +10 |
| Attack VULN_CONFIRMED (non-critical) | +5 (finding credit) but see blockers |
| INCONCLUSIVE | −20 |
| Hardening meta-test PASS (`07`) | +10 |

### Critical blockers (zero deployability)

Any of the following forces **`deployability = NO-GO`** regardless of numeric score:

| Blocker ID | Condition |
| --- | --- |
| `BLOCK_COMPROMISED_FUNDER` | Production candidate runs ungated/legacy path, empty allowlist outside lab, or `#06` regression (`VULN_CONFIRMED` on hardened path). Hardened `#06` is **DEFENDED*** — not “NOT DEFENDED YET”. |
| `BLOCK_DIRECT_RPC_DOWN` | `direct_rpc_unavailable` during validation window |
| `BLOCK_GUARD_BYPASS` | Any path signs without G1–G3 in hardened mode |
| `BLOCK_MAINNET_KEYS` | Non-lab keys detected in env/CI for battle suite |

### Score interpretation

| Score | Blockers | Gate |
| --- | --- | --- |
| ≥ 70 | none | Conditional GO (staging) |
| ≥ 70 | any critical | **NO-GO** |
| 50–69 | none | NEEDS HARDENING |
| < 50 | — | NO-GO |

Exit code policy for Go agent (target):

- `0` — score ≥ 70 **and** no critical blockers  
- `2` — critical blocker present  
- `1` — score < 70 without critical blocker (or inconclusive-heavy)

---

## Known Gaps

| Gap | Impact | Direction |
| --- | --- | --- |
| Allowlist ops / gate discipline | `#06` is **DEFENDED*** on hardened path; risk returns if gates off, allowlist empty, or destination key check regresses | Keep `GO_LIVE_GATES` / `RequireAllowlist` mandatory outside lab; CI + review for allowlist drift |
| TOCTOU residual after `SecureSignRescue` | Race/front-run window shrinks but not zero | Enforce SecureSign on all value paths; soak + phase gates |
| Single direct RPC | Truth-source SPOF / eclipse | Multi-RPC quorum 2/3 |
| Proxy is pass-through only | No active response mutation defense beyond compare | Keep untrusted; never sign on proxy alone |
| Host / CI key exposure | Guards irrelevant if raw key stolen | Code: AWS/GCP KMS wired (`SIGNER_BACKEND=kms`); ops: IAM/policy, staging smoke, no mainnet keys in CI |
| Replay residual | Replay variants may slip if intent claim bypassed | Keep intent hash + `(intent, nonce, chainId)` claim on all sign paths |
| Alerting without paging SLO | Detection ≠ response | Webhook sink wired (`ALERT_*` / `alerting.PageCritical`); operator must configure URL + pass `paging_drill.py` — see `docs/ops/PAGING-ONCALL.md` |
| Samson vs HexStrike sandbox docs | Two stacks | Cross-link core spec; do not conflate ports/roles |
| SMS OTP as auth factor | Breaks at network / carrier / device / radio | See `docs/intel/SMS-2FA-THREAT-MODEL.md` — prefer WebAuthn/passkeys |

---

## Security Invariants

These must remain true in hardened mode:

1. **No sign on proxy-only data** — G3 direct-RPC required.  
2. **Fail-closed on direct RPC errors** — no rescue broadcast.  
3. **Any guard failure blocks** — no override flag in production builds.  
4. **Lab keys only in Anvil / `GO_LIVE_PHASE=lab`** — `local_key` forbidden outside lab; canary/limited require KMS/remote.  
5. **Destination policy (`#06` DEFENDED*)** — `ALLOWED_DESTINATIONS` / `destAllow[destination]` + non-empty allowlist required outside lab; ungated legacy path remains VULN by design.  
6. **Signer backend** — production value path uses `SIGNER_BACKEND=kms` (AWS/GCP SDK) or remote; fail-closed without cloud config.  
7. **Auditability** — every block/sign writes structured events (`dummy-bot-events.jsonl`, `anomaly-alerts.jsonl`).  
8. **Trust boundary** — proxy traffic never becomes sole truth source.

---

## Operational Runbooks

### Alert severity matrix

| Alert | Severity | Immediate action | Escalate if |
| --- | --- | --- | --- |
| `rpc_mismatch` | **critical** | Block signing (already); isolate proxy; capture both balances | Repeats >3 / 5min |
| `direct_rpc_unavailable` | **critical** | Fail-closed; page on-call; do not fail-open | >60s downtime |
| `anomaly_no_onchain_activity` | **high** | Block signing; freeze rescue; review txs | Confirmed drain |
| `false_trigger_proxy` | medium | Keep blocked; inspect proxy logs | Correlated with mismatch |
| repeated INCONCLUSIVE tests | medium | Fix harness/flakes before score trust | Blocks release |

### Runbook: `rpc_mismatch`

1. Confirm hardened bot blocked (no TX).  
2. Diff `primary_wei` vs `direct_wei` from alert.  
3. Restart/replace proxy; verify direct Anvil healthy.  
4. Preserve `rpc-interceptor.jsonl` + `anomaly-alerts.jsonl`.  
5. Re-run `07-hardening-blocks-tamper` before resume.

### Runbook: `direct_rpc_unavailable`

1. Keep fail-closed (do not route truth through proxy).  
2. Check Anvil/process, port `:8545`, disk/FD limits.  
3. Restore direct RPC; warm G2 state.  
4. Resume only after G1–G3 smoke + battle subset.

### Runbook: repeated anomaly

1. Halt autonomous rescue.  
2. Export balances/nonces timeline.  
3. If real drain: rotate lab keys, reset Anvil, open incident.  
4. File gap if anomaly FP storm (tune warm-up / allowlist self-ops).

### SLO targets (lab → staging)

| Metric | Target |
| --- | --- |
| MTTD (mismatch → alert log) | ≤ 10s |
| MTTR (critical alert → signing safe state confirmed) | ≤ 15 min (lab), ≤ 30 min (staging) |
| Fail-closed on direct RPC outage | 100% (no signed rescue) |
| Battle suite flake rate | < 5% inconclusive |

---

## Production Controls (beyond Step 3)

Required before any non-lab value path. Step 3 / **DEFENDED*** do **not** mean production-complete.

| Control | Spec |
| --- | --- |
| Signer isolation | See **Key management (§4)** below |
| Key rotation | Scheduled + emergency rotate; revoke old material |
| Rate limits | Max rescue attempts / window; cooldown after block |
| Budget caps | Max value per TX and per rolling window |
| Multi-RPC quorum | ≥3 endpoints; proceed only on **2/3** agreement for balance/nonce |
| Destination allowlist | `#06` **DEFENDED*** — enforce/maintain `ALLOWED_*` + `RequireAllowlist`; unsigned if `to` not allowlisted |
| CI separation | Battle CI uses Anvil only; no production secrets |

### Key management (§4)

| Item | Status |
| --- | --- |
| Code-gap (AWS/GCP KMS SDK) | **Closed** — `SIGNER_BACKEND=kms` → `signer.NewFromEnv` wires AWS SDK v2 (`AWS_KMS_KEY_ID`, `AWS_REGION`) or GCP Cloud KMS (`KMS_PROVIDER=gcp`, `GCP_KMS_KEY_NAME`); DER→eth in `eth_sig.go` |
| Fail-closed | Missing cloud config → error; `local_key` only in `GO_LIVE_PHASE=lab` |
| Operator-owned (remaining) | KMS IAM/policy audit, staging smoke with real credentials, paging for signer denials |

---

## Readiness Gates (Go / No-Go)

| Gate | GO requires | NO-GO if |
| --- | --- | --- |
| G-Lab | Steps 1–3 runnable; artifacts written | Harness broken |
| G-Score | Score ≥ 70 under v2 | Score < 70 |
| G-Critical | No critical blockers | Any `BLOCK_*` |
| G-Allowlist | `#06` **DEFENDED*** (risk-reduced under lab model) + destination/funder regression tests | Ungated legacy path, empty allowlist outside lab, or `#06` regression |
| G-TOCTOU | `SecureSignRescue` (intent claim + post-sign recheck) on value path | Sign/broadcast without recheck |
| G-KMS | `SIGNER_BACKEND=kms` (or remote) outside lab; no raw key in prod env | `local_key` / raw `BOT_PRIVATE_KEY` outside lab |
| G-RPC | Quorum 2/3 in staging/prod design | Single RPC as sole truth in prod |
| G-Ops | Runbooks + alert sinks / paging wired | Alerts only to local jsonl |

**Staging GO:** G-Lab + G-Score + G-Critical + G-Ops (+ G-KMS config smoke).  
**Production GO:** all gates, including G-Allowlist, G-TOCTOU, G-KMS, G-RPC, production controls + operator-owned §4 leftovers.

---

## Flow Example: Proxy Tamper → Block

```text
t=0  Attacker forges proxy getBalance → 0
t=1  Bot trigger on proxy read
t=2  G1: proxy 0 vs direct 10 → BLOCK (rpc_mismatch)
t=3  Alert critical + bot event action=blocked
t=4  No TX signed
```

Without hardening: sign → attacker wins.  
With Step 3: risk-reduced block + alert (still subject to Known Gaps).

---

## Go Agent Orchestration

`hexstrike-agent` (Go):

1. Verify prerequisites (`anvil`, `cast`, `python3`, `bash`).  
2. Setup `artifacts/` + Anvil env.  
3. Run attacks `01`…`07` sequentially.  
4. Classify: `VULN_CONFIRMED` | `DEFENDED` | `INCONCLUSIVE` | `NOT_DEFENDED_YET`.  
5. Score with **v2** (additive + critical blockers).  
6. Emit `artifacts/sandbox/battle-report.json` + console report.  
7. Exit: `0` GO, `1` needs hardening, `2` critical blocker.

---

## Deployment Strategy

```text
Step 1 Baseline (dev smoke) → Step 2 Monitoring (staging detect)
    → Step 3 Hardened (risk-reduced defend) → Production controls (GO gates)
```

Do **not** label Step 3 as production-complete. Production requires § Production Controls + all Readiness Gates.

### Git workflow (battle agent)

1. PR with sandbox changes.  
2. CI runs agent on push.  
3. Agent comments score + blockers.  
4. Merge only if exit `0` (score + no critical blockers).  

---

## Comparison Table (corrected)

| Test | Step 1 | Step 2 | Step 3 | Guard |
| --- | --- | --- | --- | --- |
| 01 Baseline | VULN | VULN | DEFENDED | G3 |
| 02 Race duplicate | VULN | VULN | DEFENDED* | G1 |
| 03 Front-run | VULN | VULN | DEFENDED* | G3 |
| 04 Replay | VULN | VULN | DEFENDED* | G2 |
| 05 TOCTOU nonce | VULN | VULN | **PARTIAL** | G2 + `SecureSignRescue` (residual window) |
| 06 Compromised funder | VULN | VULN | **DEFENDED*** | Allowlist + destination key check — **DEFENDED*** (risk-reduced under lab model) |
| 07 Hardening blocks | N/A | N/A | TEST PASS | G1–G3 |

Illustrative scores: Step 1 ~20 · Step 2 ~20 · Step 3 ~60–75. **`#06` = DEFENDED*** on hardened path. **Prod still NO-GO** until remaining Critical/operator gates in `docs/GO_LIVE_CHECKLIST.md` (quorum soak, phase canary, paging, §4 IAM/staging smoke). Step 3 / DEFENDED* ≠ production-complete. KMS **code-gap closed** (AWS/GCP SDK); operator-owned leftovers remain.

---

## Document History

| Version | Change |
| --- | --- |
| 1.x | ASCII evolution narrative; overstated “FULL PROTECTION”; `06` marked defended inconsistently |
| 2.0 | Defense-in-depth wording; trust boundaries; G1–G3 contracts; TOCTOU; scoring v2; Known Gaps; runbooks/SLO; readiness gates |
| 2.1 | Attack `#06` hardened path = `DEFENDED*`; comparison table synced; Known Gaps updated; prod NO-GO tied to remaining Critical gates |
| 2.2 | Post PR #49: `#06` unified **DEFENDED***; Known Gaps = allowlist ops (not “missing”); §4 KMS code-gap closed + operator-owned leftovers; G-KMS + invariants synced |
