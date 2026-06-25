# How to Use the Automation Dashboard

## What each repo covers

| Repo | Stack | Scope |
|------|-------|-------|
| **Web** | Selenium + Cucumber + TestNG | Rebotics Management web UI — scans, tasks, imports, spatial review |
| **Mobile** | Appium + Cucumber | iOS & Android retail associate apps |
| **API** | REST Assured + TestNG | REBM backend API contracts and integrations |

## Reading pass / fail

- **Green card** — Latest CI run had zero failures
- **Red card** — One or more tests failed or were broken
- **Numbers** — Total / Passed / Failed / Skipped from the most recent run

## Debugging failures in Allure

1. Click **View Allure Report** on the repo card
2. Open **Suites** or **Behaviors** tab
3. Click a failed test → review **Steps**, **Attachments** (screenshots, page source), and **History**
4. Check labels: `failure.category`, `failure.reason`, `repo`, `environment`, `suite`

## Common failure categories

| Category | Typical cause | First action |
|----------|---------------|--------------|
| `login` | Auth API down, expired credentials | Check staging auth health |
| `locator` | UI change, wrong selector | Compare screenshot vs current UI |
| `timeout` | Slow page/API, missing wait | Check network tab / API latency |
| `api` | HTTP 4xx/5xx from backend | Review API logs for endpoint |
| `data` | Bad test data, CSV mismatch | Verify test fixtures |
| `environment` | 503, deploy in progress | Check deployment status |
| `assertion` | Expected vs actual mismatch | Review assertion in feature file |

## Contact / ownership

- **Web automation:** QA Web team — `retech-web-automation`
- **Mobile automation:** QA Mobile team — `retech-mobile-automation`
- **API automation:** QA API team — `retech-api-automation`
- **Dashboard:** #qa-automation Slack channel
