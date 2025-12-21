import asyncio

import pytest

from agent_memory import tools
from agent_memory.safety import InvalidRepositoryError, MemorySafetyError, PathTraversalError


def test_validation_helpers_specific_missing_fields(tmp_path):
    root = str(tmp_path)

    with pytest.raises(ValueError):
        tools.validate_start_session_params({"agent_name": "a"})

    with pytest.raises(ValueError):
        tools.validate_append_entry_params({"agent_name": "a", "repo_root": root, "section": "Context", "content": "x", "date": 123})

    with pytest.raises(ValueError):
        tools.validate_basic_params({"repo_root": root})

    with pytest.raises(ValueError):
        tools.validate_update_summary_params({"agent_name": "a", "repo_root": root, "content": "x", "mode": "append"})

    with pytest.raises(ValueError):
        tools.validate_update_summary_params({"agent_name": "a", "repo_root": root, "section": "s", "mode": "append"})


def test_tool_start_session_file_not_found_and_generic_safety(monkeypatch, tmp_path):
    repo_root = str(tmp_path)

    class Missing:
        def __init__(self, *args, **kwargs):
            raise FileNotFoundError("missing")

    monkeypatch.setattr(tools, "MemoryManager", Missing)
    r = asyncio.run(tools.tool_start_session({"agent_name": "a", "repo_root": repo_root}))
    assert r["code"] == "NotFound"

    class GenericSafety:
        def __init__(self, *args, **kwargs):
            raise MemorySafetyError("nope")

    monkeypatch.setattr(tools, "MemoryManager", GenericSafety)
    r = asyncio.run(tools.tool_start_session({"agent_name": "a", "repo_root": repo_root}))
    assert r["code"] == "Forbidden"


def test_tool_append_entry_all_exception_branches(monkeypatch, tmp_path):
    repo_root = str(tmp_path)

    class Traversal:
        def __init__(self, *args, **kwargs):
            raise PathTraversalError("escape")

    monkeypatch.setattr(tools, "MemoryManager", Traversal)
    r = asyncio.run(tools.tool_append_entry({"agent_name": "a", "repo_root": repo_root, "section": "Context", "content": "x"}))
    assert r["code"] == "Forbidden"

    class BadRepo:
        def __init__(self, *args, **kwargs):
            raise InvalidRepositoryError("bad")

    monkeypatch.setattr(tools, "MemoryManager", BadRepo)
    r = asyncio.run(tools.tool_append_entry({"agent_name": "a", "repo_root": repo_root, "section": "Context", "content": "x"}))
    assert r["code"] == "UserInput"

    class GenericSafety:
        def __init__(self, *args, **kwargs):
            raise MemorySafetyError("nope")

    monkeypatch.setattr(tools, "MemoryManager", GenericSafety)
    r = asyncio.run(tools.tool_append_entry({"agent_name": "a", "repo_root": repo_root, "section": "Context", "content": "x"}))
    assert r["code"] == "Forbidden"

    class Explode:
        def __init__(self, *args, **kwargs):
            pass

        def append_entry(self, *args, **kwargs):
            raise RuntimeError("boom")

    async def run_direct(coro_or_factory, timeout_seconds=10.0):
        coro = coro_or_factory() if callable(coro_or_factory) else coro_or_factory
        return await coro

    monkeypatch.setattr(tools, "MemoryManager", Explode)
    monkeypatch.setattr(tools, "run_with_timeout", run_direct)
    r = asyncio.run(tools.tool_append_entry({"agent_name": "a", "repo_root": repo_root, "section": "Context", "content": "x"}))
    assert r["code"] == "Internal"


