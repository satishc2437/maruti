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
from github_app_mcp.policy import Policy


class DummyGitHub:
    async def request_json(self, **_kwargs: Any) -> object:  # pragma: no cover
        raise AssertionError("GitHub should not be called for denied operations")


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
            pr_only=cfg.policy.pr_only,
            protected_branch_patterns=cfg.policy.protected_branches,
        ),
        auth=None,  # type: ignore[arg-type]
        github=DummyGitHub(),  # type: ignore[arg-type]
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
            pr_only=cfg.policy.pr_only,
            protected_branch_patterns=cfg.policy.protected_branches,
        ),
        auth=None,  # type: ignore[arg-type]
        github=DummyGitHub(),  # type: ignore[arg-type]
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
