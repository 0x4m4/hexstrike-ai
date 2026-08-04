# Branch protection: require `policy-gate`

After merging PR #46, a repo admin should enable:

```bash
gh api -X PUT repos/Banda198565/hexstrike-ai/branches/master/protection \
  -H "Accept: application/vnd.github+json" \
  -f required_status_checks='{"strict":true,"contexts":["policy-gate"]}' \
  -F enforce_admins=true \
  -F required_pull_request_reviews='{"required_approving_review_count":1}' \
  -F restrictions=null \
  -F allow_force_pushes=false \
  -F allow_deletions=false
```

If GitHub shows the check as `gate` (job name) rather than `policy-gate` (workflow name), use the exact name from the Checks UI — currently the check run name is **`gate`** under workflow **`policy-gate`**. Prefer renaming the job to `policy-gate` for a stable required-check name:

```yaml
jobs:
  policy-gate:
    name: policy-gate
```

Then set required context to `policy-gate`.
