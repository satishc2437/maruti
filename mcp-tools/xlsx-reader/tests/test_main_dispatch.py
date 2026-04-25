"""Tests for xlsx_reader.__main__ CLI dispatch.

Covers setup_logging, the main() dispatch path with default flags and
--debug, KeyboardInterrupt handling, and the sys.exit(1) on
unexpected exception.
"""

import logging
import sys
from unittest.mock import patch

import pytest

from xlsx_reader.__main__ import main, setup_logging


def test_setup_logging_default_passes_info_level_to_basic_config():
    """setup_logging() with debug=False forwards INFO to logging.basicConfig."""
    with patch("xlsx_reader.__main__.logging.basicConfig") as mock_cfg:
        setup_logging(debug=False)
    mock_cfg.assert_called_once()
    assert mock_cfg.call_args.kwargs["level"] == logging.INFO


def test_setup_logging_debug_passes_debug_level_to_basic_config():
    """setup_logging(debug=True) forwards DEBUG to logging.basicConfig."""
    with patch("xlsx_reader.__main__.logging.basicConfig") as mock_cfg:
        setup_logging(debug=True)
    mock_cfg.assert_called_once()
    assert mock_cfg.call_args.kwargs["level"] == logging.DEBUG


def test_main_default_dispatches_to_run_and_logs_at_info():
    """main() with no flags awaits run() and uses INFO logging."""
    with patch("xlsx_reader.__main__.asyncio.run") as mock_run, \
         patch.object(sys, "argv", ["xlsx_reader"]):
        main()
    mock_run.assert_called_once()
    coro = mock_run.call_args[0][0]
    assert coro.__qualname__ == "run"
    coro.close()


def test_main_with_debug_flag_enables_debug_logging_before_dispatch():
    """main() with --debug calls setup_logging(debug=True) before dispatch."""
    with patch("xlsx_reader.__main__.asyncio.run") as mock_run, \
         patch("xlsx_reader.__main__.setup_logging") as mock_setup, \
         patch.object(sys, "argv", ["xlsx_reader", "--debug"]):
        main()
    mock_setup.assert_called_once_with(True)
    mock_run.assert_called_once()
    coro = mock_run.call_args[0][0]
    coro.close()


def test_main_handles_keyboard_interrupt_without_raising():
    """KeyboardInterrupt during asyncio.run is logged and swallowed."""
    with patch(
        "xlsx_reader.__main__.asyncio.run", side_effect=KeyboardInterrupt(),
    ), patch.object(sys, "argv", ["xlsx_reader"]):
        main()  # must not raise


def test_main_unexpected_exception_exits_with_code_one():
    """Any other exception is logged and triggers sys.exit(1)."""
    with patch(
        "xlsx_reader.__main__.asyncio.run", side_effect=RuntimeError("boom"),
    ), patch.object(sys, "argv", ["xlsx_reader"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1
