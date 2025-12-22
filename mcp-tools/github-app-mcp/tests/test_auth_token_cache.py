"""Auth token caching tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from github_app_mcp.auth import GitHubAppAuth
from github_app_mcp.config import AppConfig, LimitsConfig, PolicyConfig
from github_app_mcp.errors import SafeError


def _write_test_key(tmp_path: Path) -> Path:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path = tmp_path / "key.pem"
    path.write_bytes(pem)
    return path


def _cfg(tmp_path: Path) -> AppConfig:
    return AppConfig(
        app_id=1,
        installation_id=2,
        private_key_path=_write_test_key(tmp_path),
        policy=PolicyConfig(allowed_repos=frozenset(), pr_only=False, protected_branches=()),
        audit_log_path=None,
        audit_max_bytes=5 * 1024 * 1024,
        audit_max_backups=2,
        limits=LimitsConfig(),
    )


@pytest.mark.asyncio
async def test_installation_token_is_cached_when_not_near_expiry(tmp_path: Path) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        expires = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        return httpx.Response(201, json={"token": f"t{calls['n']}", "expires_at": expires})

    transport = httpx.MockTransport(handler)
    auth = GitHubAppAuth(config=_cfg(tmp_path), transport=transport)

    t1 = await auth.get_installation_token()
    t2 = await auth.get_installation_token()

    assert t1 == t2
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_installation_token_refreshes_when_near_expiry(tmp_path: Path) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        expires = (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat().replace("+00:00", "Z")
        return httpx.Response(201, json={"token": f"t{calls['n']}", "expires_at": expires})

    transport = httpx.MockTransport(handler)
    auth = GitHubAppAuth(config=_cfg(tmp_path), transport=transport)

    t1 = await auth.get_installation_token()
    t2 = await auth.get_installation_token()

    assert t1 != t2
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_installation_token_401_raises_safe_auth_error(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "bad creds"})

    auth = GitHubAppAuth(config=_cfg(tmp_path), transport=httpx.MockTransport(handler))

    with pytest.raises(SafeError) as exc:
        _ = await auth.get_installation_token()

    assert exc.value.code == "Auth"
    assert "authentication failed" in exc.value.message.lower()


@pytest.mark.asyncio
async def test_installation_token_500_raises_github_error(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "oops"})

    auth = GitHubAppAuth(config=_cfg(tmp_path), transport=httpx.MockTransport(handler))

    with pytest.raises(SafeError) as exc:
        _ = await auth.get_installation_token()

    assert exc.value.code == "GitHub"


@pytest.mark.asyncio
async def test_installation_token_missing_fields_raises_auth_error(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        expires = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        return httpx.Response(201, json={"expires_at": expires})

    auth = GitHubAppAuth(config=_cfg(tmp_path), transport=httpx.MockTransport(handler))

    with pytest.raises(SafeError) as exc:
        _ = await auth.get_installation_token()

    assert exc.value.code == "Auth"
