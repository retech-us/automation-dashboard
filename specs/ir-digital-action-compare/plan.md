# Plan: IR Audit — Digital Report Action Compare Tab

**Branch**: `feat/ir-digital-action-compare` | **Date**: 2026-09-04 | **Spec**: [`spec.md`](./spec.md)

**Status**: Ready for tasks (API locked). Implementation starts only after `tasks.md` is approved / next implement command.

## Summary

Enhance the IR E2E Audit HTML report with six tabs. Fetch Digital Report item lists via `GET /api/v1/reporting/R07/section-product-reports/?scan_id=` using the same Token as task load. Join on `scan_id` then UPC. Show `action_type` / `action_taken` on Step Trace. Compare generated vs performed. Combined compliance = min(execution, digital alignment) when digital fetch succeeds.

## Technical Context

| Item | Choice |
|------|--------|
| Language | Python 3, existing `mobile-backend-integration-tests` |
| HTTP | stdlib `urllib` (same as adapters; no new deps) |
| Auth | `Authorization: Token {token}` already used for `/api/v4/tasks/{id}/` |
| Report UI | Generated HTML + tab CSS/JS pattern from `backward_compat_report_generator.py` |
| Tests | `unittest` + JSON fixtures (no live network in CI) |

## Constitution Check

- Deterministic verdicts — OK.
- Explicit status if digital missing — OK.
- Domain mapping stays out of HTML — new client + compare modules; generator only renders.
- Combined compliance is computed in compare module, not in templates.

## Architecture

```text
taskId → action-list domain (scan_id on current/expected position)
              │
              ├── StepTelemetryRecord.scan_id
              │
              └── unique scan_ids
                        │
                        ▼
         GET /api/v1/reporting/R07/section-product-reports/?scan_id=
         (same Token as task fetch)
                        │
                        ▼
              action_compare.join()
                        │
         TaskAuditSummary.digital_compare
         + combined_compliance_pct
                        │
                        ▼
         tabbed e2e_audit_report_generator
```

### Files

| File | Role |
|------|------|
| `core/digital_report_client.py` | Fetch + normalize R07 rows; injectable opener |
| `core/action_compare.py` | Join + statuses + alignment % |
| `core/e2e_audit_engine.py` | `scan_id` on steps; attach compare; dual compliance |
| `core/e2e_audit_report_generator.py` | Six tabs; new columns; compare table; dashboard link |
| `tests/test_action_compare.py` | Join / compliance math |
| `tests/test_digital_report_client.py` | Normalize fixture JSON |
| `tests/test_e2e_audit_report_tabs.py` | HTML tab ids + column headers |
| `tests/fixtures/section_product_reports_ok.json` | Sample Item list rows |

### Join rules

1. Index digital items by `scan_id` then by `(scan_id, upc)`.
2. For each generated step with `scan_id`: match digital items with same `scan_id` and UPC.
3. If multiple digital items for same UPC on that scan: also match `pog_position` / section+shelf+pos when present.
4. Else `AMBIGUOUS`.
5. Unmatched generated → `GENERATED_ONLY`. Unmatched digital → `DIGITAL_ONLY`. A generated row from a scan whose R07 request failed → `UNAVAILABLE`.
6. `MATCH` only if `action_type` and `action_taken` equal after trim/casefold; `"-"` / empty `action_taken` equals `"-"` / `""` / `None`.
7. v1 does **not** treat Digital `"ok"` as matching generated `REMOVE` / `SET_ASIDE` (that is a MISMATCH). Document this in the compare tab hint.

### Compliance

- `execution_compliance_pct`: existing performed / generated steps.
- `digital_alignment_pct`: matched / scored compare rows; `UNAVAILABLE` rows are visible but excluded.
- `combined_compliance_pct`: `min(execution, alignment)` when digital fetch `ok`; else execution only.
- Overview KPI cards show all three when digital present.

### Category / date (Q4 locked)

- Fetch does not use category/date.
- Dashboard link: `store` + `planogram` from audit; `category` and `date` from task payload if present, else CLI kwargs on the generator/engine; omit missing query params.

## Risks

| Risk | Mitigation |
|------|------------|
| Response shape unknown beyond screenshot columns | Client accepts list or `{results: []}`; tests pin aliases `action_type`/`actionType` |
| `"ok"` vs IR action names always mismatch | Spec-explicit; show both values; do not invent synonym map in v1 |
| Report HTML already large | Extract tab shell + keep section builders; no nested ternaries |
| Multiple scan_ids | One request per unique id; merge |

## Verification

```bash
cd mobile-backend-integration-tests
python3 -m unittest tests.test_action_compare tests.test_digital_report_client tests.test_e2e_audit_report_tabs -v
```
