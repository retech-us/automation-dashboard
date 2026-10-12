# Sentry Span Usage & Cost Optimization Audit

Organization: `retech-labs` (sentry.io). Measurement window: last 30 days (2026-09-12 to 2026-10-12, UTC). Audit date: 2026-10-12.
Scope: read-only. No settings, code, or data were changed.

Written for: the engineers and SRE owners of the Sentry projects, who need to act on quota exhaustion.

---

## 1. Executive summary

- **The org is over its span quota, and ingestion has effectively stopped.** Accepted span volume ends on 2026-09-29. Since then, drops are recorded with reason `span_usage_exceeded` (2.25B spans dropped in the 30-day window). Production telemetry for the affected projects is being lost right now.
- **`rebm` is the number-one span producer** (~727.9M spans, 68.6% of observed 30-day volume). **`hawkeye` is second** (~316.4M, 29.8%). Together they are 98.4% of volume.
- **Main confirmed driver:** Django framework instrumentation. `event.django` + `middleware.django` + `db` make up most spans in both projects (see section 4).
- **Billing attribution is not confirmed.** The org's plan, quota, and billing breakdown were not reachable through the MCP tools used here (section 7). The `span_usage_exceeded` reason confirms the span quota is the limiting factor, but not the exact price or amount.
- **Highest-confidence reduction:** lower the volume of Django-level spans (`event.django`, `middleware.django`) in `rebm` and `hawkeye`, and sample `db`/`http.client` spans, while keeping errors and transactions at full rate. This needs code confirmation first (section 6).
- **Exact next action:** Check the org's span quota and current usage in *Settings → Subscription / Stats* (section 7). In parallel, decide whether to raise the quota or to cut span volume in `rebm` and `hawkeye` before the next billing cycle. Do not disable Sentry.

---

## 2. Projects discovered

21 projects are visible through the MCP connection:

`sas-business-system`, `admin`, `android`, `core`, `cpg-api`, `cvat`, `data_integrations`, `dataset`, `fvm`, `hawkeye`, `ios`, `ner`, `omega`, `race-platform`, `rebm`, `rebotics`, `rebotics-frontend`, `sas-integration`, `staff-flow-backend`, `staff-flow-frontend`, `version-checker`

Only 7 projects reported span volume in the 30-day window. The other 14 reported none.

---

## 3. Top span-generating projects (30-day volume)

Source: `search_traces`, dataset `spans`, `count()` grouped by `project`, period `30d`.
Dashboard: https://retech-labs.sentry.io/explore/traces/?aggregateField=%7B%22groupBy%22%3A%22project%22%7D&mode=aggregate&statsPeriod=30d&table=span

| Rank | Project | Platform (inferred from name) | Span volume (30d) | Share of observed | Trend | Priority |
|---|---|---|---|---|---|---|
| 1 | `rebm` | backend (Django) | 727,873,845 | 68.6% | Not measured (no prior-period query run) | P1 |
| 2 | `hawkeye` | backend (Django) | 316,385,261 | 29.8% | Not measured | P1 |
| 3 | `ios` | iOS | 9,539,091 | 0.9% | Not measured | P3 |
| 4 | `rebotics-frontend` | web | 3,667,264 | 0.3% | Not measured | P3 |
| 5 | `android` | Android | 2,986,056 | 0.3% | Not measured | P3 |
| 6 | `race-platform` | other | 766,800 | 0.07% | Not measured | P4 |
| 7 | `fvm` | other | 39 | ~0% | Not measured | none |

Total observed (accepted) volume: ~1,061.2M spans. Platform labels are inferred from project names and should be confirmed.

**Ranked by growth rate:** not available. The 14-day daily series is incomplete (see section 5). A prior-period comparison query has not been run, so no growth rates are claimed.

---

## 4. Top span operations per project

Source: `search_traces`, `count()` grouped by `span.op`, filtered by project, period `30d`.

### `rebm` (727.9M spans)

