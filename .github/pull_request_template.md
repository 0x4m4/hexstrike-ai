## Go-Live Impact

- [ ] This PR does **not** reduce existing security controls.
- [ ] If touching tx/sign/broadcast paths, [`docs/GO_LIVE_CHECKLIST.md`](../docs/GO_LIVE_CHECKLIST.md) reviewed.

## Critical Gates (must pass)

- [ ] Allowlist enforcement (`destination` + `funder`)
- [ ] TOCTOU controls (intent hash, nonce lock, post-sign recheck, single-flight)
- [ ] Replay binding/dedup
- [ ] KMS/HSM/remote signer only (no raw key in env/CI)
- [ ] Multi-RPC quorum (no single-RPC truth)
- [ ] Tx limits + kill switch

## Evidence

- Tests:
- Logs/artifacts:
- Risk notes:
