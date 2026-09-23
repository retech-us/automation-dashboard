"""Date-range history of Intelligent Reset task quality.

Two sources feed the same entry shape: tasks this tool has audited locally
(rich, with quality scores) and tasks listed by a backend instance (thin, but
complete for the range). A warehouse source can be added later by producing the
same entry shape and passing it in as ``remote``.
"""

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HISTORY_SCHEMA_VERSION = 1
MAX_HISTORY_ENTRIES = 1000

# Preset -> number of days to look back, inclusive of today.
RANGE_PRESETS = {
    "today": (0, "Today"),
    "7d": (6, "Last 7 days"),
    "14d": (13, "Last 14 days"),
    "30d": (29, "Last 30 days"),
}

# `start` is the scheduled work date and is what people mean by the task's date;
# `created_at` only says when the record appeared, so it comes later in the list.
_DATE_FIELDS = ("task_date", "capture_date_local", "due_date", "start", "created_at", "updated_at")


def _parse_date(value: Any) -> Optional[date]:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def resolve_range(
    preset: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    today: Optional[date] = None,
) -> Dict[str, str]:
    """Turn a preset or custom pair into an inclusive, ordered date window."""
    today = today or datetime.now(timezone.utc).date()
    key = (preset or "7d").strip().casefold()

    if key in RANGE_PRESETS:
        lookback, label = RANGE_PRESETS[key]
        return {
            "preset": key,
            "from": (today - timedelta(days=lookback)).isoformat(),
            "to": today.isoformat(),
            "label": label,
        }

    if key != "custom":
        raise ValueError(f"Unknown date range '{preset}'.")

    first, last = _parse_date(start), _parse_date(end)
    if first is None or last is None:
        raise ValueError("A custom range needs both a start and an end date (YYYY-MM-DD).")
    if first > last:
        first, last = last, first
    return {
        "preset": "custom",
        "from": first.isoformat(),
        "to": last.isoformat(),
        "label": f"{first.isoformat()} to {last.isoformat()}",
    }


