# Regression gates (CI)

There are **3 gates**. Gate A is the PR bot. Gate B is live nightly/manual. Gate C is release.

| Gate | When | Purpose | Status |
|------|------|---------|--------|
| **A** | Every PR | Fast offline judgement + PR comment | ✅ Live on PR bot workflow |
| **B** | Nightly / `workflow_dispatch` | Live auth + IR action-list + domain + provision dry-run | ✅ Implemented |
| **C** | Release / `workflow_dispatch` | Full release pack + dashboard `run-summary` artifact | ✅ Implemented |

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

## Gate C — Release

Composes release layers and emits a dashboard-oriented artifact:

```bash
python3 regression/cli.py gate-c run --env=epsilon \
  --json-out=/tmp/gate-c.json \
  --summary-out=/tmp/regression-release-summary.json \
  --markdown-out=/tmp/gate-c.md
```

### Layers
| Layer | Required? | Notes |
|-------|-----------|--------|
| `gate_a_pr_bot_smoke` | Yes | Offline Gate A pack |
| `domain_parity_cat1` | Yes | Android CAT1 count lock |
| `gate_b_live` | If creds / `--require-live` | Skipped (not failed) when no creds |
| `api_ir_subset` | Optional | Enable via `REGRESSION_API_IR_CMD` |
| `appium_ir_thin` | Optional | Enable via `REGRESSION_APPIUM_CMD` |

Skipped optional layers do **not** fail the release pack. Failed required layers do.

### Artifacts
- `regression-gate-c.json` — full Gate C report  
- `regression-release-summary.json` — `schemaVersion: 1.0` run-summary with `repo: regression` + `regression_platform` block  
- `regression-gate-c.md` — human summary  

### CI secrets (optional extras)
- `REGRESSION_API_IR_CMD` — shell command for API IR Maven/subset  
- `REGRESSION_APPIUM_CMD` — shell command for thin Appium IR  

Workflow: `.github/workflows/regression-gate-c.yml`  
UI: **Actions → Regression Gate C (release) → Run workflow**
