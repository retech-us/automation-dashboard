#!/usr/bin/env python3
"""Regression platform CLI — Slices 1–7 (tools + CI PR bot)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from regression.action_list import ActionListError, run_action_list_check
from regression.auth import (
    AuthCredentialsMissing,
    AuthSmokeError,
    load_credentials,
    run_auth_smoke,
    skipped_result,
)
from regression.domain_parity import DomainParityError, run_domain_parity
from regression.env import EnvironmentResolutionError, resolve_base_url
from regression.image_catalog import ImageCatalog, ImageCatalogError
from regression.impact import ImpactError
from regression.pr_bot import (
    PrBotError,
    git_changed_files,
    post_github_comment,
    render_pr_comment,
    run_pr_bot,
)
from regression.provisioner import ProvisionerError, run_provision
from regression.tools import invoke_tool, list_tools_payload
from regression.tools_http import serve_forever


def cmd_resolve_env(args: argparse.Namespace) -> int:
    try:
        resolved = resolve_base_url(
            args.env,
            base_url_override=args.base_url,
            allow_mutate=args.allow_mutate,
        )
    except EnvironmentResolutionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    payload = {
        "env": resolved.env,
        "base_url": resolved.base_url,
        "mutate_allowed": resolved.mutate_allowed,
        "source": resolved.source,
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_resolve_images(args: argparse.Namespace) -> int:
    try:
        catalog = ImageCatalog.load(
            Path(args.catalog) if args.catalog else None,
            repo_root=ROOT,
        )
        bays = [int(x) for x in args.bays.split(",") if x.strip()]
        resolutions = catalog.resolve_bays(
            category=args.category,
            bays=bays,
            stage=args.stage,
            require_file_exists=not args.allow_missing_files,
        )
    except (ImageCatalogError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    payload = {
        "category": args.category,
        "stage": args.stage,
        "images": [r.entry.as_dict() for r in resolutions],
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_auth_smoke(args: argparse.Namespace) -> int:
    try:
        if args.skip_if_no_creds:
            try:
                load_credentials(username=args.username, password=args.password)
            except AuthCredentialsMissing as exc:
                resolved = resolve_base_url(args.env, base_url_override=args.base_url)
                result = skipped_result(resolved.env, str(exc), base_url=resolved.base_url)
                print(json.dumps(result.as_dict(), indent=2))
                return 0

        result = run_auth_smoke(
            args.env,
            base_url_override=args.base_url,
            credentials=load_credentials(username=args.username, password=args.password),
            allow_mutate=args.allow_mutate,
        )
    except AuthCredentialsMissing as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (AuthSmokeError, EnvironmentResolutionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return getattr(exc, "exit_code", 1)

    print(json.dumps(result.as_dict(), indent=2))
    if result.skipped:
        return 0
    return 0 if result.ok else 1


def cmd_provision(args: argparse.Namespace) -> int:
    bays = [int(x) for x in args.bays.split(",") if x.strip()]
    dry_run = not args.execute
    try:
        result = run_provision(
            env=args.env,
            category=args.category,
            bays=bays,
            stage=args.stage,
            store_id=args.store_id,
            task_id=args.task_id,
            pog_id=args.pog_id,
            category_id=args.category_id,
            category_name=args.category_name,
            base_url_override=args.base_url,
            dry_run=dry_run,
        )
    except ProvisionerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return int(exc.exit_code)
    except AuthCredentialsMissing as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ImageCatalogError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result.as_dict(), indent=2))
    return 0 if result.ok else 1


def cmd_action_list(args: argparse.Namespace) -> int:
    payload_override = None
    if args.fixture:
        fixture_path = Path(args.fixture)
        if not fixture_path.is_file():
            print(f"ERROR: Fixture not found: {fixture_path}", file=sys.stderr)
            return 2
        payload_override = json.loads(fixture_path.read_text(encoding="utf-8"))

    try:
        result = run_action_list_check(
            env=args.env,
            task_id=args.task_id,
            base_url_override=args.base_url,
            credentials=(
                None
                if payload_override is not None
                else load_credentials(username=args.username, password=args.password)
            ),
            payload_override=payload_override,
            strict_unknown_actions=args.strict_unknown_actions,
            contract_path=Path(args.contract) if args.contract else None,
        )
    except AuthCredentialsMissing as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (ActionListError, EnvironmentResolutionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return getattr(exc, "exit_code", 1)

    print(json.dumps(result.as_dict(), indent=2))
    return 0 if result.ok else 1


def cmd_domain_parity(args: argparse.Namespace) -> int:
    payload_override = None
    if args.fixture:
        fixture_path = Path(args.fixture)
        if not fixture_path.is_file():
            print(f"ERROR: Fixture not found: {fixture_path}", file=sys.stderr)
            return 2
        payload_override = json.loads(fixture_path.read_text(encoding="utf-8"))

    try:
        result = run_domain_parity(
            env=args.env,
            task_id=args.task_id,
            base_url_override=args.base_url,
            credentials=(
                None
                if payload_override is not None or args.task_id is None
                else load_credentials(username=args.username, password=args.password)
            ),
            payload_override=payload_override,
            case=args.case,
            baseline_path=Path(args.baseline) if args.baseline else None,
            include_completed=args.include_completed,
        )
    except AuthCredentialsMissing as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (DomainParityError, EnvironmentResolutionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return getattr(exc, "exit_code", 1)

    print(json.dumps(result.as_dict(), indent=2))
    return 0 if result.ok else 1


def cmd_tools_list(_args: argparse.Namespace) -> int:
    print(json.dumps(list_tools_payload(), indent=2))
    return 0


def cmd_tools_call(args: argparse.Namespace) -> int:
    tool_args: dict = {}
    if args.args_json:
        try:
            parsed = json.loads(args.args_json)
        except json.JSONDecodeError as exc:
            print(f"ERROR: Invalid --args-json: {exc}", file=sys.stderr)
            return 2
        if not isinstance(parsed, dict):
            print("ERROR: --args-json must be a JSON object", file=sys.stderr)
            return 2
        tool_args = parsed
    if args.args_file:
        path = Path(args.args_file)
        if not path.is_file():
            print(f"ERROR: args file not found: {path}", file=sys.stderr)
            return 2
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"ERROR: Invalid args file JSON: {exc}", file=sys.stderr)
            return 2
        if not isinstance(parsed, dict):
            print("ERROR: args file must contain a JSON object", file=sys.stderr)
            return 2
        tool_args.update(parsed)

    resp = invoke_tool(args.name, tool_args)
    print(json.dumps(resp.as_dict(), indent=2))
    return int(resp.exit_code)


def cmd_tools_serve(args: argparse.Namespace) -> int:
    serve_forever(host=args.host, port=args.port)
    return 0


def cmd_pr_bot_run(args: argparse.Namespace) -> int:
    changed: list[str] = []
    if args.changed_file:
        changed.extend(args.changed_file)
    if args.git_base:
        try:
            changed.extend(git_changed_files(base_ref=args.git_base))
        except ImpactError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return int(exc.exit_code)

    try:
        report = run_pr_bot(
            env=args.env,
            mode=args.mode,
            changed_files=changed,
            pr_number=args.pr,
            head_sha=args.sha,
            include_auth_optional=args.include_auth,
        )
    except (PrBotError, ImpactError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return getattr(exc, "exit_code", 1)

    comment = render_pr_comment(report)
    if args.comment_out:
        Path(args.comment_out).write_text(comment, encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(report.as_dict(), indent=2) + "\n", encoding="utf-8"
        )

    payload = report.as_dict()
    payload["comment_markdown"] = comment
    print(json.dumps(payload, indent=2))

    if args.post_comment:
        if not args.pr:
            print("ERROR: --post-comment requires --pr", file=sys.stderr)
            return 2
        posted = post_github_comment(body=comment, pr_number=str(args.pr))
        print(json.dumps({"comment_post": posted}, indent=2))
        if not posted.get("ok"):
            # Comment failure is infra (2), not product fail — preserve tool verdict exit
            if report.ok:
                return 2
    return int(report.exit_code)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="regression",
        description="Regression platform CLI (Slices 1–7)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_env = sub.add_parser("resolve-env", help="Resolve --env to base URL")
    p_env.add_argument("--env", required=True, help="Instance slug (e.g. epsilon)")
    p_env.add_argument("--base-url", default=None, help="Optional full URL override")
    p_env.add_argument(
        "--allow-mutate",
        action="store_true",
        help="Allow mutate flag even for denied production-like targets",
    )
    p_env.set_defaults(func=cmd_resolve_env)

    p_img = sub.add_parser(
        "resolve-images",
        help="Resolve scan images by planogram category + bay + stage",
    )
    p_img.add_argument("--category", required=True, help="Planogram category (e.g. pasta, deli)")
    p_img.add_argument("--bays", default="1", help="Comma-separated bay numbers (default: 1)")
    p_img.add_argument("--stage", default="pre_photo", help="pre_photo | post_photo")
    p_img.add_argument("--catalog", default=None, help="Path to image-catalog.yaml")
    p_img.add_argument(
        "--allow-missing-files",
        action="store_true",
        help="Do not require image files to exist on disk",
    )
    p_img.set_defaults(func=cmd_resolve_images)

    p_auth = sub.add_parser(
        "auth-smoke",
        help="Login via /api/v1/2fa/verify/ then GET /api/v4/me/",
    )
    p_auth.add_argument("--env", required=True, help="Instance slug (e.g. epsilon)")
    p_auth.add_argument("--base-url", default=None, help="Optional full URL override")
    p_auth.add_argument("--username", default=None, help="Override username")
    p_auth.add_argument("--password", default=None, help="Override password")
    p_auth.add_argument(
        "--skip-if-no-creds",
        action="store_true",
        help="Exit 0 with skipped=true when credentials are missing",
    )
    p_auth.add_argument("--allow-mutate", action="store_true")
    p_auth.set_defaults(func=cmd_auth_smoke)

    p_prov = sub.add_parser(
        "provision",
        help="Plan/execute IR data provision with catalog-matched images",
    )
    p_prov.add_argument("--env", required=True)
    p_prov.add_argument("--category", required=True, help="Planogram category (pasta, deli, …)")
    p_prov.add_argument("--bays", default="1", help="Comma-separated bay numbers")
    p_prov.add_argument("--stage", default="pre_photo")
    p_prov.add_argument("--store-id", type=int, default=None)
    p_prov.add_argument("--task-id", type=int, default=None, help="Existing task (select mode)")
    p_prov.add_argument("--pog-id", type=int, default=None, help="Store planogram id for uploads")
    p_prov.add_argument("--category-id", type=int, default=None, help="Required for --execute create")
    p_prov.add_argument("--category-name", default=None)
    p_prov.add_argument("--base-url", default=None)
    p_prov.add_argument(
        "--execute",
        action="store_true",
        help="Mutate backend (default is dry-run plan only)",
    )
    p_prov.set_defaults(func=cmd_provision)

    p_al = sub.add_parser(
        "action-list",
        help="Fetch retailer action-list and assert contract baseline",
    )
    p_al.add_argument("--env", required=True, help="Instance slug (e.g. epsilon)")
    p_al.add_argument("--task-id", type=int, required=True, help="Task id")
    p_al.add_argument("--base-url", default=None)
    p_al.add_argument("--username", default=None)
    p_al.add_argument("--password", default=None)
    p_al.add_argument(
        "--fixture",
        default=None,
        help="Offline JSON fixture (skip live fetch)",
    )
    p_al.add_argument(
        "--contract",
        default=None,
        help="Override path to action_list_retailer_contract.yaml",
    )
    p_al.add_argument(
        "--strict-unknown-actions",
        action="store_true",
        help="Treat unknown action tokens as hard failures",
    )
    p_al.set_defaults(func=cmd_action_list)

    p_dp = sub.add_parser(
        "domain-parity",
        help="Map action-list via interim mobile domain mapper; assert Android CAT1 counts",
    )
    p_dp.add_argument("--env", required=True, help="Instance slug (e.g. epsilon)")
    p_dp.add_argument("--task-id", type=int, default=None, help="Live task id (report mode)")
    p_dp.add_argument("--base-url", default=None)
    p_dp.add_argument("--username", default=None)
    p_dp.add_argument("--password", default=None)
    p_dp.add_argument(
        "--fixture",
        default=None,
        help="Offline JSON action-list fixture (assert against --case expectations)",
    )
    p_dp.add_argument(
        "--case",
        default="cat1_t5_mixed",
        help="Baseline case id (default: cat1_t5_mixed)",
    )
    p_dp.add_argument(
        "--baseline",
        default=None,
        help="Override path to domain_count_parity.yaml",
    )
    p_dp.add_argument(
        "--include-completed",
        action="store_true",
        help="Include non-IDLE items in domain transform",
    )
    p_dp.set_defaults(func=cmd_domain_parity)

    p_tools = sub.add_parser(
        "tools",
        help="Agent tools JSON API (list / call / serve)",
    )
    tools_sub = p_tools.add_subparsers(dest="tools_command", required=True)

    p_tl = tools_sub.add_parser("list", help="List tool specs (JSON)")
    p_tl.set_defaults(func=cmd_tools_list)

    p_tc = tools_sub.add_parser("call", help="Invoke a tool with JSON args")
    p_tc.add_argument("name", help="Tool name (e.g. resolve_env, domain_parity)")
    p_tc.add_argument(
        "--args-json",
        default=None,
        help='Inline JSON object, e.g. \'{"env":"epsilon"}\'',
    )
    p_tc.add_argument("--args-file", default=None, help="Path to JSON args object")
    p_tc.set_defaults(func=cmd_tools_call)

    p_ts = tools_sub.add_parser("serve", help="Serve HTTP JSON tools API")
    p_ts.add_argument("--host", default="127.0.0.1")
    p_ts.add_argument("--port", type=int, default=8765)
    p_ts.set_defaults(func=cmd_tools_serve)

    p_bot = sub.add_parser(
        "pr-bot",
        help="CI PR bot — run judgement pack + render comment (GenAI-first surface)",
    )
    bot_sub = p_bot.add_subparsers(dest="pr_bot_command", required=True)

    p_run = bot_sub.add_parser("run", help="Select packs, invoke tools, emit JSON + markdown")
    p_run.add_argument("--env", default="epsilon")
    p_run.add_argument(
        "--mode",
        choices=["smoke", "impacted", "full"],
        default="smoke",
        help="smoke=offline Gate A; impacted=path rules; full=smoke+auth_optional",
    )
    p_run.add_argument(
        "--changed-file",
        action="append",
        default=[],
        help="Changed path (repeatable); used with --mode=impacted",
    )
    p_run.add_argument(
        "--git-base",
        default=None,
        help="Git base ref for changed files (e.g. origin/master)",
    )
    p_run.add_argument("--pr", default=None, help="PR number for comment metadata/posting")
    p_run.add_argument("--sha", default=None, help="Head SHA for comment footer")
    p_run.add_argument("--include-auth", action="store_true", help="Also run auth_optional pack")
    p_run.add_argument("--json-out", default=None, help="Write machine report JSON")
    p_run.add_argument("--comment-out", default=None, help="Write PR comment markdown")
    p_run.add_argument(
        "--post-comment",
        action="store_true",
        help="Post comment via gh (requires --pr and gh auth)",
    )
    p_run.set_defaults(func=cmd_pr_bot_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
