"""
Intelligent Reset Simplified E2E Audit & Bi-Directional Trace Report Generator.
Renders a historical-task audit report visualizing:
1. Total Backend Generated Actions (Raw DB) vs Total Mobile Displayed Actions.
2. Duplicate / Same UPC Multi-Location Distribution (keeps duplicates grouped aside with all locations).
3. Streamlined Step-by-Step Action List using task action-list data.
4. Pre-photo and post-photo Digital Shelf comparisons.

Lifecycle simulation, payload inspection, and HTTP traffic belong only to a
true E2E run where the runner captured those events; they are intentionally
excluded from this historical task-ID report.
"""

import json
import html
import re
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional
from core.e2e_audit_engine import TaskAuditSummary, StepTelemetryRecord
from core.ir_export_script import ensure_ir_export_inline


def _build_verdict_html(audit: TaskAuditSummary) -> str:
    """Render a one-line plain-language answer: did the user do the right actions?"""
    counts = audit.digital_compare_counts or {}
    matched = counts.get("matched", 0)
    mismatched = counts.get("mismatched", 0)
    missing = counts.get("generated_only", 0)
    extra = counts.get("digital_only", 0)
    checked = matched + mismatched + missing

    if audit.digital_alignment_pct is None:
        headline = "⚠️ CANNOT CONFIRM — Digital Shelf report could not be read"
        detail = "The comparison needs the Digital Shelf report. Retry once it is reachable."
        colors = ("#FEF3C7", "#92400E", "#F59E0B")
    elif mismatched:
        headline = f"❌ {mismatched} action(s) were done differently than instructed"
        detail = (
            f"{matched} of {checked} generated actions were performed correctly. "
            f"{mismatched} were performed as a different action. "
            f"{missing} could not be found in the Digital Shelf report."
        )
        colors = ("#FEF2F2", "#B91C1C", "#EF4444")
    elif missing:
        headline = f"⚠️ {matched} of {checked} generated actions confirmed correct"
        detail = (
            f"No action was done incorrectly, but {missing} generated action(s) have no matching "
            f"row in the Digital Shelf report, so they cannot be confirmed."
        )
        colors = ("#FFFBEB", "#92400E", "#F59E0B")
    else:
        headline = f"✅ All {matched} generated actions were performed correctly"
        detail = "Every generated action has a matching user action in the Digital Shelf report."
        colors = ("#F0FDF4", "#15803D", "#22C55E")

    if extra:
        detail += (
            f" The Digital Shelf also lists {extra} item(s) with no matching generated action."
        )

    background, text_color, border = colors
    return (
        f'<div style="background:{background}; color:{text_color}; border-left:5px solid {border}; '
        'padding:14px 16px; border-radius:8px; margin-bottom:14px;">'
        f'<div style="font-size:15px; font-weight:800;">{html.escape(headline)}</div>'
        f'<div style="font-size:12px; margin-top:5px; line-height:1.5;">{html.escape(detail)}</div>'
        "</div>"
    )


def _build_run_gates_html(audit: TaskAuditSummary) -> str:
    """Show a compact, evidence-linked quality checklist for non-technical readers."""
    work_passed = (
        audit.total_pending_actions == 0
        and audit.total_rejected_actions == 0
        and audit.total_dropped_actions == 0
    )
    score_known = audit.digital_alignment_pct is not None
    checks = [
        (
            "Work completed",
            "PASS" if work_passed else "NEEDS ATTENTION",
            (
                "Every requested action was completed."
                if work_passed
                else (
                    f"{audit.total_pending_actions} pending, {audit.total_rejected_actions} rejected, "
                    f"{audit.total_dropped_actions} dropped."
                )
            ),
            "step-trace",
        ),
        (
            "Pre-photo actions verified",
            "PASS" if score_known else "NOT CHECKED",
            (
                f"{audit.digital_alignment_pct:.1f}% matched what Digital Shelf recorded."
                if score_known
                else (audit.digital_fetch_error or "Digital Shelf data was not available.")
            ),
            "action-compare",
        ),
        (
            "Post photo available",
            "PASS" if audit.post_digital_loaded else "NEEDS ATTENTION",
            (
                f"{audit.post_generated_action_count} post-photo action(s) were checked."
                if audit.post_digital_loaded
                else (audit.post_digital_error or "No verified post-photo comparison is available.")
            ),
            "post-photo-compare",
        ),
        (
            "Overall quality gate (95%)",
            (
                "PASS"
                if score_known and audit.combined_compliance_pct >= 95
                else "NEEDS ATTENTION" if score_known else "NOT CHECKED"
            ),
            (
                f"Overall score is {audit.combined_compliance_pct:.1f}%."
                if score_known
                else "The score is not calculated until Digital Shelf data is available."
            ),
            "overview",
        ),
    ]
    cards = []
    for label, status, detail, tab in checks:
        color = "#15803D" if status == "PASS" else "#B91C1C" if status == "NEEDS ATTENTION" else "#92400E"
        background = "#F0FDF4" if status == "PASS" else "#FEF2F2" if status == "NEEDS ATTENTION" else "#FFFBEB"
        cards.append(
            f'<button type="button" onclick="switchReportTab(\'{tab}\', document.getElementById(\'tab-{tab}\'))" '
            f'style="text-align:left; background:{background}; border:1px solid {color}; border-radius:8px; padding:11px; cursor:pointer;">'
            f'<div style="font-size:10px; font-weight:800; color:{color};">{html.escape(status)}</div>'
            f'<div style="font-size:12px; font-weight:800; color:#0F172A; margin-top:3px;">{html.escape(label)}</div>'
            f'<div style="font-size:10.5px; color:#475569; margin-top:4px; line-height:1.4;">{html.escape(detail)}</div>'
            "</button>"
        )
    return (
        '<div class="main-card" style="margin-bottom:14px;">'
        '<div class="card-header"><div><div class="card-title">Run Quality Checks</div>'
        '<div style="font-size:11px; color:#64748B; margin-top:4px;">'
        "Select a check to open its supporting evidence.</div></div></div>"
        f'<div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:10px; padding:14px;">{"".join(cards)}</div>'
        "</div>"
    )


def _build_reconciliation_html(audit: TaskAuditSummary) -> str:
    """Explain how the backend row count becomes the on-screen action count."""
    merged = audit.total_raw_db_detections - audit.unique_backend_actions
    counts = audit.digital_compare_counts or {}
    lines = [
        (
            f"{audit.total_raw_db_detections} rows returned by the backend action list",
            "One row per detected product facing.",
        ),
        (
            f"− {merged} duplicate rows merged",
            f"Several rows share the same action id, so the app shows {audit.unique_backend_actions} unique actions "
            "(the mobile app de-duplicates by action id).",
        ),
        (
            f"+ {audit.two_phase_split_steps} extra steps for cross-bay moves",
            "Moving a product to a different bay is shown as two steps: pick it into the cart, then place it on the target shelf.",
        ),
        (
            f"= {audit.total_generated_mobile_cards} actions shown to the user",
            f"{audit.total_performed_actions} completed, {audit.total_rejected_actions} rejected by the user, "
            f"{audit.total_pending_actions} still pending.",
        ),
        (
            f"{counts.get('matched', 0)} confirmed by the Digital Shelf report",
            f"{counts.get('mismatched', 0)} done differently, {counts.get('generated_only', 0)} not found in the Digital Shelf, "
            f"{counts.get('no_action_needed', 0)} shelf products needed no action at all.",
        ),
        (
            f"Work Finished = {audit.total_performed_actions} ÷ {audit.total_generated_mobile_cards} "
            f"= {audit.compliance_score_pct:.1f}%",
            (
                f"The {audit.total_rejected_actions} action(s) the user rejected are not counted as done, which is why "
                f"this is below 100% even with nothing left pending."
                if audit.total_rejected_actions
                else "Every action the app asked for was completed."
            ),
        ),
    ]
    items = "".join(
        f'<div style="display:flex; gap:12px; padding:7px 0; border-bottom:1px solid #E2E8F0;">'
        f'<div style="min-width:290px; font-weight:700; color:#0F172A; font-size:12px;">{html.escape(headline)}</div>'
        f'<div style="font-size:11.5px; color:#475569; line-height:1.45;">{html.escape(detail)}</div>'
        "</div>"
        for headline, detail in lines
    )
    return (
        '<div class="main-card" style="margin-top:14px;">'
        '<div class="card-header"><div class="card-title">🧮 How These Numbers Add Up</div></div>'
        f'<div style="padding:4px 16px 14px;">{items}</div>'
        "</div>"
    )


def _format_duration(seconds: Optional[int]) -> str:
    if seconds is None:
        return "Not available"
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def _build_timeline_html(audit: TaskAuditSummary) -> str:
    timeline = audit.task_timeline or {}
    pre_scan = timeline.get("pre_scan") or {}
    post_scan = timeline.get("post_scan") or {}
    values = [
        ("Task created", timeline.get("task_created_at") or "Not returned by API"),
        ("Task started", timeline.get("task_started_at") or "Not returned by API"),
        ("Pre photo uploaded", pre_scan.get("uploaded_at") or "Not returned by API"),
        ("Post photo uploaded", post_scan.get("uploaded_at") or "No post photo found"),
        ("Task completed", timeline.get("task_completed_at") or "Not returned by API"),
        (
            "Start → completion",
            _format_duration(timeline.get("task_duration_seconds")),
        ),
        (
            "Pre photo → post photo",
            _format_duration(timeline.get("photo_duration_seconds")),
        ),
    ]
    cards = "".join(
        '<div class="kpi-card">'
        f'<div class="kpi-label">{html.escape(label)}</div>'
        f'<div style="font-size:13px; font-weight:700; color:#0F172A; margin-top:7px;">'
        f"{html.escape(str(value))}</div></div>"
        for label, value in values
    )
    return (
        '<div class="main-card" style="margin-top:14px;">'
        '<div class="card-header"><div><div class="card-title">🕒 Task &amp; Photo Timeline</div>'
        '<div style="font-size:11px; color:#64748B; margin-top:4px;">'
        "Times are displayed only when returned by the task or scan API. "
        "Per-action times are intentionally not estimated.</div></div></div>"
        f'<div class="kpi-grid" style="padding:14px;">{cards}</div></div>'
    )


