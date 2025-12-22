"""GitHub App authentication.

Implements App JWT signing and installation token exchange.
Secrets (private key content, tokens, installation IDs) must never be exposed.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
import jwt

from .config import AppConfig
from .errors import SafeError


@dataclass(frozen=True, slots=True)
class InstallationToken:
    """Cached installation access token + expiry."""

    token: str
    expires_at: datetime


class GitHubAppAuth:
    """Manages GitHub App JWT creation and installation token caching."""

    def __init__(self, *, config: AppConfig, transport: httpx.AsyncBaseTransport | None = None) -> None:
        """Create an auth helper for a single app installation."""
        self._config = config
        self._transport = transport
        self._lock = asyncio.Lock()
        self._cached: InstallationToken | None = None

    def _build_app_jwt(self) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=10)).timestamp()),
            "iss": self._config.app_id,
        }
        private_key_pem = self._config.private_key_path.read_text(encoding="utf-8")
        return jwt.encode(payload, private_key_pem, algorithm="RS256")

    async def get_installation_token(self) -> str:
        """Get a valid installation access token (refreshing if needed)."""
        async with self._lock:
            if self._cached is not None:
                remaining = (self._cached.expires_at - datetime.now(timezone.utc)).total_seconds()
                if remaining > 30:
                    return self._cached.token

            app_jwt = self._build_app_jwt()
            headers = {
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            url = f"https://api.github.com/app/installations/{self._config.installation_id}/access_tokens"
            async with httpx.AsyncClient(
                follow_redirects=False,
                timeout=30.0,
                transport=self._transport,
            ) as client:
                resp = await client.post(url, headers=headers, json={})

            if resp.status_code in (401, 403):
                raise SafeError(code="Auth", message="GitHub App authentication failed")
            if resp.status_code >= 400:
                raise SafeError(code="GitHub", message="Failed to obtain installation token")

            data = resp.json()
            token = data.get("token")
            expires_at_raw = data.get("expires_at")
            if not token or not expires_at_raw:
                raise SafeError(code="Auth", message="GitHub token response missing required fields")

            # RFC3339 timestamp like 2025-01-01T00:00:00Z
            expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
            self._cached = InstallationToken(token=token, expires_at=expires_at)
            return token
