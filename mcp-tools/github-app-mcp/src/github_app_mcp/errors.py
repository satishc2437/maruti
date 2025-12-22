"""Safe error types and serialization helpers.

Errors returned to agents must be non-secret and stable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SafeError(Exception):
    """An error safe to expose to agents.

    This must never include secrets (tokens, private key content, key path, installation IDs).
    """

    code: str
    message: str
    hint: str | None = None
    status_code: int | None = None


def github_auth_forbidden(*, status_code: int) -> SafeError:
    """Return a safe Forbidden error for GitHub auth/revocation failures.

    Used when GitHub returns 401/403 (installation revoked/uninstalled, or missing permissions).
    """
    return SafeError(
        code="Forbidden",
        message="GitHub App is not authorized for this repository or operation",
        hint="The GitHub App may be uninstalled, revoked, or missing required permissions",
        status_code=status_code,
    )


def safe_error_to_result(err: SafeError) -> dict[str, Any]:
    """Convert a SafeError into the standard tool envelope."""
    return to_error_result(code=err.code, message=err.message, hint=err.hint)


def to_error_result(*, code: str, message: str, hint: str | None = None) -> dict[str, Any]:
    """Build a standard tool error envelope."""
    out: dict[str, Any] = {"ok": False, "code": code, "message": message}
    if hint:
        out["hint"] = hint
    return out


def user_input_error(message: str, hint: str | None = None) -> dict[str, Any]:
    """Error for invalid tool arguments or unsupported operations."""
    return to_error_result(code="UserInput", message=message, hint=hint)


def forbidden_error(message: str, hint: str | None = None) -> dict[str, Any]:
    """Error for policy- or authorization-denied actions."""
    return to_error_result(code="Forbidden", message=message, hint=hint)


def internal_error(message: str = "Internal error") -> dict[str, Any]:
    """Error for unexpected failures."""
    return to_error_result(code="Internal", message=message)
