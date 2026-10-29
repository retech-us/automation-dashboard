"""
Dynamic Runtime Authentication Client for Shelf Intelligence E2E Automation.
Enables zero-static-token runtime login via 2FA verify / JWT token endpoints,
with in-memory token caching and automatic expiration management.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("dynamic_auth")

DEFAULT_DEVICE_ID = "d422969d-7d77-45de-953d-a4435abcd6dc"
DEFAULT_VERIFICATION_CODE = "000000"


@dataclass
class CachedAuthToken:
    token: str
    token_type: str  # "Token" or "Bearer"
    obtained_at: float
    ttl_seconds: float = 3600.0  # 1 hour default TTL

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.obtained_at) >= self.ttl_seconds

    @property
    def auth_header(self) -> str:
        return f"{self.token_type} {self.token}"


class DynamicAuthClient:
    """
    Handles dynamic runtime authentication against Rebotics backend instances.
    Eliminates static hardcoded tokens by authenticating dynamically using credentials.
    """

    _cached_tokens: Dict[str, CachedAuthToken] = {}

    def __init__(
        self,
        base_url: str = "https://krcs.rebotics.net",
        username: Optional[str] = None,
        password: Optional[str] = None,
        device_id: Optional[str] = None,
        verification_code: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username or os.environ.get("TEST_USERNAME")
        self.password = password or os.environ.get("TEST_PASSWORD")
        self.device_id = device_id or os.environ.get("TEST_DEVICE_ID", DEFAULT_DEVICE_ID)
        self.verification_code = (
            verification_code
            or os.environ.get("TEST_VERIFICATION_CODE", DEFAULT_VERIFICATION_CODE)
        )

    def get_auth_token(self, force_refresh: bool = False) -> str:
        """
        Returns a valid authentication token.
        Uses in-memory cache if fresh, otherwise triggers dynamic runtime login.
        """
        cache_key = self.base_url.lower()
        cached = self._cached_tokens.get(cache_key)

        if cached and not cached.is_expired and not force_refresh:
            return cached.token

        # Check if a static token exists in environment as an override
        env_token = (
            os.environ.get("REBOTICS_AUTH_TOKEN")
            or os.environ.get("TEST_INGESTION_TOKEN")
            or os.environ.get("TEST_TOKEN")
        )
        if env_token and not (self.username and self.password):
            return env_token

        # Perform dynamic login
        if self.username and self.password:
            token, token_type = self._login_dynamic()
            self._cached_tokens[cache_key] = CachedAuthToken(
                token=token,
                token_type=token_type,
                obtained_at=time.time(),
            )
            return token

        # If static token exists as fallback, return it
        if env_token:
            return env_token

        return ""

    def get_auth_header(self) -> Dict[str, str]:
        """Returns standard Authorization header dict for HTTP requests."""
        token = self.get_auth_token()
        if not token:
            return {}

        cache_key = self.base_url.lower()
        cached = self._cached_tokens.get(cache_key)
        prefix = cached.token_type if cached else "Token"
        return {"Authorization": f"{prefix} {token}"}

    def _login_dynamic(self) -> tuple[str, str]:
        """
        Attempts dynamic login:
        1. Tries 2FA verify endpoint: POST /api/v1/2fa/verify/
        2. Fallback to JWT obtain pair: POST /api/v1/token/
        """
        # Primary strategy: 2FA verify endpoint (returns simple DRF token)
        verify_url = f"{self.base_url}/api/v1/2fa/verify/"
        payload_2fa = {
            "username": self.username,
            "password": self.password,
            "device_id": self.device_id,
            "verification_code": self.verification_code,
            "token_type": "simple",
        }

        try:
            req = urllib.request.Request(
                verify_url,
                data=json.dumps(payload_2fa).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "ShelfIntelligenceE2E/DynamicAuth",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                token = data.get("token") or data.get("key")
                if token:
                    logger.info("Dynamic runtime login succeeded via /api/v1/2fa/verify/")
                    return token, "Token"
        except urllib.error.HTTPError as e:
            # If 404 or method not allowed, try fallback to /api/v1/token/
            logger.debug(f"/api/v1/2fa/verify/ returned HTTP {e.code}. Attempting JWT fallback...")
        except Exception as e:
            logger.warning(f"Error during /api/v1/2fa/verify/ request: {e}")

        # Fallback strategy: SimpleJWT endpoint POST /api/v1/token/
        jwt_url = f"{self.base_url}/api/v1/token/"
        payload_jwt = {
            "username": self.username,
            "password": self.password,
        }
        try:
            req = urllib.request.Request(
                jwt_url,
                data=json.dumps(payload_jwt).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "ShelfIntelligenceE2E/DynamicAuth",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                access_token = data.get("access") or data.get("token")
                if access_token:
                    logger.info("Dynamic runtime login succeeded via /api/v1/token/")
                    return access_token, "Bearer"
        except Exception as e:
            raise RuntimeError(
                f"Dynamic runtime login failed against {self.base_url}. "
                f"Verify TEST_USERNAME and TEST_PASSWORD: {e}"
            ) from e

        raise RuntimeError(f"Could not acquire token from {self.base_url} responses.")
