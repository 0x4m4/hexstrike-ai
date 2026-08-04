# Draft — OVH Abuse (BSC Geth RPC node)

**To:** abuse@ovh.ca  
**Subject:** Information — publicly reachable Geth JSON-RPC on 51.222.42.220:8545

---

Hello OVH Abuse Team,

This is an informational **passive disclosure** regarding a host in your network. No scanning beyond standard connectivity checks and read-only RPC methods was performed.

## Summary

| Field | Value |
|-------|-------|
| IP | 51.222.42.220 |
| Service | Geth JSON-RPC (:8545) |
| Observed behavior | Read-only methods; no `personal_*` / unlock exposed |
| Risk | Information disclosure, resource abuse if left public |

## Context

The node appears to serve BSC (BNB Chain) JSON-RPC. External connections may be filtered (connection reset from some networks). If publicly reachable, we recommend the tenant:

1. Firewall `:8545` to application subnets only.
2. Disable wallet/unlock/admin namespaces on the RPC surface.
3. Never store private keys on the node filesystem.

## Attachments

- `defensive-audit-template.md` — Geth/RPC hardening section

## Scope

- We do **not** assert a verified link between this IP and any specific on-chain wallet.
- No exploitation attempted.

Please forward to the customer security contact if appropriate.

## Contact

[Your name]  
[Your email]

Thank you.
