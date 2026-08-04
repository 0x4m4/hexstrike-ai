# KMS IAM / Policy Hardening (operator-owned)

Fail-closed goal: only the runtime principal can **Sign** + **GetPublicKey** on the secp256k1 key used by `SIGNER_BACKEND=kms`.

## AWS

1. Create ECC_SECG_P256K1 key (sign/verify). Enable **automatic key rotation** where supported; document rotation runbook if not.
2. Attach `docs/ops/iam/aws-kms-signer-policy.json` to the **task role / instance profile** only (replace REGION/ACCOUNT/KEY).
3. Key policy: remove broad principals (`*`, human admin IAM users). Admins use break-glass role with MFA + CloudTrail review.
4. Enable **CloudTrail** data events for `kms.amazonaws.com` (Sign, GetPublicKey) → SIEM / audit trail.
5. Deny `kms:CreateGrant` to signer role (see Deny statement in policy JSON).
6. Optional: VPC endpoint for KMS; no public internet egress for signer.

**Evidence to attach:** key ARN, IAM policy JSON (redacted), CloudTrail sample Sign event, list of principals on key policy.

## GCP

1. Create key with algorithm **EC_SIGN_SECP256K1_SHA256** (or org-approved secp256k1 sign).
2. Create custom role from `docs/ops/iam/gcp-kms-signer-role.yaml`; bind **only** to runtime SA.
3. No user accounts with `cloudkms.admin` on the keyring in prod; break-glass group with just-in-time elevation.
4. Enable **Data Access audit logs** for Cloud KMS (ADMIN_READ + DATA_WRITE) → Cloud Logging sink.
5. Prefer Workload Identity; avoid long-lived JSON keys. If JSON key exists → rotate and delete.

**Evidence to attach:** key resource name, IAM binding screenshot/CLI output, audit log sample AsymmetricSign.

## Rotation & revoke

| Event | Action |
| --- | --- |
| Scheduled | New key version → update `AWS_KMS_KEY_ID` / `GCP_KMS_KEY_NAME` + `SIGNER_ADDRESS` → smoke → retire old |
| Suspected compromise | Disable key / destroy version schedule → engage kill switch → page on-call |
| Principal offboarding | Remove IAM binding same day; verify audit |

## Checklist (§4 auditable)

- [ ] Least-privilege policy applied (templates above)
- [ ] No extra principals on key
- [ ] Audit trail enabled and sampled
- [ ] Rotation procedure documented + owner named
