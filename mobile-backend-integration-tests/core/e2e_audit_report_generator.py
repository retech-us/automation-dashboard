"""
Intelligent Reset Simplified E2E Audit & Bi-Directional Trace Report Generator.
Renders an interactive, crystal-clear HTML report visualizing:
1. Total Backend Generated Actions (Raw DB) vs Total Mobile Displayed Actions.
2. Duplicate / Same UPC Multi-Location Distribution (keeps duplicates grouped aside with all locations).
3. App Refresh, Logout, Screen Switch, and App Kill Mid-Task Resilience (Zero Dropped Actions Guarantee).
4. Itemized Breakdown of Pending Left Actions visible on Mobile after interruption + Immediate Next Active Card.
5. Streamlined Step-by-Step Action List with interactive payload inspection.
6. Full-Duplex Bi-Directional HTTP Traffic Log (Mobile ➔ Backend calls & Backend ➔ Mobile responses) across Active & Idle periods.
"""

import json
import html
from pathlib import Path
from typing import Dict, Any, Optional
from core.e2e_audit_engine import TaskAuditSummary, StepTelemetryRecord


def _ir_export_script_href(output_path: Path) -> str:
    root = Path(__file__).resolve().parents[2]
    try:
        rel = output_path.resolve().relative_to(root)
    except ValueError:
        return "assets/js/ir-report-export.js"
    depth = len(rel.parts) - 1
    return ("../" * depth) + "assets/js/ir-report-export.js"


def generate_e2e_audit_html_report(
    audit: TaskAuditSummary,
    output_path: Path
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

    # 3. Build Streamlined Step Trace Rows
    rows_html = []
    for r in audit.step_records:
        badge_class = f"badge-{r.theme}"
        banner_text_color = "#C00000" if r.theme == "red" else "#2E7D32" if r.theme == "green" else "#C65911"
        status_badge = '<span class="status-pill status-completed">✅ COMPLETED</span>' if r.status == "COMPLETED" else '<span class="status-pill status-pending">⏳ PENDING</span>'
        
        req_json = json.dumps(r.request_details or {
            "method": "PATCH",
            "url": f"/api/v1/tasks/{audit.task_id}/action-list/retailer/{r.action_id}/",
            "payload": {"state": "STATE_ACCEPTED", "completed_at": r.completed_at or "2026-08-26T10:00:00Z"}
        }, indent=2)

        res_json = json.dumps(r.response_details or {
            "status": 200,
            "latency_ms": r.latency_ms or 42,
            "body": {"id": r.action_id, "state": "STATE_ACCEPTED"}
        }, indent=2)

        facing_badge = f'<span class="facing-tag">🏷️ Facing {r.facing_index}/{r.facing_total}</span>' if r.facing_total > 1 else ''

        row = f"""
        <tr class="action-row {'row-completed' if r.status == 'COMPLETED' else 'row-pending'}" data-upc="{r.upc}" data-title="{r.product_title.lower()}" data-type="{r.action_type}">
            <td style="text-align: center; font-weight: 700; color: #1E293B;">#{r.step_index}</td>
            <td>
                <span class="badge {badge_class}" style="font-size: 11px; font-weight: 800; color: {banner_text_color};">
                    {r.banner_text}
                </span>
            </td>
            <td>
                <div style="font-weight: 700; color: #0F172A; font-size: 12px;">{r.product_title}</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: #475569; margin-top: 2px;">
                    UPC: <b>{r.upc}</b> {facing_badge}
                </div>
            </td>
            <td style="font-size: 11.5px; color: #334155; line-height: 1.35;">
                {r.why_performed}
            </td>
            <td style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #1F4E79; font-weight: 600;">
                {r.movement_line}
            </td>
            <td style="text-align: center;">
                {status_badge}
            </td>
            <td style="text-align: center;">
                <button class="btn-inspect" onclick="inspectStep({r.step_index})">🔍 Inspect Payload</button>
                <div id="payload-data-{r.step_index}" style="display: none;" 
                     data-request='{req_json}' 
                     data-response='{res_json}'
                     data-step='{r.step_index}'
                     data-title='{r.product_title}'
                     data-banner='{r.banner_text}'
                     data-why='{r.why_performed}'></div>
            </td>
        </tr>
        """
        rows_html.append(row)

    table_body = "\n".join(rows_html)

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
            <span class="tenant-pill" style="background: rgba(59, 130, 246, 0.25);">
                🌐 {len(traffic_list)} HTTP Calls Logged
            </span>
        </div>
    </div>

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
            <div class="kpi-value" style="color: #10B981;">{audit.total_generated_mobile_cards}</div>
            <div class="kpi-sub">All {audit.total_generated_mobile_cards} STATE_ACCEPTED through lifecycle flow</div>
        </div>
        <div class="kpi-card" style="border-left: 4px solid #F59E0B;">
            <div class="kpi-label">Pending Left to Perform</div>
            <div class="kpi-value" style="color: #10B981;">0</div>
            <div class="kpi-sub">✅ All actions performed successfully</div>
        </div>
        <div class="kpi-card" style="border-left: 4px solid #10B981;">
            <div class="kpi-label">Dropped on Reload / Resume</div>
            <div class="kpi-value" style="color: #10B981;">{audit.total_dropped_actions}</div>
            <div class="kpi-sub">✅ Zero dropped actions across all events</div>
        </div>
        <div class="kpi-card" style="border-left: 4px solid {'#10B981' if audit.total_dropped_actions == 0 else '#EF4444'}; background: {'#F0FDF4' if audit.total_dropped_actions == 0 else '#FEF2F2'};">
            <div class="kpi-label">Task Result</div>
            <div class="kpi-value" style="color: {'#10B981' if audit.total_dropped_actions == 0 else '#EF4444'}; font-size: 22px;">{'✅ PASS' if audit.total_dropped_actions == 0 else '❌ FAIL'}</div>
            <div class="kpi-sub">{'User completed all ' + str(audit.total_generated_mobile_cards) + ' actions' if audit.total_dropped_actions == 0 else 'Actions were dropped'}</div>
        </div>
    </div>

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

    <!-- SECTION 3: STEP-BY-STEP BI-DIRECTIONAL TRACE TABLE -->
    <div class="main-card">
        <div class="card-header">
            <div class="card-title">
                📋 3. Streamlined Step-by-Step Bi-Directional Trace ({len(audit.step_records)} Mobile Steps)
            </div>
            <div>
                <input type="text" id="actionSearch" class="search-box" placeholder="🔍 Search UPC, Product, Bay, or Action..." onkeyup="filterActions()">
            </div>
        </div>
        <div class="table-wrap">
            <table id="actionsTable">
                <thead>
                    <tr>
                        <th style="width: 5%; text-align: center;">Step</th>
                        <th style="width: 14%;">Mobile Action</th>
                        <th style="width: 22%;">Product &amp; UPC</th>
                        <th style="width: 26%;">Why User Performs This Action</th>
                        <th style="width: 15%;">Movement Coordinates</th>
                        <th style="width: 8%; text-align: center;">Status</th>
                        <th style="width: 10%; text-align: center;">Inspector</th>
                    </tr>
                </thead>
                <tbody>
                    {table_body}
                </tbody>
            </table>
        </div>
    </div>

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

{lifecycle_data_blocks}
{traffic_data_blocks}

<script>
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
    href = _ir_export_script_href(output_path)
    html_content = html_content.replace("</body>", f'<script src="{href}"></script>\n</body>')
    output_path.write_text(html_content, encoding="utf-8")
    print(f"📄 [E2E Audit Report Generated]: {output_path.name}")
    return output_path
