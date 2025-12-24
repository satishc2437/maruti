"""GitHub REST client wrapper.

Provides:
- strict host allowlist and no-redirect behavior
- bounded retries with backoff
- finite timeouts
- safe error translation
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

import httpx

from .config import LimitsConfig
from .errors import SafeError, github_auth_forbidden


@dataclass(frozen=True, slots=True)
class RequestBudget:
    """Budget for a single tool call."""

    total_timeout_s: float


class GitHubClient:
    """Minimal GitHub REST client."""

    def __init__(
        self,
        *,
        token_provider,
        limits: LimitsConfig,
        api_base_url: str = "https://api.github.com",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Create a GitHub REST client.

        Args:
            token_provider: Async callable that returns an installation token.
            limits: Timeouts/retry limits.
            api_base_url: Must be https://api.github.com (enforced).
            transport: Optional httpx transport for tests.
        """
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
        # attempt_index: 1 for first retry, 2 for second retry...
        base = min(self._limits.max_backoff_s, 0.5 * (2 ** (attempt_index - 1)))
        # deterministic "jitter" component to avoid strict thundering herds without randomness
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

    async def request_json(
        self,
        *,
        method: str,
        path: str,
        json_body: dict | None = None,
        params: dict[str, str] | None = None,
        budget: RequestBudget,
    ) -> object:
        """Make a request and return decoded JSON.

        GitHub APIs may return either an object (dict) or an array (list).
        """
        url = f"{self._api_base_url}{path}"
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
                    resp = await client.request(
                        method,
                        url,
                        headers=self._headers(token),
                        json=json_body,
                        params=params,
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
                                message="GitHub request failed",
                                hint=safe_hint,
                                status_code=resp.status_code,
                            )

                        if attempt < self._limits.max_attempts and self._is_retryable(resp.status_code, None):
                            await asyncio.sleep(self._compute_backoff_s(attempt))
                            continue

                        raise SafeError(
                            code="GitHub",
                            message="GitHub request failed",
                            hint=safe_hint,
                            status_code=resp.status_code,
                        )

                    try:
                        data = resp.json()
                    except json.JSONDecodeError as exc:
                        raise SafeError(code="GitHub", message="GitHub returned invalid JSON") from exc

                    return data

                except SafeError:
                    raise
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    last_exc = exc
                    if attempt < self._limits.max_attempts and self._is_retryable(None, exc):
                        await asyncio.sleep(self._compute_backoff_s(attempt))
                        continue
                    raise SafeError(code="Network", message="Network request failed") from exc

        raise SafeError(code="Network", message=f"Request failed (status={last_status})") from last_exc
