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
        policy=PolicyConfig(
            allowed_repos=frozenset({"octo/repo"}),
            allowed_projects=frozenset(),
            pr_only=True,
            protected_branches=("main",),
        ),
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
            allowed_projects=cfg.policy.allowed_projects,
            pr_only=cfg.policy.pr_only,
            protected_branch_patterns=cfg.policy.protected_branches,
        ),
        auth=None,  # type: ignore[arg-type]
        github=DummyGitHub(),  # type: ignore[arg-type]
        graphql=None,  # type: ignore[arg-type]
    )


def test_validate_tool_arguments_unknown_tool() -> None:
    with pytest.raises(SafeError):
        tools.validate_tool_arguments("no_such_tool", {})


def test_validate_tool_arguments_missing_required_field() -> None:
    with pytest.raises(SafeError) as exc:
        tools.validate_tool_arguments("get_repository", {"owner": "octo"})
    assert "Missing required field" in exc.value.message


def test_validate_tool_arguments_rejects_unexpected_fields_when_additional_properties_false() -> None:
    with pytest.raises(SafeError):
        tools.validate_tool_arguments("get_repository", {"owner": "octo", "repo": "repo", "extra": "no"})


def test_validate_tool_arguments_validates_basic_types() -> None:
    with pytest.raises(SafeError):
        tools.validate_tool_arguments("get_issue", {"owner": "octo", "repo": "repo", "number": "12"})


def test_extract_first_single_select_value_handles_non_object() -> None:
    assert tools._extract_first_single_select_value(None) == (None, None)  # pylint: disable=protected-access
    assert tools._extract_first_single_select_value({"nodes": "nope"}) == (None, None)  # pylint: disable=protected-access


def test_extract_first_single_select_value_finds_first_valid_option() -> None:
    field_values = {
        "nodes": [
            "nope",
            {"__typename": "Other", "optionId": "O_X", "name": "X"},
            {"__typename": "ProjectV2ItemFieldSingleSelectValue", "optionId": "O_TODO", "name": "Todo"},
        ]
    }
    assert tools._extract_first_single_select_value(field_values) == ("O_TODO", "Todo")  # pylint: disable=protected-access


def test_find_single_select_value_by_option_id_matches_exact_option() -> None:
    field_values = {
        "nodes": [
            {"__typename": "ProjectV2ItemFieldSingleSelectValue", "optionId": "O_DONE", "name": "Done"},
            {"__typename": "ProjectV2ItemFieldSingleSelectValue", "optionId": "O_TODO", "name": "Todo"},
        ]
    }
    assert tools._find_single_select_value_by_option_id(field_values, "O_TODO") == ("O_TODO", "Todo")  # pylint: disable=protected-access
    assert tools._find_single_select_value_by_option_id(field_values, "O_MISSING") == (None, None)  # pylint: disable=protected-access


def test_parse_issue_content_covers_non_issue_types_and_missing_fields() -> None:
    assert tools._parse_issue_content(None) == ("unknown", None)  # pylint: disable=protected-access

    content_type, issue_obj = tools._parse_issue_content({"__typename": "PullRequest"})  # pylint: disable=protected-access
    assert content_type == "pullrequest"
    assert issue_obj is None

    content_type, issue_obj = tools._parse_issue_content({"__typename": "Issue", "id": "I"})  # pylint: disable=protected-access
    assert content_type == "issue"
    assert issue_obj is None


def test_parse_issue_content_happy_path_returns_issue_object() -> None:
    content_type, issue_obj = tools._parse_issue_content(  # pylint: disable=protected-access
        {
            "__typename": "Issue",
            "id": "I_1",
            "number": 12,
            "url": "https://example.invalid",
            "repository": {"name": "repo", "owner": {"login": "octo"}},
        }
    )
    assert content_type == "issue"
    assert issue_obj is not None
    assert issue_obj["issue_node_id"] == "I_1"


def test_project_allowlist_check_or_forbid_allows_and_forbids() -> None:
    runtime = _runtime()
    with pytest.raises(SafeError):
        tools._project_allowlist_check_or_forbid(runtime, owner_login="octo-org", project_number=3)  # pylint: disable=protected-access

    cfg = runtime.config
    cfg2 = AppConfig(
        app_id=cfg.app_id,
        installation_id=cfg.installation_id,
        private_key_path=cfg.private_key_path,
        policy=PolicyConfig(
            allowed_repos=cfg.policy.allowed_repos,
            allowed_projects=frozenset({"octo-org/3"}),
            pr_only=cfg.policy.pr_only,
            protected_branches=cfg.policy.protected_branches,
        ),
        audit_log_path=cfg.audit_log_path,
        audit_max_bytes=cfg.audit_max_bytes,
        audit_max_backups=cfg.audit_max_backups,
        limits=cfg.limits,
    )
    runtime2 = tools.Runtime(
        config=cfg2,
        audit=runtime.audit,
        policy=Policy(
            allowed_repos=cfg2.policy.allowed_repos,
            allowed_projects=cfg2.policy.allowed_projects,
            pr_only=cfg2.policy.pr_only,
            protected_branch_patterns=cfg2.policy.protected_branches,
        ),
        auth=runtime.auth,
        github=runtime.github,
        graphql=runtime.graphql,
    )

    tools._project_allowlist_check_or_forbid(runtime2, owner_login="octo-org", project_number=3)  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_tool_list_project_v2_items_validates_page_size_type() -> None:
    runtime = _runtime()
    with pytest.raises(SafeError):
        await tools._tool_list_project_v2_items(  # pylint: disable=protected-access
            runtime,
            {"project_id": "PVT_1", "page_size": "20"},
        )


