"""Structured audit logging.

The audit log must include exactly one event per operation attempt and must never contain
secret material (tokens, private key content/path, installation IDs).
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def new_correlation_id() -> str:
    """Generate a random correlation id for traceability.

    Must not encode or include installation identifiers.
    """
    return uuid.uuid4().hex


def _now_rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """A single audit event."""

    timestamp: str
    correlation_id: str
    operation: str
    target_repo: str
    outcome: str
    reason: str | None
    duration_ms: int | None


class AuditLogger:
    """Writes audit events as JSONL to stderr and optionally to a file."""

    def __init__(
        self,
        *,
        sink_path: Path | None,
        max_bytes: int = 5 * 1024 * 1024,
        max_backups: int = 2,
    ) -> None:
        """Create an audit logger.

        Rotation is best-effort; failures writing the optional file sink must not
        break tool execution.
        """
        self._sink_path = sink_path
        self._max_bytes = max_bytes
        self._max_backups = max_backups

    def _rotate_if_needed(self) -> None:
        if self._sink_path is None:
            return
        try:
            if not self._sink_path.exists():
                return
            size = self._sink_path.stat().st_size
            if size < self._max_bytes:
                return

            # Rotate: log -> log.1 -> log.2 (best-effort).
            # Avoid emitting paths to agent-visible outputs.
            if self._max_backups > 0:
                oldest = Path(f"{self._sink_path}.{self._max_backups}")
                if oldest.exists():
                    oldest.unlink(missing_ok=True)
                for i in range(self._max_backups, 1, -1):
                    src = Path(f"{self._sink_path}.{i - 1}")
                    dst = Path(f"{self._sink_path}.{i}")
                    if src.exists():
                        src.replace(dst)
                self._sink_path.replace(Path(f"{self._sink_path}.1"))
            else:
                # No backups retained; truncate.
                self._sink_path.write_text("", encoding="utf-8")
        except Exception:  # pragma: no cover  # pylint: disable=broad-exception-caught
            # Never crash tool execution due to audit sink I/O.
            return

    def write_event(self, event: AuditEvent) -> None:
        """Write an audit event to stderr and optionally to a JSONL file."""
        payload = {
            "timestamp": event.timestamp,
            "correlation_id": event.correlation_id,
            "operation": event.operation,
            "target_repo": event.target_repo,
            "outcome": event.outcome,
        }
        if event.reason is not None:
            payload["reason"] = event.reason
        if event.duration_ms is not None:
            payload["duration_ms"] = event.duration_ms

        line = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        print(line, file=sys.stderr)
        if self._sink_path is not None:
            try:
                self._sink_path.parent.mkdir(parents=True, exist_ok=True)
                self._rotate_if_needed()
                with self._sink_path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:  # pragma: no cover  # pylint: disable=broad-exception-caught
                return

    def measure_start(self) -> float:
        """Return a monotonic start timestamp for duration measurement."""
        return time.monotonic()

    def measure_duration_ms(self, start: float) -> int:
        """Convert a monotonic start timestamp into elapsed milliseconds."""
        return int((time.monotonic() - start) * 1000)


def build_event(
    *,
    correlation_id: str,
    operation: str,
    target_repo: str,
    outcome: str,
    reason: str | None = None,
    duration_ms: int | None = None,
) -> AuditEvent:
    """Construct an audit event."""
    return AuditEvent(
        timestamp=_now_rfc3339(),
        correlation_id=correlation_id,
        operation=operation,
        target_repo=target_repo,
        outcome=outcome,
        reason=reason,
        duration_ms=duration_ms,
    )
