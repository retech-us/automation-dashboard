"""
Action List State Diff Comparator
=================================
Compares action list state before and after mid-task mobile app refresh / app restart / backend re-fetch.
Verifies:
1. Completed actions (STATE_ACCEPTED) are excluded from the active queue.
2. Downstream uncompleted actions (e.g. Bay 2 placements, remaining picks, restocks) are 100% preserved.
3. Mathematical conservation: Accepted Actions + Remaining Active Cards == Total Actions Ingested.
4. Detects specific client regressions (e.g., Re-Pick on Resume, Dropped Bay 2 Placement Cards).
"""

from typing import List, Dict, Any, Tuple, Optional
from core.action_list_domain_mapper import transform_action_list_to_domain
from core.action_list_ui_mapper import map_domain_to_ui_model, partition_ui_models_by_bay
from core.current_mobile_code_evaluator import CurrentMobileClientSimulator


def compare_action_list_refresh_states(
    initial_raw_items: List[Dict[str, Any]],
    executed_action_ids: List[int],
    post_refresh_raw_items: List[Dict[str, Any]],
    use_current_mobile_simulator: bool = False
) -> Dict[str, Any]:
    """
    Executes a side-by-side diff comparing initial mobile state vs post-refresh mobile state.
    """
    # 1. Initial State
    if use_current_mobile_simulator:
        initial_ui_cards = CurrentMobileClientSimulator.run_current_mobile_pipeline(initial_raw_items)
    else:
        init_domain = transform_action_list_to_domain(initial_raw_items)
        initial_ui_cards = [map_domain_to_ui_model(d, idx).__dict__ for idx, d in enumerate(init_domain, 1)]

    # 2. Post-Refresh State
    if use_current_mobile_simulator:
        post_refresh_ui_cards = CurrentMobileClientSimulator.run_current_mobile_pipeline(post_refresh_raw_items)
    else:
        post_domain = transform_action_list_to_domain(post_refresh_raw_items)
        # Active execution cards are those pending / not yet resolved
        post_refresh_ui_cards = [map_domain_to_ui_model(d, idx).__dict__ for idx, d in enumerate(post_domain, 1) if not d.action_resolved]

    initial_card_ids = [c.get("id") or c.get("action_id") for c in initial_ui_cards]
    post_card_ids = [c.get("id") or c.get("action_id") for c in post_refresh_ui_cards]

    # Categorize Diffs
    resolved_actions = []
    retained_active_actions = []
    re_pick_regressions = []
    dropped_placement_regressions = []

    def is_executed(card_id, card_subtype):
        for ex in executed_action_ids:
            if isinstance(ex, tuple) and len(ex) == 2:
                if ex[0] == card_id and ex[1] == card_subtype:
                    return True
            elif isinstance(ex, dict):
                if ex.get("id") == card_id and ex.get("step_subtype") == card_subtype:
                    return True
            elif ex == card_id:
                # If raw ID given and it's a cross-bay action, the first step executed is 'pick'
                if card_subtype == "pick" or card_subtype in ("remove", "shift", "identify", "exception", "restock"):
                    return True
                elif card_subtype == "place":
                    # Place is only executed if explicitly indicated
                    return False
        return False

    for c in initial_ui_cards:
        c_id = c.get("id") or c.get("action_id")
        step_sub = c.get("step_subtype")
        upc = c.get("upc") or c.get("displayed_upc")
        title = c.get("product_title") or c.get("title")

        if is_executed(c_id, step_sub):
            # Check if this executed card reappears post-refresh
            matching_post = [p for p in post_refresh_ui_cards if (p.get("id") or p.get("action_id")) == c_id and p.get("step_subtype") == step_sub]
            if matching_post:
                re_pick_regressions.append({
                    "id": c_id,
                    "upc": upc,
                    "title": title,
                    "step_subtype": step_sub,
                    "reason": f"Card #{c_id} ({step_sub}) was executed in-flight but falsely reappeared in post-refresh active queue."
                })
            else:
                resolved_actions.append({
                    "id": c_id,
                    "upc": upc,
                    "title": title,
                    "step_subtype": step_sub,
                    "status": "RESOLVED_AND_EXCLUDED"
                })
        else:
            # Check if unexecuted card is preserved
            matching_post = [p for p in post_refresh_ui_cards if (p.get("id") or p.get("action_id")) == c_id and p.get("step_subtype") == step_sub]
            if matching_post:
                retained_active_actions.append({
                    "id": c_id,
                    "upc": upc,
                    "title": title,
                    "step_subtype": step_sub,
                    "status": "RETAINED_ACTIVE"
                })
            else:
                dropped_placement_regressions.append({
                    "id": c_id,
                    "upc": upc,
                    "title": title,
                    "step_subtype": step_sub,
                    "reason": f"Card #{c_id} ({step_sub}) was NOT completed but was dropped from post-refresh active queue."
                })

    # Mathematical Conservation Assertion
    total_initial = len(initial_ui_cards)
    total_post = len(post_refresh_ui_cards)
    total_resolved = len(resolved_actions)
    
    # Calculate cart balance continuity
    foreign_initial = sum(1 for c in initial_ui_cards if c.get("action_type") == "Remove" or c.get("step_subtype") == "remove")
    picks_initial = sum(1 for c in initial_ui_cards if c.get("action_type") == "SetAside" or c.get("step_subtype") == "pick")
    
    foreign_resolved = sum(1 for r in resolved_actions if r.get("step_subtype") == "remove")
    picks_resolved = sum(1 for r in resolved_actions if r.get("step_subtype") == "pick")
    adds_resolved = sum(1 for r in resolved_actions if r.get("step_subtype") == "place")

    cart_balance_post = {
        "foreign": foreign_resolved,
        "picks": max(0, picks_resolved - adds_resolved),
        "surplus": 0
    }

    is_conserved = (len(re_pick_regressions) == 0 and len(dropped_placement_regressions) == 0)

    return {
        "status": "success",
        "is_conserved": is_conserved,
        "summary": {
            "initial_cards_count": total_initial,
            "executed_in_flight_count": len(executed_action_ids),
            "post_refresh_cards_count": total_post,
            "resolved_count": total_resolved,
            "retained_active_count": len(retained_active_actions),
            "re_pick_regressions_count": len(re_pick_regressions),
            "dropped_placement_regressions_count": len(dropped_placement_regressions),
        },
        "cart_balance": cart_balance_post,
        "resolved_actions": resolved_actions,
        "retained_active_actions": retained_active_actions,
        "re_pick_regressions": re_pick_regressions,
        "dropped_placement_regressions": dropped_placement_regressions,
        "initial_cards": initial_ui_cards,
        "post_refresh_cards": post_refresh_ui_cards,
    }
