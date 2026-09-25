"""Shelf-Reset Sequencing Engine.

Decomposes slot/product mismatches into a dependency-safe, minimum-effort
action sequence (Move / Swap / Slide / Hold / Place / Restock / Pull) for
store associates.
"""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Set, Tuple


class ActionType(str, Enum):
    HOLD = "hold"
    MOVE = "move"
    FIX_IN_BAY = "fix_in_bay"
    SET_ASIDE = "set_aside"
    PLACE = "place"
    PLACE_FROM_CART = "place_from_cart"
    SWAP = "swap"
    SLIDE = "slide"
    RESTOCK = "restock"
    PULL = "pull"


@dataclass
class Coordinates:
    x: float
    y: float


@dataclass
class Slot:
    id: str
    bay: str
    current: Optional[str]
    target: Optional[str]
    coordinates: Optional[Coordinates] = None
    facing_qty: int = 1
    shelf: Optional[int] = None
    position: Optional[str] = None
    upc: Optional[str] = None
    product_title: Optional[str] = None
    brand: Optional[str] = None
    image: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Slot":
        coords = None
        raw_coords = data.get("coordinates")
        if isinstance(raw_coords, dict):
            coords = Coordinates(
                x=float(raw_coords.get("x", 0)),
                y=float(raw_coords.get("y", 0)),
            )
        elif isinstance(raw_coords, (list, tuple)) and len(raw_coords) >= 2:
            coords = Coordinates(x=float(raw_coords[0]), y=float(raw_coords[1]))

        return cls(
            id=str(data.get("id", "")).strip(),
            bay=str(data.get("bay", "")).strip(),
            current=data.get("current") if data.get("current") is not None else None,
            target=data.get("target") if data.get("target") is not None else None,
            coordinates=coords,
            facing_qty=int(data.get("facingQty", data.get("facing_qty", 1))),
            shelf=data.get("shelf"),
            position=str(data.get("position")) if data.get("position") is not None else None,
            upc=data.get("upc"),
            product_title=data.get("productTitle") or data.get("product_title"),
            brand=data.get("brand"),
            image=data.get("image"),
        )

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "id": self.id,
            "bay": self.bay,
            "current": self.current,
            "target": self.target,
            "facingQty": self.facing_qty,
        }
        if self.coordinates:
            res["coordinates"] = {"x": self.coordinates.x, "y": self.coordinates.y}
        if self.shelf is not None:
            res["shelf"] = self.shelf
        if self.position is not None:
            res["position"] = self.position
        if self.upc:
            res["upc"] = self.upc
        if self.product_title:
            res["productTitle"] = self.product_title
        if self.brand:
            res["brand"] = self.brand
        if self.image:
            res["image"] = self.image
        return res


@dataclass
class SubMove:
    from_slot: str
    to_slot: str
    item: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fromSlot": self.from_slot,
            "toSlot": self.to_slot,
            "item": self.item,
        }


@dataclass
class Step:
    type: ActionType
    description: str
    slot_id: str
    item: Optional[str] = None
    to_slot_id: Optional[str] = None
    item_b: Optional[str] = None
    sub_moves: List[SubMove] = field(default_factory=list)
    bay: str = ""
    rationale: str = ""
    product_title: Optional[str] = None
    upc: Optional[str] = None
    brand: Optional[str] = None
    image: Optional[str] = None
    from_bay: str = ""
    from_shelf: str = ""
    from_position: str = ""
    to_bay: str = ""
    to_shelf: str = ""
    to_position: str = ""
    clearance_info: Dict[str, Any] = field(default_factory=dict)
    facing_qty: int = 1
    from_cart: bool = False

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "type": self.type.value,
            "description": self.description,
            "slotId": self.slot_id,
            "bay": self.bay,
            "rationale": self.rationale,
            "from_bay": self.from_bay or self.bay,
            "from_shelf": self.from_shelf,
            "from_position": self.from_position,
            "fromLocation": {
                "bay": self.from_bay or self.bay,
                "shelf": self.from_shelf,
                "position": self.from_position,
            },
        }
        if self.item is not None:
            res["item"] = self.item
        if self.to_slot_id is not None:
            res["toSlotId"] = self.to_slot_id
            res["to_bay"] = self.to_bay or self.bay
            res["to_shelf"] = self.to_shelf
            res["to_position"] = self.to_position
            res["toLocation"] = {
                "bay": self.to_bay or self.bay,
                "shelf": self.to_shelf,
                "position": self.to_position,
            }
        if self.item_b is not None:
            res["itemB"] = self.item_b
        if self.sub_moves:
            res["subMoves"] = [sm.to_dict() for sm in self.sub_moves]
        if self.product_title:
            res["productTitle"] = self.product_title
        if self.upc:
            res["upc"] = self.upc
        if self.brand:
            res["brand"] = self.brand
        if self.image:
            res["image"] = self.image
        if self.facing_qty > 1:
            res["facingQty"] = self.facing_qty
            res["facing_qty"] = self.facing_qty
        if self.from_cart:
            res["fromCart"] = self.from_cart
            res["from_cart"] = self.from_cart
        if self.clearance_info:
            res["clearanceInfo"] = self.clearance_info
            res["clearance_info"] = self.clearance_info
        return res


def _parse_slot_num(slot_id: str) -> Optional[int]:
    """Extract numeric suffix from slot ID e.g. 'A10' -> 10, 'B3' -> 3."""
    match = re.search(r"(\d+)$", slot_id)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def _bay_num(val: Any) -> int:
    """Extract integer bay number e.g. 'Bay 2', '2', 'B2' -> 2."""
    if not val:
        return 1
    m = re.search(r"\d+", str(val))
    return int(m.group(0)) if m else 1


def _extract_int_pos(val: Any) -> int:
    """Extract integer position e.g. 'P3', '3' -> 3."""
    if not val:
        return 1
    m = re.search(r"\d+", str(val))
    return int(m.group(0)) if m else 1


def _extract_int_shelf(val: Any) -> int:
    """Extract integer shelf number e.g. 'S4', '4' -> 4."""
    if not val:
        return 1
    m = re.search(r"\d+", str(val))
    return int(m.group(0)) if m else 1


