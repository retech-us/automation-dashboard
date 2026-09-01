# Task List — Autonomous Regression Platform

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked

## Phase 0 — Discovery
- [x] Audit android-rebotics, ios-rebotics, django, automation suites
- [x] Write docs/regression/00–14 + KNOWN_LIMITATIONS.md
- [x] Write tasks/plan.md + tasks/todo.md
- [x] **HUMAN GATE (partial):** All mobile features + no test-side logic clone + multi-env (`docs/regression/15-product-decisions.md`)
- [ ] **HUMAN GATE (remaining):** List envs to configure first + mobile owners for UI-free domain entry points

## Phase 1 — Inventory & Honesty

### Task 1: Expand toward full mobile feature inventory
**Description:** Catalog all mobile modules/features (Android + iOS). IR remains first implementation slice, not scope limit. Keep inventory updatable as mobile changes.  
**Acceptance criteria:**
- [ ] Feature IDs cover all major mobile modules (not only IR)
- [ ] Each feature lists mobile entry points + APIs + headless feasibility
- [ ] Process documented to add/update features when mobile PRs land
**Verification:**
- [ ] YAML parses; spot-check against Android `features/` and iOS `Screens/Modules/`
**Dependencies:** Human gate remaining items  
**Files:** `docs/regression/02-feature-inventory.yaml`  
**Scope:** M

### Task 2: OpenAPI baseline export
**Description:** Capture swagger/auto-docs snapshots for IR/auth/upload endpoints into versioned baselines.  
**Acceptance criteria:**
- [ ] Baselines committed under `docs/regression/baselines/`
- [ ] Document update policy
**Verification:**
- [ ] Diff tool runs locally against live schema
**Dependencies:** Task 1  
**Files:** `docs/regression/baselines/**`, `03-api-inventory.yaml`  
**Scope:** M

### Task 3: README honesty rewrite
**Description:** Correct MBIT README claims about JVM/Swift runtime; document REAL vs SIMULATED.  
**Acceptance criteria:**
- [ ] README matches actual adapter implementation
- [ ] Architecture doc linked
**Verification:**
- [ ] Human review  
**Dependencies:** None  
**Files:** `mobile-backend-integration-tests/README.md`  
**Scope:** S

### Task 4: Impact map (keeps suite current with mobile)
**Description:** Map repo file path globs → feature IDs so mobile enhancements auto-select scenarios.  
**Acceptance criteria:**
- [ ] Covers android features/*, ios Screens/Modules/*, django apps, api tests
**Verification:**
- [ ] Sample mobile PR diff resolves to expected features  
**Dependencies:** Task 1  
**Files:** `docs/regression/impact-map.yaml`  
**Scope:** S

### Task 4b: Multi-environment selection
**Description:** Config + CLI so any configured env can be chosen at run time.  
**Acceptance criteria:**
- [ ] `environments.yaml` (or equivalent) lists named envs with base URL hooks
- [ ] Runner accepts `--env=<name>`; credentials via env/secrets (not git)
- [ ] Production mutate blocked unless explicit override
**Verification:**
- [ ] Same smoke scenario invoked with two different `--env` values  
**Dependencies:** Env list from human  
**Files:** `mobile-backend-integration-tests/config/environments.json`, orchestrator config  
**Scope:** S

### Checkpoint — Phase 1
- [ ] Full-feature inventory direction + multi-env + honest README reviewed

## Phase 2 — Headless Parity

### Task 5: Golden action-list fixtures
**Acceptance criteria:**
- [ ] ≥3 fixtures (simple, multibay, duplicate UPC) checked in
**Files:** `mobile-backend-integration-tests/backend/fixtures/ir/**`  
**Scope:** S

### Task 6: Parity test Python ↔ Android
**Acceptance criteria:**
- [ ] CI-comparable command fails if domain outputs diverge
**Files:** MBIT tests, `native_mobile_runner.py`  
**Scope:** M

### Task 7: Portable native runner paths
**Acceptance criteria:**
- [ ] Env vars replace hardcoded user paths
**Scope:** S

### Task 8: iOS golden DTO decode tests
**Acceptance criteria:**
- [ ] XCTest (or equivalent) decodes golden fixtures
**Files:** ios-rebotics ReboticsTests  
**Scope:** M

### Checkpoint — Phase 2
- [ ] Parity job green on main

## Phase 3–4 — Provisioning

### Task 9: Shared IR provisioner
**Acceptance criteria:**
- [ ] Single API creates IR-ready task with scans processed
**Scope:** M

### Task 10: Cleanup + safety
**Acceptance criteria:**
- [ ] Blocks production base URLs; cleans tagged tasks
**Scope:** S

### Task 11: Scenario data YAML
**Acceptance criteria:**
- [ ] data/*.yaml referenced by scenarios
**Scope:** S

## Phase 5–6 — Scenarios & Orchestrator

### Task 12: IR scenario pack ≥10
**Acceptance criteria:**
- [ ] SC-IR-001…010 implemented per `09-scenario-model.md`
**Scope:** M

### Task 13: Regression CLI
**Acceptance criteria:**
- [ ] `./regression run --suite=ir-smoke` works unattended
**Files:** `regression/**` or `scripts/regression*`  
**Scope:** M

### Task 14: Evidence pack
**Acceptance criteria:**
- [ ] On failure, zip contains request/response/state/logs
**Scope:** S

### Checkpoint — Orchestrator
- [ ] Two consecutive epsilon smokes pass

## Phase 7–8 — Contracts & Failures

### Task 15: Contract drift gate (API repo)
**Acceptance criteria:**
- [ ] Baseline diff fails CI on breaking change
**Scope:** M

### Task 16: Unified failure taxonomy
**Acceptance criteria:**
- [ ] MBIT + orchestrator emit classes from `11-failure-classification.md`
**Scope:** M

### Task 17: AI analysis hook (optional)
**Acceptance criteria:**
- [ ] Annotations only; cannot override FAIL
**Scope:** M

## Phase 9–10 — CI & Autonomy

### Task 18: Gate A on PR
**Acceptance criteria:**
- [ ] Unit + parity required on automation-dashboard PRs
**Scope:** S

### Task 19: Gate B nightly live smoke
**Acceptance criteria:**
- [ ] Scheduled workflow + secrets
**Scope:** M

### Task 20: Impacted selection + release report
**Acceptance criteria:**
- [ ] `--mode=impacted` selects scenarios; release report PASS/FAIL
**Scope:** M

### Checkpoint — Complete
- [ ] Executive targets for IR smoke met
- [ ] KNOWN_LIMITATIONS updated
- [ ] Human sign-off for rollout

---

## Parallelization Notes

- Safe in parallel after Phase 1: Task 8 (iOS) vs Task 6 (Android parity), Task 15 (API repo) vs Task 13 (orchestrator)
- Sequential: provisioner before live scenario pack; taxonomy before AI hook

## Out of Scope Until Later

- Full Option C application headless runtime
- Replacing web/mobile UI suites
- Production mutating autonomous runs
