"""Regression: completed cross-bay moves with null position states."""

import unittest

from core.action_list_domain_mapper import transform_action_list_to_domain
from core.e2e_audit_engine import audit_task_execution


def _move_item(*, item_id=1, upc="681421029100", root_state="STATE_ACCEPTED",
               cur_state=None, exp_state=None):
    return {
        "id": item_id,
        "action": "ACTION_MOVE",
        "state": root_state,
        "upc": upc,
        "displayed_upc": upc,
        "product_title": "DULCOLAX LIQUID LAXATIVE CHERR 12 OZ",
        "current_position": {
            "action": "set_aside",
            "state": cur_state,
            "shelf": 2,
            "position": 1,
            "scan_id": 7,
            "section_info": {"id": 1, "name": "Bay 3"},
            "planogram_info": {"bay": "3"},
        },
        "expected_position": {
            "action": "place_on_shelf_add_to_bay",
            "state": exp_state,
            "shelf": 2,
            "position": 16,
            "scan_id": 7,
            "section_info": {"id": 2, "name": "Bay 2"},
            "planogram_info": {"bay": "2"},
        },
    }


class TestTwoPhaseMoveRootStateFallback(unittest.TestCase):
    def test_null_position_states_inherit_root_accepted(self):
        models = transform_action_list_to_domain(
            [_move_item()], include_completed=True
        )
        self.assertEqual(len(models), 2)
        self.assertEqual(
            [(m.action_type, m.state) for m in models],
            [("SetAside", "STATE_ACCEPTED"), ("AddItems", "STATE_ACCEPTED")],
        )

    def test_audit_marks_both_halves_completed(self):
        audit = audit_task_execution(
            task_id=1,
            store_id=1,
            pog_id=1,
            raw_items=[_move_item()],
        )
        statuses = [
            (r.action_type, r.status)
            for r in audit.step_records
            if r.upc == "681421029100"
        ]
        self.assertEqual(
            statuses,
            [("SET_ASIDE", "COMPLETED"), ("ADD_TO_SHELF", "COMPLETED")],
        )
        self.assertTrue(
            all(
                r.completed_at is None
                for r in audit.step_records
                if r.upc == "681421029100"
            ),
            "Accepted actions must not receive a generated completion timestamp",
        )

    def test_real_backend_completed_at_is_preserved(self):
        item = _move_item()
        item["completed_at"] = "2026-09-04T10:15:30Z"
        audit = audit_task_execution(
            task_id=1,
            store_id=1,
            pog_id=1,
            raw_items=[item],
        )

        self.assertEqual(
            {
                r.completed_at
                for r in audit.step_records
                if r.upc == "681421029100"
            },
            {"2026-09-04T10:15:30Z"},
        )


if __name__ == "__main__":
    unittest.main()
