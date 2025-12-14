#!/usr/bin/env python3
"""
Simple test for Agent Memory core functionality.
Tests individual modules directly to avoid MCP dependency.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import individual modules directly
sys.path.insert(0, str(Path(__file__).parent / "src" / "agent_memory"))
import memory_ops
import safety


def test_safety_functions():
    """Test safety validation functions."""
    print("Testing safety functions...")

    # Test repository validation with temp dir
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            repo_path = safety.validate_repository_root(temp_dir)
            print(f"✓ Repository validation passed: {repo_path}")
        except Exception as e:
            print(f"✗ Repository validation failed: {e}")
            return False

    # Test agent name validation
    try:
        agent_name = safety.validate_agent_name("test_agent")
        print(f"✓ Agent name validation passed: {agent_name}")
    except Exception as e:
        print(f"✗ Agent name validation failed: {e}")
        return False

    # Test invalid agent name
    try:
        safety.validate_agent_name("invalid/agent")
        print("✗ Should have failed for invalid agent name")
        return False
    except ValueError as e:
        print(f"✓ Correctly rejected invalid agent name: {type(e).__name__}")

    return True

def test_memory_manager():
    """Test memory manager functionality."""
    print("\nTesting memory manager...")

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Initialize manager
            manager = memory_ops.MemoryManager(temp_dir, "test_agent")
            print(f"✓ Memory manager initialized")

            # Check if directories were created
            if manager.memory_path.exists():
                print(f"✓ Memory directory created: {manager.memory_path}")
            else:
                print(f"✗ Memory directory not created")
                return False

            # Test schema file creation
            if manager.schema_path.exists():
                print(f"✓ Schema file created: {manager.schema_path}")
                schema_content = manager.schema_path.read_text()
                if "Agent Memory Schema v1" in schema_content:
                    print("✓ Schema contains expected content")
                else:
                    print("✗ Schema content missing")
                    return False
            else:
                print(f"✗ Schema file not created")
                return False

            # Test summary file creation
            if manager.summary_path.exists():
                print(f"✓ Summary file created: {manager.summary_path}")
            else:
                print(f"✗ Summary file not created")
                return False

            # Test session start
            result = manager.start_session()
            print(f"✓ Session started: {result}")

            # Test entry append
            result = manager.append_entry("Context", "Test context entry")
            print(f"✓ Entry appended successfully")

            # Test summary read
            result = manager.read_summary()
            print(f"✓ Summary read: {len(result['summary'])} characters")

            # Test summary update
            result = manager.update_summary("Overview", "Test overview", "append")
            print(f"✓ Summary updated successfully")

            # Test session list
            result = manager.list_sessions()
            print(f"✓ Sessions listed: {len(result['sessions'])} sessions")

            return True

        except Exception as e:
            print(f"✗ Memory manager test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_schema_validation():
    """Test schema validation."""
    print("\nTesting schema validation...")

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            manager = memory_ops.MemoryManager(temp_dir, "test_agent")

            # Test valid section
            allowed_sections = manager._get_allowed_sections()
            print(f"✓ Allowed sections: {allowed_sections}")

            # Test section validation
            if "Context" in allowed_sections:
                print("✓ Context section is allowed")
            else:
                print("✗ Context section should be allowed")
                return False

            # Test invalid section (should fail when appending)
            try:
                manager.append_entry("InvalidSection", "Test content")
                print("✗ Should have failed for invalid section")
                return False
            except Exception as e:
                print(f"✓ Correctly rejected invalid section: {type(e).__name__}")

            return True

        except Exception as e:
            print(f"✗ Schema validation test failed: {e}")
            return False

if __name__ == "__main__":
    print("Agent Memory - Simple Test Suite")
    print("=" * 40)

    success = True
    success &= test_safety_functions()
    success &= test_memory_manager()
    success &= test_schema_validation()

    print("\n" + "=" * 40)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("\nThe agent-memory MCP tool is ready for use!")
        print("To run the full server:")
        print("  uvx python -m agent_memory")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED!")
        sys.exit(1)
