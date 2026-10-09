"""Investigate a scan problem: what happened, the defect, the root cause, and the fix.

The checks encode the three KRCS defects already confirmed against live scans:
a product marked correct on the wrong planogram slot, a move whose source and
destination are the same slot, and a post-photo that generates that move again.
"""

import json
import ssl
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse


SlotKey = Tuple[str, str]


def parse_scan_url(value: str) -> Dict[str, str]:
    """Read scan id, store, planogram, and date from a reporting URL or a bare id."""
    text = (value or "").strip()
    if text.isdigit():
        return {"scan_id": text}
    parsed = urlparse(text)
    parts = [part for part in parsed.path.split("/") if part]
    scan_id = ""
    if "scans" in parts:
        index = parts.index("scans")
        if index + 1 < len(parts) and parts[index + 1].isdigit():
            scan_id = parts[index + 1]
    query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
    return {
        "scan_id": scan_id,
        "store": query.get("store", ""),
        "planogram": query.get("planogram", ""),
        "date": query.get("date", ""),
        "base_url": f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else "",
    }


def planogram_slots(rows: Iterable[Dict[str, Any]], upc_by_product_id: Dict[str, Dict[str, str]]) -> Dict[SlotKey, Dict[str, str]]:
    """Map section + product-order slot to the planogram UPC.

    Horizontal facings stay one product-order position. Position 1 with five
    facings is slot ``1``, not positions 1 through 5.
    """
    grouped: Dict[Tuple[str, int], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        section = str(row.get("section") or "")
        shelf = row.get("shelf")
        if not section or shelf is None:
            continue
        grouped[(section, int(shelf))].append(row)

    slots: Dict[SlotKey, Dict[str, str]] = {}
    for (section, shelf), items in grouped.items():
        for ordinal, row in enumerate(sorted(items, key=lambda item: int(item.get("position") or 0)), start=1):
            product = row.get("product") if isinstance(row.get("product"), dict) else {}
            meta = upc_by_product_id.get(str(product.get("id")), {})
            slots[(section, f"{shelf}:{ordinal}")] = {
                "upc": str(meta.get("upc") or ""),
                "name": str(meta.get("title") or product.get("name") or ""),
            }
    return slots


def compare_realogram_positions(scans: List[Dict[str, Any]], slots: Dict[SlotKey, Dict[str, str]]) -> Dict[str, Any]:
    """Count detected products whose realogram slot is not their planogram slot."""
    homes: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for (section, slot), expected in slots.items():
        if expected.get("upc"):
            homes[expected["upc"]].append((section, slot))

    by_stage: Dict[str, Dict[str, Any]] = {}
    for scan in scans:
        section = str(scan.get("section") or "")
        stage = str(scan.get("stage") or "scan")
        bucket = by_stage.setdefault(stage, {"same": {}, "different": {}, "absent": {}})
        for item in scan.get("items") or []:
            upc = str(item.get("upc") or "")
            slot = str(item.get("pos") or "")
            if item.get("type") == "missing" or not upc or not slot:
                continue
            key = (section, upc, slot)
            home = homes.get(upc, [])
            record = {
                "section": section,
                "slot": slot,
                "upc": upc,
                "product": item.get("label") or "",
                "belongs_at": ", ".join(f"{home_section} {home_slot}" for home_section, home_slot in home),
            }
            if any(home_section == section and home_slot == slot for home_section, home_slot in home):
                bucket["same"][key] = record
            elif home:
                bucket["different"][key] = record
            else:
                bucket["absent"][key] = record

    stages = {
        stage: {
            "same_position": len(bucket["same"]),
            "different_position": len(bucket["different"]),
            "not_on_planogram": len(bucket["absent"]),
            "detected_products": len(bucket["same"]) + len(bucket["different"]) + len(bucket["absent"]),
            "examples": list(bucket["different"].values())[:20],
        }
        for stage, bucket in by_stage.items()
    }
    chosen = "pre_photo" if "pre_photo" in stages else next(iter(stages), "")
    selected = stages.get(chosen, {})
    return {
        "stage": chosen,
        "by_stage": stages,
        "detected_products": selected.get("detected_products", 0),
        "same_position": selected.get("same_position", 0),
        "different_position": selected.get("different_position", 0),
        "not_on_planogram": selected.get("not_on_planogram", 0),
        "examples": selected.get("examples", []),
    }


def _focus(problem: str) -> str:
    text = (problem or "").lower()
    if "post" in text:
        return "post_photo"
    if "set aside" in text or "same slot" in text or "same action" in text:
        return "same_slot"
    if "ok" in text or "correct" in text:
        return "wrong_slot_ok"
    return "all"


def investigate_issue(
    problem: str,
    scans: List[Dict[str, Any]],
    slots: Dict[SlotKey, Dict[str, str]],
) -> Dict[str, Any]:
    """Classify scan evidence into a finding, a root cause, and a fix."""
    homes: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for (section, slot), expected in slots.items():
        if expected.get("upc"):
            homes[(section, expected["upc"])].append(slot)

    wrong_slot = []
    same_slot = []
    post_repeat = []
    pre_same = {}
    for scan in scans:
        section = str(scan.get("section") or "")
        stage = str(scan.get("stage") or "")
        present = {
            (item.get("upc"), item.get("pos"))
            for item in scan.get("items") or []
            if item.get("type") != "missing" and item.get("upc") and item.get("pos")
        }
        for item in scan.get("items") or []:
            slot = str(item.get("pos") or "")
            expected = slots.get((section, slot))
            if item.get("action_type") != "ACTION_CORRECT" or not expected or not expected.get("upc"):
                continue
            if item.get("upc") == expected["upc"]:
                continue
            home_shelf = {value.split(":", 1)[0] for value in homes.get((section, item.get("upc")), [])}
            if slot.split(":", 1)[0] not in home_shelf:
                continue
            wrong_slot.append({
                "code": "OK_ON_WRONG_SLOT",
                "section": section,
                "stage": stage,
                "scan_id": scan.get("id"),
                "slot": slot,
                "upc": item.get("upc"),
                "product": item.get("label") or "",
                "expected_upc": expected["upc"],
                "expected_product": expected["name"],
                "belongs_at": ", ".join(homes.get((section, item.get("upc")), [])),
            })
        for action in scan.get("actions") or []:
            source = str(action.get("from") or "")
            target = str(action.get("to") or "")
            if not source or source != target:
                continue
            expected = slots.get((section, source))
            if not expected or action.get("upc") != expected.get("upc"):
                continue
            if (action.get("upc"), source) not in present:
                continue
            row = {
                "code": "SAME_SLOT_ACTION",
                "section": section,
                "stage": stage,
                "scan_id": scan.get("id"),
                "slot": source,
                "upc": action.get("upc"),
                "product": expected.get("name") or "",
                "reason": action.get("reason") or "",
                "move": f"{source} → {target}",
            }
            same_slot.append(row)
            if stage == "pre_photo":
                pre_same[(section, action.get("upc"), source)] = row

    for row in same_slot:
        if row["stage"] == "post_photo" and (row["section"], row["upc"], row["slot"]) in pre_same:
            post_repeat.append({**row, "code": "POST_PHOTO_REPEATS_SAME_SLOT"})

    focus = _focus(problem)
    counts = {
        "scans": len(scans),
        "wrong_slot_ok": len({(row["section"], row["slot"], row["upc"]) for row in wrong_slot}),
        "same_slot_actions": len(same_slot),
        "post_photo_repeats": len(post_repeat),
    }
    return {
        "focus": focus,
        "what_happened": _what_happened(scans, counts),
        "problem": _problem(focus, counts),
        "root_cause": _root_cause(focus),
        "how_to_solve": _how_to_solve(focus),
        "counts": counts,
        "findings": _selected(focus, wrong_slot, same_slot, post_repeat)[:40],
    }


def _what_happened(scans: List[Dict[str, Any]], counts: Dict[str, int]) -> str:
    sections = sorted({str(scan.get("section") or "") for scan in scans if scan.get("section")})
    stages = sorted({str(scan.get("stage") or "") for scan in scans if scan.get("stage")})
    return (
        f"Checked {counts['scans']} scan(s) across sections {', '.join(sections) or 'unknown'} "
        f"({', '.join(stages) or 'unknown stage'}). "
        f"{counts['wrong_slot_ok']} products are marked correct on the wrong slot, "
        f"{counts['same_slot_actions']} actions move a product to the slot it is already in, "
        f"and {counts['post_photo_repeats']} of those same-slot actions are repeated on the post-photo."
    )


def _problem(focus: str, counts: Dict[str, int]) -> str:
    if focus == "post_photo":
        return (
            f"Post-photo processing asks for {counts['post_photo_repeats']} actions on products "
            "that were already in the correct slot on the pre-photo."
        )
    if focus == "same_slot":
        return (
            f"{counts['same_slot_actions']} actions tell the associate to move a product "
            "from a slot to that same slot."
        )
    if focus == "wrong_slot_ok":
        return (
            f"{counts['wrong_slot_ok']} products are marked ok even though the UPC in the slot "
            "is not the planogram UPC."
        )
    return (
        "The scan is mixing three defects: ok on the wrong slot, a move to the same slot, "
        "and a post-photo that generates that move again."
    )


def _root_cause(focus: str) -> str:
    causes = {
        "wrong_slot_ok": (
            "ok means the UPC was recognized on that shelf. ACTION_CORRECT is assigned from that shelf membership, "
            "not from an exact planogram position match. A missing product shifts the shelf, and the shifted UPCs stay green."
        ),
        "same_slot": (
            "A matched UPC is still saved as ACTION_MOVE with reason Add Item and the same source and destination. "
            "The mobile flow turns Add Item into set-aside and then place, so the associate is asked to pick the product up and put it back."
        ),
        "post_photo": (
            "Post-photo processing classifies the new photo on its own. A UPC already in its planogram slot stays ACTION_MOVE "
            "with from equal to to and state STATE_ACCEPTED, so the same accepted add is produced again. "
            "Extra facings of one planogram position are all anchored on that position, which repeats the same slot."
        ),
    }
    if focus in causes:
        return causes[focus]
    return " ".join(causes.values())


def _how_to_solve(focus: str) -> str:
    rules = [
        "Mark a product ACTION_CORRECT only when its realogram slot UPC equals the planogram UPC for that slot.",
        "Do not emit ACTION_MOVE when from and to are the same slot. Leave that product out of the action list.",
        "Do not turn a same-slot Add Item into a set-aside.",
        "On post-photo, do not generate a new move for a UPC that already matches its planogram slot.",
        "Count extra facings separately. Do not anchor every facing on the planogram start position and ask for the same move.",
    ]
    if focus == "wrong_slot_ok":
        return rules[0]
    if focus == "same_slot":
        return " ".join(rules[1:3])
    if focus == "post_photo":
        return " ".join(rules[3:])
    return " ".join(rules)


def fetch_investigation(base_url: str, token: str, scan_url: str, problem: str = "", opener: Optional[Callable[..., Any]] = None) -> Dict[str, Any]:
    """Load the scan, its section pair, and the planogram, then investigate."""
    parsed = parse_scan_url(scan_url)
    scan_id = parsed.get("scan_id")
    if not scan_id:
        raise ValueError("Enter a scan URL or a scan id")
    host = parsed.get("base_url") or base_url
    if not host:
        raise ValueError("Enter the instance URL")
    open_request = opener or _default_opener

    opened = _get_json(open_request, host, token, f"/api/v4/processing/actions/{scan_id}/")
    planogram = (opened.get("store_planogram") or {}).get("planogram") or {}
    planogram_id = parsed.get("planogram") or str(planogram.get("id") or "")
    store_id = parsed.get("store") or str(opened.get("store_id") or "")
    date = parsed.get("date") or str(opened.get("captured_at") or "")[:10]
    summaries = _matching_scans(open_request, host, token, store_id, planogram_id, date, opened.get("planogram_id"))
    if not summaries:
        summaries = [{"id": opened.get("id"), "section": opened.get("section"), "stage": opened.get("stage")}]
    details = {str(opened.get("id")): opened}
    pending = [row["id"] for row in summaries if str(row.get("id")) != str(opened.get("id"))]
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_get_json, open_request, host, token, f"/api/v4/processing/actions/{scan_id}/") for scan_id in pending]
        for future in as_completed(futures):
            payload = future.result()
            details[str(payload.get("id"))] = payload

    pog_rows = _planogram_rows(open_request, host, token, planogram_id)
    sections = {str(row.get("section")) for row in summaries}
    product_ids = sorted({
        str((row.get("product") or {}).get("id"))
        for row in pog_rows
        if str(row.get("section")) in sections and (row.get("product") or {}).get("id") is not None
    })
    upc_by_product_id = _product_upcs(open_request, host, token, product_ids)
    scans = [_compact_scan(details[str(row["id"])]) for row in summaries if str(row.get("id")) in details]
    report = investigate_issue(problem, scans, planogram_slots(pog_rows, upc_by_product_id))
    report["scan"] = {
        "id": opened.get("id"),
        "section": opened.get("section"),
        "stage": opened.get("stage"),
        "store": opened.get("store_name"),
        "planogram": planogram.get("title") or planogram_id,
    }
    return report


