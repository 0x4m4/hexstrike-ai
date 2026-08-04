# Critical alert paging (operator-owned)

## Wiring (code)

| Path | Behavior |
| --- | --- |
| Python `append_alert` | jsonl + `alert_paging.maybe_page` |
| Go `Engine.OnCritical` | kill switch + async `alerting.PageCritical` |

## Env

```bash
export ALERT_PAGING_ENABLED=true
export ALERT_WEBHOOK_URL=https://hooks.slack.com/services/...   # Slack
# OR:
export ALERT_PAGERDUTY_KEY=<events-v2-integration-key>
export ALERT_PAGING_TIMEOUT_SEC=5
export ALERT_PAGING_SEVERITIES=critical,high
```

## Routed kinds (minimum)

`rpc_mismatch`, `direct_rpc_unavailable`, `BLOCK_COMPROMISED_FUNDER`, `post_sign_drift`, other `BLOCK_*`, `paging_drill`.

## Drill

```bash
export ALERT_PAGING_ENABLED=true
export ALERT_WEBHOOK_URL=...   # or ALERT_PAGERDUTY_KEY
python3 scripts/ops/paging_drill.py
# → alert_sent=true, result=PASS_PENDING_ACK
# After on-call ACK:
export PAGING_DRILL_ACK=true
python3 scripts/ops/paging_drill.py --record-ack
# expect result=PASS with ack_received=true
```

## Evidence for GO_LIVE §7

```json
{
  "result": "PASS",
  "alert_sent": true,
  "webhook_status": 200,
  "ack_received": true
}
```

- Screenshot / on-call ack of the test page  
- Confirm production webhook is not a personal sandbox forever
