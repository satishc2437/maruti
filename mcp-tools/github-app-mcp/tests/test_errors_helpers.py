"""Errors helper coverage."""

from __future__ import annotations

from github_app_mcp.errors import (forbidden_error, internal_error,
                                   user_input_error)


def test_user_input_error_shape() -> None:
    out = user_input_error("bad")
    assert out == {"ok": False, "code": "UserInput", "message": "bad"}


def test_forbidden_error_shape() -> None:
    out = forbidden_error("no", hint="h")
    assert out == {"ok": False, "code": "Forbidden", "message": "no", "hint": "h"}


def test_internal_error_shape() -> None:
    out = internal_error()
    assert out["ok"] is False
    assert out["code"] == "Internal"
