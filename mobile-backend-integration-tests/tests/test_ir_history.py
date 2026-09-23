import json
import tempfile
import unittest
import unittest.mock
from datetime import date
from pathlib import Path

from core.ir_history import (
    build_history_view,
    cache_lookup,
    cache_store,
    entry_from_snapshot,
    filter_entries,
    load_history,
    merge_entries,
    normalize_instance_tasks,
    normalize_status,
    record_entry,
    resolve_range,
    save_history,
    status_label,
)


class ResolveRangeTests(unittest.TestCase):
    today = date(2026, 9, 9)

    def test_presets_cover_inclusive_windows(self):
        cases = {
            "today": ("2026-09-09", "2026-09-09", "Today"),
            "7d": ("2026-09-03", "2026-09-09", "Last 7 days"),
            "14d": ("2026-08-27", "2026-09-09", "Last 14 days"),
            "30d": ("2026-08-11", "2026-09-09", "Last 30 days"),
        }
        for preset, (start, end, label) in cases.items():
            with self.subTest(preset=preset):
                resolved = resolve_range(preset, today=self.today)
                self.assertEqual(resolved["from"], start)
                self.assertEqual(resolved["to"], end)
                self.assertEqual(resolved["label"], label)

    def test_custom_range_uses_supplied_dates(self):
        resolved = resolve_range("custom", "2026-08-01", "2026-08-05", today=self.today)

        self.assertEqual(resolved["from"], "2026-08-01")
        self.assertEqual(resolved["to"], "2026-08-05")
        self.assertEqual(resolved["label"], "2026-08-01 to 2026-08-05")

    def test_custom_range_swaps_reversed_dates(self):
        resolved = resolve_range("custom", "2026-08-05", "2026-08-01", today=self.today)

        self.assertEqual(resolved["from"], "2026-08-01")
        self.assertEqual(resolved["to"], "2026-08-05")

    def test_unknown_preset_and_bad_custom_dates_are_rejected(self):
        with self.assertRaises(ValueError):
            resolve_range("last-century", today=self.today)
        with self.assertRaises(ValueError):
            resolve_range("custom", "not-a-date", "2026-08-05", today=self.today)
        with self.assertRaises(ValueError):
            resolve_range("custom", None, None, today=self.today)