def _number(value: Any) -> Optional[float]:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def entry_from_snapshot(
    snapshot: Dict[str, Any],
    task_date: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """Reduce a live scorecard to the compact row kept in history."""
    task_id = snapshot.get("task_id")
    if not task_id:
        return None

    metrics = snapshot.get("metrics") or {}
    findings = snapshot.get("findings") if isinstance(snapshot.get("findings"), list) else []
    recorded_at = (now or datetime.now(timezone.utc)).isoformat()
    generated_date = _parse_date(snapshot.get("generated_at"))
    resolved_date = _parse_date(task_date) or generated_date
    status = normalize_status(snapshot.get("task_status"))

    return {
        "task_id": task_id,
        "instance": snapshot.get("instance"),
        "task_date": resolved_date.isoformat() if resolved_date else None,
        "date_source": "task" if _parse_date(task_date) else "recorded",
        "recorded_at": recorded_at,
        "source": "local_audit",
        "audited": True,
        "status": status,
        "status_label": status_label(status),
        "title": None,
        "store_id": None,
        "gate_state": (snapshot.get("quality_gate") or {}).get("state") or "unknown",
        "post_photo_state": (snapshot.get("post_photo") or {}).get("state"),
        "overall_score_pct": _number(metrics.get("overall_score_pct")),
        "digital_alignment_pct": _number(metrics.get("digital_alignment_pct")),
        "post_alignment_pct": _number(metrics.get("post_alignment_pct")),
        "work_finished_pct": _number(metrics.get("work_finished_pct")),
        "findings_total": len(findings),
        "findings_critical": sum(
            1 for f in findings if isinstance(f, dict) and f.get("severity") == "critical"
        ),
    }


def record_entry(entries: List[Dict[str, Any]], entry: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Upsert one row keyed by instance and task, newest wins."""
    if not entry:
        return list(entries)
    key = (str(entry.get("instance")), str(entry.get("task_id")))
    kept = [
        existing
        for existing in entries
        if (str(existing.get("instance")), str(existing.get("task_id"))) != key
    ]
    kept.append(entry)
    return kept[-MAX_HISTORY_ENTRIES:]


def save_history(entries: List[Dict[str, Any]], path: Path) -> None:
    """Atomically persist history; the entry shape carries no credentials."""
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {"schema_version": HISTORY_SCHEMA_VERSION, "entries": entries[-MAX_HISTORY_ENTRIES:]}
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def load_history(path: Path) -> List[Dict[str, Any]]:
    """Read stored history; anything unreadable degrades to an empty list."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(document, dict) or document.get("schema_version") != HISTORY_SCHEMA_VERSION:
        return []
    entries = document.get("entries")
    return [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []


def _status_text(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        # `id` is the machine value ("created"); `name` is display wording ("Not started").
        for key in ("id", "slug", "name", "status"):
            if value.get(key):
                return str(value[key]).casefold()
        return None
    return str(value).casefold() if value else None


# The backend returns the same state under several spellings, e.g. "not started"
# and "not_started" in one response, so every status is collapsed to one slug.
_STATUS_ALIASES = {
    "not_started": "not_started",
    "notstarted": "not_started",
    "new": "not_started",
    "created": "not_started",
    "in_progress": "in_progress",
    "inprogress": "in_progress",
    "started": "in_progress",
    "active": "in_progress",
    "completed": "completed",
    "complete": "completed",
    "done": "completed",
    "finished": "completed",
    "incomplete": "incomplete",
    "on_hold": "on_hold",
    "hold": "on_hold",
    "paused": "on_hold",
}

_STATUS_LABELS = {
    "not_started": "Not started",
    "in_progress": "In progress",
    "completed": "Completed",
    "incomplete": "Incomplete",
    "on_hold": "On hold",
    "unknown": "Unknown",
}


def normalize_status(value: Any) -> str:
    """Collapse the backend's status spellings onto one slug per state."""
    text = _status_text(value)
    if not text:
        return "unknown"
    slug = text.strip().replace(" ", "_").replace("-", "_")
    return _STATUS_ALIASES.get(slug, slug)


def status_label(slug: str) -> str:
    """Human wording for a status slug, for people who do not read snake_case."""
    return _STATUS_LABELS.get(slug) or str(slug).replace("_", " ").capitalize()


def _named(value: Any) -> Tuple[Optional[str], Any]:
    """Pull (name, id) out of the backend's {"id": .., "name": ..} reference objects."""
    if isinstance(value, dict):
        name = value.get("name") or value.get("title")
        return (str(name) if name else None), value.get("id")
    return (str(value) if value else None), None


def normalize_instance_tasks(payload: Any, instance: Optional[str]) -> List[Dict[str, Any]]:
    """Map a backend task list onto the shared entry shape."""
    rows = payload.get("results") if isinstance(payload, dict) else payload
    entries: List[Dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        task_id = row.get("id") or row.get("task_id")
        task_date = next((_parse_date(row.get(field)) for field in _DATE_FIELDS if row.get(field)), None)
        if not task_id or task_date is None:
            continue
        store = row.get("store")
        status = normalize_status(row.get("status"))
        raw_status = row.get("status")
        type_name, type_id = _named(row.get("type"))
        category_name, _ = _named(row.get("category"))
        entries.append({
            "task_id": task_id,
            "instance": instance,
            "task_type": type_name,
            "task_type_id": type_id,
            "category": category_name,
            "task_date": task_date.isoformat(),
            "date_source": "task",
            "recorded_at": None,
            "source": "instance",
            "audited": False,
            "status": status,
            "status_label": (
                (raw_status.get("name") if isinstance(raw_status, dict) else None)
                or status_label(status)
            ),
            "title": row.get("task_def_title") or row.get("title") or None,
            "store_id": (store.get("id") if isinstance(store, dict) else None) or row.get("store_id"),
            "store_name": store.get("name") if isinstance(store, dict) else None,
            "store_custom_id": store.get("custom_id") if isinstance(store, dict) else None,
            "gate_state": "unknown",
            "post_photo_state": None,
            "overall_score_pct": None,
            "digital_alignment_pct": None,
            "post_alignment_pct": None,
            "work_finished_pct": None,
            "findings_total": 0,
            "findings_critical": 0,
        })
    return entries


def filter_entries(
    entries: List[Dict[str, Any]],
    instance: Optional[str],
    start: str,
    end: str,
    task_type: Optional[str] = None,
    statuses: Optional[List[str]] = None,
    title_contains: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Keep rows for one instance inside a date window, optionally by type, status and title."""
    first, last = _parse_date(start), _parse_date(end)
    wanted_type = (task_type or "").strip().casefold()
    if wanted_type in ("", "all"):
        wanted_type = ""
    needle = (title_contains or "").strip().casefold()
    wanted = {normalize_status(value) for value in statuses} if statuses else None

    kept = []
    for entry in entries:
        if instance and entry.get("instance") != instance:
            continue
        entry_date = _parse_date(entry.get("task_date"))
        if entry_date is None or first is None or last is None:
            continue
        if not (first <= entry_date <= last):
            continue
        if wanted_type and str(entry.get("task_type") or "").strip().casefold() != wanted_type:
            continue
        if needle and needle not in str(entry.get("title") or "").casefold():
            continue
        if wanted and normalize_status(entry.get("status")) not in wanted:
            continue
        kept.append(entry)
    return kept


def merge_entries(
    local: List[Dict[str, Any]],
    remote: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Combine both sources, preferring the audited local row, newest first."""
    merged: Dict[tuple, Dict[str, Any]] = {}
    for entry in remote:
        merged[(str(entry.get("instance")), str(entry.get("task_id")))] = dict(entry)
    for entry in local:
        key = (str(entry.get("instance")), str(entry.get("task_id")))
        thin = merged.get(key) or {}
        combined = dict(entry)
        # The audit owns the quality numbers; the instance owns what the task *is*.
        # A stale snapshot of the title or status must never mask the live one.
        for field in ("title", "store_id", "store_name", "store_custom_id", "task_type", "task_type_id", "category"):
            if thin.get(field):
                combined[field] = thin[field]
            else:
                combined[field] = combined.get(field)
        if thin.get("status"):
            combined["status"] = thin["status"]
            combined["status_label"] = thin.get("status_label") or status_label(thin["status"])
        merged[key] = combined
    return sorted(
        merged.values(),
        key=lambda e: (e.get("task_date") or "", str(e.get("task_id"))),
        reverse=True,
    )


def cache_lookup(
    cache: Dict[Any, Any],
    key: Any,
    now: float,
    ttl_seconds: float,
) -> Optional[List[Dict[str, Any]]]:
    """Return cached rows while they are fresh, so re-filtering costs no network."""
    stored = cache.get(key)
    if not stored:
        return None
    fetched_at, entries = stored
    if now - fetched_at > ttl_seconds:
        cache.pop(key, None)
        return None
    return entries


def cache_store(cache: Dict[Any, Any], key: Any, now: float, entries: List[Dict[str, Any]]) -> None:
    cache[key] = (now, entries)


def _status_counts(tasks: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for task in tasks:
        slug = normalize_status(task.get("status"))
        counts[slug] = counts.get(slug, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _facets(entries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Offer only the types and statuses the instance actually returned."""
    types: Dict[str, int] = {}
    statuses: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        name = str(entry.get("task_type") or "").strip()
        if name:
            types[name] = types.get(name, 0) + 1
        slug = normalize_status(entry.get("status"))
        bucket = statuses.setdefault(slug, {
            "value": slug,
            "label": entry.get("status_label") or status_label(slug),
            "count": 0,
        })
        bucket["count"] += 1
    return {
        "types": [
            {"value": name, "label": name, "count": count}
            for name, count in sorted(types.items(), key=lambda item: (-item[1], item[0]))
        ],
        "statuses": sorted(statuses.values(), key=lambda item: (-item["count"], item["value"])),
    }


def _average(values: List[Optional[float]]) -> Optional[float]:
    known = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
    return round(sum(known) / len(known), 1) if known else None


def build_history_view(
    local: List[Dict[str, Any]],
    remote: List[Dict[str, Any]],
    instance: Optional[str],
    range_info: Dict[str, str],
    remote_error: Optional[str] = None,
    available: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Assemble the endpoint contract the dashboard renders.

    `available` is the unfiltered set, so the dropdowns still list every choice
    once a filter has narrowed the table down.
    """
    tasks = merge_entries(local, remote)
    audited = [task for task in tasks if task.get("audited")]
    gate_pass = sum(1 for task in tasks if task.get("gate_state") == "pass")
    gate_fail = sum(1 for task in tasks if task.get("gate_state") == "fail")

    totals = {
        "tasks": len(tasks),
        "audited": len(audited),
        "not_audited": len(tasks) - len(audited),
        "gate_pass": gate_pass,
        "gate_fail": gate_fail,
        "gate_unknown": len(tasks) - gate_pass - gate_fail,
        "avg_overall_score_pct": _average([task.get("overall_score_pct") for task in tasks]),
        "avg_digital_alignment_pct": _average([task.get("digital_alignment_pct") for task in tasks]),
        "findings_critical": sum(int(task.get("findings_critical") or 0) for task in tasks),
        "status_counts": _status_counts(tasks),
    }

    label = range_info.get("label", "the selected range")
    where = f" on {instance}" if instance else ""
    if not tasks:
        summary = (
            f"No Intelligent Reset tasks were found{where} for {label}. "
            "Pick a wider range, or check the instance and sign-in."
        )
    else:
        scored = (
            f"Average quality score {totals['avg_overall_score_pct']}%. "
            if totals["avg_overall_score_pct"] is not None
            else ""
        )
        summary = (
            f"{totals['tasks']} task(s){where} for {label}. "
            f"{totals['audited']} fully checked by this tool, {totals['not_audited']} not checked yet. "
            f"{scored}{gate_pass} passed the quality gate and {gate_fail} need attention."
        )
    if remote_error:
        summary = f"{summary} {remote_error}"

    return {
        "schema_version": HISTORY_SCHEMA_VERSION,
        "instance": instance,
        "range": range_info,
        "facets": _facets(available if available is not None else tasks),
        "totals": totals,
        "plain_language_summary": summary,
        "remote_error": remote_error,
        "tasks": [
            dict(
                task,
                report_url=f"/api/runner/e2e_audit_report?task_id={task.get('task_id')}",
                audit_action="/api/runner/audit_task",
            )
            for task in tasks
        ],
    }
