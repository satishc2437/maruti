"""Direct tests for internal tool functions.

Some validation branches in `github_app_mcp.tools` are not reachable via `dispatch_tool`
(because the minimal schema validator rejects them first). We call the internal
functions directly to keep coverage meaningful without weakening validation.
"""

from __future__ import annotations

import base64
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
        return {"ok": True}


def _runtime() -> tools.Runtime:
    cfg = AppConfig(
        app_id=1,
        installation_id=2,
        private_key_path=Path("/tmp/does-not-matter.pem"),
        policy=PolicyConfig(allowed_repos=frozenset({"octo/repo"}), pr_only=True, protected_branches=("main",)),
        audit_log_path=None,
        audit_max_bytes=5 * 1024 * 1024,
        audit_max_backups=2,
        limits=LimitsConfig(get_file_max_bytes=100),
    )

    return tools.Runtime(
        config=cfg,
        audit=DummyAudit(events=[]),  # type: ignore[arg-type]
        policy=Policy(
            allowed_repos=cfg.policy.allowed_repos,
            pr_only=cfg.policy.pr_only,
            protected_branch_patterns=cfg.policy.protected_branches,
        ),
        auth=None,  # type: ignore[arg-type]
        github=DummyGitHub(),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_tool_open_pull_request_validates_body_type() -> None:
    runtime = _runtime()

    with pytest.raises(SafeError):
        await tools._tool_open_pull_request(  # pylint: disable=protected-access
            runtime,
            {"owner": "octo", "repo": "repo", "title": "t", "head": "h", "base": "b", "body": 123},
        )


@pytest.mark.asyncio
async def test_tool_open_pull_request_validates_draft_type() -> None:
    runtime = _runtime()

    with pytest.raises(SafeError):
        await tools._tool_open_pull_request(  # pylint: disable=protected-access
            runtime,
            {"owner": "octo", "repo": "repo", "title": "t", "head": "h", "base": "b", "draft": "no"},
        )


@pytest.mark.asyncio
async def test_tool_get_file_validates_ref_type() -> None:
    runtime = _runtime()

    with pytest.raises(SafeError):
        await tools._tool_get_file(runtime, {"owner": "octo", "repo": "repo", "path": "a", "ref": 1})  # pylint: disable=protected-access


def test_target_repo_from_args_unknown() -> None:
    assert tools._target_repo_from_args({}) == "<unknown>"  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_decode_change_content_base64_path_is_exercised() -> None:
    runtime = _runtime()

    # Exercise the base64 decode path in the commit handler.
    content_b64 = base64.b64encode(b"hi").decode("utf-8")

    with pytest.raises(SafeError):
        await tools._tool_commit_changes(  # pylint: disable=protected-access
            runtime,
            {
                "owner": "octo",
                "repo": "repo",
                "branch": "feature/x",
                "message": "m",
                "changes": [{"path": "a", "action": "upsert", "content": content_b64, "encoding": "base64"}],
            },
        )


@pytest.mark.asyncio
async def test_tool_list_pull_requests_validates_state_type() -> None:
    runtime = _runtime()
    with pytest.raises(SafeError):
        await tools._tool_list_pull_requests(  # pylint: disable=protected-access
            runtime,
            {"owner": "octo", "repo": "repo", "state": 123},
        )


@pytest.mark.asyncio
async def test_tool_list_pull_requests_rejects_unexpected_response_type() -> None:
    class GitHubBad:
        async def request_json(self, **_kwargs: Any) -> object:
            return {"not": "a list"}

    runtime = _runtime()
    runtime = tools.Runtime(
        config=runtime.config,
        audit=runtime.audit,
        policy=runtime.policy,
        auth=runtime.auth,
        github=GitHubBad(),  # type: ignore[arg-type]
    )

    with pytest.raises(SafeError):
        await tools._tool_list_pull_requests(runtime, {"owner": "octo", "repo": "repo"})  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_tool_list_issues_validates_state_type() -> None:
    runtime = _runtime()
    with pytest.raises(SafeError):
        await tools._tool_list_issues(  # pylint: disable=protected-access
            runtime,
            {"owner": "octo", "repo": "repo", "state": 123},
        )


@pytest.mark.asyncio
async def test_tool_commit_changes_rejects_non_object_change() -> None:
    runtime = _runtime()
    with pytest.raises(SafeError):
        await tools._tool_commit_changes(  # pylint: disable=protected-access
            runtime,
            {"owner": "octo", "repo": "repo", "branch": "feature/x", "message": "m", "changes": ["nope"]},
        )


@pytest.mark.asyncio
async def test_tool_commit_changes_rejects_missing_path() -> None:
    runtime = _runtime()
    with pytest.raises(SafeError):
        await tools._tool_commit_changes(  # pylint: disable=protected-access
            runtime,
            {
                "owner": "octo",
                "repo": "repo",
                "branch": "feature/x",
                "message": "m",
                "changes": [{"action": "delete"}],
            },
        )


@pytest.mark.asyncio
async def test_tool_commit_changes_rejects_invalid_action() -> None:
    runtime = _runtime()
    with pytest.raises(SafeError):
        await tools._tool_commit_changes(  # pylint: disable=protected-access
            runtime,
            {
                "owner": "octo",
                "repo": "repo",
                "branch": "feature/x",
                "message": "m",
                "changes": [{"path": "a", "action": "nope"}],
            },
        )


@pytest.mark.asyncio
async def test_tool_commit_changes_rejects_missing_content_for_upsert() -> None:
    runtime = _runtime()
    with pytest.raises(SafeError):
        await tools._tool_commit_changes(  # pylint: disable=protected-access
            runtime,
            {
                "owner": "octo",
                "repo": "repo",
                "branch": "feature/x",
                "message": "m",
                "changes": [{"path": "a", "action": "upsert"}],
            },
        )


@pytest.mark.asyncio
async def test_tool_commit_changes_rejects_non_string_encoding() -> None:
    runtime = _runtime()
    with pytest.raises(SafeError):
        await tools._tool_commit_changes(  # pylint: disable=protected-access
            runtime,
            {
                "owner": "octo",
                "repo": "repo",
                "branch": "feature/x",
                "message": "m",
                "changes": [{"path": "a", "action": "upsert", "content": "hi", "encoding": 1}],
            },
        )


@pytest.mark.asyncio
async def test_tool_commit_changes_rejects_unexpected_blob_response() -> None:
    class GitHubRoutes:
        async def request_json(self, **kwargs: Any) -> object:
            method = str(kwargs.get("method") or "")
            path = str(kwargs.get("path") or "")
            if method == "GET" and path.endswith("/git/ref/heads/feature/x"):
                return {"object": {"sha": "c0"}}
            if method == "GET" and path.endswith("/git/commits/c0"):
                return {"tree": {"sha": "t0"}}
            if method == "POST" and path.endswith("/git/blobs"):
                return []
            raise AssertionError(f"Unexpected call: {method} {path}")

    runtime = _runtime()
    runtime = tools.Runtime(
        config=runtime.config,
        audit=runtime.audit,
        policy=runtime.policy,
        auth=runtime.auth,
        github=GitHubRoutes(),  # type: ignore[arg-type]
    )

    with pytest.raises(SafeError):
        await tools._tool_commit_changes(  # pylint: disable=protected-access
            runtime,
            {
                "owner": "octo",
                "repo": "repo",
                "branch": "feature/x",
                "message": "m",
                "changes": [{"path": "a", "action": "upsert", "content": "hi"}],
            },
        )
