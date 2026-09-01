"""
ActionListUiMapper
Faithful Python implementation of Android's ActionListUiMapper.kt and iOS SwiftUI/UIKit presentation model.

Maps ActionListDomainModel items to ActionListItemUiModel:
1. Bay, Shelf, Position resolution based on getExpectedOrCurrentValue().
2. Mobile UI Screen Banners (e.g., 'SET ASIDE FOR BAY 2', 'ADD TO SHELF BAY 1').
3. Color themes: Warm Orange (#FCE4D6), Soft Green (#E2EFDA), Soft Red (#F8CBAD).
4. Physical movement lines: 'Bay 1, Sh 5, Pos 1 ➔ Bay 2, Sh 3, Pos 4'.
5. Multi-bay grouping and total counter map calculations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from core.action_list_domain_mapper import ActionListDomainModel, ActionTypeByName


@dataclass
class ActionListItemUiModel:
    id: int
    step_index: int
    product_title: str
    upc: str
    displayed_upc: str
    thumbnail_url: str
    action_type: str
    action_type_enum: str
    step_subtype: str  # 'pick', 'place', 'shift', 'remove', 'restock'
    
    # Active Screen Bay context
    screen_bay: str
    shelf: int
    position: int
    
    # Movement Details
    source_bay: str
    source_shelf: Optional[int]
    source_position: Optional[int]
    target_bay: str
    target_shelf: Optional[int]
    target_position: Optional[int]
    movement_line: str
    
    # Mobile UI Presentation
    banner_text: str
    banner_color_theme: str  # 'orange', 'green', 'red'
    banner_bg_hex: str
    banner_font_hex: str
    user_action_meaning: str
    reason: str = ""
    is_completed: bool = False


@dataclass
class BayUiSummary:
    bay_name: str
    total_actions: int
    set_aside_count: int
    fix_in_bay_count: int
    add_to_shelf_count: int
    restock_count: int
    remove_count: int
    identify_count: int
    items: List[ActionListItemUiModel] = field(default_factory=list)


def resolve_expected_or_current(
    action_type_enum: str,
    step_subtype: str,
    expected: Any,
    current: Any,
) -> Any:
    """
    Mirror Kotlin getExpectedOrCurrentValue:
    If item is SetAside / pick -> takes current value (source).
    If item is Add / Move / Fix / Restock -> takes expected value (target).
    """
    if step_subtype == "pick" or action_type_enum == ActionTypeByName.SET_ASIDE.value:
        return current if current is not None else expected
    if action_type_enum in (
        ActionTypeByName.FIX_POSITION_IN_BAY.value,
        ActionTypeByName.FIX_POSITION_MOVE_TO_BAY.value,
        ActionTypeByName.PLACE_ON_SHELF_ADD_TO_BAY.value,
        ActionTypeByName.PLACE_ON_SHELF_RESTOCK.value,
    ):
        return expected if expected is not None else current
    return current if current is not None else expected


def map_domain_to_ui_model(domain_item: ActionListDomainModel, step_index: int) -> ActionListItemUiModel:
    curr = domain_item.current_position
    exp = domain_item.expected_position

    src_bay = (curr.section_info.name if curr and curr.section_info and curr.section_info.name else None) or (exp.section_info.name if exp and exp.section_info and exp.section_info.name else None) or "1"
    src_sh = curr.shelf if curr else None
    src_pos = curr.position if curr else None

    tgt_bay = (exp.section_info.name if exp and exp.section_info and exp.section_info.name else None) or (curr.section_info.name if curr and curr.section_info and curr.section_info.name else None) or "1"
    tgt_sh = exp.shelf if exp else None
    tgt_pos = exp.position if exp else None

    # Resolve active screen bay based on whether this step is a Pick or Place
    screen_bay = resolve_expected_or_current(
        domain_item.action_type_enum,
        domain_item.step_subtype,
        tgt_bay,
        src_bay,
    )
    shelf = resolve_expected_or_current(
        domain_item.action_type_enum,
        domain_item.step_subtype,
        tgt_sh,
        src_sh,
    ) or -1
    pos = resolve_expected_or_current(
        domain_item.action_type_enum,
        domain_item.step_subtype,
        tgt_pos,
        src_pos,
    ) or -1

    # Movement Line
    src_desc = f"Bay {src_bay}, Sh {src_sh or '?'}, Pos {src_pos or '?'}" if curr else "Cart / Inventory"
    tgt_desc = f"Bay {tgt_bay}, Sh {tgt_sh or '?'}, Pos {tgt_pos or '?'}" if exp else "Backroom Cart"
    movement_line = f"{src_desc} ➔ {tgt_desc}"

    # Banner text, color theme, and user action meaning
    if domain_item.step_subtype == "pick" or domain_item.action_type == "SetAside":
        banner_text = f"SET ASIDE FOR BAY {tgt_bay}"
        banner_color = "orange"
        bg_hex = "#FCE4D6"
        font_hex = "#C65911"
        action_meaning = f"Pick from Bay {src_bay} shelf and stage on cart for Bay {tgt_bay}"
    elif domain_item.action_type_enum == ActionTypeByName.FIX_POSITION_IN_BAY.value:
        banner_text = f"FIX POSITION IN BAY {tgt_bay}"
        banner_color = "orange"
        bg_hex = "#FCE4D6"
        font_hex = "#C65911"
        action_meaning = f"Slide item horizontally across shelf {tgt_sh} to position {tgt_pos}"
    elif domain_item.action_type_enum == ActionTypeByName.PLACE_ON_SHELF_ADD_TO_BAY.value or domain_item.step_subtype == "place":
        banner_text = f"ADD TO SHELF BAY {tgt_bay}"
        banner_color = "green"
        bg_hex = "#E2EFDA"
        font_hex = "#375623"
        action_meaning = f"Take staged item from cart and place on Bay {tgt_bay}, Shelf {tgt_sh}, Pos {tgt_pos}"
    elif domain_item.action_type_enum == ActionTypeByName.PLACE_ON_SHELF_RESTOCK.value:
        banner_text = f"RESTOCK BAY {tgt_bay}"
        banner_color = "green"
        bg_hex = "#E2EFDA"
        font_hex = "#375623"
        action_meaning = f"Bring new stock from backroom and place on Bay {tgt_bay}, Shelf {tgt_sh}, Pos {tgt_pos}"
    elif domain_item.action_type_enum == ActionTypeByName.REMOVE.value:
        banner_text = f"REMOVE FROM BAY {src_bay}"
        banner_color = "red"
        bg_hex = "#F8CBAD"
        font_hex = "#C00000"
        action_meaning = f"Remove foreign/discontinued product from Bay {src_bay} and put in cart for backroom"
    elif domain_item.action_type_enum == ActionTypeByName.IDENTIFY.value:
        banner_text = f"IDENTIFY PRODUCT IN BAY {src_bay}"
        banner_color = "orange"
        bg_hex = "#FCE4D6"
        font_hex = "#C65911"
        action_meaning = f"Scan barcode on Shelf {src_sh}, Pos {src_pos} to identify unknown item"
    elif domain_item.action_type == "Exception" or domain_item.step_subtype == "exception" or domain_item.action_type_enum == ActionTypeByName.EXCEPTION.value:
        banner_text = f"EXCEPTION IN BAY {src_bay}"
        banner_color = "neutral"
        bg_hex = "#EDEDED"
        font_hex = "#595959"
        action_meaning = f"Item marked as exception ({domain_item.reason or 'wrong/damaged item'}). Staged for manager review."
    else:
        banner_text = f"ACTION FOR BAY {screen_bay}"
        banner_color = "green"
        bg_hex = "#E2EFDA"
        font_hex = "#375623"
        action_meaning = "Perform planogram reset action"

    return ActionListItemUiModel(
        id=domain_item.id,
        step_index=step_index,
        product_title=domain_item.product_title,
        upc=domain_item.upc,
        displayed_upc=domain_item.displayed_upc,
        thumbnail_url=domain_item.planogram_thumbnail,
        action_type=domain_item.action_type,
        action_type_enum=domain_item.action_type_enum,
        step_subtype=domain_item.step_subtype,
        screen_bay=str(screen_bay),
        shelf=shelf,
        position=pos,
        source_bay=str(src_bay),
        source_shelf=src_sh,
        source_position=src_pos,
        target_bay=str(tgt_bay),
        target_shelf=tgt_sh,
        target_position=tgt_pos,
        movement_line=movement_line,
        banner_text=banner_text,
        banner_color_theme=banner_color,
        banner_bg_hex=bg_hex,
        banner_font_hex=font_hex,
        user_action_meaning=action_meaning,
        reason=domain_item.reason,
        is_completed=domain_item.action_resolved,
    )


def partition_ui_models_by_bay(
    domain_items: List[ActionListDomainModel],
    available_bays: Optional[List[str]] = None,
) -> Dict[str, BayUiSummary]:
    """
    Groups and sorts action items for every active bay in the planogram.
    Sorts each bay by: SET_ASIDE (0) -> FIX_POSITION_IN_BAY (2) -> ADD_TO_BAY (3) -> RESTOCK (4) -> REMOVE (5).
    """
    ui_items: List[ActionListItemUiModel] = []
    for idx, d_item in enumerate(domain_items, start=1):
        ui_items.append(map_domain_to_ui_model(d_item, idx))

    # Determine all bays
    bays_set = set(available_bays or [])
    for it in ui_items:
        if it.screen_bay:
            bays_set.add(it.screen_bay)
    
    sorted_bays = sorted(list(bays_set), key=lambda x: int(x) if x.isdigit() else 999)
    bay_map: Dict[str, BayUiSummary] = {}

    for bay_name in sorted_bays:
        bay_items = [it for it in ui_items if it.screen_bay == bay_name]
        
        # Sort items inside the bay: Invaders (Remove) & Picks (Set Aside) first, then Shifts, then Identify, then Adds, then Restocks
        def bay_item_sort_key(it: ActionListItemUiModel) -> int:
            if it.action_type_enum == ActionTypeByName.REMOVE.value:
                return 0
            if it.step_subtype == "pick" or it.action_type == "SetAside":
                return 1
            if it.action_type_enum == ActionTypeByName.FIX_POSITION_IN_BAY.value:
                return 2
            if it.action_type_enum == ActionTypeByName.IDENTIFY.value:
                return 3
            if it.action_type_enum == ActionTypeByName.PLACE_ON_SHELF_ADD_TO_BAY.value or it.step_subtype == "place":
                return 4
            if it.action_type_enum == ActionTypeByName.PLACE_ON_SHELF_RESTOCK.value:
                return 5
            return 6

        sorted_bay_items = sorted(bay_items, key=bay_item_sort_key)

        # Recalculate bay step indices 1..N
        reindexed = []
        for i, item in enumerate(sorted_bay_items, start=1):
            item.step_index = i
            reindexed.append(item)

        set_aside_cnt = sum(1 for it in reindexed if it.step_subtype == "pick" or it.action_type == "SetAside")
        fix_in_bay_cnt = sum(1 for it in reindexed if it.action_type_enum == ActionTypeByName.FIX_POSITION_IN_BAY.value)
        add_cnt = sum(1 for it in reindexed if (it.action_type_enum == ActionTypeByName.PLACE_ON_SHELF_ADD_TO_BAY.value or it.step_subtype == "place"))
        restock_cnt = sum(1 for it in reindexed if it.action_type_enum == ActionTypeByName.PLACE_ON_SHELF_RESTOCK.value)
        remove_cnt = sum(1 for it in reindexed if it.action_type_enum == ActionTypeByName.REMOVE.value)
        identify_cnt = sum(1 for it in reindexed if it.action_type_enum == ActionTypeByName.IDENTIFY.value)

        bay_map[bay_name] = BayUiSummary(
            bay_name=bay_name,
            total_actions=len(reindexed),
            set_aside_count=set_aside_cnt,
            fix_in_bay_count=fix_in_bay_cnt,
            add_to_shelf_count=add_cnt,
            restock_count=restock_cnt,
            remove_count=remove_cnt,
            identify_count=identify_cnt,
            items=reindexed,
        )

    return bay_map


@dataclass
class ActionCompletionSyncRecord:
    step_number: int
    action_id: int
    product_title: str
    upc: str
    screen_bay: str
    action_type: str
    banner_text: str
    completed_at: str
    backend_endpoint: str
    backend_http_code: int
    state_before: str  # 'STATE_IDLE'
    state_after: str   # 'STATE_ACCEPTED'
    shelf_state_after: str
    cart_balance_after: int


def build_global_action_sequence(
    domain_items: List[ActionListDomainModel],
) -> List[ActionListItemUiModel]:
    """
    Builds the exact associate physical workflow sequence:
    1. Global Identify Queue (All bays).
    2. Global Invader Removal Queue (All bays).
    3. Bay-by-Bay Queue (For each bay: Set Aside -> Fix in Bay -> Add -> Restock).
    """
    ui_items = [map_domain_to_ui_model(d, idx) for idx, d in enumerate(domain_items, start=1)]

    # 1. Global Identifies
    identifies = [it for it in ui_items if it.action_type_enum == ActionTypeByName.IDENTIFY.value]
    identifies.sort(key=lambda x: (int(x.screen_bay) if x.screen_bay.isdigit() else 99, x.shelf, int(x.position) if str(x.position).isdigit() else 99))

    # 2. Global Invader Removals
    removals = [it for it in ui_items if it.action_type_enum == ActionTypeByName.REMOVE.value]
    removals.sort(key=lambda x: (int(x.screen_bay) if x.screen_bay.isdigit() else 99, x.shelf, int(x.position) if str(x.position).isdigit() else 99))

    # 3. Bay-by-Bay items
    bay_map = partition_ui_models_by_bay(domain_items)
    bay_by_bay_items = []
    for bay_name in sorted(bay_map.keys(), key=lambda x: int(x) if x.isdigit() else 99):
        summary = bay_map[bay_name]
        # Filter out identify and remove since handled in global queues
        b_items = [it for it in summary.items if it.action_type_enum not in (ActionTypeByName.IDENTIFY.value, ActionTypeByName.REMOVE.value)]
        bay_by_bay_items.extend(b_items)

    complete_sequence = identifies + removals + bay_by_bay_items
    for idx, item in enumerate(complete_sequence, start=1):
        item.step_index = idx

    return complete_sequence


def simulate_associate_execution_and_sync(
    sequence: List[ActionListItemUiModel],
    task_id: int,
) -> List[ActionCompletionSyncRecord]:
    """
    Simulates associate step execution and generates the exact backend update records.
    Tracks live cart balance and shelf transitions after every action.
    """
    sync_records: List[ActionCompletionSyncRecord] = []
    cart_balance = 0

    for idx, item in enumerate(sequence, start=1):
        # Update physical cart balance
        if item.action_type_enum == ActionTypeByName.REMOVE.value:
            cart_balance += 1
            shelf_state = f"Bay {item.screen_bay}, Sh {item.shelf}, Pos {item.position} CLEARED (Invader to Cart)"
        elif item.step_subtype == "pick" or item.action_type == "SetAside":
            cart_balance += 1
            shelf_state = f"Bay {item.screen_bay}, Sh {item.shelf}, Pos {item.position} CLEARED (POG Item Staged to Cart)"
        elif item.step_subtype == "place" or item.action_type_enum == ActionTypeByName.PLACE_ON_SHELF_ADD_TO_BAY.value:
            cart_balance = max(0, cart_balance - 1)
            shelf_state = f"Bay {item.screen_bay}, Sh {item.shelf}, Pos {item.position} OCCUPIED (Placed from Cart)"
        elif item.action_type_enum == ActionTypeByName.PLACE_ON_SHELF_RESTOCK.value:
            shelf_state = f"Bay {item.screen_bay}, Sh {item.shelf}, Pos {item.position} RESTOCKED (From Backroom Box)"
        elif item.action_type_enum == ActionTypeByName.FIX_POSITION_IN_BAY.value:
            shelf_state = f"Bay {item.screen_bay}, Sh {item.shelf} ALIGNED (Direct Slide to Pos {item.target_position})"
        else:
            shelf_state = f"Bay {item.screen_bay}, Sh {item.shelf}, Pos {item.position} IDENTIFIED"

        sync_records.append(
            ActionCompletionSyncRecord(
                step_number=idx,
                action_id=item.id,
                product_title=item.product_title,
                upc=item.displayed_upc,
                screen_bay=item.screen_bay,
                action_type=item.action_type_enum,
                banner_text=item.banner_text,
                completed_at=f"2026-08-22T06:{30 + (idx // 60):02d}:{idx % 60:02d}Z",
                backend_endpoint=f"PATCH /api/v1/tasks/{task_id}/action-list/retailer/{item.id}/",
                backend_http_code=200,
                state_before="STATE_IDLE",
                state_after="STATE_ACCEPTED",
                shelf_state_after=shelf_state,
                cart_balance_after=cart_balance,
            )
        )

    return sync_records