| span.op | Count | Share of rebm |
|---|---|---|
| event.django | 522,772,958 | 71.8% |
| middleware.django | 103,885,821 | 14.3% |
| db | 78,117,589 | 10.7% |
| http.server | 5,700,265 | 0.8% |
| view.render | 5,266,333 | 0.7% |
| http.client | 4,629,897 | 0.6% |
| view.response.render | 4,579,978 | 0.6% |
| db.redis | 2,597,256 | 0.4% |
| http.client.stream | 319,748 | <0.1% |
| template.render | 4,000 | <0.1% |

### `hawkeye` (316.4M spans)

| span.op | Count | Share of hawkeye |
|---|---|---|
| event.django | 159,286,084 | 50.4% |
| db | 83,058,193 | 26.3% |
| http.server | 26,416,863 | 8.4% |
| view.response.render | 26,406,709 | 8.3% |
| http.client | 13,231,498 | 4.2% |
| db.redis | 4,378,331 | 1.4% |
| middleware.django | 3,221,315 | 1.0% |
| view.render | 256,255 | 0.1% |
| view.authenticate | 119,983 | <0.1% |
| template.render | 10,030 | <0.1% |

**Observations:**
- `event.django` is the single largest op in both projects. It is a per-event wrapper span from the Sentry Django integration. Its volume is driven by the number of signals/events the app dispatches, not by request count alone. Checking the source of the events is needed (section 6).
- `middleware.django` in `rebm` (103.9M) is high relative to its request-level span count. This suggests a deep middleware stack, or very frequent requests to endpoints that run middleware.
- `db` spans are 10.7% of `rebm` and 26.3% of `hawkeye`. The `hawkeye` DB share is high.
- Operation-level counts were not broken down further by endpoint or transaction name (`transaction` grouping not run). That breakdown is the next query needed.

---

## 5. Ingestion status and dropped data

Source: `find_dropped_events` (dataset `spans`, period `30d`). Raw output was saved to the tool-results file and summarized with jq.

### Accepted span volume by bucket

- Accepted events range from **2026-09-25 to 2026-09-29** (last accepted bucket).
- The 14-day daily count shows volume only on 09-28 (198.1M) and 09-29 (347.8M); every day from 09-30 to 10-12 is 0.

### Dropped span volume (30-day totals, counts summed)

| Outcome / reason | Dropped spans | Meaning |
|---|---|---|
| rate_limited / **span_usage_exceeded** | **2,249,083,901** | Org span quota exhausted. Server-side drop. |
| client_discard / ratelimit_backoff | 1,746,639,042 | SDK backed off after rate limiting. |
| invalid / too_large:transaction | 363,796,918 | Transaction payload over size limit. |
| client_discard / sample_rate | 362,098,689 | Dropped by the SDK's configured sample rate. |
| rate_limited / spike_protection | 96,678,015 | Spike protection throttled ingestion. |
| client_discard / backpressure | 62,124,149 | SDK queue backpressure. |
| client_discard / network_error | 2,146,267 | |
| client_discard / send_error | 467,446 | |
| client_discard / before_send | 205,231 | |
| filtered / web-crawlers | 190,611 | |
| invalid / too_large:span | 72,685 | |
| Other (cache_overflow, queue_overflow, filtered-transaction, invalid_transaction, no_parent_span, legacy-browsers) | < 0.1M combined | |

**Confirmed:** the dominant server-side drop is `span_usage_exceeded`, which means spans are being rejected because the org quota is used up. The client-side `ratelimit_backoff` (1.75B) is the SDK's response to that same rate limiting. The `sample_rate` drop (362M) is an intentional SDK-side sampling decision and is not an error.

**Also important:** the `find_dropped_events` output is not split by project in this summary. The per-project breakdown is still needed.

---

## 6. Root causes

### Confirmed facts
1. Span quota is exhausted. The org has been rate-limited on spans since at least 2026-09-29.
2. `rebm` and `hawkeye` produce ~98% of observed span volume.
3. Django framework spans (`event.django`, `middleware.django`) and DB spans dominate both projects.
4. `ios`, `android`, and `rebotics-frontend` are small (< 1% each).

