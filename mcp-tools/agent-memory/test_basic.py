#!/usr/bin/env python3
"""Basic functionality test for Agent Memory MCP Server.

Tests core memory operations without requiring MCP framework.
"""

import tempfile

import pytest

from agent_memory import memory_ops, safety


def test_basic_functionality():
    """Test basic memory operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = safety.validate_repository_root(temp_dir)
        assert repo_path is not None

        assert safety.validate_agent_name("test_agent") == "test_agent"

        manager = memory_ops.MemoryManager(temp_dir, "test_agent")
        assert manager.memory_path.exists()

        result = manager.start_session()
        assert isinstance(result, dict)

        result = manager.read_summary()
        assert isinstance(result, dict)
        assert "summary" in result

        result = manager.append_entry("Context", "This is a test entry")
        assert isinstance(result, dict)

        result = manager.list_sessions()
        assert isinstance(result, dict)
        assert "sessions" in result

        result = manager.update_summary("Overview", "Test summary update", "append")
        assert isinstance(result, dict)

        # Verify file structure was created
        expected_files = [
            manager.schema_path,
            manager.summary_path,
            manager.logs_path
        ]

        for file_path in expected_files:
            assert file_path.exists(), f"Expected file to exist: {file_path.name}"

def test_error_conditions():
    """Test error handling."""
    with pytest.raises(Exception):
        safety.validate_repository_root("/nonexistent/path")

    with pytest.raises(ValueError):
        safety.validate_agent_name("invalid/agent")

    with pytest.raises(ValueError):
        safety.validate_agent_name("")

if __name__ == "__main__":
    print("Agent Memory MCP Server - Basic Test Suite")
    print("=" * 50)

    try:
        test_basic_functionality()
        test_error_conditions()
    except Exception:
        print("❌ SOME TESTS FAILED!")
        raise
    else:
        print("🎉 ALL TESTS PASSED!")
