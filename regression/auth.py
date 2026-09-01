"""Slice 2 — Auth smoke against https://{env}.rebotics.net."""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from regression.env import ResolvedEnvironment, resolve_base_url

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACCOUNTS_PATH = (
    REPO_ROOT
    / "mobile-backend-integration-tests"
    / "config"
    / "test-accounts.json"
)

# Avoid corporate TLS interception issues in lab environments (same pattern as runner).
_SSL_CTX = ssl._create_unverified_context()


class AuthSmokeError(Exception):
    def __init__(self, message: str, *, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


class AuthCredentialsMissing(AuthSmokeError):
    def __init__(self, message: str):
        super().__init__(message, exit_code=2)


@dataclass(frozen=True)
class AuthCredentials:
    username: str
    password: str
    device_id: str = "HEADLESS-REGRESSION-DEVICE-001"
    token_type: str = "simple"
    source: str = "env"


@dataclass(frozen=True)
class AuthSmokeResult:
    ok: bool
    env: str
    base_url: str
    skipped: bool
    username: Optional[str]
    user_id: Optional[Any]
    email: Optional[str]
    token_present: bool
    me_status: Optional[int]
    error: Optional[str]
    credential_source: Optional[str]

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_credentials(
    *,
    username: Optional[str] = None,
    password: Optional[str] = None,
    device_id: Optional[str] = None,
    accounts_path: Optional[Path] = None,
) -> AuthCredentials:
    """
    Credential precedence:
    1. Explicit username/password args
    2. REGRESSION_USERNAME / REGRESSION_PASSWORD (/ REGRESSION_DEVICE_ID)
    3. mobile-backend-integration-tests/config/test-accounts.json (gitignored)
    """
    user = (username or os.environ.get("REGRESSION_USERNAME") or "").strip()
    pwd = (password or os.environ.get("REGRESSION_PASSWORD") or "").strip()
    device = (
        device_id
        or os.environ.get("REGRESSION_DEVICE_ID")
        or "HEADLESS-REGRESSION-DEVICE-001"
    ).strip()

    if user and pwd:
        return AuthCredentials(
            username=user,
            password=pwd,
            device_id=device,
            source="cli_or_env",
        )

    path = accounts_path
    if path is None:
        env_path = (os.environ.get("REGRESSION_ACCOUNTS_PATH") or "").strip()
        path = Path(env_path) if env_path else DEFAULT_ACCOUNTS_PATH
    if path.is_file():
        raw = json.loads(path.read_text(encoding="utf-8"))
        account = (raw.get("accounts") or {}).get("standard_user") or {}
        user = str(account.get("username") or "").strip()
        pwd = str(account.get("password") or "").strip()
        if user and pwd and user != "YOUR_USERNAME" and pwd != "YOUR_PASSWORD":
            return AuthCredentials(
                username=user,
                password=pwd,
                device_id=str(account.get("deviceId") or device),
                token_type=str(account.get("tokenType") or "simple"),
                source=f"file:{path.name}",
            )

    raise AuthCredentialsMissing(
        "No credentials. Set REGRESSION_USERNAME and REGRESSION_PASSWORD, "
        "or create mobile-backend-integration-tests/config/test-accounts.json "
        "from test-accounts.example.json"
    )


def _http_json(
    method: str,
    url: str,
    *,
    headers: Dict[str, str],
    body: Optional[Dict[str, Any]] = None,
    timeout: float = 20.0,
) -> tuple[int, Dict[str, Any], str]:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            raw = resp.read().decode("utf-8")
            parsed: Dict[str, Any]
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {"_raw": raw}
            return resp.status, parsed, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"_raw": raw}
        return exc.code, parsed, raw


def run_auth_smoke(
    env: str,
    *,
    base_url_override: Optional[str] = None,
    credentials: Optional[AuthCredentials] = None,
    allow_mutate: bool = False,
) -> AuthSmokeResult:
    resolved: ResolvedEnvironment = resolve_base_url(
        env,
        base_url_override=base_url_override,
        allow_mutate=allow_mutate,
    )
    creds = credentials or load_credentials()

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Store Intelligence Regression AuthSmoke/0.1",
    }
    verify_url = f"{resolved.base_url}/api/v1/2fa/verify/"
    status, payload, _ = _http_json(
        "POST",
        verify_url,
        headers=headers,
        body={
            "username": creds.username,
            "password": creds.password,
            "device_id": creds.device_id,
            "token_type": creds.token_type,
        },
    )
    token = payload.get("token") or payload.get("access")
    if status >= 400 or not token:
        return AuthSmokeResult(
            ok=False,
            env=resolved.env,
            base_url=resolved.base_url,
            skipped=False,
            username=creds.username,
            user_id=None,
            email=None,
            token_present=False,
            me_status=None,
            error=f"Auth failed HTTP {status}: {payload}",
            credential_source=creds.source,
        )

    auth_header = (
        f"Bearer {token}" if payload.get("access") and not payload.get("token") else f"Token {token}"
    )
    me_headers = {**headers, "Authorization": auth_header}
    me_url = f"{resolved.base_url}/api/v4/me/"
    me_status, me_payload, _ = _http_json("GET", me_url, headers=me_headers)
    if me_status >= 400:
        return AuthSmokeResult(
            ok=False,
            env=resolved.env,
            base_url=resolved.base_url,
            skipped=False,
            username=creds.username,
            user_id=None,
            email=None,
            token_present=True,
            me_status=me_status,
            error=f"/me failed HTTP {me_status}: {me_payload}",
            credential_source=creds.source,
        )

    return AuthSmokeResult(
        ok=True,
        env=resolved.env,
        base_url=resolved.base_url,
        skipped=False,
        username=me_payload.get("username") or creds.username,
        user_id=me_payload.get("id"),
        email=me_payload.get("email"),
        token_present=True,
        me_status=me_status,
        error=None,
        credential_source=creds.source,
    )


def skipped_result(env: str, message: str, *, base_url: str = "") -> AuthSmokeResult:
    return AuthSmokeResult(
        ok=True,
        env=env,
        base_url=base_url,
        skipped=True,
        username=None,
        user_id=None,
        email=None,
        token_present=False,
        me_status=None,
        error=message,
        credential_source=None,
    )
