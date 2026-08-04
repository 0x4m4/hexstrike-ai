# Battle Agent — Inspector Audit Response & Deployment Roadmap

**Date:** 2026-07-11  
**Current readiness:** 75/100  
**Target:** 100/100 battle deployment  
**Status:** Engineering confirmation for inspector handoff

---

## Executive decision: what ships first?

| Priority | Module | Rationale |
|----------|--------|-----------|
| **P0 (now)** | `internal/guard/limits.go` | Zero external deps; fixes semantics of threshold vs high-value escalation |
| **P1 (week 1)** | **Arkham/OSINT cache** (`internal/entity`) | Eliminates blind signing; async pre-warm; no mempool race dependency |
| **P2 (week 1–2)** | **EIP-1559 fee builder** (`internal/tx`) | Required before any mainnet broadcast path |
| **P3 (week 2)** | **Private relay abstraction** | Chain-specific: Ethereum → Flashbots; **BSC → Puissant/48Club** (not Flashbots) |
| **P4 (week 2–3)** | Battle suite hardening | Close 5 vuln + 2 defended gaps → 100/100 score |

### Inspector question: Flashbots Bundle Client **or** Arkham API first?

**Answer: Arkham/OSINT cache first.** Flashbots bundle client is **not** the correct first relay for our primary target chain (BSC).

Reasoning:

1. **Entity unidentified is a hard gate** — without address reputation, private relay only hides tx from mempool; it does not prevent sending rescue to a compromised funder or labeled exploit sink.
2. **Cache is hot-path safe** — `sync.Map` + artifact bootstrap (already in `artifacts/entity-id.json`) gives **0 ms** on race; HTTP enrichment runs in background `Prewarm()` before battle loop.
3. **Flashbots ≠ BSC** — field targets are BSC (`chain_id=56`). Puissant validator `0x484848…` is already in our graph. Bundle API must be **chain-aware** (`internal/relay/bsc_puissant.go` vs `internal/relay/flashbots.go`).
4. **EIP-1559 is prerequisite for relay** — bundles need correctly typed dynamic-fee txs; gas benchmark today is Legacy on Anvil.

We **do** commit to private relay in P3 — but only after entity gate + 1559 builder exist.

---

## Clarification: «≥0.501 ETH → bot idle»

Inspector item #3 conflates two different quantities:

| Quantity | Meaning in current code | Behavior |
|----------|-------------------------|----------|
| **Wallet balance** | `THRESHOLD_WEI = 0.5 ETH` | balance ≥ 0.5 → `THRESHOLD_OK` (healthy, no rescue) |
| **Rescue tx value** | `RESCUE_VALUE_WEI` (0.001–1 ETH in tests) | Separate policy via `EvaluateRescueValue()` |

Large wallet balance **should not** trigger rescue — that is correct safety semantics, not a missed critical save.

What we **will** add (implemented in `limits.go`):

- `HIGH_VALUE_ESCALATION` when **rescue native value** > 0.5 ETH → emit `security.high_value_pending` (KMS/multi-sig), not blind auto-sign.
- `THRESHOLD_OK` renamed from informal «idle» to avoid audit confusion.

---

## Inspector findings → engineering tasks

### 1. Entity OSINT (P1)

**Shipped (skeleton):** `cmd/agent/internal/entity/cache.go`

- `sync.Map` TTL cache
- Bootstrap from `artifacts/entity-id.json` (0 ms)
- Next: `ARKHAM_API_KEY`, Etherscan labels, blocklist for known exploit contracts
- Integration point: `guard` calls `entity.ShouldBlockSigning()` before `AUTO_SIGN_CLEAR`

### 2. Dynamic gas EIP-1559 (P2)

**Planned:** `cmd/agent/internal/tx/fees1559.go`

- `SuggestGasTipCap` + aggressive offset (+15–20% on critical)
- Port patterns from `src/hexstrike/core/execution/broadcaster.py`
- Replace Legacy `cast send` in rescue path

### 3. High-value escalation (P0 — shipped)

**Shipped:** `cmd/agent/internal/guard/limits.go` + tests

```go
rg := guard.NewRouteGuard()
rg.EvaluateBalance(balance)      // trigger path
rg.EvaluateRescueValue(value)    // escalation path
rg.EvaluateCombined(balance, value)
```

Benchmark alignment: 120/120 fork runs map 1:1 to `EvaluateBalance` cases.

### 4. Front-run / private relay (P3)

**Planned:** `cmd/agent/internal/relay/`

| Chain | Relay |
|-------|-------|
| Ethereum | Flashbots / MEV-Share |
| BSC | Puissant Builder API (48Club) |
| Anvil | Public RPC (test only) |

