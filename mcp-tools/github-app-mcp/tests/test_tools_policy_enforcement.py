"""Tool-level policy enforcement tests (US2).

These tests focus on protected-branch and PR-only behavior at the tool layer.
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
from github_app_mcp.github_graphql_client import GraphQLResult
from github_app_mcp.policy import Policy


class DummyGitHub:
    async def request_json(self, **_kwargs: Any) -> object:  # pragma: no cover
        raise AssertionError("GitHub should not be called for denied operations")


class DummyGraphQL:
    def __init__(self, results: list[dict[str, Any]]) -> None:
        self._results = list(results)
        self.calls: list[dict[str, Any]] = []

    async def execute(self, query: str, variables: dict[str, Any] | None = None, budget: object | None = None) -> GraphQLResult:
        self.calls.append({"query": query, "variables": variables, "budget": budget})
        if not self._results:
            raise AssertionError("Unexpected GraphQL call")
        return GraphQLResult(data=self._results.pop(0))


@dataclass
class DummyAudit:
    events: list[AuditEvent]

    def write_event(self, event: AuditEvent) -> None:
        self.events.append(event)

    def measure_start(self) -> float:
        return time.monotonic()

    def measure_duration_ms(self, start: float) -> int:
        return int((time.monotonic() - start) * 1000)


@pytest.mark.asyncio
async def test_commit_changes_denied_on_protected_branch(monkeypatch: pytest.MonkeyPatch) -> None:
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
        github=DummyGitHub(),  # type: ignore[arg-type]
        graphql=None,  # type: ignore[arg-type]
    )

    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    res = await tools.dispatch_tool(
        "commit_changes",
        {
            "owner": "octo",
            "repo": "repo",
            "branch": "main",
            "message": "msg",
            "changes": [{"path": "a.txt", "action": "upsert", "content": "hi"}],
        },
    )

    assert res["ok"] is False
    assert res["code"] == "Forbidden"
    assert "protected" in res["message"].lower()
    assert "correlation_id" in res

    assert len(audit.events) == 1
    assert audit.events[0].outcome == "denied"


@pytest.mark.asyncio
async def test_create_branch_denied_on_protected_branch_name(monkeypatch: pytest.MonkeyPatch) -> None:
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
        github=DummyGitHub(),  # type: ignore[arg-type]
        graphql=None,  # type: ignore[arg-type]
    )

    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    res = await tools.dispatch_tool(
        "create_branch",
        {"owner": "octo", "repo": "repo", "base": "main", "branch": "main"},
    )

    assert res["ok"] is False
    assert res["code"] == "Forbidden"
    assert "protected" in res["message"].lower()
    assert "correlation_id" in res

    assert len(audit.events) == 1
    assert audit.events[0].outcome == "denied"


@pytest.mark.asyncio
async def test_project_tools_denied_when_project_allowlist_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
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
    graphql = DummyGraphQL(
        results=[
            {
                "node": {
                    "__typename": "ProjectV2",
                    "number": 3,
                    "owner": {"login": "octo-org"},
                    "fields": {"nodes": []},
                }
            }
        ]
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
        github=DummyGitHub(),  # type: ignore[arg-type]
        graphql=graphql,  # type: ignore[arg-type]
    )

    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    res = await tools.dispatch_tool("list_project_v2_fields", {"project_id": "PVT_123"})

    assert res["ok"] is False
    assert res["code"] == "Forbidden"
    assert "correlation_id" in res
    assert len(audit.events) == 1
    assert audit.events[0].outcome == "denied"
    assert len(graphql.calls) == 1
