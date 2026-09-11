"""
ActionListDomainMapper
Faithful Python implementation of Android's ActionListDomainMapper.kt and iOS Swift action-list mapping.

Handles:
1. Priority sorting: SET_ASIDE (0) -> FIX_POSITION_MOVE_TO_BAY (1) -> FIX_POSITION_IN_BAY (2) -> PLACE_ON_SHELF_ADD_TO_BAY (3) -> PLACE_ON_SHELF_RESTOCK (4)
2. STATE_IDLE filtering: only active items with state == 'STATE_IDLE' are processed.
3. 1-to-2 Step Duplication: items with action 'place_on_shelf_add_to_bay' generate TWO distinct domain models:
   - SetAside (Pick from source bay to cart)
   - AddItems (Place from cart to target shelf)
4. Coordinate and bay resolution.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ActionTypeByName(str, Enum):
    SET_ASIDE = "set_aside"
    FIX_POSITION_MOVE_TO_BAY = "fix_position_move_to_bay"
    FIX_POSITION_IN_BAY = "fix_position_in_bay"
    PLACE_ON_SHELF_ADD_TO_BAY = "place_on_shelf_add_to_bay"
    PLACE_ON_SHELF_RESTOCK = "place_on_shelf_restock"
    REMOVE = "remove"
    IDENTIFY = "identify"
    EXCEPTION = "exception"
    FINISH = "finish"


ACTION_PRIORITY_MAP = {
    ActionTypeByName.SET_ASIDE.value: 0,
    ActionTypeByName.FIX_POSITION_MOVE_TO_BAY.value: 1,
    ActionTypeByName.FIX_POSITION_IN_BAY.value: 2,
    ActionTypeByName.PLACE_ON_SHELF_ADD_TO_BAY.value: 3,
    ActionTypeByName.PLACE_ON_SHELF_RESTOCK.value: 4,
    ActionTypeByName.REMOVE.value: 5,
    ActionTypeByName.IDENTIFY.value: 6,
    ActionTypeByName.EXCEPTION.value: 7,
}


@dataclass
class SectionInfoDomainModel:
    id: Optional[int]
    name: str
    original_name: Optional[str] = None


@dataclass
class PositionDomainModel:
    action: Optional[str]
    section_info: SectionInfoDomainModel
    shelf: Optional[int] = None
    position: Optional[int] = None
    scan_id: Optional[int] = None
    facing_width: int = 0
    facing_height: int = 0
    coordinates: Optional[List[List[float]]] = None
    realogram_item_id: Optional[int] = None
    planogram_item_id: Optional[int] = None
    state: str = "STATE_IDLE"


@dataclass
class ActionListDomainModel:
    id: int
    source_id: int
    upc: str
    displayed_upc: str
    product_title: str
    product_id: int
    planogram_thumbnail: str
    action_type_reasons: str
    action_type: str  # 'SetAside', 'FixInBay', 'AddItems', 'Remove', 'Identify', etc.
    action_type_enum: str  # raw action string e.g. 'place_on_shelf_add_to_bay'
    store_planogram_id: int
    current_position: Optional[PositionDomainModel]
    expected_position: Optional[PositionDomainModel]
    action_resolved: bool
    is_new: bool
    reason: str = ""
    step_subtype: str = "standard"  # 'pick' for SetAside, 'place' for AddItems
    state: str = "STATE_IDLE"


def resolve_domain_action_type(raw_action: str) -> str:
    raw = (raw_action or "").lower()
    if raw in (ActionTypeByName.SET_ASIDE.value, ActionTypeByName.FIX_POSITION_MOVE_TO_BAY.value):
        return "SetAside"
    elif raw == ActionTypeByName.FIX_POSITION_IN_BAY.value:
        return "FixInBay"
    elif raw == ActionTypeByName.PLACE_ON_SHELF_ADD_TO_BAY.value:
        return "AddItems"
    elif raw == ActionTypeByName.PLACE_ON_SHELF_RESTOCK.value:
        return "Restock"
    elif raw == ActionTypeByName.REMOVE.value:
        return "Remove"
    elif raw == ActionTypeByName.IDENTIFY.value:
        return "Identify"
    elif raw == ActionTypeByName.EXCEPTION.value:
        return "Exception"
    return "Finish"


def compute_upc_check_digit(upc_11: str) -> str:
    if len(upc_11) != 11 or not upc_11.isdigit():
        return upc_11
    odd_sum = sum(int(upc_11[i]) for i in range(0, 11, 2))
    even_sum = sum(int(upc_11[i]) for i in range(1, 11, 2))
    total = (odd_sum * 3) + even_sum
    check_digit = (10 - (total % 10)) % 10
    return upc_11 + str(check_digit)


def resolve_full_upc(raw_upc: Any, disp_upc: Any) -> str:
    u = str(raw_upc or "").strip()
    d = str(disp_upc or "").strip()
    if len(u) >= 12:
        return u
    if len(d) >= 12:
        return d
    candidate = u or d
    if len(candidate) == 11 and candidate.isdigit():
        return compute_upc_check_digit(candidate)
    return candidate


def resolve_root_action_state(item: Dict[str, Any]) -> str:
    """
    Evaluates the root action state based on the 3 canonical Rebotics states:
    - STATE_IDLE
    - STATE_ACCEPTED
    - STATE_REJECTED
    (Note: STATE_COMPLETED does NOT exist in backend/mobile contract).

    For Cross-Bay actions (both current_position and expected_position present):
    - Root state is STATE_ACCEPTED ONLY WHEN BOTH current_position.state == 'STATE_ACCEPTED'
      AND expected_position.state == 'STATE_ACCEPTED'.
    - If either sub-position is STATE_REJECTED, root state is STATE_REJECTED.
    - If only one position is accepted (or both idle), root state remains STATE_IDLE.
    For Single-Position actions:
    - Root state follows the single existing sub-position's state or the root state.
    """
    curr = item.get("current_position")
    exp = item.get("expected_position")
    
    if curr and exp:
        curr_st = curr.get("state")
        exp_st = exp.get("state")
        
        # If sub-action states are present
        if curr_st or exp_st:
            curr_val = curr_st or "STATE_IDLE"
            exp_val = exp_st or "STATE_IDLE"
            
            if curr_val == "STATE_REJECTED" or exp_val == "STATE_REJECTED":
                return "STATE_REJECTED"
            elif curr_val == "STATE_ACCEPTED" and exp_val == "STATE_ACCEPTED":
                return "STATE_ACCEPTED"
            else:
                return "STATE_IDLE"
                
    elif curr and not exp:
        if curr.get("state"):
            return curr.get("state")
    elif exp and not curr:
        if exp.get("state"):
            return exp.get("state")
            
    return item.get("state", "STATE_IDLE")


def map_raw_action_to_domain(item: Dict[str, Any]) -> ActionListDomainModel:
    curr_raw = item.get("current_position") or {}
    exp_raw = item.get("expected_position") or {}

    curr_sec_raw = curr_raw.get("section_info") or {}
    exp_sec_raw = exp_raw.get("section_info") or {}

    curr_sec = SectionInfoDomainModel(
        id=curr_sec_raw.get("id"),
        name=str(curr_sec_raw.get("name", "")),
        original_name=curr_sec_raw.get("original_name"),
    )
    exp_sec = SectionInfoDomainModel(
        id=exp_sec_raw.get("id"),
        name=str(exp_sec_raw.get("name", "")),
        original_name=exp_sec_raw.get("original_name"),
    )

    curr_pos = PositionDomainModel(
        action=curr_raw.get("action"),
        section_info=curr_sec,
        shelf=curr_raw.get("shelf"),
        position=curr_raw.get("position"),
        scan_id=curr_raw.get("scan_id"),
        facing_width=item.get("horizontal_facings") or 0,
        facing_height=item.get("vertical_facings") or 0,
        coordinates=curr_raw.get("coordinates"),
        realogram_item_id=curr_raw.get("realogram_item_id"),
        state=curr_raw.get("state", item.get("state", "STATE_IDLE")),
    ) if item.get("current_position") else None

    exp_pos = PositionDomainModel(
        action=exp_raw.get("action"),
        section_info=exp_sec,
        shelf=exp_raw.get("shelf"),
        position=exp_raw.get("position"),
        scan_id=exp_raw.get("scan_id"),
        facing_width=exp_raw.get("horizontal_facings") or (item.get("horizontal_facings") or 0),
        facing_height=exp_raw.get("vertical_facings") or (item.get("vertical_facings") or 0),
        planogram_item_id=exp_raw.get("planogram_item_id"),
        state=exp_raw.get("state", item.get("state", "STATE_IDLE")),
    ) if item.get("expected_position") else None

    raw_action = (exp_raw.get("action") or curr_raw.get("action") or item.get("action") or "").lower()
    domain_type = resolve_domain_action_type(raw_action)
    full_upc = resolve_full_upc(item.get("upc"), item.get("displayed_upc"))

    step_sub = "standard"
    if domain_type == "SetAside":
        step_sub = "pick"
    elif domain_type == "AddItems":
        step_sub = "place"
    elif domain_type == "Restock":
        step_sub = "restock"
    elif domain_type == "FixInBay":
        step_sub = "shift"
    elif domain_type == "Remove":
        step_sub = "remove"
    elif domain_type == "Identify":
        step_sub = "identify"
    elif domain_type == "Exception":
        step_sub = "exception"

    computed_state = resolve_root_action_state(item)

    return ActionListDomainModel(
        id=item.get("id", 0),
        source_id=item.get("source_id", 0),
        upc=full_upc,
        displayed_upc=full_upc,
        product_title=item.get("product_title") or item.get("product_name") or "Unnamed Product",
        product_id=item.get("product_id", 0),
        planogram_thumbnail=item.get("image") or item.get("thumbnail") or "",
        action_type_reasons=item.get("action", ""),
        action_type=domain_type,
        action_type_enum=raw_action,
        store_planogram_id=item.get("store_planogram_id", 0),
        current_position=curr_pos,
        expected_position=exp_pos,
        action_resolved=computed_state not in ("STATE_IDLE", ""),
        is_new=bool(item.get("is_new")),
        reason=item.get("reason", ""),
        step_subtype=step_sub,
        state=computed_state,
    )


def transform_action_list_to_domain(raw_results: List[Dict[str, Any]], include_completed: bool = False) -> List[ActionListDomainModel]:
    """
    Executes the exact Kotlin ActionListDomainMapper.kt pipeline:
    1. Sort by action priority.
    2. Filter state == 'STATE_IDLE' (or retain completed if include_completed=True or if dataset contains only completed items).
    3. Distinct by item.id.
    4. Duplicate PLACE_ON_SHELF_ADD_TO_BAY into SetAside (Pick) + AddItems (Place).
    """
    # 1. Sort by action priority
    def get_priority(item: Dict[str, Any]) -> int:
        exp_act = (item.get("expected_position") or {}).get("action")
        curr_act = (item.get("current_position") or {}).get("action")
        act = (exp_act or curr_act or item.get("action") or "").lower()
        return ACTION_PRIORITY_MAP.get(act, 999)

    sorted_raw = sorted(raw_results, key=get_priority)
    # 2. Filter for active pending items: STATE_IDLE only (exclude finished STATE_ACCEPTED and STATE_REJECTED unless include_completed=True)
    if include_completed:
        items_to_process = sorted_raw
    else:
        items_to_process = [
            it for it in sorted_raw 
            if it.get("state") == "STATE_IDLE" or not it.get("state")
        ]
    
    # 3. Deduplicate by action item id (Faithful to Kotlin ActionListDomainMapper.kt distinctBy { it.id })
    distinct_items = []
    seen_ids = set()
    for it in items_to_process:
        it_id = it.get("id")
        if it_id is not None:
            if it_id not in seen_ids:
                seen_ids.add(it_id)
                distinct_items.append(it)
        else:
            distinct_items.append(it)

    # 4. Map to domain models for all distinct items
    domain_models: List[ActionListDomainModel] = []
    for idx, item in enumerate(distinct_items, start=1):
        dm = map_raw_action_to_domain(item)
        # Ensure unique ID per physical item facing
        dm.source_id = idx
        domain_models.append(dm)

    # 4. 1-to-2 Step Duplication:
    # Cross-bay items (current bay != target bay) generate TWO distinct domain models:
    # 1) SetAside (Pick from source bay to cart)
    # 2) AddItems (Place from cart to target shelf)
    # Intra-bay items (current bay == target bay) are strictly FixInBay (horizontal shift on same bay shelf).
    set_asides: List[ActionListDomainModel] = []
    final_placements: List[ActionListDomainModel] = []

    for item in domain_models:
        curr_b = item.current_position.section_info.name if item.current_position and item.current_position.section_info else None
        exp_b = item.expected_position.section_info.name if item.expected_position and item.expected_position.section_info else None
        curr_sh = item.current_position.shelf if item.current_position else None
        exp_sh = item.expected_position.shelf if item.expected_position else None
        curr_act = (item.current_position.action or "").lower() if item.current_position else ""
        exp_act = (item.expected_position.action or "").lower() if item.expected_position else ""

        # 1. 2-Phase Move: Pick from source (SetAside) ➔ Place into target (AddItems)
        # Occurs when:
        # - Cross-Bay move (Source bay != Target bay)
        # - Current position action is explicitly 'set_aside' or root action is SetAside
        is_cross_bay = (curr_b is not None and exp_b is not None and str(curr_b) != str(exp_b))
        is_explicit_set_aside = (
            curr_act == "set_aside"
            or item.action_type == "SetAside"
            or item.action_type_enum == ActionTypeByName.SET_ASIDE.value
        )
        is_two_phase_move = (
            (item.current_position is not None and item.expected_position is not None) and (
                is_cross_bay
                or is_explicit_set_aside
                or item.action_type_enum in (ActionTypeByName.PLACE_ON_SHELF_ADD_TO_BAY.value, ActionTypeByName.FIX_POSITION_MOVE_TO_BAY.value)
            )
        )

        # 2. Intra-Bay Alignment (FixInBay)
        # Occurs when move is within the same bay and backend action is fix_position_fix_in_bay
        is_intra_bay_shift = (
            (not is_cross_bay and not is_explicit_set_aside) and (
                exp_act == "fix_position_fix_in_bay"
                or item.action_type == "FixInBay"
                or item.action_type_enum == ActionTypeByName.FIX_POSITION_IN_BAY.value
                or (
                    item.current_position is not None and item.expected_position is not None
                    and curr_b is not None and exp_b is not None and str(curr_b) == str(exp_b)
                    and curr_act not in ("set_aside", "remove")
                    and exp_act not in ("place_on_shelf_add_to_bay", "add_from_cart_to_bay", "add")
                )
            )
        )

        if is_two_phase_move:
            # 1) Pick step (SetAside) in source bay
            pick_state = item.current_position.state if item.current_position else item.state
            pick_clone = ActionListDomainModel(
                id=item.id,
                source_id=item.source_id,
                upc=item.upc,
                displayed_upc=item.displayed_upc,
                product_title=item.product_title,
                product_id=item.product_id,
                planogram_thumbnail=item.planogram_thumbnail,
                action_type_reasons=item.action_type_reasons,
                action_type="SetAside",
                action_type_enum=ActionTypeByName.SET_ASIDE.value,
                store_planogram_id=item.store_planogram_id,
                current_position=item.current_position,
                expected_position=item.expected_position,
                action_resolved=pick_state != "STATE_IDLE",
                is_new=item.is_new,
                reason=item.reason,
                step_subtype="pick",
                state=pick_state,
            )
            set_asides.append(pick_clone)

            # 2) Place step (AddItems) in target bay
            place_state = item.expected_position.state if item.expected_position else item.state
            place_clone = ActionListDomainModel(
                id=item.id,
                source_id=item.source_id,
                upc=item.upc,
                displayed_upc=item.displayed_upc,
                product_title=item.product_title,
                product_id=item.product_id,
                planogram_thumbnail=item.planogram_thumbnail,
                action_type_reasons=item.action_type_reasons,
                action_type="AddItems",
                action_type_enum=ActionTypeByName.PLACE_ON_SHELF_ADD_TO_BAY.value,
                store_planogram_id=item.store_planogram_id,
                current_position=item.current_position,
                expected_position=item.expected_position,
                action_resolved=place_state != "STATE_IDLE",
                is_new=item.is_new,
                reason=item.reason,
                step_subtype="place",
                state=place_state,
            )
            final_placements.append(place_clone)

        elif is_intra_bay_shift:
            # Intra-bay horizontal shift (FixInBay)
            item.action_type = "FixInBay"
            item.action_type_enum = ActionTypeByName.FIX_POSITION_IN_BAY.value
            item.step_subtype = "shift"
            final_placements.append(item)

        else:
            # Removals, Identifies, Restocks, etc.
            final_placements.append(item)

    all_generated_models = set_asides + final_placements
    return sort_domain_models_by_mobile_canonical_order(all_generated_models)


def sort_domain_models_by_mobile_canonical_order(domain_models: List[ActionListDomainModel]) -> List[ActionListDomainModel]:
    """
    Enforces exact Mobile App Canonical Execution Order:
    1. Phase 1: All IDENTIFY actions (Scan physical barcodes first across all shelves).
    2. Phase 2: All REMOVE actions (Clear all foreign/delisted items into discard cart).
    3. Phase 3: SET_ASIDE (Pick from bay shelves to rolling cart to clear shelf space, ordered by bay, shelf, position).
    4. Phase 4: FIX_IN_BAY (Intra-bay horizontal shifts across shelves, ordered by bay, shelf, position).
    5. Phase 5: ADD_TO_SHELF / AddItems (Place staged items from cart into destination bay shelves, ordered by target bay, shelf, position).
    6. Phase 6: RESTOCK (Place fresh backroom inventory into destination bay shelves, ordered by target bay, shelf, position).
    """
    def mobile_sort_key(dm: ActionListDomainModel):
        act = (dm.action_type or "").upper()
        curr_b = dm.current_position.section_info.name if dm.current_position and dm.current_position.section_info else "1"
        exp_b = dm.expected_position.section_info.name if dm.expected_position and dm.expected_position.section_info else curr_b
        curr_sh = dm.current_position.shelf if dm.current_position and dm.current_position.shelf is not None else 999
        exp_sh = dm.expected_position.shelf if dm.expected_position and dm.expected_position.shelf is not None else curr_sh
        curr_pos = int(dm.current_position.position) if dm.current_position and str(dm.current_position.position).isdigit() else 999
        exp_pos = int(dm.expected_position.position) if dm.expected_position and str(dm.expected_position.position).isdigit() else 999

        # Phase 0: Global Identify
        if "IDENTIFY" in act:
            b_num = int(curr_b) if str(curr_b).isdigit() else 1
            return (0, b_num, curr_sh, curr_pos)
        
        # Phase 1: Global Remove (Delisted / foreign items)
        if "REMOVE" in act:
            b_num = int(curr_b) if str(curr_b).isdigit() else 1
            return (1, b_num, curr_sh, curr_pos)
        
        # Phase 2: SetAside (Picks from shelf to rolling cart)
        if "SET_ASIDE" in act or "SETASIDE" in act:
            b_num = int(curr_b) if str(curr_b).isdigit() else 1
            return (2, b_num, curr_sh, curr_pos)
        
        # Phase 3: FixInBay (Intra-bay horizontal slides)
        if "FIX_IN_BAY" in act or "FIXINBAY" in act:
            b_num = int(curr_b) if str(curr_b).isdigit() else 1
            return (3, b_num, curr_sh, curr_pos)
        
        # Phase 4: AddItems (Placements from cart to shelf)
        if "ADD" in act:
            b_num = int(exp_b) if str(exp_b).isdigit() else 1
            return (4, b_num, exp_sh, exp_pos)
        
        # Phase 5: Restock (Backroom additions)
        if "RESTOCK" in act:
            b_num = int(exp_b) if str(exp_b).isdigit() else 1
            return (5, b_num, exp_sh, exp_pos)

        # Fallback
        b_num = int(exp_b) if str(exp_b).isdigit() else 1
        return (6, b_num, exp_sh, exp_pos)

    return sorted(domain_models, key=mobile_sort_key)


@dataclass
class IdentifyResolutionResult:
    status: str  # 'RESOLVED_REMOVE', 'RESOLVED_CROSS_BAY', 'RESOLVED_INTRA_BAY', 'RESOLVED_DVOID_MATCH', 'RESOLVED_EXCEPTION'
    resolved_actions: List[ActionListDomainModel]
    explanation: str
    is_exception: bool = False
    exception_reason: Optional[str] = None


def resolve_scanned_identify_action(
    identify_item: ActionListDomainModel,
    scanned_upc: Optional[str] = None,
    product_title: Optional[str] = None,
    planogram_target: Optional[Dict[str, Any]] = None,
    exception_reason: Optional[str] = None,
) -> IdentifyResolutionResult:
    """
    Simulates the mobile associate barcode scan or manual exception flagging on an IDENTIFY card:
    
    1. EXCEPTION / WRONG ITEM:
       If exception_reason is provided (e.g. 'damaged_packaging', 'unreadable_barcode', 'wrong_item'),
       marks the item as STATE_EXCEPTION for store manager / backroom review without blocking the bay.
       
    2. NOT IN PLANOGRAM (Foreign Invader / Delisted SKU):
       If scanned_upc is not in the planogram (planogram_target is None),
       the unidentified facing immediately resolves into a REMOVE FROM BAY X card (Red theme, return to cart).
       
    3. IN PLANOGRAM - DIFFERENT BAY (Cross-Bay Move):
       If planogram_target has target_bay != source_bay (e.g. found in Bay 1, belongs in Bay 3),
       generates TWO paired cards:
       - Step 1 (Bay 1): SET ASIDE FOR BAY 3 (Pick from Bay 1 shelf to rolling cart)
       - Step 2 (Bay 3): ADD TO SHELF BAY 3 (Place from cart to Bay 3 shelf)
       
    4. IN PLANOGRAM - SAME BAY (Intra-Bay Slide):
       If planogram_target has target_bay == source_bay,
       resolves into FIX POSITION IN BAY X (Slide horizontally on same bay shelf, NEVER Set Aside).
       
    5. IN PLANOGRAM - MATCHES DVOID FACING:
       If scanned item matches an out-of-stock DVoid in target position,
       fulfills the facing directly without requiring a trip to backroom inventory.
    """
    curr = identify_item.current_position
    src_bay = curr.section_info.name if curr and curr.section_info else "1"
    src_sh = curr.shelf if curr else 1
    src_pos = curr.position if curr else 1

    # Case 1: Exception / Wrong Item flagged by user
    if exception_reason:
        exc_item = ActionListDomainModel(
            id=identify_item.id,
            source_id=identify_item.source_id,
            upc=scanned_upc or identify_item.upc,
            displayed_upc=scanned_upc or identify_item.displayed_upc,
            product_title=product_title or identify_item.product_title,
            product_id=identify_item.product_id,
            planogram_thumbnail=identify_item.planogram_thumbnail,
            action_type_reasons=f"Exception: {exception_reason}",
            action_type="Exception",
            action_type_enum=ActionTypeByName.EXCEPTION.value,
            store_planogram_id=identify_item.store_planogram_id,
            current_position=identify_item.current_position,
            expected_position=None,
            action_resolved=True,
            is_new=False,
            reason=exception_reason,
            step_subtype="exception",
        )
        return IdentifyResolutionResult(
            status="RESOLVED_EXCEPTION",
            resolved_actions=[exc_item],
            explanation=f"Item flagged as exception: {exception_reason}. Staged for manager review.",
            is_exception=True,
            exception_reason=exception_reason,
        )

    # If no planogram target found -> Foreign SKU (REMOVE)
    if not planogram_target:
        remove_item = ActionListDomainModel(
            id=identify_item.id,
            source_id=identify_item.source_id,
            upc=scanned_upc or identify_item.upc,
            displayed_upc=scanned_upc or identify_item.displayed_upc,
            product_title=product_title or "Foreign / Delisted Item",
            product_id=identify_item.product_id,
            planogram_thumbnail=identify_item.planogram_thumbnail,
            action_type_reasons="Foreign item not in planogram",
            action_type="Remove",
            action_type_enum=ActionTypeByName.REMOVE.value,
            store_planogram_id=identify_item.store_planogram_id,
            current_position=identify_item.current_position,
            expected_position=None,
            action_resolved=False,
            is_new=False,
            reason="not_in_planogram",
            step_subtype="remove",
        )
        return IdentifyResolutionResult(
            status="RESOLVED_REMOVE",
            resolved_actions=[remove_item],
            explanation=f"Product {scanned_upc} does not belong to planogram. Resolved to REMOVE FROM BAY {src_bay}.",
        )

    # Extract target coordinates
    tgt_bay = str(planogram_target.get("bay", src_bay))
    tgt_sh = planogram_target.get("shelf", src_sh)
    tgt_pos = planogram_target.get("position", src_pos)
    tgt_sec_id = planogram_target.get("section_id", 0)

    exp_pos = PositionDomainModel(
        action="place_on_shelf_add_to_bay" if tgt_bay != src_bay else "fix_position_in_bay",
        section_info=SectionInfoDomainModel(id=tgt_sec_id, name=tgt_bay),
        shelf=tgt_sh,
        position=tgt_pos,
    )

    # Case 2: Cross-Bay Move (Bay S -> Bay T)
    if tgt_bay != src_bay:
        # Step 1: Pick in Source Bay (SetAside)
        pick_item = ActionListDomainModel(
            id=identify_item.id,
            source_id=identify_item.source_id,
            upc=scanned_upc or identify_item.upc,
            displayed_upc=scanned_upc or identify_item.displayed_upc,
            product_title=product_title or identify_item.product_title,
            product_id=identify_item.product_id,
            planogram_thumbnail=identify_item.planogram_thumbnail,
            action_type_reasons="Cross-bay relocation after identify scan",
            action_type="SetAside",
            action_type_enum=ActionTypeByName.SET_ASIDE.value,
            store_planogram_id=identify_item.store_planogram_id,
            current_position=identify_item.current_position,
            expected_position=exp_pos,
            action_resolved=False,
            is_new=False,
            reason="cross_bay_relocation",
            step_subtype="pick",
        )
        # Step 2: Place in Target Bay (AddItems)
        place_item = ActionListDomainModel(
            id=identify_item.id + 10000,
            source_id=identify_item.source_id,
            upc=scanned_upc or identify_item.upc,
            displayed_upc=scanned_upc or identify_item.displayed_upc,
            product_title=product_title or identify_item.product_title,
            product_id=identify_item.product_id,
            planogram_thumbnail=identify_item.planogram_thumbnail,
            action_type_reasons="Cross-bay placement after identify scan",
            action_type="AddItems",
            action_type_enum=ActionTypeByName.PLACE_ON_SHELF_ADD_TO_BAY.value,
            store_planogram_id=identify_item.store_planogram_id,
            current_position=identify_item.current_position,
            expected_position=exp_pos,
            action_resolved=False,
            is_new=False,
            reason="cross_bay_placement",
            step_subtype="place",
        )
        return IdentifyResolutionResult(
            status="RESOLVED_CROSS_BAY",
            resolved_actions=[pick_item, place_item],
            explanation=f"Product {scanned_upc} belongs in Bay {tgt_bay}. Generated SET ASIDE FOR BAY {tgt_bay} and ADD TO SHELF BAY {tgt_bay}.",
        )

    # Case 3: Intra-Bay Slide (Bay S -> Bay S)
    is_dvoid_match = planogram_target.get("is_dvoid_match", False)
    if is_dvoid_match:
        fix_item = ActionListDomainModel(
            id=identify_item.id,
            source_id=identify_item.source_id,
            upc=scanned_upc or identify_item.upc,
            displayed_upc=scanned_upc or identify_item.displayed_upc,
            product_title=product_title or identify_item.product_title,
            product_id=identify_item.product_id,
            planogram_thumbnail=identify_item.planogram_thumbnail,
            action_type_reasons="Fulfills missing DVoid facing in same bay",
            action_type="FixInBay",
            action_type_enum=ActionTypeByName.FIX_POSITION_IN_BAY.value,
            store_planogram_id=identify_item.store_planogram_id,
            current_position=identify_item.current_position,
            expected_position=exp_pos,
            action_resolved=False,
            is_new=False,
            reason="dvoid_fulfilled_by_identified_item",
            step_subtype="shift",
        )
        return IdentifyResolutionResult(
            status="RESOLVED_DVOID_MATCH",
            resolved_actions=[fix_item],
            explanation=f"Product {scanned_upc} fulfilled missing DVoid in Bay {src_bay}, Shelf {tgt_sh}, Pos {tgt_pos}.",
        )

    fix_item = ActionListDomainModel(
        id=identify_item.id,
        source_id=identify_item.source_id,
        upc=scanned_upc or identify_item.upc,
        displayed_upc=scanned_upc or identify_item.displayed_upc,
        product_title=product_title or identify_item.product_title,
        product_id=identify_item.product_id,
        planogram_thumbnail=identify_item.planogram_thumbnail,
        action_type_reasons="Intra-bay alignment after identify scan",
        action_type="FixInBay",
        action_type_enum=ActionTypeByName.FIX_POSITION_IN_BAY.value,
        store_planogram_id=identify_item.store_planogram_id,
        current_position=identify_item.current_position,
        expected_position=exp_pos,
        action_resolved=False,
        is_new=False,
        reason="intra_bay_slide",
        step_subtype="shift",
    )
    return IdentifyResolutionResult(
        status="RESOLVED_INTRA_BAY",
        resolved_actions=[fix_item],
        explanation=f"Product {scanned_upc} belongs in Bay {src_bay}. Resolved to FIX POSITION IN BAY {src_bay}.",
    )
