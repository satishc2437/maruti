#!/usr/bin/env python3
"""
Basic functionality test for Agent Memory MCP Server.
Tests core memory operations without requiring MCP framework.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import modules directly to avoid MCP dependency during testing
import agent_memory.memory_ops as memory_ops
import agent_memory.safety as safety


def test_basic_functionality():
    """Test basic memory operations."""
    print("Testing Agent Memory basic functionality...")

    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temp directory: {temp_dir}")

        # Test repository validation
        try:
            repo_path = validate_repository_root(temp_dir)
            print(f"✓ Repository validation passed: {repo_path}")
        except Exception as e:
            print(f"✗ Repository validation failed: {e}")
            return False

        # Test agent name validation
        try:
            agent_name = validate_agent_name("test_agent")
            print(f"✓ Agent name validation passed: {agent_name}")
        except Exception as e:
            print(f"✗ Agent name validation failed: {e}")
            return False

        # Test memory manager initialization
        try:
            manager = MemoryManager(temp_dir, "test_agent")
            print(f"✓ Memory manager initialized")
            print(f"  Memory path: {manager.memory_path}")
            print(f"  Schema file: {manager.schema_path}")
            print(f"  Summary file: {manager.summary_path}")
        except Exception as e:
            print(f"✗ Memory manager initialization failed: {e}")
            return False

        # Test session creation
        try:
            result = manager.start_session()
            print(f"✓ Session started: {result}")
        except Exception as e:
            print(f"✗ Session creation failed: {e}")
            return False

        # Test reading summary
        try:
            result = manager.read_summary()
            print(f"✓ Summary read successfully")
            print(f"  Summary length: {len(result['summary'])} characters")
        except Exception as e:
            print(f"✗ Summary read failed: {e}")
            return False

        # Test appending entry
        try:
            result = manager.append_entry("Context", "This is a test entry")
            print(f"✓ Entry appended: {result}")
        except Exception as e:
            print(f"✗ Entry append failed: {e}")
            return False

        # Test listing sessions
        try:
            result = manager.list_sessions()
            print(f"✓ Sessions listed: {len(result['sessions'])} sessions")
        except Exception as e:
            print(f"✗ Session listing failed: {e}")
            return False

        # Test updating summary
        try:
            result = manager.update_summary("Overview", "Test summary update", "append")
            print(f"✓ Summary updated: {result}")
        except Exception as e:
            print(f"✗ Summary update failed: {e}")
            return False

        # Verify file structure was created
        expected_files = [
            manager.schema_path,
            manager.summary_path,
            manager.logs_path
        ]

        for file_path in expected_files:
            if file_path.exists():
                print(f"✓ File exists: {file_path.name}")
            else:
                print(f"✗ File missing: {file_path.name}")
                return False

        print("\n✓ All basic functionality tests passed!")
        return True

def test_error_conditions():
    """Test error handling."""
    print("\nTesting error conditions...")

    # Test invalid repository
    try:
        validate_repository_root("/nonexistent/path")
        print("✗ Should have failed for nonexistent repository")
        return False
    except Exception as e:
        print(f"✓ Correctly rejected invalid repository: {type(e).__name__}")

    # Test invalid agent name
    try:
        validate_agent_name("invalid/agent")
        print("✗ Should have failed for invalid agent name")
        return False
    except Exception as e:
        print(f"✓ Correctly rejected invalid agent name: {type(e).__name__}")

    # Test invalid agent name (empty)
    try:
        validate_agent_name("")
        print("✗ Should have failed for empty agent name")
        return False
    except Exception as e:
        print(f"✓ Correctly rejected empty agent name: {type(e).__name__}")

    print("✓ Error condition tests passed!")
    return True

if __name__ == "__main__":
    print("Agent Memory MCP Server - Basic Test Suite")
    print("=" * 50)

    success = True
    success &= test_basic_functionality()
    success &= test_error_conditions()

    print("\n" + "=" * 50)
    if success:
        print("🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED!")
        sys.exit(1)
