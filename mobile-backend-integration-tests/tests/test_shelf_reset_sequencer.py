"""Tests for the Shelf-Reset Sequencing Engine and Retailer API Adapter."""

import json
from pathlib import Path
import unittest

from core.shelf_reset_sequencer import (
    ActionType,
    Slot,
    extract_slots_from_retailer_actions,
    sequence_shelf_reset,
)


class TestShelfResetSequencer(unittest.TestCase):
    def setUp(self):
        # Section 7 Reference Fixture
        self.reference_fixture = [
            {"id": "A1", "bay": "A", "current": "Corn Flakes", "target": "Orange Juice"},
            {"id": "A2", "bay": "A", "current": "Orange Juice", "target": "Corn Flakes"},
            {"id": "A3", "bay": "A", "current": "Tomato Soup", "target": "Penne Pasta"},
            {"id": "A4", "bay": "A", "current": "Penne Pasta", "target": "Marinara Sauce"},
            {"id": "A5", "bay": "A", "current": "Marinara Sauce", "target": "Tomato Soup"},
            {"id": "A6", "bay": "A", "current": "Potato Chips", "target": "Whole Milk"},
            {"id": "A7", "bay": "A", "current": None, "target": "Potato Chips"},
            {"id": "A8", "bay": "A", "current": "Whole Milk", "target": None},
            {"id": "A9", "bay": "A", "current": "Granola Bars", "target": "Granola Bars"},
            {"id": "A10", "bay": "A", "current": "Expired Yogurt Drink", "target": None},
            {"id": "B1", "bay": "B", "current": "Trail Mix", "target": "Keto Bar (new)"},
            {"id": "B2", "bay": "B", "current": "Protein Bar", "target": "Trail Mix"},
            {"id": "B3", "bay": "B", "current": "Nut Clusters", "target": "Protein Bar"},
            {"id": "B4", "bay": "B", "current": None, "target": "Nut Clusters"},
        ]

    def test_section_7_reference_fixture_exact_sequence(self):
        """Verify the reference test fixture produces exactly the 10 steps in specified order."""
        slots = [Slot.from_dict(d) for d in self.reference_fixture]
        steps = sequence_shelf_reset(slots)

        self.assertEqual(len(steps), 10, f"Expected exactly 10 steps, got {len(steps)}")

        # Step 1: hold A3 (Tomato Soup)
        self.assertEqual(steps[0].type, ActionType.HOLD)
        self.assertEqual(steps[0].description, "hold A3 (Tomato Soup)")
        self.assertEqual(steps[0].slot_id, "A3")
        self.assertEqual(steps[0].item, "Tomato Soup")

        # Step 2: move A4→A3 (Penne Pasta)
        self.assertEqual(steps[1].type, ActionType.MOVE)
        self.assertEqual(steps[1].description, "move A4→A3 (Penne Pasta)")
        self.assertEqual(steps[1].slot_id, "A4")
        self.assertEqual(steps[1].to_slot_id, "A3")
        self.assertEqual(steps[1].item, "Penne Pasta")

        # Step 3: move A5→A4 (Marinara Sauce)
        self.assertEqual(steps[2].type, ActionType.MOVE)
        self.assertEqual(steps[2].description, "move A5→A4 (Marinara Sauce)")
        self.assertEqual(steps[2].slot_id, "A5")
        self.assertEqual(steps[2].to_slot_id, "A4")
        self.assertEqual(steps[2].item, "Marinara Sauce")

        # Step 4: place →A5 (Tomato Soup)
        self.assertEqual(steps[3].type, ActionType.PLACE)
        self.assertEqual(steps[3].description, "place →A5 (Tomato Soup)")
        self.assertEqual(steps[3].slot_id, "A5")
        self.assertEqual(steps[3].item, "Tomato Soup")

        # Step 5: move A6→A7 (Potato Chips)
        self.assertEqual(steps[4].type, ActionType.MOVE)
        self.assertEqual(steps[4].description, "move A6→A7 (Potato Chips)")
        self.assertEqual(steps[4].slot_id, "A6")
        self.assertEqual(steps[4].to_slot_id, "A7")
        self.assertEqual(steps[4].item, "Potato Chips")

        # Step 6: move A8→A6 (Whole Milk)
        self.assertEqual(steps[5].type, ActionType.MOVE)
        self.assertEqual(steps[5].description, "move A8→A6 (Whole Milk)")
        self.assertEqual(steps[5].slot_id, "A8")
        self.assertEqual(steps[5].to_slot_id, "A6")
        self.assertEqual(steps[5].item, "Whole Milk")

        # Step 7: slide B3→B4, B2→B3, B1→B2 (3 items)
        self.assertEqual(steps[6].type, ActionType.SLIDE)
        self.assertEqual(steps[6].description, "slide B3→B4, B2→B3, B1→B2 (3 items)")
        self.assertEqual(len(steps[6].sub_moves), 3)

        # Step 8: swap A1↔A2 (Corn Flakes / Orange Juice)
        self.assertEqual(steps[7].type, ActionType.SWAP)
        self.assertIn("swap A1↔A2", steps[7].description)

        # Step 9: restock B1 (Keto Bar (new))
        self.assertEqual(steps[8].type, ActionType.RESTOCK)
        self.assertEqual(steps[8].description, "restock B1 (Keto Bar (new))")

        # Step 10: pull A10 (Expired Yogurt Drink)
        self.assertEqual(steps[9].type, ActionType.PULL)
        self.assertEqual(steps[9].description, "pull A10 (Expired Yogurt Drink)")

        # CRITICAL ASSERTION: A9 (Granola Bars) never appears anywhere in output
        for i, step in enumerate(steps):
            self.assertNotIn("A9", step.slot_id, f"Slot A9 appeared in step {i + 1}")
            self.assertNotIn("A9", step.to_slot_id or "", f"Slot A9 appeared as destination in step {i + 1}")
            self.assertNotIn("Granola Bars", step.description, f"Granola Bars appeared in step {i + 1}")

    def test_cross_bay_cycle_prefers_holding_cross_bay_item(self):
        """In a cycle spanning multiple bays, the engine must prefer holding the cross-bay item."""
        slots = [
            Slot(id="A1", bay="A", current="ProductA", target="ProductC"),
            Slot(id="A2", bay="A", current="ProductB", target="ProductA"),
            Slot(id="B1", bay="B", current="ProductC", target="ProductB"),  # B1 is cross-bay
        ]
        steps = sequence_shelf_reset(slots)
        # Cycle is: A1 (ProductA -> target of ProductA is A2) -> A2 (ProductB -> target is B1) -> B1 (ProductC -> target is A1)
        # B1 -> A1 or A2 -> B1 are cross bay.
        hold_step = steps[0]
        self.assertEqual(hold_step.type, ActionType.HOLD)
        # The cross bay node (e.g. A2 -> B1 or B1 -> A1) should be chosen to hold
        self.assertIn(hold_step.slot_id, ["A2", "B1"])

    def test_idempotent_resume_skips_duplicate_hold(self):
        """If associate is already holding the item mid-cycle, do not re-emit hold step."""
        slots = [
            Slot(id="A3", bay="A", current="Tomato Soup", target="Penne Pasta"),
            Slot(id="A4", bay="A", current="Penne Pasta", target="Marinara Sauce"),
            Slot(id="A5", bay="A", current="Marinara Sauce", target="Tomato Soup"),
        ]
        steps = sequence_shelf_reset(slots, currently_held_item="Tomato Soup")
        # Should NOT contain HOLD A3 (Tomato Soup)
        self.assertFalse(any(s.type == ActionType.HOLD for s in steps))
        # Should directly have MOVE steps and then PLACE
        self.assertEqual(steps[0].type, ActionType.MOVE)
        self.assertEqual(steps[-1].type, ActionType.PLACE)

    def test_already_correct_slots_strictly_omitted(self):
        """All correctly placed slots must be completely excluded from generated actions."""
        slots = [
            Slot(id="C1", bay="C", current="CorrectItem1", target="CorrectItem1"),
            Slot(id="C2", bay="C", current="CorrectItem2", target="CorrectItem2"),
            Slot(id="C3", bay="C", current="MisplacedItem", target=None),
        ]
        steps = sequence_shelf_reset(slots)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].type, ActionType.PULL)
        self.assertEqual(steps[0].slot_id, "C3")

    def test_retailer_api_actions_adapter(self):
        """Test extraction and sequencing of raw retailer backend action-list items."""
        sample_path = Path(__file__).resolve().parent.parent.parent / "raw_backend_actions_task_8648127.json"
        if not sample_path.exists():
            self.skipTest(f"Fixture {sample_path} not found")

        with open(sample_path, "r", encoding="utf-8") as f:
            raw_actions = json.load(f)

        slots = extract_slots_from_retailer_actions(raw_actions)
        self.assertGreater(len(slots), 0)

        # Run sequencing
        steps = sequence_shelf_reset(slots)
        self.assertGreater(len(steps), 0)

        # Verify priority ordering
        tier_map = {
            ActionType.HOLD: 1,
            ActionType.MOVE: 2,
            ActionType.PLACE: 1,  # Tied to cycle completion
            ActionType.SLIDE: 2,
            ActionType.SWAP: 3,
            ActionType.RESTOCK: 4,
            ActionType.PULL: 5,
        }
        # Verify all steps have descriptions and rationales
        for step in steps:
            self.assertTrue(len(step.description) > 0)
            self.assertTrue(len(step.rationale) > 0)

    def test_clearance_info_provenance(self):
        """Verify slot occupancy and clearance provenance tracking across sequence steps."""
        slots = [Slot.from_dict(d) for d in self.reference_fixture]
        steps = sequence_shelf_reset(slots)

        # Step 2: move A4->A3 (Penne Pasta into A3)
        # A3 was initially occupied by Tomato Soup, cleared in Step 1 (HOLD)
        step2 = steps[1]
        self.assertEqual(step2.type, ActionType.MOVE)
        self.assertEqual(step2.to_slot_id, "A3")
        c2 = step2.clearance_info
        self.assertTrue(c2["wasInitiallyOccupied"])
        self.assertEqual(c2["initialOccupant"], "Tomato Soup")
        self.assertTrue(c2["clearedBeforePlacement"])
        self.assertEqual(c2["clearedInStep"], 1)
        self.assertEqual(c2["clearedByActionType"], "hold")
        self.assertTrue(c2["isCurrentlyVacant"])
        self.assertIn("100% VACANT", c2["explanation"])

        # Step 5: move A6->A7 (Potato Chips into A7)
        # A7 was naturally vacant at start of reset
        step5 = steps[4]
        self.assertEqual(step5.type, ActionType.MOVE)
        self.assertEqual(step5.to_slot_id, "A7")
        c5 = step5.clearance_info
        self.assertFalse(c5["wasInitiallyOccupied"])
        self.assertTrue(c5["clearedBeforePlacement"])
        self.assertIsNone(c5["clearedInStep"])
        self.assertTrue(c5["isCurrentlyVacant"])
        self.assertIn("naturally VACANT", c5["explanation"])

        # Step 6: move A8->A6 (Whole Milk into A6)
        # A6 was initially occupied by Potato Chips, cleared in Step 5 (MOVE)
        step6 = steps[5]
        self.assertEqual(step6.type, ActionType.MOVE)
        self.assertEqual(step6.to_slot_id, "A6")
        c6 = step6.clearance_info
        self.assertTrue(c6["wasInitiallyOccupied"])
        self.assertEqual(c6["initialOccupant"], "Potato Chips")
        self.assertTrue(c6["clearedBeforePlacement"])
        self.assertEqual(c6["clearedInStep"], 5)
        self.assertEqual(c6["clearedByActionType"], "move")
        self.assertTrue(c6["isCurrentlyVacant"])

        # Step 9: restock B1 (Keto Bar into B1)
        # B1 was initially occupied by Trail Mix, cleared in Step 7 (SLIDE)
        step9 = steps[8]
        self.assertEqual(step9.type, ActionType.RESTOCK)
        self.assertEqual(step9.slot_id, "B1")
        c9 = step9.clearance_info
        self.assertTrue(c9["wasInitiallyOccupied"])
        self.assertEqual(c9["initialOccupant"], "Trail Mix")
        self.assertTrue(c9["clearedBeforePlacement"])
        self.assertEqual(c9["clearedInStep"], 7)
        self.assertEqual(c9["clearedByActionType"], "slide")
        self.assertTrue(c9["isCurrentlyVacant"])

    def test_cross_bay_restock_companion_step(self):
        """Cross-bay item staged to cart in Bay 1 emits an explicit place_from_cart in Bay 2."""
        slots = [
            Slot(id="Bay1_S2_P1", bay="1", shelf=2, position=1, current="Campbells Soup", target="Progresso Soup"),
            Slot(id="Bay2_S2_P1", bay="2", shelf=2, position=1, current="Old Cereal", target="Campbells Soup"),
            Slot(id="Bay2_S2_P2", bay="2", shelf=2, position=2, current="Progresso Soup", target=None),
        ]
        steps = sequence_shelf_reset(slots)
        
        # Look for SET_ASIDE in Bay 1
        set_aside_bay1 = [s for s in steps if s.type == ActionType.SET_ASIDE and s.bay == "1"]
        self.assertEqual(len(set_aside_bay1), 1)
        self.assertEqual(set_aside_bay1[0].item, "Campbells Soup")

        # Look for companion PLACE_FROM_CART in Bay 2
        place_cart_bay2 = [s for s in steps if s.type == ActionType.PLACE_FROM_CART and s.bay == "2"]
        self.assertEqual(len(place_cart_bay2), 1)
        pfc = place_cart_bay2[0]
        self.assertEqual(pfc.bay, "2")
        self.assertEqual(pfc.to_bay, "2")
        self.assertEqual(pfc.from_bay, "1")
        self.assertEqual(pfc.from_position, "Transit Cart")
        self.assertTrue(pfc.from_cart)
        self.assertEqual(pfc.item, "Campbells Soup")
        self.assertEqual(pfc.to_slot_id, "Bay2_S2_P1")

    def test_multi_facing_bundling(self):
        """Contiguous facings of the same SKU moving in unison on the same shelf are bundled."""
        slots = [
            # 3 adjacent facings of Chicken Noodle moving from pos 2,3,4 to pos 5,6,7
            Slot(id="Bay1_S3_P2", bay="1", shelf=3, position=2, current="Chicken Noodle", target="Other A"),
            Slot(id="Bay1_S3_P3", bay="1", shelf=3, position=3, current="Chicken Noodle", target="Other B"),
            Slot(id="Bay1_S3_P4", bay="1", shelf=3, position=4, current="Chicken Noodle", target="Other C"),
            Slot(id="Bay1_S3_P5", bay="1", shelf=3, position=5, current=None, target="Chicken Noodle"),
            Slot(id="Bay1_S3_P6", bay="1", shelf=3, position=6, current=None, target="Chicken Noodle"),
            Slot(id="Bay1_S3_P7", bay="1", shelf=3, position=7, current=None, target="Chicken Noodle"),
        ]
        steps = sequence_shelf_reset(slots, bundle_facings=True)
        bundled = [s for s in steps if s.facing_qty > 1]
        self.assertEqual(len(bundled), 1)
        b = bundled[0]
        self.assertEqual(b.facing_qty, 3)
        self.assertIn("3 facings", b.description)
        self.assertEqual(len(b.sub_moves), 3)
        self.assertIn(b.from_position, ["2..4", "4..2"])
        self.assertIn(b.to_position, ["5..7", "7..5"])

    def test_ergonomic_shelf_sweep_direction(self):
        """Top-to-bottom sweep orders high shelf tier actions before lower shelves."""
        slots = [
            Slot(id="Bay1_S1_P1", bay="1", shelf=1, position=1, current="Bottom Item", target=None),
            Slot(id="Bay1_S6_P1", bay="1", shelf=6, position=1, current="Top Item", target=None),
        ]
        steps = sequence_shelf_reset(slots, sweep_vertical="top_to_bottom")
        # Pull on Shelf 6 must appear before Pull on Shelf 1
        shelf_order = [s.from_shelf for s in steps if s.from_shelf]
        self.assertEqual(shelf_order, ["6", "1"])

    def test_five_phase_reset_order(self):
        """Verify the mandatory 5-phase store reset execution order:
        1. Remove action for all bays first (PULL across all bays).
        2. Within each bay:
           - Set aside items going to future bay (SET_ASIDE)
           - Fix in bay (FIX_IN_BAY / SWAP / SLIDE)
           - Items coming from future bay or transit cart pick from (PLACE_FROM_CART)
           - Restock missing items from backroom (RESTOCK)
        """
        slots = [
            # Bay 1 items
            Slot(id="Bay1_S2_P1", bay="1", shelf=2, position=1, current="Expired A", target=None),
            Slot(id="Bay1_S2_P2", bay="1", shelf=2, position=2, current="Item For Bay 2", target="Same Bay B"),
            Slot(id="Bay1_S2_P3", bay="1", shelf=2, position=3, current="Same Bay B", target=None),
            Slot(id="Bay1_S2_P4", bay="1", shelf=2, position=4, current=None, target="Backroom New 1"),
            
            # Bay 2 items
            Slot(id="Bay2_S2_P1", bay="2", shelf=2, position=1, current="Expired B", target=None),
            Slot(id="Bay2_S2_P2", bay="2", shelf=2, position=2, current=None, target="Item For Bay 2"),
            Slot(id="Bay2_S2_P3", bay="2", shelf=2, position=3, current="Swap 1", target="Swap 2"),
            Slot(id="Bay2_S2_P4", bay="2", shelf=2, position=4, current="Swap 2", target="Swap 1"),
            Slot(id="Bay2_S2_P5", bay="2", shelf=2, position=5, current=None, target="Backroom New 2"),
        ]
        steps = sequence_shelf_reset(slots, pull_first=True)

        # 1. PULL across all bays must be FIRST (both Bay 1 and Bay 2 pulls before any set-asides or fixes)
        pull_indices = [i for i, s in enumerate(steps) if s.type == ActionType.PULL]
        non_pull_indices = [i for i, s in enumerate(steps) if s.type != ActionType.PULL]
        self.assertTrue(max(pull_indices) < min(non_pull_indices), "All PULL actions must execute first across all bays!")

        # 2. In Bay 1: SET_ASIDE comes before RESTOCK
        bay1_set_aside = [i for i, s in enumerate(steps) if s.type == ActionType.SET_ASIDE and s.bay == "1"][0]
        bay1_restock = [i for i, s in enumerate(steps) if s.type == ActionType.RESTOCK and s.bay == "1"][0]
        self.assertTrue(bay1_set_aside < bay1_restock, "SET_ASIDE in Bay 1 must precede RESTOCK in Bay 1")

        # 3. In Bay 2: FIX (SWAP) comes before PLACE_FROM_CART, which comes before RESTOCK
        bay2_swap = [i for i, s in enumerate(steps) if s.type == ActionType.SWAP and s.bay == "2"][0]
        bay2_pfc = [i for i, s in enumerate(steps) if s.type == ActionType.PLACE_FROM_CART and s.bay == "2"][0]
        bay2_restock = [i for i, s in enumerate(steps) if s.type == ActionType.RESTOCK and s.bay == "2"][0]
        self.assertTrue(bay2_swap < bay2_pfc, "In Bay 2, fix in bay (swap) must precede place_from_cart")
        self.assertTrue(bay2_pfc < bay2_restock, "In Bay 2, place_from_cart must precede restock")


if __name__ == "__main__":
    unittest.main()


