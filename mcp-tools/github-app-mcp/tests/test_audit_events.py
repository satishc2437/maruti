"""Audit event tests (US3).

Verifies audit log payloads:
- always include correlation_id
- never include obvious token markers
- file sink rotation is best-effort and safe
"""

from __future__ import annotations

import json

from github_app_mcp.audit import AuditLogger, build_event


def test_audit_event_emits_correlation_id_and_no_tokens(capsys) -> None:
    logger = AuditLogger(sink_path=None)

    ev = build_event(
        correlation_id="abc123",
        operation="get_repository",
        target_repo="octo/repo",
        outcome="succeeded",
        reason=None,
        duration_ms=12,
    )

    logger.write_event(ev)
    captured = capsys.readouterr()

    payload = json.loads(captured.err.strip())
    assert payload["correlation_id"] == "abc123"
    assert payload["operation"] == "get_repository"

    # Basic guardrails for obvious token markers.
    assert "ghp_" not in captured.err
    assert "github_pat_" not in captured.err
    assert "Bearer " not in captured.err


def test_audit_file_sink_rotates(tmp_path) -> None:
    sink = tmp_path / "audit.jsonl"
    logger = AuditLogger(sink_path=sink, max_bytes=80, max_backups=2)

    # Write enough events to exceed max_bytes and trigger rotation.
    for i in range(10):
        ev = build_event(
            correlation_id=f"c{i}",
            operation="get_repository",
            target_repo="octo/repo",
            outcome="succeeded",
            reason=None,
            duration_ms=1,
        )
        logger.write_event(ev)

    # Best-effort: rotation should have produced at least one backup.
    assert sink.exists()
    assert (tmp_path / "audit.jsonl.1").exists() or (tmp_path / "audit.jsonl.2").exists()
