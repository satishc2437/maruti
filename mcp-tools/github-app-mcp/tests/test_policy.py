"""Policy unit tests (US2).

Covers:
- repo allowlist
- operation allowlist
- protected branch patterns and PR-only fail-safe
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


def test_operation_allowlist() -> None:
    policy = Policy(allowed_repos=frozenset(), allowed_projects=frozenset(), pr_only=False, protected_branch_patterns=())

    assert policy.check_operation_allowed("get_repository").allowed is True
    assert policy.check_operation_allowed("totally_not_allowed").allowed is False


def test_pr_only_property_reflects_configuration() -> None:
    policy = Policy(allowed_repos=frozenset(), allowed_projects=frozenset(), pr_only=True, protected_branch_patterns=())
    assert policy.pr_only is True


def test_repo_allowlist_empty_allows_any_repo() -> None:
    policy = Policy(allowed_repos=frozenset(), allowed_projects=frozenset(), pr_only=False, protected_branch_patterns=())

    assert policy.check_repo_allowed("octo/repo").allowed is True
    assert policy.check_repo_allowed("other/repo").allowed is True


def test_repo_allowlist_denies_non_members() -> None:
    policy = Policy(
        allowed_repos=frozenset({"octo/repo"}),
        allowed_projects=frozenset(),
        pr_only=False,
        protected_branch_patterns=(),
    )

    assert policy.check_repo_allowed("octo/repo").allowed is True
    assert policy.check_repo_allowed("other/repo").allowed is False


def test_protected_branch_patterns_match() -> None:
    policy = Policy(
        allowed_repos=frozenset(),
        allowed_projects=frozenset(),
        pr_only=False,
        protected_branch_patterns=("main", "release/*"),
    )

    assert policy.is_branch_protected("main") is True
    assert policy.is_branch_protected("release/1.0") is True
    assert policy.is_branch_protected("feature/x") is False


def test_pr_only_fail_safe_treats_branch_as_protected_when_no_patterns() -> None:
    policy = Policy(allowed_repos=frozenset(), allowed_projects=frozenset(), pr_only=True, protected_branch_patterns=())

    assert policy.is_branch_protected("main") is True
    assert policy.is_branch_protected("any-branch") is True


def test_no_patterns_and_pr_only_disabled_means_not_protected() -> None:
    policy = Policy(allowed_repos=frozenset(), allowed_projects=frozenset(), pr_only=False, protected_branch_patterns=())

    assert policy.is_branch_protected("main") is False
    assert policy.is_branch_protected("any-branch") is False


def test_project_allowlist_empty_denies_all_projects() -> None:
    policy = Policy(allowed_repos=frozenset(), allowed_projects=frozenset(), pr_only=False, protected_branch_patterns=())
    assert policy.check_project_allowed(owner_login="octo-org", project_number=3).allowed is False


def test_project_allowlist_allows_configured_project() -> None:
    policy = Policy(
        allowed_repos=frozenset(),
        allowed_projects=frozenset({"octo-org/3"}),
        pr_only=False,
        protected_branch_patterns=(),
    )
    assert policy.check_project_allowed(owner_login="octo-org", project_number=3).allowed is True
    assert policy.check_project_allowed(owner_login="octo-org", project_number=4).allowed is False


def test_project_allowlist_owner_login_is_normalized() -> None:
    policy = Policy(
        allowed_repos=frozenset(),
        allowed_projects=frozenset({"octo-org/3"}),
        pr_only=False,
        protected_branch_patterns=(),
    )
    assert policy.check_project_allowed(owner_login=" Octo-Org ", project_number=3).allowed is True


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
        raise AssertionError("GitHub should not be called for denied operations")


def _runtime_for_repo_deny() -> tools.Runtime:
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
@pytest.mark.parametrize(
    "tool_name,args",
    [
        ("create_issue", {"owner": "evil", "repo": "repo", "title": "t", "body": "b"}),
        ("get_issue", {"owner": "evil", "repo": "repo", "number": 1}),
        ("update_issue", {"owner": "evil", "repo": "repo", "number": 1, "title": "t2"}),
    ],
)
async def test_repo_scoped_tools_denied_when_repo_not_allowlisted(
    monkeypatch: pytest.MonkeyPatch, tool_name: str, args: dict[str, Any]
) -> None:
    runtime = _runtime_for_repo_deny()
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(tool_name, args)

    assert out["ok"] is False
    assert out["code"] == "Forbidden"
    assert "correlation_id" in out
