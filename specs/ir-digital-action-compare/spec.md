# Spec: IR Audit — Digital Report Action Compare Tab

**Feature Branch**: `feat/ir-digital-action-compare`

**Created**: 2026-09-04

**Status**: Specified (locked for Plan/Tasks)

**Input**: Enhance E2E Audit report: move Streamlined Step Trace into its own tab; add user-performed action column from Digital Report; compare generated vs performed actions.

**Related code today**:
- `mobile-backend-integration-tests/core/e2e_audit_engine.py` (`TaskAuditSummary`, `StepTelemetryRecord`)
- `mobile-backend-integration-tests/core/e2e_audit_report_generator.py` (section “3. Streamlined Step-by-Step Bi-Directional Trace”)
- Domain already has `scan_id` on `PositionDomainModel`; audit summary already has `store_id`, `pog_id`

---

## Locked decisions (from product)

1. Host remains this repo’s IR E2E Audit HTML report (in-page tabs, not a new dashboard app tab).
2. Digital data is **not** scraped from `/reporting/dashboard`. Fetch JSON:
   `GET /api/v1/reporting/R07/section-product-reports/?scan_id={scan_id}`
3. Auth is the **same token** used to load task details / action-list (`Authorization: Token …`).
4. UI Item list columns map to JSON fields **`action_type`** and **`action_taken`**. Example from Digital Report:
   - `action_type`: `"ok"`
   - `action_taken`: `"-"` (dash / empty means no user action recorded)
5. Digital rows include **`scan_id`**. Primary join: `scan_id`, then `upc` (+ position if needed).
6. Historical task-ID report tabs: **Overview · Slot · Step Trace · Pre Photo Compare · Post Photo Compare**. Lifecycle, payload inspection, and HTTP Traffic are excluded because they are only valid when captured during a true task-creation-to-completion E2E run.
7. Mismatches are **informational in the compare tab and they lower combined compliance** when digital data is present.
8. Category and date are **not required to fetch digital rows** (scan_id is enough). They are used for the dashboard deep link: task payload first, CLI `--category` / `--date` override if provided.

---

## Objective

When an IR task is loaded and actions are generated (scan id, UPC, product), the E2E Audit HTML report must:

1. Present the **Streamlined Step-by-Step Bi-Directional Trace** in tab **Step Trace**.
2. Show extra columns: **Digital Action Type** and **User Action Taken**.
3. Provide tab **Action Compare** that diffs generated mobile actions vs digital-report performed actions.
4. Surface both **execution compliance** and **digital alignment**, and a **combined compliance** that drops on mismatch.

**Success**: QA opens one HTML file, uses Step Trace + Action Compare, sees generated vs user actions, and compliance reflects digital mismatch without opening the SPA.

---

## User Scenarios & Testing

### User Story 1 — Dedicated Trace tab (Priority: P1)

QA opens an IR E2E Audit HTML report and uses tabs instead of a long scroll.

**Independent Test**: Open report → click “Step Trace” → former section-3 table is the visible panel.

**Acceptance Scenarios**:

1. **Given** a historical task-ID audit with N step records, **When** the report loads, **Then** tabs are: Overview, Slot, Step Trace, Pre Photo Compare, Post Photo Compare. Overview is default.
2. **Given** Step Trace is selected, **When** user views the page, **Then** the table titled “Streamlined Step-by-Step Bi-Directional Trace (N Mobile Steps)” is shown with existing search/filter.
3. **Given** Excel export exists, **When** user exports, **Then** Step Trace is included with a clear section title.

---

### User Story 2 — User action columns from Digital Report (Priority: P1)

On each generated step row, show Digital Report `action_type` and `action_taken`, joined by `scan_id` / UPC.

**Independent Test**: Fixture `section-product-reports` JSON + known generated steps → columns populated; unmatched show `—` / `NOT IN DIGITAL`.

**Acceptance Scenarios**:

1. **Given** a digital row with `scan_id`, `upc`, `action_type="ok"`, `action_taken="-"`, **When** report is built, **Then** the matching Step Trace row shows those values in **Digital Action Type** and **User Action Taken**.
2. **Given** no digital match for a generated step, **When** report is built, **Then** those cells are `—` with status `NOT IN DIGITAL`.
3. **Given** digital fetch fails (401/404/timeout), **When** report is built, **Then** Step Trace still renders generated steps and a banner states digital data unavailable.

---

### User Story 3 — Generated vs performed comparison + compliance (Priority: P1)

Action Compare tab classifies rows and updates compliance.

**Independent Test**: Fixture with 1 MATCH, 1 MISMATCH, 1 GENERATED_ONLY, 1 DIGITAL_ONLY → exact counts; combined compliance < 100 when mismatches exist.

**Acceptance Scenarios**:

1. **Given** both sides loaded, **When** Action Compare opens, **Then** summary shows matched, mismatched, generated-only, digital-only.
2. **Given** same `scan_id` (and UPC) but different `action_type` / `action_taken` vs generated action, **When** compared, **Then** status = `MISMATCH` and both sides are shown.
3. **Given** a digital row with no generated counterpart, **When** compared, **Then** status = `DIGITAL_ONLY`.
4. **Given** digital data is present, **When** overview KPIs render, **Then** they show execution compliance, digital alignment, and combined compliance. Combined score is the minimum of execution compliance and digital alignment (so any mismatch or unmatched row lowers the headline score).
5. **Given** digital data is unavailable, **When** overview KPIs render, **Then** combined compliance equals existing execution compliance (do not penalize fetch failure).

---

### User Story 4 — Digital dashboard deep link (Priority: P2)

**Acceptance Scenarios**:

