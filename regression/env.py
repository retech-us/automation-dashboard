"""Environment resolution: --env=X → https://X.rebotics.net"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

_ENV_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", re.IGNORECASE)

# Mutating automation blocked by default for these slugs / hosts.
_MUTATE_DENY_SLUGS = frozenset(
    {
        "production",
        "prod",
        "live",
        "www",
    }
)
_MUTATE_DENY_HOST_SUFFIXES = (
    "r3us-admin.rebotics.net",  # production admin gateway
)


@dataclass(frozen=True)
class ResolvedEnvironment:
    env: str
    base_url: str
    mutate_allowed: bool
    source: str  # "pattern" | "override" | "env_var"


class EnvironmentResolutionError(ValueError):
    pass


def normalize_env_slug(env: str) -> str:
    slug = (env or "").strip().lower()
    if not slug:
        raise EnvironmentResolutionError("Environment name is empty")
    if not _ENV_SLUG_RE.match(slug):
        raise EnvironmentResolutionError(
            f"Invalid environment slug {env!r}. Use letters, numbers, hyphens "
            "(e.g. epsilon, delta, gamma)."
        )
    return slug


def resolve_base_url(
    env: str,
    *,
    base_url_override: Optional[str] = None,
    allow_mutate: bool = False,
) -> ResolvedEnvironment:
    """
    Resolve a runnable Management API base URL.

    Default: https://{env}.rebotics.net
    Override: explicit base_url, or REGRESSION_BASE_URL env var.
    """
    override = (base_url_override or os.environ.get("REGRESSION_BASE_URL") or "").strip()
    if override:
        url = override.rstrip("/")
        _validate_http_url(url)
        slug = normalize_env_slug(env) if env and env.strip() else "custom"
        return ResolvedEnvironment(
            env=slug,
            base_url=url,
            mutate_allowed=_compute_mutate_allowed(slug, url, allow_mutate),
            source="override" if base_url_override else "env_var",
        )

    slug = normalize_env_slug(env)
    url = f"https://{slug}.rebotics.net"
    return ResolvedEnvironment(
        env=slug,
        base_url=url,
        mutate_allowed=_compute_mutate_allowed(slug, url, allow_mutate),
        source="pattern",
    )


def _validate_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise EnvironmentResolutionError(f"Invalid base URL: {url!r}")


def _compute_mutate_allowed(slug: str, url: str, allow_mutate: bool) -> bool:
    if allow_mutate:
        return True
    host = urlparse(url).netloc.lower()
    if slug in _MUTATE_DENY_SLUGS:
        return False
    if any(host == s or host.endswith("." + s) for s in _MUTATE_DENY_HOST_SUFFIXES):
        return False
    if host.endswith("-admin.rebotics.net") and "r3us" in host:
        return False
    return True