def _ergonomic_sort_key(
    st: Step,
    vertical_direction: str = "top_to_bottom",
    horizontal_direction: str = "snake",
) -> Tuple[int, int, int, int, int]:
    """Sort key enforcing the strict 5-phase store reset sequence:
    1. Phase 1: All PULL (Remove) actions across ALL bays first.
    2. Within each bay:
       a. SET_ASIDE / HOLD items destined for future bays.
       b. FIX_IN_BAY, SWAP, SLIDE, intra-bay MOVE (rearrange within bay).
       c. PLACE_FROM_CART (items coming from future bays or transit cart).
       d. RESTOCK / PLACE missing items from backroom.
    3. Ergonomic vertical shelf sweep (top-to-bottom or bottom-to-top).
    4. Lateral horizontal sweep (snake / boustrophedon or left-to-right).
    """
    # Macro Phase:
    # 0 = All PULL (Remove) actions across ALL bays first
    # 1 = Bay-by-bay execution of set-aside, fix, place-from-cart, restock
    if st.type == ActionType.PULL:
        macro_phase = 0
        bay_str = st.bay or st.from_bay or "1"
        bay_idx = _bay_num(bay_str)
        phase_in_bay = 0
    else:
        macro_phase = 1
        # For items placed from cart, associate is positioned at to_bay
        if st.type == ActionType.PLACE_FROM_CART:
            bay_str = st.to_bay or st.bay or "1"
        else:
            bay_str = st.from_bay or st.bay or "1"
        bay_idx = _bay_num(bay_str)

        if st.type in (ActionType.SET_ASIDE, ActionType.HOLD):
            # Step 1: Set aside items destined for future bays
            phase_in_bay = 1
        elif st.type in (ActionType.FIX_IN_BAY, ActionType.SWAP, ActionType.SLIDE):
            # Step 2: Fix within bay
            phase_in_bay = 2
        elif st.type == ActionType.MOVE and (st.from_bay == st.to_bay or not st.to_bay):
            # Intra-bay move
            phase_in_bay = 2
        elif st.type == ActionType.PLACE_FROM_CART:
            # Step 3: In same bay, pick/place items coming from future bay / cart
            phase_in_bay = 3
        elif st.type in (ActionType.PLACE, ActionType.RESTOCK):
            # Step 4: Restock missing items from backroom
            phase_in_bay = 4
        else:
            phase_in_bay = 5

    # Shelf tier (e.g. Shelf 7 down to Shelf 1)
    shelf_raw = st.from_shelf or st.to_shelf or "1"
    shelf_num = _extract_int_shelf(shelf_raw)
    shelf_key = -shelf_num if vertical_direction == "top_to_bottom" else shelf_num

    # Position sweep (horizontal)
    pos_raw = st.from_position or st.to_position or "1"
    pos_num = _extract_int_pos(pos_raw)

    if horizontal_direction == "snake":
        # Alternating Boustrophedon sweep: even shelves Left-to-Right, odd shelves Right-to-Left
        pos_key = pos_num if (shelf_num % 2 == 0) else -pos_num
    elif horizontal_direction == "right_to_left":
        pos_key = -pos_num
    else:
        pos_key = pos_num

    return (macro_phase, bay_idx, phase_in_bay, shelf_key, pos_key)


def _bundle_multi_facings(steps: List[Step]) -> List[Step]:
    """Combine contiguous moves of the same SKU on the same shelf into single multi-facing steps."""
    if not steps:
        return []

    bundled: List[Step] = []
    i = 0
    n = len(steps)

    while i < n:
        curr = steps[i]
        # Only bundle FIX_IN_BAY or MOVE actions that have explicit shelf and position
        if (curr.type not in (ActionType.FIX_IN_BAY, ActionType.MOVE) 
                or not curr.from_shelf or not curr.to_shelf 
                or not curr.from_position or not curr.to_position):
            bundled.append(curr)
            i += 1
            continue

        group = [curr]
        j = i + 1
        curr_prod = curr.upc or curr.item or curr.product_title or ""

        from_p_prev = _extract_int_pos(curr.from_position)
        to_p_prev = _extract_int_pos(curr.to_position)

        while j < n:
            nxt = steps[j]
            if (
                nxt.type == curr.type
                and nxt.bay == curr.bay
                and nxt.from_shelf == curr.from_shelf
                and nxt.to_shelf == curr.to_shelf
            ):
                nxt_prod = nxt.upc or nxt.item or nxt.product_title or ""
                nxt_from_p = _extract_int_pos(nxt.from_position)
                nxt_to_p = _extract_int_pos(nxt.to_position)

                is_same_product = (nxt_prod == curr_prod) or (curr.item and curr.item == nxt.item)
                is_contiguous = (
                    abs(nxt_from_p - from_p_prev) == 1
                    and abs(nxt_to_p - to_p_prev) == 1
                    and (nxt_to_p - nxt_from_p) == (to_p_prev - from_p_prev)
                )

                if is_same_product and is_contiguous:
                    group.append(nxt)
                    from_p_prev = nxt_from_p
                    to_p_prev = nxt_to_p
                    j += 1
                    continue
            break

        if len(group) > 1:
            sub_moves = []
            for s in group:
                sub_moves.append(SubMove(
                    from_slot=s.slot_id,
                    to_slot=s.to_slot_id or s.slot_id,
                    item=s.item or "",
                ))
            first = group[0]
            last = group[-1]
            k = len(group)
            verb = "fix_in_bay" if first.type == ActionType.FIX_IN_BAY else "move"
            desc = f"{verb} S{first.from_shelf}:P{first.from_position}..P{last.from_position}→P{first.to_position}..P{last.to_position} ({first.item or first.product_title} • {k} facings)"
            rationale = (
                f"Multi-facing bundle: Shift all {k} contiguous facings of '{first.item or first.product_title}' "
                f"simultaneously from Shelf {first.from_shelf} Pos {first.from_position}..{last.from_position} "
                f"to Pos {first.to_position}..{last.to_position} in a single motion, saving {k - 1} separate physical touches."
            )
            bundled_step = Step(
                type=first.type,
                description=desc,
                slot_id=first.slot_id,
                to_slot_id=last.to_slot_id,
                item=first.item,
                sub_moves=sub_moves,
                bay=first.bay,
                rationale=rationale,
                product_title=first.product_title,
                upc=first.upc,
                brand=first.brand,
                image=first.image,
                from_bay=first.from_bay,
                from_shelf=first.from_shelf,
                from_position=f"{first.from_position}..{last.from_position}",
                to_bay=first.to_bay,
                to_shelf=first.to_shelf,
                to_position=f"{first.to_position}..{last.to_position}",
                facing_qty=k,
            )
            bundled.append(bundled_step)
            i = j
        else:
            bundled.append(curr)
            i += 1

    return bundled


