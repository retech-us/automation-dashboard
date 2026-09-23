# Tasks: IR Audit — Digital Report Action Compare Tab

**Input**: [`spec.md`](./spec.md), [`plan.md`](./plan.md), [`contracts/section-product-reports.md`](./contracts/section-product-reports.md)

**Tests**: Required (constitution TDD). Write failing tests before implementation.

**Paths**: `mobile-backend-integration-tests/` unless noted.

## Format

`[ID] [P?] [Story] Description`

- **[P]**: parallel-safe (different files)
- **[Story]**: US1–US4

---

## Phase 1: Setup

- [x] T001 Create fixture file `mobile-backend-integration-tests/tests/fixtures/section_product_reports_ok.json` with two Item list rows matching the screenshot (`upc` `840093104403` / `840093102034`, `action_type` `ok`, `action_taken` `-`, `scan_id`, `section`, `pog_position`, `rog_position`, `product_name`).
- [x] T002 [P] Create fixture `mobile-backend-integration-tests/tests/fixtures/section_product_reports_mismatch.json` with one MATCH-shaped row and one row whose `action_type` differs from generated IR type.

**Verify**: fixtures parse as JSON (`python3 -m json.tool <file>`).

---

## Phase 2: Foundational (blocks stories)

- [x] T003 Write failing tests in `mobile-backend-integration-tests/tests/test_digital_report_client.py`: normalize array vs `{results:[]}`, map `action_type`/`action_taken`, empty taken → `"-"`, camelCase aliases.
  - Acceptance: tests fail (module missing).
  - Verify: `python3 -m unittest tests.test_digital_report_client -v` (from `mobile-backend-integration-tests`)
- [x] T004 Implement `mobile-backend-integration-tests/core/digital_report_client.py`: `fetch_section_product_reports(base_url, token, scan_id, opener=None)` using stdlib urllib; injectable opener for tests.
  - Acceptance: T003 passes; 401/404 returns structured error without raising into report crash path.
  - Verify: same unittest command.
- [x] T005 Write failing tests in `mobile-backend-integration-tests/tests/test_action_compare.py`: MATCH, MISMATCH, GENERATED_ONLY, DIGITAL_ONLY, AMBIGUOUS; `digital_alignment_pct`; `combined = min(execution, alignment)` when digital ok; fetch-fail does not lower combined.
  - Verify: `python3 -m unittest tests.test_action_compare -v`
- [x] T006 Implement `mobile-backend-integration-tests/core/action_compare.py` join rules from plan.md.
  - Verify: T005 passes.

**Checkpoint**: client + compare work with fixtures, no HTML yet.

---

## Phase 3: US1 — Dedicated Trace tab (P1) 🎯 MVP chrome

- [x] T007 Write failing test `mobile-backend-integration-tests/tests/test_e2e_audit_report_tabs.py`: generated HTML contains tab buttons/ids `tab-overview`, `tab-slot`, `tab-lifecycle`, `tab-step-trace`, `tab-action-compare`, `tab-http`; Step Trace contains heading text `Streamlined Step-by-Step Bi-Directional Trace`.
  - Verify: `python3 -m unittest tests.test_e2e_audit_report_tabs -v`
- [x] T008 Refactor `mobile-backend-integration-tests/core/e2e_audit_report_generator.py` to tabbed layout (reuse tab CSS/JS pattern from `backward_compat_report_generator.py`). Move current section 3 into Step Trace. Keep Slot, Lifecycle, HTTP Traffic, Overview KPIs.
  - Acceptance: T007 passes; Excel export still includes Step Trace table.
  - Verify: T007 + existing `tests.test_e2e_integration_flow` report test still pass.

**Checkpoint**: report is tabbed; Step Trace is its own tab.

---

## Phase 4: US2 — Digital columns on Step Trace (P1)

