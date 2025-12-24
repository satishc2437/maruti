"""GitHub GraphQL client tests.

Covers:
- request construction (URL + auth)
- bounded retry on 429
- GraphQL error mapping
"""

from __future__ import annotations

import httpx
import pytest
from github_app_mcp.config import LimitsConfig
from github_app_mcp.errors import SafeError
from github_app_mcp.github_client import RequestBudget
from github_app_mcp.github_graphql_client import GitHubGraphQLClient


@pytest.mark.asyncio
async def test_github_graphql_client_sends_bearer_auth_header_and_correct_url() -> None:
    seen = {"url": None, "auth": None}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"data": {"ok": True}})

    transport = httpx.MockTransport(handler)

    async def token_provider() -> str:
        return "tok"

    client = GitHubGraphQLClient(token_provider=token_provider, limits=LimitsConfig(max_attempts=1), transport=transport)

    out = await client.execute(query="query { viewer { login } }", budget=RequestBudget(total_timeout_s=5.0))
    assert out.data == {"ok": True}
    assert seen["url"] == "https://api.github.com/graphql"
    assert seen["auth"] == "Bearer tok"


@pytest.mark.asyncio
async def test_github_graphql_client_retries_on_429_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, json={"message": "rate limited"})
        return httpx.Response(200, json={"data": {"ok": True}})

    transport = httpx.MockTransport(handler)

    async def token_provider() -> str:
        return "tok"

    client = GitHubGraphQLClient(
        token_provider=token_provider,
        limits=LimitsConfig(max_attempts=3, max_backoff_s=0.0),
        transport=transport,
    )

    out = await client.execute(query="query { rateLimit { remaining } }", budget=RequestBudget(total_timeout_s=5.0))
    assert out.data == {"ok": True}
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_github_graphql_client_maps_graphql_errors_to_safe_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": None,
                "errors": [{"message": "Something went wrong"}],
            },
        )

    transport = httpx.MockTransport(handler)

    async def token_provider() -> str:
        return "tok"

    client = GitHubGraphQLClient(token_provider=token_provider, limits=LimitsConfig(max_attempts=1), transport=transport)

    with pytest.raises(SafeError) as exc:
        _ = await client.execute(query="query { viewer { login } }", budget=RequestBudget(total_timeout_s=5.0))

    assert exc.value.code == "GitHub"
    assert "GraphQL" in exc.value.message
    assert exc.value.hint == "Something went wrong"


def test_github_graphql_client_rejects_non_default_api_base_url() -> None:
    async def token_provider() -> str:
        return "tok"

    with pytest.raises(SafeError) as exc:
        _ = GitHubGraphQLClient(token_provider=token_provider, limits=LimitsConfig(), api_base_url="https://example.com")

    assert exc.value.code == "Config"


@pytest.mark.asyncio
async def test_github_graphql_client_rejects_missing_query() -> None:
    async def token_provider() -> str:
        return "tok"

    client = GitHubGraphQLClient(token_provider=token_provider, limits=LimitsConfig(max_attempts=1))

    with pytest.raises(SafeError) as exc:
        _ = await client.execute(query=" ", budget=RequestBudget(total_timeout_s=5.0))

    assert exc.value.code == "Internal"


@pytest.mark.asyncio
async def test_github_graphql_client_invalid_json_response_raises_safe_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json", headers={"content-type": "application/json"})

    async def token_provider() -> str:
        return "tok"

    client = GitHubGraphQLClient(
        token_provider=token_provider,
        limits=LimitsConfig(max_attempts=1),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SafeError) as exc:
        _ = await client.execute(query="query { viewer { login } }", budget=RequestBudget(total_timeout_s=5.0))

    assert exc.value.code == "GitHub"


@pytest.mark.asyncio
async def test_github_graphql_client_non_dict_payload_raises_safe_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[1, 2, 3])

    async def token_provider() -> str:
        return "tok"

    client = GitHubGraphQLClient(token_provider=token_provider, limits=LimitsConfig(max_attempts=1), transport=httpx.MockTransport(handler))

    with pytest.raises(SafeError) as exc:
        _ = await client.execute(query="query { viewer { login } }", budget=RequestBudget(total_timeout_s=5.0))

    assert exc.value.code == "GitHub"