def _extract_bay_shelf_pos(slot: Optional[Slot], slot_id: str) -> Tuple[str, str, str]:
    """Extract (bay, shelf, position) from slot object or slot_id string."""
    bay = ""
    shelf = ""
    pos = ""
    if slot:
        bay = str(slot.bay or "")
        shelf = str(slot.shelf) if slot.shelf is not None else ""
        pos = str(slot.position or "")

    if not shelf or not pos:
        m = re.search(r"Bay([^_]+)_S([^_]+)_P(.+)", slot_id, re.IGNORECASE)
        if m:
            bay = bay or m.group(1)
            shelf = shelf or m.group(2)
            pos = pos or m.group(3)

    if not shelf or not pos:
        m_simple = re.search(r"^([A-Za-z]+)(\d+)$", slot_id)
        if m_simple:
            bay = bay or m_simple.group(1)
            num_val = int(m_simple.group(2))
            shelf = shelf or ("2" if num_val <= 5 else "1")
            pos = pos or m_simple.group(2)

    return (bay, shelf, pos)


def _is_contiguous_chain(path: List[Slot]) -> bool:
    """Return True if path has >= 4 slots, in same bay, with contiguous numeric IDs."""
    if len(path) < 4:
        return False
    bay = path[0].bay
    if any(s.bay != bay for s in path):
        return False

    nums = [_parse_slot_num(s.id) for s in path]
    if any(n is None for n in nums):
        return False

    # Check forward contiguous (1, 2, 3, 4) or backward contiguous (4, 3, 2, 1)
    diffs = [nums[i + 1] - nums[i] for i in range(len(nums) - 1)]  # type: ignore
    return all(d == 1 for d in diffs) or all(d == -1 for d in diffs)


