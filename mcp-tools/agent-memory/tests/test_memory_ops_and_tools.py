import asyncio

import pytest

from agent_memory import memory_ops, safety, tools


def test_memory_manager_roundtrip(tmp_path):
    manager = memory_ops.MemoryManager(tmp_path, "test_agent")

    start = manager.start_session("2025-01-02")
    assert start["created"] is True

    append = manager.append_entry("Context", "hello", date="2025-01-02")
    assert append["ok"] is True

    sessions = manager.list_sessions(limit=10)
    assert "sessions" in sessions
    assert "2025-01-02.md" in sessions["sessions"]

    summary = manager.read_summary()
    assert "summary" in summary
    assert "file_path" in summary

    upd1 = manager.update_summary("Overview", "first", mode="append")
    assert upd1["ok"] is True

    upd2 = manager.update_summary("Overview", "replaced", mode="replace")
    assert upd2["ok"] is True


def test_memory_manager_validation_errors(tmp_path):
    manager = memory_ops.MemoryManager(tmp_path, "test_agent")

    with pytest.raises(ValueError):
        manager.append_entry("NotASection", "x")

    with pytest.raises(ValueError):
        safety.validate_agent_name("invalid/agent")

    with pytest.raises(ValueError):
        safety.validate_date_format("2025-99-99")


def test_tools_validation_helpers(tmp_path):
    # start_session
    ok = tools.validate_start_session_params({"agent_name": "a", "repo_root": str(tmp_path)})
    assert ok["agent_name"] == "a"

    with pytest.raises(ValueError):
        tools.validate_start_session_params({"agent_name": 123, "repo_root": str(tmp_path)})

    # append_entry
    with pytest.raises(ValueError):
        tools.validate_append_entry_params({"agent_name": "a", "repo_root": str(tmp_path), "section": "Context"})


def test_run_with_timeout_times_out():
    async def slow():
        await asyncio.sleep(0.05)
        return 123

    result = asyncio.run(tools.run_with_timeout(slow(), timeout_seconds=0.001))
    assert result["ok"] is False
    assert result["code"] == "Timeout"


def test_tool_endpoints_happy_and_error(tmp_path):
    repo_root = str(tmp_path)

    start = asyncio.run(tools.tool_start_session({"agent_name": "test_agent", "repo_root": repo_root, "date": "2025-01-02"}))
    assert start["ok"] is True

    append = asyncio.run(
        tools.tool_append_entry(
            {
                "agent_name": "test_agent",
                "repo_root": repo_root,
                "date": "2025-01-02",
                "section": "Context",
                "content": "hi",
            }
        )
    )
    assert append["ok"] is True

    read = asyncio.run(tools.tool_read_summary({"agent_name": "test_agent", "repo_root": repo_root}))
    assert read["ok"] is True

    upd = asyncio.run(
        tools.tool_update_summary(
            {
                "agent_name": "test_agent",
                "repo_root": repo_root,
                "section": "Overview",
                "content": "x",
                "mode": "append",
            }
        )
    )
    assert upd["ok"] is True

    sessions = asyncio.run(tools.tool_list_sessions({"agent_name": "test_agent", "repo_root": repo_root, "limit": 5}))
    assert sessions["ok"] is True

    # Bad repo_root
    bad = asyncio.run(tools.tool_start_session({"agent_name": "test_agent", "repo_root": "/nonexistent"}))
    assert bad["ok"] is False
