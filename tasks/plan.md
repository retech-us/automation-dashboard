# Implementation Plan: Autonomous Mobile + Backend Regression Platform

## Overview

Build an autonomous regression and release validation platform that covers **all mobile features** (not IR-only), keeps inventory updated as mobile evolves, runs against **any selected environment**, and validates that **real mobile code** works with the **real backend** — without reimplementing mobile business logic inside the test framework, and without UI automation as the primary mechanism.

Discovery is complete. Stakeholder decisions are locked in `docs/regression/15-product-decisions.md`.

**North star:** Option B (backend + real mobile domain headless).  
**Near-term delivery tactic:** Option D hybrid only where native headless is not yet extractable — then retire test-side logic.

## Architecture Decisions

1. **Scope = all mobile features** — IR is first slice for delivery order only.
2. **Do not duplicate mobile business logic in tests** — drive production Android/iOS domain/API layers; assert contracts and expected state.
3. **Environment is selectable at runtime** — any configured env (`--env=...`); production mutate blocked by default.
4. **Continuous update** — git diff / feature inventory drives which scenarios run as mobile changes.
5. **Deterministic assertions beat AI** — AI annotates failures only.
6. **Thin Appium ring** — true UI-only cases (camera, PlanogramView, etc.).
7. **Primary home for orchestrator** — `automation-dashboard`, invoking native + API suites as needed.
8. **Python MBIT domain mapper is interim debt** — must not expand to “all features”; shrink as native drivers land.

## Task List

### Phase 0: Foundation (Discovery) — DONE
- [x] Multi-repo architecture audit
- [x] Docs `docs/regression/00`–`14` + `KNOWN_LIMITATIONS.md`
- [x] This plan + `tasks/todo.md`
- [x] Stakeholder decisions: all features, real mobile code, multi-env (`15-product-decisions.md`)

### Checkpoint: Discovery
- [x] Scope clarified: all features + multi-env + no test-side business-logic clone
- [ ] Confirm list of environments to configure first (URLs/accounts via secrets)
- [ ] Confirm Android/iOS owners for extracting UI-free domain entry points (required for Decision 2)

### Phase 1: Inventory & Honesty
- [ ] Task 1: Expand feature inventory toward **full mobile catalog** (not only P0 IR)
- [ ] Task 2: Export/version OpenAPI baselines for IR/auth/upload (then widen)
- [ ] Task 3: Correct MBIT README REAL vs SIMULATED claims; mark Python domain as interim
- [ ] Task 4: Add impact-map.yaml (paths → features) for continuous update
- [ ] Task 4b: Multi-env config model (`environments.yaml` + `--env` selection)

### Checkpoint: Inventory
- [ ] Inventories validate against schema
- [ ] No overclaim in README

### Phase 2: Headless Parity
- [ ] Task 5: Golden action-list fixtures
- [ ] Task 6: Parity test Python mapper ↔ Android unit output
- [ ] Task 7: Portable NativeMobileRunner paths
- [ ] Task 8: iOS DTO decode tests for golden fixtures

### Checkpoint: Parity
- [ ] CI job fails on mapper drift

### Phase 3–4: Provisioning & Data
- [ ] Task 9: Shared IR data provisioner library
- [ ] Task 10: Cleanup + tenant safety guards
- [ ] Task 11: Scenario data YAML pack

### Phase 5–6: Scenarios & Orchestrator
- [ ] Task 12: Scenario schema + IR smoke pack (≥10)
- [ ] Task 13: `./regression` CLI orchestrator
- [ ] Task 14: Evidence pack writer

### Checkpoint: Orchestrator
- [ ] Unattended IR smoke on epsilon passes twice

### Phase 7–8: Contracts & Failures
- [ ] Task 15: Persist API schema baselines + drift gate
- [ ] Task 16: Unified failure taxonomy
- [ ] Task 17: Optional AI analysis annotations

### Phase 9–10: CI & Autonomy
- [ ] Task 18: Gate A (unit/parity) on PR
- [ ] Task 19: Gate B nightly live smoke
- [ ] Task 20: Impacted-feature selection + full mode + release report

### Checkpoint: Complete
- [ ] All acceptance criteria in todo.md met
- [ ] Ready for review / rollout

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Python ≠ production mobile | High | Parity lock; extract use cases |
| Tenant Constance drift | High | Document profiles; multi-env smoke |
| Async flakes | Med | Poll SLO; classify env vs product |
| Scope explosion | Med | IR vertical slice first |
| Secrets leakage | High | gitignore + examples only |
| AI false waivers | High | Hard forbid override |

## Open Questions

1. Which non-prod tenant is the **source of truth** for IR automation (Epsilon vs other)?
2. Is Android Presenter extraction approved for a pilot sprint?
3. Should orchestrator live only in automation-dashboard or also as a shared internal package?
4. Who owns contract baseline waivers?
5. Minimum Appium IR smoke — restore `09_IntelligenceReset` or rewrite thinner?

## Definition of Done (standing)

See `.agents/skills/planning-and-task-breakdown/references/definition-of-done.md`.  
Plus: every dependency labeled REAL/CONTROLLED/SIMULATED/MOCKED; evidence pack on failure; no production mutation.
