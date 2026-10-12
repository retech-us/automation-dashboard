#!/usr/bin/env python3
"""
Fetch live Sentry span usage for the dashboard's Sentry tab.

Writes data/sentry-live.json from the Sentry REST API:
  - stats_v2 (category span, daily, by outcome/reason): accepted vs dropped per day and per month
  - stats_v2 per category over the billing period: billed usage for spans, errors, replays, ...
  - stats_v2 (category span, by project, accepted): billed spans per project this period
  - events (dataset spans): stored (count_sample) vs extrapolated (count) spans by project/environment,
    and stored spans by span.op for the top projects
  - customers endpoint (best effort): billing period and reserved quotas

Env:
  SENTRY_AUTH_TOKEN  required (org:read, project:read; org:billing for the customers endpoint)
  SENTRY_ORG         default "retech-labs"
  SENTRY_BASE_URL    default "https://sentry.io"

Never fails the dashboard build: on missing token or API errors it writes the file with "errors".
"""

import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

SENTRY_AUTH_TOKEN = os.environ.get("SENTRY_AUTH_TOKEN", "").strip()
SENTRY_ORG = os.environ.get("SENTRY_ORG", "retech-labs").strip() or "retech-labs"
SENTRY_BASE_URL = (os.environ.get("SENTRY_BASE_URL", "https://sentry.io").strip() or "https://sentry.io").rstrip("/")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "sentry-live.json")
CONFIG_FILE = os.path.join(DATA_DIR, "sentry-config.json")

# stats_v2 category -> dashboard feature name (matches plan.features[].feature in sentry-config.json)
USAGE_CATEGORIES = {
    "error": "Errors",
    "log_byte": "Logs",
    "replay": "Replays",
    "span": "Spans",
    "attachment": "Attachments",
    "profile_duration_ui": "UI Profile Hours",
    "profile_duration": "Continuous Profile Hours",
    "monitor_seat": "Cron Monitors",
    "uptime": "Uptime Monitors",
}
# Profile durations are reported in milliseconds.
MS_PER_HOUR = 3_600_000
BYTE_CATEGORIES = {"attachment", "log_byte"}
BYTES_PER_GB = 1_000_000_000
QUOTA_REASON = "span_usage_exceeded"
STATS_PERIOD = "90d"  # stats_v2 retention
TOP_PROJECTS_FOR_OPS = 2


