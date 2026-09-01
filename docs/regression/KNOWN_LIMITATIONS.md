# KNOWN_LIMITATIONS

Discovery date: 2026-09-01. Do not hide these.

## Platform / Architecture

1. **No true production mobile headless runtime today.** MBIT adapters are Python HTTP clients, not Koin/Retrofit or Moya DI graphs.
2. **IR sequencing is UI-bound** on Android (`ActionListPresenter`) and iOS (VIPER TaskActionList).
3. **KMP shared module is negligible** — cannot share IR domain across Android/iOS via KMP today.
4. **Dual API generations (v1 + v4)** — inventory and tests must cover both until mobile fully migrates.
5. **Per-retailer tenants + Constance** — behavior differs by environment; one green suite ≠ all tenants.
6. **Async Core/Dramatiq** — timing flakes unless poll/SLO policy is strict.
7. **intellitrade / trade-auth are unrelated** — ignore for this platform.

## Automation Estate

8. **MBIT/runner_server not CI-gated.**
9. **Appium IR feature file is commented out** — UI IR coverage inactive.
10. **OpenAPI schemas downloaded but baselines not persisted** — contract drift gate incomplete (`CONTRACT_DRIFT_AUDIT_REPORT` in API repo).
11. **action-collector / state-collector directories are empty stubs.**
12. **test_directory_registry is a hardcoded PASSED catalog**, not a live executor.
13. **NativeMobileRunner uses machine-local paths** — not portable CI.
14. **Failure classification exists in mobile Appium only** — not unified.
15. **No impacted-feature selection** from git diff.
16. **README overclaims** JVM/Swift execution — must be corrected to avoid false confidence.

## Data / Security

17. **Real credentials must not be committed** (`test-accounts.json` gitignored).
18. **Production must not be mutated** by autonomous suites.
19. **Golden IR HTML reports / raw JSON** are generated artifacts — gitignored; not source of truth.

## Coverage Honesty

20. Feature inventory is a **seed**, not a complete mobile feature catalog.
21. iOS **lacks dedicated IR unit tests**.
22. AI analysis is **design-only** — not implemented.
23. Option C (full app headless) is **not feasible near-term** without major refactors.

## Process

24. **Human approval required** before implementation phases that touch production apps.
25. Discovery docs live in `automation-dashboard/docs/regression/` — cross-repo work needs coordination PRs in android/ios/django/api/mobile automation repos.
