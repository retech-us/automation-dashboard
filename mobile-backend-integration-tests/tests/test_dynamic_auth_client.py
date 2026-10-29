"""
Unit tests for DynamicAuthClient: runtime login, in-memory caching, token expiration, and auth headers.
"""

import os
import time
import unittest
from unittest.mock import MagicMock, patch

from core.dynamic_auth_client import CachedAuthToken, DynamicAuthClient


class DynamicAuthClientTests(unittest.TestCase):
    def setUp(self):
        DynamicAuthClient._cached_tokens.clear()

    def test_cached_auth_token_expiration(self):
        token = CachedAuthToken(
            token="test_tok_123",
            token_type="Token",
            obtained_at=time.time() - 4000,
            ttl_seconds=3600,
        )
        self.assertTrue(token.is_expired)
        self.assertEqual(token.auth_header, "Token test_tok_123")

    def test_cached_auth_token_fresh(self):
        token = CachedAuthToken(
            token="test_tok_fresh",
            token_type="Bearer",
            obtained_at=time.time(),
            ttl_seconds=3600,
        )
        self.assertFalse(token.is_expired)
        self.assertEqual(token.auth_header, "Bearer test_tok_fresh")

    def test_env_token_override_when_no_credentials(self):
        with patch.dict(os.environ, {"REBOTICS_AUTH_TOKEN": "env_secret_token_abc"}):
            client = DynamicAuthClient(base_url="https://test.rebotics.net")
            tok = client.get_auth_token()
            self.assertEqual(tok, "env_secret_token_abc")
            headers = client.get_auth_header()
            self.assertEqual(headers.get("Authorization"), "Token env_secret_token_abc")

    @patch("core.dynamic_auth_client.urllib.request.urlopen")
    def test_dynamic_login_via_2fa_verify(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"token": "dynamic_2fa_token_xyz"}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        client = DynamicAuthClient(
            base_url="https://krcs.rebotics.net",
            username="test_associate",
            password="test_password_123",
        )
        token = client.get_auth_token()
        self.assertEqual(token, "dynamic_2fa_token_xyz")

        # Second call must use in-memory cache without calling urlopen again
        token_cached = client.get_auth_token()
        self.assertEqual(token_cached, "dynamic_2fa_token_xyz")
        mock_urlopen.assert_called_once()

    @patch("core.dynamic_auth_client.urllib.request.urlopen")
    def test_dynamic_login_fallback_to_jwt_token(self, mock_urlopen):
        import urllib.error

        # First call to /2fa/verify/ fails with 404
        # Second call to /token/ succeeds with JWT access token
        error_resp = urllib.error.HTTPError(
            url="https://test.rebotics.net/api/v1/2fa/verify/",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )
        success_resp = MagicMock()
        success_resp.read.return_value = b'{"access": "jwt_access_token_789"}'
        success_resp.__enter__.return_value = success_resp

        mock_urlopen.side_effect = [error_resp, success_resp]

        client = DynamicAuthClient(
            base_url="https://test.rebotics.net",
            username="test_jwt_user",
            password="test_password_jwt",
        )
        token = client.get_auth_token()
        self.assertEqual(token, "jwt_access_token_789")
        headers = client.get_auth_header()
        self.assertEqual(headers.get("Authorization"), "Bearer jwt_access_token_789")


if __name__ == "__main__":
    unittest.main()
