# 13 — CI/CD Integration

## Current Pipelines

| Repo | CI | Gate? |
|------|----|-------|
| rebotics-management-django | GHA parallel tests + deploy workflows | Yes (backend) |
| android-rebotics | Bitbucket build/distribute | Build-oriented |
| ios-rebotics | Fastlane TestFlight | Release-oriented |
| retech-api-automation | GHA Maven | Yes |
| retech-mobile-automation | GHA LambdaTest batches | Yes |
| retech-web-automation | GHA split jobs | Yes |
| automation-dashboard | update-dashboard.yml Pages | **No test gate** |

## Target Gates (phased)

### Gate A — PR (fast)
- MBIT unit tests (`test_mobile_action_list_logic.py`)
- Contract baseline diff for touched APIs
- Android IR mapper unit tests (if Android repo PR)

### Gate B — Merge / Nightly
- Live IR smoke against epsilon (provision + action-list + invariants)
- API `IntelligenceResetApiTest` subset
- Impacted scenario pack from diff

### Gate C — Release
- Full IR suite + API IR + thin Appium IR smoke
- Unified PASS/FAIL artifact published to dashboard

## Orchestrator in CI

```yaml
# sketch
- name: Regression
  run: ./regression run --mode=impacted --base=${{ github.event.pull_request.base.sha }}
  env:
    TEST_USER: ${{ secrets.REGRESSION_USER }}
    TEST_PASSWORD: ${{ secrets.REGRESSION_PASSWORD }}
    BASE_URL: ${{ vars.EPSILON_URL }}
```

Publish: JUnit XML, JSON result, HTML report, evidence zip.

## Exit Code Mapping

| Code | CI meaning |
|------|------------|
| 0 | Pass |
| 1 | Product/contract failure → fail job |
| 2 | Env/infra → fail or retryable workflow |
| 3 | Framework bug → fail + alert QA platform |

## Dashboard Integration

Extend run-summary schema with `regression_platform` block; fetch into AI usage / new Regression tab (future). Do not block Pages deploy on lab failures until Gate A is green locally.
