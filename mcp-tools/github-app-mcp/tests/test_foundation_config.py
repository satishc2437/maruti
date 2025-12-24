"""Foundational tests: configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest
from github_app_mcp.config import load_config_from_env
from github_app_mcp.errors import SafeError


def test_load_config_requires_required_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_APP_ID", raising=False)
    monkeypatch.delenv("GITHUB_APP_INSTALLATION_ID", raising=False)
    monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY_PATH", raising=False)

    with pytest.raises(SafeError) as exc:
        _ = load_config_from_env()

    assert "Missing required configuration" in exc.value.message


def test_load_config_validates_key_path_absolute(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pem = tmp_path / "key.pem"
    pem.write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n", encoding="utf-8")

    monkeypatch.setenv("GITHUB_APP_ID", "1")
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "2")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", "relative.pem")

    with pytest.raises(SafeError) as exc:
        _ = load_config_from_env()

    assert "absolute path" in exc.value.message


def test_load_config_parses_policy_env_vars(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pem = tmp_path / "key.pem"
    pem.write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n", encoding="utf-8")

    monkeypatch.setenv("GITHUB_APP_ID", "123")
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "456")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(pem))
    monkeypatch.setenv("GITHUB_APP_MCP_ALLOWED_REPOS", "octo/repo1, octo/repo2")
    monkeypatch.setenv("GITHUB_APP_MCP_ALLOWED_PROJECTS", "octo-org/3, octo-org/7")
    monkeypatch.setenv("GITHUB_APP_MCP_PR_ONLY", "1")
    monkeypatch.setenv("GITHUB_APP_MCP_PROTECTED_BRANCHES", "main,release/*")

    cfg = load_config_from_env()
    assert cfg.app_id == 123
    assert cfg.installation_id == 456
    assert cfg.private_key_path == pem
    assert cfg.policy.pr_only is True
    assert cfg.policy.allowed_repos == frozenset({"octo/repo1", "octo/repo2"})
    assert cfg.policy.allowed_projects == frozenset({"octo-org/3", "octo-org/7"})
    assert cfg.policy.protected_branches == ("main", "release/*")


def test_load_config_rejects_invalid_allowed_projects_entry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pem = tmp_path / "key.pem"
    pem.write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n", encoding="utf-8")

    monkeypatch.setenv("GITHUB_APP_ID", "1")
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "2")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(pem))
    monkeypatch.setenv("GITHUB_APP_MCP_ALLOWED_PROJECTS", "not-a-project")

    with pytest.raises(SafeError) as exc:
        _ = load_config_from_env()

    assert "GITHUB_APP_MCP_ALLOWED_PROJECTS" in exc.value.message


@pytest.mark.parametrize(
    "value",
    [
        "/3",  # missing owner
        "octo-org/not-int",  # bad number
        "octo-org/0",  # number too small
    ],
)
def test_load_config_rejects_more_invalid_allowed_projects_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str
) -> None:
    pem = tmp_path / "key.pem"
    pem.write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n", encoding="utf-8")

    monkeypatch.setenv("GITHUB_APP_ID", "1")
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "2")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(pem))
    monkeypatch.setenv("GITHUB_APP_MCP_ALLOWED_PROJECTS", value)

    with pytest.raises(SafeError) as exc:
        _ = load_config_from_env()

    assert "GITHUB_APP_MCP_ALLOWED_PROJECTS" in exc.value.message


def test_load_config_validates_app_id_and_installation_id_ints(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pem = tmp_path / "key.pem"
    pem.write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n", encoding="utf-8")

    monkeypatch.setenv("GITHUB_APP_ID", "not-int")
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "2")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(pem))

    with pytest.raises(SafeError) as exc:
        _ = load_config_from_env()

    assert "must be integers" in exc.value.message


def test_load_config_rejects_missing_or_non_file_key_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    missing = tmp_path / "missing.pem"

    monkeypatch.setenv("GITHUB_APP_ID", "1")
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "2")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(missing))

    with pytest.raises(SafeError) as exc:
        _ = load_config_from_env()

    assert "missing" in exc.value.message.lower()


def test_load_config_validates_audit_log_path_absolute(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pem = tmp_path / "key.pem"
    pem.write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n", encoding="utf-8")

    monkeypatch.setenv("GITHUB_APP_ID", "1")
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "2")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(pem))
    monkeypatch.setenv("GITHUB_APP_MCP_AUDIT_LOG_PATH", "relative.jsonl")

    with pytest.raises(SafeError) as exc:
        _ = load_config_from_env()

    assert "absolute" in exc.value.message.lower()


def test_load_config_accepts_absolute_audit_log_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pem = tmp_path / "key.pem"
    pem.write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n", encoding="utf-8")
    audit = tmp_path / "audit.jsonl"

    monkeypatch.setenv("GITHUB_APP_ID", "1")
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "2")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(pem))
    monkeypatch.setenv("GITHUB_APP_MCP_AUDIT_LOG_PATH", str(audit))

    cfg = load_config_from_env()
    assert cfg.audit_log_path == audit


def test_load_config_rejects_relative_audit_log_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pem = tmp_path / "key.pem"
    pem.write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n", encoding="utf-8")

    monkeypatch.setenv("GITHUB_APP_ID", "1")
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "2")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(pem))
    monkeypatch.setenv("GITHUB_APP_MCP_AUDIT_LOG_PATH", "./audit.jsonl")

    with pytest.raises(SafeError):
        _ = load_config_from_env()