@pytest.mark.asyncio
async def test_tool_list_project_v2_items_validates_after_cursor_type() -> None:
    runtime = _runtime()
    with pytest.raises(SafeError):
        await tools._tool_list_project_v2_items(  # pylint: disable=protected-access
            runtime,
            {"project_id": "PVT_1", "page_size": 1, "after_cursor": 1},
        )


@pytest.mark.asyncio
async def test_tool_list_project_v2_items_validates_status_option_id_type() -> None:
    runtime = _runtime()
    with pytest.raises(SafeError):
        await tools._tool_list_project_v2_items(  # pylint: disable=protected-access
            runtime,
            {"project_id": "PVT_1", "page_size": 1, "status_option_id": 1},
        )


@pytest.mark.asyncio
async def test_tool_get_issue_rejects_number_lt_1() -> None:
    runtime = _runtime()
    with pytest.raises(SafeError):
        await tools._tool_get_issue(runtime, {"owner": "octo", "repo": "repo", "number": 0})  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_tool_get_issue_rejects_unexpected_response_type() -> None:
    class GitHubBad:
        async def request_json(self, **_kwargs: Any) -> object:
            return []

    runtime = _runtime()
    runtime = tools.Runtime(
        config=runtime.config,
        audit=runtime.audit,
        policy=runtime.policy,
        auth=runtime.auth,
        github=GitHubBad(),  # type: ignore[arg-type]
        graphql=runtime.graphql,
    )

    with pytest.raises(SafeError):
        await tools._tool_get_issue(runtime, {"owner": "octo", "repo": "repo", "number": 1})  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_tool_get_issue_coerces_non_string_body_to_none() -> None:
    class GitHubBody:
        async def request_json(self, **_kwargs: Any) -> object:
            return {
                "number": 1,
                "node_id": "I_1",
                "html_url": "https://example.invalid",
                "title": "t",
                "body": 123,
                "state": "open",
            }

    runtime = _runtime()
    runtime = tools.Runtime(
        config=runtime.config,
        audit=runtime.audit,
        policy=runtime.policy,
        auth=runtime.auth,
        github=GitHubBody(),  # type: ignore[arg-type]
        graphql=runtime.graphql,
    )

    out = await tools._tool_get_issue(runtime, {"owner": "octo", "repo": "repo", "number": 1})  # pylint: disable=protected-access
    assert out["issue"]["body"] is None


@pytest.mark.asyncio
async def test_tool_update_issue_validates_number_and_field_types() -> None:
    runtime = _runtime()
    with pytest.raises(SafeError):
        await tools._tool_update_issue(runtime, {"owner": "octo", "repo": "repo", "number": 0})  # pylint: disable=protected-access

    with pytest.raises(SafeError):
        await tools._tool_update_issue(runtime, {"owner": "octo", "repo": "repo", "number": 1, "title": 1})  # pylint: disable=protected-access

    with pytest.raises(SafeError):
        await tools._tool_update_issue(runtime, {"owner": "octo", "repo": "repo", "number": 1, "body": 1})  # pylint: disable=protected-access

    with pytest.raises(SafeError):
        await tools._tool_update_issue(runtime, {"owner": "octo", "repo": "repo", "number": 1, "state": 1})  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_tool_update_issue_rejects_bad_github_response_shapes() -> None:
    class GitHubBadUpdate:
        def __init__(self, resp: object):
            self._resp = resp

        async def request_json(self, **_kwargs: Any) -> object:
            return self._resp

    runtime = _runtime()

    runtime1 = tools.Runtime(
        config=runtime.config,
        audit=runtime.audit,
        policy=runtime.policy,
        auth=runtime.auth,
        github=GitHubBadUpdate([]),  # type: ignore[arg-type]
        graphql=runtime.graphql,
    )
    with pytest.raises(SafeError):
        await tools._tool_update_issue(runtime1, {"owner": "octo", "repo": "repo", "number": 1, "title": "t"})  # pylint: disable=protected-access

    runtime2 = tools.Runtime(
        config=runtime.config,
        audit=runtime.audit,
        policy=runtime.policy,
        auth=runtime.auth,
        github=GitHubBadUpdate({"node_id": None}),  # type: ignore[arg-type]
        graphql=runtime.graphql,
    )
    with pytest.raises(SafeError):
        await tools._tool_update_issue(runtime2, {"owner": "octo", "repo": "repo", "number": 1, "title": "t"})  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_tool_update_issue_coerces_non_string_body_to_none() -> None:
    class GitHubBody:
        async def request_json(self, **_kwargs: Any) -> object:
            return {
                "node_id": "I_1",
                "html_url": "https://example.invalid",
                "title": "t",
                "body": 123,
                "state": "open",
            }

    runtime = _runtime()
    runtime = tools.Runtime(
        config=runtime.config,
        audit=runtime.audit,
        policy=runtime.policy,
        auth=runtime.auth,
        github=GitHubBody(),  # type: ignore[arg-type]
        graphql=runtime.graphql,
    )

    out = await tools._tool_update_issue(runtime, {"owner": "octo", "repo": "repo", "number": 1, "title": "t"})  # pylint: disable=protected-access
    assert out["issue"]["body"] is None


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
        graphql=runtime.graphql,
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
        graphql=runtime.graphql,
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