def placement_for_task_scans(
    base_url: str,
    token: str,
    scan_rows: List[Dict[str, Any]],
    fallback_planogram_id: str = "",
    opener: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """Compare every scan linked to a task with its planogram product-order slots."""
    scan_ids = []
    for row in scan_rows or []:
        scan_id = row.get("id")
        if scan_id and scan_id not in scan_ids:
            scan_ids.append(scan_id)
    if not scan_ids:
        return {"status": "unavailable", "error": "This task has no linked scans"}
    open_request = opener or _default_opener
    details = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [
            pool.submit(_get_json, open_request, base_url, token, f"/api/v4/processing/actions/{scan_id}/")
            for scan_id in scan_ids[:20]
        ]
        for future in as_completed(futures):
            details.append(future.result())
    planogram = ((details[0].get("store_planogram") or {}).get("planogram") or {}) if details else {}
    planogram_id = str(planogram.get("id") or fallback_planogram_id or "")
    pog_rows = _planogram_rows(open_request, base_url, token, planogram_id)
    sections = {str(payload.get("section")) for payload in details}
    product_ids = sorted({
        str((row.get("product") or {}).get("id"))
        for row in pog_rows
        if str(row.get("section")) in sections and (row.get("product") or {}).get("id") is not None
    })
    report = compare_realogram_positions(
        [_compact_scan(payload) for payload in details],
        planogram_slots(pog_rows, _product_upcs(open_request, base_url, token, product_ids)),
    )
    report["status"] = "ready"
    report["planogram"] = planogram.get("title") or planogram_id
    report["scans"] = len(details)
    return report


def investigate_scan_problem(base_url: str, token: str, problem: str, scan_url: str, opener: Optional[Callable[..., Any]] = None) -> Dict[str, Any]:
    """Fetch live evidence and answer the problem the user described."""
    return fetch_investigation(base_url, token, scan_url, problem=problem, opener=opener)


def _default_opener(request, timeout=40):
    return urllib.request.urlopen(request, context=ssl._create_unverified_context(), timeout=timeout)


def _get_json(opener, base_url: str, token: str, path: str) -> Dict[str, Any]:
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        headers={"Accept": "application/json", "Authorization": f"Token {token}"},
    )
    with opener(request, timeout=40) as response:
        return json.loads(response.read().decode("utf-8"))


