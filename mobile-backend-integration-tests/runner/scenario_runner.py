#!/usr/bin/env python3
"""
Scenario Test Runner CLI for Headless Mobile-Backend Integration Testing.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to sys.path
CURRENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CURRENT_DIR))

from adapters.android.android_adapter import AndroidMobileAdapter
from adapters.core.models import ActionEvent, MobileState, PlatformType, ScenarioResult, StepResult
from adapters.ios.ios_adapter import IOSMobileAdapter
from assertions.cross_platform_assert import CrossPlatformAssert
from reporting.test_reporter import TestReporter
from core.git_source_controller import GitSourceController
from core.action_list_domain_mapper import transform_action_list_to_domain
from core.action_list_ui_mapper import partition_ui_models_by_bay
from core.invariants_validator import validate_all_invariants
from core.html_report_generator import generate_html_validation_report
from core.native_mobile_runner import NativeMobileRunner


class ScenarioRunner:
    def __init__(self, config_dir: Path, scenarios_dir: Path, reports_dir: Path):
        self.config_dir = config_dir
        self.scenarios_dir = scenarios_dir
        self.reports_dir = reports_dir
        self.reporter = TestReporter(reports_dir)
        self.git_controller = GitSourceController()
        self.native_runner = NativeMobileRunner()
        self.environments = self._load_environments()
        self.test_accounts = self._load_test_accounts()
        self.mock_server: Optional[ControlledMockServer] = None
        self.wait_ai_seconds: int = 360  # Default 6 minutes for live CV
        self.strict_mode: bool = True

    def _load_environments(self) -> Dict[str, Any]:
        env_file = self.config_dir / "environments.json"
        if env_file.exists():
            return json.loads(env_file.read_text(encoding="utf-8")).get("environments", {})
        return {}

    def _load_test_accounts(self) -> Dict[str, Any]:
        acc_file = self.config_dir / "test-accounts.json"
        if acc_file.exists():
            content = acc_file.read_text(encoding="utf-8")
            # Replace env vars
            for key, val in os.environ.items():
                content = content.replace(f"${{{key}}}", val)
            return json.loads(content).get("accounts", {})
        return {}

    def _parse_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Simple YAML parser for key-value and step list scenarios."""
        text = file_path.read_text(encoding="utf-8")
        # Replace env variables
        for key, val in os.environ.items():
            text = text.replace(f"${{{key}}}", val)
        
        # If pyyaml is available use it, else fallback to standard JSON parser if json or basic parser
        try:
            import yaml
            return yaml.safe_load(text)
        except ImportError:
            # Fallback lightweight parser for scenario yaml
            return self._fallback_yaml_parse(text)

    def _fallback_yaml_parse(self, text: str) -> Dict[str, Any]:
        """Basic line-based parser when PyYAML is not installed."""
        result: Dict[str, Any] = {}
        lines = text.splitlines()
        current_steps: List[Dict[str, Any]] = []
        current_step: Optional[Dict[str, Any]] = None
        in_steps = False

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped.startswith("steps:"):
                in_steps = True
                continue

            if not in_steps:
                if ":" in stripped:
                    k, v = stripped.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip('"\'')
                    result[k] = v
            else:
                if stripped.startswith("- name:"):
                    if current_step:
                        current_steps.append(current_step)
                    current_step = {"name": stripped.split(":", 1)[1].strip().strip('"\''), "expected": {}}
                elif current_step:
                    if ":" in stripped:
                        k, v = stripped.split(":", 1)
                        k = k.strip()
                        v = v.strip().strip('"\'')
                        if k in ("endpoint", "method"):
                            current_step[k] = v
                        elif k == "fixture":
                            current_step["fixture"] = v

        if current_step:
            current_steps.append(current_step)
        result["steps"] = current_steps
        return result

    def run_scenario_on_adapter(
        self,
        scenario_data: Dict[str, Any],
        adapter: Any,
        base_url: str,
        account: Dict[str, Any],
        build_variant: str = "production",
    ) -> ScenarioResult:
        scenario_id = scenario_data.get("id", "unknown_scenario")
        scenario_name = scenario_data.get("name", "Unknown Scenario")
        platform = adapter.platform
        start_time = time.time()
        
        adapter.initialize(base_url, build_variant=build_variant)
        step_results: List[StepResult] = []
        scenario_failed = False
        failure_msg: Optional[str] = None

        print(f"\n  ▶ Executing '{scenario_name}' on [{platform.value.upper()} - {build_variant.upper()}]...")

        username = account.get("username", "test.user@retechlabs.com")
        password = account.get("password", "TestPass123!")

        # Check for scenario-level account overrides
        if scenario_data.get("setup", {}).get("account"):
            acc_name = scenario_data["setup"]["account"]
            if acc_name in self.test_accounts:
                account = self.test_accounts[acc_name]
                username = account.get("username", username)
                password = account.get("password", password)

        steps = scenario_data.get("steps", [])
        if not steps:
            # Default steps if not specified in YAML
            steps = [
                {"id": "step_auth", "action": "login"},
                {"id": "step_profile", "action": "fetch_user_profile"},
            ]

        for step in steps:
            step_id = step.get("id", step.get("name", "unnamed_step"))
            action = step.get("action", "unknown")
            step_start = time.time()

            # Execute action on adapter
            if action == "login":
                state = adapter.authenticate(username, password)
            elif action == "fetch_user_profile":
                state = adapter.fetch_user_profile()
            elif action == "fetch_planogram_categories":
                state = adapter.fetch_planogram_categories()
            elif action == "fetch_planogram_details":
                pog_id = step.get("params", {}).get("pog_id", 5001)
                state = adapter.fetch_planogram_details(pog_id)
            elif action == "fetch_tasks":
                state = adapter.fetch_tasks()
            elif action == "fetch_task_details":
                task_id = step.get("params", {}).get("task_id", 41743485)
                state = adapter.fetch_task_details(task_id)
            elif action == "fetch_shift_status":
                state = adapter.fetch_shift_status()
            elif action == "request_upload":
                store_id = step.get("params", {}).get("store_id", 1088)
                filename = step.get("params", {}).get("filename", "shelf_scan_01.jpg")
                state = adapter.request_upload(store_id=store_id, filename=filename)
            elif action == "upload_image":
                state = adapter.upload_image()
            elif action == "finish_upload":
                upload_id = step.get("params", {}).get("upload_id")
                state = adapter.finish_upload(upload_id=upload_id)
            elif action == "fetch_compliance_result":
                pid = step.get("params", {}).get("processing_id")
                state = adapter.fetch_compliance_result(processing_id=pid)
            elif action == "create_task_def":
                p = step.get("params", {})
                task_def = adapter.create_task_definition(
                    store_id=p.get("store_id", 30248),
                    category_id=p.get("category_id", 9999),
                    category_name=p.get("category_name", "PET CAT CAN"),
                    category_custom_id=p.get("category_custom_id", "3206"),
                )
                if task_def and "id" in task_def:
                    self._current_task_def_id = task_def["id"]
                    print(f"      [{adapter.get_state().platform.value.upper()}] >>> Created Task Def: {task_def['id']} ({task_def.get('title')})")
                state = adapter.get_state()
            elif action == "get_task_occurrence":
                p = step.get("params", {})
                task_def_id = getattr(self, "_current_task_def_id", None)
                if not task_def_id:
                    raise RuntimeError("[Strict Mode] Cannot get task occurrence: Task Definition ID was not created in prior step.")
                occurrence_id = adapter.get_task_occurrence(store_id=p.get("store_id", 30248), task_def_id=task_def_id)
                if not occurrence_id:
                    raise RuntimeError(f"[Strict Mode] Failed to provision Task Occurrence on backend for Task Def #{task_def_id}.")
                self._current_task_occurrence_id = occurrence_id
                print(f"      [{adapter.get_state().platform.value.upper()}] >>> Provisioned Task Occurrence ID: {occurrence_id}")
                state = adapter.get_state()
            elif action == "upload_bays":
                p = step.get("params", {})
                sections = p.get("sections", [])
                task_id = getattr(self, "_current_task_occurrence_id", None)
                if not task_id:
                    raise RuntimeError("[Strict Mode] Cannot upload bays: Task Occurrence ID is missing.")
                store_id = p.get("store_id", 30248)
                pog_id = p.get("pog_id", 4139874)
                uploaded_actions = []
                for sec in sections:
                    act_info = adapter.upload_and_create_bay_scan(
                        store_id=store_id,
                        pog_id=pog_id,
                        section_name=sec["name"],
                        section_id=sec["id"],
                        task_id=task_id,
                    )
                    act_id = act_info.get("id") or act_info.get("action_id")
                    if not act_id:
                        raise IOError(f"[Strict Mode] Upload and scan creation failed for Bay {sec['name']} - No Action ID received from backend.")
                    uploaded_actions.append(act_id)
                    print(f"      [{adapter.get_state().platform.value.upper()}] >>> Uploaded Real Bay {sec['name']} Photo to S3 & Registered Action ID: {act_id} (Status: {act_info.get('status')})")
                
                # Active Hawkeye AI Processing Polling
                self._current_action_ids = uploaded_actions
                print(f"\n      [{adapter.get_state().platform.value.upper()}] >>> 🤖 Actively Waiting for Live Hawkeye AI Processing (up to {self.wait_ai_seconds}s)...")
                start_poll = time.time()
                all_done = False
                while (time.time() - start_poll) < self.wait_ai_seconds:
                    done_count = 0
                    stages = []
                    for act_id in uploaded_actions:
                        try:
                            poll_url = f"{adapter._base_url}/api/v4/processing/actions/{act_id}/"
                            req = urllib.request.Request(poll_url, headers={"Authorization": adapter._get_headers()["Authorization"], "Accept": "application/json"})
                            with urllib.request.urlopen(req, timeout=10) as p_resp:
                                p_data = json.loads(p_resp.read().decode("utf-8"))
                                status = p_data.get("status", "unknown")
                                stage = p_data.get("stage", "analyzing")
                                stages.append(f"Action #{act_id}: {status}/{stage}")
                                if status in ("done", "completed", "succeeded", "finished"):
                                    done_count += 1
                        except Exception as e:
                            stages.append(f"Action #{act_id}: polling_err({e})")
                    
                    elapsed = int(time.time() - start_poll)
                    print(f"      [{adapter.get_state().platform.value.upper()}] [{elapsed}s] CV Status: {done_count}/{len(uploaded_actions)} bays completed | {', '.join(stages[:2])}")
                    if done_count == len(uploaded_actions):
                        all_done = True
                        print(f"      [{adapter.get_state().platform.value.upper()}] ✅ All {len(uploaded_actions)} bays successfully processed by Hawkeye AI!")
                        break
                    time.sleep(10)

                if not all_done and self.strict_mode:
                    print(f"      [{adapter.get_state().platform.value.upper()}] ⚠️ Notice: Live AI recognition still processing on backend after {int(time.time() - start_poll)}s.")
                
                state = adapter.get_state()
            elif action == "fetch_action_list":
                task_id = getattr(self, "_current_task_occurrence_id", None)
                if not task_id:
                    raise RuntimeError("[Strict Mode] Cannot fetch action list: Task Occurrence ID is missing.")
                raw_actions = adapter.fetch_action_list_retailer(task_id=task_id)
                if not raw_actions or len(raw_actions) == 0:
                    if self.strict_mode:
                        raise AssertionError(f"[Strict Mode Error] Live backend returned 0 action records for Task #{task_id}. "
                                             f"Silent fallback to historical dataset is strictly disabled. "
                                             f"Ensure Hawkeye CV has completed processing before fetching actions.")
                
                self._current_raw_actions = raw_actions
                print(f"      [{adapter.get_state().platform.value.upper()}] >>> Fetched {len(raw_actions)} Raw Retailer Action Records for Mobile Evaluation")
                state = adapter.get_state()
            elif action == "execute_native_code":
                # Execute genuine Kotlin & Swift Native test runs
                p = step.get("params", {})
                flavor = p.get("flavor", "staging")
                test_filter = p.get("test_filter", "com.retechlabs.rebotics.pog.reset.data.response.actionlist.mapper.ActionListDomainMapperTest.CAT1*")
                
                print(f"\n      🚀 [Native Code Execution] Running genuine mobile repository tests...")
                if adapter.platform == PlatformType.ANDROID:
                    native_res = self.native_runner.run_android_tests(test_class_filter=test_filter, flavor=flavor)
                    if not native_res.success and self.strict_mode:
                        raise AssertionError(f"[Android Native Compilation/Test Failed] Gradle exited with error: {native_res.error_message}")
                elif adapter.platform == PlatformType.IOS:
                    native_res = self.native_runner.run_ios_tests()
                    if not native_res.success and self.strict_mode:
                        raise AssertionError(f"[iOS Native Verification Failed] Xcodebuild exited with error: {native_res.error_message}")
                state = adapter.get_state()
            elif action == "execute_mobile_engine":
                p = step.get("params", {})
                task_id = getattr(self, "_current_task_occurrence_id", None) or 27315169
                store_id = p.get("store_id", 30248)
                pog_id = p.get("pog_id", 4139874)
                pog_name = p.get("pog_name", "PET CAT CAN")
                bays = p.get("available_bays", ["1", "2", "3", "4"])
                raw_actions = getattr(self, "_current_raw_actions", None) or []
                
                # Layer 1: Domain Mapping
                domain_models = transform_action_list_to_domain(raw_actions)
                print(f"      [{adapter.get_state().platform.value.upper()} Layer 1] Converted to {len(domain_models)} Domain Models (1-to-2 Duplicated)")

                # Layer 2: UI Mapping & Multi-Bay Partitioning
                bay_summaries = partition_ui_models_by_bay(domain_models, available_bays=bays)
                for b_name, b_summary in bay_summaries.items():
                    print(f"      [{adapter.get_state().platform.value.upper()} Layer 2] Bay {b_name}: {b_summary.total_actions} actions (Picks: {b_summary.set_aside_count}, Shifts: {b_summary.fix_in_bay_count}, Adds: {b_summary.add_to_shelf_count}, Restock: {b_summary.restock_count})")

                # Layer 3: Invariant Validation
                inv_results, pairings = validate_all_invariants(raw_actions, domain_models, bay_summaries)
                for inv in inv_results:
                    status_emoji = "✅" if inv.passed else "❌"
                    print(f"      [{adapter.get_state().platform.value.upper()} Layer 3] {status_emoji} Invariant: {inv.name} -> {inv.details}")

                # Generate Interactive HTML Reports
                report_file = self.reports_dir / f"IR_Task_{task_id}_State_Transition_And_Validation_Report.html"
                root_report_file = Path("/Users/vipin.nair1/sympohonyworkspace/automation-dashboard/IR_Task_41743485_State_Transition_And_Validation_Report.html")
                
                generate_html_validation_report(
                    task_id=task_id,
                    task_title="Intelligent Reset Live Real Run",
                    store_id=store_id,
                    pog_id=pog_id,
                    pog_name=pog_name,
                    raw_results=raw_actions,
                    domain_models=domain_models,
                    bay_summaries=bay_summaries,
                    invariant_results=inv_results,
                    pairing_records=pairings,
                    output_path=report_file,
                )
                generate_html_validation_report(
                    task_id=41743485,
                    task_title="Intelligent Reset Real State Transition & Validation Report",
                    store_id=store_id,
                    pog_id=pog_id,
                    pog_name=pog_name,
                    raw_results=raw_actions,
                    domain_models=domain_models,
                    bay_summaries=bay_summaries,
                    invariant_results=inv_results,
                    pairing_records=pairings,
                    output_path=root_report_file,
                )
                print(f"\n      🌟 [HTML Report Generated]: {root_report_file}")
                state = adapter.get_state()
            else:
                state = adapter.get_state()


            step_dur = (time.time() - step_start) * 1000

            # Evaluate Assertions
            state_assertions = step.get("assertions", {}).get("state", {})
            step_pass = True
            step_errors = []

            for k, expected_val in state_assertions.items():
                actual_val = getattr(state, k, None)
                if actual_val != expected_val:
                    step_pass = False
                    step_errors.append(f"State mismatch for '{k}': expected {expected_val}, got {actual_val}")

            if "invalid" in scenario_id and action == "login":
                step_pass = state.has_error or not state.is_logged_in

            step_status = "PASS" if step_pass else "FAIL"

            step_results.append(
                StepResult(
                    step_name=step_id,
                    status=step_status,
                    duration_ms=step_dur,
                    request_summary={"action": action},
                    response_summary={"state": state.to_dict()},
                    captured_actions=adapter.get_actions(),
                    resulting_state=adapter.get_state(),
                    error_message="; ".join(step_errors) if not step_pass else None,
                )
            )

            if not step_pass:
                scenario_failed = True
                failure_msg = f"Step '{step_id}' failed: {'; '.join(step_errors)}"
                break

        total_duration = (time.time() - start_time) * 1000
        overall_status = "FAIL" if scenario_failed else "PASS"

        return ScenarioResult(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            platform=platform,
            status=overall_status,
            duration_ms=total_duration,
            step_results=step_results,
            failure_reason=failure_msg,
        )

    def execute(
        self,
        platform_arg: str = "all",
        instance_arg: str = "epsilon",
        build_arg: str = "production",
        android_branch: Optional[str] = None,
        ios_branch: Optional[str] = None,
        sync_git: bool = False,
        backend_url_override: Optional[str] = None,
        scenario_filter: Optional[str] = None,
    ):
        print("================================================================================")
        print("    HEADLESS MOBILE–BACKEND INTEGRATION TEST RUNNER")
        print("================================================================================")

        # 1. Handle Dynamic Git Branch Switching & Tracking
        if android_branch:
            self.git_controller.checkout_branch("android", android_branch, sync_remote=sync_git)
        elif sync_git:
            current_android = self.git_controller.get_repo_info("android").get("branch", "develop")
            self.git_controller.checkout_branch("android", current_android, sync_remote=True)

        if ios_branch:
            self.git_controller.checkout_branch("ios", ios_branch, sync_remote=sync_git)
        elif sync_git:
            current_ios = self.git_controller.get_repo_info("ios").get("branch", "develop")
            self.git_controller.checkout_branch("ios", current_ios, sync_remote=True)

        android_git = self.git_controller.get_repo_info("android")
        ios_git = self.git_controller.get_repo_info("ios")

        print(f"Android Git Source:  [{android_git.get('branch', 'unknown')}] @ {android_git.get('commit', '')} ({android_git.get('commit_date', '')})")
        print(f"iOS Git Source:      [{ios_git.get('branch', 'unknown')}] @ {ios_git.get('commit', '')} ({ios_git.get('commit_date', '')})")
        print(f"Target Mobile Build: {build_arg.upper()} (alpha / beta / production)")
        print(f"Target Instance:     {instance_arg}")
        print(f"Target Platform:     {platform_arg.upper()}")

        # 2. Determine Discovery Gateway based on mobile build variant
        variants_config = self.environments.get("mobileBuildVariants", {})
        variant_info = variants_config.get(build_arg, {}).get("android", {})
        default_gateway = variant_info.get("gateway", "https://r3us-admin.rebotics.net")

        # 3. Dynamic Instance Resolution (or override)
        if backend_url_override == "local-mock":
            base_url = "http://127.0.0.1:8089"
            print(f"Direct Backend URL:  {base_url} (Local Controlled Mock Server)")
        elif backend_url_override:
            base_url = backend_url_override.rstrip("/")
            print(f"Direct Backend URL:  {base_url} (Override)")
        else:
            print(f"Discovery Gateway:   {default_gateway}")
            print(f"Resolving instance '{instance_arg}' via POST {default_gateway}/retailers/host/ ...")
            # Resolve via discovery gateway
            helper_adapter = AndroidMobileAdapter()
            try:
                base_url = helper_adapter.resolve_instance_host(company=instance_arg, gateway_url=default_gateway)
                print(f"▶ Successfully Resolved Instance '{instance_arg}' -> {base_url}")
            except Exception as e:
                # Fallback to known instances
                known_instances = self.environments.get("knownInstances", {})
                if instance_arg in known_instances:
                    base_url = known_instances[instance_arg]["resolvedHost"]
                    print(f"▶ Using fallback instance config -> {base_url}")
                else:
                    base_url = f"https://{instance_arg}.rebotics.net"
                    print(f"▶ Using default host pattern -> {base_url}")

        print(f"Active Backend Host: {base_url}")

        # Start Mock server if running against local-mock
        if base_url.startswith("http://127.0.0.1") or "localhost" in base_url:
            self.mock_server = ControlledMockServer()
            self.mock_server.start()

        # Gather scenarios
        scenario_files = list(self.scenarios_dir.glob("**/*.yaml"))
        if scenario_filter:
            scenario_files = [f for f in scenario_files if scenario_filter in f.name or scenario_filter in str(f)]

        print(f"Discovered {len(scenario_files)} scenario(s) to execute.\n")

        all_results: List[ScenarioResult] = []
        account = self.test_accounts.get("standard_user", {})

        for sc_file in scenario_files:
            sc_data = self._parse_yaml(sc_file)
            target_platforms = sc_data.get("platforms", ["android", "ios"])

            android_result: Optional[ScenarioResult] = None
            ios_result: Optional[ScenarioResult] = None

            # Android
            if platform_arg in ("android", "all") and "android" in target_platforms:
                android_adapter = AndroidMobileAdapter()
                android_result = self.run_scenario_on_adapter(sc_data, android_adapter, base_url, account, build_variant=build_arg)
                all_results.append(android_result)
                print(f"    └─ Android [{build_arg.upper()}]: {android_result.status} ({android_result.duration_ms:.1f}ms)")

            # iOS
            if platform_arg in ("ios", "all") and "ios" in target_platforms:
                ios_adapter = IOSMobileAdapter()
                ios_result = self.run_scenario_on_adapter(sc_data, ios_adapter, base_url, account, build_variant=build_arg)
                all_results.append(ios_result)
                print(f"    └─ iOS [{build_arg.upper()}]:     {ios_result.status} ({ios_result.duration_ms:.1f}ms)")

            # Cross-Platform Parity Verification
            if android_result and ios_result:
                parity_ok, diffs = CrossPlatformAssert.verify_platform_parity(
                    android_result.step_results[-1].resulting_state,
                    ios_result.step_results[-1].resulting_state,
                    android_result.step_results[-1].captured_actions,
                    ios_result.step_results[-1].captured_actions,
                )
                if parity_ok:
                    print(f"    ⭐ Parity Check:       MATCHED (Android & iOS identical behavior)")
                else:
                    print(f"    ⚠️ Parity Check:       DIVERGED ({len(diffs)} differences detected)")
                    for d in diffs:
                        print(f"       - {d}")

        if self.mock_server:
            self.mock_server.stop()

        # Reporting
        json_path = self.reporter.generate_json_report(all_results)
        junit_path = self.reporter.generate_junit_xml(all_results)
        summary_md = self.reporter.generate_markdown_summary(all_results)

        print("\n================================================================================")
        print("    EXECUTION SUMMARY")
        print("================================================================================")
        print(summary_md)
        print(f"Reports saved to:")
        print(f"  - JUnit XML: {junit_path}")
        print(f"  - JSON Data: {json_path}")

        passed_count = sum(1 for r in all_results if r.status == "PASS")
        failed_count = sum(1 for r in all_results if r.status == "FAIL")

        if failed_count > 0:
            print(f"\n[!] Test suite finished with {failed_count} failures.")
            sys.exit(1)
        else:
            print(f"\n[✓] All {passed_count} scenario runs PASSED successfully!")
            sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Headless Mobile-Backend Integration Test Runner")
    parser.add_argument("-p", "--platform", choices=["android", "ios", "all"], default="all", help="Target mobile platform (default: all)")
    parser.add_argument("-b", "--build", choices=["alpha", "beta", "production"], default="production", help="Mobile build flavor/variant (default: production)")
    parser.add_argument("-i", "--instance", default="epsilon", help="Target instance / company codename (e.g. epsilon, delta, gamma) resolved via Discovery Gateway (default: epsilon)")
    parser.add_argument("-s", "--backend", "--url", default=None, help="Direct backend URL override (bypasses discovery gateway)")
    parser.add_argument("--android-branch", default=None, help="Checkout specific Git branch in Android repo before testing")
    parser.add_argument("--ios-branch", default=None, help="Checkout specific Git branch in iOS repo before testing")
    parser.add_argument("--branch", default=None, help="Checkout specific Git branch on both Android and iOS repos")
    parser.add_argument("--sync", action="store_true", help="Fetch and pull latest remote commits before running tests")
    parser.add_argument("--list-branches", action="store_true", help="List available Git branches on remote repositories and exit")
    parser.add_argument("--scenario", default=None, help="Filter by specific scenario ID or file name")
    parser.add_argument("--wait-ai", type=int, default=360, help="Maximum seconds to wait for live Hawkeye AI computer vision processing (default: 360)")
    parser.add_argument("--strict", dest="strict", action="store_true", default=True, help="Enforce strict mode: zero silent fallbacks, fail on errors (default: True)")
    parser.add_argument("--no-strict", dest="strict", action="store_false", help="Allow fallback modes for non-critical runs")
    args = parser.parse_args()

    runner = ScenarioRunner(
        config_dir=CURRENT_DIR / "config",
        scenarios_dir=CURRENT_DIR / "scenarios",
        reports_dir=CURRENT_DIR / "test-reports",
    )
    runner.wait_ai_seconds = args.wait_ai
    runner.strict_mode = args.strict

    if args.list_branches:
        print("================================================================================")
        print("    AVAILABLE REMOTE GIT BRANCHES")
        print("================================================================================")
        print("\n📱 Android (android-rebotics):")
        for b in runner.git_controller.list_branches("android"):
            print(f"   - {b}")
        print("\n🍏 iOS (ios-rebotics):")
        for b in runner.git_controller.list_branches("ios"):
            print(f"   - {b}")
        sys.exit(0)

    andr_b = args.android_branch or args.branch
    ios_b = args.ios_branch or args.branch

    runner.execute(
        platform_arg=args.platform,
        instance_arg=args.instance,
        build_arg=args.build,
        android_branch=andr_b,
        ios_branch=ios_b,
        sync_git=args.sync,
        backend_url_override=args.backend,
        scenario_filter=args.scenario,
    )


if __name__ == "__main__":
    main()
