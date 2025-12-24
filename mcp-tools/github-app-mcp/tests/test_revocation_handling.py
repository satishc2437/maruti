"""Revocation/uninstall simulation tests (US3).

Simulates GitHub 401/403 responses and verifies:
- tool returns a safe Forbidden error
- audit outcome is denied
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import github_app_mcp.tools as tools
import httpx
import pytest
from github_app_mcp.audit import AuditEvent
from github_app_mcp.config import AppConfig, LimitsConfig, PolicyConfig
from github_app_mcp.github_client import GitHubClient
from github_app_mcp.policy import Policy


@dataclass
class DummyAudit:
    events: list[AuditEvent]

    def write_event(self, event: AuditEvent) -> None:
        self.events.append(event)

    def measure_start(self) -> float:
        return time.monotonic()

    def measure_duration_ms(self, start: float) -> int:
        return int((time.monotonic() - start) * 1000)


async def _token_provider() -> str:
    return "token-will-not-be-logged"


def _make_runtime(*, transport: httpx.AsyncBaseTransport) -> tuple[tools.Runtime, DummyAudit]:
    cfg = AppConfig(
        app_id=1,
        installation_id=2,
        private_key_path=Path("/tmp/does-not-matter.pem"),
        policy=PolicyConfig(
            allowed_repos=frozenset({"octo/repo"}),
            allowed_projects=frozenset(),
            pr_only=False,
            protected_branches=(),
        ),
        audit_log_path=None,
        audit_max_bytes=5 * 1024 * 1024,
        audit_max_backups=2,
        limits=LimitsConfig(),
    )

    audit = DummyAudit(events=[])
    github = GitHubClient(token_provider=_token_provider, limits=cfg.limits, transport=transport)

    runtime = tools.Runtime(
        config=cfg,
        audit=audit,  # type: ignore[arg-type]
        policy=Policy(
            allowed_repos=cfg.policy.allowed_repos,
            allowed_projects=cfg.policy.allowed_projects,
            pr_only=cfg.policy.pr_only,
            protected_branch_patterns=cfg.policy.protected_branches,
        ),
        auth=None,  # type: ignore[arg-type]
        github=github,
        graphql=None,  # type: ignore[arg-type]
    )

    return runtime, audit


@pytest.mark.asyncio
async def test_github_401_maps_to_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Bad credentials"})

    runtime, audit = _make_runtime(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    res = await tools.dispatch_tool("get_repository", {"owner": "octo", "repo": "repo"})

    assert res["ok"] is False
    assert res["code"] == "Forbidden"
    assert "authorized" in res["message"].lower()
    assert "correlation_id" in res

    assert len(audit.events) == 1
    assert audit.events[0].outcome == "denied"


@pytest.mark.asyncio
async def test_github_403_maps_to_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "Resource not accessible"})

    runtime, audit = _make_runtime(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    res = await tools.dispatch_tool("get_repository", {"owner": "octo", "repo": "repo"})

    assert res["ok"] is False
    assert res["code"] == "Forbidden"
    assert "authorized" in res["message"].lower()
    assert "correlation_id" in res

    assert len(audit.events) == 1
    assert audit.events[0].outcome == "denied"
