"""
Shelf Intelligence Quality Automation — Preflight Validation Engine.
Performs safe, non-destructive pre-test verification of run configuration, Git commit
resolution, target base URL format, credential readiness, and state mutation guards.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from core.git_source_controller import GitSourceController
from core.run_config import RunConfig


@dataclass
class PreflightResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    resolved_sources: Dict[str, Any] = field(default_factory=dict)
    target_summary: Dict[str, Any] = field(default_factory=dict)
    execution_manifest: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PreflightValidator:
    """
    Validates run configuration before any test execution starts.
    Guarantees no state changes occur during preflight.
    """

    def __init__(self, git_controller: Optional[GitSourceController] = None):
        self.git = git_controller or GitSourceController()

    def validate(self, config: RunConfig, check_connectivity: bool = False) -> PreflightResult:
        errors: List[str] = []
        warnings: List[str] = []
        resolved_sources: Dict[str, Any] = {}

        # 1. Validate Configuration Syntax and Bounds
        try:
            config.validate()
        except ValueError as e:
            errors.append(f"Configuration error: {str(e)}")

        # 2. Resolve Source Revisions (Git branch & commit resolution)
        target_repo = config.source.repository.lower()
        repos_to_resolve = []
        if target_repo == "all":
            repos_to_resolve = ["backend", "android", "ios"]
        elif target_repo in ("backend", "android", "ios"):
            repos_to_resolve = [target_repo]
        else:
            errors.append(f"Unsupported source repository for resolution: '{config.source.repository}'")

        for r in repos_to_resolve:
            try:
                res = self.git.resolve_revision(
                    repo_name=r,
                    branch=config.source.branch,
                    commit=config.source.commit,
                )
                if not res.get("resolved_cleanly"):
                    errors.append(f"Failed to resolve Git revision for '{r}': {res.get('error')}")
                else:
                    resolved_sources[r] = {
                        "repo_name": res["repo_name"],
                        "repo_path": res["repo_path"],
                        "target_ref": res["target_ref"],
                        "resolved_sha": res["resolved_sha"],
                        "short_sha": res["short_sha"],
                        "commit_author": res["commit_author"],
                        "commit_date": res["commit_date"],
                        "commit_message": res["commit_message"],
                        "branch": res["selected_branch"],
                    }
            except Exception as e:
                errors.append(f"Exception resolving Git repo '{r}': {str(e)}")

        # 3. Target Base URL & Identity Validation
        parsed_url = urlparse(config.target.base_url)
        if not parsed_url.scheme or parsed_url.scheme not in ("http", "https"):
            errors.append(f"Invalid target URL scheme: '{parsed_url.scheme}'. Must be 'http' or 'https'.")
        if not parsed_url.netloc:
            errors.append(f"Invalid target URL missing host: '{config.target.base_url}'")

        target_summary = {
            "name": config.target.name,
            "base_url": config.target.base_url,
            "api_prefix": config.target.api_prefix,
            "hostname": parsed_url.netloc,
            "is_secure": parsed_url.scheme == "https",
        }

        # 4. Credential & Auth Readiness Check
        creds = config.target.auth.resolve_credentials()
        has_auth = bool(creds.get("token") or (creds.get("username") and creds.get("password")))
        target_summary["auth_configured"] = has_auth

        if config.execution.mode == "live" and not has_auth:
            errors.append(
                f"Execution mode is 'live' but no authentication credentials found. "
                f"Ensure {config.target.auth.username_env} and {config.target.auth.password_env} "
                f"or {config.target.auth.token_env} are set."
            )
        elif not has_auth:
            warnings.append(
                "No environment credentials configured. Executing in simulated/mock mode."
            )

        # 5. Mutation Guard & State Safety Validation
        is_dry_run = config.execution.mode == "dry_run"
        allows_changes = config.execution.allow_state_changes

        if not allows_changes and config.execution.mode == "live":
            # Live mode with allow_state_changes=False must ensure safe scopes
            if config.tests.scope in ("workflow", "rescan"):
                errors.append(
                    f"Selected scope '{config.tests.scope}' modifies application state, "
                    f"but 'allow_state_changes' is set to False. Aborting preflight."
                )

        # 6. Optional Read-Only Network Connectivity Verification
        if check_connectivity and not errors:
            test_endpoint = f"{config.target.base_url.rstrip('/')}{config.target.api_prefix}/users/password/"
            try:
                req = urllib.request.Request(
                    test_endpoint,
                    headers={"User-Agent": "Shelf-Intelligence-Preflight/1.0", "Accept": "application/json"},
                    method="GET",
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    target_summary["reachability"] = f"HTTP {resp.status}"
            except urllib.error.HTTPError as he:
                # 401 or 403 or 405 proves the server is reachable and active
                target_summary["reachability"] = f"HTTP {he.code} (Reachable)"
            except Exception as e:
                errors.append(f"Network connectivity check failed for target base_url '{config.target.base_url}': {str(e)}")

        execution_manifest = {
            "mode": config.execution.mode,
            "allow_state_changes": config.execution.allow_state_changes,
            "scope": config.tests.scope,
            "platform": config.execution.platform,
            "timeout_seconds": config.execution.timeout_seconds,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        }

        is_valid = len(errors) == 0

        return PreflightResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            resolved_sources=resolved_sources,
            target_summary=target_summary,
            execution_manifest=execution_manifest,
        )
