"""GitHub GraphQL client wrapper.

Provides:
- strict host allowlist and no-redirect behavior
- bounded retries with backoff
- finite timeouts
- safe error translation

This client is intended only for fixed query/mutation documents controlled by the server.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

import httpx

from .config import LimitsConfig
from .errors import SafeError, github_auth_forbidden
from .github_client import RequestBudget


@dataclass(frozen=True, slots=True)
class GraphQLResult:
    """Parsed GraphQL response."""

    data: dict[str, Any]


class GitHubGraphQLClient:
    """Minimal GitHub GraphQL client (POST /graphql only)."""

    def __init__(
        self,
        *,
        token_provider,
        limits: LimitsConfig,
        api_base_url: str = "https://api.github.com",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Create a GraphQL client bound to api.github.com with safe defaults."""
        self._token_provider = token_provider
        self._limits = limits
        self._api_base_url = api_base_url.rstrip("/")
        self._transport = transport

        if self._api_base_url != "https://api.github.com":
            raise SafeError(code="Config", message="Only https://api.github.com is allowed")

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _compute_backoff_s(self, attempt_index: int) -> float:
        base = min(self._limits.max_backoff_s, 0.5 * (2 ** (attempt_index - 1)))
        jitter = min(0.05, 0.01 * attempt_index)
        return min(self._limits.max_backoff_s, base + jitter)

    def _is_retryable(self, status_code: int | None, exc: Exception | None) -> bool:
        if exc is not None:
            return isinstance(exc, (httpx.TimeoutException, httpx.TransportError))
        if status_code is None:
            return False
        if status_code == 429:
            return True
        return 500 <= status_code <= 599

    def _is_non_retryable(self, status_code: int) -> bool:
        return status_code in (401, 403, 404)

    async def execute(
        self,
        *,
        query: str,
        variables: dict[str, Any] | None = None,
        budget: RequestBudget,
    ) -> GraphQLResult:
        """Execute a fixed GraphQL query/mutation and return parsed data."""
        if not isinstance(query, str) or not query.strip():
            raise SafeError(code="Internal", message="GraphQL query is missing")

        url = f"{self._api_base_url}/graphql"
        token = await self._token_provider()

        timeout = httpx.Timeout(
            timeout=min(budget.total_timeout_s, self._limits.total_timeout_s),
            connect=self._limits.connect_timeout_s,
            read=self._limits.read_timeout_s,
        )

        last_exc: Exception | None = None
        last_status: int | None = None

        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=timeout,
            transport=self._transport,
        ) as client:
            for attempt in range(1, self._limits.max_attempts + 1):
                try:
                    resp = await client.post(
                        url,
                        headers=self._headers(token),
                        json={"query": query, "variables": variables or {}},
                    )
                    last_status = resp.status_code

                    if resp.status_code >= 400:
                        safe_hint = None
                        try:
                            err_payload = resp.json()
                            if isinstance(err_payload, dict) and isinstance(err_payload.get("message"), str):
                                safe_hint = err_payload.get("message")
                        except Exception:  # pylint: disable=broad-exception-caught
                            safe_hint = None

                        if resp.status_code in (401, 403):
                            raise github_auth_forbidden(status_code=resp.status_code)

                        if self._is_non_retryable(resp.status_code):
                            raise SafeError(
                                code="GitHub",
                                message="GitHub GraphQL request failed",
                                hint=safe_hint,
                                status_code=resp.status_code,
                            )

                        if attempt < self._limits.max_attempts and self._is_retryable(resp.status_code, None):
                            await asyncio.sleep(self._compute_backoff_s(attempt))
                            continue

                        raise SafeError(
                            code="GitHub",
                            message="GitHub GraphQL request failed",
                            hint=safe_hint,
                            status_code=resp.status_code,
                        )

                    try:
                        payload = resp.json()
                    except json.JSONDecodeError as exc:
                        raise SafeError(code="GitHub", message="GitHub returned invalid JSON") from exc

                    if not isinstance(payload, dict):
                        raise SafeError(code="GitHub", message="GitHub returned invalid JSON")

                    errors = payload.get("errors")
                    if isinstance(errors, list) and errors:
                        first = errors[0]
                        hint = None
                        if isinstance(first, dict) and isinstance(first.get("message"), str):
                            hint = first.get("message")
                        raise SafeError(code="GitHub", message="GitHub GraphQL request failed", hint=hint)

                    data = payload.get("data")
                    if not isinstance(data, dict):
                        raise SafeError(code="GitHub", message="GitHub GraphQL returned no data")

                    return GraphQLResult(data=data)

                except SafeError:
                    raise
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    last_exc = exc
                    if attempt < self._limits.max_attempts and self._is_retryable(None, exc):
                        await asyncio.sleep(self._compute_backoff_s(attempt))
                        continue
                    raise SafeError(code="Network", message="Network request failed") from exc

        raise SafeError(code="Network", message=f"Request failed (status={last_status})") from last_exc