def _matching_scans(opener, base_url, token, store_id, planogram_public_id, date, store_planogram_id) -> List[Dict[str, Any]]:
    if not store_id or not date:
        return []
    query = urllib.parse.urlencode({"store": store_id, "planogram": planogram_public_id, "date": date, "limit": 50})
    url = f"/api/v4/processing/actions/?{query}"
    matched = []
    pages = 0
    while url and pages < 8:
        page = _get_json(opener, base_url, token, url)
        for row in page.get("results") or []:
            if store_planogram_id and row.get("planogram_id") not in (None, store_planogram_id) and row.get("store_planogram_id") not in (None, store_planogram_id):
                continue
            if store_planogram_id and row.get("planogram_id") != store_planogram_id and row.get("store_planogram_id") != store_planogram_id:
                continue
            matched.append({"id": row.get("id"), "section": row.get("section"), "stage": row.get("stage")})
        next_url = page.get("next") or ""
        url = urllib.parse.urlparse(next_url).path + (("?" + urllib.parse.urlparse(next_url).query) if next_url else "")
        pages += 1
    return matched


def _planogram_rows(opener, base_url, token, planogram_id) -> List[Dict[str, Any]]:
    if not planogram_id:
        return []
    payload = _get_json(opener, base_url, token, f"/api/v1/planograms/{planogram_id}/items/?limit=1000")
    return payload.get("results") or []


