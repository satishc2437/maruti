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


def _runtime(*, routes: dict[tuple[str, str], object | Exception]) -> tools.Runtime:
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
        limits=LimitsConfig(commit_max_files=2, commit_max_file_bytes=10, commit_max_total_bytes=15),
    )
    audit = DummyAudit(events=[])
    return tools.Runtime(
        config=cfg,
        audit=audit,  # type: ignore[arg-type]
        policy=Policy(
            allowed_repos=cfg.policy.allowed_repos,
            pr_only=cfg.policy.pr_only,
            protected_branch_patterns=cfg.policy.protected_branches,
        ),
        auth=None,  # type: ignore[arg-type]
        github=DummyGitHub(routes),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_get_file_rejects_non_file_type(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = _runtime(routes={("GET", "/repos/octo/repo/contents/a"): {"type": "dir"}})
    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("get_file", {"owner": "octo", "repo": "repo", "path": "a"})

    assert out["ok"] is False
    assert out["code"] == "UserInput"


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
            pr_only=runtime.config.policy.pr_only,
            protected_branch_patterns=runtime.config.policy.protected_branches,
        ),
        auth=runtime.auth,
        github=runtime.github,
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
