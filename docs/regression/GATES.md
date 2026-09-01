# Regression gates (CI)

There are **3 gates**. All are **on demand** (Actions UI) and/or **cron**.  
They do **not** auto-run on every pull request.

| Gate | When | Purpose | Status |
|------|------|---------|--------|
| **A** | Actions UI + weekday cron | Fast offline judgement pack | ✅ |
| **B** | Actions UI + nightly cron | Live auth + IR action-list + domain + provision dry-run | ✅ |
| **C** | Actions UI (+ optional release event) | Full release pack + dashboard `run-summary` artifact | ✅ |

---

## How to trigger (GitHub UI)

1. Open repo → **Actions**
2. Pick workflow:
   - **Regression Gate A (on demand)**
   - **Regression Gate B (live)**
   - **Regression Gate C (release)**
3. Click **Run workflow** → choose branch / inputs → **Run workflow**
4. Open the run → logs + **Artifacts**

---

## Gate A — Fast offline

```bash
python3 regression/cli.py pr-bot run --env=epsilon --mode=smoke
```

Workflow: `.github/workflows/regression-pr-bot.yml`  
Triggers: `workflow_dispatch` + cron `0 6 * * 1-5` (weekdays 06:00 UTC)

---

## Gate B — Live

Requires credentials (env or `test-accounts.json`):

```bash
export REGRESSION_TASK_ID=27277459   # optional

python3 regression/cli.py gate-b run --env=epsilon --json-out=/tmp/gate-b.json
```

Workflow: `.github/workflows/regression-gate-b.yml`  
Triggers: `workflow_dispatch` + nightly cron  

### CI secrets
- `REGRESSION_USERNAME` / `REGRESSION_PASSWORD` (required for live)
- `REGRESSION_TASK_ID` (optional)

---

## Gate C — Release

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
| `gate_b_live` | If creds / `--require-live` | Skipped when no creds |
| `api_ir_subset` | Optional | `REGRESSION_API_IR_CMD` |
| `appium_ir_thin` | Optional | `REGRESSION_APPIUM_CMD` |

Workflow: `.github/workflows/regression-gate-c.yml`  
Triggers: `workflow_dispatch` (+ `release` published)
