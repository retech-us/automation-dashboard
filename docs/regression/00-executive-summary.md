# 00 — Executive Summary: Autonomous Regression & Release Validation

**Date:** 2026-09-01  
**Status:** Discovery complete — stakeholder decisions locked in `15-product-decisions.md`  
**Primary workspace:** `automation-dashboard`  
**Scope repos:** `android-rebotics`, `ios-rebotics`, `rebotics-management-django`, `retech-api-automation`, `retech-mobile-automation`, `retech-web-automation`

**Locked product intent:** (1) cover **all** mobile features and keep updating as mobile evolves, (2) validate **real mobile code** (do not reimplement app logic in tests), (3) **choose any configured environment** at run time.

---

## CURRENT SYSTEM

### Mobile
| Platform | Stack | Architecture | IR location |
|----------|-------|--------------|-------------|
| Android | Kotlin 2.2, Koin, Retrofit/OkHttp, Room, Compose (POG Reset) | Hybrid modular Clean-ish + MVI presenters | `features/rebotics_pog_reset` — action workflow in ~3k-LOC `ActionListPresenter` |
| iOS | Swift, VIPER + Coordinator, Moya, Realm | Generamba VIPER modules | Spread across Tasks/Planogram VIPER (`TaskActionList*`) |

### Backend
- **Rebotics Management Django** `26.5.51` — Django 4.2 / DRF / Postgres / Redis / Dramatiq (not Celery)
- Hybrid multi-tenant: **one Management + DB per retailer**
- Intelligent Reset ≡ POG Reset via `TaskDef.pog_reset_task_step_enabled`
- Dual API generations: `/api/v1/*` (current) + `/api/v4/*` (legacy mobile spine)

### Database
- Postgres per tenant; key tables: `tasks_task*`, planogram/compliance action tables, `realograms_implementation_*`, `shifts_shift`

### Existing automation
| Layer | Repo | Maturity | UI required? |
|-------|------|----------|--------------|
| IR domain lab | `automation-dashboard` / MBIT | Deep IR invariants + reports; **not CI-gated** | No (operator UI optional) |
| API | `retech-api-automation` | Strong RestAssured + schemas; drift gate incomplete | No |
| Mobile UI | `retech-mobile-automation` | Solid Appium/LambdaTest; IR feature **dormant** | Yes |
| Web UI | `retech-web-automation` | Strong portal CI; adjacent to IR cards | Yes |
| Dashboard | static Pages aggregator | Observability only | N/A |

### Current regression capability
- API CRUD/E2E and schema download: **strong**
- Associate UI smoke/regression: **strong**
- IR action-list / conservation / multi-bay state: **lab-only** (Python domain simulation + live backend)
- True production Kotlin/Swift headless runtime: **not present**
- Change-impact suite selection: **not present**
- Unified failure taxonomy across repos: **partial** (mobile only)

---

## CURRENT GAPS

1. README/marketing overclaims “JVM/Swift production runtime”; adapters are Python HTTP clients + Python-ported domain logic.
2. IR business rules remain UI-bound (`ActionListPresenter` / VIPER interactors) — not extractable as-is for Option C.
3. MBIT / runner_server not wired as a CI gate.
4. OpenAPI schema download exists; **baseline contract drift gate does not**.
5. Appium IR feature file is commented out — UI IR coverage gap.
6. No impacted-feature selection from git diff → feature inventory.
7. Dual API (v1/v4) + per-tenant Constance flags make “one env” regression unsafe.
8. Empty `action-collector/` / `state-collector/` stubs vs documented promises.
9. AI analysis / autonomous failure classification not productized for IR.
10. No shared release-data factory spanning API + MBIT + Appium.

---

## HEADLESS FEASIBILITY