class HistoryEntryTests(unittest.TestCase):
    snapshot = {
        "schema_version": 1,
        "task_id": 42484849,
        "instance": "krcs",
        "task_status": "completed",
        "generated_at": "2026-09-08T18:16:00+00:00",
        "quality_gate": {"state": "fail", "threshold_pct": 95.0},
        "metrics": {
            "overall_score_pct": 87.5,
            "digital_alignment_pct": 87.5,
            "post_alignment_pct": None,
            "work_finished_pct": 90.0,
        },
        "post_photo": {"state": "unavailable"},
        "findings": [
            {"code": "IR-QUALITY-GATE", "severity": "critical"},
            {"code": "IR-POST-UNAVAILABLE", "severity": "warning"},
        ],
    }

    def test_entry_from_snapshot_keeps_evidence_and_drops_unknowns(self):
        entry = entry_from_snapshot(self.snapshot, task_date="2026-09-08")

        self.assertEqual(entry["task_id"], 42484849)
        self.assertEqual(entry["instance"], "krcs")
        self.assertEqual(entry["task_date"], "2026-09-08")
        self.assertEqual(entry["source"], "local_audit")
        self.assertTrue(entry["audited"])
        self.assertEqual(entry["gate_state"], "fail")
        self.assertEqual(entry["overall_score_pct"], 87.5)
        self.assertIsNone(entry["post_alignment_pct"])
        self.assertEqual(entry["findings_total"], 2)
        self.assertEqual(entry["findings_critical"], 1)

    def test_entry_without_task_date_falls_back_to_generated_date(self):
        entry = entry_from_snapshot(self.snapshot)

        self.assertEqual(entry["task_date"], "2026-09-08")
        self.assertEqual(entry["date_source"], "recorded")

    def test_snapshot_without_task_is_not_recordable(self):
        self.assertIsNone(entry_from_snapshot({"task_id": None, "metrics": {}}))

    def test_record_entry_upserts_by_instance_and_task(self):
        first = entry_from_snapshot(self.snapshot, task_date="2026-09-08")
        newer = dict(first, overall_score_pct=99.0, recorded_at="2026-09-09T10:00:00+00:00")
        other_instance = dict(first, instance="harr")

        entries = record_entry([], first)
        entries = record_entry(entries, newer)
        entries = record_entry(entries, other_instance)

        self.assertEqual(len(entries), 2)
        krcs = [e for e in entries if e["instance"] == "krcs"]
        self.assertEqual(len(krcs), 1)
        self.assertEqual(krcs[0]["overall_score_pct"], 99.0)

    def test_history_file_roundtrip_rejects_corrupt_payloads(self):
        entry = entry_from_snapshot(self.snapshot, task_date="2026-09-08")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ir-history.json"
            save_history([entry], path)
            self.assertEqual(load_history(path)[0]["task_id"], 42484849)

            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(load_history(path), [])

            path.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
            self.assertEqual(load_history(path), [])

    def test_saved_history_never_contains_credentials(self):
        entry = entry_from_snapshot(
            dict(self.snapshot, token="secret-token", password="secret-password"),
            task_date="2026-09-08",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ir-history.json"
            save_history([entry], path)
            saved = path.read_text(encoding="utf-8")

        self.assertNotIn("secret-token", saved)
        self.assertNotIn("secret-password", saved)


class InstanceTaskNormalisationTests(unittest.TestCase):
    def test_reads_dates_and_status_from_varied_backend_shapes(self):
        payload = {
            "results": [
                {
                    "id": 41295167,
                    "task_date": "2026-08-04",
                    "status": {"slug": "completed"},
                    "store": {"id": 5347},
                    "task_def_title": "038 Frozen Pizza - Intelligent Reset Training",
                },
                {
                    "id": 41295168,
                    "created_at": "2026-08-05T10:00:00Z",
                    "status": "in_progress",
                    "store_id": 5346,
                    "title": "006 Soup Condensed",
                },
            ]
        }

        entries = normalize_instance_tasks(payload, "krcs")

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["task_date"], "2026-08-04")
        self.assertEqual(entries[0]["status"], "completed")
        self.assertEqual(entries[0]["store_id"], 5347)
        self.assertEqual(entries[1]["task_date"], "2026-08-05")
        self.assertEqual(entries[1]["status"], "in_progress")
        for entry in entries:
            self.assertEqual(entry["source"], "instance")
            self.assertFalse(entry["audited"])
            self.assertEqual(entry["gate_state"], "unknown")
            self.assertIsNone(entry["overall_score_pct"])

    def test_rows_without_id_or_date_are_skipped_not_guessed(self):
        payload = [
            {"id": None, "task_date": "2026-08-04"},
            {"id": 5, "task_date": None},
            {"id": 6, "task_date": "2026-08-06"},
        ]

        entries = normalize_instance_tasks(payload, "krcs")

        self.assertEqual([e["task_id"] for e in entries], [6])


class StatusNormalisationTests(unittest.TestCase):
    def test_backend_status_spellings_collapse_to_one_value(self):
        cases = {
            "not started": ("not_started", "Not started"),
            "not_started": ("not_started", "Not started"),
            "NOT-STARTED": ("not_started", "Not started"),
            "in progress": ("in_progress", "In progress"),
            "in_progress": ("in_progress", "In progress"),
            "started": ("in_progress", "In progress"),
            "completed": ("completed", "Completed"),
            "done": ("completed", "Completed"),
            "incomplete": ("incomplete", "Incomplete"),
            "on hold": ("on_hold", "On hold"),
        }
        for raw, (slug, label) in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_status(raw), slug)
                self.assertEqual(status_label(slug), label)

    def test_unknown_status_is_kept_rather_than_discarded(self):
        self.assertEqual(normalize_status("awaiting_review"), "awaiting_review")
        self.assertEqual(normalize_status(None), "unknown")

    def test_instance_rows_expose_normalised_status_and_label(self):
        entries = normalize_instance_tasks(
            [
                {"id": 1, "task_date": "2026-09-09", "status": "not started"},
                {"id": 2, "task_date": "2026-09-09", "status": {"slug": "in_progress"}},
            ],
            "harr",
        )

        self.assertEqual([e["status"] for e in entries], ["not_started", "in_progress"])
        self.assertEqual([e["status_label"] for e in entries], ["Not started", "In progress"])


