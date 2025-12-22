"""Foundational tests: audit event schema."""

from __future__ import annotations

import json
from pathlib import Path

from github_app_mcp.audit import AuditLogger, build_event, new_correlation_id


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
