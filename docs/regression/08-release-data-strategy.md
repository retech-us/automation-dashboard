# 08 — Release Data Strategy

## Problem

Static mocks do not validate release behavior. We need **deterministic, controllable, production-like** data on a real (non-prod) tenant.

## How Release Data Enters Today

| Mechanism | Where | Class |
|-----------|-------|-------|
| factory-boy factories | Django `apps/*/factories.py` | CONTROLLED |
| Sparse JSON fixtures | compliance fixtures | CONTROLLED |
| Live task provisioning | MBIT adapters + runner_server + API IR tests | REAL/CONTROLLED |
| Bay scan JPG fixtures | `test-data/images/*` uploaded for real | CONTROLLED bytes → REAL pipeline |
| Tenant DB restore | ops README restore | REAL dump |
| Constance flags | per-tenant DB | CONTROLLED profile |
| Web scan-upload CI job | retech-web-automation | REAL provisioning |
| Local mock server | MBIT `backend/simulator` | MOCKED |

## Target Provisioning Flow

```text
Scenario
  → Required Data Definition (YAML)
  → Data Provisioner
  → Auth as test user
  → Ensure shift/store
  → Create/select TaskDef (IR enabled)
  → Create/claim Task occurrence
  → Upload controlled bay scans
  → Poll processing until READY
  → Snapshot initial state (task, actions, DB summaries)
  → Execute workflow under test
  → Validate final state
  → Cleanup (delete or mark test tasks)
```

## Principles

1. Prefer **API-based setup** over direct DB writes (safer across tenants).
2. Use factories/DB only when API cannot express precondition.
3. Never commit secrets; use `test-accounts.example.json` pattern.
4. Tag provisioned entities with automation marker for cleanup.
5. Document Constance profile required for scenario pack per `{env}.rebotics.net`.
6. Avoid hundreds of static response mocks; keep **few golden payloads** for contract/unit only.
7. **Scan images are planogram/category-specific — never one global `bay_1_scan.jpg` for all tasks.**

## Scan / bay image selection (locked)

Uploading the wrong shelf image for a planogram produces wrong or empty actions. Provisioning must choose images that match:

| Key | Why |
|-----|-----|
| Planogram id / category (e.g. deli, pasta, grocery) | Layout and products differ |
| Bay index | Bay 1 ≠ Bay 2 visually or in POG |
| Stage (`pre_photo` / `post_photo`) | Different compliance expectations |
| Retailer / env | Media and POG catalogs differ per `{env}.rebotics.net` |

### How the provisioner picks images

```text
Task / Planogram / Category
        ↓
Image catalog lookup (fixtures indexed by category + bay + stage)
        ↓
If exact match missing → fail provisioning with clear error
   (do NOT silently fall back to unrelated bay_1_scan.jpg)
        ↓
Upload matched images → poll processing
```

### Catalog shape (sketch)

```yaml
# docs/regression/data/image-catalog.yaml (conceptual)
images:
  - id: pasta_bay1_pre
    file: test-data/images/Pasta_Bay1.jpg
    categories: [pasta, dry_grocery]
    bay: 1
    stage: pre_photo
  - id: deli_bay1_pre
    file: test-data/images/bay_1_scan.jpg   # only valid for matching deli-like POGs
    categories: [deli_meat, deli]
    bay: 1
    stage: pre_photo
```

Scenario data then references **selection rules**, not a hard-coded single file for every task:

```yaml
data:
  env: epsilon
  store_id: 5342
  require:
    task_def:
      pog_reset_task_step_enabled: true
    planogram:
      category: pasta   # drives image selection
    scans:
      strategy: catalog_match   # NOT fixed bay_1_scan.jpg
      bays: [1, 2]
      stage: pre_photo
```

GenAI may **suggest** which catalog entries fit a new planogram category; it must not invent image bytes or silently reuse a mismatched photo.

## Data Definition Schema (sketch)

```yaml
data:
  env: epsilon
  store_id: 5342
  require:
    shift: open
    task_def:
      pog_reset_task_step_enabled: true
    planogram:
      category: pasta
    scans:
      strategy: catalog_match
      bays: [1, 2]
      stage: pre_photo
  snapshots:
    - name: initial_action_list
      api: GET /api/v1/tasks/{task_id}/action-list/retailer/
  cleanup:
    strategy: abandon_task_or_delete_if_allowed
```

## Environments

| Env | Use |
|-----|-----|
| local-mock | Offline mapper/unit only |
| any `{name}.rebotics.net` | Via `--env=name` |
| production hosts | **Read-only probes only** — never mutate by default |

## Risks

- Shared tenant pollution
- Async processing SLAs vary
- **Mismatched scan image vs planogram category** → empty/wrong actions (mitigate with catalog_match + fail-fast)
- Image rejection rules change
- Quota/throttle on 2FA