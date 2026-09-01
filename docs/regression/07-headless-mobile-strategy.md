# 07 — Headless Mobile Strategy

## Goal

Execute **real mobile-side behavior** (API, parse, domain, state) without launching Android/iOS UI, Appium, or emulator interaction as the primary mechanism.

## Honest Current State

| Claim in MBIT README | Reality |
|----------------------|---------|
| Android adapter runs JVM/Retrofit/Koin | **False today** — Python urllib HTTP client with mobile-like headers |
| iOS adapter runs Swift/Moya | **False today** — Python urllib |
| Zero UI | **True** for MBIT path |
| Real backend mode | **True** (Epsilon etc.) |
| Action/state collectors | **Stubs empty** |

## Feasibility by Layer

### Android — PARTIAL

**Can run headless now:**
- Retrofit interfaces (`PogResetApi`) under unit/integration with injected OkHttp
- Action-list mappers (`ActionListDomainMapper*`) — existing JVM tests
- Repositories with fakes/real Retrofit

**Cannot run headless without refactor:**
- `ActionListPresenter` (~3k LOC) — imports Compose Color, Activity companions
- Full Koin graph expecting `Application`

**Strategy:**
1. Keep MBIT Python engine as interim oracle.
2. Make Android mapper + workflow unit tests the **parity source of truth**.
3. Extract sequencing interfaces from Presenter behind UI-free use cases (pilot).
4. Only then invoke production Kotlin from CI headless harness.

### iOS — PARTIAL

**Can run headless now:**
- `rebotics_api` framework (Moya targets/DTOs) in theory as a test host
- Some services without UIKit

**Cannot easily:**
- TaskActionList VIPER (presenter-coupled)
- Services importing PlanogramView

**Strategy:**
1. Prefer API-level + shared fixtures for iOS until a CLI/test host wraps `rebotics_api`.
2. Add IR DTO decode unit tests (missing today).
3. Avoid claiming Swift headless until a real test target exists.

## Recommended Headless Runtime Shapes

### Near-term (Phase 2–3) — Hybrid Harness

```text
Scenario
  → Data provisioner (REAL API)
  → Fetch action-list (REAL)
  → Domain engine:
        primary: Android unit tests OR Python mapper (parity-locked)
  → Assert invariants + state
  → Evidence pack
```

### Mid-term (Phase 5+) — Native Domain Drivers

```text
Scenario
  → HeadlessMobileRunner
  → Production UseCase/Repository (Kotlin / Swift API)
  → REAL API
  → Assertions on domain state objects
```

### Explicit non-goals (core suite)

- Appium taps
- Emulator UI
- Full Application onCreate for every test (until justified)

## UI Automation Role

Keep Appium as a **thin ring** for:
- Camera permission/UX
- PlanogramView/RealogramView visual interactions
- Smoke navigation

Target: ≤10% of IR scenarios require UI.

## Parity Lock Protocol

1. Golden action-list JSON fixtures checked in.
2. Android mapper output = canonical expected.
3. Python MBIT mapper must match canonical (CI fails on drift).
4. iOS DTO decode must accept same fixtures.
5. No silent dual logic forever — track as tech debt with owner.

## Risks

- False confidence if Python diverges from Kotlin/Swift.
- Extraction of Presenter blocked by product roadmap.
- Realm/Room side effects in “almost headless” tests.
