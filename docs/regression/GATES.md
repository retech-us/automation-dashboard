# Regression gates (CI)

There are **3 gates**. Gate A is the PR bot. Gate B is live nightly/manual. Gate C is release.

| Gate | When | Purpose | Status |
|------|------|---------|--------|
| **A** | Every PR | Fast offline judgement + PR comment | ✅ Live on PR bot workflow |
| **B** | Nightly / `workflow_dispatch` | Live auth + IR action-list + domain + provision dry-run | ✅ Implemented |
| **C** | Release | Full IR + API + thin Appium + dashboard artifact | Pending |

---

## Gate A — PR (fast)

```bash
python3 regression/cli.py pr-bot run --env=epsilon --mode=smoke
```

Workflow: `.github/workflows/regression-pr-bot.yml`

---

## Gate B — Merge / Nightly (live)

Requires credentials (env or `test-accounts.json`):

```bash
# Auto-discover Intelligent Reset task with actions, or:
export REGRESSION_TASK_ID=27277459   # optional override

python3 regression/cli.py gate-b run --env=epsilon --json-out=/tmp/gate-b.json
```

Optional mutate (non-prod only; needs IDs):

```bash
python3 regression/cli.py gate-b run --env=epsilon --task-id=... \
  --store-id=... --pog-id=... --execute
```

### Steps
1. `resolve_env`
2. `auth_smoke` (required — no skip)
3. `discover_task` (IR with action-list, or `--task-id` / `REGRESSION_TASK_ID`)
4. `action_list_live` + contract assert
5. `domain_transform_live` (count report; not CAT1 fixture)
6. `provision_dry_run` (always); `provision_execute` only with `--execute`

### CI secrets
- `REGRESSION_USERNAME` / `REGRESSION_PASSWORD` (required)
- `REGRESSION_TASK_ID` (optional)
- `REGRESSION_STORE_ID` / `REGRESSION_POG_ID` (only if enabling execute later)

Workflow: `.github/workflows/regression-gate-b.yml`  
UI: **Actions → Regression Gate B (live) → Run workflow**

---

## Gate C — Release (not started)

Full IR suite + API IR subset + thin Appium + unified dashboard PASS/FAIL artifact.