class FilterTests(unittest.TestCase):
    def entry(self, task_id, title, status, task_type="INTELLIGENT RESET", task_date="2026-09-09"):
        return {
            "task_id": task_id,
            "instance": "harr",
            "task_date": task_date,
            "title": title,
            "status": status,
            "task_type": task_type,
        }

    entries = None

    def setUp(self):
        self.entries = [
            self.entry(1, "DRIED FRUIT - Intelligent Reset - 0906", "not_started"),
            self.entry(2, "APPLESAUCE - Intelligent Reset - 0906", "completed"),
            self.entry(3, "Priority 5 Endcap Display Compliance", "not_started", "DISPLAY COMPLIANCE"),
            self.entry(4, "Priority 7 Endcap Display Compliance", "in_progress", "DISPLAY COMPLIANCE"),
            self.entry(5, "4454-HBC Digestive Health- RICK", "incomplete"),
        ]

    def test_task_type_matches_the_type_field_case_insensitively(self):
        kept = filter_entries(
            self.entries, "harr", "2026-09-01", "2026-09-30", task_type="intelligent reset"
        )

        # Task 5 is an Intelligent Reset whose title never says so.
        self.assertEqual([e["task_id"] for e in kept], [1, 2, 5])

    def test_blank_task_type_keeps_everything(self):
        for value in (None, "", "  ", "all"):
            with self.subTest(value=value):
                kept = filter_entries(
                    self.entries, "harr", "2026-09-01", "2026-09-30", task_type=value
                )
                self.assertEqual(len(kept), 5)

    def test_status_filter_accepts_several_states(self):
        kept = filter_entries(
            self.entries,
            "harr",
            "2026-09-01",
            "2026-09-30",
            statuses=["in_progress", "completed"],
        )

        self.assertEqual(sorted(e["task_id"] for e in kept), [2, 4])

    def test_status_filter_normalises_incoming_spellings(self):
        kept = filter_entries(
            self.entries, "harr", "2026-09-01", "2026-09-30", statuses=["In Progress"]
        )

        self.assertEqual([e["task_id"] for e in kept], [4])

    def test_type_and_status_filters_combine(self):
        kept = filter_entries(
            self.entries,
            "harr",
            "2026-09-01",
            "2026-09-30",
            task_type="INTELLIGENT RESET",
            statuses=["completed"],
        )

        self.assertEqual([e["task_id"] for e in kept], [2])


# Mirrors the real harr.rebotics.net /api/v1/tasks/ payload: `type` and `status`
# are nested objects, and the title does not reliably mention the task type.
REAL_TASK_PAYLOAD = {
    "results": [
        {
            "id": 8707576,
            "type": {"id": 26, "name": "INTELLIGENT RESET", "custom_id": None},
            "category": {"id": 1992, "custom_id": "117", "name": "DRIED FRUIT"},
            "status": {"id": "created", "name": "Not started"},
            "title": "DRIED FRUIT - Intelligent Reset - 0906",
            "start": "2026-09-09T04:00:00Z",
            "store": {"id": 41},
        },
        {
            "id": 8707572,
            "type": {"id": 26, "name": "INTELLIGENT RESET", "custom_id": None},
            "category": {"id": 1895, "custom_id": "4454", "name": "HBC DIGESTIVE HEALTH"},
            "status": {"id": "in_progress", "name": "In progress"},
            "title": "4454-HBC Digestive Health- RICK",
            "start": "2026-09-09T04:00:00Z",
            "store": {"id": 41},
        },
        {
            "id": 8707400,
            "type": {"id": 12, "name": "DISPLAY COMPLIANCE", "custom_id": None},
            "category": {"id": 1700, "custom_id": "9", "name": "ENDCAP"},
            "status": {"id": "completed", "name": "Completed"},
            "title": "Priority 5 Endcap Display Compliance for Wk of 09/06",
            "start": "2026-09-09T04:00:00Z",
            "store": {"id": 41},
        },
    ]
}


