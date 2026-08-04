# Monitor Combat Readiness — Hot Wallet IR

**Target:** `0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA`  
**IR trigger:** unsigned pending **outflow** from hot wallet → `HOT_WALLET_OUTFLOW` alert (`ir_trigger: true`)

## What the monitor does

| Check | Implementation |
|-------|----------------|
| Mempool (pending) | `txpool_content` every ~2s |
| Block fallback | `eth_getBlockByNumber(latest)` every `MONITOR_BLOCK_SCAN_POLLS` (default 60) |
| Heartbeat | `[HEARTBEAT]` log every `MONITOR_HEARTBEAT_POLLS` (default 30) |
| Outflow filter | `from == hot_wallet` AND (value > 0 OR contract input) |
| Inflow / unrelated | Ignored |
| Reorg / tx vanish | `seen_hashes` — no repeat alert; vanish ≠ IR |
| Rescue owner | **Manual** — see `INCIDENT-CONCLUSION.md` |

## Sanity checks (operator)

### Mac

```bash
cd /Volumes/Eva/mufasaai-storage/hexstrike-ai
source scripts/forensics-env-mac.sh
export MONITOR_HEARTBEAT_POLLS=5 MONITOR_READINESS_SAMPLE_SEC=25
bash scripts/monitor-combat-readiness.sh
```

### Server

```bash
cd /opt/hexstrike-ai
source scripts/forensics-env-vps.sh
export MONITOR_HEARTBEAT_POLLS=5 MONITOR_READINESS_SAMPLE_SEC=25
bash scripts/monitor-combat-readiness.sh
```

### Latency probe (optional)

Send a **small test tx from a different wallet** (not hot wallet). Monitor should **not** emit `HOT_WALLET_OUTFLOW`. Compare block timestamp vs first log line if testing hot-wallet path on testnet only.

## Risk zones

1. **Gnosis Safe / proxy** — `from` may be module/relayer; extend filters if wallet type changes.
2. **Flashbots / private order flow** — mempool blind; block scan is the fallback (seconds later).
3. **Nonce gap / bundles** — each pending tx evaluated; bundle semantics need human IR review.
4. **RPC rate limit** — use fallbacks in `config/rpc_config.json`; rotate `RPC_URL`.

## IR readiness (pre-staged)

- [ ] Rescue owner script: non-interactive sign, nonce synced
- [ ] Aggressive gas (priority fee) pre-calculated
- [ ] Secondary RPC exported (`RPC_URL_FALLBACK`)
- [ ] Single monitor instance (`pgrep -af autonomous_monitor`)

## Alert paths

- `artifacts/alerts.log` — all alerts
- `artifacts/pending_action.json` — last IR-relevant action with `recommended_actions`

## Verdict

**Green zone** when readiness script exits 0 **and** production log shows regular `[HEARTBEAT]` + mempool/block scans.  
**Critical question:** do you see **pending outflow before confirmation**? That is the only window that matters.