def sequence_shelf_reset(
    slots: List[Slot],
    currently_held_item: Optional[str] = None,
    pull_first: Optional[bool] = None,
    sweep_vertical: str = "top_to_bottom",
    sweep_horizontal: str = "snake",
    bundle_facings: bool = True,
) -> List[Step]:
    """Execute the full graph decomposition algorithm on a list of slots."""
    if pull_first is None:
        # Automatically prioritize pulls and cross-bay set-asides before fix-in-bay for real tasks
        pull_first = any(s.id.startswith("Bay") for s in slots)

    slot_map: Dict[str, Slot] = {s.id: s for s in slots}

    # 3.1 Build graph
    # Map target SKU -> slot id (skip null targets and already-satisfied slots)
    target_to_slots: Dict[str, List[str]] = {}
    for s in slots:
        if s.target is not None and s.current != s.target:
            target_to_slots.setdefault(s.target, []).append(s.id)

    # Edge: for each slot where current !== target and current is not null:
    # look up targetToSlot(current). If found and != slot.id, edge slot.id -> destSlotId.
    # Exclude already-correct slots (current === target) completely.
    edges: Dict[str, str] = {}
    reverse_edges: Dict[str, List[str]] = {s.id: [] for s in slots}
    active_mismatched: Set[str] = set()

    assigned_dests: Set[str] = set()
    for s in slots:
        # Protect already-correct slots from being disturbed
        if s.current == s.target:
            continue

        active_mismatched.add(s.id)
        if s.current is not None:
            dest_candidates = target_to_slots.get(s.current, [])
            # Filter candidates that are not self and not yet assigned
            valid_dests = [d for d in dest_candidates if d != s.id and d not in assigned_dests]
            if valid_dests:
                # Prefer destination in same bay or first available
                chosen_dest = valid_dests[0]
                edges[s.id] = chosen_dest
                assigned_dests.add(chosen_dest)
                reverse_edges[chosen_dest].append(s.id)

    # 3.2 Decompose into components
    visited: Set[str] = set()
    components: List[Tuple[int, Any, str]] = []  # (priority_tier, component_data, sort_key)
    # Tiers:
    # 1: Hold-cycle
    # 2: Chains/Slides
    # 3: Swaps
    # 4: Restocks
    # 5: Pulls

    # Identify Chain Heads: outgoing edge and in-degree 0
    chain_heads = [
        s_id for s_id in edges
        if len(reverse_edges.get(s_id, [])) == 0
    ]
    # Sort chain heads by bay then slot id for deterministic traversal
    chain_heads.sort(key=lambda sid: (slot_map[sid].bay, _parse_slot_num(sid) or 0, sid))

    chains: List[List[Slot]] = []
    for head_id in chain_heads:
        if head_id in visited:
            continue
        path = [slot_map[head_id]]
        visited.add(head_id)
        curr = head_id
        while curr in edges:
            nxt = edges[curr]
            if nxt in visited:
                break
            visited.add(nxt)
            path.append(slot_map[nxt])
            curr = nxt
        chains.append(path)

    # Now identify remaining unvisited nodes with outgoing edges -> Cycles
    remaining_with_edges = [s_id for s_id in edges if s_id not in visited]
    # Sort for deterministic processing
    remaining_with_edges.sort(key=lambda sid: (slot_map[sid].bay, _parse_slot_num(sid) or 0, sid))

    for start_id in remaining_with_edges:
        if start_id in visited:
            continue
        cycle_path: List[Slot] = []
        curr = start_id
        while curr not in visited and curr in edges:
            visited.add(curr)
            cycle_path.append(slot_map[curr])
            curr = edges[curr]

        if not cycle_path:
            continue

        if len(cycle_path) == 2:
            # Classify as Swap
            sort_key = f"{cycle_path[0].bay}_{cycle_path[0].id}"
            components.append((3, ("swap", cycle_path), sort_key))
        else:
            # Hold-cycle (length >= 3)
            # Cross-bay preference: if cycle spans multiple bays, prefer holding cross-bay item
            has_cross_bay = any(
                cycle_path[i].bay != cycle_path[(i + 1) % len(cycle_path)].bay
                for i in range(len(cycle_path))
            )
            if has_cross_bay:
                # Find the index of the first cross-bay transition
                for idx in range(len(cycle_path)):
                    if cycle_path[idx].bay != cycle_path[(idx + 1) % len(cycle_path)].bay:
                        # Rotate so cross-bay item is at index 0
                        cycle_path = cycle_path[idx:] + cycle_path[:idx]
                        break

            sort_key = f"{cycle_path[0].bay}_{cycle_path[0].id}"
            components.append((1, ("hold_cycle", cycle_path), sort_key))

    # Add Chains/Slides
    for path in chains:
        sort_key = f"{path[0].bay}_{path[0].id}"
        components.append((2, ("chain", path), sort_key))

    # Restocks: any slot where target is non-null, current !== target, and not destination of any edge
    restocks: List[Slot] = [
        s for s in slots
        if s.target is not None
        and s.current != s.target
        and len(reverse_edges.get(s.id, [])) == 0
    ]
    restocks.sort(key=lambda s: (s.bay, _parse_slot_num(s.id) or 0, s.id))
    for r in restocks:
        sort_key = f"{r.bay}_{r.id}"
        components.append((4, ("restock", r), sort_key))

    # Pulls: any slot where current is non-null, current !== target, and has no outgoing edge
    pulls: List[Slot] = [
        s for s in slots
        if s.current is not None
        and s.current != s.target
        and s.id not in edges
    ]
    pulls.sort(key=lambda s: (s.bay, _parse_slot_num(s.id) or 0, s.id))
    for p in pulls:
        sort_key = f"{p.bay}_{p.id}"
        components.append((5, ("pull", p), sort_key))

    # 3.4 Order the master queue:
    # Priority tiers: 1 (Hold-cycles) -> 2 (Chains/Slides) -> 3 (Swaps) -> 4 (Restocks) -> 5 (Pulls)
    components.sort(key=lambda c: (c[0], c[2]))

    # Flatten components into ordered atomic steps
    final_steps: List[Step] = []
    pulled_slot_ids: Set[str] = set()

    for tier, (kind, data), _ in components:
        if kind == "hold_cycle":
            path = data
            k = len(path)
            held_node = path[0]
            held_item_name = held_node.current or ""

            # Check if this item is already held (idempotent resume)
            already_held = (currently_held_item is not None and currently_held_item == held_item_name)
            if not already_held:
                final_steps.append(Step(
                    type=ActionType.HOLD,
                    description=f"hold {held_node.id} ({held_item_name})",
                    slot_id=held_node.id,
                    item=held_item_name,
                    bay=held_node.bay,
                    rationale=(
                        f"Vacate {held_node.id} by holding '{held_item_name}' to break the {k}-node circular "
                        f"dependency cycle, creating a vacant buffer slot with zero cart footprint."
                    ),
                ))

            # 2. For i from k-1 down to 1: move(path[i] -> path[(i+1)%k])
            for i in range(k - 1, 0, -1):
                from_node = path[i]
                to_node = path[(i + 1) % k]
                item_name = from_node.current or ""
                is_same_bay = (from_node.bay == to_node.bay and from_node.id.startswith("Bay"))
                if is_same_bay:
                    step_type = ActionType.FIX_IN_BAY
                    verb = "fix_in_bay"
                    rationale = (
                        f"Direct same-bay shift within Bay {from_node.bay}. Destination {to_node.id} is now empty, "
                        f"allowing direct shelf repositioning without intermediate cart staging."
                    )
                elif from_node.id.startswith("Bay"):
                    step_type = ActionType.SET_ASIDE
                    verb = "set_aside"
                    rationale = (
                        f"Set aside '{item_name}' into transit cart for future Bay {to_node.bay}, clearing slot {from_node.id}."
                    )
                    final_steps.append(Step(
                        type=step_type,
                        description=f"{verb} {from_node.id}→{to_node.id} ({item_name})",
                        slot_id=from_node.id,
                        to_slot_id=to_node.id,
                        item=item_name,
                        bay=from_node.bay,
                        to_bay=to_node.bay,
                        rationale=rationale,
                    ))
                    is_from_future = _bay_num(from_node.bay) > _bay_num(to_node.bay)
                    pfc_rat = (
                        f"Take '{item_name}' coming from future Bay {from_node.bay} (or transit cart) and place into "
                        f"final destination {to_node.id} in Bay {to_node.bay}."
                        if is_from_future else
                        f"Take '{item_name}' staged from Bay {from_node.bay} transit cart and place into "
                        f"final destination {to_node.id} in Bay {to_node.bay}, completing cross-bay restock."
                    )
                    final_steps.append(Step(
                        type=ActionType.PLACE_FROM_CART,
                        description=f"place_from_cart →{to_node.id} ({item_name})",
                        slot_id=to_node.id,
                        to_slot_id=to_node.id,
                        item=item_name,
                        bay=to_node.bay,
                        from_bay=from_node.bay,
                        to_bay=to_node.bay,
                        from_position="Transit Cart",
                        from_shelf="Cart",
                        from_cart=True,
                        rationale=pfc_rat,
                    ))
                    continue
                else:
                    step_type = ActionType.MOVE
                    verb = "move"
                    rationale = (
                        f"Move '{item_name}' into now-vacant destination {to_node.id}, "
                        f"safely clearing slot {from_node.id} for the preceding item."
                    )
                final_steps.append(Step(
                    type=step_type,
                    description=f"{verb} {from_node.id}→{to_node.id} ({item_name})",
                    slot_id=from_node.id,
                    to_slot_id=to_node.id,
                    item=item_name,
                    bay=from_node.bay,
                    rationale=rationale,
                ))

            # 3. place(heldItem -> path[1])
            dest_node = path[1]
            final_steps.append(Step(
                type=ActionType.PLACE,
                description=f"place →{dest_node.id} ({held_item_name})",
                slot_id=dest_node.id,
                to_slot_id=dest_node.id,
                item=held_item_name,
                bay=dest_node.bay,
                rationale=(
                    f"Place held item '{held_item_name}' into destination {dest_node.id} to close out "
                    f"the cycle and leave associate hands completely free."
                ),
            ))

        elif kind == "chain":
            path = data
            # If the terminal node of the chain holds a decommissioned item (not part of edges),
            # pull it first before walking backward so destination slot is guaranteed vacant.
            term_node = path[-1]
            if (term_node.current is not None 
                    and term_node.id not in edges 
                    and term_node.current != term_node.target 
                    and term_node.id not in pulled_slot_ids):
                pulled_slot_ids.add(term_node.id)
                final_steps.append(Step(
                    type=ActionType.PULL,
                    description=f"pull {term_node.id} ({term_node.current})",
                    slot_id=term_node.id,
                    item=term_node.current,
                    bay=term_node.bay,
                    rationale=(
                        f"Pull decommissioned item '{term_node.current}' from {term_node.id} directly to "
                        f"return cart before chain shifts, ensuring destination slot is vacant."
                    ),
                ))

            if _is_contiguous_chain(path):
                # Collapse into Slide
                sub_moves: List[SubMove] = []
                for i in range(len(path) - 1, 0, -1):
                    from_node = path[i - 1]
                    to_node = path[i]
                    sub_moves.append(SubMove(
                        from_slot=from_node.id,
                        to_slot=to_node.id,
                        item=from_node.current or "",
                    ))
                sub_str = ", ".join(f"{sm.from_slot}→{sm.to_slot}" for sm in sub_moves)
                final_steps.append(Step(
                    type=ActionType.SLIDE,
                    description=f"slide {sub_str} ({len(sub_moves)} items)",
                    slot_id=path[0].id,
                    to_slot_id=path[-1].id,
                    sub_moves=sub_moves,
                    bay=path[0].bay,
                    rationale=(
                        f"Execute a contiguous physical slide across adjacent slots {path[0].id}..{path[-1].id} "
                        f"in a single motion, saving individual pick/place touches."
                    ),
                ))
            else:
                # Walk backward from empty/terminal end
                for i in range(len(path) - 1, 0, -1):
                    from_node = path[i - 1]
                    to_node = path[i]
                    item_name = from_node.current or ""
                    is_same_bay = (from_node.bay == to_node.bay and from_node.id.startswith("Bay"))
                    if is_same_bay:
                        step_type = ActionType.FIX_IN_BAY
                        verb = "fix_in_bay"
                        rationale = (
                            f"Direct same-bay shelf shift within Bay {from_node.bay}. Destination {to_node.id} is verified empty, "
                            f"allowing direct repositioning on the shelf and bypassing the retailer API's redundant 'Set Aside to Cart' instruction."
                        )
                    elif from_node.id.startswith("Bay"):
                        step_type = ActionType.SET_ASIDE
                        verb = "set_aside"
                        rationale = (
                            f"Product belongs to future Bay {to_node.bay}. Staged/set-aside into transit cart now before Bay {from_node.bay} "
                            f"fix-in-bay shifts, vacating slot {from_node.id} so same-bay products have maximum unobstructed room."
                        )
                        final_steps.append(Step(
                            type=step_type,
                            description=f"{verb} {from_node.id}→{to_node.id} ({item_name})",
                            slot_id=from_node.id,
                            to_slot_id=to_node.id,
                            item=item_name,
                            bay=from_node.bay,
                            to_bay=to_node.bay,
                            rationale=rationale,
                        ))
                        is_from_future = _bay_num(from_node.bay) > _bay_num(to_node.bay)
                        pfc_rat = (
                            f"Take '{item_name}' coming from future Bay {from_node.bay} (or transit cart) and place into "
                            f"verified-empty destination {to_node.id} in Bay {to_node.bay}."
                            if is_from_future else
                            f"Take '{item_name}' staged from Bay {from_node.bay} transit cart and place into "
                            f"verified-empty destination {to_node.id} in Bay {to_node.bay}, completing cross-bay restock."
                        )
                        final_steps.append(Step(
                            type=ActionType.PLACE_FROM_CART,
                            description=f"place_from_cart →{to_node.id} ({item_name})",
                            slot_id=to_node.id,
                            to_slot_id=to_node.id,
                            item=item_name,
                            bay=to_node.bay,
                            from_bay=from_node.bay,
                            to_bay=to_node.bay,
                            from_position="Transit Cart",
                            from_shelf="Cart",
                            from_cart=True,
                            rationale=pfc_rat,
                        ))
                        continue
                    else:
                        step_type = ActionType.MOVE
                        verb = "move"
                        rationale = (
                            f"Move '{item_name}' from {from_node.id} to verified-empty slot {to_node.id} "
                            f"(backward chain walk guarantees destination is never occupied)."
                        )
                    final_steps.append(Step(
                        type=step_type,
                        description=f"{verb} {from_node.id}→{to_node.id} ({item_name})",
                        slot_id=from_node.id,
                        to_slot_id=to_node.id,
                        item=item_name,
                        bay=from_node.bay,
                        rationale=rationale,
                    ))

        elif kind == "swap":
            path = data
            s1, s2 = path[0], path[1]
            desc = f"swap {s1.id}↔{s2.id} ({s1.current} / {s2.current})"
            final_steps.append(Step(
                type=ActionType.SWAP,
                description=desc,
                slot_id=s1.id,
                to_slot_id=s2.id,
                item=s1.current,
                item_b=s2.current,
                bay=s1.bay,
                rationale=(
                    f"Simultaneously swap mutually displaced products between {s1.id} and {s2.id} "
                    f"in one dual-hand exchange without placing either into cart."
                ),
            ))

        elif kind == "restock":
            r_slot = data
            final_steps.append(Step(
                type=ActionType.RESTOCK,
                description=f"restock {r_slot.id} ({r_slot.target})",
                slot_id=r_slot.id,
                item=r_slot.target,
                bay=r_slot.bay,
                rationale=(
                    f"Replenish vacant shelf position {r_slot.id} with incoming stock item '{r_slot.target}', "
                    f"executed after shelf shifts are stabilized."
                ),
            ))

        elif kind == "pull":
            p_slot = data
            if p_slot.id in pulled_slot_ids:
                continue
            pulled_slot_ids.add(p_slot.id)
            final_steps.append(Step(
                type=ActionType.PULL,
                description=f"pull {p_slot.id} ({p_slot.current})",
                slot_id=p_slot.id,
                item=p_slot.current,
                bay=p_slot.bay,
                rationale=(
                    f"Remove decommissioned/expired item '{p_slot.current}' from {p_slot.id} directly to "
                    f"return cart with no remaining destination in this planogram."
                ),
            ))

    # Enrich steps with product metadata from slot_map and location breakdown
    for step in final_steps:
        if step.type == ActionType.PLACE_FROM_CART:
            step.from_shelf = step.from_shelf or "Cart"
            step.from_position = step.from_position or "Transit Cart"
            if step.to_slot_id:
                to_obj = slot_map.get(step.to_slot_id)
                to_b, to_s, to_p = _extract_bay_shelf_pos(to_obj, step.to_slot_id)
                step.to_bay = to_b or step.bay
                step.to_shelf = to_s
                step.to_position = to_p
                if to_obj:
                    if not step.product_title and to_obj.product_title:
                        step.product_title = to_obj.product_title
                    if not step.upc and to_obj.upc:
                        step.upc = to_obj.upc
                    if not step.brand and to_obj.brand:
                        step.brand = to_obj.brand
                    if not step.image and to_obj.image:
                        step.image = to_obj.image
            continue

        s_obj = slot_map.get(step.slot_id)
        from_b, from_s, from_p = _extract_bay_shelf_pos(s_obj, step.slot_id)
        step.from_bay = from_b or step.bay
        step.from_shelf = from_s
        step.from_position = from_p

        if s_obj:
            if not step.product_title and s_obj.product_title:
                step.product_title = s_obj.product_title
            if not step.upc and s_obj.upc:
                step.upc = s_obj.upc
            if not step.brand and s_obj.brand:
                step.brand = s_obj.brand
            if not step.image and s_obj.image:
                step.image = s_obj.image
        if step.to_slot_id:
            to_obj = slot_map.get(step.to_slot_id)
            to_b, to_s, to_p = _extract_bay_shelf_pos(to_obj, step.to_slot_id)
            step.to_bay = to_b or step.bay
            step.to_shelf = to_s
            step.to_position = to_p
            if to_obj:
                if not step.product_title and to_obj.product_title:
                    step.product_title = to_obj.product_title
                if not step.upc and to_obj.upc:
                    step.upc = to_obj.upc
                if not step.brand and to_obj.brand:
                    step.brand = to_obj.brand
                if not step.image and to_obj.image:
                    step.image = to_obj.image

    # Ergonomic Phase & Directional Sorting:
    if pull_first:
        final_steps.sort(key=lambda s: _ergonomic_sort_key(s, vertical_direction=sweep_vertical, horizontal_direction=sweep_horizontal))

    # Multi-Facing Bundling:
    if pull_first and bundle_facings:
        final_steps = _bundle_multi_facings(final_steps)

    # Topological Vacancy Enforcement:
    # Ensure that any step vacating slot X executes BEFORE any step placing into slot X.
    for i in range(len(final_steps)):
        if final_steps[i].type in (ActionType.FIX_IN_BAY, ActionType.MOVE, ActionType.SLIDE):
            dest = final_steps[i].to_slot_id
            if dest:
                for j in range(i + 1, len(final_steps)):
                    if final_steps[j].type != final_steps[i].type or (final_steps[j].bay and final_steps[i].bay and final_steps[j].bay != final_steps[i].bay):
                        break
                    if final_steps[j].slot_id == dest:
                        v_step = final_steps.pop(j)
                        final_steps.insert(i, v_step)
                        break

    # Symbolic Clearance and Occupancy Tracker
    # Validates and records slot vacancy and removal provenance for every action
    current_occupancy: Dict[str, Optional[str]] = {s.id: s.current for s in slots}
    initial_occupancy: Dict[str, Optional[str]] = {s.id: s.current for s in slots}
    clearance_events: Dict[str, Dict[str, Any]] = {}

    for idx, step in enumerate(final_steps, start=1):
        dest_id = step.to_slot_id or (step.slot_id if step.type in (ActionType.PLACE, ActionType.RESTOCK, ActionType.PLACE_FROM_CART) else None)

        if dest_id and step.type != ActionType.SET_ASIDE:
            dest_obj = slot_map.get(dest_id)
            d_bay, d_shelf, d_pos = _extract_bay_shelf_pos(dest_obj, dest_id)
            loc_str = f"Bay {d_bay or '1'} • Shelf {d_shelf or '1'} • Pos {d_pos or '1'}"
            init_item = initial_occupancy.get(dest_id)
            was_init_occupied = (init_item is not None)
            curr_item = current_occupancy.get(dest_id)
            is_vacant_now = (curr_item is None)
            ev = clearance_events.get(dest_id)

            if was_init_occupied:
                if ev:
                    cleared_before = True
                    explanation = (
                        f"Target position ({loc_str}) was initially occupied by '{init_item}'. "
                        f"In Step {ev['stepNumber']} ({ev['actionType'].upper()}), that product was {ev['howCleared']}. "
                        f"The position is verified 100% VACANT before placing '{step.item or step.product_title or 'product'}'."
                    )
                else:
                    cleared_before = False
                    explanation = (
                        f"Target position ({loc_str}) was occupied by '{init_item}' and has not been cleared yet."
                    )
            else:
                cleared_before = True
                explanation = (
                    f"Target position ({loc_str}) was naturally VACANT at the start of reset. "
                    f"No product needed to be removed before placement."
                )

            step.clearance_info = {
                "destSlotId": dest_id,
                "destLocation": loc_str,
                "wasInitiallyOccupied": was_init_occupied,
                "initialOccupant": init_item or "Naturally Vacant (Empty Slot)",
                "clearedBeforePlacement": cleared_before,
                "clearedInStep": ev["stepNumber"] if ev else None,
                "clearedByActionType": ev["actionType"] if ev else None,
                "clearedByDescription": ev["description"] if ev else None,
                "howCleared": ev["howCleared"] if ev else ("Naturally vacant at start of reset" if not was_init_occupied else "Not cleared"),
                "isCurrentlyVacant": is_vacant_now,
                "explanation": explanation,
            }
        elif step.type == ActionType.HOLD:
            src_obj = slot_map.get(step.slot_id)
            s_bay, s_shelf, s_pos = _extract_bay_shelf_pos(src_obj, step.slot_id)
            loc_str = f"Bay {s_bay or '1'} • Shelf {s_shelf or '1'} • Pos {s_pos or '1'}"
            step.clearance_info = {
                "destSlotId": step.slot_id,
                "destLocation": loc_str,
                "wasInitiallyOccupied": True,
                "initialOccupant": step.item or "Product",
                "clearedBeforePlacement": True,
                "clearedInStep": idx,
                "clearedByActionType": "hold",
                "clearedByDescription": step.description,
                "howCleared": "Lifted into hands to vacate slot",
                "isCurrentlyVacant": False,
                "explanation": f"Lifting '{step.item}' clears position ({loc_str}) to serve as an empty buffer slot for circular moves.",
            }
        elif step.type == ActionType.PULL:
            src_obj = slot_map.get(step.slot_id)
            s_bay, s_shelf, s_pos = _extract_bay_shelf_pos(src_obj, step.slot_id)
            loc_str = f"Bay {s_bay or '1'} • Shelf {s_shelf or '1'} • Pos {s_pos or '1'}"
            step.clearance_info = {
                "destSlotId": step.slot_id,
                "destLocation": loc_str,
                "wasInitiallyOccupied": True,
                "initialOccupant": step.item or "Decommissioned Product",
                "clearedBeforePlacement": True,
                "clearedInStep": idx,
                "clearedByActionType": "pull",
                "clearedByDescription": step.description,
                "howCleared": "Removed to return cart",
                "isCurrentlyVacant": False,
                "explanation": f"Pulling decommissioned item '{step.item}' from ({loc_str}) vacates the slot for future planograms.",
            }
        elif step.type == ActionType.SET_ASIDE:
            src_obj = slot_map.get(step.slot_id)
            s_bay, s_shelf, s_pos = _extract_bay_shelf_pos(src_obj, step.slot_id)
            loc_str = f"Bay {s_bay or '1'} • Shelf {s_shelf or '1'} • Pos {s_pos or '1'}"
            to_obj = slot_map.get(step.to_slot_id or "")
            t_bay, t_shelf, t_pos = _extract_bay_shelf_pos(to_obj, step.to_slot_id or "")
            dest_desc = f"Bay {t_bay or 'future'} • Shelf {t_shelf or '1'} • Pos {t_pos or '1'}"
            step.clearance_info = {
                "destSlotId": step.slot_id,
                "destLocation": loc_str,
                "wasInitiallyOccupied": True,
                "initialOccupant": step.item or "Product",
                "clearedBeforePlacement": True,
                "clearedInStep": idx,
                "clearedByActionType": "set_aside",
                "clearedByDescription": step.description,
                "howCleared": f"Staged to transit cart for {dest_desc}",
                "isCurrentlyVacant": True,
                "explanation": (
                    f"Product '{step.item}' belongs to future {dest_desc}. "
                    f"It is set aside into transit cart in Step {idx}, clearing {loc_str} so same-bay "
                    f"products have immediate free space for fix-in-bay moves."
                ),
            }
        elif step.type == ActionType.SWAP:
            s1_obj = slot_map.get(step.slot_id)
            s2_obj = slot_map.get(step.to_slot_id or "")
            b1, sh1, p1 = _extract_bay_shelf_pos(s1_obj, step.slot_id)
            b2, sh2, p2 = _extract_bay_shelf_pos(s2_obj, step.to_slot_id or "")
            loc_str = f"Bay {b1} • S{sh1} • P{p1} ↔ Bay {b2} • S{sh2} • P{p2}"
            step.clearance_info = {
                "destSlotId": f"{step.slot_id} ↔ {step.to_slot_id}",
                "destLocation": loc_str,
                "wasInitiallyOccupied": True,
                "initialOccupant": f"{step.item} / {step.item_b}",
                "clearedBeforePlacement": True,
                "clearedInStep": idx,
                "clearedByActionType": "swap",
                "clearedByDescription": step.description,
                "howCleared": "Simultaneous two-hand swap",
                "isCurrentlyVacant": False,
                "explanation": f"Mutual displacement between ({loc_str}). Both items lifted and swapped simultaneously with two hands.",
            }

        # Update occupancy simulation after this action
        if step.type == ActionType.HOLD:
            item = current_occupancy.get(step.slot_id)
            current_occupancy[step.slot_id] = None
            clearance_events[step.slot_id] = {
                "stepNumber": idx,
                "actionType": "hold",
                "description": step.description,
                "itemRemoved": item,
                "howCleared": "lifted into associate's hands (creating buffer slot)",
            }
        elif step.type == ActionType.SET_ASIDE:
            item = current_occupancy.get(step.slot_id)
            current_occupancy[step.slot_id] = None
            to_obj = slot_map.get(step.to_slot_id) if step.to_slot_id else None
            t_bay, t_s, t_p = _extract_bay_shelf_pos(to_obj, step.to_slot_id or "")
            to_loc_short = f"Bay {t_bay} Shelf {t_s} Pos {t_p}" if t_s else (step.to_slot_id or "future bay")
            clearance_events[step.slot_id] = {
                "stepNumber": idx,
                "actionType": "set_aside",
                "description": step.description,
                "itemRemoved": item,
                "howCleared": f"set aside into transit cart for {to_loc_short}",
            }
        elif step.type in (ActionType.MOVE, ActionType.FIX_IN_BAY):
            if step.sub_moves:
                for sm in step.sub_moves:
                    item = current_occupancy.get(sm.from_slot)
                    current_occupancy[sm.from_slot] = None
                    current_occupancy[sm.to_slot] = item
                    to_obj = slot_map.get(sm.to_slot) if sm.to_slot else None
                    _, to_s, to_p = _extract_bay_shelf_pos(to_obj, sm.to_slot or "")
                    to_loc_short = f"Shelf {to_s} Pos {to_p}" if to_s else (sm.to_slot or "destination")
                    clearance_events[sm.from_slot] = {
                        "stepNumber": idx,
                        "actionType": step.type.value,
                        "description": step.description,
                        "itemRemoved": item,
                        "howCleared": f"moved to {to_loc_short}",
                    }
            else:
                item = current_occupancy.get(step.slot_id)
                current_occupancy[step.slot_id] = None
                if step.to_slot_id:
                    current_occupancy[step.to_slot_id] = item
                to_obj = slot_map.get(step.to_slot_id) if step.to_slot_id else None
                _, to_s, to_p = _extract_bay_shelf_pos(to_obj, step.to_slot_id or "")
                to_loc_short = f"Shelf {to_s} Pos {to_p}" if to_s else (step.to_slot_id or "destination")
                clearance_events[step.slot_id] = {
                    "stepNumber": idx,
                    "actionType": step.type.value,
                    "description": step.description,
                    "itemRemoved": item,
                    "howCleared": f"moved to {to_loc_short}",
                }
        elif step.type in (ActionType.PLACE, ActionType.PLACE_FROM_CART):
            target_id = step.to_slot_id or step.slot_id
            current_occupancy[target_id] = step.item
        elif step.type == ActionType.SWAP:
            s1, s2 = step.slot_id, step.to_slot_id
            item1 = current_occupancy.get(s1)
            item2 = current_occupancy.get(s2) if s2 else None
            current_occupancy[s1] = item2
            if s2:
                current_occupancy[s2] = item1
                clearance_events[s1] = {
                    "stepNumber": idx,
                    "actionType": "swap",
                    "description": step.description,
                    "itemRemoved": item1,
                    "howCleared": f"swapped simultaneously with {s2}",
                }
                clearance_events[s2] = {
                    "stepNumber": idx,
                    "actionType": "swap",
                    "description": step.description,
                    "itemRemoved": item2,
                    "howCleared": f"swapped simultaneously with {s1}",
                }
        elif step.type == ActionType.RESTOCK:
            current_occupancy[step.slot_id] = step.item
        elif step.type == ActionType.PULL:
            item = current_occupancy.get(step.slot_id)
            current_occupancy[step.slot_id] = None
            clearance_events[step.slot_id] = {
                "stepNumber": idx,
                "actionType": "pull",
                "description": step.description,
                "itemRemoved": item,
                "howCleared": "pulled directly into return cart",
            }
        elif step.type == ActionType.SLIDE:
            for sm in step.sub_moves:
                item = current_occupancy.get(sm.from_slot)
                current_occupancy[sm.from_slot] = None
                current_occupancy[sm.to_slot] = item
                clearance_events[sm.from_slot] = {
                    "stepNumber": idx,
                    "actionType": "slide",
                    "description": step.description,
                    "itemRemoved": item,
                    "howCleared": f"slid to {sm.to_slot}",
                }

    return final_steps


