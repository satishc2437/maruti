import json
import os
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
SRC_DIR = PKG_DIR / "src"

def run_rpc(requests: list[dict], cwd: Path) -> list[dict]:
    """
    Launch agent_memory server and send one or more JSON-RPC requests via stdin.
    Returns parsed JSON responses in the same order.
    Ensures proper cleanup of subprocess and pipes to avoid ResourceWarning.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR)
    proc = subprocess.Popen(
        [sys.executable, "-m", "agent_memory"],
        cwd=str(cwd),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )
    responses: list[dict] = []
    try:
        # Write all requests
        assert proc.stdin is not None
        for req in requests:
            proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        # Signal EOF to server to allow it to exit after processing
        try:
            proc.stdin.close()
        except Exception:
            pass

        # Read exactly len(requests) responses or until EOF
        assert proc.stdout is not None
        for _ in requests:
            out_line = proc.stdout.readline()
            if not out_line:
                break
            responses.append(json.loads(out_line))

        # Drain stderr for diagnostics (not asserted)
        try:
            if proc.stderr is not None:
                _ = proc.stderr.read()
        except Exception:
            pass

        # Wait for graceful exit
        try:
            proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=1.0)
        return responses
    finally:
        # Close remaining pipes explicitly
        for pipe in (proc.stdout, proc.stderr):
            try:
                if pipe:
                    pipe.close()
            except Exception:
                pass


class TestAgentMemoryServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_root = Path("/app/tmp-agent-memory-tests").resolve()
        if cls.tmp_root.exists():
            shutil.rmtree(cls.tmp_root, ignore_errors=True)
        cls.tmp_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        # Clean up after tests
        try:
            shutil.rmtree(cls.tmp_root, ignore_errors=True)
        except Exception:
            pass

    def test_start_session_creates_layout_and_file(self):
        req = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tool_call",
            "params": {
                "name": "start_session",
                "arguments": {
                    "agent_name": "socrates",
                    "repo_root": str(self.tmp_root),
                    "date": "2025-01-01",
                },
            },
        }
        responses = run_rpc([req], PKG_DIR)
        self.assertEqual(len(responses), 1)
        resp = responses[0]
        self.assertEqual(resp["id"], "1")
        self.assertTrue(resp["result"]["ok"])
        session_path = Path(resp["result"]["session_file"])
        self.assertTrue(session_path.exists())
        # Check contract structure
        base = self.tmp_root / ".github" / "agent-memory" / "socrates"
        self.assertTrue((base / "logs").exists())
        self.assertTrue((base / "_summary.md").exists())
        self.assertTrue((base / "_schema.md").exists())

    def test_append_entry_and_list_sessions(self):
        # Ensure session exists (today)
        req1 = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tool_call",
            "params": {
                "name": "start_session",
                "arguments": {
                    "agent_name": "socrates",
                    "repo_root": str(self.tmp_root),
                },
            },
        }
        # Append to Decisions
        req2 = {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "tool_call",
            "params": {
                "name": "append_entry",
                "arguments": {
                    "agent_name": "socrates",
                    "repo_root": str(self.tmp_root),
                    "section": "Decisions",
                    "content": "Adopt deterministic memory control.",
                },
            },
        }
        # List sessions
        req3 = {
            "jsonrpc": "2.0",
            "id": "4",
            "method": "tool_call",
            "params": {
                "name": "list_sessions",
                "arguments": {
                    "agent_name": "socrates",
                    "repo_root": str(self.tmp_root),
                    "limit": 10,
                },
            },
        }
        responses = run_rpc([req1, req2, req3], PKG_DIR)
        self.assertEqual(len(responses), 3)
        self.assertTrue(responses[0]["result"]["ok"])
        self.assertTrue(responses[1]["result"]["ok"])
        self.assertTrue(responses[2]["result"]["ok"])
        sessions = responses[2]["result"]["sessions"]
        self.assertGreaterEqual(len(sessions), 1)
        self.assertTrue(sessions[0].endswith(".md"))

    def test_read_and_update_summary(self):
        agent = "plato"
        # Initialize session
        req1 = {
            "jsonrpc": "2.0",
            "id": "5",
            "method": "tool_call",
            "params": {
                "name": "start_session",
                "arguments": {
                    "agent_name": agent,
                    "repo_root": str(self.tmp_root),
                },
            },
        }
        # Read summary (auto-init)
        req2 = {
            "jsonrpc": "2.0",
            "id": "6",
            "method": "tool_call",
            "params": {
                "name": "read_summary",
                "arguments": {
                    "agent_name": agent,
                    "repo_root": str(self.tmp_root),
                },
            },
        }
        # Append to Decisions in summary
        req3 = {
            "jsonrpc": "2.0",
            "id": "7",
            "method": "tool_call",
            "params": {
                "name": "update_summary",
                "arguments": {
                    "agent_name": agent,
                    "repo_root": str(self.tmp_root),
                    "section": "Decisions",
                    "content": "Use schema v1 for all logs.",
                    "mode": "append",
                },
            },
        }
        # Replace Context section in summary
        req4 = {
            "jsonrpc": "2.0",
            "id": "8",
            "method": "tool_call",
            "params": {
                "name": "update_summary",
                "arguments": {
                    "agent_name": agent,
                    "repo_root": str(self.tmp_root),
                    "section": "Context",
                    "content": "Project=Agent Memory; Focus=Schema; Stage=Validation",
                    "mode": "replace",
                },
            },
        }
        responses = run_rpc([req1, req2, req3, req4], PKG_DIR)
        self.assertEqual(len(responses), 4)
        for i in range(4):
            self.assertEqual(responses[i]["jsonrpc"], "2.0")
            self.assertEqual(responses[i]["id"], str(5 + i))
            self.assertIn("result", responses[i])
            self.assertTrue(responses[i]["result"]["ok"])

        # Validate updated summary content on disk
        base = self.tmp_root / ".github" / "agent-memory" / agent
        summary_path = base / "_summary.md"
        text = summary_path.read_text(encoding="utf-8")
        self.assertIn("Use schema v1 for all logs.", text)
        self.assertIn("Project=Agent Memory; Focus=Schema; Stage=Validation", text)

    def test_invalid_section_error(self):
        agent = "aristotle"
        # Ensure layout exists
        req1 = {
            "jsonrpc": "2.0",
            "id": "9",
            "method": "tool_call",
            "params": {
                "name": "start_session",
                "arguments": {
                    "agent_name": agent,
                    "repo_root": str(self.tmp_root),
                },
            },
        }
        # Attempt to append to invalid section
        req2 = {
            "jsonrpc": "2.0",
            "id": "10",
            "method": "tool_call",
            "params": {
                "name": "append_entry",
                "arguments": {
                    "agent_name": agent,
                    "repo_root": str(self.tmp_root),
                    "section": "Thoughts",
                    "content": "This should be rejected.",
                },
            },
        }
        responses = run_rpc([req1, req2], PKG_DIR)
        self.assertEqual(len(responses), 2)
        self.assertTrue(responses[0]["result"]["ok"])
        # Second should be an error object
        err = responses[1]["result"]
        self.assertFalse(err["ok"])
        self.assertEqual(err["error"], "InvalidSection")
        self.assertIn("not defined", err["message"])


if __name__ == "__main__":
    unittest.main()
