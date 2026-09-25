# Shelf-Reset Sequencing Engine: Mathematical Rules & Architecture

---

## 1. Executive Summary & Problem Statement

In retail planogram resets, store associates are tasked with transforming an existing physical shelf layout ($S_{current}$) into an updated target planogram ($S_{target}$).

### The Naive Retailer Approach ❌
Legacy retailer APIs generate instructions naively:
1. Every misplaced product on a shelf is instructed to be **"Set Aside into Transit Cart"** ($N$ picks + $N$ cart placements = $2N$ touches).
2. The associate wheels a heavy cart loaded with dozens of mixed SKUs up and down the aisle.
3. Every product is then searched for in the cart and placed onto the shelf ($N$ cart searches + $N$ placements).
4. **Result**: Extreme physical fatigue, cart clutter, $2N$ to $3N$ touches, aisle congestion, and high error rates.

### The Antigravity Graph Sequencer ⚡
The **Antigravity Sequencing Engine** models the entire physical aisle as a directed dependency graph. By identifying **vacant buffer slots**, decomposing the problem into **chains, slides, swaps, and hold-cycles**, and staging only cross-bay items, the engine:
- Achieves **direct same-bay shelf shifts** with **zero cart touches**.
- Pre-verifies slot vacancy to eliminate spatial collision.
- Reduces physical touches by **40% to 65%**.
- Closes the loop on cross-bay items with explicit **`PLACE_FROM_CART`** companion actions.
- Bundles multi-facing moves and sweeps shelves ergonomically.

---

## 2. Mathematical Graph Theory Model

Let the aisle be represented as a set of physical slots:
$$V = \{s_1, s_2, \dots, s_n\}$$
Each slot $s \in V$ is defined by a 3D coordinate tuple:
$$s = (\text{bay}, \text{shelf}, \text{position})$$
with state:
$$\text{state}(s) = \langle \text{current}(s), \text{target}(s) \rangle$$
where $\text{current}(s), \text{target}(s) \in \text{SKU} \cup \{\emptyset\}$.

### Graph Construction:
We construct a directed dependency multigraph $G = (V, E)$.
For every slot $u \in V$ where $\text{current}(u) \neq \text{target}(u)$ and $\text{current}(u) \neq \emptyset$:
$$\exists v \in V \text{ such that } \text{target}(v) = \text{current}(u) \text{ and } u \neq v \implies (u \to v) \in E$$
- Edge $(u \to v)$ indicates that the product currently sitting in slot $u$ must physically move into slot $v$.
- If $\text{current}(s) = \text{target}(s)$, slot $s$ is **in-place** and is excluded from $E$ (degree $= 0$).

---

## 3. Action Taxonomy (Complete Step Types)

The sequencer outputs 8 distinct, deterministic action types:

| Action Type | Icon | Direction | Physical Description |
| :--- | :---: | :--- | :--- |
| **`PULL`** | 📤 | Shelf $\to$ Salvage Cart | Dead stock / discontinued item removed directly to return cart. Vacates slot. |
| **`SET_ASIDE`** | 📦 | Shelf $\to$ Transit Cart | Product belonging to a *future bay* staged into cart. Vacates current slot. |
| **`HOLD`** | ✋ | Shelf $\to$ Hands | Cycle-breaker: lifts 1 item into hands to create temporary empty buffer slot. |
| **`FIX_IN_BAY`** | ⚡ | Shelf $\to$ Shelf (Same Bay) | Direct intra-bay shelf shift with 0 cart touches into verified empty slot. |
| **`SLIDE`** | ↔️ | Shelf $\to$ Shelf (Adjacent) | Contiguous chain of adjacent facings shifted together in a single motion. |
| **`SWAP`** | 🤝 | Shelf $\leftrightarrow$ Shelf (Mutual) | 2-item mutual cycle exchanged simultaneously using two hands. |
| **`PLACE_FROM_CART`** | 📥 | Transit Cart $\to$ Shelf | Cross-bay item taken from transit cart and placed into target bay. |
| **`RESTOCK`** | ➕ | Case / Box $\to$ Shelf | Fresh incoming inventory stocked from freight case into empty slot. |

---

## 4. The 10 Core Sequencing Invariants & Rules

### Rule 1: Collision-Free Invariant & Topological Vacancy Ordering Guarantee
> **Invariant**: No product may be placed into slot $v$ while slot $v$ is occupied.
> Formally, an action $\text{place}(u \to v)$ at step index $t_{place}$ is valid if and only if the step $t_{vacate}$ that removed or shifted the prior occupant of $v$ strictly precedes it:
> $$S_{\text{vacate}}(v) \prec S_{\text{place}}(v) \iff t_{\text{vacate}}(v) < t_{\text{place}}(v)$$
> and at the moment of execution:
> $$\text{occupancy}_t(v) = \emptyset$$

