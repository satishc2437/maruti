"""Audit logger rotation coverage."""

from __future__ import annotations

from pathlib import Path

from github_app_mcp.audit import AuditLogger, build_event


def test_audit_logger_rotates_when_exceeding_max_bytes(tmp_path: Path) -> None:
    sink = tmp_path / "audit.jsonl"

    logger = AuditLogger(sink_path=sink, max_bytes=1, max_backups=2)

    # First write creates the file.
    logger.write_event(
        build_event(
            correlation_id="c1",
            operation="op",
            target_repo="octo/repo",
            outcome="succeeded",
            reason=None,
            duration_ms=1,
        )
    )

    # Second write triggers rotation (best-effort) due to tiny max_bytes.
    logger.write_event(
        build_event(
            correlation_id="c2",
            operation="op",
            target_repo="octo/repo",
            outcome="succeeded",
            reason=None,
            duration_ms=1,
        )
    )

    assert sink.exists()
    assert (tmp_path / "audit.jsonl.1").exists()


def test_audit_logger_truncates_when_backups_disabled(tmp_path: Path) -> None:
    sink = tmp_path / "audit.jsonl"

    logger = AuditLogger(sink_path=sink, max_bytes=1, max_backups=0)

    logger.write_event(
        build_event(
            correlation_id="c1",
            operation="op",
            target_repo="octo/repo",
            outcome="succeeded",
            reason="r",
            duration_ms=None,
        )
    )

    logger.write_event(
        build_event(
            correlation_id="c2",
            operation="op",
            target_repo="octo/repo",
            outcome="succeeded",
            reason="r",
            duration_ms=None,
        )
    )

    assert sink.exists()


def test_audit_logger_creates_parent_dir_and_does_not_rotate_when_small(tmp_path: Path) -> None:
    sink = tmp_path / "subdir" / "audit.jsonl"
    logger = AuditLogger(sink_path=sink, max_bytes=10_000, max_backups=2)

    logger.write_event(
        build_event(
            correlation_id="c1",
            operation="op",
            target_repo="octo/repo",
            outcome="succeeded",
            reason=None,
            duration_ms=1,
        )
    )

    assert sink.exists()
    assert not (tmp_path / "subdir" / "audit.jsonl.1").exists()


def test_audit_logger_rotate_if_needed_no_sink_is_noop() -> None:
    logger = AuditLogger(sink_path=None)
    logger._rotate_if_needed()  # pylint: disable=protected-access


def test_audit_logger_rotate_if_needed_returns_when_file_missing(tmp_path: Path) -> None:
    sink = tmp_path / "missing.jsonl"
    logger = AuditLogger(sink_path=sink, max_bytes=1, max_backups=1)
    logger._rotate_if_needed()  # pylint: disable=protected-access


def test_audit_logger_rotate_if_needed_returns_when_under_size_limit(tmp_path: Path) -> None:
    sink = tmp_path / "audit.jsonl"
    sink.write_text("x\n", encoding="utf-8")
    logger = AuditLogger(sink_path=sink, max_bytes=10_000, max_backups=1)
    logger._rotate_if_needed()  # pylint: disable=protected-access


def test_audit_logger_writes_to_file_sink(tmp_path: Path) -> None:
    sink = tmp_path / "subdir2" / "audit.jsonl"
    logger = AuditLogger(sink_path=sink, max_bytes=10_000, max_backups=1)

    logger.write_event(
        build_event(
            correlation_id="c123",
            operation="op",
            target_repo="octo/repo",
            outcome="succeeded",
            reason=None,
            duration_ms=1,
        )
    )

    text = sink.read_text(encoding="utf-8")
    assert "c123" in text