def api_get(path, params=None):
    query = urllib.parse.urlencode(params or [], doseq=True)
    url = f"{SENTRY_BASE_URL}/api/0/{path.lstrip('/')}" + (f"?{query}" if query else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {SENTRY_AUTH_TOKEN}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def stats_v2(params):
    base = [("field", "sum(quantity)")]
    return api_get(f"organizations/{SENTRY_ORG}/stats_v2/", base + list(params))


def load_config():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def billing_period(customer, config):
    """Prefer the subscription's on-demand period; fall back to the config's period."""
    start = (customer or {}).get("onDemandPeriodStart")
    end = (customer or {}).get("onDemandPeriodEnd")
    if start and end:
        return {"start": start[:10], "end": end[:10], "source": "sentry-subscription"}
    cfg = ((config.get("plan") or {}).get("billing_period")) or {}
    if cfg.get("start") and cfg.get("end"):
        return {"start": cfg["start"], "end": cfg["end"], "source": "config"}
    today = datetime.date.today()
    first = today.replace(day=1)
    next_first = (first + datetime.timedelta(days=32)).replace(day=1)
    return {
        "start": first.isoformat(),
        "end": (next_first - datetime.timedelta(days=1)).isoformat(),
        "source": "calendar-month",
    }


def reserved_quotas(customer):
    """Reserved (included) volume per stats category from the subscription, when exposed."""
    out = {}
    categories = (customer or {}).get("categories") or {}
    # Subscription categories are plural (errors, spans, replays, logBytes, ...).
    plural = {
        "errors": "error", "spans": "span", "replays": "replay", "attachments": "attachment",
        "logBytes": "log_byte", "monitorSeats": "monitor_seat", "uptime": "uptime",
        "profileDurationUI": "profile_duration_ui", "profileDuration": "profile_duration",
    }
    for key, info in categories.items():
        cat = plural.get(key)
        if cat and isinstance(info, dict) and info.get("reserved") is not None:
            # Reserved byte volumes are reported in GB; usage from stats_v2 is in bytes.
            out[cat] = info["reserved"] * BYTES_PER_GB if cat in BYTE_CATEGORIES else info["reserved"]
    return out


def daily_span_outcomes():
    """Per-day accepted, quota-dropped and all-dropped spans over the stats retention window."""
    resp = stats_v2([
        ("category", "span"), ("interval", "1d"), ("statsPeriod", STATS_PERIOD),
        ("groupBy", "outcome"), ("groupBy", "reason"),
    ])
    days = [i[:10] for i in resp.get("intervals", [])]
    accepted = [0] * len(days)
    quota = [0] * len(days)
    dropped = [0] * len(days)
    reasons = defaultdict(int)
    for group in resp.get("groups", []):
        by = group.get("by", {})
        series = (group.get("series") or {}).get("sum(quantity)") or [0] * len(days)
        outcome = by.get("outcome")
        reason = by.get("reason") or "none"
        for i, v in enumerate(series[: len(days)]):
            v = v or 0
            if outcome == "accepted":
                accepted[i] += v
            else:
                dropped[i] += v
                if reason == QUOTA_REASON:
                    quota[i] += v
        if outcome != "accepted":
            reasons[f"{outcome}/{reason}"] += sum(v or 0 for v in series)
    daily = [
        {"date": d, "accepted": accepted[i], "quota_dropped": quota[i], "dropped": dropped[i]}
        for i, d in enumerate(days)
    ]
    return daily, dict(sorted(reasons.items(), key=lambda kv: -kv[1]))


def months_from_daily(daily):
    """Calendar-month totals; days_covered counts the days present in the window."""
    months = {}
    for row in daily:
        key = row["date"][:7]
        m = months.setdefault(key, {
            "month": key, "days_covered": 0, "accepted_total": 0, "quota_dropped": 0, "all_dropped": 0,
        })
        m["days_covered"] += 1
        m["accepted_total"] += row["accepted"]
        m["quota_dropped"] += row["quota_dropped"]
        m["all_dropped"] += row["dropped"]
    return [months[k] for k in sorted(months)]


def period_usage(period):
    """Accepted (billed) volume per category over the billing period, to today."""
    end = min(datetime.date.fromisoformat(period["end"]), datetime.date.today())
    usage = {}
    for category in USAGE_CATEGORIES:
        try:
            resp = stats_v2([
                ("category", category), ("interval", "1d"), ("outcome", "accepted"),
                ("start", f"{period['start']}T00:00:00Z"), ("end", f"{end.isoformat()}T23:59:59Z"),
            ])
        except urllib.error.HTTPError:
            continue  # category not enabled for this org
        total = sum(((g.get("totals") or {}).get("sum(quantity)") or 0) for g in resp.get("groups", []))
        if category.startswith("profile_duration"):
            total = round(total / MS_PER_HOUR, 2)
        usage[category] = total
    return usage


def error_drops_30d():
    resp = stats_v2([
        ("category", "error"), ("interval", "1d"), ("statsPeriod", "30d"), ("groupBy", "outcome"),
    ])
    out = defaultdict(int)
    for g in resp.get("groups", []):
        out[g.get("by", {}).get("outcome", "unknown")] += (g.get("totals") or {}).get("sum(quantity)") or 0
    return dict(out)


def project_slugs():
    # One page (100) covers this org's projects; ids that are missing fall back to the raw id.
    projects = api_get(f"organizations/{SENTRY_ORG}/projects/")
    return {str(p.get("id")): p.get("slug") for p in projects}


def projects_period(period, slugs):
    end = min(datetime.date.fromisoformat(period["end"]), datetime.date.today())
    resp = stats_v2([
        ("category", "span"), ("interval", "1d"), ("outcome", "accepted"), ("groupBy", "project"),
        ("start", f"{period['start']}T00:00:00Z"), ("end", f"{end.isoformat()}T23:59:59Z"),
    ])
    rows = []
    for g in resp.get("groups", []):
        pid = str(g.get("by", {}).get("project"))
        rows.append({
            "project": slugs.get(pid, pid),
            "accepted": (g.get("totals") or {}).get("sum(quantity)") or 0,
        })
    return sorted(rows, key=lambda r: -r["accepted"])


def span_events(fields, query="", limit=50):
    params = [("dataset", "spans"), ("statsPeriod", "30d"), ("per_page", str(limit)),
              ("sort", "-count_sample()"), ("project", "-1")]
    params += [("field", f) for f in fields]
    if query:
        params.append(("query", query))
    return api_get(f"organizations/{SENTRY_ORG}/events/", params).get("data", [])


def environments_30d():
    rows = span_events(["project", "environment", "count()", "count_sample()"])
    return [{
        "project": r.get("project"),
        "environment": r.get("environment") or "(none)",
        "stored": r.get("count_sample()") or 0,
        "extrapolated": r.get("count()") or 0,
    } for r in rows]


def span_ops_30d(projects):
    out = {}
    for project in projects:
        rows = span_events(["span.op", "count_sample()", "count()"], query=f"project:{project}", limit=15)
        out[project] = {r.get("span.op") or "(none)": r.get("count_sample()") or 0 for r in rows}
    return out


def collect():
    config = load_config()
    result = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "org": SENTRY_ORG,
        "source": "sentry-api",
        "errors": [],
    }

    def attempt(key, fn, *args):
        try:
            result[key] = fn(*args)
        except Exception as exc:  # keep partial data; report what failed
            result["errors"].append(f"{key}: {exc}")
            print(f"[Sentry Fetcher] {key} failed: {exc}")

    customer = None
    try:
        customer = api_get(f"customers/{SENTRY_ORG}/")
    except Exception as exc:
        result["errors"].append(f"subscription: {exc} (needs org:billing; plan caps fall back to config)")

    result["billing_period"] = billing_period(customer, config)
    result["reserved"] = reserved_quotas(customer)

    try:
        daily, reasons = daily_span_outcomes()
        result["daily"] = daily
        result["months"] = months_from_daily(daily)
        result["span_drop_reasons_90d"] = reasons
    except Exception as exc:
        result["errors"].append(f"daily: {exc}")

    attempt("period_usage", period_usage, result["billing_period"])
    attempt("error_outcomes_30d", error_drops_30d)
    try:
        result["projects_period"] = projects_period(result["billing_period"], project_slugs())
    except Exception as exc:
        result["errors"].append(f"projects_period: {exc}")
    attempt("environments_30d", environments_30d)

    stored = defaultdict(int)
    for row in result.get("environments_30d", []):
        stored[row["project"]] += row["stored"]
    top = [p for p, _ in sorted(stored.items(), key=lambda kv: -kv[1])[:TOP_PROJECTS_FOR_OPS]]
    if top:
        attempt("span_ops_30d", span_ops_30d, top)
    return result


def main():
    if not SENTRY_AUTH_TOKEN:
        print("[Sentry Fetcher] SENTRY_AUTH_TOKEN not set; writing empty live file.")
        data = {
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "org": SENTRY_ORG,
            "source": "unavailable",
            "errors": ["SENTRY_AUTH_TOKEN not set"],
        }
    else:
        data = collect()
        print(f"[Sentry Fetcher] Done with {len(data['errors'])} error(s).")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[Sentry Fetcher] Wrote {os.path.normpath(OUTPUT_FILE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
