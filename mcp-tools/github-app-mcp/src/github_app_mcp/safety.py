"""Safety helpers.

Implements deterministic secret detection/redaction rules and size limit helpers.

Key rule: if an agent-provided input appears to be a credential, reject the request
and do not echo the suspected secret value.
"""

from __future__ import annotations

import re
from typing import Any

from .errors import SafeError

_CRED_FIELD_NAMES = {
    "token",
    "access_token",
    "authorization",
    "password",
    "private_key",
    "pem",
    "jwt",
}

_TOKEN_PREFIXES = (
    "ghp_",
    "gho_",
    "ghu_",
    "ghs_",
    "github_pat_",
)

_JWT_LIKE_RE = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")


def looks_like_secret_value(value: str) -> bool:
    """Return True if the value looks like a credential.

    Matching rules (minimum):
    - prefix-at-start after trimming leading whitespace
    - bearer prefix treated case-insensitively
    - JWT-looking value treated as secret-like (conservative)
    """
    if not isinstance(value, str):
        return False
    trimmed = value.lstrip()
    lowered = trimmed.lower()
    if lowered.startswith("bearer "):
        return True
    if lowered.startswith(tuple(p.lower() for p in _TOKEN_PREFIXES)):
        return True
    # Conservative JWT-like detection to prevent accidental echo/exfil.
    if len(trimmed) >= 40 and _JWT_LIKE_RE.match(trimmed):
        return True
    return False


def looks_like_credential_field_name(field_name: str) -> bool:
    """Return True if a key name looks like a credential field."""
    if not isinstance(field_name, str):
        return False
    return field_name.strip().lower() in _CRED_FIELD_NAMES


def validate_no_secrets(obj: Any) -> None:
    """Reject any agent-provided input that appears to contain credentials.

    Raises SafeError without echoing any suspected secret values.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if looks_like_credential_field_name(str(k)):
                raise SafeError(code="UserInput", message="Credential-like fields are not allowed")
            validate_no_secrets(v)
        return
    if isinstance(obj, list):
        for item in obj:
            validate_no_secrets(item)
        return
    if isinstance(obj, str):
        if looks_like_secret_value(obj):
            raise SafeError(code="UserInput", message="Credential-like values are not allowed")
        return


def enforce_max_bytes(*, data: bytes, max_bytes: int, what: str) -> None:
    """Enforce an upper bound on byte payloads."""
    if len(data) > max_bytes:
        raise SafeError(code="UserInput", message=f"{what} exceeds size limit")


def redact_text(text: str) -> str:
    """Return a redacted representation safe for logs."""
    if not isinstance(text, str):
        return "<non-string>"
    if looks_like_secret_value(text):
        return "<redacted>"
    return text
