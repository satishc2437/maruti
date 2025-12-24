"""Safety helpers coverage."""

from __future__ import annotations

import pytest
from github_app_mcp.errors import SafeError
from github_app_mcp.safety import (enforce_max_bytes,
                                   looks_like_credential_field_name,
                                   looks_like_secret_value, redact_text,
                                   validate_no_secrets)


def test_looks_like_secret_value_detects_bearer_prefix() -> None:
    assert looks_like_secret_value("Bearer abc") is True


def test_looks_like_secret_value_detects_jwt_like_string() -> None:
    jwtish = "a" * 14 + "." + "b" * 14 + "." + "c" * 14
    assert looks_like_secret_value(jwtish) is True


def test_looks_like_secret_value_detects_known_token_prefix() -> None:
    assert looks_like_secret_value("gho_abcdef") is True


def test_looks_like_secret_value_false_for_normal_string() -> None:
    assert looks_like_secret_value("hello") is False


def test_looks_like_secret_value_false_for_non_string() -> None:
    assert looks_like_secret_value(123) is False  # type: ignore[arg-type]


def test_looks_like_credential_field_name_handles_non_string() -> None:
    assert looks_like_credential_field_name(123) is False  # type: ignore[arg-type]


def test_redact_text_non_string() -> None:
    assert redact_text(123) == "<non-string>"  # type: ignore[arg-type]


def test_redact_text_redacts_secret_like() -> None:
    assert redact_text("ghp_123456") == "<redacted>"


def test_validate_no_secrets_rejects_credential_field_name() -> None:
    with pytest.raises(SafeError):
        validate_no_secrets({"token": "not-a-token"})


def test_enforce_max_bytes_raises() -> None:
    with pytest.raises(SafeError):
        enforce_max_bytes(data=b"0123456789", max_bytes=3, what="file")