class RealPayloadShapeTests(unittest.TestCase):
    def setUp(self):
        self.entries = normalize_instance_tasks(REAL_TASK_PAYLOAD, "harr")

    def test_task_type_is_read_from_the_type_object_not_the_title(self):
        by_id = {entry["task_id"]: entry for entry in self.entries}

        self.assertEqual(by_id[8707576]["task_type"], "INTELLIGENT RESET")
        self.assertEqual(by_id[8707576]["task_type_id"], 26)
        # This one is an Intelligent Reset even though its title never says so,
        # which is exactly what a title substring match got wrong.
        self.assertEqual(by_id[8707572]["task_type"], "INTELLIGENT RESET")
        self.assertEqual(by_id[8707400]["task_type"], "DISPLAY COMPLIANCE")

    def test_status_uses_the_stable_id_and_shows_the_backend_wording(self):
        by_id = {entry["task_id"]: entry for entry in self.entries}

        self.assertEqual(by_id[8707576]["status"], "not_started")
        self.assertEqual(by_id[8707576]["status_label"], "Not started")
        self.assertEqual(by_id[8707572]["status"], "in_progress")
        self.assertEqual(by_id[8707400]["status"], "completed")

    def test_category_is_kept_for_display(self):
        self.assertEqual(self.entries[0]["category"], "DRIED FRUIT")

    def test_filtering_by_type_keeps_untitled_intelligent_resets(self):
        kept = filter_entries(
            self.entries, "harr", "2026-09-01", "2026-09-30", task_type="INTELLIGENT RESET"
        )

        self.assertEqual([entry["task_id"] for entry in kept], [8707576, 8707572])

    def test_filtering_by_type_and_status_together(self):
        kept = filter_entries(
            self.entries,
            "harr",
            "2026-09-01",
            "2026-09-30",
            task_type="INTELLIGENT RESET",
            statuses=["in_progress"],
        )

        self.assertEqual([entry["task_id"] for entry in kept], [8707572])

    def test_title_search_is_a_separate_filter_from_type(self):
        kept = filter_entries(
            self.entries, "harr", "2026-09-01", "2026-09-30", title_contains="applesauce"
        )
        self.assertEqual(kept, [])

        kept = filter_entries(
            self.entries, "harr", "2026-09-01", "2026-09-30", title_contains="dried fruit"
        )
        self.assertEqual([entry["task_id"] for entry in kept], [8707576])

    def test_view_offers_the_real_types_and_statuses_as_choices(self):
        view = build_history_view(
            [], self.entries, "harr", {"from": "2026-09-01", "to": "2026-09-30", "label": "September"},
            available=self.entries,
        )

        self.assertEqual(
            view["facets"]["types"],
            [
                {"value": "INTELLIGENT RESET", "label": "INTELLIGENT RESET", "count": 2},
                {"value": "DISPLAY COMPLIANCE", "label": "DISPLAY COMPLIANCE", "count": 1},
            ],
        )
        self.assertEqual(
            sorted(item["value"] for item in view["facets"]["statuses"]),
            ["completed", "in_progress", "not_started"],
        )

    def test_audited_row_keeps_its_score_but_takes_identity_from_the_instance(self):
        audited_local = {
            "task_id": 8707572,
            "instance": "harr",
            "task_date": "2026-09-09",
            "source": "local_audit",
            "audited": True,
            "status": "not_started",
            "status_label": "Not started",
            "title": None,
            "gate_state": "pass",
            "overall_score_pct": 100.0,
        }

        merged = merge_entries([audited_local], self.entries)
        row = next(entry for entry in merged if entry["task_id"] == 8707572)

        self.assertTrue(row["audited"])
        self.assertEqual(row["overall_score_pct"], 100.0)
        self.assertEqual(row["title"], "4454-HBC Digestive Health- RICK")
        self.assertEqual(row["task_type"], "INTELLIGENT RESET")
        self.assertEqual(row["status"], "in_progress")
        self.assertEqual(row["status_label"], "In progress")


class TaskCacheTests(unittest.TestCase):
    def test_fresh_entries_are_reused_and_stale_ones_expire(self):
        cache = {}
        rows = [{"task_id": 1}]
        cache_store(cache, ("harr", "2026-09-01", "2026-09-09"), 1000.0, rows)

        self.assertEqual(
            cache_lookup(cache, ("harr", "2026-09-01", "2026-09-09"), 1200.0, 300.0), rows
        )
        self.assertIsNone(
            cache_lookup(cache, ("harr", "2026-09-01", "2026-09-09"), 1400.0, 300.0)
        )
        self.assertEqual(cache, {})

    def test_different_range_or_instance_is_a_different_entry(self):
        cache = {}
        cache_store(cache, ("harr", "2026-09-01", "2026-09-09"), 1000.0, [{"task_id": 1}])

        self.assertIsNone(cache_lookup(cache, ("krcs", "2026-09-01", "2026-09-09"), 1000.0, 300.0))
        self.assertIsNone(cache_lookup(cache, ("harr", "2026-08-01", "2026-09-09"), 1000.0, 300.0))


