#!/usr/bin/env python3
"""Simple test for Agent Memory core functionality.

Tests individual modules directly to avoid MCP dependency.
"""

import tempfile

import pytest

from agent_memory import memory_ops, safety


def test_safety_functions():
    """Test safety validation functions."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = safety.validate_repository_root(temp_dir)
        assert repo_path is not None

    assert safety.validate_agent_name("test_agent") == "test_agent"
    with pytest.raises(ValueError):
        safety.validate_agent_name("invalid/agent")

def test_memory_manager():
    """Test memory manager functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = memory_ops.MemoryManager(temp_dir, "test_agent")
        assert manager.memory_path.exists(), "Expected memory directory to be created"

        assert manager.schema_path.exists(), "Expected schema file to be created"
        schema_content = manager.schema_path.read_text(encoding="utf-8")
        assert "Agent Memory Schema v1" in schema_content

        assert manager.summary_path.exists(), "Expected summary file to be created"

        result = manager.start_session()
        assert isinstance(result, dict)

        result = manager.append_entry("Context", "Test context entry")
        assert isinstance(result, dict)

        result = manager.read_summary()
        assert isinstance(result, dict)
        assert "summary" in result

        result = manager.update_summary("Overview", "Test overview", "append")
        assert isinstance(result, dict)

        result = manager.list_sessions()
        assert isinstance(result, dict)
        assert "sessions" in result

def test_schema_validation():
    """Test schema validation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = memory_ops.MemoryManager(temp_dir, "test_agent")

        # Valid sections should be accepted.
        result = manager.append_entry("Context", "Test content")
        assert result["ok"] is True

        with pytest.raises(ValueError):
            manager.append_entry("InvalidSection", "Test content")

if __name__ == "__main__":
    print("Agent Memory - Simple Test Suite")
    print("=" * 40)
    try:
        test_safety_functions()
        test_memory_manager()
        test_schema_validation()
    except Exception:  # pylint: disable=broad-except
        print("❌ SOME TESTS FAILED!")
        raise
    else:
        print("🎉 ALL TESTS PASSED!")
