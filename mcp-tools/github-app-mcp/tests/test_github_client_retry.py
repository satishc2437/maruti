"""Foundational tests: retry/backoff behavior."""

from __future__ import annotations

import httpx
import pytest
from github_app_mcp.config import LimitsConfig
from github_app_mcp.github_client import GitHubClient, RequestBudget


@pytest.mark.asyncio
async def test_github_client_retries_on_429_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, json={"message": "rate limited"})
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)

    async def token_provider() -> str:
        return "tok"  # not secret-like

    client = GitHubClient(
        token_provider=token_provider,
        limits=LimitsConfig(max_attempts=3, max_backoff_s=0.0),
        transport=transport,
    )

    out = await client.request_json(
        method="GET",
        path="/rate_limit",
        budget=RequestBudget(total_timeout_s=5.0),
    )

    assert out == {"ok": True}
    assert calls["n"] == 3
