"""Foundational tests: audit event schema."""

from __future__ import annotations

import json
from pathlib import Path

import github_app_mcp.tools as tools
import pytest
from github_app_mcp.audit import AuditLogger, build_event, new_correlation_id
from github_app_mcp.config import AppConfig, LimitsConfig, PolicyConfig
from github_app_mcp.github_graphql_client import GraphQLResult
from github_app_mcp.policy import Policy


def test_new_correlation_id_is_hex() -> None:
    cid = new_correlation_id()
    assert len(cid) == 32
    int(cid, 16)  # should parse


def test_audit_logger_writes_jsonl_to_file(tmp_path: Path) -> None:
    sink = tmp_path / "audit.jsonl"
    logger = AuditLogger(sink_path=sink)

    event = build_event(
        correlation_id="abcd" * 8,
        operation="get_repository",
        target_repo="octo/repo",
        outcome="denied",
        reason="Repository is not allowed",
        duration_ms=12,
    )
    logger.write_event(event)

    lines = sink.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["correlation_id"] == "abcd" * 8
    assert payload["operation"] == "get_repository"
    assert payload["target_repo"] == "octo/repo"
    assert payload["outcome"] == "denied"
    assert "timestamp" in payload
    assert payload["duration_ms"] == 12


class DummyGraphQL:
    async def execute(self, _query: str, _variables: dict[str, object] | None = None, _budget: object | None = None) -> GraphQLResult:
        # Return a non-project node so the tool fails predictably.
        return GraphQLResult(data={"node": {"__typename": "NotAProject"}})


class DummyGitHub:
    async def request_json(self, **_kwargs: object) -> object:  # pragma: no cover
        raise AssertionError("GitHub should not be called")


@pytest.mark.asyncio
async def test_failed_project_tool_is_audited_once_and_returns_correlation_id(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = AppConfig(
        app_id=1,
        installation_id=2,
        private_key_path=Path("/tmp/does-not-matter.pem"),
        policy=PolicyConfig(
            allowed_repos=frozenset({"octo/repo"}),
            allowed_projects=frozenset({"octo-org/3"}),
            pr_only=False,
            protected_branches=(),
        ),
        audit_log_path=None,
        audit_max_bytes=5 * 1024 * 1024,
        audit_max_backups=2,
        limits=LimitsConfig(),
    )

    # Reuse the real audit logger interface via tools.Runtime.
    class InMemoryAudit:
        def __init__(self) -> None:
            self.events = []

        def write_event(self, event: object) -> None:
            self.events.append(event)

        def measure_start(self) -> float:
            return 0.0

        def measure_duration_ms(self, _start: float) -> int:
            return 0

    audit = InMemoryAudit()
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
        graphql=DummyGraphQL(),  # type: ignore[arg-type]
    )

    monkeypatch.setattr(tools, "initialize_runtime_from_env", lambda: runtime)

    out = await tools.dispatch_tool("list_project_v2_fields", {"project_id": "PVT_123"})

    assert out["ok"] is False
    assert "correlation_id" in out
    assert len(audit.events) == 1
