"""Foundational tests: secret detection and redaction."""

from __future__ import annotations

import pytest
from github_app_mcp.errors import SafeError
from github_app_mcp.safety import (enforce_max_bytes, redact_text,
                                   validate_no_secrets)


def test_validate_no_secrets_rejects_token_like_prefix_without_echo() -> None:
    token = "ghp_1234567890abcdef"
    with pytest.raises(SafeError) as exc:
        validate_no_secrets({"owner": "o", "repo": "r", "note": token})

    assert "Credential-like" in exc.value.message
    assert token not in exc.value.message


def test_validate_no_secrets_rejects_credential_field_name() -> None:
    with pytest.raises(SafeError):
        validate_no_secrets({"token": "not-a-token"})


def test_redact_text_masks_token_like_values() -> None:
    assert redact_text("ghp_abcdef") == "<redacted>"
    assert redact_text("hello") == "hello"


def test_enforce_max_bytes_rejects_large_payload() -> None:
    with pytest.raises(SafeError):
        enforce_max_bytes(data=b"x" * 6, max_bytes=5, what="payload")


@pytest.mark.parametrize(
    "payload",
    [
        {"owner": "o", "repo": "r", "title": "t", "body": "ghp_1234567890abcdef"},
        {"owner": "o", "repo": "r", "title": "t", "body": "b", "labels": ["ghp_1234567890abcdef"]},
        {"owner": "o", "repo": "r", "title": "t", "body": "b", "assignees": ["ghp_1234567890abcdef"]},
    ],
)
def test_validate_no_secrets_rejects_tokens_in_issue_inputs_without_echo(payload: dict) -> None:
    token = "ghp_1234567890abcdef"
    with pytest.raises(SafeError) as exc:
        validate_no_secrets(payload)

    assert token not in exc.value.message