The engine guarantees this by:
1. **Topological Vacancy Ordering**: If action $A_i$ places into slot $X$, and action $A_j$ vacates slot $X$, the sequencer's dependency sorter ensures $j < i$ so slot $X$ is empty prior to placement.
2. **Backward Chain Traversal**: Walking displacement chains backward starting from a naturally empty or freshly vacated terminal slot ($v_k \to v_{k-1} \to \dots \to v_1$).
3. **Single-Hold Buffer Induction**: Breaking closed cycles with a single `HOLD` into hands to create a temporary buffer vacancy.
4. **Full Clearance Provenance**: Every placement step carries structured `clearance_info` proving exactly which step cleared slot $v$, the action type that cleared it, and the prior occupant removed.

---

### Rule 2: In-Place Item Preservation & Target Slot Immunity (Zero Disturbance)
> **Rule**: Any slot where $\text{current}(s) == \text{target}(s)$ must never be touched, moved, displaced, or targeted.
> $$\forall s \in V: \text{current}(s) = \text{target}(s) \implies s \notin \text{Actions} \land s \notin \text{TargetSlots}$$

- **Zero Touch**: The engine completely ignores correctly positioned stock, preventing redundant moves and shelf clutter.
- **Target Immunity**: In-place slots are strictly excluded from the pool of open destination slots (`target_to_slots`). An incoming product is NEVER directed into an in-place slot, preventing catastrophic spatial collisions and planogram overwriting.

---

### Rule 3: Phase 1 — Dead Stock Removal Across ALL Bays First (`PULL` / `ACTION_REMOVE`)
> **Phase 1 in Store Execution**: Decommissioned, discontinued, or expired products ($\text{target}(s) = \emptyset$) must be removed across **ALL BAYS FIRST** to the salvage cart before any product repositioning starts.

- **Aisle-Wide Sweep**: The associate sweeps the entire section first to clear all dead stock across Bay 1, Bay 2, Bay 3, etc.
- **Why**: Removing dead stock aisle-wide immediately creates fresh empty buffer slots on shelves across all bays, preventing associates from working around junk and maximizing room for subsequent intra-bay and cross-bay shifts.

---

### Rule 4: Phase 2 — Future-Bay Transit Cart Staging (`SET_ASIDE`)
> **Phase 2 in Bay Execution**: Products currently sitting in Bay $X$ whose target planogram location is in a different bay ($Y > X$) are staged into the transit cart **before** same-bay shifts begin.

- **Why**: Products leaving Bay $X$ vacate their slots immediately, maximizing free space for same-bay reorganization.
- **Cart Categorization**: The mobile app tags each set-aside item with its exact destination (`Cart Slot: Bay Y • Shelf S • Pos P`).

---

### Rule 5: Phase 3 — Same-Bay Zero-Cart Shifts & Swaps (`FIX_IN_BAY`)
> **Phase 3 in Bay Execution**: Products moving within the same bay ($\text{bay}(u) = \text{bay}(v)$) are shifted, slid, or swapped directly on the shelf **after** future-bay items have been set aside.

- **Why**: Bypasses the retailer API's redundant "Set Aside to Cart" instruction. Instead of 2 touches (shelf $\to$ cart $\to$ shelf), the associate shifts the item directly (1 touch).
- **50% Effort Reduction**: Directly cuts touch count in half for all intra-bay moves.

---

### Rule 6: Single-Hold Circular Dependency Breaker (`HOLD` & `PLACE`)
> **Rule**: For any closed cycle of moves $u_1 \to u_2 \to \dots \to u_k \to u_1$ ($k \ge 3$):
1. Lift $u_1$ into associate's hands: $\text{HOLD}(u_1)$.
2. Slot $u_1$ is now physically vacant.
3. Walk the cycle backward: shift $u_k \to u_1$, then $u_{k-1} \to u_k$, ..., down to $u_2 \to u_3$.
4. Place the held item into slot $u_2$: $\text{PLACE}(held \to u_2)$.

- **Why**: Resolves circular deadlocks with exactly **1 temporary hold** and **0 cart touches**. Associate hands are completely free at the conclusion of the cycle.
- **2-Item Cycles**: Handled as an instantaneous two-hand dual swap: $\text{SWAP}(u_1 \leftrightarrow u_2)$.

---

### Rule 7: Phase 4 — Cross-Bay Placement & Pick from Future Bay (`PLACE_FROM_CART`)
> **Phase 4 in Bay Execution**: In the current bay, items coming from future bays or staged earlier in the transit cart are picked and placed into their final target shelf slots.

- **Companion Action Generation**:
  $$\text{SET\_ASIDE}(u \in \text{Bay } X \to v \in \text{Bay } Y) \implies \text{PLACE\_FROM\_CART}(\text{Cart} \to v \in \text{Bay } Y)$$
