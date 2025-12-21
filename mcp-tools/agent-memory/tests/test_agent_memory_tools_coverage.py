import asyncio
import importlib
import sys
import types

import pytest

import agent_memory
from agent_memory import tools
from agent_memory.safety import InvalidRepositoryError, MemorySafetyError, PathTraversalError


def test_init_try_import_branch(monkeypatch):
    # Force the try-import branch in agent_memory.__init__ by injecting a fake server.
    fake_server = types.ModuleType("agent_memory.server")
    fake_server.run_server = lambda: None
    fake_server.test_server = lambda: None

    monkeypatch.setitem(sys.modules, "agent_memory.server", fake_server)
    reloaded = importlib.reload(agent_memory)
    assert reloaded.__all__ == ["run_server", "test_server"]

    # Restore prior behavior for the rest of the test session.
    monkeypatch.delitem(sys.modules, "agent_memory.server", raising=False)
    importlib.reload(agent_memory)


def test_validate_param_helpers_error_branches(tmp_path):
    root = str(tmp_path)

    with pytest.raises(ValueError):
        tools.validate_start_session_params({"repo_root": root})

    with pytest.raises(ValueError):
        tools.validate_start_session_params({"agent_name": 123, "repo_root": root})

    with pytest.raises(ValueError):
        tools.validate_start_session_params({"agent_name": "a", "repo_root": root, "date": 123})

    with pytest.raises(ValueError):
        tools.validate_append_entry_params({"agent_name": "a", "repo_root": root, "section": "Context"})

    with pytest.raises(ValueError):
        tools.validate_append_entry_params({"agent_name": "a", "repo_root": root, "section": 123, "content": "x"})

    with pytest.raises(ValueError):
        tools.validate_basic_params({"agent_name": "a"})

    with pytest.raises(ValueError):
        tools.validate_update_summary_params({"agent_name": "a", "repo_root": root, "section": "s", "content": "x", "mode": "nope"})

    with pytest.raises(ValueError):
        tools.validate_list_sessions_params({"agent_name": "a", "repo_root": root, "limit": 0})

    with pytest.raises(ValueError):
        tools.validate_list_sessions_params({"agent_name": "a", "repo_root": root, "limit": 101})

    with pytest.raises(ValueError):
        tools.validate_list_sessions_params({"agent_name": "a", "repo_root": root, "limit": "x"})


def test_tool_start_session_validation_error():
    r = asyncio.run(tools.tool_start_session({"agent_name": 123, "repo_root": "/"}))
    assert r["ok"] is False
    assert r["code"] == "UserInput"


def test_tool_wrappers_return_passthrough_errors(monkeypatch):
    # If the underlying operation returns a structured error dict, tools pass it through.
    async def fake_timeout(*args, **kwargs):
        return {"ok": False, "code": "Timeout", "message": "x", "correlation_id": "c"}

    monkeypatch.setattr(tools, "run_with_timeout", fake_timeout)

    r = asyncio.run(tools.tool_start_session({"agent_name": "a", "repo_root": "/tmp"}))
    assert r["ok"] is False
    assert r["code"] == "Timeout"

    r = asyncio.run(tools.tool_append_entry({"agent_name": "a", "repo_root": "/tmp", "section": "Context", "content": "x"}))
    assert r["ok"] is False

    r = asyncio.run(tools.tool_read_summary({"agent_name": "a", "repo_root": "/tmp"}))
    assert r["ok"] is False

    r = asyncio.run(tools.tool_update_summary({"agent_name": "a", "repo_root": "/tmp", "section": "s", "content": "x", "mode": "append"}))
    assert r["ok"] is False

    r = asyncio.run(tools.tool_list_sessions({"agent_name": "a", "repo_root": "/tmp"}))
    assert r["ok"] is False


