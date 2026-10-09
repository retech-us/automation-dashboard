# KRCS scan findings — realogram versus planogram

Reviewed and corrected 2026-10-09. Three issues. Each section has the finding, then the root cause.

Slot numbers in this document are product-order positions. A planogram product with `horizontal_facing` greater than 1 still occupies one product-order slot. Raw facing indexes are not used.

## Finding 1 — Scan 17743155: products marked ok in the wrong slot

Scan: [17743155](https://krcs.rebotics.net/reporting/scans/17743155?store=5347&category=979&planogram=1216617&date=2026-10-05)

| Field | Value |
|---|---|
| Store | 024-00713 Test (5347) |
| Category | 594-DRESSINGS/DIPS (979) |
| Planogram | 594-DRESSINGS/DIPS 700 (1216617) |
| Section | 1 |
| Captured | 2026-10-05 10:52 UTC |
| Stage | Pre-photo, processing done |

### Finding

The scan treats **ok** as “this UPC belongs somewhere on this shelf.” It does not require the UPC in the slot to be the planogram UPC for that position.

A product is location-ok only when the realogram UPC at a slot is the planogram UPC for that same shelf and product-order position. On this scan, **4 product slots** meet that rule. Those 4 slots are 6 detection rows. **38 product slots marked ok do not.** Those 38 slots are 46 detection rows. Each of those 38 is a real planogram UPC for the same shelf, sitting in a different slot, and the scan still sets `action_type` to `ACTION_CORRECT` and does not ask for a move.

No product that is already in its correct slot is asked to move.

Shelf 7 is the pattern. Position 7:1 should be Homestyle `070200551619`. The shelf shows Lemon `070200551640`, which belongs at 7:2, and the scan still marks Lemon ok. The products after it are each shifted into the next product’s slot and marked ok the same way.

### Root cause

`ok` on this scan means the UPC was recognized. `ACTION_CORRECT` is assigned when that UPC belongs on the same shelf, not when the realogram position equals the planogram position. `exceptions` is empty, so there is no separate mismatch reason.

Shelf 7 shows how that rule fails. Homestyle `070200551619` is missing from planogram position 7:1. Lemon `070200551640` is detected at 7:1. Lemon is a shelf-7 UPC, so the scan sets `ACTION_CORRECT` and does not ask for a move. Every following product is one slot left of its planogram UPC and is marked the same way. A product whose UPC belongs on a different shelf is the one that gets `ACTION_MOVE`.

### What the scan calls ok

Each realogram product comes back with:

- `type` / `item_type.type`: `ok` (drawn green), `hole`, or `invader`
- `action_type`: `ACTION_CORRECT`, `ACTION_MOVE`, `ACTION_ADD`, or `ACTION_REMOVE`
- `exceptions`: empty on every product in this scan

There is no reason string on an ok product. `ACTION_CORRECT` is the only signal that the scan decided not to ask for a move.

Checked against the planogram item list, every `ACTION_CORRECT` product whose slot UPC does not match still belongs on that same shelf. Products whose UPC belongs on a different shelf are the ones given `ACTION_MOVE`.

### Facings whose UPC matches the slot

These four were correctly left alone. Slot 2:10 has three detection rows of the same UPC.

| Slot | UPC | Product | Detection rows |
|---|---|---|---|
| 2:1 | 811892026807 | CABO AVOCADO SQUEEZE | 1 |
| 2:3 | 811892021895 | CABO GUACAMOLE AUTHENTIC | 1 |
| 2:4 | 811892024896 | CABO GUACAMOLE FIESTA | 1 |
| 2:10 | 040822346535 | TOST GUAC LIME MEDIUM | 3 |

### Marked ok, present UPC is not the planogram UPC

Present UPC is what the realogram detected. Expected UPC is the planogram product assigned to that same shelf and position, including a product that occupies the next facing when `horizontal_facing` is greater than 1. The last column is the planogram slot for the UPC that was actually seen.

Shelf 2 has three planogram UPCs named TOST GUAC HINT LIME MILD: `040822346511` at 2:7, `040822346498` at 2:8, and `040822346504` at 2:9. The realogram UPC at 2:9 is `040822346511`, which belongs at 2:7.

Positions 4:12, 4:13, and 4:14 are past the end of the planogram. Shelf 4 stops at product-order position 11.

| Slot | Present UPC | Present product | Expected UPC | Expected product | Present UPC belongs at |
|---|---|---|---|---|---|
| 7:1 | 070200551640 | SIMPLY DRESSED LEMON DRES | 070200551619 | SIMPLY DRESSED HOMESTYLE | 7:2 |
| 7:2 | 070200551626 | SIMPLY DRESSED BALSAMIC V | 070200551640 | SIMPLY DRESSED LEMON DRES | 7:3 |
| 7:3 | 071464022853 | BLTH RANCH YOGURT DRSG | 070200551626 | SIMPLY DRESSED BALSAMIC V | 7:4 |
| 7:4 | 071464022846 | BLTH CHKY BLU CHEESE DRSG | 071464022853 | BLTH RANCH YOGURT DRSG | 7:5 |
| 7:5 | 071464022778 | BLTH CREAMY CAESAR DRSG | 071464022846 | BLTH CHKY BLU CHEESE DRSG | 7:6 |
| 7:6 | 071464021818 | BLTH RANCH YOGURT DRSG | 071464022778 | BLTH CREAMY CAESAR DRSG | 7:7 |
| 7:10 | 755763001756 | MAKT HONEY GINGER DRSG | 011110691804 | PRSL DRSG TRUFFLE RANCH | 7:8 |
| 7:11 | 755763004009 | MAKT GINGER DRSNG | 011110691811 | PRSL DRSG SPICY BLEU CHS | 7:9 |
| 6:2 | 070200856127 | CHICK-FIL-A AVO LIME DRSG | 070200504219 | MARZ CHNKY BLUE CHS DRSG | 6:6 |
| 6:3 | 070200856134 | CHICK-FIL-A CRMY SALSA DR | 070200524521 | MARZ SIGNATRE BL CHS DRSG | 6:7 |
| 6:4 | 070200856141 | CHICK-FIL-A GDN HERB DRS | 070200551107 | MARZ RANCH DRSG | 6:8 |
| 6:6 | 070200853829 | CHICK-FIL-A AVO LIME RNCH | 070200856127 | CHICK-FIL-A AVO LIME DRSG | 6:9 |
| 5:3 | 070200551121 | MARZ CAESAR DRSG | 070200504226 | MARZ THOUSAND ISLAND DRSG | 5:9 |
| 5:4 | 070200540354 | MARZ SLAW DRSG | 070200504318 | MARZ POPPYSEED DRSG | 5:10 |
| 5:5 | 077661125113 | LTHS HOMESTYLE RANCH DRSG | 070200504448 | MARZ HONEY FRENCH DRSG | 5:11 |
| 5:6 | 077661123270 | LTHS JALAPENO RANCH DRSG | 070200504240 | MARZ SWEET ITALIAN DRSG | 5:12 |
| 5:7 | 077661162064 | LTHS DILL RANCH DIP | 070200504394 | MARZ CAESAR SUPREME DRSG | 5:13 |
| 5:10 | 077661123218 | LTHS BL CH CHNKY SQZ DRSG | 070200540354 | MARZ SLAW DRSG | 5:14 |
| 5:11 | 077661171523 | LTHS CAESAR DRESSING | 077661125113 | LTHS HOMESTYLE RANCH DRSG | 5:15 |
| 4:10 | 071840050807 | MRES CHNKY BLU CHS DRSSNG | 077661003169 | LTHS CHNKY BLUE CHSE DRSG | 4:6 |
| 4:11 | 077661048139 | LTHS HOMESTYL RANCH DRSNG | 077661117927 | LTHS BIG BLUE DRESSING | 4:8 |
| 4:12 | 077661119099 | LTHS RANCH BUTTERMILK DRS | — | No planogram product at this position | 4:9 |
| 4:13 | 077661003169 | LTHS CHNKY BLUE CHSE DRSG | — | No planogram product at this position | 4:10 |
| 4:14 | 077661117927 | LTHS BIG BLUE DRESSING | — | No planogram product at this position | 4:11 |
| 3:8 | 851146002638 | FRCV SALSA MEDIUM | 070200530058 | MARZ CREAM CHSE FRUIT DIP | 3:5 |
| 3:8 | 851146002621 | FRCV SALSA MILD | 070200530058 | MARZ CREAM CHSE FRUIT DIP | 3:6 |
| 3:9 | 044276091706 | FRCV BRUSCHETTA TOM BASIL | 070200530140 | MARZ STRW CRM CHS FRT DIP | 3:7 |
| 2:7 | 736798903727 | GDFG CHUNKY GUACAMOLE | 040822346511 | TOST GUAC HINT LIME MILD | 2:5 |
| 2:8 | 736798903604 | GDFG SS BLK PPR AVCD MASH | 040822346498 | TOST GUAC HINT LIME MILD | 2:6 |
| 2:9 | 040822346511 | TOST GUAC HINT LIME MILD | 040822346504 | TOST GUAC HINT LIME MILD | 2:7 |
| 1:1 | 616112353561 | WHLY GUAC RESTAURANT BOWL | 616112465288 | WHLY GUACAMLE SQUEEZE MLD | 1:2 |
| 1:2 | 616112866702 | WHLY GUACAMOLE CLSSC BOWL | 616112353561 | WHLY GUAC RESTAURANT BOWL | 1:3 |
| 1:2 | 616112866733 | WHLY GUACAMOLE CLSC BOWL | 616112353561 | WHLY GUAC RESTAURANT BOWL | 1:4 |
| 1:3 | 616112866719 | WHLY GUACAMOLE CHNKY BOWL | 616112866702 | WHLY GUACAMOLE CLSSC BOWL | 1:5 |
| 1:5 | 616112866740 | WHLY GUACAMOLE CHNKY BOWL | 616112866719 | WHLY GUACAMOLE CHNKY BOWL | 1:6 |
| 1:7 | 616112031957 | WHLY GUACAMOLE 100CAL PK | 616112266069 | WHOLLY DICED AVOCADO TRAY | 1:8 |
| 1:8 | 616112031988 | WHLY GUACAMOLE SP HM MINI | 616112031957 | WHLY GUACAMOLE 100CAL PK | 1:9 |
| 1:9 | 616112031964 | WHLY GUACAMOLE SPICY MINI | 616112031988 | WHLY GUACAMOLE SP HM MINI | 1:10 |

### Move destinations

The scan generated 60 report-action rows, all recorded as `STATE_ACCEPTED`: 27 moves with reason Add Item, 10 moves with reason Fixed Item, 19 restocks, and 4 removes. The 37 move rows are 34 unique action ids.

Every move destination matches the planogram product-order slot for that UPC. An earlier comparison marked 13 of these destinations as wrong because it compared them with raw facing indexes. After horizontal facings are collapsed, those destinations are the correct slots.

Example: Panera Caesar `018959755551` is seen at 7:7 and asked to move to 6:10. Its planogram item has raw position 12 and `horizontal_facing` 1, which is product-order slot 6:10. The move to 6:10 is the correct slot.

### Shelf scores on the scan record

| Measure | Value |
|---|---|
| Detections | 101 |
| On-shelf availability | 78.4% |
| Facing compliance | 83.0% |
| Compliance before actions | 69.3% |
| Sequence compliance | 100% |
| Compliance after the actions were accepted | 100% |

The 100% figures are the post-acceptance scores on the scan record. They are not a count of slots whose realogram UPC matches the planogram UPC.

### Sources for finding 1

- `GET /api/v4/processing/actions/17743155/` for realogram products, positions, action types, and report actions
- `GET /api/v1/planograms/1216617/items/` for planogram shelf, position, and facing width
- `GET /api/v4/products/{id}/` for the planogram UPC of each product
- `GET /api/v1/reporting/R07/section-product-reports/?scan_id=17743155` for the digital-report status and reason

## Finding 2 — Scan 17773117: set-aside asked for products already in the correct slot

Scan: [17773117](https://krcs.rebotics.net/reporting/scans/17773117?store=5347&category=830&planogram=1216760&date=2026-10-06&selectedProductKey=030772093856-6:1)

| Field | Value |
|---|---|
| Store | 024-00713 Test (5347) |
| Category | 104-LAUNDRY DETERGENTS (830) |
| Planogram | 1216760, sections 1–7 |
| Captured | 2026-10-06 10:56 UTC |
| Stage | Pre-photo and post-photo, processing done |
| Selected product | `030772093856` at section 1, 6:1 |

### Finding

The defect is not limited to section 1. Across the 7 sections of this visit (14 scans), the backend asks for **32 same-slot actions on pre-photo and 31 on post-photo**. The 32 pre-photo actions are 31 Add Item set-asides and 1 Fixed Item. The 31 post-photo actions are all Add Item. **20** of the post-photo set-asides repeat the same product and slot from pre-photo. In section 1, **7 products that were moved into their correct slot on pre-photo are asked to set aside again on post-photo.** **45 products are marked ok in the wrong slot** on pre-photo. Sections 1, 3, 5, and 7 have the set-aside defect. Every section has products marked ok in the wrong slot. The section-by-section detail is under [All sections of this visit](#all-sections-of-this-visit).

In section 1 alone, the report asks for **23 Add Item / set-aside** actions. **15 of those 23 are unnecessary.** The UPC is already in the correct planogram slot, and the backend still emits `ACTION_MOVE` with reason Add Item where the source slot and the destination slot are the same, for example `4:1 → 4:1`. That no-op move is what becomes a set-aside: pick the product up and put it back in the same place.

**8 of the 23 are valid.** Those UPCs are not in their planogram slot, and the destination is the correct slot.

The “23 out of 29” count mixes two numbers. **29 is the price-tag count** on the scan. The digital report has **31 recognized ok rows and 9 out-of-stock rows**.

The selected UPC `030772093856` (TIDE EVO ORGNL SCENT DTRG) belongs at 6:1. The copies seen at 6:2 and 6:3 are real set-asides back to 6:1. A third copy seen at 5:1 is also in the wrong place, and that one gets no action.

### Root cause

The processing payload marks a product `ACTION_MOVE` with reason `Add Item` even when `from` and `to` are the same slot, for example `4:1 → 4:1`. The UPC in that slot is already the planogram UPC. The move does not change the position.

The mobile action list turns an Add Item move into a set-aside (pick) and then a place. With the same source and destination, that flow asks the associate to pick the product up and put it back. Those rows should be `ACTION_CORRECT`, or they should be left out of the action list.

Planogram positions here are the product order on the shelf. A product with two horizontal facings still occupies one product-order slot. Comparing the raw facing index would mark correct multi-facing products as shifted.

Post-photo processing classifies the new photo on its own and emits the same no-op move again. A product moved into its correct slot on pre-photo is asked to set aside on post-photo because its post-photo move is also from that slot to the same slot.

`ACTION_CORRECT` is also assigned when a product belongs to the neighboring section. For example, section 3 at 1:1 shows `030772172926`, whose planogram slot is section 2, 1:4, and it is still marked ok.

### Unnecessary set-asides

The present UPC matches the planogram UPC for that slot. The backend move does not change the slot.

| Slot | UPC | Product | Backend move |
|---|---|---|---|
| 6:3 | 030772093849 | TIDE EVO DETERGENT TILES | 6:3 → 6:3 |
| 5:5 | 030772235836 | TIDE LIQ HE DETERGENT | 5:5 → 5:5 |
| 4:1 | 030772171066 | TIDE PODS 3IN1 ORIGINAL | 4:1 → 4:1 |
| 4:2 | 030772171080 | TIDE PODS SPR MDW DTRGNT | 4:2 → 4:2 |
| 4:3 | 030772091630 | TIDE PWR POD HYG DETERGNT | 4:3 → 4:3 |
| 4:4 | 030772171325 | TIDE PWR PODS OXI BOOST | 4:4 → 4:4 |
| 4:5 | 030772171035 | TIDE W DWNY PWR PODS | 4:5 → 4:5 |
| 3:1 | 030772091654 | TIDE PODS SCNTD LNDRY SP | 3:1 → 3:1 |
| 3:3 | 030772091647 | TIDE PODS ULTRA LNDRY SP | 3:3 → 3:3 |
| 3:5 | 030772094969 | TIDE PWR PODS ULT DTRGNT | 3:5 → 3:5 |
| 2:1 | 037000009351 | TIDE PODS HE ORIG SCENT | 2:1 → 2:1 |
| 2:2 | 037000004622 | TIDE PODS SPRING MEADOW | 2:2 → 2:2 |
| 1:1 | 030772247518 | TIDE DTRGENT PODS | 1:1 → 1:1 |
| 1:2 | 030772247532 | TIDE LND DTR PDS 3IN1 SM | 1:2 → 1:2 |
| 1:3 | 030772171288 | TIDE PWR PODS OXI BOOST | 1:3 → 1:3 |

### Valid set-asides

These UPCs are not in the planogram slot, and the destination is that slot.

| Seen at | UPC | Product | Planogram slot |
|---|---|---|---|
| 6:2 | 030772093856 | TIDE EVO ORGNL SCENT DTRG | 6:1 |
| 6:3 | 030772093856 | TIDE EVO ORGNL SCENT DTRG | 6:1 |
| 6:4 | 030772093887 | TIDE EVO SPRNG BLAST DTRG | 6:2 |
| 6:5 | 030772093900 | TIDE EVO SB DETRGNT TILES | 6:4 |
| 6:6 | 030772244661 | TIDE LND DTR 2X LS ORIG | 6:5 |
| 5:3 | 030772093887 | TIDE EVO SPRNG BLAST DTRG | 6:2 |
| 2:3 | 030772171332 | TIDE POWER PODS OXI BOOST | 2:4 |
| 2:4 | 030772118054 | TIDE DOWNY SB PWR PODS FS | 2:3 |

Positions 2:3 and 2:4 are swapped with each other. Both set-asides are the right correction.

### Misplaced products that got no action

The same scan leaves these recognized products as ok with an empty reason, even though the UPC does not belong in the slot.

| Seen at | UPC | Product | Belongs at |
|---|---|---|---|
| 5:1 | 030772093856 | TIDE EVO ORGNL SCENT DTRG | 6:1 |
| 5:2 | 030772093849 | TIDE EVO DETERGENT TILES | 6:3 |
| 5:4 | 030772093900 | TIDE EVO SB DETRGNT TILES | 6:4 |
| 3:2 | 030772171080 | TIDE PODS SPR MDW DTRGNT | 4:2 |
| 3:4 | 030772171325 | TIDE PWR PODS OXI BOOST | 4:4 |
| 2:5 | 030772076828 | TIDE PWR PD FBZ ODR ELMNT | Section 2, 2:1 |

### Shelf scores on the scan record

| Measure | Value |
|---|---|
| Detections | 38 |
| Price tags | 29 |
| Correct in section | 5 |
| Wandering | 25 |
| Missing | 9 |
| On-shelf availability | 72.7% |
| Facing compliance | 97.6% |
| Compliance before actions | 42.4% |
| Sequence compliance | 100% |
| Compliance after the actions were accepted | 100% |

Report actions on the processing payload: 30 moves and 9 restocks, all `STATE_ACCEPTED`. Of the moves, 28 are Add Item and 2 are Fixed Item. Eighteen of the Add Item moves have the same source and destination.

### All sections of this visit

Same store, planogram, and date. Each section has one pre-photo and one post-photo scan. A same-slot action means the UPC is detected in its planogram slot and the backend still emits `ACTION_MOVE` from that slot to the same slot. On pre-photo, 31 of those actions are Add Item and 1 is Fixed Item (section 5, slot 2:4). On post-photo, all 31 are Add Item. Restocks of a UPC that is not detected are excluded because those are real holes. Counts are unique product slots.

| Section | Pre scan | Post scan | Pre actions | Post actions | Same-slot actions on pre | Same-slot actions on post | Repeated on post | Ok on the wrong slot (pre) |
|---|---|---|---|---|---|---|---|---|
| 1 | 17773117 | 17780691 | 39 | 37 | 15 | 19 | 12 | 6 |
| 2 | 17773121 | 17780693 | 8 | 6 | 0 | 0 | 0 | 5 |
| 3 | 17773129 | 17780706 | 40 | 40 | 7 | 1 | 1 | 4 |
| 4 | 17773128 | 17780713 | 18 | 15 | 0 | 0 | 0 | 14 |
| 5 | 17773135 | 17780721 | 43 | 41 | 6 | 7 | 5 | 3 |
| 6 | 17773134 | 17780722 | 16 | 10 | 0 | 0 | 0 | 9 |
| 7 | 17773141 | 17780727 | 30 | 32 | 4 | 4 | 2 | 4 |
| **Total** | | | **194** | **181** | **32** | **31** | **20** | **45** |

Sections 2, 4, and 6 mostly use `Moved Item` actions between different slots and have no same-slot set-aside. Sections 1, 3, 5, and 7 use `Add Item` heavily, and that is where the same-slot set-asides appear.

#### Section 1 products asked to set aside again after they were corrected

On pre-photo these products were in the wrong slot and got a valid set-aside to their planogram slot. On post-photo each one is in its planogram slot and is asked to set aside again from that slot to the same slot.

| Section | Slot | UPC | Product | Post-photo |
|---|---|---|---|---|
| 1 | 2:3 | 030772118054 | TIDE DOWNY SB PWR PODS FS | `2:3 → 2:3` Add Item |
| 1 | 2:4 | 030772171332 | TIDE POWER PODS OXI BOOST | `2:4 → 2:4` Add Item |
| 1 | 6:1 | 030772093856 | TIDE EVO ORGNL SCENT DTRG | `6:1 → 6:1` Add Item |
| 1 | 6:2 | 030772093887 | TIDE EVO SPRNG BLAST DTRG | `6:2 → 6:2` Add Item |
| 1 | 6:4 | 030772093900 | TIDE EVO SB DETRGNT TILES | `6:4 → 6:4` Add Item |
| 1 | 6:5 | 030772244661 | TIDE LND DTR 2X LS ORIG | `6:5 → 6:5` Add Item |
| 1 | 6:6 | 030772244678 | TIDE LND DTR 6X HE SPR MD | `6:6 → 6:6` Add Item |

Twelve of the 15 unnecessary section 1 set-asides listed above are repeated on post-photo: 1:1, 1:2, 1:3, 2:1, 2:2, 3:1, 3:3, 3:5, 4:1, 4:2, 4:3, and 6:3.

#### Same-slot set-asides in sections 3, 5, and 7

| Section | Slot | UPC | Product | Pre-photo | Post-photo |
|---|---|---|---|---|---|
| 3 | 4:1 | 030772175262 | TIDE HGH SD ORG HD HYG DT | `4:1 → 4:1` Add Item | — |
| 3 | 4:3 | 030772235843 | TIDE FC UNSC LIQ DTRGNT | `4:3 → 4:3` Add Item | — |
| 3 | 4:4 | 850078565013 | ETH BRZ FRG FREE SHTS | `4:4 → 4:4` Add Item | — |
| 3 | 5:3 | 030772171059 | TIDE PODS FG UNSC DTRG | `5:3 → 5:3` Add Item | `5:3 → 5:3` Add Item |
| 3 | 6:3 | 030772247549 | TIDE FC DETERGENT PODS | `6:3 → 6:3` Add Item | — |
| 3 | 6:4 | 732913447053 | SVNG FC LQD DTRGNT U/C | `6:4 → 6:4` Add Item | — |
| 3 | 6:5 | 732913453016 | SVNG FC LNDR DTRG SHTS | `6:5 → 6:5` Add Item | — |
| 5 | 2:4 | 030772226254 | GAIN LND DTR 2X HS DWDRP | `2:4 → 2:4` Fixed Item | `2:4 → 2:4` Add Item |
| 5 | 3:2 | 030772289853 | GAIN MNLGHT BRZ DTRGNT | — | `3:2 → 3:2` Add Item |
| 5 | 3:3 | 030772289822 | GAIN WTRFULL LIQ DTRGN | — | `3:3 → 3:3` Add Item |
| 5 | 5:3 | 072613474158 | ALL FREECLR HE LND DTRG | `5:3 → 5:3` Add Item | — |
| 5 | 6:1 | 030772247839 | GAIN LNDR DTRGNT FLINGS | `6:1 → 6:1` Add Item | `6:1 → 6:1` Add Item |
| 5 | 6:2 | 030772247846 | GAIN FLINGS 2X MNLT BRZ | `6:2 → 6:2` Add Item | `6:2 → 6:2` Add Item |
| 5 | 6:3 | 030772247655 | GAIN ARMBST DTRGNT | `6:3 → 6:3` Add Item | `6:3 → 6:3` Add Item |
| 5 | 6:4 | 030772247617 | GAIN MNLT BRZ LIQ DTRGNT | `6:4 → 6:4` Add Item | `6:4 → 6:4` Add Item |
| 7 | 1:3 | 033200065104 | AHMR W/OXI FRSH SCNT PWDR | `1:3 → 1:3` Add Item | — |
| 7 | 1:4 | 037000945994 | ARIEL2X LNDRY DTRG POWDER | `1:4 → 1:4` Add Item | — |
| 7 | 2:1 | 033200300038 | AHMR LNDR DTRGNT OXI CLN | `2:1 → 2:1` Add Item | `2:1 → 2:1` Add Item |
| 7 | 3:1 | 033200178224 | AHMR LNDR DTRGNT OXI CLN | — | `3:1 → 3:1` Add Item |
| 7 | 3:2 | 024200056872 | PUREX ADVANCED OXI | — | `3:2 → 3:2` Add Item |
| 7 | 6:4 | 033200001713 | AHMR ORDR BLSTRS TRPL CBR | `6:4 → 6:4` Add Item | `6:4 → 6:4` Add Item |

#### Products marked ok in the wrong slot in sections 2–7

Pre-photo, `action_type` `ACTION_CORRECT`, and the present UPC differs from the planogram UPC for that slot. Section 1 is in the table [Misplaced products that got no action](#misplaced-products-that-got-no-action).

| Section | Seen at | UPC present | Planogram UPC for that slot | Present UPC belongs at |
|---|---|---|---|---|
| 2 | 2:1 | 030772190425 TIDE LN DET 2X LS ODR OXI | 030772076828 TIDE PWR PD FBZ ODR ELMNT | 2:2 |
| 2 | 2:2 | 030772175347 TIDE OXI ODOR REMVR | 030772190425 TIDE LN DET 2X LS ODR OXI | 2:3 |
| 2 | 2:3 | 030772175316 TIDE SPORT/FEBRZ LIQ DTRG | 030772175347 TIDE OXI ODOR REMVR | 2:4 |
| 2 | 4:2 | 030772175385 TIDE ULTR OXI DETRGMT LQ | 030772175330 TIDE HYGENIC FABRIC CLNR | 4:1 |
| 2 | 6:4 | 030772244630 TIDE DWNY LS LIQ DTRGNT | 030772218624 TIDE LN DT EVO FR GNT TLS | 6:1 |
| 3 | 1:1 | 030772172926 TIDE 2X LOW SDS SPR MDW | 030772172933 TIDE LN DET 2X LS SPR MDW | Section 2, 1:4 |
| 3 | 3:1 | 030772175309 TIDE LNDRY DTRGNT FRSHNS | 030772175323 TIDE DOWNY APRIL FRESH | Section 2, 3:3 |
| 3 | 3:5 | 030772235843 TIDE FC UNSC LIQ DTRGNT | 030772121412 TIDE LW SDS HE SCNT FR DT | 4:3 |
| 3 | 4:2 | 030772171059 TIDE PODS FG UNSC DTRG | 030772094884 TIDE PDS FREE GNTL DTRGNT | 5:3 |
| 4 | 1:5 | 030772289891 GAIN PLUS 2X HS HE ORIGNL | 024200054670 PERSIL PROCLN INTNSE FRSH | 1:6 |
| 4 | 3:2 | 749174098894 ECOS FREE CLEAR DETERGENT | 749174098917 ECOS 2X ULTRA LAV LND DTG | 3:1 |
| 4 | 3:3 | 749174098917 ECOS 2X ULTRA LAV LND DTG | 024200054960 PERSIL ORIGINAL | 3:2 |
| 4 | 3:4 | 024200054960 PERSIL ORIGINAL | 024200054489 PERSIL PROCLN ORIG SCENT | 3:3 |
| 4 | 3:5 | 024200054489 PERSIL PROCLN ORIG SCENT | 037000488484 GAIN FLNGS 3IN1 OB FBZ MB | 3:4 |
| 4 | 4:1 | 033200003663 AHMR FB LAUNDRY SHEETS | 033200003670 AHMR FF LAUNDRY SHEETS | 4:2 |
| 4 | 4:2 | 024200054823 PERSIL CC UP LNDRY DTRGT | 033200003663 AHMR FB LAUNDRY SHEETS | 4:3 |
| 4 | 4:4 | 030772226261 GAIN LIQUID ORIGINAL | 037000488538 GAIN FLINGS ORIG SCENT | 4:5 |
| 4 | 5:4 | 024200055141 PERSIL ORIGINAL ULTRA PAC | 030772092071 GAIN FLXG OXI BST DTRGNT | 5:2 |
| 4 | 5:5 | 024200053567 PERSIL INT FRSH UP LN DTR | 030772231548 GAIN PLUS DETERGNT FLINGS | 5:3 |
| 4 | 6:2 | 749174095374 ECOS NL LNDR DTRGNT FC | 883049287256 AFRS WASHER CLEANER | 6:1 |
| 4 | 6:3 | 883049287256 AFRS WASHER CLEANER | 814521012257 TIDE WASHING MACHIN CLRN | 6:2 |
| 4 | 6:4 | 814521012257 TIDE WASHING MACHIN CLRN | 024200057664 PERSIL PROCLEAN OXI | 6:3 |
| 4 | 6:5 | 024200057664 PERSIL PROCLEAN OXI | 024200057602 PERSIL PROCLN OXI DISCS | 6:4 |
| 5 | 1:1 | 030772289891 GAIN PLUS 2X HS HE ORIGNL | 030772225936 GAIN DETERGENT ORIGINAL | Section 4, 1:6 |
| 5 | 4:1 | 030772226261 GAIN LIQUID ORIGINAL | 030772226247 GAIN LIQ MNLT BRZ DTRGNT | Section 4, 4:5 |
| 5 | 5:1 | 030772231548 GAIN PLUS DETERGNT FLINGS | 030772289877 GAIN PLUS LIQ LND DTRGNT | Section 4, 5:5 |
| 6 | 1:3 | 033200070085 AHMR SNSTV SKN LIQUID | 033200002673 AHMR SNTV SKN LNDRY DTG | 1:2 |
| 6 | 1:4 | 033200002673 AHMR SNTV SKN LNDRY DTG | 033200002680 AHMR FREE CLR LNDRY DTR | 1:3 |
| 6 | 2:3 | 033200004271 EHMR LNDR DTRGNT PWR CLN | 033200977339 AHMR BK SODA FRSH DTRG | 2:2 |
| 6 | 2:4 | 033200977339 AHMR BK SODA FRSH DTRG | 033200300021 AHMR LNDR DTRGNT OXI CLN | 2:3 |
| 6 | 5:2 | 033200997481 AHMR DTRGNT OXI CLN FRE | 033200003991 AHMR LNDR DTRGNT OXI CLN | 5:1 |
| 6 | 5:3 | 033200003991 AHMR LNDR DTRGNT OXI CLN | 033200178217 AHMR PLUS OXICLN DETERGNT | 5:2 |
| 6 | 6:3 | 072613475087 ALL FREE CLEAR MIGHTY PAC | 072613739813 ALL STAINLIFTR MP FC OXI | 6:1 |
| 6 | 6:4 | 072613739783 ALL MIGHTYPAC FR CLR DTRG | 072613739776 ALL 19CT SDL FREE CLEAR | 6:2 |
| 6 | 6:5 | 072613739813 ALL STAINLIFTR MP FC OXI | 033200977193 AHMR DP CLN STN FRML PK | 6:3 |
| 7 | 1:1 | 033200002680 AHMR FREE CLR LNDRY DTR | 033200002819 AHMR LNDR DTRGNT SEN SKIN | Section 6, 1:4 |
| 7 | 4:1 | 033200178231 AHMR OXI CLN LNDRY DTRGNT | 094514002162 XTRA CALYPSO FRESH DTRGNT | 5:2 |
| 7 | 5:1 | 033200004264 AHMR LNDR DTRGNT MEGA VAL | 033200977346 AHMR LND DTR BK SDA FRSH | Section 6, 5:4 |
| 7 | 6:1 | 033200977193 AHMR DP CLN STN FRML PK | 033200942122 AHMR UNT DS OXCLN TRPL LQ | Section 6, 6:5 |

Sections 4 and 6 show the shelf-shift pattern from Finding 1: each product sits one slot away from its planogram slot on the same shelf, and each one is still marked ok.

### Sources for finding 2

- `GET /api/v4/processing/actions/?store=5347&planogram=1216760&date=2026-10-06` for the 14 pre-photo and post-photo scans of this visit
- `GET /api/v4/processing/actions/{scan_id}/` for each of those scans
- `GET /api/v4/processing/actions/17773117/` for realogram products and report actions
- `GET /api/v1/planograms/1216760/items/` for shelf and position in sections 1–7
- `GET /api/v4/products/{id}/` for the planogram UPC of each product
- `GET /api/v1/reporting/R07/section-product-reports/?scan_id=17773117` for the 23 Add Item rows

## Finding 3 — Scan 17806323: post-photo actions on products already in the correct slot

Opened scan: [17806323](https://krcs.rebotics.net/reporting/scans/17806323?store=5346&category=830&planogram=1217193&date=2026-10-07)

| Field | Value |
|---|---|
| Store | 024-00785 Test (5346) |
| Category | 104-LAUNDRY DETERGENTS (830) |
| Planogram | 104-LAUNDRY DETERGENTS 906 (1217193) |
| Opened scan | Section 1, pre-photo, captured 2026-10-07 11:17 UTC |
| Compared | Pre-photo and post-photo for sections 1 through 10 |

### Finding

The opened scan is only section 1’s pre-photo. That section is already in good shape: 35 of 36 detections are `ACTION_CORRECT`, and the only pre-photo action is one restock. Its post-photo (`17808650`) does **not** generate moves for those corrected products. It adds two restocks, and both UPCs are absent from the post-photo, so they are holes rather than products already sitting in the right slot.

The problem is on the other sections of the same planogram and the same day. Post-photo processing generated **209 actions** across sections 1–10. **38 of those actions are for a UPC that is already detected in its planogram slot, and the move is `slot → same slot`.** 37 are Add Item and 1 is Fixed Item. They cover **25 product slots** in sections 2, 4, 6, and 8. **32 of those 38 action rows, covering 19 of the 25 slots, were already the same move on the pre-photo.** Six slots appear for the first time on the post-photo: section 2 slot 4:2, section 4 slot 2:5, and section 6 slots 6:4, 6:5, 6:6, and 6:7. Those products are ok by UPC and position, and the associate is still asked to act on the same slot.

The other 27 same-slot rows are restocks of a UPC that the post-photo does not detect. Those are missing-product restocks, not actions on an ok product. Sections 3, 5, 7, 9, and 10 do not have this same-slot Add Item defect. Their post-photo actions are moves to a different slot, or restocks of a product that is not on the shelf.

### Root cause

Post-photo processing classifies the new photo on its own. When the detected UPC is already the planogram UPC for that slot, it still writes `ACTION_MOVE`, reason `Add Item`, with `from` equal to `to`, and `state` `STATE_ACCEPTED`. It does not change that product to `ACTION_CORRECT`. The associate flow is again set-aside, then place on the same slot.

Section 2 post-photo `17808655`, shelf 6, is a one-facing case. Planogram 6:2 is `033200977193`. The photo shows that UPC at 6:2. The action is `ACTION_MOVE` / `Add Item` / `6:2 → 6:2`, with `from_shelf` 6 and `from_position_unique` 2. Positions 6:1 through 6:5 match the same way. On that same photo, `033200003984` at 2:1 is `ACTION_CORRECT` and has no action. The matcher can mark a matched slot as correct, and on these rows it marked a matched slot as a move.

A multi-facing group makes the same slot repeat. Section 2 shelf 3 position 1 allows 5 facings of `033200003984`. The photo has 6 facings. All 6 are anchored on `3:1`: `from` and `to` are both `3:1`, while `from_position_unique` runs from 1 to 6. Each facing is a separate `Add Item` for the same displayed slot. The pre-photo had already classified these products as `ACTION_MOVE`, and the post-photo produced the same accepted move again.

### Unnecessary post-photo actions

The detected UPC matches the planogram UPC for that slot. Source and destination are the same. Thirty-two of these action rows were already `ACTION_MOVE` on the pre-photo. The six slots named above are new on the post-photo.

| Section | Slot | UPC | Product | Post-photo action | Facings |
|---|---|---|---|---|---|
| 2 | 6:1 | 033200942122 | AHMR UNT DS OXCLN TRPL LQ | Add Item 6:1 → 6:1 | 1 |
| 2 | 6:2 | 033200977193 | AHMR DP CLN STN FRML PK | Add Item 6:2 → 6:2 | 1 |
| 2 | 6:3 | 033200977186 | AHMR DP CLN ODR PK FRMLA | Add Item 6:3 → 6:3 | 1 |
| 2 | 6:4 | 033200977162 | AHMR DP CLN FREE CLEAR | Add Item 6:4 → 6:4 | 1 |
| 2 | 6:5 | 072613739813 | ALL STAINLIFTR MP FC OXI | Add Item 6:5 → 6:5 | 1 |
| 2 | 5:1 | 033200004264 | AHMR LNDR DTRGNT MEGA VAL | Add Item 5:1 → 5:1 | 2 |
| 2 | 4:2 | 033200977346 | AHMR LND DTR BK SDA FRSH | Fixed Item 4:2 → 4:2 | 1 |
| 2 | 3:2 | 033200977155 | AHMR DP CLN ODR FRMLA | Add Item 3:2 → 3:2 | 1 |
| 2 | 3:1 | 033200003984 | AHMR OXI CLN LNDRY DTRGNT | Add Item 3:1 → 3:1 | 6 |
| 4 | 6:1 | 072613475087 | ALL FREE CLEAR MIGHTY PAC | Add Item 6:1 → 6:1 | 2 |
| 4 | 6:2 | 030772247662 | GAIN LND DTR HE 2X WF DL | Add Item 6:2 → 6:2 | 2 |
| 4 | 6:3 | 030772247617 | GAIN MNLT BRZ LIQ DTRGNT | Add Item 6:3 → 6:3 | 1 |
| 4 | 6:4 | 030772247655 | GAIN ARMBST DTRGNT | Add Item 6:4 → 6:4 | 1 |
| 4 | 2:2 | 030772226131 | GAIN LIQ WTRFL DLT DTRGNT | Add Item 2:2 → 2:2 | 1 |
| 4 | 2:3 | 030772226254 | GAIN LND DTR 2X HS DWDRP | Add Item 2:3 → 2:3 | 1 |
| 4 | 2:5 | 030772226339 | GAIN DTRGNT 2X MNLGHT BRZ | Add Item 2:5 → 2:5 | 1 |
| 6 | 6:2 | 024200057664 | PERSIL PROCLEAN OXI | Add Item 6:2 → 6:2 | 3 |
| 6 | 6:3 | 814521012257 | TIDE WASHING MACHIN CLRN | Add Item 6:3 → 6:3 | 1 |
| 6 | 6:4 | 883049287256 | AFRS WASHER CLEANER | Add Item 6:4 → 6:4 | 1 |
| 6 | 6:5 | 749174095374 | ECOS NL LNDR DTRGNT FC | Add Item 6:5 → 6:5 | 1 |
| 6 | 6:6 | 732913453023 | SVNG LVND LNDR DTRG SHTS | Add Item 6:6 → 6:6 | 1 |
| 6 | 6:7 | 732913453016 | SVNG FC LNDR DTRG SHTS | Add Item 6:7 → 6:7 | 1 |
| 8 | 4:1 | 030772175200 | TIDE LW SDS HE ORG OXI DT | Add Item 4:1 → 4:1 | 2 |
| 8 | 4:2 | 030772175330 | TIDE HYGENIC FABRIC CLNR | Add Item 4:2 → 4:2 | 2 |
| 8 | 4:3 | 030772175385 | TIDE ULTR OXI DETRGMT LQ | Add Item 4:3 → 4:3 | 2 |

### Post-photo action counts by section

| Section | Pre scan | Post scan | Pre actions | Post actions | Same-slot actions on an already correct UPC |
|---|---|---|---|---|---|
| 1 | 17806323 | 17808650 | 1 | 2 | 0 |
| 2 | 17806326 | 17808655 | 34 | 32 | 15 |
| 3 | 17806333 | 17808662 | 18 | 8 | 0 |
| 4 | 17806329 | 17808667 | 38 | 34 | 9 |
| 5 | 17806338 | 17808671 | 19 | 19 | 0 |
| 6 | 17806341 | 17808673 | 39 | 42 | 8 |
| 7 | 17806352 | 17808681 | 23 | 17 | 0 |
| 8 | 17806358 | 17808688 | 38 | 37 | 6 |
| 9 | 17806363 | 17808702 | 8 | 9 | 0 |
| 10 | 17806367 | 17808707 | 13 | 9 | 0 |

### Sources for finding 3

- `GET /api/v4/processing/actions/?store=5346&planogram=1217193&date=2026-10-07` for the 10 pre-photo and 10 post-photo scans
- `GET /api/v4/processing/actions/{id}/` for items and report actions on each of those scans
- `GET /api/v1/planograms/1217193/items/` for every section
- `GET /api/v4/products/{id}/` for the planogram UPC of each product