- **Zero Stranded Items**: Guarantees that at the end of the shift, the transit cart is 100% empty and no product is left stranded.
- **Sequencing Order**: In Bay $Y$, dead stock is already pulled, future-bay items are staged, and same-bay shifts have executed. Target slot $v$ is guaranteed verified vacant before the cart/future-bay item is placed.

---

### Rule 7b: Phase 5 — Backroom Missing Inventory Restocking (`RESTOCK`)
> **Phase 5 in Bay Execution**: Fresh incoming inventory from freight cases / backroom carts is stocked into remaining empty slots **last**, once all existing shelf stock has been organized.

---

### Rule 8: Multi-Facing Bundling (`facing_qty` Bundling)
> **Rule**: When $K$ adjacent facings of the same SKU on the same shelf move in unison:
> $$\text{Shift}(S: P_{start}..P_{end} \to P'_{start}..P'_{end})$$

- Instead of instructing the associate to move 3 identical cans one by one in 3 separate steps, the engine emits a single bundled step:
  `fix_in_bay S3:P2..P4→P5..P7 (Chicken Noodle • 3 facings)`
- **Human Factor**: Associates naturally push adjacent facings together with two hands. Bundling eliminates repetitive tapping on the mobile screen.

---

### Rule 9: Ergonomic Boustrophedon Sweep
> **Rule**: Actions within each bay are sorted to minimize physical fatigue:
> 1. **Vertical Sweep (Top-to-Bottom)**: High shelf tiers (Shelf 6/7) are cleared and reorganized first, moving down to lower shelves (Shelf 1). Reduces repeated bending and stooping.
> 2. **Lateral Sweep (Snake / Boustrophedon)**:
>    - Even shelves (Shelf 6, 4, 2): Left-to-Right ($P_1 \to P_n$).
>    - Odd shelves (Shelf 5, 3, 1): Right-to-Left ($P_n \to P_1$).
> 3. **Mobile Display Convention**:
>    - Badge displays: `📍 Shelf S (Tier) • Direction: Left ➔ Right` to give simple, clear direction on the sales floor.

---

### Rule 10: Automated Physical Invariants Validation (The 9 IR Studio Invariants)
> **Verification Gate**: Every sequence output by the backend or simulated on mobile is subjected to 9 strict physical invariant rules enforced by `invariants_validator.py`:

| Invariant # | Name | Mathematical / Physical Constraint Enforced |
| :---: | :--- | :--- |
| **1** | **Action Count Fidelity** | Total backend planogram actions equal domain model actions across all bays. |
| **2** | **Zero Duplicate Action Cards** | Every physical card key `(bay, shelf, pos, subtype)` is unique. |
| **3** | **Fix-in-Bay Mutual Exclusivity** | Intra-bay shifts never emit redundant `SetAside` or `AddItems` cards. |
| **4** | **100% Cross-Bay Pairing** | Every `SetAside` pick is bijectively paired with a companion `Place` card (0 ghost adds, 0 stranded picks). |
| **5** | **Shelf Topology & Bounds** | Shelf numbers, position indices, and bay geometry respect physical boundaries. |
| **6** | **Out-of-Stock Restock Sourcing** | Shelf voids without current occupants are sourced from backroom stock. |
| **7** | **Identify Scan Resolution** | Camera scan resolution handles all product outcomes without unhandled states. |
| **8** | **Final Rolling Cart Balance** | Transit cart holds exactly 0 items at shift conclusion (only salvage items staged for backroom return). |
| **9** | **In-Place Preservation** | In-place products ($\text{current} = \text{target}$) generate **0 moves** and are immune from being targeted as open slots. |

---

## 5. Clearance Provenance & Location A to B Clearance Semantics

When moving a product from **Location A to Location B**, the associate must never find Location B occupied. The engine tracks clearance with deterministic provenance:

```
[ Step K: Vacate Slot B ]  ──────> [ Step M: Move Product A → Slot B ]
  (e.g., FIX_IN_BAY, PULL,               (Guaranteed: M > K)
   or SET_ASIDE from Slot B)              (Target Slot B is 100% Vacant)
```

### Clearance States for Target Slot B:
1. **Naturally Vacant at Start**:
   - Location B had no product initially ($\text{initialOccupant} = \emptyset$).
   - Mobile badge: `🟢 Target Slot: Naturally Vacant at Start`.
   - Explanation: `Target position was naturally VACANT at the start of reset. No product needed to be removed before placement.`
2. **Pre-Cleared in Earlier Step $K$**:
   - Location B initially held an item, which was moved, pulled, or staged in Step $K$ ($K < M$).
   - Mobile badge: `✅ Target Slot: Already Cleared in Step K (FIX_IN_BAY)`.
   - Mobile Verification Card:
     > **Verification Passed**: Target slot (`Bay 1 • Shelf 3 • Pos 5`) was already cleared in earlier **Step K** when `'Initial Item'` was moved to Shelf 3 Pos 8. The slot is guaranteed **100% VACANT** before placing `'New Item'`.