class MergeAndSummaryTests(unittest.TestCase):
    range_info = {"from": "2026-08-01", "to": "2026-08-31", "label": "Custom", "preset": "custom"}

    def local_entry(self, task_id, gate_state, score, task_date="2026-08-10"):
        return {
            "task_id": task_id,
            "instance": "krcs",
            "task_date": task_date,
            "source": "local_audit",
            "audited": True,
            "gate_state": gate_state,
            "status": "completed",
            "overall_score_pct": score,
            "digital_alignment_pct": score,
            "post_alignment_pct": None,
            "work_finished_pct": 100.0,
            "findings_total": 1,
            "findings_critical": 1 if gate_state == "fail" else 0,
        }

    def remote_entry(self, task_id, task_date="2026-08-10"):
        return {
            "task_id": task_id,
            "instance": "krcs",
            "task_date": task_date,
            "source": "instance",
            "audited": False,
            "gate_state": "unknown",
            "status": "completed",
            "overall_score_pct": None,
            "digital_alignment_pct": None,
            "post_alignment_pct": None,
            "work_finished_pct": None,
            "findings_total": 0,
            "findings_critical": 0,
        }

    def test_audited_local_entry_wins_over_thin_remote_row(self):
        merged = merge_entries([self.local_entry(1, "pass", 99.0)], [self.remote_entry(1), self.remote_entry(2)])

        self.assertEqual(len(merged), 2)
        audited = next(e for e in merged if e["task_id"] == 1)
        self.assertTrue(audited["audited"])
        self.assertEqual(audited["overall_score_pct"], 99.0)

    def test_merge_sorts_newest_first(self):
        merged = merge_entries(
            [self.local_entry(1, "pass", 99.0, task_date="2026-08-01")],
            [self.remote_entry(2, task_date="2026-08-20")],
        )

        self.assertEqual([e["task_id"] for e in merged], [2, 1])

    def test_filter_uses_inclusive_bounds_and_instance(self):
        entries = [
            self.local_entry(1, "pass", 99.0, task_date="2026-07-31"),
            self.local_entry(2, "pass", 99.0, task_date="2026-08-01"),
            self.local_entry(3, "pass", 99.0, task_date="2026-08-31"),
            self.local_entry(4, "pass", 99.0, task_date="2026-09-01"),
            dict(self.local_entry(5, "pass", 99.0, task_date="2026-08-10"), instance="harr"),
        ]

        kept = filter_entries(entries, "krcs", "2026-08-01", "2026-08-31")

        self.assertEqual(sorted(e["task_id"] for e in kept), [2, 3])

    def test_summary_averages_ignore_unknown_scores(self):
        view = build_history_view(
            local=[self.local_entry(1, "pass", 100.0), self.local_entry(2, "fail", 80.0)],
            remote=[self.remote_entry(3)],
            instance="krcs",
            range_info=self.range_info,
        )
        totals = view["totals"]

        self.assertEqual(totals["tasks"], 3)
        self.assertEqual(totals["audited"], 2)
        self.assertEqual(totals["gate_pass"], 1)
        self.assertEqual(totals["gate_fail"], 1)
        self.assertEqual(totals["gate_unknown"], 1)
        self.assertEqual(totals["avg_overall_score_pct"], 90.0)
        self.assertEqual(totals["not_audited"], 1)

    def test_empty_range_explains_itself_without_pretending_zero(self):
        view = build_history_view(local=[], remote=[], instance="krcs", range_info=self.range_info)

        self.assertEqual(view["totals"]["tasks"], 0)
        self.assertIsNone(view["totals"]["avg_overall_score_pct"])
        self.assertIn("No Intelligent Reset tasks", view["plain_language_summary"])
        self.assertIn("Custom", view["plain_language_summary"])

    def test_remote_error_is_surfaced_and_local_data_still_shown(self):
        view = build_history_view(
            local=[self.local_entry(1, "pass", 100.0)],
            remote=[],
            instance="krcs",
            range_info=self.range_info,
            remote_error="Sign in to krcs to load tasks from the instance.",
        )

        self.assertEqual(view["totals"]["tasks"], 1)
        self.assertEqual(view["remote_error"], "Sign in to krcs to load tasks from the instance.")
        self.assertIn("Sign in", view["plain_language_summary"])

    def test_every_task_row_offers_a_deep_audit_action(self):
        view = build_history_view(
            local=[],
            remote=[self.remote_entry(4242)],
            instance="krcs",
            range_info=self.range_info,
        )

        self.assertEqual(view["tasks"][0]["audit_action"], "/api/runner/audit_task")
        self.assertIn("task_id=4242", view["tasks"][0]["report_url"])


