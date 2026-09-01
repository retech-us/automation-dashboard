# 14 — Implementation Roadmap

## Recommended Architecture

**Option D — Hybrid** (see `01-system-architecture.md`).

## Phases

### PHASE 0 — Repository discovery
**Status:** Complete (this document set)  
**Goal:** Understand system; no product code changes  
**Acceptance:** Docs 00–14 + KNOWN_LIMITATIONS + tasks/* reviewed by human  

### PHASE 1 — Feature/API inventory hardening
**Goal:** Expand inventories to release-critical completeness; impact map  
**New components:** `impact-map.yaml`, baseline folder  
**Tasks:** inventory expansion, API baseline export, README honesty fix  
**Tests:** schema validation of YAML inventories  
**Acceptance:** All P0 features have IDs + APIs linked  
**Risks:** Incomplete iOS paths  
**Rollback:** docs-only  

### PHASE 2 — Headless mobile execution layer (honest)
**Goal:** Formalize harness; parity lock Python↔Android mappers  
**Files:** MBIT core, adapters, `native_mobile_runner.py`  
**New:** golden fixtures; parity CI job  
**Acceptance:** Parity test fails if Python drifts from Android unit output  
**Risks:** Path portability  
**Rollback:** disable parity job  

### PHASE 3 — Backend integration library
**Goal:** Shared provisioner (task def → scans → action-list) used by MBIT + API  
**Acceptance:** One library call creates IR-ready task on epsilon  
**Risks:** Tenant pollution — require cleanup  

### PHASE 4 — Release data provisioning
**Goal:** Scenario data YAML + cleanup  
**Acceptance:** SC-IR-001 runs twice idempotently  

### PHASE 5 — Scenario engine
**Goal:** Unified scenario schema + IR pack (≥10 scenarios)  
**Acceptance:** `./regression run --suite=ir-smoke` executes pack  

### PHASE 6 — Regression orchestrator
**Goal:** CLI orchestrator with evidence + exit codes  
**Acceptance:** Unattended run on CI runner  

### PHASE 7 — Contract validation
**Goal:** Persisted OpenAPI baselines + drift gate  
**Repos:** primarily `retech-api-automation` + docs baselines  
**Acceptance:** Breaking field type change fails CI  

### PHASE 8 — Failure analysis
**Goal:** Taxonomy + optional AI annotations  
**Acceptance:** Every failure record includes classification  

### PHASE 9 — CI/CD
**Goal:** Gate A/B wired for dashboard + API; Android mapper on Android CI  
**Acceptance:** PR cannot merge on IR parity/contract break (policy TBD)  

### PHASE 10 — Autonomous regression
**Goal:** Impacted selection + full mode + release report  
**Acceptance:** Release command produces PASS/FAIL with evidence pack  

### Later — Native extraction (Option B convergence)
Extract Android Presenter / iOS Interactor rules into UI-free use cases; reduce Python simulation.

## Per-Phase Task Template Fields

Each phase tracks: Goal, Files/modules, New components, Dependencies, Implementation tasks, Tests, Acceptance criteria, Risks, Rollback — detailed checklist in `tasks/todo.md`.

## Sequencing Rationale

Inventory → honest headless → provisioner → scenarios → orchestrator → contracts → classification → CI → autonomy.  
High-risk illusions (README overclaim, no CI) fixed early.