@pytest.mark.asyncio
async def test_github_graphql_client_401_maps_to_forbidden() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "bad creds"})

    async def token_provider() -> str:
        return "tok"

    client = GitHubGraphQLClient(token_provider=token_provider, limits=LimitsConfig(max_attempts=1), transport=httpx.MockTransport(handler))

    with pytest.raises(SafeError) as exc:
        _ = await client.execute(query="query { viewer { login } }", budget=RequestBudget(total_timeout_s=5.0))

    assert exc.value.code == "Forbidden"


@pytest.mark.asyncio
async def test_github_graphql_client_404_is_non_retryable_and_reports_status() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not found"})

    async def token_provider() -> str:
        return "tok"

    client = GitHubGraphQLClient(token_provider=token_provider, limits=LimitsConfig(max_attempts=2), transport=httpx.MockTransport(handler))

    with pytest.raises(SafeError) as exc:
        _ = await client.execute(query="query { viewer { login } }", budget=RequestBudget(total_timeout_s=5.0))

    assert exc.value.code == "GitHub"
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_github_graphql_client_retries_on_timeout_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ReadTimeout("timeout")
        return httpx.Response(200, json={"data": {"ok": True}})

    async def token_provider() -> str:
        return "tok"

    client = GitHubGraphQLClient(
        token_provider=token_provider,
        limits=LimitsConfig(max_attempts=2, max_backoff_s=0.0),
        transport=httpx.MockTransport(handler),
    )

    out = await client.execute(query="query { viewer { login } }", budget=RequestBudget(total_timeout_s=5.0))
    assert out.data == {"ok": True}
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_github_graphql_client_retries_on_500_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, json={"message": "server error"})
        return httpx.Response(200, json={"data": {"ok": True}})

    async def token_provider() -> str:
        return "tok"

    client = GitHubGraphQLClient(
        token_provider=token_provider,
        limits=LimitsConfig(max_attempts=2, max_backoff_s=0.0),
        transport=httpx.MockTransport(handler),
    )

    out = await client.execute(query="query { viewer { login } }", budget=RequestBudget(total_timeout_s=5.0))
    assert out.data == {"ok": True}
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_github_graphql_client_400_includes_message_hint() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "bad request"})

    async def token_provider() -> str:
        return "tok"

    client = GitHubGraphQLClient(token_provider=token_provider, limits=LimitsConfig(max_attempts=1), transport=httpx.MockTransport(handler))

    with pytest.raises(SafeError) as exc:
        _ = await client.execute(query="query { viewer { login } }", budget=RequestBudget(total_timeout_s=5.0))

    assert exc.value.code == "GitHub"
    assert exc.value.hint == "bad request"
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_github_graphql_client_400_with_non_json_body_has_no_hint() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, content=b"not-json", headers={"content-type": "application/json"})

    async def token_provider() -> str:
        return "tok"

    client = GitHubGraphQLClient(token_provider=token_provider, limits=LimitsConfig(max_attempts=1), transport=httpx.MockTransport(handler))

    with pytest.raises(SafeError) as exc:
        _ = await client.execute(query="query { viewer { login } }", budget=RequestBudget(total_timeout_s=5.0))

    assert exc.value.code == "GitHub"
    assert exc.value.hint is None
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_github_graphql_client_graphql_errors_without_message_hint_none() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": None, "errors": ["nope"]})

    async def token_provider() -> str:
        return "tok"

    client = GitHubGraphQLClient(token_provider=token_provider, limits=LimitsConfig(max_attempts=1), transport=httpx.MockTransport(handler))

    with pytest.raises(SafeError) as exc:
        _ = await client.execute(query="query { viewer { login } }", budget=RequestBudget(total_timeout_s=5.0))

    assert exc.value.code == "GitHub"
    assert exc.value.hint is None
