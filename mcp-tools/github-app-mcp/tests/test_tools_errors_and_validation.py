"""Error-path and validation coverage for tools dispatch.

These tests ensure tool dispatch rejects secrets, unknown tools, disallowed repos,
invalid arguments, and certain GitHub error translations.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import github_app_mcp.tools as tools
import pytest
from github_app_mcp.audit import AuditEvent
from github_app_mcp.config import AppConfig, LimitsConfig, PolicyConfig
from github_app_mcp.errors import SafeError
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


class DummyGitHub:
    async def request_json(self, **_kwargs: Any) -> object:  # pragma: no cover
        raise AssertionError("GitHub should not be called")


def _runtime(*, allowed_repos: frozenset[str]) -> tools.Runtime:
    cfg = AppConfig(
        app_id=1,
        installation_id=2,
        private_key_path=Path("/tmp/does-not-matter.pem"),
        policy=PolicyConfig(
            allowed_repos=allowed_repos,
            allowed_projects=frozenset(),
            pr_only=True,
            protected_branches=("main",),
        ),
        audit_log_path=None,
        audit_max_bytes=5 * 1024 * 1024,
        audit_max_backups=2,
        limits=LimitsConfig(),
    )

    audit = DummyAudit(events=[])
    return tools.Runtime(
        config=cfg,
        audit=audit,  # type: ignore[arg-type]
        policy=Policy(
            allowed_repos=cfg.policy.allowed_repos,
            allowed_projects=cfg.policy.allowed_projects,
            pr_only=cfg.policy.pr_only,
            protected_branch_patterns=cfg.policy.protected_branches,
        ),
        auth=None,  # type: ignore[arg-type]
        github=DummyGitHub(),  # type: ignore[arg-type]
        graphql=None,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_dispatch_tool_rejects_credential_like_values(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(allowed_repos=frozenset({"octo/repo"}))
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "comment_on_issue",
        {"owner": "octo", "repo": "repo", "issue_number": 1, "body": "ghp_1234567890"},
    )

    assert out["ok"] is False
    assert out["code"] == "UserInput"
    assert "Credential-like" in out["message"]


@pytest.mark.asyncio
async def test_dispatch_tool_rejects_unknown_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(allowed_repos=frozenset({"octo/repo"}))
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("not_a_tool", {"owner": "octo", "repo": "repo"})

    assert out["ok"] is False
    assert out["code"] == "UserInput"
    assert "Unknown tool" in out["message"]


@pytest.mark.asyncio
async def test_dispatch_tool_denies_repo_not_allowlisted(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(allowed_repos=frozenset({"octo/repo"}))
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_repository", {"owner": "evil", "repo": "repo"})

    assert out["ok"] is False
    assert out["code"] == "Forbidden"


@pytest.mark.asyncio
async def test_dispatch_tool_validates_missing_required_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(allowed_repos=frozenset({"octo/repo"}))
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_repository", {"owner": "octo"})

    assert out["ok"] is False
    assert out["code"] == "UserInput"
    assert "Missing required field" in out["message"]


@pytest.mark.asyncio
async def test_create_branch_translates_reference_already_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = AppConfig(
        app_id=1,
        installation_id=2,
        private_key_path=Path("/tmp/does-not-matter.pem"),
        policy=PolicyConfig(
            allowed_repos=frozenset({"octo/repo"}),
            allowed_projects=frozenset(),
            pr_only=True,
            protected_branches=("main",),
        ),
        audit_log_path=None,
        audit_max_bytes=5 * 1024 * 1024,
        audit_max_backups=2,
        limits=LimitsConfig(),
    )

    audit = DummyAudit(events=[])

    class GitHubAlreadyExists:
        async def request_json(self, **kwargs: Any) -> object:
            if kwargs.get("method") == "GET":
                return {"object": {"sha": "base"}}
            raise SafeError(
                code="GitHub",
                message="GitHub request failed",
                hint="Reference already exists",
                status_code=422,
            )

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
        github=GitHubAlreadyExists(),  # type: ignore[arg-type]
        graphql=None,  # type: ignore[arg-type]
    )

    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "create_branch",
        {"owner": "octo", "repo": "repo", "base": "main", "branch": "feature/x"},
    )

    assert out["ok"] is False
    assert out["code"] == "UserInput"
    assert "already exists" in out["message"].lower()