3. **Collision Warning (Violation Caught by Validator)**:
   - If a step attempts to place into an occupied slot where $\text{clearedBeforePlacement} = \text{False}$:
   - Mobile badge: `⚠️ Target Slot: Currently Occupied (Collision Warning!)`.
   - Status Pill: `⚠️ Occupied Collision`. Protects store associate from attempting impossible physical shelf placement.

---

## 6. Effort Calculation Methodology (KLM-P Model)

The effort savings metric is derived from the industrial engineering **Keystroke-Level & Physical Action Model (KLM-P)** standard.

### Definition of a "Physical Touch"
- **1 Physical Touch**: The act of an associate physically picking up an item from a shelf/cart, **OR** placing an item down onto a shelf/cart.
- A direct shelf move ($A \to B$) = 1 pick + 1 place = **2 physical touches** (1 operation).
- A cart round-trip ($A \to \text{Cart} \to B$) = 1 pick + 1 cart drop + 1 cart search/pick + 1 shelf place = **4 physical touches** (2 separate operations).

### Mathematical Formulas

#### 1. Naive Retailer Baseline
In the naive approach, every mismatched slot ($M$) undergoes a 2-step cart round-trip:
$$\text{Naive Steps} = M \times 2$$
$$\text{Naive Touches} = M \times 2 \text{ actions} = 2M$$

#### 2. Antigravity Sequencer Actuals
Our sequencer shifts same-bay items directly (1 step), bundles multi-facings, and only stages true cross-bay items:
$$\text{Actual Touches} = \sum_{s \in \text{Steps}} (\text{sub\_moves}(s) \text{ if bundled else } 1)$$

#### 3. Percentage Effort Saved
$$\text{Effort Saved \%} = \frac{\text{Naive Touches} - \text{Actual Touches}}{\text{Naive Touches}} \times 100$$

---

## 7. Real-World Task Benchmark (`Task #42484849`)

| Dimension | ❌ Naive Retailer API | ⚡ Antigravity Graph Sequencer | Real-World Store Impact |
| :--- | :---: | :---: | :--- |
| **Mismatched Planogram Slots** | 197 slots | 197 slots | Identical planogram requirements |
| **Total Steps Generated** | 197 steps | **123 steps** | **-37.6% fewer steps on screen** |
| **Physical Touch Operations** | 394 touches | **233 touches** | **-40.9% physical effort reduction** |
| **Same-Bay Cart Stops** | 68 items to cart | **0 items** | **100% direct shelf shifts** |
| **Cross-Bay Cart Tracking** | Stranded in cart | **31 explicit `place_from_cart`** | **100% loop closure (0 stranded items)** |
| **Multi-Facing Handling** | 1-by-1 single cans | **8 bundled sweeps** | **Shifted together as blocks** |
| **Spatial Collisions** | Frequent | **0 Collisions** | **Guaranteed pre-placement vacancy** |

---

## 8. Architectural Separation: Backend Engine vs. Mobile UI

| Concern | ⚙️ Backend Sequencing Engine (`shelf_reset_sequencer.py`) | 📱 Mobile Application (`shelf_reset_mobile.html` / Flutter) |
| :--- | :--- | :--- |
| **Dependency Graph** | Constructs $G = (V, E)$, detects cycles, resolves Tarjan components. | None. Consumes linear JSON step list. |
| **Phase Orchestration** | Enforces Pull $\to$ Set-Aside $\to$ Hold $\to$ Fix-in-Bay $\to$ Place from Cart. | Displays current phase banner & step progress. |
| **Clearance Simulation** | Simulates virtual occupancy at every step; generates `clearance_info`. | Displays `Provenance & Clearance` verification cards. |
| **Ergonomics & Direction**| Computes top-to-bottom vertical and serpentine lateral order. | Displays `📍 Shelf S (Tier) • Direction: Left ➔ Right`. |
| **Facing Bundling** | Aggregates adjacent identical moves into `facing_qty > 1` + `sub_moves`.| Displays `📦 3 FACINGS BUNDLE` pill with slot range. |
| **Trace Filtering** | Emits normalized step types (`fix_in_bay`, `pull`, `set_aside`, etc.). | Trace filter chips (`⚡ Move / Fix-in-Bay`, `📥 From Cart`). |
| **Hardware & Scanning** | Agnostic. Exposes clean REST API. | Barcode laser/camera scanning, haptic feedback, audio tones. |
| **2D Planogram View** | Supplies slot geometry and SKU metadata. | Interactive SVG/DOM shelf grid with real-time color states. |