### Hypotheses (not yet verified)
- **H1: instrumentation growth.** Recent code added Django integration spans or an additional middleware/signal handler, raising `event.django` volume. Needs a release-level comparison (`release` grouping) to confirm.
- **H2: traffic growth or polling loops.** High `http.server` (26.4M in `hawkeye`) and `view.response.render` counts suggest high request volume, possibly from polling or retry loops. Needs endpoint-level and transaction-level breakdown.
- **H3: `db` spans without diagnostic value.** `db` is 26% of `hawkeye`. Duplicate or per-row queries in loops are plausible. Needs a query-text and `transaction` breakdown.
- **H4: dev/staging traffic sent to the production project.** Not checked. Needs an `environment` breakdown.

The "increase" in usage cannot be confirmed from this data. No prior-period baseline has been measured.

---

## 7. Billing and cost attribution

**Not available through the connected MCP tools used in this audit.**

Missing items, and where to get them:
- Plan, span quota per billing period, and current usage: *Sentry → Settings → Subscription* (`https://sentry.io/settings/retech-labs/billing/`), or the billing API `GET /api/0/customers/retech-labs/`.
- Historical usage by category (spans vs. transactions vs. errors): *Settings → Subscription → Usage Stats*, or the `stats_v2` API (`GET /api/0/organizations/retech-labs/stats_v2/` with `category=span`).
- Overage and pricing: the Subscription page. No price per span was assumed.

Per-project trend (current vs. previous period): run `search_traces` with `period=7d` and `period=14d` per project, or use the Explore UI. Not run.

---

## 8. Sampling and instrumentation

Not verified in this audit. The SDK configuration (`tracesSampleRate`, `tracesSampler`, `DjangoIntegration` options, `middleware` instrumentation) lives in the application repositories for `rebm` and `hawkeye`. Those repos are not in this workspace, and the MCP tools cannot read SDK settings. The `sample_rate` client drops (362M) show some sampling already exists on the SDK side, but its rate is unknown.

Before changing config, verify the Django SDK version and its supported options against the official docs, because `event.django` and `middleware.django` are integration-level spans and may be controlled by integration flags rather than `tracesSampleRate`.

---

## 9. Proposed optimizations (not implemented)

| # | Change | Projects | Expected effect | Confidence | Risk | Approval needed |
|---|---|---|---|---|---|---|
| A | Confirm the span quota and raise it temporarily, or reduce the spend cap, to restore ingestion | org | Restores telemetry immediately | High (quota drop confirmed) | Cost | Yes (billing decision) |
| B | Lower the number of Django integration spans (`event.django`, `middleware.django`) through integration options or by excluding noisy middleware | `rebm`, `hawkeye` | Could remove the majority of spans (71.8% and 50.4% of the two projects) | Medium (needs code check) | Lower diagnostic detail for middleware | Yes |
| C | Sample `db` and `http.client` spans in the SDK (for example, a lower `tracesSampleRate` for non-error transactions) | `hawkeye` (db 26%), `rebm` | Proportional to sampled share | Medium | Less DB visibility | Yes |
| D | Find and filter known high-frequency transactions (polling, health checks, retries) through `before_send_transaction` | `hawkeye` (http.server 26.4M) | Depends on the transaction breakdown | Unknown until breakdown done | Low if verified | Yes |
| E | Confirm `environment` split and remove non-production traffic from the production project | all | Unknown | Unknown | Low | Yes |

Savings estimates are not calculated. No monetary value can be stated without pricing and a baseline (section 7).

---

## 10. Production observability risks

- **The org is losing span data now.** Any production performance investigation since 2026-09-29 has a gap. Errors may also be affected if the quota covers all categories. Check whether error ingestion is also dropped (run `find_dropped_events` with `dataset=errors`; not run in this audit).
- Reducing `event.django` or `middleware.django` removes framework context from traces. Keep `db` and `http.server` spans for transactions that have errors or high latency.
- Sampling reduces the number of transactions, so latency percentiles are based on fewer data points. Keep the rate high for `hawkeye` and `rebm` until the breakdown supports a change.

---

## 11. Prioritized implementation plan

