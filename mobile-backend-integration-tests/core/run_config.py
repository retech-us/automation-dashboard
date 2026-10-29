"""
Shelf Intelligence Quality Automation — Run Configuration Engine.
Parses, validates, and models run configuration contracts (YAML/JSON) with dynamic
environment variable interpolation and zero credential leakage.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# Optional YAML support with JSON fallback
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
import json


ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z0-9_]+)(?::-([^}]*))?\}")


def expand_env_vars(content: str) -> str:
    """
    Substitutes environment variables in strings:
    - ${VAR_NAME} -> os.environ.get("VAR_NAME", "")
    - ${VAR_NAME:-default} -> os.environ.get("VAR_NAME", "default")
    """
    def _replacer(match: re.Match) -> str:
        var_name = match.group(1)
        default_val = match.group(2) if match.group(2) is not None else ""
        return os.environ.get(var_name, default_val)

    return ENV_VAR_PATTERN.sub(_replacer, content)


@dataclass
class SourceConfig:
    repository: str = "backend"  # "backend", "android", "ios", "all"
    branch: str = "current"       # "develop", "master", or "current"
    commit: str = "auto"          # "auto" or specific 40-char SHA
    sync_remote: bool = False

    def validate(self):
        valid_repos = ("backend", "android", "ios", "all", "rebotics-management-django", "android-rebotics", "ios-rebotics")
        if self.repository.lower() not in valid_repos:
            raise ValueError(
                f"Invalid source repository: '{self.repository}'. Expected one of: {list(valid_repos)}"
            )


@dataclass
class AuthConfig:
    username_env: str = "TEST_USERNAME"
    password_env: str = "TEST_PASSWORD"
    token_env: str = "TEST_TOKEN"
    device_id: str = "d422969d-7d77-45de-953d-a4435abcd6dc"

    def resolve_credentials(self) -> Dict[str, Optional[str]]:
        """Resolves credentials dynamically from environment variables."""
        return {
            "username": os.environ.get(self.username_env),
            "password": os.environ.get(self.password_env),
            "token": os.environ.get(self.token_env),
            "device_id": self.device_id,
        }

    def has_credentials(self) -> bool:
        creds = self.resolve_credentials()
        return bool(creds.get("token") or (creds.get("username") and creds.get("password")))


@dataclass
class TargetConfig:
    name: str = "epsilon"        # "epsilon", "krcs", "harr", "custom"
    base_url: str = "https://epsilon.rebotics.net"
    api_prefix: str = "/api/v1"
    auth: AuthConfig = field(default_factory=AuthConfig)

    def validate(self):
        parsed = urlparse(self.base_url)
        if not parsed.scheme or parsed.scheme not in ("http", "https"):
            raise ValueError(f"Target base_url must have a valid http or https scheme. Got: '{self.base_url}'")
        if not parsed.netloc:
            raise ValueError(f"Target base_url missing hostname. Got: '{self.base_url}'")


@dataclass
class TestsConfig:
    scope: str = "regression"    # "smoke", "rules", "api", "ai_benchmark", "regression"
    scenarios: List[str] = field(default_factory=list)
    filter_tags: List[str] = field(default_factory=list)

    def validate(self):
        valid_scopes = ("smoke", "rules", "api", "ai_benchmark", "regression", "workflow", "rescan", "all")
        if self.scope.lower() not in valid_scopes:
            raise ValueError(f"Invalid test scope: '{self.scope}'. Expected one of: {valid_scopes}")


@dataclass
class ExecutionConfig:
    mode: str = "dry_run"        # "dry_run" (safe read-only) or "live"
    allow_state_changes: bool = False
    timeout_seconds: int = 300
    retry_count: int = 1
    platform: str = "all"        # "android", "ios", "all"

    def validate(self):
        if self.mode not in ("dry_run", "live"):
            raise ValueError(f"Invalid execution mode: '{self.mode}'. Expected 'dry_run' or 'live'.")
        if self.platform not in ("android", "ios", "all"):
            raise ValueError(f"Invalid platform: '{self.platform}'. Expected 'android', 'ios', or 'all'.")


@dataclass
class RunConfig:
    version: str = "1.0"
    source: SourceConfig = field(default_factory=SourceConfig)
    target: TargetConfig = field(default_factory=TargetConfig)
    tests: TestsConfig = field(default_factory=TestsConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self):
        self.source.validate()
        self.target.validate()
        self.tests.validate()
        self.execution.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RunConfig:
        source_data = data.get("source", {})
        target_data = data.get("target", {})
        tests_data = data.get("tests", {})
        exec_data = data.get("execution", {})

        auth_data = target_data.get("auth", {})
        auth_cfg = AuthConfig(
            username_env=auth_data.get("username_env", "TEST_USERNAME"),
            password_env=auth_data.get("password_env", "TEST_PASSWORD"),
            token_env=auth_data.get("token_env", "TEST_TOKEN"),
            device_id=auth_data.get("device_id", "d422969d-7d77-45de-953d-a4435abcd6dc"),
        )

        source_cfg = SourceConfig(
            repository=source_data.get("repository", "backend"),
            branch=source_data.get("branch", "current"),
            commit=source_data.get("commit", "auto"),
            sync_remote=bool(source_data.get("sync_remote", False)),
        )

        target_cfg = TargetConfig(
            name=target_data.get("name", "epsilon"),
            base_url=target_data.get("base_url", "https://epsilon.rebotics.net"),
            api_prefix=target_data.get("api_prefix", "/api/v1"),
            auth=auth_cfg,
        )

        tests_cfg = TestsConfig(
            scope=tests_data.get("scope", "regression"),
            scenarios=tests_data.get("scenarios", []) or [],
            filter_tags=tests_data.get("filter_tags", []) or [],
        )

        exec_cfg = ExecutionConfig(
            mode=exec_data.get("mode", "dry_run"),
            allow_state_changes=bool(exec_data.get("allow_state_changes", False)),
            timeout_seconds=int(exec_data.get("timeout_seconds", 300)),
            retry_count=int(exec_data.get("retry_count", 1)),
            platform=exec_data.get("platform", "all"),
        )

        cfg = cls(
            version=str(data.get("version", "1.0")),
            source=source_cfg,
            target=target_cfg,
            tests=tests_cfg,
            execution=exec_cfg,
            metadata=data.get("metadata", {}) or {},
        )
        cfg.validate()
        return cfg

    @classmethod
    def from_file(cls, path_or_str: str | Path) -> RunConfig:
        file_path = Path(path_or_str)
        if not file_path.exists():
            raise FileNotFoundError(f"Run configuration file not found: {file_path}")

        raw_text = file_path.read_text(encoding="utf-8")
        interpolated = expand_env_vars(raw_text)

        if file_path.suffix.lower() in (".yaml", ".yml"):
            if not HAS_YAML:
                # Basic fallback if pyyaml is unavailable
                raise RuntimeError("PyYAML is not installed. Use JSON config or install PyYAML.")
            parsed = yaml.safe_load(interpolated)
        else:
            parsed = json.loads(interpolated)

        if not isinstance(parsed, dict):
            raise ValueError(f"Configuration file must contain a top-level mapping/object, got {type(parsed)}")

        return cls.from_dict(parsed)

    def to_safe_dict(self) -> Dict[str, Any]:
        """Serializes configuration for logging and reports without sensitive data."""
        data = asdict(self)
        # Ensure password or tokens are never present in output
        auth_dict = data.get("target", {}).get("auth", {})
        auth_dict["credentials_configured"] = self.target.auth.has_credentials()
        return data
