"""Happy-path tool execution tests.

These tests exercise the bulk of `github_app_mcp.tools` tool implementations using
an in-memory GitHub client stub. They intentionally avoid any real network calls.
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
from github_app_mcp.github_graphql_client import GraphQLResult
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
    def __init__(self, routes: dict[tuple[str, str], object | Exception]) -> None:
        self._routes = routes
        self.calls: list[dict[str, Any]] = []

    async def request_json(self, **kwargs: Any) -> object:
        self.calls.append(dict(kwargs))
        method = str(kwargs.get("method"))
        path = str(kwargs.get("path"))
        key = (method, path)
        if key not in self._routes:
            raise AssertionError(f"Unexpected GitHub call: {key}")
        val = self._routes[key]
        if isinstance(val, Exception):
            raise val
        return val


class DummyGraphQL:
    def __init__(self, results: list[GraphQLResult]) -> None:
        self._results = list(results)
        self.calls: list[dict[str, Any]] = []

    async def execute(self, query: str, variables: dict[str, Any] | None = None, budget: object | None = None) -> GraphQLResult:
        self.calls.append({"query": query, "variables": variables, "budget": budget})
        if not self._results:
            raise AssertionError("Unexpected GraphQL call")
        return self._results.pop(0)


def _runtime(*, routes: dict[tuple[str, str], object | Exception], limits: LimitsConfig | None = None) -> tools.Runtime:
    cfg = AppConfig(
        app_id=1,
        installation_id=2,
        private_key_path=Path("/tmp/does-not-matter.pem"),
        policy=PolicyConfig(
            allowed_repos=frozenset({"octo/repo"}),
            allowed_projects=frozenset(),
            pr_only=True,
            protected_branches=("main", "release/*"),
        ),
        audit_log_path=None,
        audit_max_bytes=5 * 1024 * 1024,
        audit_max_backups=2,
        limits=limits or LimitsConfig(max_backoff_s=0.0),
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
        github=DummyGitHub(routes),  # type: ignore[arg-type]
        graphql=DummyGraphQL(results=[GraphQLResult(data={})]),  # type: ignore[arg-type]
    )


def _runtime_with_project(
    *,
    routes: dict[tuple[str, str], object | Exception],
    graphql_results: list[dict[str, Any]],
    allowed_projects: frozenset[str] = frozenset({"octo-org/3"}),
) -> tools.Runtime:
    cfg = AppConfig(
        app_id=1,
        installation_id=2,
        private_key_path=Path("/tmp/does-not-matter.pem"),
        policy=PolicyConfig(
            allowed_repos=frozenset({"octo/repo"}),
            allowed_projects=allowed_projects,
            pr_only=True,
            protected_branches=("main", "release/*"),
        ),
        audit_log_path=None,
        audit_max_bytes=5 * 1024 * 1024,
        audit_max_backups=2,
        limits=LimitsConfig(max_backoff_s=0.0),
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
        github=DummyGitHub(routes),  # type: ignore[arg-type]
        graphql=DummyGraphQL(results=[GraphQLResult(data=r) for r in graphql_results]),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_get_repository_success(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo"): {
                "full_name": "octo/repo",
                "default_branch": "main",
                "private": True,
                "html_url": "https://github.com/octo/repo",
            }
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_repository", {"owner": "octo", "repo": "repo"})

    assert out["ok"] is True
    assert out["repository"]["full_name"] == "octo/repo"
    assert out["repository"]["default_branch"] == "main"
    assert "correlation_id" in out


@pytest.mark.asyncio
async def test_list_branches_success(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo"): {"default_branch": "main"},
            ("GET", "/repos/octo/repo/branches"): [
                {"name": "main"},
                {"name": "feature/x"},
                {"name": 123},
            ],
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_branches", {"owner": "octo", "repo": "repo"})

    assert out["ok"] is True
    assert out["default_branch"] == "main"
    assert out["branches"] == ["main", "feature/x"]


@pytest.mark.asyncio
async def test_list_branches_defaults_default_branch_when_missing_or_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo"): {"default_branch": 123},
            ("GET", "/repos/octo/repo/branches"): [],
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_branches", {"owner": "octo", "repo": "repo"})

    assert out["ok"] is True
    assert out["default_branch"] == ""


@pytest.mark.asyncio
async def test_get_file_success(monkeypatch: pytest.MonkeyPatch) -> None:
    content = "hello\n"
    content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/contents/README.md"): {
                "type": "file",
                "encoding": "base64",
                "content": content_b64,
            }
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "get_file",
        {"owner": "octo", "repo": "repo", "path": "README.md", "ref": "main"},
    )

    assert out["ok"] is True
    assert out["file"]["path"] == "README.md"
    assert out["file"]["content"] == content
    assert out["file"]["ref"] == "main"


@pytest.mark.asyncio
async def test_get_file_success_without_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    content = "hello\n"
    content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/contents/README.md"): {
                "type": "file",
                "encoding": "base64",
                "content": content_b64,
            }
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "get_file",
        {"owner": "octo", "repo": "repo", "path": "README.md"},
    )

    assert out["ok"] is True
    assert out["file"]["content"] == content
    assert "ref" not in out["file"]

    @pytest.mark.asyncio
    async def test_get_file_success_with_ref(monkeypatch: pytest.MonkeyPatch) -> None:
        content_b64 = base64.b64encode(b"hi\n").decode("utf-8")

        runtime = _runtime(
            routes={
                ("GET", "/repos/octo/repo/contents/a.txt"): {"type": "file", "encoding": "base64", "content": content_b64}
            }
        )
        monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

        out = await tools.dispatch_tool("get_file", {"owner": "octo", "repo": "repo", "path": "a.txt", "ref": "main"})

        assert out["ok"] is True
        assert out["file"]["path"] == "a.txt"
        assert out["file"]["ref"] == "main"
        assert out["file"]["content"].strip() == "hi"

        calls = getattr(runtime.github, "calls")
        assert calls[-1]["params"] == {"ref": "main"}


@pytest.mark.asyncio
async def test_list_pull_requests_success(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/pulls"): [
                {"number": 1, "html_url": "https://github.com/octo/repo/pull/1"},
                {"number": "bad", "html_url": "https://example.invalid"},
            ]
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "list_pull_requests",
        {"owner": "octo", "repo": "repo", "state": "open"},
    )

    assert out["ok"] is True
    assert out["pull_requests"] == [{"number": 1, "url": "https://github.com/octo/repo/pull/1"}]


@pytest.mark.asyncio
async def test_list_pull_requests_defaults_state_and_skips_non_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/pulls"): [
                "not-a-dict",
                {"number": 2, "html_url": "https://github.com/octo/repo/pull/2"},
            ]
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_pull_requests", {"owner": "octo", "repo": "repo"})

    assert out["ok"] is True
    assert out["pull_requests"] == [{"number": 2, "url": "https://github.com/octo/repo/pull/2"}]


@pytest.mark.asyncio
async def test_list_issues_success_filters_pull_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/issues"): [
                {"number": 1, "html_url": "https://github.com/octo/repo/issues/1"},
                {"number": 2, "html_url": "https://github.com/octo/repo/pull/2", "pull_request": {}},
            ]
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "list_issues",
        {"owner": "octo", "repo": "repo", "state": "open"},
    )

    assert out["ok"] is True
    assert out["issues"] == [{"number": 1, "url": "https://github.com/octo/repo/issues/1"}]


@pytest.mark.asyncio
async def test_create_issue_success(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("POST", "/repos/octo/repo/issues"): {
                "number": 12,
                "html_url": "https://github.com/octo/repo/issues/12",
                "node_id": "I_kwDO123",
            }
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "create_issue",
        {
            "owner": "octo",
            "repo": "repo",
            "title": "t",
            "body": "b",
            "labels": ["bug"],
            "assignees": ["octocat"],
            "milestone": 1,
        },
    )

    assert out["ok"] is True
    assert out["issue"]["owner"] == "octo"
    assert out["issue"]["repo"] == "repo"
    assert out["issue"]["number"] == 12
    assert out["issue"]["issue_node_id"] == "I_kwDO123"


@pytest.mark.asyncio
async def test_add_issue_to_project_v2_success(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime_with_project(
        routes={},
        graphql_results=[
            {
                "node": {
                    "__typename": "ProjectV2",
                    "number": 3,
                    "url": "https://github.com/orgs/octo-org/projects/3",
                    "owner": {"login": "octo-org"},
                }
            },
            {
                "addProjectV2ItemById": {
                    "item": {"id": "PVTI_123"},
                }
            },
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "add_issue_to_project_v2",
        {"project_id": "PVT_123", "issue_node_id": "I_kwDO123"},
    )

    assert out["ok"] is True
    assert out["item"]["item_id"] == "PVTI_123"


@pytest.mark.asyncio
async def test_list_project_v2_fields_success(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime_with_project(
        routes={},
        graphql_results=[
            {
                "node": {
                    "__typename": "ProjectV2",
                    "number": 3,
                    "owner": {"login": "octo-org"},
                    "fields": {
                        "nodes": [
                            {
                                "__typename": "ProjectV2SingleSelectField",
                                "id": "F_STATUS",
                                "name": "Status",
                                "options": [
                                    {"id": "O_TODO", "name": "Todo"},
                                    {"id": "O_DONE", "name": "Done"},
                                ],
                            },
                            {"__typename": "ProjectV2TextField", "id": "F_TXT", "name": "Notes"},
                        ]
                    },
                }
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_project_v2_fields", {"project_id": "PVT_123"})

    assert out["ok"] is True
    assert any(f["field_id"] == "F_STATUS" for f in out["fields"])


@pytest.mark.asyncio
async def test_list_project_v2_items_success_with_status_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime_with_project(
        routes={},
        graphql_results=[
            {
                "node": {
                    "__typename": "ProjectV2",
                    "number": 3,
                    "owner": {"login": "octo-org"},
                    "items": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {
                                "id": "PVTI_1",
                                "content": {
                                    "__typename": "Issue",
                                    "id": "I_1",
                                    "number": 12,
                                    "url": "https://github.com/octo/repo/issues/12",
                                    "repository": {"name": "repo", "owner": {"login": "octo"}},
                                },
                                "fieldValues": {
                                    "nodes": [
                                        {
                                            "__typename": "ProjectV2ItemFieldSingleSelectValue",
                                            "name": "Todo",
                                            "optionId": "O_TODO",
                                        }
                                    ]
                                },
                            },
                            {
                                "id": "PVTI_2",
                                "content": {
                                    "__typename": "Issue",
                                    "id": "I_2",
                                    "number": 13,
                                    "url": "https://github.com/octo/repo/issues/13",
                                    "repository": {"name": "repo", "owner": {"login": "octo"}},
                                },
                                "fieldValues": {
                                    "nodes": [
                                        {
                                            "__typename": "ProjectV2ItemFieldSingleSelectValue",
                                            "name": "Done",
                                            "optionId": "O_DONE",
                                        }
                                    ]
                                },
                            },
                        ],
                    },
                }
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "list_project_v2_items",
        {"project_id": "PVT_123", "page_size": 20, "status_option_id": "O_TODO"},
    )

    assert out["ok"] is True
    assert out["page_info"]["has_next_page"] is False
    assert len(out["items"]) == 1
    assert out["items"][0]["item_id"] == "PVTI_1"
    assert out["items"][0]["issue"]["issue_node_id"] == "I_1"


@pytest.mark.asyncio
async def test_get_project_v2_item_success(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime_with_project(
        routes={},
        graphql_results=[
            {
                "project": {"__typename": "ProjectV2", "number": 3, "owner": {"login": "octo-org"}},
                "item": {
                    "__typename": "ProjectV2Item",
                    "id": "PVTI_1",
                    "content": {
                        "__typename": "Issue",
                        "id": "I_1",
                        "number": 12,
                        "url": "https://github.com/octo/repo/issues/12",
                        "repository": {"name": "repo", "owner": {"login": "octo"}},
                    },
                    "fieldValues": {
                        "nodes": [
                            {
                                "__typename": "ProjectV2ItemFieldSingleSelectValue",
                                "name": "Todo",
                                "optionId": "O_TODO",
                            }
                        ]
                    },
                },
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_project_v2_item", {"project_id": "PVT_123", "item_id": "PVTI_1"})

    assert out["ok"] is True
    assert out["item"]["item_id"] == "PVTI_1"
    assert out["item"]["status_option_id"] == "O_TODO"
    assert out["item"]["issue"]["issue_node_id"] == "I_1"


@pytest.mark.asyncio
async def test_set_project_v2_item_field_value_success(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime_with_project(
        routes={},
        graphql_results=[
            {"node": {"__typename": "ProjectV2", "number": 3, "owner": {"login": "octo-org"}}},
            {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "PVTI_1"}}},
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "set_project_v2_item_field_value",
        {"project_id": "PVT_123", "item_id": "PVTI_1", "field_id": "F_STATUS", "single_select_option_id": "O_DONE"},
    )

    assert out["ok"] is True
    assert out["item"]["item_id"] == "PVTI_1"


@pytest.mark.asyncio
async def test_get_issue_success(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/issues/12"): {
                "number": 12,
                "html_url": "https://github.com/octo/repo/issues/12",
                "node_id": "I_1",
                "title": "t",
                "body": "b",
                "state": "open",
            }
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_issue", {"owner": "octo", "repo": "repo", "number": 12})

    assert out["ok"] is True
    assert out["issue"]["issue_node_id"] == "I_1"
    assert out["issue"]["state"] == "open"


@pytest.mark.asyncio
async def test_update_issue_success(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("PATCH", "/repos/octo/repo/issues/12"): {
                "number": 12,
                "html_url": "https://github.com/octo/repo/issues/12",
                "node_id": "I_1",
                "title": "t2",
                "body": "b2",
                "state": "closed",
            }
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "update_issue",
        {
            "owner": "octo",
            "repo": "repo",
            "number": 12,
            "title": "t2",
            "body": "b2",
            "state": "closed",
        },
    )

    assert out["ok"] is True
    assert out["issue"]["title"] == "t2"
    assert out["issue"]["state"] == "closed"


@pytest.mark.asyncio
async def test_update_issue_includes_optional_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("PATCH", "/repos/octo/repo/issues/12"): {
                "number": 12,
                "html_url": "https://github.com/octo/repo/issues/12",
                "node_id": "I_1",
                "title": "t2",
                "body": "b2",
                "state": "open",
            }
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "update_issue",
        {
            "owner": "octo",
            "repo": "repo",
            "number": 12,
            "title": "t2",
            "body": "b2",
            "labels": ["bug"],
            "assignees": ["octocat"],
            "milestone": 1,
        },
    )

    assert out["ok"] is True
    calls = getattr(runtime.github, "calls")
    patch_call = calls[-1]
    assert patch_call["method"] == "PATCH"
    assert patch_call["json_body"]["labels"] == ["bug"]
    assert patch_call["json_body"]["assignees"] == ["octocat"]
    assert patch_call["json_body"]["milestone"] == 1


@pytest.mark.asyncio
async def test_list_issues_defaults_state_and_skips_non_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/issues"): [
                "not-a-dict",
                {"number": 3, "html_url": "https://github.com/octo/repo/issues/3"},
            ]
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_issues", {"owner": "octo", "repo": "repo"})

    assert out["ok"] is True
    assert out["issues"] == [{"number": 3, "url": "https://github.com/octo/repo/issues/3"}]


@pytest.mark.asyncio
async def test_create_branch_success_base_is_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/git/ref/heads/main"): {"object": {"sha": "base123"}},
            ("POST", "/repos/octo/repo/git/refs"): {"ok": True},
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "create_branch",
        {"owner": "octo", "repo": "repo", "base": "main", "branch": "feature/x"},
    )

    assert out["ok"] is True
    assert out["ref"] == "refs/heads/feature/x"


@pytest.mark.asyncio
async def test_create_branch_success_base_is_sha_when_ref_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/git/ref/heads/deadbeef"): SafeError(
                code="GitHub",
                message="GitHub request failed",
                hint="Not Found",
                status_code=404,
            ),
            ("POST", "/repos/octo/repo/git/refs"): {"ok": True},
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "create_branch",
        {"owner": "octo", "repo": "repo", "base": "deadbeef", "branch": "feature/y"},
    )

    assert out["ok"] is True
    assert out["ref"] == "refs/heads/feature/y"


@pytest.mark.asyncio
async def test_commit_changes_success_with_upsert_and_delete(monkeypatch: pytest.MonkeyPatch) -> None:
    content_b64 = base64.b64encode(b"hi\n").decode("utf-8")

    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/git/ref/heads/feature/x"): {"object": {"sha": "c0"}},
            ("GET", "/repos/octo/repo/git/commits/c0"): {"tree": {"sha": "t0"}},
            ("POST", "/repos/octo/repo/git/blobs"): {"sha": "b1"},
            ("POST", "/repos/octo/repo/git/trees"): {"sha": "t1"},
            ("POST", "/repos/octo/repo/git/commits"): {"sha": "c1"},
            ("PATCH", "/repos/octo/repo/git/refs/heads/feature/x"): {"ok": True},
        },
        limits=LimitsConfig(commit_max_total_bytes=1024, commit_max_files=10, commit_max_file_bytes=1024, max_backoff_s=0.0),
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "commit_changes",
        {
            "owner": "octo",
            "repo": "repo",
            "branch": "feature/x",
            "message": "msg",
            "changes": [
                {"path": "a.txt", "action": "upsert", "content": content_b64, "encoding": "base64"},
                {"path": "b.txt", "action": "delete"},
            ],
        },
    )

    assert out["ok"] is True
    assert out["commit"]["sha"] == "c1"
    assert out["commit"]["url"].endswith("/commit/c1")


@pytest.mark.asyncio
async def test_open_pull_request_success(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("POST", "/repos/octo/repo/pulls"): {"number": 7, "html_url": "https://github.com/octo/repo/pull/7"}
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "open_pull_request",
        {
            "owner": "octo",
            "repo": "repo",
            "title": "t",
            "head": "feature/x",
            "base": "main",
            "body": "b",
            "draft": False,
        },
    )

    assert out["ok"] is True
    assert out["pull_request"]["number"] == 7


@pytest.mark.asyncio
async def test_open_pull_request_defaults_draft_false(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("POST", "/repos/octo/repo/pulls"): {"number": 8, "html_url": "https://github.com/octo/repo/pull/8"}
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "open_pull_request",
        {
            "owner": "octo",
            "repo": "repo",
            "title": "t",
            "head": "feature/x",
            "base": "main",
        },
    )

    assert out["ok"] is True
    assert out["pull_request"]["number"] == 8


@pytest.mark.asyncio
async def test_comment_on_issue_success(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("POST", "/repos/octo/repo/issues/3/comments"): {"id": 99, "html_url": "https://github.com/octo/repo/issues/3#issuecomment-99"}
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "comment_on_issue",
        {"owner": "octo", "repo": "repo", "issue_number": 3, "body": "hi"},
    )

    assert out["ok"] is True
    assert out["comment"]["id"] == 99
