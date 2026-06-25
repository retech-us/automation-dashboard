# Automation Dashboard

Unified static dashboard for **Web**, **Mobile**, and **API** automation test health.

**Live URL (after setup):** `https://retech-us.github.io/automation-dashboard/`

## Architecture

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Web Automation  │  │Mobile Automation│  │ API Automation  │
│ (Selenium)      │  │ (Appium)        │  │ (REST Assured)  │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │ run-summary.json   │                    │
         ▼                    ▼                    ▼
    GitHub Pages         GitHub Pages         GitHub Pages
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                   ┌──────────────────────┐
                   │ automation-dashboard │
                   │  (static HTML/JS)    │
                   └──────────────────────┘
```

No backend required for MVP. Each repo publishes `run-summary.json` alongside its Allure report.

## Folder Structure

```
automation-dashboard/
├── index.html                 # Main dashboard page
├── assets/
│   ├── css/dashboard.css
│   └── js/dashboard.js
├── data/
│   ├── repos.json             # Repo metadata / URLs
│   ├── web.json               # Cached latest web summary (CI-updated)
│   ├── mobile.json
│   └── api.json
├── schemas/
│   └── run-summary.schema.json
├── docs/
│   └── HOW_TO_USE.md
└── .github/workflows/
    └── update-dashboard.yml   # Fetches summaries + deploys Pages
```

## Setup

1. Create GitHub repo `retech-us/automation-dashboard`
2. Enable GitHub Pages from `gh-pages` branch
3. In each automation repo, add `run-summary.json` generation (see `retech-web-automation/scripts/automation-reporting/`)
4. Optional: add `DASHBOARD_DISPATCH_TOKEN` secret to automation repos to trigger dashboard refresh on each run

## Data Contract

See `schemas/run-summary.schema.json` and sample in `retech-web-automation/schemas/run-summary.sample.json`.

## Future Enhancements

- Historical trends (append to `data/history/{repo}.jsonl`)
- Flaky test detection feed
- Slack/Teams notifications from dashboard workflow
- Combined Allure mega-report
- Database-backed dashboard (Postgres + API) when scale requires it
