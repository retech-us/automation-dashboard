# 09 — Scenario Model

## Principle

Organize regression around **business features**, not only endpoints.

## Scenario Schema

```yaml
scenario:
  id: SC-IR-001
  feature_id: FEATURE-020
  name: Fetch action list after pre-photo processing
  risk: critical
  priority: P0
  mode: [real]  # real | controlled | mock
  preconditions:
    data_ref: data/ir_basic.yaml
  actions:
    - auth
    - provision_ir_task
    - upload_pre_scans
    - wait_processing
    - get_action_list
  api_calls:
    - API-IR-001
  expected_backend_state:
    task.status: in_progress_or_ready
    action_list.count_gte: 1
  expected_mobile_state:
    domain.actions_count: equals_api_count
    invariants: all_pass
  assertions:
    - contract_schema: action_list_v1
    - invariant_pack: ir_8
  cleanup:
    - release_task
  tags: [ir, smoke, headless]
```

## IR Scenario Pack (initial)

| ID | Feature | Intent |
|----|---------|--------|
| SC-IR-001 | FEATURE-020 | Valid action-list after scans |
| SC-IR-002 | FEATURE-021 | Domain map preserves count/order |
| SC-IR-003 | FEATURE-023 | Cross-bay pairing complete |
| SC-IR-004 | FEATURE-024 | Refresh does not drop pending |
| SC-IR-005 | FEATURE-020 | Empty list when processing incomplete |
| SC-IR-006 | FEATURE-001 | 401 invalid credentials |
| SC-IR-007 | FEATURE-030 | Upload finish + poll success |
| SC-IR-008 | FEATURE-030 | Backend timeout/poll exhaust |
| SC-IR-009 | FEATURE-020 | Contract: missing optional image field |
| SC-IR-010 | FEATURE-022 | PATCH progress idempotent |

Each critical feature should grow to ≥5 scenarios (happy, validation, auth fail, timeout, schema edge).

## Existing Assets to Map

- `mobile-backend-integration-tests/scenarios/**/*.yaml`
- `intelligent_reset_full_lifecycle.yaml`
- `tests/test_mobile_action_list_logic.py` (unit scenarios)
- API `IntelligenceResetApiTest`
- Appium features (IR currently commented)

## Execution Modes

| Mode | Backend | Mobile logic |
|------|---------|--------------|
| real | REAL tenant | SIMULATED or native unit |
| controlled | REAL + provisioned data | same |
| mock | local simulator | unit/mapper only |
