"""GitHub client request construction tests."""

from __future__ import annotations

import httpx
import pytest
from github_app_mcp.config import LimitsConfig
from github_app_mcp.github_client import GitHubClient, RequestBudget


@pytest.mark.asyncio
async def test_github_client_sends_bearer_auth_header_and_correct_url() -> None:
    seen = {"url": None, "auth": None}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)

    async def token_provider() -> str:
        return "tok"

    client = GitHubClient(
        token_provider=token_provider,
        limits=LimitsConfig(max_attempts=1),
        transport=transport,
    )

    out = await client.request_json(
        method="GET",
        path="/repos/octo/repo",
        budget=RequestBudget(total_timeout_s=5.0),
    )

    assert out == {"ok": True}
    assert seen["url"] == "https://api.github.com/repos/octo/repo"
    assert seen["auth"] == "Bearer tok"