| Layer | Verdict | Explanation |
|-------|---------|-------------|
| Backend | **YES** | Real JWT/2FA APIs + DB + factories; Dramatiq async must be polled |
| Android | **PARTIAL** | `PogResetApi` + repositories + mappers are headless-capable; action sequencing is presenter-bound |
| iOS | **PARTIAL** | `rebotics_api` Moya targets are headless-capable; IR VIPER is UI-coupled; PlanogramView dependency |
| Real data | **PARTIAL** | Non-prod tenant + factories + scan upload works; prod-like dumps are ops-dependent; Constance variance |

---

## RECOMMENDED ARCHITECTURE

**North star: Option B** — real backend + real mobile domain/API layers for **all features**, env selectable (`15-product-decisions.md`).

**Delivery tactic: Option D only as temporary bridges** where UI-free mobile entry points do not exist yet — then remove test-side business logic.

```text
Choose ENV (any configured)
  + Feature inventory (ALL mobile features, continuously updated)
  + REAL Backend on that env
  + REAL mobile domain/network code (Android + iOS) headless
  + API contract/schema gate
  + Thin Appium only for true UI/camera scenarios
  + Orchestrator in automation-dashboard
```

Do **not** choose Option A alone (misses mobile processing).  
Do **not** expand Python “fake app brain” to all features.  
Do **not** choose Option C (full UI app runtime) as the default.

---

## EXPECTED RESULT (target state)

| Metric | Target (12–18 months) |
|--------|------------------------|
| Feature coverage (critical IR + auth + tasks + capture) | ≥ 90% of inventory critical features |
| Scenario coverage (happy + negative + edge) | ≥ 5 scenarios per critical feature |
| Regression execution time (impacted mode) | < 30 min; full mode < 2 h |
| Manual effort reduction (IR release signoff) | ≥ 60% |
| UI dependency (core suite) | Near-zero; Appium ≤ 10% of IR scenarios |
| Mock dependency | Only external/uncontrollable deps |
| CI/CD integration | MBIT smoke + API IR + contract drift as gates |

---

## TOP 10 RISKS

1. Treating Python domain port as production truth without Android/iOS parity lock → false confidence.
2. Presenter/Interactor extraction rejected or delayed → permanent simulation gap.
3. Tenant Constance drift → tests pass on Epsilon, fail on KRCS (or reverse).
4. Dramatiq/Core async timing → flaky state assertions.
5. Dual v1/v4 APIs → incomplete contract inventory.
6. Hardcoded machine paths in `NativeMobileRunner` → non-portable CI.
7. Secrets / test accounts leaking into git.
8. Scope explosion (“every mobile feature”) before IR vertical slice is solid.
9. AI overriding assertion failures (explicitly forbidden).
10. Over-investing in Appium IR while headless path is unfinished.

---

## TOP 20 IMPLEMENTATION TASKS

See `tasks/todo.md` and `14-implementation-roadmap.md`. Summary:

1. Freeze inventory schema + seed FEATURE-001…N for IR/auth/tasks  
2. Publish API inventory from OpenAPI + adapters  
3. Honest adapter/README rewrite (REAL vs SIMULATED)  
4. Promote Android mapper unit tests as parity source of truth  
5. Wire MBIT unittest + live smoke into CI  
6. Finish OpenAPI baseline drift gate in API repo  
7. Unify failure classification taxonomy  
8. Fill action/state collectors  
9. Release-data provisioner (task def → scans → action-list) as library  
10. Scenario YAML schema + IR scenario pack  
11. Regression orchestrator CLI (`./regression run`)  
12. Impacted-feature selector from git diff  
13. Evidence pack (request/response/DB/mobile state)  
14. AI analysis layer (classify only; never override)  
15. Extract Android IR sequencing behind UI-free interface (pilot)  
16. iOS `rebotics_api` headless harness pilot  
17. Contract consumer tests for action-list schema  
18. Thin Appium IR smoke (un-comment/rewrite minimal)  
19. Coverage matrix generator  
20. Full regression mode + release PASS/FAIL report  

**Human gate:** review and approve this discovery pack before coding Phase 2+.
