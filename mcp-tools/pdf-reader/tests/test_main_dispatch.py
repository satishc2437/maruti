"""Tests for pdf_reader.__main__ CLI dispatch.

Covers argument parsing, the run_server vs test_server dispatch branches,
KeyboardInterrupt handling, and the unexpected-exception exit path.
"""

import sys
from unittest.mock import patch

import pytest

from pdf_reader.__main__ import main, parse_args


def test_parse_args_default_does_not_set_test_flag():
    """No --test flag results in args.test == False."""
    args = parse_args([])
    assert args.test is False


def test_parse_args_with_test_flag_sets_test_true():
    """--test flag sets args.test == True."""
    args = parse_args(["--test"])
    assert args.test is True


def test_main_default_dispatches_to_run_server():
    """main() with no flags awaits run_server() once."""
    with patch("pdf_reader.__main__.asyncio.run") as mock_run, \
         patch.object(sys, "argv", ["pdf_reader"]):
        main()
    mock_run.assert_called_once()
    coro = mock_run.call_args[0][0]
    assert coro.__qualname__ == "run_server"
    coro.close()


def test_main_with_test_flag_dispatches_to_self_test():
    """main() with --test awaits the self-test coroutine instead of run_server."""
    with patch("pdf_reader.__main__.asyncio.run") as mock_run, \
         patch.object(sys, "argv", ["pdf_reader", "--test"]):
        main()
    mock_run.assert_called_once()
    coro = mock_run.call_args[0][0]
    assert coro.__qualname__ == "test_server"
    coro.close()


def test_main_handles_keyboard_interrupt_without_raising(capsys):
    """KeyboardInterrupt during asyncio.run produces a stderr message, no exit."""
    with patch(
        "pdf_reader.__main__.asyncio.run", side_effect=KeyboardInterrupt(),
    ), patch.object(sys, "argv", ["pdf_reader"]):
        main()  # must not raise
    captured = capsys.readouterr()
    assert "stopped by user" in captured.err


def test_main_unexpected_exception_exits_with_code_one(capsys):
    """Any other exception is reported to stderr and triggers sys.exit(1)."""
    with patch(
        "pdf_reader.__main__.asyncio.run", side_effect=RuntimeError("boom"),
    ), patch.object(sys, "argv", ["pdf_reader"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "boom" in captured.err
