"""Normalize task and shelf-scan timing metadata from backend payloads."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ScanEvent:
    scan_id: int
    scan_type: str
    uploaded_at: Optional[str]
    status: str
    section: str


@dataclass
class TaskScanTimeline:
    task_created_at: Optional[str] = None
    task_started_at: Optional[str] = None
    task_completed_at: Optional[str] = None
    pre_scan: Optional[ScanEvent] = None
    post_scan: Optional[ScanEvent] = None
    task_duration_seconds: Optional[int] = None
    photo_duration_seconds: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _first(payload: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def _timestamp(payload: Dict[str, Any], *keys: str) -> Optional[str]:
    value = _first(payload, *keys)
    return str(value) if value is not None else None


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _duration(start: Optional[str], end: Optional[str]) -> Optional[int]:
    parsed_start = _parse_timestamp(start)
    parsed_end = _parse_timestamp(end)
    if not parsed_start or not parsed_end or parsed_end < parsed_start:
        return None
    return int((parsed_end - parsed_start).total_seconds())


def _scan_type(scan: Dict[str, Any]) -> str:
    candidates = [
        scan.get("scan_type"),
        scan.get("type"),
        scan.get("photo_type"),
        (scan.get("metadata") or {}).get("scan_type")
        if isinstance(scan.get("metadata"), dict)
        else None,
    ]
    text = " ".join(str(value or "") for value in candidates).casefold()
    if scan.get("is_pre_photo") is True or "pre_photo" in text or "pre photo" in text:
        return "pre"
    if (
        scan.get("is_pre_photo") is False
        or scan.get("is_post_photo") is True
        or "post_photo" in text
        or "post photo" in text
    ):
        return "post"
    return "unknown"


def normalize_scan_events(scans: List[Dict[str, Any]]) -> List[ScanEvent]:
    events = []
    for scan in scans:
        if not isinstance(scan, dict):
            continue
        scan_id = scan.get("id") or scan.get("scan_id")
        try:
            numeric_id = int(scan_id)
        except (TypeError, ValueError):
            continue
        events.append(
            ScanEvent(
                scan_id=numeric_id,
                scan_type=_scan_type(scan),
                uploaded_at=_timestamp(
                    scan,
                    "uploaded_at",
                    "upload_completed_at",
                    "created_at",
                    "created",
                    "timestamp",
                ),
                status=str(scan.get("status") or ""),
                section=str(scan.get("section") or scan.get("section_id") or ""),
            )
        )
    return events


def build_task_scan_timeline(
    task: Optional[Dict[str, Any]],
    scans: List[Dict[str, Any]],
) -> TaskScanTimeline:
    task = task if isinstance(task, dict) else {}
    events = normalize_scan_events(scans)
    pre_events = [event for event in events if event.scan_type == "pre"]
    post_events = [event for event in events if event.scan_type == "post"]
    pre_scan = min(pre_events, key=lambda event: event.scan_id) if pre_events else None
    post_scan = max(post_events, key=lambda event: event.scan_id) if post_events else None

    created = _timestamp(task, "created_at", "created", "creation_date")
    started = _timestamp(task, "started_at", "started", "start_date")
    completed = _timestamp(
        task,
        "completed_at",
        "completed",
        "finished_at",
        "completion_date",
    )
    return TaskScanTimeline(
        task_created_at=created,
        task_started_at=started,
        task_completed_at=completed,
        pre_scan=pre_scan,
        post_scan=post_scan,
        task_duration_seconds=_duration(started or created, completed),
        photo_duration_seconds=_duration(
            pre_scan.uploaded_at if pre_scan else None,
            post_scan.uploaded_at if post_scan else None,
        ),
    )
