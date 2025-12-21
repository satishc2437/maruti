import asyncio
from pathlib import Path

import pytest

from agent_memory import errors, memory_ops, safety, tools


def test_errors_helpers_cover_branches():
    e = errors.user_input_error("m", hint="h", correlation_id="abcd1234")
    assert e["ok"] is False
    assert e["code"] == "UserInput"
    assert e["hint"] == "h"
    assert e["correlation_id"] == "abcd1234"

    assert errors.forbidden_error("m", correlation_id="c")["code"] == "Forbidden"
    assert errors.not_found_error("m", correlation_id="c")["code"] == "NotFound"
    assert errors.timeout_error("m", correlation_id="c")["code"] == "Timeout"
    assert errors.cancellation_error("m", correlation_id="c")["code"] == "Cancelled"

    internal = errors.internal_error("boom", detail="x" * 1000, correlation_id="c")
    assert internal["code"] == "Internal"
    assert internal["correlation_id"] == "c"
    assert len(internal.get("detail", "")) == 200


def test_safety_validate_repository_root_path_traversal(monkeypatch, tmp_path):
    # Force resolve() to be a no-op so ".." and "~" survive into the string check.
    monkeypatch.setattr(safety.Path, "resolve", lambda self: self)

    with pytest.raises(safety.PathTraversalError):
        safety.validate_repository_root("..")

    monkeypatch.setattr(safety.os.path, "expanduser", lambda s: s)
    monkeypatch.setattr(safety.os.path, "expandvars", lambda s: s)
    with pytest.raises(safety.PathTraversalError):
        safety.validate_repository_root("~")


def test_safety_validate_repository_root_invalid_and_permissions(monkeypatch, tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(safety.InvalidRepositoryError):
        safety.validate_repository_root(missing)

    file_path = tmp_path / "file.txt"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(safety.InvalidRepositoryError):
        safety.validate_repository_root(file_path)

    monkeypatch.setattr(safety.os, "access", lambda *args, **kwargs: False)
    with pytest.raises(safety.InvalidRepositoryError):
        safety.validate_repository_root(tmp_path)


def test_safety_validate_agent_name_and_date_and_section():
    assert safety.validate_agent_name("Agent1") == "agent1"

    with pytest.raises(ValueError):
        safety.validate_agent_name("bad agent")

    with pytest.raises(ValueError):
        safety.validate_agent_name("!bad")

    with pytest.raises(ValueError):
        safety.validate_agent_name("a" * 51)

    assert safety.validate_date_format("2025-01-02") == "2025-01-02"

    with pytest.raises(ValueError):
        safety.validate_date_format("2025/01/02")

    with pytest.raises(ValueError):
        safety.validate_date_format(123)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        safety.validate_date_format("2025-02-30")

    with pytest.raises(ValueError):
        safety.validate_section_name("Nope", ["Context"])

    with pytest.raises(ValueError):
        safety.validate_section_name(123, ["Context"])  # type: ignore[arg-type]


def test_safety_ensure_memory_path_error(monkeypatch, tmp_path):
    monkeypatch.setattr(safety.Path, "mkdir", lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("nope")))
    with pytest.raises(safety.MemorySafetyError):
        safety.ensure_memory_path(Path(tmp_path), "agent")


def test_safety_get_safe_file_info_and_sanitize(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x", encoding="utf-8")
    info = safety.get_safe_file_info(f)
    assert info["exists"] is True
    assert info["filename"] == "a.txt"
    assert info["size_bytes"] == 1

    f.unlink()
    missing = safety.get_safe_file_info(f)
    assert missing["exists"] is False

    assert safety.sanitize_content(123).startswith("123")
    big = safety.sanitize_content("a" * 10001)
    assert big.endswith("... [truncated]")


def test_memory_ops_allowed_sections_and_errors(tmp_path, monkeypatch):
    m = memory_ops.MemoryManager(tmp_path, "agent")

    # Explicit schema sections
    m.schema_path.write_text("# X\n\n## Header\n- x\n\n## A\n- a\n\n## B\n- b\n", encoding="utf-8")
    assert m._get_allowed_sections() == ["A", "B"]

    # No sections -> defaults
    m.schema_path.write_text("# X\n\n## Header\n- x\n", encoding="utf-8")
    assert m._get_allowed_sections() == memory_ops.DEFAULT_ALLOWED_SECTIONS

    # Read error -> defaults
    monkeypatch.setattr(Path, "read_text", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("boom")))
    assert m._get_allowed_sections() == memory_ops.DEFAULT_ALLOWED_SECTIONS