1. **Today:** Check span quota and usage in Sentry billing (section 7). Decide whether to raise the quota or accept a gap.
2. **Today:** Confirm error ingestion is not also being dropped (`find_dropped_events`, dataset `errors`).
3. **This week:** Run the breakdowns still missing: `transaction` and `release` grouping for `rebm` and `hawkeye`; `environment` grouping for all projects; per-project 7-day vs. prior-7-day trend.
4. **This week:** Review SDK init in the `rebm` and `hawkeye` repos for `DjangoIntegration` options and `tracesSampleRate`/`tracesSampler`.
5. **After approval:** Apply the lowest-risk change first (B or C in a staging project), then measure. Compare `span_usage_exceeded` drops and accepted volume over 7 days.

---

## 12. Verification and rollback

**Verify:** After each change, repeat the section 3 query for `rebm` and `hawkeye` (7-day window) and `find_dropped_events` with `reason=span_usage_exceeded`. Expect accepted volume to fall and drops to fall. Compare `event.django` counts before and after.

**Rollback:** Revert the SDK config or integration change in the application repo and redeploy. For a quota change, revert the subscription/spend-cap setting in Sentry billing.

---

## 13. Unavailable data and how to get it

| Missing | How to obtain |
|---|---|
| Plan, span quota, current usage, overage | Sentry Settings → Subscription; `GET /api/0/customers/retech-labs/` |
| Historical usage by category | Settings → Subscription → Usage Stats; `GET /api/0/organizations/retech-labs/stats_v2/` |
| Prior-period span counts | `search_traces` with `period=7d` / `14d` per project |
| Transaction-level breakdown | `search_traces` grouped by `transaction` per project |
| Release-level growth | `search_traces` grouped by `release` (or Release Health UI) |
| Per-project drop reasons | `find_dropped_events` with `projectSlug` set |
| Error ingestion drops | `find_dropped_events` with `dataset=errors` |
| SDK sampling config and integrations | Application repos for `rebm` and `hawkeye` (not in this workspace) |

---

## 14. Correction (2026-10-12): stored vs extrapolated spans

The span counts in sections 3 and 4 use Sentry's `count()`, which is **extrapolated** by sample rate. Billing counts **stored** spans, which `count_sample()` returns. Re-run with both (30 days, grouped by project and environment):

| Project / environment | Extrapolated `count()` | Stored `count_sample()` | Kept |
|---|---|---|---|
| rebm / krcs | 308.6M | **180.1M** | 58% |
| rebm / albt | 78.6M | 29.5M | 38% |
| rebm / krog | 27.6M | 25.2M | 91% |
| rebm / harr | 19.7M | 10.8M | 55% |
| rebm / prgm | 15.6M | 10.6M | 68% |
| rebm / qktp | 193.9M | 3.4M | 1.8% |
| rebm, all environments in top 25 | — | **~276M** | — |
| hawkeye / epsilon | 1.79M | 1.79M | 100% |
| hawkeye / stgalbt | 1.42M | 1.42M | 100% |
| rebotics-frontend / production | 3.67M | 3.67M | 100% |
| ios / production | 9.54M | 3.59M | 38% |
| android / production | 2.98M | 2.98M | 100% |
| race-platform / test01 + dev01 | 0.76M | 0.55M | 72% |

**Corrected conclusions**

- **rebm produces about 95% of billed spans.** Its ~276M stored matches the 271.5M billed figure. hawkeye stores only about 3.2M, almost all from the `epsilon` and `stgalbt` environments, which its code samples at 100% (`hawkeye/settings/environments/prod.py`, `traces_sample_rate`). hawkeye's 316M was an extrapolation.
- **rebm ignores its own 0.1% rate in practice.** The code sets `traces_sample_rate=0.001` (`rebotics-management-django/config/settings/components/sentry.py`; also `deploy/production/django/scripts/run_dramatiq.py`), yet krcs keeps 58% and krog 91%. The largest single item is `/api/v1/mobile/capture/retailer/` in krcs: 95.2M stored of 97.7M (97%).
- **Likely cause: inherited (parent-based) sampling.** With `traces_sample_rate`, the Python SDK honours an incoming "sampled" trace header. The Android app samples production at 50% (`SentryCrashMetricsService.kt`) but does not wire the OkHttp integration, so it is not confirmed as the source. The upstream caller is not yet identified.
- **Dynamic Sampling settings could not be read**: the Sentry MCP has no tool for them. Check Settings → Dynamic Sampling (org) and each project's Performance settings in the Sentry UI.