- [x] T009 Extend `StepTelemetryRecord` in `mobile-backend-integration-tests/core/e2e_audit_engine.py` with `scan_id`, `digital_action_type`, `digital_action_taken`, `digital_match_status`. Populate `scan_id` from domain `current_position.scan_id` or `expected_position.scan_id`.
  - Acceptance: unit assertion on a raw action-list item with `scan_id` 16920444.
  - Verify: add case in `tests/test_e2e_integration_flow.py` or new `tests/test_e2e_audit_scan_id.py`
- [x] T010 Wire `audit_task_execution` (or report caller in `runner_server.py`) to fetch R07 per unique scan_id via `digital_report_client` when token+base_url provided; on failure leave digital fields empty and set `digital_fetch_error`.
  - Acceptance: injectable fetch; no live network in tests.
- [x] T011 [US2] Add Step Trace columns **Digital Action Type** and **User Action Taken** in `e2e_audit_report_generator.py`. Unmatched → `—` / `NOT IN DIGITAL`. Banner when `digital_fetch_error`.
  - Verify: extend `test_e2e_audit_report_tabs.py` to assert column headers and a fixture-driven cell value `ok`.

**Checkpoint**: Step Trace shows digital columns.

---

## Phase 5: US3 — Action Compare + compliance (P1)

- [x] T012 Attach compare result onto `TaskAuditSummary` (`digital_compare` rows + counts, `digital_alignment_pct`, `combined_compliance_pct`). Execution KPI remains; combined uses spec formula.
  - Verify: `tests.test_action_compare` + engine test with fixture.
- [x] T013 [US3] Render Action Compare tab: summary counts + row table (generated action vs `action_type` / `action_taken` + status). Hint that Digital `"ok"` is not auto-equivalent to IR action names in v1.
  - Verify: HTML contains `MATCH`/`MISMATCH` sample from fixture.
- [x] T014 [US3] Overview KPI cards show execution, digital alignment, and combined when digital loaded; combined omitted or equals execution when fetch failed.
  - Verify: tab test asserts KPI labels.

**Checkpoint**: compare tab + compliance behavior complete.

---

## Phase 6: US4 — Dashboard deep link (P2)

- [x] T015 [US4] Build dashboard URL from `instance_slug`, `store_id`, `pog_id`, optional `category_id` and `date` (task payload then generator kwargs). Omit missing query params. Place link on Action Compare and Step Trace headers.
  - Verify: HTML contains `/reporting/dashboard?store=` and does not invent a date when none passed.

---

## Phase 7: Polish

- [x] T016 Run `python3 -m unittest tests.test_action_compare tests.test_digital_report_client tests.test_e2e_audit_report_tabs tests.test_e2e_integration_flow -v` from `mobile-backend-integration-tests`.
- [x] T017 [P] Confirm Excel export includes Step Trace and Action Compare tables (extend export JS section titles if needed in `e2e_audit_report_generator.py`).

## Phase 8: Task timeline and post-photo verification

- [x] T018 Normalize task lifecycle timestamps and explicit pre/post scan metadata without guessing scan type.
- [x] T019 Persist live task/scans payloads and pass normalized timeline data into the audit report.
- [x] T020 Add Overview timeline cards and duration calculations; show unavailable when APIs omit dates.
- [x] T021 Fetch post-scan R07 data and add the Post Photo Compare tab.
- [x] T022 Report post-photo action-list growth only when scan payloads expose comparable action counts.
- [x] T023 Keep per-action timestamps disabled until action-list GET returns a real completion timestamp.
- [x] T024 Add unit/HTML coverage and run the complete test suite.

---

## Dependencies

```
T001, T002
    → T003 → T004
    → T005 → T006
         → T007 → T008   (US1)
         → T009 → T010 → T011  (US2)
         → T012 → T013 → T014  (US3)
         → T015 (US4)
         → T016, T017
```

US1 can start after T006. US2–US3 share engine/generator files — implement sequentially to avoid merge conflicts.

## Implementation strategy

1. Finish Phase 2 (pure logic).
2. US1 tabs (visible MVP).
3. US2 columns + fetch.
4. US3 compare + compliance.
5. US4 link.

Do not start coding until this task list is the agreed execution order.