def extract_slots_from_retailer_actions(actions: List[Dict[str, Any]]) -> List[Slot]:
    """Adapt raw backend action-list items from the retailer API into Slot models."""
    slots_by_id: Dict[str, Slot] = {}

    for item in actions:
        if not isinstance(item, dict):
            continue

        product_name = str(item.get("product_title") or "")
        product_obj = item.get("product")
        if not product_name and isinstance(product_obj, dict):
            product_name = str(product_obj.get("name") or "")

        upc = str(item.get("displayed_upc") or item.get("upc") or "")
        if not upc and isinstance(product_obj, dict):
            upc = str(product_obj.get("upc") or product_obj.get("product_code") or "")

        brand = str(item.get("brand") or "")
        if not brand and isinstance(product_obj, dict):
            brand = str(product_obj.get("brand") or "")

        image = str(item.get("image") or "")
        if not image and isinstance(product_obj, dict):
            image = str(product_obj.get("image") or "")

        item_label = product_name or upc or f"SKU-{item.get('id', 'unknown')}"

        # Current Position
        curr_pos = item.get("current_position")
        if isinstance(curr_pos, dict):
            sec_info = curr_pos.get("section_info") or {}
            raw_bay = str(sec_info.get("name") or sec_info.get("id") or "1").strip()
            bay = re.sub(r"^bay\s*", "", raw_bay, flags=re.IGNORECASE).strip() or "1"
            shelf_raw = curr_pos.get("shelf", "0")
            pos_raw = str(curr_pos.get("position", "0")).strip()
            slot_id = f"Bay{bay}_S{shelf_raw}_P{pos_raw}"
            coords_raw = curr_pos.get("coordinates")
            coords = None
            if isinstance(coords_raw, (list, tuple)) and len(coords_raw) >= 1:
                first_pt = coords_raw[0]
                if isinstance(first_pt, (list, tuple)) and len(first_pt) >= 2:
                    coords = Coordinates(x=float(first_pt[0]), y=float(first_pt[1]))

            shelf_digits = re.sub(r"\D", "", str(shelf_raw))
            shelf_num = int(shelf_digits) if shelf_digits else None

            if slot_id not in slots_by_id:
                slots_by_id[slot_id] = Slot(
                    id=slot_id,
                    bay=bay,
                    current=item_label,
                    target=None,
                    coordinates=coords,
                    shelf=shelf_num,
                    position=pos_raw,
                    upc=upc,
                    product_title=product_name,
                    brand=brand,
                    image=image,
                )
            else:
                s = slots_by_id[slot_id]
                s.current = item_label
                if not s.upc and upc:
                    s.upc = upc
                if not s.product_title and product_name:
                    s.product_title = product_name
                if not s.brand and brand:
                    s.brand = brand
                if not s.image and image:
                    s.image = image

        # Expected Position
        exp_pos = item.get("expected_position")
        if isinstance(exp_pos, dict):
            sec_info = exp_pos.get("section_info") or {}
            raw_bay = str(sec_info.get("name") or sec_info.get("id") or "1").strip()
            bay = re.sub(r"^bay\s*", "", raw_bay, flags=re.IGNORECASE).strip() or "1"
            shelf_raw = exp_pos.get("shelf", "0")
            pos_raw = str(exp_pos.get("position", "0")).strip()
            slot_id = f"Bay{bay}_S{shelf_raw}_P{pos_raw}"
            shelf_digits = re.sub(r"\D", "", str(shelf_raw))
            shelf_num = int(shelf_digits) if shelf_digits else None

            if slot_id not in slots_by_id:
                slots_by_id[slot_id] = Slot(
                    id=slot_id,
                    bay=bay,
                    current=None,
                    target=item_label,
                    shelf=shelf_num,
                    position=pos_raw,
                    upc=upc,
                    product_title=product_name,
                    brand=brand,
                    image=image,
                )
            else:
                s = slots_by_id[slot_id]
                s.target = item_label
                if not s.upc and upc:
                    s.upc = upc
                if not s.product_title and product_name:
                    s.product_title = product_name
                if not s.brand and brand:
                    s.brand = brand
                if not s.image and image:
                    s.image = image

    return list(slots_by_id.values())