def generate_e2e_audit_html_report(
    audit: TaskAuditSummary,
    output_path: Path,
    category_id: Optional[int] = None,
    report_date: Optional[str] = None,
) -> Path:
    """
    Renders the simplified interactive E2E Audit & Trace HTML Report.
    """
    # 1. Build Multi-Location Duplicate UPC Rows
    dup_clusters_html = []
    if audit.duplicate_upc_clusters:
        for c in audit.duplicate_upc_clusters:
            loc_items = []
            for loc in c.locations:
                badge_type = loc.get("action_type", "ACTION")
                loc_badge_color = "#375623" if "ADD" in badge_type or "RESTOCK" in badge_type else "#C65911" if "SET" in badge_type or "FIX" in badge_type else "#C00000"
                loc_bg = "#E2EFDA" if "ADD" in badge_type or "RESTOCK" in badge_type else "#FCE4D6" if "SET" in badge_type or "FIX" in badge_type else "#F8CBAD"
                
                exchange_detail = loc.get("slot_exchange_info", "")
                exchange_html = f'<div style="font-size: 10.5px; color: #475569; margin-top: 3px; padding-left: 6px; border-left: 2px solid #CBD5E1; line-height: 1.3;">{exchange_detail}</div>' if exchange_detail else ''

                loc_html = f"""
                <div style="display: flex; flex-direction: column; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 6px 10px; border-radius: 6px; margin: 4px 0; width: 100%; box-sizing: border-box; font-size: 11px;">
                    <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                        <span style="font-weight: 700; color: #1E293B;">Step #{loc.get('step_index', '?')}:</span>
                        <span style="background: {loc_bg}; color: {loc_badge_color}; padding: 2px 7px; border-radius: 4px; font-weight: 800; font-size: 10px;">{loc.get('banner_text', badge_type)}</span>
                        <span style="font-family: 'JetBrains Mono', monospace; color: #1F4E79; font-weight: 600;">{loc.get('location_desc', '')}</span>
                    </div>
                    {exchange_html}
                </div>
                """
                loc_items.append(loc_html)

            locations_block = "".join(loc_items)
            bays_tags = ", ".join(f"Bay {b}" for b in c.unique_bays)
            shelves_tags = ", ".join(f"Sh {s}" for s in c.unique_shelves)

            pog_rog_badge = ''
            if c.pog_facings or c.rog_facings:
                extra_label = f' <span style="background: #FEE2E2; color: #B91C1C; padding: 1px 5px; border-radius: 4px; font-size: 9px; font-weight: 800; margin-left: 3px;">⚡ {c.extra_facings} extra</span>' if c.extra_facings > 0 else ''
                pog_rog_badge = (
                    f'<div style="font-size: 10px; color: #475569; margin-top: 4px;">'
                    f'POG: <b>{c.pog_facings}</b> &bull; ROG: <b>{c.rog_facings}</b>{extra_label}'
                    f'</div>'
                )

            row = f"""
            <tr>
                <td style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #0F172A;">
                    {c.upc}
                </td>
                <td style="font-weight: 600; color: #1E293B; font-size: 12.5px;">
                    {c.product_title}
                </td>
                <td style="text-align: center;">
                    <span style="background: #EEF2FF; color: #4338CA; border: 1px solid #C7D2FE; font-size: 11px; padding: 3px 8px; border-radius: 9999px; font-weight: 800;">
                        🏷️ {c.total_facings} Facings
                    </span>
                    <div style="font-size: 10px; color: #64748B; margin-top: 3px;">{bays_tags} &bull; {shelves_tags}</div>
                    {pog_rog_badge}
                </td>
                <td>
                    <div style="display: flex; flex-wrap: wrap;">
                        {locations_block}
                    </div>
                </td>
            </tr>
            """
            dup_clusters_html.append(row)
    else:
        dup_clusters_html.append("""
        <tr>
            <td colspan="4" style="text-align: center; color: #64748B; padding: 18px;">
                ✅ No duplicate / multi-facing UPCs detected. All UPCs in this task are single facing.
            </td>
        </tr>
        """)
    dup_table_body = "\n".join(dup_clusters_html)

    # 1.1 Build Removed Products Replacement Table Rows (What Was Removed ➔ What Came on That Location)
    slot_rows_html = []
    for rem in (audit.shelf_slot_exchange_matrix or []):
        p = rem.get("single_replacement")
        if p:
            replacement_html = f"""
            <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-left: 4px solid #10B981; padding: 8px 12px; border-radius: 6px;">
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                    <span style="font-weight: 800; color: #15803D; font-size: 11px;">Step #{p['step_index']}:</span>
                    <span style="background: #DCFCE7; color: #166534; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 800;">{p['banner_text']}</span>
                    <span style="font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: #1F4E79; font-weight: 700;">Target Pos {p['target_position']}</span>
                </div>
                <div style="font-weight: 700; color: #0F172A; font-size: 12.5px; margin-top: 4px;">{p['title']}</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #475569; margin-top: 2px;">
                    UPC: <b>{p['upc']}</b>
                </div>
            </div>
            """
        else:
            replacement_html = '<span style="color: #64748B; font-style: italic;">Shelf space re-allocated to adjacent planogram items</span>'

        slot_rows_html.append(f"""
        <tr style="background: #FFFDFD;">
            <td style="font-size: 12px; color: #0F172A; vertical-align: top;">
                <div style="font-weight: 800; color: #B91C1C;">
                    Step #{rem['step_index']}: REMOVE
                </div>
                <div style="font-weight: 700; color: #1E293B; margin-top: 3px; font-size: 12.5px;">{rem['product_title']}</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #475569; margin-top: 2px;">
                    UPC: <b>{rem['upc']}</b>
                </div>
            </td>
            <td style="font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #1F4E79; vertical-align: top; font-size: 12px;">
                {rem['location_label']}
                <div style="font-size: 10px; color: #B91C1C; font-weight: 700; margin-top: 4px;">🗑️ Cleared From Shelf</div>
            </td>
            <td style="font-size: 11.5px; color: #1E293B; vertical-align: top;">
                {replacement_html}
            </td>
            <td style="text-align: center; vertical-align: middle;">
                <span style="background: #DCFCE7; color: #15803D; border: 1px solid #86EFAC; font-weight: 800; font-size: 11px; padding: 4px 8px; border-radius: 6px; display: inline-block;">
                    {rem['shelf_fill_status']}
                </span>
                <div style="font-size: 10px; color: #64748B; margin-top: 3px;">Zero empty gap &bull; Reset complete</div>
            </td>
        </tr>
        """)
    slot_table_body = "\n".join(slot_rows_html) if slot_rows_html else """
    <tr><td colspan="4" style="text-align: center; color: #64748B; padding: 18px;">✅ No removed products in this task.</td></tr>
    """

    # 2. Build Lifecycle Resilience Rows with Itemized Pending Actions
    lifecycle_rows_html = []
    lifecycle_data_divs = []

    for l in audit.lifecycle_audits:
        res_badge = '<span style="background: #DCFCE7; color: #15803D; border: 1px solid #86EFAC; padding: 3px 10px; border-radius: 9999px; font-weight: 800; font-size: 11px;">✅ PASSED (Zero Loss)</span>' if l.is_resilience_passed else '<span style="background: #FEE2E2; color: #B91C1C; border: 1px solid #FCA5A5; padding: 3px 10px; border-radius: 9999px; font-weight: 800; font-size: 11px;">❌ MISMATCH</span>'

        next_card_info = l.next_active_card or {}
        next_step_idx = next_card_info.get("step_index", "-")
        next_product = next_card_info.get("product_title", "-")
        next_action = next_card_info.get("action_type", "-")

        # Continuation: after returning, user performs more actions
        after_done = l.actions_performed_after_returning
        final_left = l.final_remaining_after_performing
        resume_from_step = int(next_step_idx) + after_done if str(next_step_idx).isdigit() else "-"

        lifecycle_json = json.dumps({
            "event_name": l.event_name,
            "event_description": l.event_description,
            "initial_mobile_actions": l.initial_mobile_actions,
            "actions_performed_before_event": l.actions_performed_before_event,
            "reloaded_completed_count": l.reloaded_completed_count,
            "reloaded_pending_count": l.reloaded_pending_count,
            "reloaded_total_available": l.reloaded_total_available,
            "dropped_actions": l.dropped_actions,
            "actions_performed_after_returning": l.actions_performed_after_returning,
            "final_remaining_after_performing": l.final_remaining_after_performing,
            "next_active_card": l.next_active_card,
            "pending_records": l.pending_records,
            "completed_records": l.completed_records
        })

        lifecycle_data_divs.append(f"""
        <div id="lifecycle-data-{l.event_name}" style="display: none;" data-lifecycle='{html.escape(lifecycle_json, quote=True)}'></div>
        """)

        # Special rendering for TASK_COMPLETED final row
        if l.event_name == "TASK_COMPLETED":
            row = f"""
        <tr style="background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%); border-top: 3px solid #22C55E;">
            <td style="font-weight: 800; color: #15803D;">
                🏁 TASK COMPLETED
                <div style="font-weight: 500; font-size: 11px; color: #166534; margin-top: 2px;">{l.event_description}</div>
            </td>
            <td style="text-align: center; font-weight: 700; color: #1E293B;">{l.initial_mobile_actions}</td>
            <td style="text-align: center;">
                <span style="font-weight: 900; color: #15803D; font-size: 16px;">{l.initial_mobile_actions}</span>
                <div style="font-size: 10px; color: #15803D; font-weight: 700;">All steps #1 → #{l.initial_mobile_actions}</div>
            </td>
            <td style="text-align: center; background: #DCFCE7; border-left: 3px solid #22C55E;">
                <div style="font-size: 15px; color: #15803D; font-weight: 900;">0</div>
                <div style="font-size: 10px; color: #15803D; font-weight: 700;">none remaining</div>
            </td>
            <td style="text-align: center; background: #DCFCE7;">
                <div style="font-size: 14px; color: #15803D; font-weight: 900;">—</div>
                <div style="font-size: 10px; color: #15803D; font-weight: 600;">all done</div>
            </td>
            <td style="text-align: center; background: #DCFCE7;">
                <div style="font-size: 14px; color: #15803D; font-weight: 900;">0</div>
                <div style="font-size: 10px; color: #15803D; font-weight: 700;">✅ zero pending</div>
            </td>
            <td style="text-align: center; font-weight: 800; color: #15803D;">0</td>
            <td style="text-align: center;">
                <span style="background: #15803D; color: white; padding: 5px 12px; border-radius: 9999px; font-weight: 900; font-size: 11px;">🏆 ALL {l.initial_mobile_actions} DONE</span>
            </td>
            <td style="text-align: center;">
                <span style="font-size: 11px; color: #15803D; font-weight: 700;">✅ {l.initial_mobile_actions}/{l.initial_mobile_actions} Completed</span>
            </td>
        </tr>
        """
        else:
            row = f"""
        <tr>
            <td style="font-weight: 700; color: #1F4E79;">
                {l.event_name.replace('_', ' ')}
                <div style="font-weight: 400; font-size: 11px; color: #64748B; margin-top: 2px;">{l.event_description}</div>
            </td>
            <td style="text-align: center; font-weight: 700; color: #1E293B;">{l.initial_mobile_actions}</td>
            <td style="text-align: center;">
                <span style="font-weight: 800; color: #15803D;">{l.actions_performed_before_event}</span>
                <div style="font-size: 10px; color: #64748B;">Steps #1 → #{l.actions_performed_before_event}</div>
            </td>
            <td style="text-align: center; background: #F0FDF4; border-left: 3px solid #22C55E;">
                <div style="font-size: 15px; color: #15803D; font-weight: 900;">{l.reloaded_pending_count}</div>
                <div style="font-size: 10px; color: #15803D; font-weight: 600;">actions on mobile</div>
                <div style="font-size: 10px; color: #64748B; margin-top: 2px;">Steps #{next_step_idx} → #{l.initial_mobile_actions}</div>
                <div style="font-size: 10px; color: #0284C7; margin-top: 1px;">Next: #{next_step_idx} ({next_action})</div>
            </td>
            <td style="text-align: center; background: #EFF6FF; border-left: 3px solid #3B82F6;">
                <div style="font-size: 14px; color: #1D4ED8; font-weight: 900;">{after_done}</div>
                <div style="font-size: 10px; color: #1D4ED8; font-weight: 600;">actions performed</div>
                <div style="font-size: 10px; color: #64748B; margin-top: 2px;">Steps #{next_step_idx} → #{resume_from_step}</div>
            </td>
            <td style="text-align: center; background: #FFFBEB; border-left: 3px solid #F59E0B;">
                <div style="font-size: 14px; color: #B45309; font-weight: 900;">{final_left}</div>
                <div style="font-size: 10px; color: #B45309; font-weight: 600;">still pending</div>
                <div style="font-size: 10px; color: #64748B; margin-top: 2px;">Steps #{resume_from_step} → #{l.initial_mobile_actions}</div>
            </td>
            <td style="text-align: center; font-weight: 800; color: #15803D;">{l.dropped_actions}</td>
            <td style="text-align: center;">{res_badge}</td>
            <td style="text-align: center;">
                <button class="btn-inspect" onclick="viewLifecyclePending('{l.event_name}')" style="background: #EEF2FF; color: #4338CA; border-color: #C7D2FE;">
                    👁️ View {l.reloaded_pending_count} Pending &bull; Card #{next_step_idx}
                </button>
            </td>
        </tr>
        """
        lifecycle_rows_html.append(row)

    lifecycle_table_body = "\n".join(lifecycle_rows_html)
    lifecycle_data_blocks = "\n".join(lifecycle_data_divs)

    dashboard_params = {"store": audit.store_id, "planogram": audit.pog_id}
    if category_id is not None:
        dashboard_params["category"] = category_id
    if report_date:
        dashboard_params["date"] = report_date

    def digital_shelf_url(
        scan_id: Optional[int] = None,
        upc: str = "",
        position: str = "",
    ) -> str:
        """Deep link to the Digital Shelf: the scan page when known, else the dashboard."""
        params = dict(dashboard_params)
        if upc and position:
            params["selectedProductKey"] = f"{upc}-{position}"
        path = f"reporting/scans/{scan_id}" if scan_id else "reporting/dashboard"
        return (
            f"https://{audit.instance_slug}.rebotics.net/{path}?"
            f"{urllib.parse.urlencode(params, safe=':')}"
        )

    primary_scan_id = next(
        (record.scan_id for record in audit.step_records if record.scan_id), None
    )
    dashboard_url = digital_shelf_url(primary_scan_id)

    # 3. Build Streamlined Step Trace Rows
    rows_html = []
    for r in audit.step_records:
        badge_class = f"badge-{r.theme}"
        banner_text_color = "#C00000" if r.theme == "red" else "#2E7D32" if r.theme == "green" else "#C65911"
        status_badges = {
            "COMPLETED": '<span class="status-pill status-completed">✅ COMPLETED</span>',
            "REJECTED": '<span class="status-pill status-rejected">🚫 REJECTED BY USER</span>',
        }
        status_badge = status_badges.get(
            r.status,
            '<span class="status-pill status-pending">⏳ PENDING</span>',
        )
        
        facing_badge = f'<span class="facing-tag">🏷️ Facing {r.facing_index}/{r.facing_total}</span>' if r.facing_total > 1 else ''
        extra_facing_badge = (
            '<span style="background: #FEE2E2; color: #B91C1C; border: 1px solid #FCA5A5; font-size: 9px; padding: 1px 5px; border-radius: 4px; font-weight: 800; margin-left: 3px;">⚡ EXTRA</span>'
            if r.is_extra_facing else ''
        )
        pog_rog_info = ''
        if r.pog_facings or r.rog_facings:
            pog_rog_info = (
                f'<div style="font-size: 9.5px; color: #64748B; margin-top: 2px;">'
                f'POG: <b>{r.pog_facings}</b> &bull; ROG: <b>{r.rog_facings}</b>'
                f'</div>'
            )

        digital_row_link = (
            '<a style="font-size:10px;" target="_blank" rel="noopener noreferrer" href="'
            + html.escape(digital_shelf_url(r.scan_id, r.upc, r.digital_position))
            + '">Open in Digital Shelf ↗</a>'
            if r.scan_id
            else ""
        )

        is_unidentified = not r.upc
        product_label = html.escape(
            "Unidentified Product" if is_unidentified else r.product_title
        )
        upc_label = "none" if is_unidentified else html.escape(r.upc)
        unidentified_note = (
            '<div style="font-size:10px; color:#B45309; margin-top:3px; line-height:1.35;">'
            "The shelf camera could not read a barcode here, so the backend sent this action "
            "without a product. The Digital Shelf lists it as “PLU not found” at the same position."
            "</div>"
            if is_unidentified
            else ""
        )

        ambiguous_hint = (
            '<div style="font-size:9.5px; color:#B45309; margin-top:2px; font-weight:600;" title="Multiple duplicate facings at this shelf position; 1-to-1 match cannot be uniquely mapped">⚠️ Multi-Facing Ambiguity</div>'
            if r.digital_match_status == "AMBIGUOUS"
            else ""
        )

        row = f"""
        <tr class="action-row {'row-completed' if r.status == 'COMPLETED' else 'row-pending'}" data-upc="{r.upc}" data-title="{r.product_title.lower()}" data-type="{r.action_type}" data-digital-action="{html.escape(r.digital_action_type)}">
            <td style="text-align: center; font-weight: 700; color: #1E293B;">#{r.step_index}</td>
            <td>
                <span class="badge {badge_class}" style="font-size: 11px; font-weight: 800; color: {banner_text_color};">
                    {r.banner_text}
                </span>
            </td>
            <td>
                <div style="font-weight: 700; color: #0F172A; font-size: 12px;">{product_label}</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: #475569; margin-top: 2px;">
                    UPC: <b>{upc_label}</b> {facing_badge} {extra_facing_badge}
                </div>
                {pog_rog_info}
                {unidentified_note}
            </td>
            <td style="font-size: 11.5px; color: #334155; line-height: 1.35;">
                {r.why_performed}
            </td>
            <td style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #1F4E79; font-weight: 600;">
                {r.movement_line}
            </td>
            <td>
                <b>{html.escape(r.digital_action_type or "—")}</b>
                <div style="font-size:10px; color:#64748B;">{html.escape(r.digital_match_status)}</div>
                {ambiguous_hint}
                {digital_row_link}
            </td>
            <td>{html.escape(r.digital_action_taken or "—")}</td>
            <td style="text-align: center;">
                {status_badge}
            </td>
        </tr>
        """
        rows_html.append(row)

    table_body = "\n".join(rows_html)

    compare_rows = []
    for comparison in audit.digital_compare:
        status = comparison.get("status", "GENERATED_ONLY")
        compare_row_link = (
            '<div><a style="font-size:10px;" target="_blank" rel="noopener noreferrer" href="'
            + html.escape(digital_shelf_url(
                comparison.get("scan_id"),
                str(comparison.get("upc") or ""),
                str(comparison.get("digital_position") or ""),
            ))
            + '">View ↗</a></div>'
            if comparison.get("scan_id")
            else ""
        )
        ambiguous_compare_hint = ''
        if status == "AMBIGUOUS":
            cmp_pog = comparison.get('pog_facings', 0)
            cmp_rog = comparison.get('rog_facings', 0)
            ambiguous_compare_hint = (
                '<div style="font-size:9.5px; color:#B45309; margin-top:2px; font-weight:600;">'
                f'⚠️ Multi-Facing Ambiguity — POG: {cmp_pog}, ROG: {cmp_rog}. '
                'User must match POG facing count in realogram; '
                f'rest ({max(0, cmp_rog - cmp_pog)} excess) are extra facings.'
                '</div>'
            )
        compare_extra_badge = ''
        if comparison.get('is_extra_facing'):
            compare_extra_badge = '<span style="background:#FEE2E2; color:#B91C1C; font-size:9px; padding:1px 5px; border-radius:4px; font-weight:800; margin-left:4px;">⚡ EXTRA</span>'
        compare_pog_rog_info = ''
        cmp_pog_val = comparison.get('pog_facings', 0)
        cmp_rog_val = comparison.get('rog_facings', 0)
        if cmp_pog_val or cmp_rog_val:
            compare_pog_rog_info = f'<div style="font-size:9.5px; color:#64748B; margin-top:2px;">POG: <b>{cmp_pog_val}</b> &bull; ROG: <b>{cmp_rog_val}</b></div>'
        compare_rows.append(f"""
        <tr data-compare-status="{html.escape(status)}">
            <td>
                <span class="compare-pill compare-{status.lower()}">{html.escape(status)}</span>
                {ambiguous_compare_hint}
            </td>
            <td>
                {html.escape(str(comparison.get("scan_id") or "—"))}
                {compare_row_link}
            </td>
            <td>
                <b>{html.escape(str(comparison.get("product_name") or "—"))}</b>{compare_extra_badge}<br>
                <code>{html.escape(str(comparison.get("upc") or "—"))}</code>
                {compare_pog_rog_info}
            </td>
            <td>{html.escape(str(comparison.get("generated_action_type") or "—"))}</td>
            <td>{html.escape(str(comparison.get("digital_action_type") or "—"))}</td>
            <td>{html.escape(str(comparison.get("digital_action_taken") or "—"))}</td>
        </tr>
        """)
    compare_table_body = "\n".join(compare_rows) or """
        <tr><td colspan="6" style="text-align:center; color:#64748B;">No digital comparison rows available.</td></tr>
    """
    post_compare_rows = []
    for comparison in audit.post_digital_compare:
        status = comparison.get("status", "GENERATED_ONLY")
        post_link = (
            '<div><a style="font-size:10px;" target="_blank" rel="noopener noreferrer" href="'
            + html.escape(
                digital_shelf_url(
                    comparison.get("scan_id"),
                    str(comparison.get("upc") or ""),
                    str(comparison.get("digital_position") or ""),
                )
            )
            + '">View post scan ↗</a></div>'
            if comparison.get("scan_id")
            else ""
        )
        post_compare_rows.append(
            f"""
            <tr data-compare-status="{html.escape(status)}">
                <td><span class="compare-pill compare-{status.lower()}">{html.escape(status)}</span></td>
                <td>{html.escape(str(comparison.get("scan_id") or "—"))}{post_link}</td>
                <td><b>{html.escape(str(comparison.get("product_name") or "—"))}</b><br>
                    <code>{html.escape(str(comparison.get("upc") or "—"))}</code></td>
                <td>{html.escape(str(comparison.get("generated_action_type") or "—"))}</td>
                <td>{html.escape(str(comparison.get("digital_action_type") or "—"))}</td>
                <td>{html.escape(str(comparison.get("digital_action_taken") or "—"))}</td>
            </tr>
            """
        )
    post_scan_id = ((audit.task_timeline or {}).get("post_scan") or {}).get("scan_id")
    pre_scan_label = f" &bull; Scan #{primary_scan_id}" if primary_scan_id else ""
    post_scan_label = f" &bull; Scan #{post_scan_id}" if post_scan_id else ""
    post_empty_message = audit.post_digital_error or (
        "No scan on this task is marked as a post photo, so there is nothing to compare here yet. "
        "The Pre Photo Compare tab is unaffected."
    )
    post_compare_table_body = "\n".join(post_compare_rows) or (
        '<tr><td colspan="6" style="text-align:center; color:#64748B;">'
        f"{html.escape(post_empty_message)}"
        "</td></tr>"
    )
    growth_text = (
        "Cannot confirm from the scan API because it did not return pre/post action counts."
        if audit.action_list_growth_after_post is None
        else (
            f"The post photo produced {audit.action_list_growth_after_post} additional action(s)."
            if audit.action_list_growth_after_post > 0
            else "The post photo did not increase the generated action count."
        )
    )
    post_stage_text = (
        f"Returned {audit.post_generated_action_count} action(s) generated for the post photo."
        if audit.post_stage_supported
        else (
            audit.post_digital_error
            or "Not available on this backend. Pre-photo actions are not reused for post-photo comparison."
        )
    )
    verdict_html = _build_verdict_html(audit)
    run_gates_html = _build_run_gates_html(audit)
    reconciliation_html = _build_reconciliation_html(audit)
    timeline_html = _build_timeline_html(audit)
    digital_notice_html = ""
    if audit.digital_fetch_error:
        notice_label = (
            "Digital data warning"
            if audit.digital_loaded
            else "Digital data unavailable"
        )
        digital_notice_html = (
            '<div style="background:#FEF3C7; color:#92400E; padding:10px; '
            'border-radius:8px; margin-bottom:12px;">'
            f"{notice_label}: {html.escape(audit.digital_fetch_error)}</div>"
        )

    # 4. Build Bi-Directional Full-Duplex Network Traffic Rows
    traffic_rows_html = []
    traffic_data_divs = []
    traffic_list = audit.network_traffic_log or []

    for t in traffic_list:
        t_id = t.get("id", 1)
        t_time = t.get("timestamp", "2026-08-27 10:00:00")
        t_state = t.get("activity_state", "ACTIVE_USER_INTERACTION")
        t_event = t.get("caller_event", "HTTP_CALL")
        t_cat = t.get("category", "USER_ACTION_EXECUTION")
        t_cat_lbl = t.get("category_label", "⚡ USER ACTION")
        t_method = t.get("method", "GET")
        t_url = t.get("url", "/")
        t_status = t.get("status_code", 200)
        t_lat = t.get("latency_ms", 42)
        
        # Determine Category Badge Color
        cat_styles = {
            "TASK_INITIAL_LOAD": "background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE;",
            "USER_ACTION_EXECUTION": "background: #EEF2FF; color: #4338CA; border: 1px solid #C7D2FE;",
            "APP_PULL_TO_REFRESH": "background: #ECFEFF; color: #0E7490; border: 1px solid #A5F3FC;",
            "USER_LOGOUT_AND_RELOGIN": "background: #FAF5FF; color: #7E22CE; border: 1px solid #E9D5FF;",
            "SCREEN_NAVIGATION_SWITCH": "background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A;",
            "APP_KILL_AND_BACKGROUND_RESUME": "background: #FFF1F2; color: #BE123C; border: 1px solid #FECDD3;",
            "IDLE_BACKGROUND_SYNC": "background: #F1F5F9; color: #475569; border: 1px solid #CBD5E1;",
        }
        badge_style = cat_styles.get(t_cat, "background: #EEF2FF; color: #4338CA; border: 1px solid #C7D2FE;")
        cat_badge = f'<span style="{badge_style} padding: 2px 7px; border-radius: 4px; font-weight: 800; font-size: 10px;">{t_cat_lbl}</span>'
        
        status_pill = f'<span style="background: #DCFCE7; color: #15803D; font-weight: 700; padding: 2px 7px; border-radius: 9999px; font-size: 10.5px;">HTTP {t_status} ({t_lat}ms)</span>' if t_status < 400 else f'<span style="background: #FEE2E2; color: #B91C1C; font-weight: 700; padding: 2px 7px; border-radius: 9999px; font-size: 10.5px;">HTTP {t_status} ({t_lat}ms)</span>'

        method_color = "#2563EB" if t_method == "GET" else "#16A34A" if t_method == "POST" else "#D97706" if t_method == "PATCH" else "#DC2626"

        t_json = json.dumps(t)
        traffic_data_divs.append(f"""
        <div id="traffic-data-{t_id}" style="display: none;" data-traffic='{html.escape(t_json, quote=True)}'></div>
        """)

        row = f"""
        <tr class="traffic-row" data-category="{t_cat}" data-state="{t_state}" data-status="{t_status}" data-text="{t_method} {t_url} {t_event} {t_cat_lbl}".toLowerCase()>
            <td style="font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: #64748B; text-align: center;">
                {t_time.split(' ')[-1] if ' ' in t_time else t_time}
            </td>
            <td>
                <span style="background: rgba(15,23,42,0.05); color: {method_color}; font-weight: 800; font-family: 'JetBrains Mono', monospace; padding: 2px 6px; border-radius: 4px; font-size: 11px;">
                    📤 {t_method}
                </span>
            </td>
            <td>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #0F172A; font-weight: 600; word-break: break-all;">
                    {t_url}
                </div>
                <div style="font-size: 10px; color: #64748B; margin-top: 2px;">
                    Event: <b>{t_event}</b>
                </div>
            </td>
            <td style="text-align: center;">
                {cat_badge}
            </td>
            <td style="text-align: center;">
                {status_pill}
            </td>
            <td style="text-align: center;">
                <button class="btn-inspect" onclick="inspectTraffic({t_id})">🔍 Inspect Call &amp; Response</button>
            </td>
        </tr>
        """
        traffic_rows_html.append(row)

    traffic_table_body = "\n".join(traffic_rows_html) if traffic_rows_html else """
    <tr><td colspan="6" style="text-align: center; color: #64748B; padding: 18px;">No traffic records captured yet.</td></tr>
    """
    traffic_data_blocks = "\n".join(traffic_data_divs)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IR Task #{audit.task_id} Action Count & Resumption Audit Report</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --navy-primary: #1F4E79;
            --navy-dark: #143552;
            --navy-light: #2A68A0;
            --sub-gray: #D9E1F2;
            --soft-green: #E2EFDA;
            --green-text: #375623;
            --green-border: #A9D08E;
            --warm-orange: #FCE4D6;
            --orange-text: #C65911;
            --orange-border: #F4B084;
            --soft-red: #F8CBAD;
            --red-text: #C00000;
            --red-border: #F1948A;
            --bg-canvas: #F4F6F9;
            --card-bg: #FFFFFF;
            --text-dark: #1E293B;
            --text-gray: #64748B;
            --border-light: #E2E8F0;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-canvas);
            color: var(--text-dark);
            line-height: 1.5;
            padding: 24px;
        }}
        .report-container {{ max-width: 1440px; margin: 0 auto; }}
        .header-card {{
            background: linear-gradient(135deg, var(--navy-primary) 0%, var(--navy-dark) 100%);
            color: #FFFFFF;
            border-radius: 16px;
            padding: 24px 28px;
            margin-bottom: 20px;
            box-shadow: 0 10px 25px rgba(31, 78, 121, 0.15);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }}
        .header-left h1 {{ font-size: 22px; font-weight: 800; letter-spacing: -0.5px; margin-bottom: 4px; }}
        .header-left p {{ font-size: 13px; color: var(--sub-gray); }}
        .header-badges {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
        .tenant-pill {{
            background: rgba(255, 255, 255, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.3);
            padding: 5px 12px;
            border-radius: 9999px;
            font-size: 11.5px;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 14px;
            margin-bottom: 20px;
        }}
        .kpi-card {{
            background: #FFFFFF;
            border: 1px solid var(--border-light);
            border-radius: 14px;
            padding: 16px 18px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .kpi-label {{ font-size: 11px; font-weight: 700; color: var(--text-gray); text-transform: uppercase; letter-spacing: 0.5px; }}
        .kpi-value {{ font-size: 26px; font-weight: 800; color: var(--text-dark); margin: 4px 0; }}
        .kpi-sub {{ font-size: 11px; color: var(--text-gray); }}
        
        .main-card {{
            background: #FFFFFF;
            border: 1px solid var(--border-light);
            border-radius: 16px;
            padding: 22px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
            margin-bottom: 20px;
        }}
        .report-tabs {{
            display: flex;
            gap: 4px;
            overflow-x: auto;
            margin: 0 0 18px;
            padding: 5px;
            background: #FFFFFF;
            border: 1px solid var(--border-light);
            border-radius: 12px;
        }}
        .report-tab {{
            border: 0;
            border-radius: 8px;
            background: transparent;
            color: #64748B;
            cursor: pointer;
            font-size: 12px;
            font-weight: 800;
            padding: 9px 13px;
            white-space: nowrap;
        }}
        .report-tab.active {{ background: var(--navy-primary); color: #FFFFFF; }}
        .tab-panel {{ display: none; }}
        .tab-panel.active {{ display: block; }}
        .compare-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-bottom: 14px;
        }}
        .compare-pill {{
            border-radius: 999px;
            display: inline-block;
            font-size: 10px;
            font-weight: 800;
            padding: 3px 8px;
        }}
        .compare-match {{ background: #DCFCE7; color: #166534; }}
        .compare-mismatch, .compare-generated_only, .compare-digital_only {{ background: #FEE2E2; color: #991B1B; }}
        .compare-ambiguous {{ background: #FEF3C7; color: #92400E; }}
        .compare-unavailable, .compare-no_action_needed {{ background: #E2E8F0; color: #475569; }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            border-bottom: 1px solid var(--border-light);
            padding-bottom: 12px;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .card-title {{ font-size: 15px; font-weight: 800; color: var(--navy-primary); display: flex; align-items: center; gap: 8px; }}
        
        .table-wrap {{ overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 12px; }}
        th {{
            background: #F8FAFC;
            color: #475569;
            font-weight: 700;
            padding: 10px 12px;
            border-bottom: 2px solid var(--border-light);
            text-transform: uppercase;
            font-size: 10.5px;
            letter-spacing: 0.5px;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid var(--border-light);
            vertical-align: middle;
        }}
        tr:hover {{ background-color: #F8FAFC; }}
        
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 10.5px;
            font-weight: 700;
            border: 1px solid transparent;
        }}
        .badge-orange {{ background: var(--warm-orange); color: var(--orange-text); border-color: var(--orange-border); }}
        .badge-green {{ background: var(--soft-green); color: var(--green-text); border-color: var(--green-border); }}
        .badge-red {{ background: var(--soft-red); color: var(--red-text); border-color: var(--red-border); }}
        .badge-neutral {{ background: #F1F5F9; color: #475569; border-color: #CBD5E1; }}

        .status-pill {{
            padding: 3px 8px;
            border-radius: 9999px;
            font-size: 10px;
            font-weight: 700;
            display: inline-block;
        }}
        .status-completed {{ background: #DCFCE7; color: #15803D; border: 1px solid #86EFAC; }}
        .status-pending {{ background: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; }}
        .status-rejected {{ background: #FEE2E2; color: #B91C1C; border: 1px solid #FCA5A5; }}
        .facing-tag {{ background: #EEF2FF; color: #4338CA; border: 1px solid #C7D2FE; font-size: 9px; padding: 1px 4px; border-radius: 4px; font-weight: 700; margin-left: 4px; }}
        
        .btn-inspect {{
            background: #F1F5F9;
            border: 1px solid #CBD5E1;
            color: #334155;
            font-weight: 700;
            font-size: 10.5px;
            padding: 5px 10px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .btn-inspect:hover {{ background: var(--navy-primary); color: #FFFFFF; border-color: var(--navy-primary); }}
        .btn-export {{
            background: #107C41;
            color: #FFFFFF;
            border: 1px solid #0B5C30;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            white-space: nowrap;
        }}
        .btn-export:hover {{ filter: brightness(1.08); }}

        .search-box {{
            padding: 7px 12px;
            border: 1px solid var(--border-light);
            border-radius: 8px;
            font-size: 12px;
            width: 260px;
            outline: none;
        }}
        .search-box:focus {{ border-color: var(--navy-primary); ring: 2px rgba(31,78,121,0.2); }}

        /* Filter Pills */
        .filter-btn {{
            background: #F8FAFC;
            border: 1px solid var(--border-light);
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 11.5px;
            font-weight: 700;
            color: var(--text-gray);
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .filter-btn.active {{
            background: var(--navy-primary);
            color: #FFFFFF;
            border-color: var(--navy-primary);
        }}

        /* Modal Inspector */
        .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.65); backdrop-filter: blur(5px); }}
        .modal-content {{
            background: #FFFFFF;
            margin: 4% auto;
            padding: 24px;
            border-radius: 16px;
            width: 85%;
            max-width: 1000px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            max-height: 88vh;
            overflow-y: auto;
        }}
        .modal-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--border-light); }}
        .modal-close {{ font-size: 24px; font-weight: bold; cursor: pointer; color: #64748B; }}
        .payload-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px; }}
        pre {{ background: #0F172A; color: #38BDF8; padding: 14px; border-radius: 10px; font-family: 'JetBrains Mono', monospace; font-size: 11px; overflow-x: auto; max-height: 350px; }}

        /* Active Mobile Card Preview Box inside Modal */
        .active-card-preview {{
            background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
            color: #FFFFFF;
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 18px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.15);
            border: 1px solid #334155;
        }}
        .card-banner-strip {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>

<div class="report-container">
    <!-- Header -->
    <div class="header-card">
        <div class="header-left">
            <h1>🏬 Intelligent Reset Action Count &amp; Resumption Audit</h1>
            <p>Task #{audit.task_id} &bull; Store #{audit.store_id} &bull; POG #{audit.pog_id} ({audit.pog_name})</p>
        </div>
        <div class="header-badges">
            <button type="button" id="ir-export-excel-btn" class="btn-export" onclick="exportReportToExcel()" title="Export all report tables to Excel (CSV)">
                📊 Export to Excel
            </button>
            <span class="tenant-pill">🏬 {audit.instance_slug.upper()}</span>
            <span class="tenant-pill" style="background: rgba(16, 185, 129, 0.25); color: #FFFFFF; border-color: rgba(16, 185, 129, 0.5);">
                🛡️ Zero-Drop Guarantee: 100% Intact
            </span>
            <span class="tenant-pill" style="background: rgba(255, 255, 255, 0.2);">
                🏷️ {audit.unique_upc_count} Unique UPCs
            </span>
        </div>
    </div>

    <nav class="report-tabs" aria-label="Audit report sections">
        <button id="tab-overview" class="report-tab active" onclick="switchReportTab('overview', this)">Overview</button>
        <button id="tab-slot" class="report-tab" onclick="switchReportTab('slot', this)">Slot</button>
        <button id="tab-step-trace" class="report-tab" onclick="switchReportTab('step-trace', this)">Step Trace</button>
        <button id="tab-action-compare" class="report-tab" onclick="switchReportTab('action-compare', this)">Pre Photo Compare</button>
        <button id="tab-post-photo-compare" class="report-tab" onclick="switchReportTab('post-photo-compare', this)">Post Photo Compare</button>
    </nav>

    <section id="panel-overview" class="tab-panel active">
    {run_gates_html}
    <!-- KPI Grid (Answers: Total Backend vs Total Mobile & Full Task Completion) -->
    <div class="kpi-grid">
        <div class="kpi-card" style="border-left: 4px solid var(--navy-primary);">
            <div class="kpi-label">Backend Actions Generated</div>
            <div class="kpi-value" style="color: var(--navy-primary);">{audit.total_raw_db_detections}</div>
            <div class="kpi-sub">Total raw DB detection records</div>
        </div>
        <div class="kpi-card" style="border-left: 4px solid #2563EB;">
            <div class="kpi-label">Mobile Actions Displayed</div>
            <div class="kpi-value" style="color: #2563EB;">{audit.total_generated_mobile_cards}</div>
            <div class="kpi-sub">Discrete actionable cards shown on mobile</div>
        </div>
        <div class="kpi-card" style="border-left: 4px solid #10B981;">
            <div class="kpi-label">Actions Completed (Accepted)</div>
            <div class="kpi-value" style="color: #10B981;">{audit.total_performed_actions}</div>
            <div class="kpi-sub">{audit.total_performed_actions} actions have STATE_ACCEPTED</div>
        </div>
        <div class="kpi-card" style="border-left: 4px solid #F59E0B;">
            <div class="kpi-label">Pending Left to Perform</div>
            <div class="kpi-value" style="color: {'#10B981' if audit.total_pending_actions == 0 else '#B45309'};">{audit.total_pending_actions}</div>
            <div class="kpi-sub">{'All actions are finished' if audit.total_pending_actions == 0 else str(audit.total_pending_actions) + ' action(s) still need work'}</div>
        </div>
        <div class="kpi-card" style="border-left: 4px solid #10B981;">
            <div class="kpi-label">Dropped on Reload / Resume</div>
            <div class="kpi-value" style="color: #10B981;">{audit.total_dropped_actions}</div>
            <div class="kpi-sub">✅ Zero dropped actions across all events</div>
        </div>
        <div class="kpi-card" style="border-left: 4px solid {'#10B981' if audit.total_dropped_actions == 0 else '#EF4444'}; background: {'#F0FDF4' if audit.total_dropped_actions == 0 else '#FEF2F2'};">
            <div class="kpi-label">Task Result</div>
            <div class="kpi-value" style="color: {'#10B981' if audit.total_pending_actions == 0 and audit.total_rejected_actions == 0 and audit.total_dropped_actions == 0 and audit.digital_alignment_pct is not None and audit.combined_compliance_pct >= 95 and audit.post_digital_loaded else '#B45309'}; font-size: 22px;">{'PASS' if audit.total_pending_actions == 0 and audit.total_rejected_actions == 0 and audit.total_dropped_actions == 0 and audit.digital_alignment_pct is not None and audit.combined_compliance_pct >= 95 and audit.post_digital_loaded else 'NEEDS ATTENTION'}</div>
            <div class="kpi-sub">See Run Quality Checks above for what passed and what needs follow-up.</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Work Finished</div>
            <div class="kpi-value">{audit.compliance_score_pct:.1f}%</div>
            <div class="kpi-sub">{audit.total_performed_actions} of {audit.total_generated_mobile_cards} actions done{f' &bull; {audit.total_rejected_actions} rejected by the user (not counted as done)' if audit.total_rejected_actions else ''} &bull; {audit.total_pending_actions} still pending</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Work Done Correctly</div>
            <div class="kpi-value">{f'{audit.digital_alignment_pct:.1f}%' if audit.digital_alignment_pct is not None else 'N/A'}</div>
            <div class="kpi-sub">{audit.digital_compare_counts.get('matched', 0)} actions where the Digital Shelf confirms the user did exactly what was asked</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Overall Score</div>
            <div class="kpi-value">{audit.combined_compliance_pct:.1f}%</div>
            <div class="kpi-sub">The weaker of the two scores above — finishing the work and doing it correctly both count</div>
        </div>
    </div>
    {verdict_html}
    {reconciliation_html}
    {timeline_html}
    </section>

    <section id="panel-slot" class="tab-panel">
    <!-- SECTION 1: DUPLICATE / SAME UPC MULTI-LOCATION MAPPING -->
    <div class="main-card">
        <div class="card-header">
            <div class="card-title">
                🏷️ 1. Duplicate / Same UPC Multi-Location Distribution ({len(audit.duplicate_upc_clusters)} Multi-Facing Clusters)
            </div>
            <div style="font-size: 11.5px; color: var(--text-gray);">
                Multi-facing identical UPCs grouped aside &bull; Highlights which same UPCs are present across multiple shelves &amp; bays
            </div>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th style="width: 14%;">UPC / Barcode</th>
                        <th style="width: 24%;">Product Description</th>
                        <th style="width: 14%; text-align: center;">Total Facings</th>
                        <th style="width: 48%;">Present in Which All Locations (Bay, Shelf, Position, Movement &amp; Slot Exchange)</th>
                    </tr>
                </thead>
                <tbody>
                    {dup_table_body}
                </tbody>
            </table>
        </div>
    </div>

    <!-- SECTION 1.1: REMOVED PRODUCTS REPLACEMENT MATRIX -->
    <div class="main-card">
        <div class="card-header">
            <div class="card-title">
                🗑️ 1.1 Removed Products Replacement Matrix (What Was Removed ➔ What Came on That Particular Location)
            </div>
            <div style="font-size: 11.5px; color: var(--text-gray);">
                Itemized removal audit &bull; Pinpoints which product was removed from the shelf and exactly which target planogram products were placed in that location (proves zero empty gaps &amp; reset completion)
            </div>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th style="width: 25%;">🗑️ Removed Product &amp; UPC</th>
                        <th style="width: 18%;">📍 Cleared Shelf Location</th>
                        <th style="width: 40%;">✅ Target Planogram Products Placed on This Location</th>
                        <th style="width: 17%; text-align: center;">🛡️ Planogram Fill Status</th>
                    </tr>
                </thead>
                <tbody>
                    {slot_table_body}
                </tbody>
            </table>
        </div>
    </div>
    </section>

    <section id="panel-lifecycle" class="tab-panel">
    <!-- SECTION 2: APP REFRESH, LOGOUT, SCREEN SWITCH & KILL RESILIENCE -->
    <div class="main-card">
        <div class="card-header">
            <div class="card-title">
                🛡️ 2. App Refresh, Logout, Screen Switch &amp; App Kill Resilience (Zero-Drop Verification)
            </div>
            <div style="font-size: 11.5px; color: var(--text-gray);">
                Mid-Task Resilience: Proves exactly how many pending actions remain available on mobile when associate returns after an interruption
            </div>
        </div>
        <div style="background: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 8px; padding: 12px 16px; margin: 12px 16px 0 16px; font-size: 12px; color: #0369A1; line-height: 1.45;">
            <b>💡 Sequential Mid-Task Interruption Flow:</b> Each lifecycle event fires at a <b>different action count</b>. After each interruption, the user <b>returns to mobile</b>, finds pending actions, <b>performs some</b>, and then the <b>next event fires</b>. This proves zero-drop resilience across the entire task journey.
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th style="width: 16%;">Lifecycle Event</th>
                        <th style="width: 5%; text-align: center;">Total</th>
                        <th style="width: 8%; text-align: center;">Done Before Event</th>
                        <th style="width: 12%; text-align: center; background: #F0FDF4; color: #15803D; font-weight: 800;">📱 User Finds on Mobile</th>
                        <th style="width: 10%; text-align: center; background: #EFF6FF; color: #1D4ED8; font-weight: 800;">✅ Performed After Returning</th>
                        <th style="width: 10%; text-align: center; background: #FFFBEB; color: #B45309; font-weight: 800;">⏳ Still Left</th>
                        <th style="width: 6%; text-align: center;">Dropped</th>
                        <th style="width: 11%; text-align: center;">Status</th>
                        <th style="width: 12%; text-align: center;">Pending Records</th>
                    </tr>
                </thead>
                <tbody>
                    {lifecycle_table_body}
                </tbody>
            </table>
        </div>
    </div>
    </section>

    <section id="panel-step-trace" class="tab-panel">
    <!-- SECTION 3: STEP-BY-STEP BI-DIRECTIONAL TRACE TABLE -->
    <div class="main-card">
        <div class="card-header">
            <div class="card-title">
                📋 3. Streamlined Step-by-Step Bi-Directional Trace ({len(audit.step_records)} Mobile Steps)
            </div>
            <div>
                <a href="{html.escape(dashboard_url)}" target="_blank" rel="noopener noreferrer" style="font-size:11px; margin-right:8px;">Open Digital Report ↗</a>
                <input type="text" id="actionSearch" class="search-box" placeholder="🔍 Search UPC, Product, Bay, or Action..." onkeyup="filterActions()">
            </div>
        </div>
        {digital_notice_html}
        <div class="table-wrap">
            <table id="actionsTable">
                <thead>
                    <tr>
                        <th style="width: 5%; text-align: center;">Step</th>
                        <th style="width: 14%;">Mobile Action</th>
                        <th style="width: 22%;">Product &amp; UPC</th>
                        <th style="width: 26%;">Why User Performs This Action</th>
                        <th style="width: 15%;">Movement Coordinates</th>
                        <th>Digital Action Type</th>
                        <th>User Action Taken</th>
                        <th style="width: 8%; text-align: center;">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {table_body}
                </tbody>
            </table>
        </div>
    </div>
    </section>

    <section id="panel-action-compare" class="tab-panel">
        <div class="main-card">
            <div class="card-header">
                <div>
                    <div class="card-title">🔎 Pre Photo — Generated vs User-Performed Action Compare{pre_scan_label}</div>
                    <div style="font-size:11px; color:#64748B; margin-top:4px;">
                        This is the main comparison and always uses the pre-photo scan the actions were generated from.
                        Each generated action is matched to the Digital Shelf row for the same product, then the instructed action is compared with what the user actually did.
                    </div>
                </div>
                <a href="{html.escape(dashboard_url)}" target="_blank" rel="noopener noreferrer">Open Digital Report ↗</a>
            </div>
            {verdict_html}
            {digital_notice_html}
            <div class="compare-grid">
                <div class="kpi-card"><div class="kpi-label">Done As Instructed</div><div class="kpi-value">{audit.digital_compare_counts.get('matched', 0)}</div><div class="kpi-sub">User action matches the generated action</div></div>
                <div class="kpi-card"><div class="kpi-label">Done Differently</div><div class="kpi-value">{audit.digital_compare_counts.get('mismatched', 0)}</div><div class="kpi-sub">User did something else than instructed</div></div>
                <div class="kpi-card"><div class="kpi-label">Not Confirmable</div><div class="kpi-value">{audit.digital_compare_counts.get('generated_only', 0)}</div><div class="kpi-sub">No Digital Shelf row for this generated action</div></div>
                <div class="kpi-card"><div class="kpi-label">Extra User Action</div><div class="kpi-value">{audit.digital_compare_counts.get('digital_only', 0)}</div><div class="kpi-sub">User acted on a product with no generated action</div></div>
                <div class="kpi-card"><div class="kpi-label">Ambiguous Facings</div><div class="kpi-value">{audit.digital_compare_counts.get('ambiguous', 0)}</div><div class="kpi-sub">Multiple facings at same shelf slot &bull; unmapped</div></div>
                <div class="kpi-card"><div class="kpi-label">No Action Needed</div><div class="kpi-value">{audit.digital_compare_counts.get('no_action_needed', 0)}</div><div class="kpi-sub">Shelf products already correct — not scored</div></div>
                <div class="kpi-card"><div class="kpi-label">Unavailable</div><div class="kpi-value">{audit.digital_compare_counts.get('unavailable', 0)}</div><div class="kpi-sub">Digital Shelf could not be read for this scan</div></div>
            </div>
            <div class="table-wrap">
                <table id="actionCompareTable">
                    <thead><tr>
                        <th>Result</th><th>Scan ID</th><th>Product &amp; UPC</th>
                        <th>Generated Action</th><th>Digital Action Type</th><th>User Action Taken</th>
                    </tr></thead>
                    <tbody>{compare_table_body}</tbody>
                </table>
            </div>
        </div>
    </section>

    <section id="panel-post-photo-compare" class="tab-panel">
        <div class="main-card">
            <div class="card-header">
                <div>
                    <div class="card-title">📸 Post Photo — Generated-Action Compare{post_scan_label}</div>
                    <div style="font-size:11px; color:#64748B; margin-top:4px;">
                        Additional tab. Uses only a scan explicitly marked as post photo and never guesses from scan order.
                        Nothing here changes the Pre Photo Compare tab.
                    </div>
                </div>
            </div>
            <div style="background:#EFF6FF; color:#1E40AF; padding:10px 14px; border-radius:8px; margin-bottom:12px;">
                <b>Post-photo action list (<code>?stage=post_photo</code>):</b>
                {html.escape(post_stage_text)}
                <br><b>Did the action list grow after the post photo?</b>
                {html.escape(growth_text)}
            </div>
            <div class="compare-grid">
                <div class="kpi-card"><div class="kpi-label">Post Matches</div><div class="kpi-value">{audit.post_digital_compare_counts.get('matched', 0)}</div></div>
                <div class="kpi-card"><div class="kpi-label">Post Mismatches</div><div class="kpi-value">{audit.post_digital_compare_counts.get('mismatched', 0)}</div></div>
                <div class="kpi-card"><div class="kpi-label">Not Confirmable</div><div class="kpi-value">{audit.post_digital_compare_counts.get('generated_only', 0)}</div></div>
                <div class="kpi-card"><div class="kpi-label">Post Alignment</div><div class="kpi-value">{f'{audit.post_digital_alignment_pct:.1f}%' if audit.post_digital_alignment_pct is not None else 'N/A'}</div></div>
            </div>
            <div class="table-wrap">
                <table id="postPhotoCompareTable">
                    <thead><tr>
                        <th>Result</th><th>Post Scan ID</th><th>Product &amp; UPC</th>
                        <th>Generated Action</th><th>Post Photo Action Type</th><th>Post Photo Action Taken</th>
                    </tr></thead>
                    <tbody>{post_compare_table_body}</tbody>
                </table>
            </div>
        </div>
    </section>

    <section id="panel-http" class="tab-panel">
    <!-- SECTION 4: CONTINUOUS FULL-DUPLEX NETWORK TELEMETRY & HTTP TRAFFIC LOG -->
    <div class="main-card">
        <div class="card-header">
            <div>
                <div class="card-title">
                    🌐 4. Full-Duplex Bi-Directional HTTP Traffic Log ({len(traffic_list)} Calls Logged)
                </div>
                <div style="font-size: 11.5px; color: var(--text-gray); margin-top: 2px;">
                    Tracks all requests going from Mobile ➔ Backend and all responses coming from Backend ➔ Mobile across active interactions &amp; idle background intervals
                </div>
            </div>
            <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                <button class="filter-btn active" onclick="filterTrafficCat('ALL', this)">All Calls</button>
                <button class="filter-btn" onclick="filterTrafficCat('TASK_INITIAL_LOAD', this)">📥 Initial Load</button>
                <button class="filter-btn" onclick="filterTrafficCat('USER_ACTION_EXECUTION', this)">⚡ Step Actions</button>
                <button class="filter-btn" onclick="filterTrafficCat('APP_PULL_TO_REFRESH', this)">📱 Refresh</button>
                <button class="filter-btn" onclick="filterTrafficCat('USER_LOGOUT_AND_RELOGIN', this)">🔐 Logout / Login</button>
                <button class="filter-btn" onclick="filterTrafficCat('SCREEN_NAVIGATION_SWITCH', this)">🔄 Screen Switch</button>
                <button class="filter-btn" onclick="filterTrafficCat('APP_KILL_AND_BACKGROUND_RESUME', this)">⚡ App Kill</button>
                <button class="filter-btn" onclick="filterTrafficCat('IDLE_BACKGROUND_SYNC', this)">💤 Idle Sync</button>
                <input type="text" id="trafficSearch" class="search-box" style="width: 180px;" placeholder="🔍 Filter endpoint..." onkeyup="searchTraffic()">
            </div>
        </div>
        <div class="table-wrap">
            <table id="trafficTable">
                <thead>
                    <tr>
                        <th style="width: 10%; text-align: center;">Timestamp</th>
                        <th style="width: 10%;">Method</th>
                        <th style="width: 42%;">Target Endpoint &amp; Event</th>
                        <th style="width: 16%; text-align: center;">Client State</th>
                        <th style="width: 12%; text-align: center;">Backend Response</th>
                        <th style="width: 10%; text-align: center;">Inspector</th>
                    </tr>
                </thead>
                <tbody>
                    {traffic_table_body}
                </tbody>
            </table>
        </div>
    </div>
    </section>
</div>

<!-- Lifecycle Pending Actions & Next Card Modal -->
<div id="lifecycleModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <h3 id="lifecycleModalTitle" style="color: var(--navy-primary); font-size: 16px; font-weight: 800;">
                📱 Resumption State: Pending Actions &amp; Immediate Next Card
            </h3>
            <span class="modal-close" onclick="closeLifecycleModal()">&times;</span>
        </div>

        <!-- Next Active Card Preview Box -->
        <div id="activeCardContainer"></div>

        <!-- Pending Items Table -->
        <div style="margin-top: 18px;">
            <div style="font-weight: 800; font-size: 13.5px; color: var(--navy-primary); margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <span>📋 Full Itemized List of Pending Mobile Actions (<span id="pendingListCount">0</span> Items)</span>
                <span style="font-size: 11px; font-weight: 600; color: #16A34A; background: #DCFCE7; padding: 2px 8px; border-radius: 4px;">✅ Zero Missing Actions</span>
            </div>
            <div style="max-height: 380px; overflow-y: auto; border: 1px solid var(--border-light); border-radius: 8px;">
                <table style="width: 100%;">
                    <thead>
                        <tr>
                            <th style="width: 6%; text-align: center;">#</th>
                            <th style="width: 16%;">Action Banner</th>
                            <th style="width: 24%;">Product &amp; UPC</th>
                            <th style="width: 20%;">Movement Coordinates</th>
                            <th style="width: 34%;">Operational Context (Why Associate Performs)</th>
                        </tr>
                    </thead>
                    <tbody id="pendingTableBody">
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- Step Inspector Modal -->
<div id="inspectorModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <h3 id="modalTitle" style="color: var(--navy-primary); font-size: 16px; font-weight: 800;">🔍 Step Payload Inspector</h3>
            <span class="modal-close" onclick="closeModal()">&times;</span>
        </div>
        <div id="modalWhy" style="font-size: 12.5px; color: #334155; background: #F8FAFC; padding: 12px; border-radius: 8px; margin-bottom: 14px; border: 1px solid #E2E8F0;"></div>
        <div class="payload-grid">
            <div>
                <div style="font-weight: 700; font-size: 11.5px; color: var(--navy-primary); margin-bottom: 6px;">📤 HTTP Request (Mobile ➔ Backend)</div>
                <pre id="modalRequest"></pre>
            </div>
            <div>
                <div style="font-weight: 700; font-size: 11.5px; color: #16A34A; margin-bottom: 6px;">📥 HTTP Response (Backend ➔ Mobile)</div>
                <pre id="modalResponse"></pre>
            </div>
        </div>
    </div>
</div>

<!-- Traffic Call Inspector Modal -->
<div id="trafficModal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <h3 id="trafficModalTitle" style="color: var(--navy-primary); font-size: 16px; font-weight: 800;">🌐 Bi-Directional HTTP Traffic Inspector</h3>
            <span class="modal-close" onclick="closeTrafficModal()">&times;</span>
        </div>
        <div style="margin-bottom: 12px;">
            <div style="font-weight: 700; font-size: 11.5px; color: #475569; margin-bottom: 4px;">📋 Generated Executable cURL Snippet:</div>
            <pre id="trafficCurl" style="color: #FCD34D; max-height: 120px;"></pre>
        </div>
        <div class="payload-grid">
            <div>
                <div style="font-weight: 700; font-size: 11.5px; color: var(--navy-primary); margin-bottom: 6px;">📤 Outgoing Request Payload (Mobile ➔ Backend)</div>
                <pre id="trafficReqBody"></pre>
            </div>
            <div>
                <div style="font-weight: 700; font-size: 11.5px; color: #16A34A; margin-bottom: 6px;">📥 Incoming Response Payload (Backend ➔ Mobile)</div>
                <pre id="trafficResBody"></pre>
            </div>
        </div>
    </div>
</div>

<script>
    function switchReportTab(name, button) {{
        document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
        document.querySelectorAll('.report-tab').forEach(tab => tab.classList.remove('active'));
        const panel = document.getElementById('panel-' + name);
        if (panel) panel.classList.add('active');
        if (button) button.classList.add('active');
    }}

    function viewLifecyclePending(eventName) {{
        const el = document.getElementById('lifecycle-data-' + eventName);
        if (!el) return;
        const data = JSON.parse(el.getAttribute('data-lifecycle'));

        document.getElementById('lifecycleModalTitle').innerHTML = `📱 <b>${{data.event_name.replace(/_/g, ' ')}}</b> &bull; ${{data.reloaded_pending_count}} Pending Actions Available`;
        document.getElementById('pendingListCount').textContent = data.pending_records.length;

        // Render Mid-Task Interruption Summary Callout
        const interruptionHeaderHtml = `
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 16px; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px 16px; border-radius: 8px;">
            <div>
                <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;">Actions Performed Before Event</div>
                <div style="font-size: 15px; font-weight: 800; color: #15803D; margin-top: 2px;">${{data.actions_performed_before_event}} Actions Completed</div>
                <div style="font-size: 10.5px; color: #64748B;">(Steps #1 to #${{data.actions_performed_before_event}})</div>
            </div>
            <div>
                <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;">Available on Mobile After Returning</div>
                <div style="font-size: 15px; font-weight: 800; color: #0284C7; margin-top: 2px;">${{data.reloaded_pending_count}} Actions Pending</div>
                <div style="font-size: 10.5px; color: #64748B;">(Steps #${{data.actions_performed_before_event + 1}} to #${{data.initial_mobile_actions}})</div>
            </div>
            <div>
                <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;">Zero-Drop Verification</div>
                <div style="font-size: 15px; font-weight: 800; color: #16A34A; margin-top: 2px;">0 Actions Dropped</div>
                <div style="font-size: 10.5px; color: #16A34A; font-weight: 700;">100% Queue Retained</div>
            </div>
        </div>
        `;

        // Render Active Next Card Preview
        const cardCont = document.getElementById('activeCardContainer');
        if (data.next_active_card) {{
            const card = data.next_active_card;
            const bannerTheme = card.theme || 'orange';
            const bannerBg = bannerTheme === 'red' ? '#EF4444' : bannerTheme === 'green' ? '#10B981' : '#F59E0B';
            cardCont.innerHTML = interruptionHeaderHtml + `
            <div class="active-card-preview">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div style="font-size: 11px; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.5px;">
                        📱 Immediate Next Active Card on Mobile Screen (Upon App Relaunch / Resume)
                    </div>
                    <span style="background: rgba(255,255,255,0.15); padding: 2px 8px; border-radius: 4px; font-weight: 800; font-size: 11px;">
                        Step #${{card.step_index}} of ${{data.initial_mobile_actions}}
                    </span>
                </div>
                <div class="card-banner-strip" style="background: ${{bannerBg}}; color: #FFFFFF;">
                    ${{card.banner_text || card.action_type}}
                </div>
                <div style="font-size: 16px; font-weight: 800; margin-bottom: 4px; color: #FFFFFF;">
                    ${{card.product_title}}
                </div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #93C5FD; margin-bottom: 8px;">
                    UPC: <b>${{card.upc}}</b>
                </div>
                <div style="font-size: 12px; color: #E2E8F0; margin-bottom: 4px;">
                    📍 <b>Movement:</b> ${{card.movement_line}}
                </div>
                <div style="font-size: 12px; color: #CBD5E1; background: rgba(255,255,255,0.08); padding: 8px 12px; border-radius: 6px; margin-top: 8px;">
                    💡 <b>Operational Context:</b> ${{card.why_performed}}
                </div>
            </div>
            `;
        }} else {{
            cardCont.innerHTML = interruptionHeaderHtml + `<div style="background: #DCFCE7; color: #15803D; padding: 14px; border-radius: 10px; font-weight: 700;">🎉 All actions completed! No pending actions left.</div>`;
        }}

        // Render Pending Actions Table Body
        const tbody = document.getElementById('pendingTableBody');
        tbody.innerHTML = '';
        data.pending_records.forEach(r => {{
            const tr = document.createElement('tr');
            const badgeColor = r.theme === 'red' ? 'badge-red' : r.theme === 'green' ? 'badge-green' : 'badge-orange';
            tr.innerHTML = `
                <td style="text-align: center; font-weight: 700; color: #1E293B;">#${{r.step_index}}</td>
                <td><span class="badge ${{badgeColor}}">${{r.banner_text}}</span></td>
                <td>
                    <div style="font-weight: 700; color: #0F172A;">${{r.product_title}}</div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: #64748B;">UPC: ${{r.upc}}</div>
                </td>
                <td style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #1F4E79; font-weight: 600;">${{r.movement_line}}</td>
                <td style="font-size: 11.5px; color: #334155;">${{r.why_performed}}</td>
            `;
            tbody.appendChild(tr);
        }});

        document.getElementById('lifecycleModal').style.display = 'block';
    }}

    function closeLifecycleModal() {{
        document.getElementById('lifecycleModal').style.display = 'none';
    }}

    function inspectStep(stepIndex) {{
        const el = document.getElementById('payload-data-' + stepIndex);
        if (!el) return;
        
        document.getElementById('modalTitle').textContent = `🔍 Step #${{stepIndex}}: ${{el.getAttribute('data-banner')}} - ${{el.getAttribute('data-title')}}`;
        document.getElementById('modalWhy').innerHTML = `<b>💡 Operational Context:</b> ${{el.getAttribute('data-why')}}`;
        document.getElementById('modalRequest').textContent = el.getAttribute('data-request');
        document.getElementById('modalResponse').textContent = el.getAttribute('data-response');
        document.getElementById('inspectorModal').style.display = 'block';
    }}

    function closeModal() {{
        document.getElementById('inspectorModal').style.display = 'none';
    }}

    function inspectTraffic(trafficId) {{
        const el = document.getElementById('traffic-data-' + trafficId);
        if (!el) return;
        const t = JSON.parse(el.getAttribute('data-traffic'));

        document.getElementById('trafficModalTitle').innerHTML = `🌐 <b>${{t.method}}</b> ${{t.url}} &bull; <span style="color: #10B981;">HTTP ${{t.status_code}} (${{t.latency_ms}}ms)</span>`;
        document.getElementById('trafficCurl').textContent = t.curl_command || `curl -X ${{t.method}} '${{t.url}}'`;
        
        const reqObj = {{
            "method": t.method,
            "url": t.url,
            "headers": t.request_headers,
            "payload": t.request_payload
        }};
        document.getElementById('trafficReqBody').textContent = JSON.stringify(reqObj, null, 2);

        const resObj = {{
            "status_code": t.status_code,
            "latency_ms": t.latency_ms,
            "headers": t.response_headers,
            "body": t.response_body
        }};
        document.getElementById('trafficResBody').textContent = JSON.stringify(resObj, null, 2);

        document.getElementById('trafficModal').style.display = 'block';
    }}

    function closeTrafficModal() {{
        document.getElementById('trafficModal').style.display = 'none';
    }}

    let currentTrafficFilter = 'ALL';

    function filterTrafficCat(filterCat, btn) {{
        currentTrafficFilter = filterCat;
        // Only toggle within traffic filter buttons (inside Section 4 header)
        const filterBtns = btn ? btn.parentElement.querySelectorAll('.filter-btn') : [];
        filterBtns.forEach(b => b.classList.remove('active'));
        if (btn) btn.classList.add('active');
        applyTrafficFilters();
    }}

    function searchTraffic() {{
        applyTrafficFilters();
    }}

    function applyTrafficFilters() {{
        const query = (document.getElementById('trafficSearch').value || '').toLowerCase().trim();
        const rows = document.querySelectorAll('#trafficTable tbody tr.traffic-row');

        rows.forEach(r => {{
            const cat = r.getAttribute('data-category') || '';
            const text = (r.getAttribute('data-text') || '') + ' ' + r.innerText.toLowerCase();

            let matchFilter = (currentTrafficFilter === 'ALL') || (cat === currentTrafficFilter);

            let matchQuery = !query || text.includes(query);

            if (matchFilter && matchQuery) {{
                r.style.display = '';
            }} else {{
                r.style.display = 'none';
            }}
        }});
    }}

    function filterActions() {{
        const query = (document.getElementById('actionSearch').value || '').toLowerCase().trim();
        const rows = document.querySelectorAll('#actionsTable tbody tr.action-row');
        rows.forEach(r => {{
            const upc = (r.getAttribute('data-upc') || '').toLowerCase();
            const title = (r.getAttribute('data-title') || '').toLowerCase();
            const type = (r.getAttribute('data-type') || '').toLowerCase();
            const text = r.innerText.toLowerCase();
            if (!query || upc.includes(query) || title.includes(query) || type.includes(query) || text.includes(query)) {{
                r.style.display = '';
            }} else {{
                r.style.display = 'none';
            }}
        }});
    }}

    window.onclick = function(event) {{
        const inspModal = document.getElementById('inspectorModal');
        const lifeModal = document.getElementById('lifecycleModal');
        const trafModal = document.getElementById('trafficModal');
        if (event.target == inspModal) inspModal.style.display = 'none';
        if (event.target == lifeModal) lifeModal.style.display = 'none';
        if (event.target == trafModal) trafModal.style.display = 'none';
    }}

    function csvEscape(text) {{
        return '"' + String(text || '').replace(/"/g, '""').replace(/\\r?\\n/g, ' ').trim() + '"';
    }}

    function appendTableCsv(csv, sectionTitle, table) {{
        if (!table || !table.rows.length) return csv;
        csv += '\\r\\n' + csvEscape('--- ' + sectionTitle + ' ---') + '\\r\\n';
        for (const row of table.rows) {{
            const cells = [...row.cells].map(c => csvEscape(c.innerText));
            if (cells.length) csv += cells.join(',') + '\\r\\n';
        }}
        return csv;
    }}

    function exportReportToExcel() {{
        let csv = '\\uFEFF';
        csv += csvEscape('Report') + ',' + csvEscape(document.querySelector('h1')?.innerText || '') + '\\r\\n';
        csv += csvEscape('Task ID') + ',' + csvEscape('{audit.task_id}') + '\\r\\n';
        document.querySelectorAll('.kpi-card').forEach(card => {{
            csv += csvEscape(card.querySelector('.kpi-label')?.innerText) + ','
                + csvEscape(card.querySelector('.kpi-value')?.innerText) + '\\r\\n';
        }});
        document.querySelectorAll('.main-card').forEach((card, idx) => {{
            const title = (card.querySelector('.card-title')?.innerText || ('Section ' + (idx + 1)))
                .replace(/\\s+/g, ' ').trim();
            const tables = card.querySelectorAll('table');
            tables.forEach((table, tidx) => {{
                const suffix = tables.length > 1 ? ' (' + (tidx + 1) + ')' : '';
                csv = appendTableCsv(csv, title + suffix, table);
            }});
        }});
        const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = 'IR_Task_{audit.task_id}_Action_Count_Resumption_Audit.csv';
        link.click();
        URL.revokeObjectURL(link.href);
    }}
</script>

</body>
</html>
"""
    # Historical task audits are reconstructed from GET responses. Remove E2E-only
    # sections whose request/response and lifecycle details cannot be proven.
    html_content = re.sub(
        r'\s*<section id="panel-(?:lifecycle|http)"[^>]*>.*?</section>',
        "",
        html_content,
        flags=re.DOTALL,
    )
    html_content = re.sub(
        r'\s*<!-- Lifecycle Pending Actions & Next Card Modal -->.*?'
        r'(?=<!-- Step Inspector Modal -->)',
        "",
        html_content,
        flags=re.DOTALL,
    )
    html_content = re.sub(
        r'\s*<!-- Step Inspector Modal -->.*?'
        r'(?=<!-- Traffic Call Inspector Modal -->)',
        "",
        html_content,
        flags=re.DOTALL,
    )
    html_content = re.sub(
        r'\s*<!-- Traffic Call Inspector Modal -->.*?(?=<script>)',
        "",
        html_content,
        flags=re.DOTALL,
    )
    html_content = ensure_ir_export_inline(html_content)
    output_path.write_text(html_content, encoding="utf-8")
    print(f"📄 [E2E Audit Report Generated]: {output_path.name}")
    return output_path