1. **Given** store, category, planogram, date are known, **When** Action Compare (and Step Trace header) render, **Then** a link  
   `https://{env}.rebotics.net/reporting/dashboard?store=…&category=…&planogram=…&date=…`  
   is shown.
2. **Given** category or date is missing, **When** report renders, **Then** the link is still shown with known params only (no invented date).

---

### Edge Cases

- Duplicate UPC facings: match by `scan_id` first; if only UPC, match by UPC + POG/ROG position (`section` / shelf:pos); else `AMBIGUOUS`.
- Empty digital `action_taken` (`"-"` / `null` / `""`) is a real value: treat as **no user action taken**, not as fetch failure.
- Digital `action_type` of `"ok"` vs generated REMOVE/SET_ASIDE/etc. is a **MISMATCH** unless a documented synonym table maps them. Current synonyms: Fixed Item→FIX_IN_BAY; Restocked Item→RESTOCK; Removed Item→REMOVE; Add Item→ADD_TO_SHELF/SET_ASIDE; Moved Item→SET_ASIDE/ADD_TO_SHELF (cross-bay pick+place); Image not Ideal…→IDENTIFY.
- Empty action-list or empty digital: empty states, not errors.
- Multiple unique `scan_id`s on one task: fetch once per unique scan_id and merge item lists.

---

## Functional Requirements

### FR-1 Report chrome
- Tabbed layout with the five historical-audit tabs.
- Move current Section 3 into **Step Trace**.
- Add **Action Compare**. Keep Slot and Overview KPIs. Lifecycle, payload inspection, and HTTP Traffic belong only to live E2E execution reports backed by captured events.

### FR-2 Generated side
- Each `StepTelemetryRecord` includes `scan_id` (nullable), `upc`, product title, generated `action_type` / banner, coordinates.

### FR-3 Digital side
- `GET {base}/api/v1/reporting/R07/section-product-reports/?scan_id={scan_id}` with the same auth as task load.
- Normalize each item to: `scan_id`, `upc`, `product_name`, `section`, `pog_position`, `rog_position`, `action_type`, `action_taken`, raw row.
- Fetch at report generation time. No SPA scrape.

### FR-4 Compare + compliance
- Join: `scan_id` then `upc` + position.
- Statuses: `MATCH` | `MISMATCH` | `GENERATED_ONLY` | `DIGITAL_ONLY` | `AMBIGUOUS` | `UNAVAILABLE`.
- A scan that failed to fetch is `UNAVAILABLE`; it remains visible but is excluded from alignment scoring so infrastructure failure does not create a product mismatch.
- `digital_alignment_pct` = `matched / (matched + mismatched + generated_only + digital_only + ambiguous) * 100` when denominator > 0, else 100 if all loaded rows match/are empty, else N/A when no digital request succeeded.
- Two mobile cards derived from one backend move (`SET_ASIDE` + `ADD_TO_SHELF`) are one logical generated action for summary counts and alignment scoring.
- `combined_compliance_pct` = `min(execution_compliance_pct, digital_alignment_pct)` when digital loaded successfully; else execution only.

### FR-5 Boundaries

| Always | Ask first | Never |
|--------|-----------|-------|
| Same Token auth as task fetch | New HTTP libraries | Scrape Digital Report DOM |
| Keep report usable if digital unavailable | Changing join key after fixtures exist | Commit secrets |
| Deterministic compare, no GenAI verdict | Mapping `"ok"` as equivalent to generated action types | Silently ignore mismatches |

### FR-6 Task/photo timeline and post-photo comparison
- Read task timestamps from task details only when the backend returns them.
- Read pre/post upload timestamps from scans explicitly identified as `pre_photo` / `post_photo`; never infer post photo from numeric scan ordering.
- Show task start-to-completion and pre-to-post duration when both endpoints are present.
- Keep per-action timestamps out of Step Trace until action-list GET returns `completed_at` or an equivalent field.
- Fetch R07 for the explicit post scan and render a separate **Post Photo Compare** tab.
- Compare post R07 only with actions returned by `action-list/retailer/?stage=post_photo`. Never reuse pre-photo generated actions when that stage is unavailable.
- Report whether the action list grew after post upload only when both scan records expose action counts; otherwise state that the API data is insufficient.

---

## Success Criteria

- [ ] Five historical-audit tabs exist; Step Trace holds the former section-3 table.
- [ ] Columns show Digital `action_type` and `action_taken`.
- [ ] Action Compare shows MATCH / MISMATCH / GENERATED_ONLY / DIGITAL_ONLY with counts.
- [ ] Combined compliance drops when digital mismatches exist; fetch failure does not drop it.
- [ ] Unit tests with fixtures cover join + HTML (no live network in CI).

---

## Open Questions (resolved)

| # | Answer |
|---|--------|
| API | `GET /api/v1/reporting/R07/section-product-reports/?scan_id=` |
| Auth | Same as task details |
| Fields | `action_type`, `action_taken` (screenshot: `"ok"`, `"-"`) |
| scan_id | Yes; primary join key with UPC |
| Category/date | Not required for fetch; task payload then CLI override for dashboard link |
| Mismatch vs compliance | Both: show in compare tab **and** lower combined compliance |
| Tabs | Overview · Slot · Step Trace · Pre Photo Compare · Post Photo Compare |

Remaining non-blocking: mismatch-only filter (P3); multi-day windows (out of v1).

---

## Out of Scope (v1)

- Changing iOS/Android/Backend product repos.
- Live browser automation of the Digital Report UI.
- Treating Digital `"ok"` as automatically equal to a generated IR action type without an explicit mapping table.
- Auto-healing / AI rewriting of actions from mismatches.
