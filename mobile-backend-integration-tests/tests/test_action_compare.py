import unittest

from core.action_compare import compare_actions


def generated(scan_id, upc, action_type, position="1:1"):
    return {
        "scan_id": scan_id,
        "upc": upc,
        "product_title": f"Generated {upc}",
        "action_type": action_type,
        "position": position,
    }


def digital(scan_id, upc, action_type, action_taken, position="1:1"):
    return {
        "scan_id": scan_id,
        "upc": upc,
        "product_name": f"Digital {upc}",
        "action_type": action_type,
        "action_taken": action_taken,
        "pog_position": position,
    }


class TestActionCompare(unittest.TestCase):
    def test_classifies_match_and_mismatch_by_scan_id_and_upc(self):
        result = compare_actions(
            [
                generated(7, "111", "REMOVE"),
                generated(7, "222", "SET_ASIDE"),
            ],
            [
                digital(7, "111", "remove", "remove"),
                digital(7, "222", "ok", "-"),
            ],
            execution_compliance_pct=100.0,
        )

        self.assertEqual([row.status for row in result.rows], ["MATCH", "MISMATCH"])
        self.assertEqual(result.counts["matched"], 1)
        self.assertEqual(result.counts["mismatched"], 1)
        self.assertEqual(result.digital_alignment_pct, 50.0)
        self.assertEqual(result.combined_compliance_pct, 50.0)

    def test_live_digital_reasons_match_their_ir_action_types(self):
        pick = generated(7, "666", "SET_ASIDE")
        place = generated(7, "666", "ADD_TO_SHELF")
        pick["source_action_id"] = 666
        place["source_action_id"] = 666
        result = compare_actions(
            [
                generated(7, "111", "FIX_IN_BAY"),
                generated(7, "222", "RESTOCK"),
                generated(7, "333", "REMOVE"),
                generated(7, "444", "ADD_TO_SHELF"),
                generated(7, "555", "SET_ASIDE"),
                pick,
                place,
            ],
            [
                digital(7, "111", "ok", "Fixed Item"),
                digital(7, "222", "oos", "Restocked Item"),
                digital(7, "333", "invader", "Removed Item"),
                digital(7, "444", "ok", "Add Item"),
                digital(7, "555", "ok", "Add Item"),
                digital(7, "666", "ok", "Moved Item"),
            ],
            execution_compliance_pct=100.0,
        )

        self.assertEqual([row.status for row in result.rows], ["MATCH"] * 7)
        self.assertEqual(result.digital_alignment_pct, 100.0)

    def test_unidentified_rows_without_upc_join_on_shelf_position(self):
        result = compare_actions(
            [
                generated(7, "", "IDENTIFY", position="1:4"),
                generated(7, "", "IDENTIFY", position="6:16"),
            ],
            [
                digital(7, "", "unidentified", "Image not Ideal to add to database", position="6:16"),
                digital(7, "", "unidentified", "Image not Ideal to add to database", position="1:4"),
            ],
            execution_compliance_pct=100.0,
        )

        self.assertEqual([row.status for row in result.rows], ["MATCH", "MATCH"])

    def test_unidentified_same_slot_different_scans_are_not_ambiguous(self):
        """Bay 1 @ 4:2 and Bay 2 @ 4:2 are different Digital Shelf rows."""
        bay1 = generated(3779208, "", "REMOVE", position="4:2")
        bay1["bay"] = "1"
        bay1["section"] = "1"
        bay2 = generated(3779211, "", "REMOVE", position="4:2")
        bay2["bay"] = "2"
        bay2["section"] = "2"

        dig1 = digital(3779208, "", "invader", "Removed Item", position="4:2")
        dig1["section"] = "1"
        dig2 = digital(3779211, "", "invader", "Removed Item", position="4:2")
        dig2["section"] = "2"

        result = compare_actions(
            [bay1, bay2],
            [dig1, dig2],
            execution_compliance_pct=100.0,
        )

        self.assertEqual([row.status for row in result.rows], ["MATCH", "MATCH"])
        self.assertEqual(result.counts["ambiguous"], 0)

    def test_two_phase_move_shares_one_digital_row(self):
        pick = generated(7, "111", "SET_ASIDE", position="2:1")
        place = generated(7, "111", "ADD_TO_SHELF", position="4:1")
        pick["source_action_id"] = 5001
        place["source_action_id"] = 5001

        result = compare_actions(
            [pick, place],
            [digital(7, "111", "ok", "Add Item", position="4:1")],
            execution_compliance_pct=100.0,
        )

        self.assertEqual([row.status for row in result.rows], ["MATCH", "MATCH"])
        self.assertEqual(result.digital_alignment_pct, 100.0)

    def test_moved_item_matches_set_aside_and_add_to_shelf(self):
        """Pick from one place + place in another = Digital 'Moved Item'."""
        pick = generated(7, "681421029100", "SET_ASIDE", position="2:1")
        place = generated(7, "681421029100", "ADD_TO_SHELF", position="4:3")
        pick["source_action_id"] = 9001
        place["source_action_id"] = 9001

        result = compare_actions(
            [pick, place],
            [digital(7, "681421029100", "ok", "Moved Item", position="4:3")],
            execution_compliance_pct=100.0,
        )

        self.assertEqual([row.status for row in result.rows], ["MATCH", "MATCH"])
        self.assertEqual(
            result.counts["matched"],
            1,
            "A two-card move is one logical generated action for scoring",
        )
        self.assertEqual(result.counts["mismatched"], 0)
        self.assertEqual(result.digital_alignment_pct, 100.0)

    def test_untouched_shelf_products_do_not_lower_the_score(self):
        result = compare_actions(
            [generated(7, "111", "REMOVE")],
            [
                digital(7, "111", "invader", "Removed Item"),
                digital(7, "222", "ok", "-"),
            ],
            execution_compliance_pct=100.0,
        )

        statuses = [row.status for row in result.rows]
        self.assertEqual(statuses, ["MATCH", "NO_ACTION_NEEDED"])
        self.assertEqual(result.counts["no_action_needed"], 1)
        self.assertEqual(result.digital_alignment_pct, 100.0)

    def test_unmatched_digital_reason_stays_mismatch(self):
        result = compare_actions(
            [generated(7, "111", "REMOVE")],
            [digital(7, "111", "ok", "Fixed Item")],
            execution_compliance_pct=100.0,
        )

        self.assertEqual(result.rows[0].status, "MISMATCH")

    def test_empty_user_action_is_mismatch_even_when_action_type_matches(self):
        result = compare_actions(
            [generated(7, "111", "REMOVE")],
            [digital(7, "111", "remove", "-")],
            execution_compliance_pct=100.0,
        )

        self.assertEqual(result.rows[0].status, "MISMATCH")
        self.assertEqual(result.digital_alignment_pct, 0.0)

    def test_numeric_and_string_scan_ids_match(self):
        result = compare_actions(
            [generated("7", "111", "REMOVE")],
            [digital(7, "111", "remove", "remove")],
            execution_compliance_pct=100.0,
        )

        self.assertEqual(result.rows[0].status, "MATCH")

    def test_classifies_generated_only_and_digital_only(self):
        result = compare_actions(
            [generated(7, "111", "REMOVE")],
            [digital(8, "222", "remove", "remove")],
            execution_compliance_pct=80.0,
        )

        self.assertEqual(
            {row.status for row in result.rows},
            {"GENERATED_ONLY", "DIGITAL_ONLY"},
        )
        self.assertEqual(result.digital_alignment_pct, 0.0)
        self.assertEqual(result.combined_compliance_pct, 0.0)

    def test_marks_duplicate_upc_without_position_match_as_ambiguous(self):
        result = compare_actions(
            [generated(7, "111", "REMOVE", position="9:9")],
            [
                digital(7, "111", "remove", "remove", position="1:1"),
                digital(7, "111", "remove", "remove", position="1:2"),
            ],
            execution_compliance_pct=100.0,
        )

        self.assertEqual(result.rows[0].status, "AMBIGUOUS")
        self.assertEqual(result.counts["ambiguous"], 1)
        self.assertEqual(result.counts["digital_only"], 0)
        self.assertEqual(len(result.rows), 1)

    def test_duplicate_upc_facings_join_by_position_not_first_unused_row(self):
        result = compare_actions(
            [
                generated(7, "111", "REMOVE", position="1:2"),
                generated(7, "111", "REMOVE", position="1:1"),
            ],
            [
                digital(7, "111", "remove", "Removed Item", position="1:1"),
                digital(7, "111", "remove", "Removed Item", position="1:2"),
            ],
            execution_compliance_pct=100.0,
        )

        self.assertEqual([row.status for row in result.rows], ["MATCH", "MATCH"])
        self.assertEqual(
            [row.digital_position for row in result.rows],
            ["1:2", "1:1"],
        )

    def test_falls_back_to_upc_and_position_when_scan_id_is_missing(self):
        result = compare_actions(
            [generated(7, "111", "REMOVE", position="2:3")],
            [digital(None, "111", "remove", "remove", position="2:3")],
            execution_compliance_pct=100.0,
        )

        self.assertEqual(result.rows[0].status, "MATCH")

    def test_fetch_failure_does_not_reduce_existing_compliance(self):
        result = compare_actions(
            [generated(7, "111", "REMOVE")],
            [],
            execution_compliance_pct=80.0,
            digital_loaded=False,
            digital_error="HTTP 401 Unauthorized",
        )

        self.assertIsNone(result.digital_alignment_pct)
        self.assertEqual(result.combined_compliance_pct, 80.0)
        self.assertEqual(result.error, "HTTP 401 Unauthorized")

    def test_partial_fetch_failure_scores_successful_scans_only(self):
        result = compare_actions(
            [
                generated(7, "111", "REMOVE"),
                generated(8, "222", "REMOVE"),
            ],
            [digital(7, "111", "remove", "remove")],
            execution_compliance_pct=90.0,
            unavailable_scan_ids=[8],
            digital_error="scan_id 8: HTTP 500",
        )

        self.assertEqual([row.status for row in result.rows], ["MATCH", "UNAVAILABLE"])
        self.assertEqual(result.digital_alignment_pct, 100.0)
        self.assertEqual(result.combined_compliance_pct, 90.0)

    def test_duplicate_facings_at_same_position_match_sequentially(self):
        result = compare_actions(
            [
                generated(7, "111", "REMOVE", position="1:3"),
                generated(7, "111", "REMOVE", position="1:3"),
            ],
            [
                digital(7, "111", "invader", "Removed Item", position="1:3"),
                digital(7, "111", "invader", "Removed Item", position="1:3"),
            ],
            execution_compliance_pct=100.0,
        )

        self.assertEqual([row.status for row in result.rows], ["MATCH", "MATCH"])
        self.assertEqual(result.counts["ambiguous"], 0)
        self.assertEqual(result.counts["matched"], 2)

    def test_extra_facing_flags_and_counts_preserved_in_rows(self):
        gen = generated(7, "111", "REMOVE", position="1:3")
        gen["is_extra_facing"] = True
        gen["pog_facings"] = 0
        gen["rog_facings"] = 2
        result = compare_actions(
            [gen],
            [digital(7, "111", "invader", "Removed Item", position="1:3")],
            execution_compliance_pct=100.0,
        )
        self.assertEqual(result.rows[0].status, "MATCH")
        self.assertTrue(result.rows[0].is_extra_facing)
        self.assertEqual(result.rows[0].pog_facings, 0)
        self.assertEqual(result.rows[0].rog_facings, 2)


if __name__ == "__main__":
    unittest.main()
