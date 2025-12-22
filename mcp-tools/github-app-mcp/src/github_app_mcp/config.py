"""Configuration loading for github-app-mcp.

Configuration is supplied by the host environment (e.g., MCP client config), not by the agent.
All sensitive values (private key path, installation id) are treated as secrets and must never
be emitted to agents, logs, or audit reasons.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .errors import SafeError


@dataclass(frozen=True, slots=True)
class PolicyConfig:
    """Policy guardrails configuration."""

    allowed_repos: frozenset[str]
    pr_only: bool
    protected_branches: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LimitsConfig:
    """Non-functional safety limits."""

    # Network
    total_timeout_s: float = 60.0
    connect_timeout_s: float = 5.0
    read_timeout_s: float = 30.0

    # Retries
    max_attempts: int = 3
    max_backoff_s: float = 5.0

    # Payload limits
    commit_max_files: int = 25
    commit_max_file_bytes: int = 50 * 1024
    commit_max_total_bytes: int = 200 * 1024
    get_file_max_bytes: int = 100 * 1024


@dataclass(frozen=True, slots=True)
class AppConfig:
    """App + installation binding configuration."""

    app_id: int
    installation_id: int
    private_key_path: Path

    policy: PolicyConfig
    audit_log_path: Path | None
    audit_max_bytes: int
    audit_max_backups: int
    limits: LimitsConfig


def _parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _parse_allowed_repos(value: str | None) -> frozenset[str]:
    if not value:
        return frozenset()
    parts = [p.strip() for p in value.split(",")]
    repos = [p for p in parts if p]
    return frozenset(repos)


def _parse_patterns(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    parts = [p.strip() for p in value.split(",")]
    patterns = [p for p in parts if p]
    return tuple(patterns)


def load_config_from_env() -> AppConfig:
    """Load and validate configuration from environment variables.

    Raises:
        SafeError: If configuration is missing/invalid.
    """
    app_id_raw = os.getenv("GITHUB_APP_ID")
    installation_id_raw = os.getenv("GITHUB_APP_INSTALLATION_ID")
    private_key_path_raw = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")

    if not app_id_raw or not installation_id_raw or not private_key_path_raw:
        raise SafeError(
            code="Config",
            message="Missing required configuration (GITHUB_APP_ID, GITHUB_APP_INSTALLATION_ID, GITHUB_APP_PRIVATE_KEY_PATH)",
        )

    try:
        app_id = int(app_id_raw)
        installation_id = int(installation_id_raw)
    except ValueError as exc:
        raise SafeError(code="Config", message="GITHUB_APP_ID and GITHUB_APP_INSTALLATION_ID must be integers") from exc

    key_path = Path(private_key_path_raw)
    if not key_path.is_absolute():
        raise SafeError(code="Config", message="GITHUB_APP_PRIVATE_KEY_PATH must be an absolute path")

    # Fail fast if unreadable; never echo the path.
    try:
        if not key_path.is_file():
            raise SafeError(code="Config", message="GitHub App private key file is missing or not a file")
        _ = key_path.read_bytes()
    except SafeError:
        raise
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise SafeError(code="Config", message="GitHub App private key file is unreadable") from exc

    allowed_repos = _parse_allowed_repos(os.getenv("GITHUB_APP_MCP_ALLOWED_REPOS"))
    pr_only = _parse_bool(os.getenv("GITHUB_APP_MCP_PR_ONLY"))
    protected = _parse_patterns(os.getenv("GITHUB_APP_MCP_PROTECTED_BRANCHES"))

    audit_path_raw = os.getenv("GITHUB_APP_MCP_AUDIT_LOG_PATH")
    audit_path: Path | None = None
    if audit_path_raw:
        p = Path(audit_path_raw)
        if not p.is_absolute():
            raise SafeError(code="Config", message="GITHUB_APP_MCP_AUDIT_LOG_PATH must be an absolute path when set")
        audit_path = p

    # Minimal retention controls (safe defaults). These are intentionally host-controlled
    # (not agent-controlled) and not exposed in tool outputs.
    audit_max_bytes = 5 * 1024 * 1024
    audit_max_backups = 2

    return AppConfig(
        app_id=app_id,
        installation_id=installation_id,
        private_key_path=key_path,
        policy=PolicyConfig(
            allowed_repos=allowed_repos,
            pr_only=pr_only,
            protected_branches=protected,
        ),
        audit_log_path=audit_path,
        audit_max_bytes=audit_max_bytes,
        audit_max_backups=audit_max_backups,
        limits=LimitsConfig(),
    )
