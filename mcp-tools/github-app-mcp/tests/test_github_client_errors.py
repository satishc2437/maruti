"""GitHub client error-path coverage.

These tests focus on JSON decode failures, non-retryable errors, and host allowlist enforcement.
"""

from __future__ import annotations

import httpx
import pytest
from github_app_mcp.config import LimitsConfig
from github_app_mcp.errors import SafeError
from github_app_mcp.github_client import GitHubClient, RequestBudget


@pytest.mark.asyncio
async def test_github_client_rejects_non_github_api_host() -> None:
    async def token_provider() -> str:
        return "tok"

    with pytest.raises(SafeError) as exc:
        _ = GitHubClient(token_provider=token_provider, limits=LimitsConfig(), api_base_url="https://example.com")

    assert exc.value.code == "Config"


@pytest.mark.asyncio
async def test_github_client_raises_on_invalid_json() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    transport = httpx.MockTransport(handler)

    async def token_provider() -> str:
        return "tok"

    client = GitHubClient(token_provider=token_provider, limits=LimitsConfig(max_attempts=1), transport=transport)

    with pytest.raises(SafeError) as exc:
        _ = await client.request_json(method="GET", path="/repos/octo/repo", budget=RequestBudget(total_timeout_s=1.0))

    assert exc.value.code == "GitHub"
    assert "invalid json" in exc.value.message.lower()


@pytest.mark.asyncio
async def test_github_client_non_retryable_404_provides_hint() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    transport = httpx.MockTransport(handler)

    async def token_provider() -> str:
        return "tok"

    client = GitHubClient(token_provider=token_provider, limits=LimitsConfig(max_attempts=3, max_backoff_s=0.0), transport=transport)

    with pytest.raises(SafeError) as exc:
        _ = await client.request_json(method="GET", path="/repos/octo/repo", budget=RequestBudget(total_timeout_s=1.0))

    assert exc.value.code == "GitHub"
    assert exc.value.status_code == 404
    assert exc.value.hint == "Not Found"


@pytest.mark.asyncio
async def test_github_client_maps_401_to_forbidden() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "bad"})

    transport = httpx.MockTransport(handler)

    async def token_provider() -> str:
        return "tok"

    client = GitHubClient(token_provider=token_provider, limits=LimitsConfig(max_attempts=1), transport=transport)

    with pytest.raises(SafeError) as exc:
        _ = await client.request_json(method="GET", path="/repos/octo/repo", budget=RequestBudget(total_timeout_s=1.0))

    assert exc.value.code == "Forbidden"
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_github_client_error_payload_non_json_still_safe() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"not-json")

    transport = httpx.MockTransport(handler)

    async def token_provider() -> str:
        return "tok"

    client = GitHubClient(
        token_provider=token_provider,
        limits=LimitsConfig(max_attempts=1),
        transport=transport,
    )

    with pytest.raises(SafeError) as exc:
        _ = await client.request_json(method="GET", path="/boom", budget=RequestBudget(total_timeout_s=1.0))

    assert exc.value.code == "GitHub"
    assert exc.value.hint is None


@pytest.mark.asyncio
async def test_github_client_error_payload_message_not_string() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": 123})

    transport = httpx.MockTransport(handler)

    async def token_provider() -> str:
        return "tok"

    client = GitHubClient(
        token_provider=token_provider,
        limits=LimitsConfig(max_attempts=1),
        transport=transport,
    )

    with pytest.raises(SafeError) as exc:
        _ = await client.request_json(method="GET", path="/boom", budget=RequestBudget(total_timeout_s=1.0))

    assert exc.value.code == "GitHub"
    assert exc.value.hint is None


@pytest.mark.asyncio
async def test_github_client_transport_error_raises_network() -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectError("nope")

    transport = httpx.MockTransport(handler)

    async def token_provider() -> str:
        return "tok"

    client = GitHubClient(
        token_provider=token_provider,
        limits=LimitsConfig(max_attempts=1),
        transport=transport,
    )

    with pytest.raises(SafeError) as exc:
        _ = await client.request_json(method="GET", path="/repos/octo/repo", budget=RequestBudget(total_timeout_s=1.0))

    assert exc.value.code == "Network"
    assert calls["n"] == 1


def test_github_client_helpers_are_deterministic() -> None:
    async def token_provider() -> str:
        return "tok"

    client = GitHubClient(token_provider=token_provider, limits=LimitsConfig(max_attempts=1, max_backoff_s=0.0))
    h = client._headers("t")  # pylint: disable=protected-access
    assert h["Authorization"] == "Bearer t"

    backoff = client._compute_backoff_s(1)  # pylint: disable=protected-access
    assert backoff >= 0.0

    assert client._is_retryable(429, None) is True  # pylint: disable=protected-access
    assert client._is_retryable(None, None) is False  # pylint: disable=protected-access
    assert client._is_retryable(None, httpx.ReadTimeout("t")) is True  # pylint: disable=protected-access
    assert client._is_non_retryable(404) is True  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_github_client_retries_on_500_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, json={"message": "oops"})
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)

    async def token_provider() -> str:
        return "tok"

    client = GitHubClient(
        token_provider=token_provider,
        limits=LimitsConfig(max_attempts=2, max_backoff_s=0.0),
        transport=transport,
    )

    out = await client.request_json(method="GET", path="/repos/octo/repo", budget=RequestBudget(total_timeout_s=1.0))
    assert out == {"ok": True}
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_github_client_raises_when_max_attempts_zero() -> None:
    async def token_provider() -> str:
        return "tok"

    client = GitHubClient(
        token_provider=token_provider,
        limits=LimitsConfig(max_attempts=0),
    )

    with pytest.raises(SafeError) as exc:
        _ = await client.request_json(method="GET", path="/repos/octo/repo", budget=RequestBudget(total_timeout_s=1.0))

    assert exc.value.code == "Network"
