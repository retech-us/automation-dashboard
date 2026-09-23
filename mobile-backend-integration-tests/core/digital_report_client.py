"""Client and boundary models for the R07 Digital Report item list."""

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class DigitalReportItem:
    scan_id: Optional[int]
    upc: str
    product_name: str
    section: str
    pog_position: str
    rog_position: str
    action_type: str
    action_taken: str
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DigitalReportFetchResult:
    ok: bool
    items: List[DigitalReportItem] = field(default_factory=list)
    error: Optional[str] = None
    status_code: Optional[int] = None
    failed_scan_ids: List[int] = field(default_factory=list)
    requested_urls: List[str] = field(default_factory=list)
    raw_payloads: List[Any] = field(default_factory=list)


def _value(row: Dict[str, Any], snake_case: str, camel_case: str) -> Any:
    value = row.get(snake_case)
    return row.get(camel_case) if value is None else value


def _first(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _product_code(*values: Any) -> str:
    """Return a usable UPC, discarding placeholders such as 'PLU not found'."""
    code = _first(*values)
    return code if any(char.isdigit() for char in code) else ""


def _normalize_action_taken(value: Any) -> str:
    text = str(value or "").strip()
    return text if text and text != "-" else "-"


def _scan_id_or_fallback(value: Any, fallback: Optional[int]) -> Optional[int]:
    try:
        return int(value) if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


def normalize_section_product_reports(
    payload: Any,
    scan_id: Optional[int] = None,
) -> List[DigitalReportItem]:
    """Normalize supported R07 response envelopes into explicit item models."""
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("results", payload.get("items", []))
    else:
        rows = []

    items = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        row_scan_id = _value(row, "scan_id", "scanId")
        product = row.get("product") if isinstance(row.get("product"), dict) else {}
        shelf_position = _first(
            _value(row, "on_shelf_position", "onShelfPosition"),
        )
        items.append(DigitalReportItem(
            scan_id=_scan_id_or_fallback(row_scan_id, scan_id),
            upc=_product_code(row.get("upc"), product.get("product_code")),
            product_name=_first(
                _value(row, "product_name", "productName"),
                product.get("name"),
            ),
            section=_first(row.get("section"), _value(row, "section_name", "sectionName")),
            pog_position=_first(
                _value(row, "pog_position", "pogPosition"),
                shelf_position,
            ),
            rog_position=_first(
                _value(row, "rog_position", "rogPosition"),
                shelf_position,
            ),
            action_type=_first(
                _value(row, "action_type", "actionType"),
                _value(row, "report_product_status", "reportProductStatus"),
            ),
            action_taken=_normalize_action_taken(
                _first(_value(row, "action_taken", "actionTaken"), row.get("reason"))
            ),
            raw=dict(row),
        ))
    return items


def fetch_section_product_reports(
    base_url: str,
    token: str,
    scan_id: int,
    opener: Optional[Callable[..., Any]] = None,
) -> DigitalReportFetchResult:
    """Fetch one scan's Digital Report rows without leaking boundary errors."""
    query = urllib.parse.urlencode({"scan_id": scan_id})
    url = (
        f"{base_url.rstrip('/')}/api/v1/reporting/R07/"
        f"section-product-reports/?{query}"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Token {token}",
        },
        method="GET",
    )
    open_request = opener or urllib.request.urlopen
    try:
        with open_request(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return DigitalReportFetchResult(
            ok=True,
            items=normalize_section_product_reports(payload, scan_id=scan_id),
            status_code=200,
            requested_urls=[url],
            raw_payloads=[payload],
        )
    except urllib.error.HTTPError as error:
        return DigitalReportFetchResult(
            ok=False,
            error=f"HTTP {error.code} {error.reason}",
            status_code=error.code,
            requested_urls=[url],
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return DigitalReportFetchResult(
            ok=False,
            error=str(error),
            requested_urls=[url],
        )


def fetch_section_product_reports_for_scans(
    base_url: str,
    token: str,
    scan_ids: List[int],
    opener: Optional[Callable[..., Any]] = None,
) -> DigitalReportFetchResult:
    """Fetch and merge one R07 item list for every unique scan ID."""
    items: List[DigitalReportItem] = []
    errors = []
    failed_scan_ids = []
    requested_urls = []
    raw_payloads = []
    unique_scan_ids = sorted(set(scan_ids))
    successful_fetches = 0
    for scan_id in unique_scan_ids:
        result = fetch_section_product_reports(
            base_url,
            token,
            scan_id,
            opener=opener,
        )
        items.extend(result.items)
        requested_urls.extend(result.requested_urls)
        raw_payloads.extend(result.raw_payloads)
        if result.ok:
            successful_fetches += 1
        else:
            errors.append(f"scan_id {scan_id}: {result.error}")
            failed_scan_ids.append(scan_id)
    return DigitalReportFetchResult(
        ok=successful_fetches > 0 or not unique_scan_ids,
        items=items,
        error="; ".join(errors) if errors else None,
        failed_scan_ids=failed_scan_ids,
        requested_urls=requested_urls,
        raw_payloads=raw_payloads,
    )