Rescue payloads submitted as **bundle**, not `eth_sendRawTransaction` to public mempool.

---

## Path 75 → 100 readiness

| Gap (battle suite) | Fix | Points |
|--------------------|-----|--------|
| 02 race duplicate sign | Nonce dedup / idempotency key | +5 |
| 03 front-run drain | Private relay + balance guard nonce check | +5 |
| 04 replay rescue | Tx hash dedup registry | +5 |
| 06 compromised funder | FUNDER allowlist + entity blocklist | +5 |
| Entity gate | OSINT cache block before sign | +5 |

Target score formula unchanged: `50 + vuln*3 + defended*5 - inconclusive*10` → need more **DEFENDED** and fewer **VULN**.

---

## Immediate next commits (engineer)

1. ✅ `internal/guard/limits.go` + tests
2. ✅ `internal/entity/cache.go` + tests (artifact bootstrap)
3. ✅ `internal/entity/gate.go` + bootstrap + Arkham HTTP client
4. ✅ `internal/tx/fees1559.go` + pure math tests
5. ✅ `internal/orchestrator/engine.go` — PrepareRescue pipeline (limits → gate → allowlist → dedup → fees)
6. Wire `PrepareRescue` into live signing path (Python parity / Go rescue signer)
7. ✅ P3: `internal/relay/` Puissant HTTP + public fallback + receipt watcher + Ollama prewarm

---

## Mainnet blind zones (inspector audit #2) — addressed

| # | Gap | Fix | Status |
|---|-----|-----|--------|
| 1 | Ollama 27s cold start blocks hot path | `LLM_ASYNC_ONLY=1` (default), `enqueue_llm_task()`, Go `async.LLMWorkQueue` | ✅ |
| 2 | Entity cache no TTL | `ValidUntil` + `ENTITY_CACHE_TTL_MINUTES` (default **15m**) | ✅ |
| 3 | Puissant no fallback | `internal/relay/` — live `eth_sendBundle`, explore poll, public `eth_sendRawTransaction` fallback | ✅ P3 wired |
| 4 | Revert does not clear dedup | `monitor.Watcher` + `HandleReceipt` + `Engine.ReleaseDedup` | ✅ |

### P3 production wiring (2026-07-11)

| Component | Path | Behavior |
|-----------|------|----------|
| Puissant HTTP | `internal/relay/client.go` | `eth_sendBundle` → `PUISSANT_BUILDER_URL` |
| Bundle status | `QueryBundleStatus` | `PUISSANT_EXPLORE_URL` poll until confirmed or timeout |
| Public fallback | `internal/relay/public.go` | `eth_sendRawTransaction` via `RELAY_PUBLIC_RPC` |
| Receipt watcher | `internal/monitor/watcher.go` | `eth_getTransactionReceipt` poll → `HandleReceipt` / `ReleaseDedup` |
| Ollama prewarm | `internal/async/prewarm.go` + `bootstrap.go` | Background `/api/tags` on `battle` start |

**Verify:** `python3 scripts/sandbox/run-p3-fork-verify.py`  
**Revert e2e:** `bash scripts/sandbox/test-revert-flow.sh`  
**Live loop e2e:** `bash scripts/sandbox/test-live-rescue-loop.sh`  
**Mainnet env:** `scripts/sandbox/mainnet.env.example` → copy to `mainnet.env` (gitignored)

### Ethereum relay (Flashbots)

| Component | Path | Behavior |
|-----------|------|----------|
| Flashbots client | `internal/relay/flashbots.go` | `eth_sendBundle` + `X-Flashbots-Signature` (reputation key) |

Env: `FLASHBOTS_RELAY_URL`, `FLASHBOTS_SIGNING_KEY`

### Direct answers

1. **Dedup on revert?** **Yes** — `Engine.HandleReceipt(dedupKey, success=false)` calls `ReleaseDedup`; retry allowed (`TestHandleReceiptRevertReleasesDedup`).
2. **Arkham TTL?** **15 minutes** safe entries (`ENTITY_CACHE_TTL_MINUTES`); blocked entries re-checked every **10 minutes** (still fail-closed until API clears).


| Question | Engineering answer |
|----------|-------------------|
| Flashbots first? | **No** — Arkham/entity cache + `limits.go` first |
| Flashbots at all? | **Yes** — Ethereum relay in P3; BSC uses Puissant |
| «Idle» on large balances? | **By design** (`THRESHOLD_OK`); escalation applies to **rescue value**, not wallet balance |
| ETA to 100/100? | P0–P2 land in Go agent; battle re-run after funder allowlist + dedup |

*Inspector audit accepted. P0 code in `cmd/agent/internal/`.*
