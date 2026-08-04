# Mainnet deployment order (BSC rescue loop)

**Ref:** commit `050dd5f` — External Funder, 3/3 wallet roles closed.

## Wallet map (no Target private key)

| Role | Address | Key |
|------|---------|-----|
| TARGET (watch) | `0x96B23C4680E1a37cE17730e6118D0C9223e72A66` | none |
| BOT (signer+gas) | `0x85dB346BE1d9d5D8ec4F57acf0067FbE53a6E846` | `BOT_PRIVATE_KEY` |
| SAFE | `0x060447dC91dfb22A5233731aF67E9E8dafdF24d1` | none |

## Quick deploy (script)

```bash
chmod +x scripts/sandbox/deploy-mainnet.sh
./scripts/sandbox/deploy-mainnet.sh setup
# edit .env — paste BOT_PRIVATE_KEY locally
./scripts/sandbox/deploy-mainnet.sh dry-run
# set DRY_RUN=false in .env
./scripts/sandbox/deploy-mainnet.sh start
./scripts/sandbox/deploy-mainnet.sh logs
```

## Manual steps (equivalent)

### Step 1 — Production config

```bash
cp scripts/sandbox/mainnet.env.example .env
# Fill TARGET_WATCH_ADDRESS, ALLOWED_FUNDERS, BOT_ADDRESS, BOT_PRIVATE_KEY
```

### Step 2 — Dry-run validation

```bash
export $(grep -v '^#' .env | xargs)
DRY_RUN=true python3 scripts/sandbox/dummy_bot.py --once --dry-run
```

Expect: `[CORE] Engine started (DRY_RUN)` and RPC OK on BSC.

### Step 3 — Live daemon

```bash
set -a && source .env && set +a
mkdir -p logs
DRY_RUN=false nohup python3 scripts/sandbox/dummy_bot.py >> logs/mainnet-prod.log 2>&1 &
```

### Step 4 — Watch logs

```bash
tail -f logs/mainnet-prod.log
```

## Build Go agent (optional — sandbox battle suite)

```bash
cd cmd/agent && go build -o ../../bin/hexstrike-agent .
./bin/hexstrike-agent battle -v   # Anvil sandbox only, not mainnet watch loop
```

Mainnet **rescue watch loop** = `dummy_bot.py` + `.env` above.