def _product_upcs(opener, base_url, token, product_ids: List[str]) -> Dict[str, Dict[str, str]]:
    found = {}

    def fetch(product_id: str):
        payload = _get_json(opener, base_url, token, f"/api/v4/products/{product_id}/")
        return product_id, {"upc": payload.get("upc") or "", "title": payload.get("title") or ""}

    with ThreadPoolExecutor(max_workers=8) as pool:
        for future in as_completed([pool.submit(fetch, product_id) for product_id in product_ids]):
            product_id, meta = future.result()
            found[product_id] = meta
    return found


def _compact_scan(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": payload.get("id"),
        "section": payload.get("section"),
        "stage": payload.get("stage"),
        "items": [
            {
                "upc": item.get("upc"),
                "label": item.get("label"),
                "pos": item.get("on_shelf_position"),
                "action_type": item.get("action_type"),
                "type": item.get("type"),
            }
            for item in payload.get("items") or []
        ],
        "actions": [
            {
                "upc": action.get("upc"),
                "action": action.get("action"),
                "reason": action.get("reason"),
                "from": action.get("from"),
                "to": action.get("to"),
                "state": action.get("state"),
            }
            for action in payload.get("report_actions") or []
        ],
    }


def _selected(focus: str, wrong_slot: List[Dict[str, Any]], same_slot: List[Dict[str, Any]], post_repeat: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if focus == "post_photo":
        return post_repeat or same_slot
    if focus == "same_slot":
        return same_slot
    if focus == "wrong_slot_ok":
        return wrong_slot
    return wrong_slot + same_slot + post_repeat
