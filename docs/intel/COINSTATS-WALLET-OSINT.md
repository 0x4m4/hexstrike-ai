# CoinStats Wallet OSINT (Samson)

| Field | Value |
| --- | --- |
| Module | `samson/redteam/coinstats_client.py` |
| CLI | `coinstats-wallet` |
| Auth | `X-API-KEY` via `SAMSON_COINSTATS_API_KEY` / `COINSTATS_API_KEY` |
| Official docs | https://coinstats.app/docs/authentication.md · https://coinstats.app/api-docs/wallet/other-chains/ |

**Policy:** public address read-only OSINT / monitoring. No private keys, no signing, no drain.

## Endpoints used

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/wallet/blockchains` | Supported chains |
| GET | `/wallet/balance?address=&connectionId=` | Token balances |
| PATCH | `/wallet/transactions?address=&connectionId=` | Sync index |
| GET | `/wallet/transactions?address=&connectionId=` | Tx history |
| GET | `/wallet/defi?address=&connectionId=` | DeFi positions (optional) |

Base URL: `https://api.coinstats.app/v1`

## CLI

```bash
export SAMSON_COINSTATS_API_KEY=...
python3 samson/orchestrator.py migrate

# list chains
python3 samson/orchestrator.py coinstats-wallet --list-chains

# balance snapshot
python3 samson/orchestrator.py coinstats-wallet \
  --address 0x28C6c06298d514Db089934071355E5743bf21d60 \
  --connection-id ethereum

# with txs + defi
python3 samson/orchestrator.py coinstats-wallet \
  --address TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH \
  --connection-id tron \
  --include-tx --include-defi --json
```

## Persistence

- Table: `coinstats_wallet_artifacts` (migration `010`)
- Non-empty wallets mirrored into `web3_recon_artifacts` for correlation with Arkham/guardrail
- Postgres cache TTL: `SAMSON_COINSTATS_CACHE_TTL_SEC` (default 86400)

## Credits (approx., per CoinStats docs)

| Call | Credits |
| --- | --- |
| blockchains | 1 |
| balance | 40 |
| tx sync | 50 |
| tx get | 30 |