class PersistIrStateTests(unittest.TestCase):
    """History rows must be attributable, so an unknown instance is never invented."""

    def persist(self, state):
        import runner_server

        with tempfile.TemporaryDirectory() as tmp:
            history_file = Path(tmp) / "ir-history.json"
            with unittest.mock.patch.multiple(
                runner_server,
                EXECUTION_STATE=state,
                IR_HISTORY_FILE=history_file,
                IR_SNAPSHOT_FILE=Path(tmp) / "ir-live-snapshot.json",
            ):
                runner_server.persist_ir_state()
            return load_history(history_file)

    def test_known_instance_is_filed_in_history(self):
        entries = self.persist({
            "active_task_id": 4242,
            "instance_slug": "harr",
            "task_info": {"task_date": "2026-09-01"},
            "latest_audit": {"task_id": 4242, "combined_compliance_pct": 96.0, "task_timeline": {}},
        })

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["instance"], "harr")
        self.assertEqual(entries[0]["task_date"], "2026-09-01")

    def test_placeholder_instance_is_not_filed_under_a_fake_name(self):
        for slug in ("live", "", None):
            with self.subTest(slug=slug):
                entries = self.persist({
                    "active_task_id": 4242,
                    "instance_slug": slug,
                    "latest_audit": {"task_id": 4242, "combined_compliance_pct": 96.0, "task_timeline": {}},
                })
                self.assertEqual(entries, [])


class HistoryUiContractTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[2]

    def test_ir_tab_exposes_instance_and_range_controls(self):
        index_html = (self.root / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="ir-history-instance"', index_html)
        self.assertIn('id="ir-history-range"', index_html)
        self.assertIn('id="ir-history-from"', index_html)
        self.assertIn('id="ir-history-to"', index_html)
        self.assertIn('id="ir-history-load"', index_html)
        self.assertIn('id="ir-history-results"', index_html)
        self.assertIn("Last 7 days", index_html)

    def test_history_script_calls_the_history_endpoint(self):
        script = (self.root / "assets/js/ir-history.js").read_text(encoding="utf-8")

        self.assertIn("/api/runner/ir_history", script)
        self.assertIn("/api/runner/audit_task", script)

    def test_panel_offers_task_type_and_status_filters(self):
        index_html = (self.root / "index.html").read_text(encoding="utf-8")
        script = (self.root / "assets/js/ir-history.js").read_text(encoding="utf-8")

        self.assertIn('id="ir-history-type"', index_html)
        self.assertIn('id="ir-history-status-filter"', index_html)
        # The summary pill also lives in this panel; a shared id would make the
        # dropdown unreadable from JS and silently drop the status filter.
        self.assertEqual(index_html.count('id="ir-history-status"'), 1)
        self.assertIn("byId('ir-history-status-filter')", script)
        self.assertIn("All task types", index_html)
        self.assertIn("params.set('type'", script)
        self.assertIn("params.set('status'", script)
        self.assertIn("params.set('title'", script)

    def test_filter_choices_come_from_the_instance_not_hardcoded_guesses(self):
        index_html = (self.root / "index.html").read_text(encoding="utf-8")
        script = (self.root / "assets/js/ir-history.js").read_text(encoding="utf-8")

        # A hardcoded "Intelligent Reset" option was a title guess that matched nothing.
        self.assertNotIn("Intelligent Reset only", index_html)
        self.assertNotIn('value="Endcap"', index_html)
        self.assertIn("fillChoices('ir-history-type', facets.types", script)
        self.assertIn("fillChoices('ir-history-status-filter', facets.statuses", script)

    def test_history_panel_can_sign_in_without_leaving_the_dashboard(self):
        index_html = (self.root / "index.html").read_text(encoding="utf-8")
        script = (self.root / "assets/js/ir-history.js").read_text(encoding="utf-8")

        self.assertIn('id="ir-history-username"', index_html)
        self.assertIn('id="ir-history-password"', index_html)
        self.assertIn('type="password"', index_html)
        self.assertIn("/api/runner/auth_ping", script)


if __name__ == "__main__":
    unittest.main()