def test_memory_ops_session_and_append_and_summary(tmp_path):
    m = memory_ops.MemoryManager(tmp_path, "agent")

    # start_session creates file and placeholders
    start = m.start_session("2025-01-02")
    assert start["created"] is True

    # append_entry creates entry
    res = m.append_entry("Context", "hello", date="2025-01-02")
    assert res["ok"] is True

    # append_entry auto-creates session when missing
    m2 = memory_ops.MemoryManager(tmp_path, "agent2")
    res2 = m2.append_entry("Context", "hello", date="2025-01-03")
    assert res2["ok"] is True

    # list_sessions filters/sorts and applies limit
    (m.logs_path / "notes.md").write_text("x", encoding="utf-8")
    m.start_session("2025-01-01")
    sessions = m.list_sessions(limit=1)["sessions"]
    assert sessions == ["2025-01-02.md"]

    # read_summary recreates missing file
    m.summary_path.unlink()
    summary = m.read_summary()
    assert "summary" in summary

    # update_summary invalid mode
    with pytest.raises(ValueError):
        m.update_summary("Overview", "x", mode="nope")

    # update_summary append and replace branches
    a = m.update_summary("Overview", "first", mode="append")
    assert a["ok"] is True
    b = m.update_summary("Overview", "replaced", mode="replace")
    assert b["ok"] is True

    # update_summary section missing branch
    c = m.update_summary("New Section", "x", mode="append")
    assert c["ok"] is True

    # list_sessions when logs dir missing
    if m.logs_path.exists():
        for child in m.logs_path.iterdir():
            child.unlink()
        m.logs_path.rmdir()
    assert m.list_sessions()["sessions"] == []

    # get_schema_info
    schema_info = m.get_schema_info()
    assert schema_info["schema_version"] == memory_ops.SCHEMA_VERSION
    assert "schema_content" in schema_info


def test_memory_ops_invalid_date_rejected(tmp_path):
    m = memory_ops.MemoryManager(tmp_path, "agent")
    with pytest.raises(ValueError):
        m._get_session_file_path("not-a-date")

    p = m._get_session_file_path("2025-01-02")
    assert p.name == "2025-01-02.md"


def test_memory_ops_append_missing_section_raises(tmp_path):
    m = memory_ops.MemoryManager(tmp_path, "agent")
    m.start_session("2025-01-02")

    # Remove the section header from the file so _find_section_in_content returns -1.
    session_file = m.logs_path / "2025-01-02.md"
    content = session_file.read_text(encoding="utf-8").replace("## Context\n\n", "")
    session_file.write_text(content, encoding="utf-8")

    with pytest.raises(safety.SchemaValidationError):
        m.append_entry("Context", "x", date="2025-01-02")


def test_tools_error_mapping(monkeypatch, tmp_path):
    repo_root = str(tmp_path)

    class BoomManager:
        def __init__(self, *args, **kwargs):
            raise safety.PathTraversalError("escape")

    monkeypatch.setattr(tools, "MemoryManager", BoomManager)
    r = asyncio.run(tools.tool_start_session({"agent_name": "a", "repo_root": repo_root}))
    assert r["ok"] is False
    assert r["code"] == "Forbidden"

    class BadRepoManager:
        def __init__(self, *args, **kwargs):
            raise safety.InvalidRepositoryError("bad")

    monkeypatch.setattr(tools, "MemoryManager", BadRepoManager)
    r = asyncio.run(tools.tool_start_session({"agent_name": "a", "repo_root": repo_root}))
    assert r["ok"] is False
    assert r["code"] == "UserInput"

    class SchemaBoomManager:
        def __init__(self, *args, **kwargs):
            pass

        def append_entry(self, *args, **kwargs):
            raise safety.SchemaValidationError("bad section")

    monkeypatch.setattr(tools, "MemoryManager", SchemaBoomManager)
    r = asyncio.run(
        tools.tool_append_entry({"agent_name": "a", "repo_root": repo_root, "section": "Context", "content": "x"})
    )
    assert r["ok"] is False
    assert r["code"] == "UserInput"


def test_run_with_timeout_success():
    async def fast():
        return 123

    assert asyncio.run(tools.run_with_timeout(fast(), timeout_seconds=1.0)) == 123