def test_tool_error_classification(monkeypatch, tmp_path):
    repo_root = str(tmp_path)

    class TraversalManager:
        def __init__(self, *args, **kwargs):
            raise PathTraversalError("escape")

    monkeypatch.setattr(tools, "MemoryManager", TraversalManager)
    r = asyncio.run(tools.tool_read_summary({"agent_name": "a", "repo_root": repo_root}))
    assert r["code"] == "Forbidden"

    class BadRepoManager:
        def __init__(self, *args, **kwargs):
            raise InvalidRepositoryError("bad")

    monkeypatch.setattr(tools, "MemoryManager", BadRepoManager)
    r = asyncio.run(tools.tool_read_summary({"agent_name": "a", "repo_root": repo_root}))
    assert r["code"] == "UserInput"

    class GenericSafetyManager:
        def __init__(self, *args, **kwargs):
            raise MemorySafetyError("nope")

    monkeypatch.setattr(tools, "MemoryManager", GenericSafetyManager)
    r = asyncio.run(tools.tool_list_sessions({"agent_name": "a", "repo_root": repo_root}))
    assert r["code"] == "Forbidden"


def test_tool_exception_falls_back_to_internal(monkeypatch, tmp_path):
    repo_root = str(tmp_path)

    class Manager:
        def __init__(self, *args, **kwargs):
            pass

        def start_session(self, *args, **kwargs):
            raise RuntimeError("boom")

    async def run_direct(coro, timeout_seconds=10.0):
        return await coro

    monkeypatch.setattr(tools, "MemoryManager", Manager)
    monkeypatch.setattr(tools, "run_with_timeout", run_direct)

    r = asyncio.run(tools.tool_start_session({"agent_name": "a", "repo_root": repo_root}))
    assert r["ok"] is False
    assert r["code"] == "Internal"


def test_tool_append_entry_value_error_and_file_not_found(monkeypatch, tmp_path):
    repo_root = str(tmp_path)

    class Manager:
        def __init__(self, *args, **kwargs):
            pass

        def append_entry(self, *args, **kwargs):
            raise ValueError("bad")

    async def run_direct(coro, timeout_seconds=10.0):
        return await coro

    monkeypatch.setattr(tools, "MemoryManager", Manager)
    monkeypatch.setattr(tools, "run_with_timeout", run_direct)
    r = asyncio.run(
        tools.tool_append_entry({"agent_name": "a", "repo_root": repo_root, "section": "Context", "content": "x"})
    )
    assert r["ok"] is False
    assert r["code"] == "UserInput"

    class Missing:
        def __init__(self, *args, **kwargs):
            raise FileNotFoundError("missing")

    monkeypatch.setattr(tools, "MemoryManager", Missing)
    r = asyncio.run(
        tools.tool_append_entry({"agent_name": "a", "repo_root": repo_root, "section": "Context", "content": "x"})
    )
    assert r["ok"] is False
    assert r["code"] == "NotFound"


def test_tool_update_summary_value_error(monkeypatch, tmp_path):
    repo_root = str(tmp_path)

    class Manager:
        def __init__(self, *args, **kwargs):
            pass

        def update_summary(self, *args, **kwargs):
            raise ValueError("bad")

    async def run_direct(coro, timeout_seconds=10.0):
        return await coro

    monkeypatch.setattr(tools, "MemoryManager", Manager)
    monkeypatch.setattr(tools, "run_with_timeout", run_direct)
    r = asyncio.run(
        tools.tool_update_summary(
            {"agent_name": "a", "repo_root": repo_root, "section": "s", "content": "x", "mode": "append"}
        )
    )
    assert r["ok"] is False
    assert r["code"] == "UserInput"


def test_tool_read_and_list_file_not_found_and_internal(monkeypatch, tmp_path):
    repo_root = str(tmp_path)

    class Manager:
        def __init__(self, *args, **kwargs):
            pass

        def read_summary(self):
            raise FileNotFoundError("missing")

        def list_sessions(self, *args, **kwargs):
            raise RuntimeError("boom")

    async def run_direct(coro, timeout_seconds=10.0):
        return await coro

    monkeypatch.setattr(tools, "MemoryManager", Manager)
    monkeypatch.setattr(tools, "run_with_timeout", run_direct)

    r = asyncio.run(tools.tool_read_summary({"agent_name": "a", "repo_root": repo_root}))
    assert r["ok"] is False
    assert r["code"] == "NotFound"

    r = asyncio.run(tools.tool_list_sessions({"agent_name": "a", "repo_root": repo_root}))
    assert r["ok"] is False
    assert r["code"] == "Internal"