def test_tool_read_summary_validation_and_generic_errors(monkeypatch, tmp_path):
    repo_root = str(tmp_path)

    r = asyncio.run(tools.tool_read_summary({"repo_root": repo_root}))
    assert r["code"] == "UserInput"

    class GenericSafety:
        def __init__(self, *args, **kwargs):
            raise MemorySafetyError("nope")

    monkeypatch.setattr(tools, "MemoryManager", GenericSafety)
    r = asyncio.run(tools.tool_read_summary({"agent_name": "a", "repo_root": repo_root}))
    assert r["code"] == "Forbidden"

    class Explode:
        def __init__(self, *args, **kwargs):
            pass

        def read_summary(self):
            raise RuntimeError("boom")

    async def run_direct(coro_or_factory, timeout_seconds=10.0):
        coro = coro_or_factory() if callable(coro_or_factory) else coro_or_factory
        return await coro

    monkeypatch.setattr(tools, "MemoryManager", Explode)
    monkeypatch.setattr(tools, "run_with_timeout", run_direct)
    r = asyncio.run(tools.tool_read_summary({"agent_name": "a", "repo_root": repo_root}))
    assert r["code"] == "Internal"


def test_tool_update_summary_validation_and_error_branches(monkeypatch, tmp_path):
    repo_root = str(tmp_path)

    r = asyncio.run(tools.tool_update_summary({"agent_name": "a", "repo_root": repo_root}))
    assert r["code"] == "UserInput"

    class Traversal:
        def __init__(self, *args, **kwargs):
            raise PathTraversalError("escape")

    monkeypatch.setattr(tools, "MemoryManager", Traversal)
    r = asyncio.run(tools.tool_update_summary({"agent_name": "a", "repo_root": repo_root, "section": "s", "content": "x", "mode": "append"}))
    assert r["code"] == "Forbidden"

    class BadRepo:
        def __init__(self, *args, **kwargs):
            raise InvalidRepositoryError("bad")

    monkeypatch.setattr(tools, "MemoryManager", BadRepo)
    r = asyncio.run(tools.tool_update_summary({"agent_name": "a", "repo_root": repo_root, "section": "s", "content": "x", "mode": "append"}))
    assert r["code"] == "UserInput"

    class Explode:
        def __init__(self, *args, **kwargs):
            pass

        def update_summary(self, *args, **kwargs):
            raise FileNotFoundError("missing")

    async def run_direct(coro_or_factory, timeout_seconds=10.0):
        coro = coro_or_factory() if callable(coro_or_factory) else coro_or_factory
        return await coro

    monkeypatch.setattr(tools, "MemoryManager", Explode)
    monkeypatch.setattr(tools, "run_with_timeout", run_direct)
    r = asyncio.run(tools.tool_update_summary({"agent_name": "a", "repo_root": repo_root, "section": "s", "content": "x", "mode": "append"}))
    assert r["code"] == "NotFound"


def test_tool_list_sessions_validation_and_file_not_found(monkeypatch, tmp_path):
    repo_root = str(tmp_path)

    r = asyncio.run(tools.tool_list_sessions({"agent_name": "a", "repo_root": repo_root, "limit": 0}))
    assert r["code"] == "UserInput"

    class Traversal:
        def __init__(self, *args, **kwargs):
            raise PathTraversalError("escape")

    monkeypatch.setattr(tools, "MemoryManager", Traversal)
    r = asyncio.run(tools.tool_list_sessions({"agent_name": "a", "repo_root": repo_root}))
    assert r["code"] == "Forbidden"

    class BadRepo:
        def __init__(self, *args, **kwargs):
            raise InvalidRepositoryError("bad")

    monkeypatch.setattr(tools, "MemoryManager", BadRepo)
    r = asyncio.run(tools.tool_list_sessions({"agent_name": "a", "repo_root": repo_root}))
    assert r["code"] == "UserInput"

    class Missing:
        def __init__(self, *args, **kwargs):
            pass

        def list_sessions(self, *args, **kwargs):
            raise FileNotFoundError("missing")

    async def run_direct(coro_or_factory, timeout_seconds=10.0):
        coro = coro_or_factory() if callable(coro_or_factory) else coro_or_factory
        return await coro

    monkeypatch.setattr(tools, "MemoryManager", Missing)
    monkeypatch.setattr(tools, "run_with_timeout", run_direct)
    r = asyncio.run(tools.tool_list_sessions({"agent_name": "a", "repo_root": repo_root}))
    assert r["code"] == "NotFound"
