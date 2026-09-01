# 05 — Workflow Map

## Trace Template

```text
User Intent
  → Mobile action
  → ViewModel / Presenter / Interactor
  → Repository / Service
  → API Client
  → HTTP Request
  → Backend Endpoint
  → Auth
  → Business Service
  → Database
  → Business Rules
  → API Response
  → Mobile Parser
  → Domain Model
  → State Management
  → UI State
  → User-visible result
```

## WF-IR-001 — Intelligent Reset Happy Path

| Step | Layer | Location | UI required? |
|------|-------|----------|--------------|
| Login + 2FA | Mobile→API | FEATURE-001 | No for API |
| Resolve store/shift | Mobile→API | FEATURE-040 | No |
| Open IR task | Mobile | Task detail + `pog_reset_task_step_enabled` | Partial |
| Pre-photo scans | Mobile→v4 upload→Core | FEATURE-030/031 | Camera UI yes; fixture upload no |
| Fetch action-list | API | API-IR-001 | No |
| Map to cards | Mobile domain | FEATURE-021 | **Logic no; today bound to Presenter** |
| Execute actions / PATCH | Mobile→API | FEATURE-022 | Partial |
| Post-photo | Upload | FEATURE-031 | Camera UI yes |
| Complete task | API | tasks/subtasks | No |

**Test without UI:** auth, provision, upload fixtures, fetch action-list, Python/Android mapper invariants, PATCH APIs.  
**Requires mobile code execution:** true Presenter/Interactor sequencing (not yet headless).  
**Requires backend:** yes.  
**Requires DB:** yes (task + compliance + scans).  
**External:** Core/Dramatiq.  
**Currently UI automation:** Appium IR dormant.  
**Currently mocked:** MBIT local-mock mode only.

## WF-AUTH-001 — Login

Fully headless via API adapters. SSO is harder (external IdP).

## WF-CAP-001 — Scan Upload

Headless with controlled images. Async poll required. Dummy images may be rejected (REAL validation).

## What Can Be Tested Without UI (summary)

| Capability | Without UI |
|------------|------------|
| Auth password/2FA | YES |
| Task CRUD / defs | YES |
| Action-list fetch + schema | YES |
| IR domain map (Python + Android unit) | YES |
| IR Presenter sequencing | NO (today) |
| PlanogramView rendering | NO |
| Camera capture UX | NO (inject/fixture instead) |
| Compliance generation | YES (after real processing) |
| Constance settings fetch | YES |

## Architecture Diagram (logical)

```text
┌──────────── Mobile ────────────┐     ┌──────── Backend ────────┐
│ UI (Compose/UIKit)             │     │ DRF Views/Serializers   │
│ Presenters/Interactors ◄─HARD──┼─────┤ Services/Modifiers      │
│ Repos/API clients ◄──HEADLESS─┼─────┤ Models/Postgres         │
│ Mappers ◄──UNIT/HEADLESS──────┼─────┤ Dramatiq → Core         │
└────────────────────────────────┘     └─────────────────────────┘
         ▲
         │ MBIT Python adapters (REAL HTTP)
         │ MBIT domain engine (SIMULATED map)
         │ API RestAssured (REAL HTTP)
```
