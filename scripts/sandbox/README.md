# HexStrike Sandbox — RPC Bot Testing

Local-only sandbox for defensive research: dummy signing bot, transparent RPC interceptor, multi-source balance hardening.

**Not for production.** Uses Anvil public test keys only.

---

## Requirements

| Tool | Purpose |
|------|---------|
| [Foundry](https://book.getfoundry.sh/getting-started/installation) (`anvil`, `cast`) | Local chain + tx signing |
| Python 3.10+ | Bot, interceptor, guards |
| `pip install -r scripts/sandbox/requirements-sandbox.txt` | Auto-installed by run-step2/3 into `.venv` |

---

## First-time setup

```bash
# 1. Install Foundry (Mac)
curl -L https://foundry.paradigm.xyz | bash && foundryup

# 2. Create local env (gitignored — contains test keys)
./scripts/sandbox/setup-anvil-env.sh
```

- `anvil.env.example` — template with placeholders (safe to commit)
- `anvil.env` — your local file with Anvil test keys (**gitignored**)

---

## Run steps

### Step 1 — Baseline bot (direct Anvil)

```bash
./scripts/sandbox/run-step1.sh
```

Bot polls `eth_getBalance` every 10s. Signs rescue tx when balance < threshold.

### Step 2 — Transparent logging proxy

```bash
./scripts/sandbox/run-step2.sh
```

Traffic: `bot → :8546 interceptor → :8545 Anvil` (no response modification).

### Step 3 — Defensive hardening

```bash
./scripts/sandbox/run-step3-defensive.sh
```

Multi-RPC validation, anomaly guard, pre-sign verify on direct Anvil.

---

## Manual / smoke test

```bash
./scripts/sandbox/start-anvil.sh
./scripts/sandbox/setup-anvil-env.sh
source scripts/sandbox/anvil.env

# Single poll cycle (CI-friendly)
python3 scripts/sandbox/dummy_bot.py --once --dry-run

# Simulate low balance
./scripts/sandbox/set-balance.sh $BOT_ADDRESS 300000000000000000
```

---

## Artifacts

| File | Content |
|------|---------|
| `artifacts/sandbox/dummy-bot-events.jsonl` | Bot poll/trigger/block events |
| `artifacts/sandbox/rpc-interceptor.jsonl` | Proxied JSON-RPC calls |
| `artifacts/sandbox/anomaly-alerts.jsonl` | Hardening alerts (Step 3) |

Logs rotate automatically at **5 MB** (`SANDBOX_LOG_MAX_BYTES` to override).

Clean manually:

```bash
rm -f artifacts/sandbox/*.jsonl artifacts/sandbox/*.jsonl.1
```

---

## Stop services

```bash
./scripts/sandbox/stop-interceptor.sh
./scripts/sandbox/stop-anvil.sh
```

---

## Signing backends

1. **Foundry `cast`** (preferred) — no extra setup
2. **`eth-account`** (optional) — installed via `requirements-sandbox.txt` if `cast` missing

---

## Env variables (anvil.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `RPC_URL` | `:8545` or proxy | Bot-facing RPC |
| `DIRECT_RPC_URL` | `:8545` | Truth source for hardening |
| `THRESHOLD_WEI` | 0.5 ETH | Rescue trigger |
| `HARDENING_ENABLED` | `false` | Enable Step 3 guards |
| `MAX_BALANCE_DELTA_WEI` | `0` | Allowed proxy vs direct delta (0 = exact) |
| `ANOMALY_STALE_TIMEOUT_SEC` | `120` | Skip anomaly check if state is stale |
| `GUARD_RPC_TIMEOUT_SEC` | `10` | Direct RPC timeout for guards |
| `DRY_RUN` | `false` | Log only, no signing |

---

## Security notes

- Never commit `anvil.env` or `.venv/` (both gitignored)
- Anvil keys are public Foundry defaults — local sandbox only
- Interceptor is **read-only** — no RPC response falsification in this sandbox
