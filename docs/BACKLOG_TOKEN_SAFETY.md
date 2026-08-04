# Backlog: TokenSafetyChecker (Defense Gate)

**Status:** Backlog — do not implement until production rescue is live (Mac E2E → TOCTOU → `DRY_RUN=false`).

**Scope:** Future ERC-20 evacuation layer for `hexstrike-agent`. Not required for native BNB/ETH rescue to an allowlisted safe address.

**Out of scope:** MEV modules (sandwich, calldata frontrunning, mempool copying). Repository `AttackID` values (`01`–`07`) are **red-team sandbox scenarios**, not production attack software.

---

## Why this layer exists

Current rescue path transfers **native gas only** to `ALLOWED_FUNDERS`. Honeypot and poison-token risk is negligible.

When the contour expands to **ERC-20 evacuation**, a third defense layer is required after:

1. **Entity gate** — fail-closed screening (Arkham / cache TTL)
2. **Funder allowlist** — hard-coded safe destinations

```
PrepareRescue → entity gate → funder allowlist → [TokenSafetyChecker] → dedup → sign → relay → watcher
```

---

## Proposed interface

Location (future): `cmd/agent/internal/guard/token_safety.go`

```go
package guard

import (
	"context"
	"math/big"

	"github.com/ethereum/go-ethereum/common"
)

// TokenSafetyChecker validates token and router interactions before signing.
type TokenSafetyChecker interface {
	// CanReceive simulates whether the token can be moved/sold without trap behavior.
	CanReceive(ctx context.Context, token common.Address, amount *big.Int) (SafetyVerdict, error)

	// CanInteract validates router/contract calldata when swap or approve paths are enabled.
	CanInteract(ctx context.Context, to common.Address, calldata []byte) (SafetyVerdict, error)
}

// SafetyVerdict is the outcome of a defense-gate check.
type SafetyVerdict struct {
	Safe   bool
	Reason string // e.g. "honeypot: sell reverts", "poison: unknown router"
	Source string // e.g. "local_sim", "goplus", "honeypot_is", "allowlist"
}

// CompositeTokenSafety runs checks in order; first failure wins (fail-closed).
type CompositeTokenSafety struct {
	Checkers []TokenSafetyChecker
}
```

### Integration hook (future)

In `orchestrator.Engine.PrepareRescue`, when `RescueRequest` includes a token address:

- If `TokenAddress` is zero → skip checker (native transfer only).
- Else → `CanReceive` must return `Safe: true` or rescue is blocked.

---

## Data sources (three directions)

### 1. Local EVM simulation (`local_sim`)

Pre-flight fork call via `eth_call` on BSC RPC:

| Call | Purpose |
|------|---------|
| `transfer(to, amount)` | Detect transfer traps / blacklists |
| `approve(spender, amount)` | Detect approval hooks |
| Simulated sell on router | Detect honeypot (buy OK, sell reverts) |

**Pros:** No external dependency; works offline on Anvil fork.  
**Cons:** Slower; may miss novel trap patterns not exercised by the probe call.

**Implementation notes:**

- Use read-only `eth_call` with `from` = bot address, `to` = token contract.
- Optional: fork at latest block via local Anvil for router simulation.
- Fail-closed on RPC error or revert.

### 2. External APIs (`goplus`, `honeypot_is`)

Fast contract screening against known blacklist and trap signatures.

| Provider | Use case |
|----------|----------|
| **GoPlus Security API** | Honeypot flags, hidden mint, proxy risks, sell tax |
| **Honeypot.is** | BSC-specific honeypot detection |

**Pros:** Fast; broad coverage of known scams.  
**Cons:** Rate limits; false positives/negatives; network egress required.

**Implementation notes:**

- Cache results with TTL (align with `ENTITY_CACHE_TTL_MINUTES`).
- Treat API timeout as **unsafe** when `FailClosed=true` on mainnet.
- Never block native BNB rescue on API failure.

### 3. Hard allowlist (`allowlist`)

Whitelist of verified tokens only — default-safe path for v1 token rescue.

**BSC starter set (examples):**

| Token | Address |
|-------|---------|
| USDT | `0x55d398326f99059fF775485246999027B3197955` |
| USDC | `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d` |
| WBNB | `0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c` |

**Pros:** Zero false negatives for listed assets.  
**Cons:** Does not protect long-tail tokens; requires manual curation.

**Policy:** Unknown token → block unless `local_sim` and external API both pass.

---

## Checker composition (recommended order)

```
1. allowlist     → instant pass for USDT/USDC/WBNB
2. goplus        → quick external screen
3. honeypot_is   → BSC-specific second opinion
4. local_sim     → final eth_call sell/transfer probe
```

Fail-closed on mainnet. Sandbox (Anvil) may set `FailClosed=false` for lab tests.

---

## Acceptance criteria (when implemented)

- [ ] Native BNB rescue unchanged — checker skipped when no token address
- [ ] Known honeypot (lab fixture) → `Safe: false`, rescue blocked
- [ ] Allowlisted USDT → `Safe: true` without external API
- [ ] API timeout + `FailClosed=true` → rescue blocked for token path only
- [ ] Unit tests: `TestTokenSafety_*` in `cmd/agent/internal/guard/`
- [ ] Red-team scenario `08-honeypot-token-blocked` in sandbox (future)

---

## Dependencies and sequencing

| Step | Gate |
|------|------|
| Mac E2E + dry-run artifacts | Required before any token safety code |
| TOCTOU fix (dynamic fee refresh in `ResignRescueTx`) | Required before mainnet |
| `DRY_RUN=false` production rescue (native only) | Required before token rescue feature flag |
| This backlog → implementation | After production native rescue is stable |

---

## Engineer note (current sprint)

> MEV/attack modules — out of scope until production rescue is live.  
> Backlog: `TokenSafetyChecker` for future token rescue.  
> Now: Mac E2E → TOCTOU → GO.

**Waiting for artifacts:**

1. `artifacts/stress_test/live-rescue-loop-e2e.json`
2. Full output of `scripts/sandbox/test-live-rescue-loop.sh`
3. Last 20 lines of `deploy-mainnet.sh dry-run`

---

## References

- `cmd/agent/agent.go` — `AttackID` red-team scenarios (sandbox only)
- `cmd/agent/internal/orchestrator/engine.go` — `PrepareRescue` pipeline
- `cmd/agent/internal/guard/` — existing hardening guards
- `scripts/sandbox/mainnet.env.example` — `ALLOWED_FUNDERS`, entity gate
