# 01 — System Architecture

## Overview

The Rebotics Store Intelligence ecosystem spans mobile clients, a per-tenant Management backend, ML/Core processing, and multiple automation repos. This document describes the **as-is** architecture and the **to-be** Autonomous Regression & Release Validation Platform.

## As-Is Ecosystem Map

```text
┌──────────────────┐   ┌──────────────────┐
│  android-rebotics │   │   ios-rebotics    │
│  Kotlin/Compose   │   │  Swift/VIPER     │
│  Retrofit/Koin    │   │  Moya/Realm      │
└────────┬─────────┘   └────────┬─────────┘
         │  Token/JWT + UA      │
         └──────────┬───────────┘
                    ▼
┌───────────────────────────────────────────┐
│     rebotics-management-django            │
│  /api/v1/*  +  /api/v4/* (legacy mobile)  │
│  Postgres (per retailer) · Redis · Dramatiq│
└───────────┬───────────────────────────────┘
            │ scan processing / FV
            ▼
     Core / FVM / Admin (sibling services)

Automation estate:
  retech-api-automation      → RestAssured, real env
  retech-mobile-automation   → Appium + LambdaTest
  retech-web-automation      → Selenium admin portal
  automation-dashboard       → health Pages + IR lab (MBIT)
```

**Out of scope for IR regression:** `intellitrade`, `intellitrade-gateway`, `trade-auth` (unrelated trading stack).

## As-Is IR Critical Path

```text
Auth (2FA/JWT)
  → Create/claim Task (pog_reset_task_step_enabled)
  → Pre/post bay scan upload (/api/v4/processing/upload*)
  → Core/Dramatiq processing
  → Compliance + action generation
  → GET /api/v1/tasks/{id}/action-list/retailer/
  → Mobile domain map → UI cards (Android Presenter / iOS Interactor)
  → PATCH scan-report-actions / complete stages
```

## Dependency Classification (target)

| Dependency | Class | Notes |
|------------|-------|-------|
| Management API (non-prod tenant) | **REAL** | Primary truth |
| Postgres state | **REAL** / **CONTROLLED** | Via API or controlled DB access |
| Dramatiq/Core processing | **REAL** | Poll for completion |
| Bay scan images | **CONTROLLED** | Deterministic fixtures uploaded as real bytes |
| Auth tokens | **CONTROLLED** | Dedicated test accounts |
| Constance flags | **CONTROLLED** | Documented per-tenant profile |
| S3/MinIO | **REAL** (non-prod) | Presigned uploads |
| Local mock server | **MOCKED** | Offline/dev only |
| Python IR domain mapper | **SIMULATED** | Interim; parity-locked to Android unit tests |
| Appium UI | **REAL** app | Thin outer ring only |
| External SSO IdP | **MOCKED/SIMULATED** | Prefer password+2FA test path |

## Architecture Options Compared

### Option A — API-only regression
| | |
|--|--|
| Advantages | Fast; reuses `retech-api-automation`; no mobile build |
| Disadvantages | Misses mobile parsing, card ordering, conservation bugs |
| Effort | Low |
| Maintenance | Low |
| Coverage | Backend/contracts only |
| Risk | High false confidence for IR |
| Performance | Excellent |
| Feasibility | High |
| **Verdict** | Necessary but **insufficient** |

### Option B — Backend + mobile domain-layer headless
| | |
|--|--|
| Advantages | Validates mobile processing without UI; aligns with prompt |
| Disadvantages | Requires UI-free use cases; Android/iOS extraction work |
| Effort | Medium–High |
| Maintenance | Medium |
| Coverage | High for IR domain |
| Risk | Medium (extraction politics) |
| Performance | Good |
| Feasibility | **PARTIAL today** — APIs/repos yes; Presenters no |
| **Verdict** | End-state target for IR |

### Option C — Full mobile application headless runtime
| | |
|--|--|
| Advantages | Maximum fidelity |
| Disadvantages | Needs Application/Koin/Realm bootstrap; Presenter still UI-bound; CI cost |
| Effort | Very High |
| Maintenance | High |
| Coverage | Highest |
| Risk | High delivery risk |
| Performance | Poor–Medium |
| Feasibility | **Low near-term** |
| **Verdict** | Reject as Phase-1 strategy |

### Option D — Hybrid (RECOMMENDED)
| | |
|--|--|
| Advantages | Ships value now; honest about simulation; path to Option B |
| Disadvantages | Dual oracles until parity proven |
| Effort | Medium |
| Maintenance | Medium |
| Coverage | Backend + simulated mobile + growing native |
| Risk | Medium — mitigated by parity lock |
| Performance | Good |
| Feasibility | **High** — builds on MBIT + API suite |
| **Verdict** | **Choose this** |

## Recommended To-Be Architecture (Option D)

```text
┌─────────────────────────────────────────────────────────────┐
│                 Regression Orchestrator                      │
│   feature discovery · scenario select · evidence · report    │
└───────────────┬─────────────────────┬───────────────────────┘
                │                     │
        ┌───────▼────────┐    ┌───────▼────────┐
        │ Contract Gate  │    │ Data Provisioner│
        │ OpenAPI baseline│   │ task/scans/POG  │
        └───────┬────────┘    └───────┬────────┘
                │                     │
                └──────────┬──────────┘
                           ▼
                 REAL Management Backend
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    API assertions   IR Domain Engine   Native parity
    (Java/RestAssured) (Python MBIT)   (Android unit /
                                        future iOS)
           │               │               │
           └───────────────┼───────────────┘
                           ▼
              Cross-layer State Validator
                           │
                           ▼
         Failure Classifier (+ optional AI analysis)
                           │
                           ▼
              PASS/FAIL + Evidence Pack
```

Thin UI ring (optional): Appium scenarios for camera/PlanogramView-only cases.

## Where Logic Lives Today (testability)

| Concern | Backend | Android | iOS | MBIT today |
|---------|---------|---------|-----|------------|
| Auth | Django 2FA/JWT | Auth activities/repos | AuthFlow + Api | Python adapter REAL |
| Action-list API | TaskActionListViewSet | PogResetApi | ActionListRetailerTarget | REAL fetch |
| Action map/sort | planogram_comparison + compliance | Domain mappers + **Presenter** | Interactor/Service | **SIMULATED** Python |
| Invariants | Partial in compliance | Implicit in UI | Implicit in UI | **Explicit** 8 invariants |
| Scan upload | realograms + v4 processing | Upload workers | Upload services | REAL |
| Card UI | N/A | Compose | UIKit/PlanogramView | Not tested (by design) |

## Design Principles (non-negotiable)

1. Deterministic assertions are authoritative; AI never flips FAIL→PASS.
2. Do not duplicate production calculations as the only oracle without an independent expected-state rule or parity lock.
3. Prefer REAL backend over mocks.
4. Do not modify production behavior solely for tests.
5. Document REAL / CONTROLLED / SIMULATED / MOCKED on every dependency.

## Related Documents

- `07-headless-mobile-strategy.md`
- `10-regression-orchestrator-design.md`
- `14-implementation-roadmap.md`
- `KNOWN_LIMITATIONS.md`
