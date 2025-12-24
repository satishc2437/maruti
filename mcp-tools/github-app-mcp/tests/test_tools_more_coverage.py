"""Additional tool coverage tests.

Focuses on type validation branches and common SafeError paths.
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
from github_app_mcp.policy import Policy, PolicyDecision


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

    async def request_json(self, **kwargs: Any) -> object:
        key = (str(kwargs.get("method")), str(kwargs.get("path")))
        if key not in self._routes:
            raise AssertionError(f"Unexpected call: {key}")
        val = self._routes[key]
        if isinstance(val, Exception):
            raise val
        return val


class DummyGraphQL:
    def __init__(self, results: list[GraphQLResult]) -> None:
        self._results = list(results)
        self.calls: list[dict[str, Any]] = []

    async def execute(self, *, query: str, variables: dict[str, Any] | None = None, budget: object | None = None) -> GraphQLResult:
        self.calls.append({"query": query, "variables": variables, "budget": budget})
        if not self._results:
            raise AssertionError("Unexpected GraphQL call")
        return self._results.pop(0)


def _runtime(
    *,
    routes: dict[tuple[str, str], object | Exception],
    graphql_results: list[dict[str, Any]] | None = None,
    allowed_projects: frozenset[str] = frozenset(),
    allowed_repos: frozenset[str] = frozenset({"octo/repo"}),
    limits: LimitsConfig | None = None,
) -> tools.Runtime:
    cfg = AppConfig(
        app_id=1,
        installation_id=2,
        private_key_path=Path("/tmp/does-not-matter.pem"),
        policy=PolicyConfig(
            allowed_repos=allowed_repos,
            allowed_projects=allowed_projects,
            pr_only=True,
            protected_branches=("main",),
        ),
        audit_log_path=None,
        audit_max_bytes=5 * 1024 * 1024,
        audit_max_backups=2,
        limits=limits or LimitsConfig(commit_max_files=2, commit_max_file_bytes=10, commit_max_total_bytes=15),
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
        graphql=DummyGraphQL(results=[GraphQLResult(data=r) for r in (graphql_results or [])]),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_get_file_rejects_non_file_type(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={("GET", "/repos/octo/repo/contents/a"): {"type": "dir"}})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_file", {"owner": "octo", "repo": "repo", "path": "a"})

    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_create_issue_rejects_title_too_large(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        limits=LimitsConfig(issue_title_max_bytes=1, issue_body_max_bytes=100),
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "create_issue",
        {"owner": "octo", "repo": "repo", "title": "hi", "body": "b"},
    )

    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_get_project_v2_by_number_success(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {
                "repositoryOwner": {
                    "__typename": "Organization",
                    "login": "octo-org",
                    "projectV2": {"id": "PVT_123", "number": 3, "title": "Queue", "url": "https://example.invalid"},
                }
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_project_v2_by_number", {"owner_login": "octo-org", "project_number": 3})

    assert out["ok"] is True
    assert out["project"]["project_id"] == "PVT_123"
    assert out["project"]["owner_login"] == "octo-org"
    assert out["project"]["project_number"] == 3


@pytest.mark.asyncio
async def test_get_project_v2_by_number_denies_when_allowlist_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={}, allowed_projects=frozenset(), graphql_results=[])
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_project_v2_by_number", {"owner_login": "octo-org", "project_number": 3})

    assert out["ok"] is False
    assert out["code"] == "Forbidden"


@pytest.mark.asyncio
async def test_get_project_v2_by_number_rejects_project_number_lt_1(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={}, allowed_projects=frozenset({"octo-org/3"}), graphql_results=[])
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_project_v2_by_number", {"owner_login": "octo-org", "project_number": 0})

    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_get_project_v2_by_number_reports_unexpected_owner_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[{"repositoryOwner": "not-a-dict"}],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_project_v2_by_number", {"owner_login": "octo-org", "project_number": 3})

    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_get_project_v2_by_number_reports_project_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[{"repositoryOwner": {"__typename": "Organization", "login": "octo-org", "projectV2": None}}],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_project_v2_by_number", {"owner_login": "octo-org", "project_number": 3})

    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_get_project_v2_by_number_reports_unexpected_project_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {
                "repositoryOwner": {
                    "__typename": "Organization",
                    "login": "octo-org",
                    "projectV2": {"id": None, "number": "3", "title": "Queue", "url": 123},
                }
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_project_v2_by_number", {"owner_login": "octo-org", "project_number": 3})

    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_create_issue_reports_unexpected_issue_response(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={("POST", "/repos/octo/repo/issues"): "not-a-dict"})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("create_issue", {"owner": "octo", "repo": "repo", "title": "t", "body": "b"})

    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_create_issue_reports_unexpected_issue_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("POST", "/repos/octo/repo/issues"): {
                "number": 1,
                "html_url": "https://example.invalid",
                "node_id": None,
            }
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("create_issue", {"owner": "octo", "repo": "repo", "title": "t", "body": "b"})

    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_add_issue_to_project_v2_reports_unexpected_payload_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {"node": {"__typename": "ProjectV2", "number": 3, "url": "u", "owner": {"login": "octo-org"}}},
            {"addProjectV2ItemById": "not-a-dict"},
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("add_issue_to_project_v2", {"project_id": "PVT_123", "issue_node_id": "I_1"})

    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_list_project_v2_fields_project_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[{"node": {"__typename": "User"}}],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_project_v2_fields", {"project_id": "PVT_123"})

    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_list_project_v2_fields_skips_invalid_nodes_and_handles_unknown_types(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {
                "node": {
                    "__typename": "ProjectV2",
                    "number": 3,
                    "owner": {"login": "octo-org"},
                    "fields": {
                        "nodes": [
                            "not-a-dict",
                            {"__typename": "ProjectV2TextField", "id": "F_TXT"},
                            {
                                "__typename": "ProjectV2SingleSelectField",
                                "id": "F_STATUS",
                                "name": "Status",
                                "options": "not-a-list",
                            },
                            {"__typename": "ProjectV2NumberField", "id": "F_NUM", "name": "Num"},
                        ]
                    },
                }
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_project_v2_fields", {"project_id": "PVT_123"})

    assert out["ok"] is True
    # Invalid nodes are skipped; unknown types are labeled as unknown.
    assert any(f["field_id"] == "F_STATUS" and f["options"] == [] for f in out["fields"])
    assert any(f["field_id"] == "F_NUM" and f["data_type"] == "unknown" for f in out["fields"])


@pytest.mark.asyncio
async def test_list_project_v2_fields_filters_invalid_options_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
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
                                    "nope",
                                    {"id": "O_TODO"},
                                    {"name": "Todo"},
                                    {"id": "O_TODO", "name": "Todo"},
                                ],
                            }
                        ]
                    },
                }
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_project_v2_fields", {"project_id": "PVT_123"})

    assert out["ok"] is True
    status = next(f for f in out["fields"] if f["field_id"] == "F_STATUS")
    assert status["options"] == [{"option_id": "O_TODO", "name": "Todo"}]


@pytest.mark.asyncio
async def test_list_project_v2_items_rejects_page_size_out_of_range(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={}, allowed_projects=frozenset({"octo-org/3"}), graphql_results=[])
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_project_v2_items", {"project_id": "PVT_123", "page_size": 51})

    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_list_project_v2_items_success_without_filter_extracts_status(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
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
                                    "url": "https://example.invalid",
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
                            }
                        ],
                    },
                }
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_project_v2_items", {"project_id": "PVT_123"})

    assert out["ok"] is True
    assert out["items"][0]["status_option_id"] == "O_TODO"
    assert out["items"][0]["status_name"] == "Todo"


@pytest.mark.asyncio
async def test_list_project_v2_items_coerces_bad_end_cursor_and_handles_non_issue_content(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {
                "node": {
                    "__typename": "ProjectV2",
                    "number": 3,
                    "owner": {"login": "octo-org"},
                    "items": {
                        "pageInfo": {"hasNextPage": True, "endCursor": 123},
                        "nodes": [
                            {"id": "PVTI_1", "content": {"__typename": "PullRequest"}, "fieldValues": {"nodes": []}},
                            {"id": "PVTI_2", "content": "not-a-dict", "fieldValues": {"nodes": []}},
                        ],
                    },
                }
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_project_v2_items", {"project_id": "PVT_123", "page_size": 1})

    assert out["ok"] is True
    assert out["page_info"]["has_next_page"] is True
    assert out["page_info"]["end_cursor"] is None
    assert out["items"][0]["content_type"] == "pullrequest"
    assert out["items"][0]["issue"] is None
    assert out["items"][1]["content_type"] == "unknown"
    assert out["items"][1]["issue"] is None


@pytest.mark.asyncio
async def test_list_project_v2_items_passes_after_cursor_and_handles_empty_status_option_id(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {
                "node": {
                    "__typename": "ProjectV2",
                    "number": 3,
                    "owner": {"login": "octo-org"},
                    "items": {
                        "pageInfo": {"hasNextPage": False, "endCursor": "CUR2"},
                        "nodes": [
                            {
                                "id": "PVTI_1",
                                "content": {
                                    "__typename": "Issue",
                                    "id": "I_1",
                                    "number": 12,
                                    "url": "https://example.invalid",
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
                            }
                        ],
                    },
                }
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "list_project_v2_items",
        {"project_id": "PVT_123", "after_cursor": "CUR1", "status_option_id": ""},
    )

    assert out["ok"] is True
    # Ensures we passed the cursor through.
    calls = getattr(runtime.graphql, "calls")
    assert calls[0]["variables"]["after"] == "CUR1"
    # Empty string should behave like no filter.
    assert out["items"][0]["status_option_id"] == "O_TODO"


@pytest.mark.asyncio
async def test_set_project_v2_item_field_value_denies_disallowed_project(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[{"node": {"__typename": "ProjectV2", "number": 4, "owner": {"login": "octo-org"}}}],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "set_project_v2_item_field_value",
        {"project_id": "PVT_999", "item_id": "PVTI_1", "field_id": "F_1", "single_select_option_id": "O_1"},
    )

    assert out["ok"] is False
    assert out["code"] == "Forbidden"


@pytest.mark.asyncio
async def test_get_project_v2_item_reports_item_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {
                "project": {"__typename": "ProjectV2", "number": 3, "owner": {"login": "octo-org"}},
                "item": {"__typename": "NotAProjectV2Item"},
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_project_v2_item", {"project_id": "PVT_123", "item_id": "PVTI_1"})

    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_get_project_v2_item_success(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
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
                        "url": "https://example.invalid",
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
    assert out["item"]["content_type"] == "issue"
    assert out["item"]["issue"]["issue_node_id"] == "I_1"


@pytest.mark.asyncio
async def test_set_project_v2_item_field_value_reports_unexpected_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {"node": {"__typename": "ProjectV2", "number": 3, "owner": {"login": "octo-org"}}},
            {"updateProjectV2ItemFieldValue": {}},
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "set_project_v2_item_field_value",
        {"project_id": "PVT_123", "item_id": "PVTI_1", "field_id": "F_1", "single_select_option_id": "O_1"},
    )

    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_get_issue_rejects_pull_request(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/issues/1"): {
                "number": 1,
                "node_id": "I_1",
                "html_url": "https://example.invalid",
                "title": "t",
                "body": "b",
                "state": "open",
                "pull_request": {},
            }
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_issue", {"owner": "octo", "repo": "repo", "number": 1})

    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_update_issue_rejects_invalid_state(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={("PATCH", "/repos/octo/repo/issues/1"): {}})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "update_issue",
        {"owner": "octo", "repo": "repo", "number": 1, "state": "merged"},
    )

    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_add_issue_to_project_v2_denies_disallowed_project(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {"node": {"__typename": "ProjectV2", "number": 4, "url": "u", "owner": {"login": "octo-org"}}}
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("add_issue_to_project_v2", {"project_id": "PVT_999", "issue_node_id": "I_1"})

    assert out["ok"] is False
    assert out["code"] == "Forbidden"


@pytest.mark.asyncio
async def test_add_issue_to_project_v2_project_not_found_for_wrong_node_type(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[{"node": {"__typename": "User"}}],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("add_issue_to_project_v2", {"project_id": "PVT_123", "issue_node_id": "I_1"})

    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_add_issue_to_project_v2_reports_unexpected_mutation_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {"node": {"__typename": "ProjectV2", "number": 3, "url": "u", "owner": {"login": "octo-org"}}},
            {"addProjectV2ItemById": {"item": {"id": None}}},
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("add_issue_to_project_v2", {"project_id": "PVT_123", "issue_node_id": "I_1"})

    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_get_file_rejects_binary_content(monkeypatch: pytest.MonkeyPatch) -> None:
    content_b64 = base64.b64encode(b"\xff\x00").decode("utf-8")
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/contents/bin.dat"): {
                "type": "file",
                "encoding": "base64",
                "content": content_b64,
            }
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_file", {"owner": "octo", "repo": "repo", "path": "bin.dat"})

    assert out["ok"] is False
    assert out["code"] == "UserInput"
    assert "binary" in out["message"].lower()


@pytest.mark.asyncio
async def test_commit_changes_rejects_too_many_files(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "commit_changes",
        {
            "owner": "octo",
            "repo": "repo",
            "branch": "feature/x",
            "message": "m",
            "changes": [
                {"path": "a", "action": "delete"},
                {"path": "b", "action": "delete"},
                {"path": "c", "action": "delete"},
            ],
        },
    )

    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_commit_changes_rejects_unsupported_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "commit_changes",
        {
            "owner": "octo",
            "repo": "repo",
            "branch": "feature/x",
            "message": "m",
            "changes": [{"path": "a", "action": "upsert", "content": "x", "encoding": "utf-16"}],
        },
    )

    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_dispatch_tool_reports_operation_not_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={})

    class DenyOpsPolicy(Policy):
        def check_operation_allowed(self, operation: str) -> PolicyDecision:  # noqa: ARG002
            return PolicyDecision(False, "no")

    runtime = tools.Runtime(
        config=runtime.config,
        audit=runtime.audit,
        policy=DenyOpsPolicy(
            allowed_repos=runtime.config.policy.allowed_repos,
            allowed_projects=runtime.config.policy.allowed_projects,
            pr_only=runtime.config.policy.pr_only,
            protected_branch_patterns=runtime.config.policy.protected_branches,
        ),
        auth=runtime.auth,
        github=runtime.github,
        graphql=runtime.graphql,
    )

    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_repository", {"owner": "octo", "repo": "repo"})

    assert out["ok"] is False
    assert out["code"] == "Forbidden"


@pytest.mark.asyncio
async def test_dispatch_tool_reports_tool_not_implemented(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    monkeypatch.setattr(tools, "_TOOL_FUNCS", {})

    out = await tools.dispatch_tool("get_repository", {"owner": "octo", "repo": "repo"})

    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_dispatch_tool_config_failure_still_returns_correlation_id(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_init() -> tools.Runtime:
        raise SafeError(code="Config", message="Missing config")

    monkeypatch.setattr(tools, "initialize_runtime_from_env", fail_init)

    out = await tools.dispatch_tool("get_repository", {"owner": "octo", "repo": "repo"})

    assert out["ok"] is False
    assert out["code"] == "Config"
    assert "correlation_id" in out


def test_validate_tool_arguments_rejects_extra_fields() -> None:
    with pytest.raises(SafeError):
        tools.validate_tool_arguments("get_repository", {"owner": "octo", "repo": "repo", "extra": "x"})


def test_validate_tool_arguments_unknown_tool() -> None:
    with pytest.raises(SafeError):
        tools.validate_tool_arguments("unknown_tool", {})


def test_validate_tool_arguments_skips_properties_without_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        tools.TOOL_METADATA,
        "_test_no_type",
        {
            "description": "test",
            "inputSchema": {
                "type": "object",
                "required": ["x"],
                "properties": {"x": {}},
                "additionalProperties": False,
            },
        },
    )

    # Should not raise due to missing type.
    tools.validate_tool_arguments("_test_no_type", {"x": "anything"})


def test_validate_tool_arguments_enforces_object_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        tools.TOOL_METADATA,
        "_test_object",
        {
            "description": "test",
            "inputSchema": {
                "type": "object",
                "required": ["obj"],
                "properties": {"obj": {"type": "object"}},
                "additionalProperties": False,
            },
        },
    )

    with pytest.raises(SafeError):
        tools.validate_tool_arguments("_test_object", {"obj": "not-an-object"})


def test_validate_tool_arguments_rejects_wrong_type() -> None:
    with pytest.raises(SafeError):
        tools.validate_tool_arguments("comment_on_issue", {"owner": "octo", "repo": "repo", "issue_number": "1", "body": "b"})


def test_validate_tool_arguments_rejects_wrong_string_type() -> None:
    with pytest.raises(SafeError):
        tools.validate_tool_arguments("get_repository", {"owner": 123, "repo": "repo"})


def test_validate_tool_arguments_rejects_wrong_boolean_type() -> None:
    with pytest.raises(SafeError):
        tools.validate_tool_arguments(
            "open_pull_request",
            {"owner": "octo", "repo": "repo", "title": "t", "head": "h", "base": "b", "draft": "no"},
        )


def test_validate_tool_arguments_rejects_wrong_array_type() -> None:
    with pytest.raises(SafeError):
        tools.validate_tool_arguments(
            "commit_changes",
            {"owner": "octo", "repo": "repo", "branch": "b", "message": "m", "changes": {"no": "list"}},
        )


def test_tools_require_helpers_raise_on_missing_or_wrong_types() -> None:
    with pytest.raises(SafeError):
        _ = tools._require_str({}, "owner")  # pylint: disable=protected-access
    with pytest.raises(SafeError):
        _ = tools._require_int({"issue_number": "1"}, "issue_number")  # pylint: disable=protected-access


def test_decode_change_content_utf8_and_base64() -> None:
    out1 = tools._decode_change_content(content="hi", encoding="utf-8")  # pylint: disable=protected-access
    assert out1 == b"hi"
    out2 = tools._decode_change_content(content="aGk=", encoding="base64")  # pylint: disable=protected-access
    assert out2 == b"hi"


@pytest.mark.asyncio
async def test_get_repository_rejects_unexpected_response(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={("GET", "/repos/octo/repo"): []})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_repository", {"owner": "octo", "repo": "repo"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_list_branches_rejects_unexpected_branches_response(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo"): {"default_branch": "main"},
            ("GET", "/repos/octo/repo/branches"): {"not": "a list"},
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_branches", {"owner": "octo", "repo": "repo"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_list_branches_rejects_unexpected_repository_response(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo"): [],
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_branches", {"owner": "octo", "repo": "repo"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_get_file_rejects_unexpected_file_response_type(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={("GET", "/repos/octo/repo/contents/a.txt"): []})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_file", {"owner": "octo", "repo": "repo", "path": "a.txt"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_list_issues_rejects_unexpected_response_type(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={("GET", "/repos/octo/repo/issues"): {"not": "a list"}})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_issues", {"owner": "octo", "repo": "repo"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_list_issues_skips_prs_and_invalid_items(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/issues"): [
                {"pull_request": {}},
                {"number": "1", "html_url": "https://example.invalid"},
                {"number": 2, "html_url": None},
                {"number": 3, "html_url": "https://github.com/octo/repo/issues/3"},
            ]
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_issues", {"owner": "octo", "repo": "repo"})
    assert out["ok"] is True
    assert out["issues"] == [{"number": 3, "url": "https://github.com/octo/repo/issues/3"}]


@pytest.mark.asyncio
async def test_create_branch_rejects_unexpected_ref_response_type(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={("GET", "/repos/octo/repo/git/ref/heads/main"): []})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("create_branch", {"owner": "octo", "repo": "repo", "base": "main", "branch": "feature/x"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_create_branch_treats_base_as_sha_when_ref_has_no_sha(monkeypatch: pytest.MonkeyPatch) -> None:
    class GitHubAssertsSha:
        async def request_json(self, **kwargs: Any) -> object:
            method = str(kwargs.get("method") or "")
            path = str(kwargs.get("path") or "")
            if method == "GET" and path.endswith("/git/ref/heads/main"):
                return {"object": {}}
            if method == "POST" and path.endswith("/git/refs"):
                assert kwargs.get("json_body", {}).get("sha") == "main"
                return {"ok": True}
            raise AssertionError(f"Unexpected call: {method} {path}")

    runtime = _runtime(routes={})
    runtime = tools.Runtime(
        config=runtime.config,
        audit=runtime.audit,
        policy=runtime.policy,
        auth=runtime.auth,
        github=GitHubAssertsSha(),  # type: ignore[arg-type]
        graphql=runtime.graphql,
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("create_branch", {"owner": "octo", "repo": "repo", "base": "main", "branch": "feature/x"})
    assert out["ok"] is True


@pytest.mark.asyncio
async def test_create_branch_propagates_post_error(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/git/ref/heads/main"): {"object": {"sha": "base"}},
            ("POST", "/repos/octo/repo/git/refs"): SafeError(code="GitHub", message="bad", status_code=400),
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("create_branch", {"owner": "octo", "repo": "repo", "base": "main", "branch": "feature/x"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_get_project_v2_by_number_reports_unexpected_owner_number_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {
                "repositoryOwner": {
                    "__typename": "Organization",
                    "login": "octo-org",
                    "projectV2": {"id": "PVT_123", "number": "3", "title": "Queue", "url": "https://example.invalid"},
                }
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_project_v2_by_number", {"owner_login": "octo-org", "project_number": 3})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_add_issue_to_project_v2_reports_unexpected_project_node_info(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[{"node": {"__typename": "ProjectV2", "number": "3", "owner": {"login": "octo-org"}}}],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("add_issue_to_project_v2", {"project_id": "PVT_123", "issue_node_id": "I_1"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_list_project_v2_fields_rejects_unexpected_owner_number_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[{"node": {"__typename": "ProjectV2", "number": "3", "owner": {"login": "octo-org"}}}],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_project_v2_fields", {"project_id": "PVT_123"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_list_project_v2_fields_rejects_unexpected_fields_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[{"node": {"__typename": "ProjectV2", "number": 3, "owner": {"login": "octo-org"}, "fields": {"nodes": "nope"}}}],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_project_v2_fields", {"project_id": "PVT_123"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_list_project_v2_items_rejects_bad_project_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime1 = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[{"node": {"__typename": "User"}}],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime1)
    out = await tools.dispatch_tool("list_project_v2_items", {"project_id": "PVT_123"})
    assert out["ok"] is False
    assert out["code"] == "UserInput"

    runtime2 = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[{"node": {"__typename": "ProjectV2", "number": "3", "owner": {"login": "octo-org"}}}],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime2)
    out = await tools.dispatch_tool("list_project_v2_items", {"project_id": "PVT_123"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_list_project_v2_items_rejects_unexpected_items_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime1 = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[{"node": {"__typename": "ProjectV2", "number": 3, "owner": {"login": "octo-org"}, "items": "nope"}}],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime1)
    out = await tools.dispatch_tool("list_project_v2_items", {"project_id": "PVT_123"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"

    runtime2 = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {
                "node": {
                    "__typename": "ProjectV2",
                    "number": 3,
                    "owner": {"login": "octo-org"},
                    "items": {"pageInfo": "nope", "nodes": []},
                }
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime2)
    out = await tools.dispatch_tool("list_project_v2_items", {"project_id": "PVT_123"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"

    runtime3 = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {
                "node": {
                    "__typename": "ProjectV2",
                    "number": 3,
                    "owner": {"login": "octo-org"},
                    "items": {"pageInfo": {"hasNextPage": "nope", "endCursor": None}, "nodes": []},
                }
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime3)
    out = await tools.dispatch_tool("list_project_v2_items", {"project_id": "PVT_123"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_list_project_v2_items_skips_non_object_and_missing_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {
                "node": {
                    "__typename": "ProjectV2",
                    "number": 3,
                    "owner": {"login": "octo-org"},
                    "items": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": ["nope", {"id": 1}],
                    },
                }
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_project_v2_items", {"project_id": "PVT_123"})
    assert out["ok"] is True
    assert out["items"] == []


@pytest.mark.asyncio
async def test_get_project_v2_item_reports_project_not_found_and_unexpected_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime1 = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[{"project": {"__typename": "User"}, "item": {}}],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime1)
    out = await tools.dispatch_tool("get_project_v2_item", {"project_id": "PVT_123", "item_id": "PVTI_1"})
    assert out["ok"] is False
    assert out["code"] == "UserInput"

    runtime2 = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {"project": {"__typename": "ProjectV2", "number": "3", "owner": {"login": "octo-org"}}, "item": {"__typename": "ProjectV2Item", "id": "PVTI_1"}}
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime2)
    out = await tools.dispatch_tool("get_project_v2_item", {"project_id": "PVT_123", "item_id": "PVTI_1"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_get_project_v2_item_reports_unexpected_item_id_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[
            {
                "project": {"__typename": "ProjectV2", "number": 3, "owner": {"login": "octo-org"}},
                "item": {"__typename": "ProjectV2Item", "id": None},
            }
        ],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_project_v2_item", {"project_id": "PVT_123", "item_id": "PVTI_1"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_set_project_v2_item_field_value_reports_project_not_found_and_unexpected_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime1 = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[{"node": {"__typename": "User"}}],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime1)
    out = await tools.dispatch_tool(
        "set_project_v2_item_field_value",
        {"project_id": "PVT_123", "item_id": "PVTI_1", "field_id": "F_1", "single_select_option_id": "O_1"},
    )
    assert out["ok"] is False
    assert out["code"] == "UserInput"

    runtime2 = _runtime(
        routes={},
        allowed_projects=frozenset({"octo-org/3"}),
        graphql_results=[{"node": {"__typename": "ProjectV2", "number": "3", "owner": {"login": "octo-org"}}}],
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime2)
    out = await tools.dispatch_tool(
        "set_project_v2_item_field_value",
        {"project_id": "PVT_123", "item_id": "PVTI_1", "field_id": "F_1", "single_select_option_id": "O_1"},
    )
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_commit_changes_rejects_empty_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)
    out = await tools.dispatch_tool("commit_changes", {"owner": "octo", "repo": "repo", "branch": "feature/x", "message": "m", "changes": []})
    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_commit_changes_reports_unexpected_ref_response(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/git/ref/heads/feature/x"): [],
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)
    out = await tools.dispatch_tool(
        "commit_changes",
        {"owner": "octo", "repo": "repo", "branch": "feature/x", "message": "m", "changes": [{"path": "a", "action": "delete"}]},
    )
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_commit_changes_reports_unexpected_commit_response(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/git/ref/heads/feature/x"): {"object": {"sha": "c0"}},
            ("GET", "/repos/octo/repo/git/commits/c0"): [],
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)
    out = await tools.dispatch_tool(
        "commit_changes",
        {"owner": "octo", "repo": "repo", "branch": "feature/x", "message": "m", "changes": [{"path": "a", "action": "delete"}]},
    )
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_commit_changes_reports_unexpected_commit_tree_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/git/ref/heads/feature/x"): {"object": {"sha": "c0"}},
            ("GET", "/repos/octo/repo/git/commits/c0"): {"tree": {}},
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)
    out = await tools.dispatch_tool(
        "commit_changes",
        {"owner": "octo", "repo": "repo", "branch": "feature/x", "message": "m", "changes": [{"path": "a", "action": "delete"}]},
    )
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_commit_changes_reports_unexpected_blob_sha(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/git/ref/heads/feature/x"): {"object": {"sha": "c0"}},
            ("GET", "/repos/octo/repo/git/commits/c0"): {"tree": {"sha": "t0"}},
            ("POST", "/repos/octo/repo/git/blobs"): {"sha": None},
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)
    out = await tools.dispatch_tool(
        "commit_changes",
        {"owner": "octo", "repo": "repo", "branch": "feature/x", "message": "m", "changes": [{"path": "a", "action": "upsert", "content": "hi"}]},
    )
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_open_pull_request_reports_unexpected_response_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime1 = _runtime(routes={("POST", "/repos/octo/repo/pulls"): []})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime1)
    out = await tools.dispatch_tool(
        "open_pull_request",
        {"owner": "octo", "repo": "repo", "title": "t", "head": "h", "base": "b"},
    )
    assert out["ok"] is False
    assert out["code"] == "GitHub"

    runtime2 = _runtime(routes={("POST", "/repos/octo/repo/pulls"): {"number": "7", "html_url": "https://example.invalid"}})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime2)
    out = await tools.dispatch_tool(
        "open_pull_request",
        {"owner": "octo", "repo": "repo", "title": "t", "head": "h", "base": "b"},
    )
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_comment_on_issue_reports_unexpected_response_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime1 = _runtime(routes={("POST", "/repos/octo/repo/issues/3/comments"): []})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime1)
    out = await tools.dispatch_tool("comment_on_issue", {"owner": "octo", "repo": "repo", "issue_number": 3, "body": "hi"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"

    runtime2 = _runtime(routes={("POST", "/repos/octo/repo/issues/3/comments"): {"id": "99", "html_url": "https://example.invalid"}})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime2)
    out = await tools.dispatch_tool("comment_on_issue", {"owner": "octo", "repo": "repo", "issue_number": 3, "body": "hi"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_get_file_validates_ref_type(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_file", {"owner": "octo", "repo": "repo", "path": "a", "ref": 123})
    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_get_file_rejects_unexpected_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/contents/a.txt"): {"type": "file", "encoding": "utf-8", "content": "nope"}
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_file", {"owner": "octo", "repo": "repo", "path": "a.txt"})
    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_create_branch_propagates_non_404_base_ref_error(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/git/ref/heads/main"): SafeError(
                code="GitHub",
                message="GitHub request failed",
                hint="Server error",
                status_code=500,
            )
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "create_branch",
        {"owner": "octo", "repo": "repo", "base": "main", "branch": "feature/x"},
    )

    assert out["ok"] is False
    assert out["code"] == "GitHub"


@pytest.mark.asyncio
async def test_commit_changes_rejects_total_bytes_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    # Two small files that together exceed commit_max_total_bytes=15.
    out = await tools.dispatch_tool(
        "commit_changes",
        {
            "owner": "octo",
            "repo": "repo",
            "branch": "feature/x",
            "message": "m",
            "changes": [
                {"path": "a", "action": "upsert", "content": "0123456789", "encoding": "utf-8"},
                {"path": "b", "action": "upsert", "content": "0123456", "encoding": "utf-8"},
            ],
        },
    )
    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_commit_changes_rejects_binary_upsert(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    b64 = base64.b64encode(b"\xff\x00").decode("utf-8")
    out = await tools.dispatch_tool(
        "commit_changes",
        {
            "owner": "octo",
            "repo": "repo",
            "branch": "feature/x",
            "message": "m",
            "changes": [{"path": "a", "action": "upsert", "content": b64, "encoding": "base64"}],
        },
    )
    assert out["ok"] is False
    assert out["code"] == "UserInput"


@pytest.mark.asyncio
async def test_create_branch_propagates_non_404_ref_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(
        routes={
            ("GET", "/repos/octo/repo/git/ref/heads/main"): SafeError(
                code="GitHub",
                message="GitHub request failed",
                hint="boom",
                status_code=500,
            )
        }
    )
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool(
        "create_branch",
        {"owner": "octo", "repo": "repo", "base": "main", "branch": "feature/z"},
    )
    assert out["ok"] is False
    assert out["code"] == "GitHub"
