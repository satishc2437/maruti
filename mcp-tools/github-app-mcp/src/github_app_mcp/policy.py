"""Policy evaluation.

This module enforces:
- repository allowlist
- operation allowlist
- PR-only workflow intent (guidance/denials are implemented at tool layer)
- protected branch rules
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass

ALLOW_LISTED_OPERATIONS: frozenset[str] = frozenset(
    {
        "get_repository",
        "list_branches",
        "get_file",
        "list_pull_requests",
        "list_issues",
        "create_branch",
        "commit_changes",
        "open_pull_request",
        "comment_on_issue",
    }
)


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """Policy decision result."""

    allowed: bool
    reason: str | None = None


class Policy:
    """Policy engine."""

    def __init__(
        self,
        *,
        allowed_repos: frozenset[str],
        pr_only: bool,
        protected_branch_patterns: tuple[str, ...],
    ) -> None:
        """Create a policy evaluator."""
        self._allowed_repos = allowed_repos
        self._pr_only = pr_only
        self._protected_patterns = protected_branch_patterns

    @property
    def pr_only(self) -> bool:
        """Return whether PR-only workflow is enabled."""
        return self._pr_only

    def check_operation_allowed(self, operation: str) -> PolicyDecision:
        """Return whether the operation name is allow-listed."""
        if operation not in ALLOW_LISTED_OPERATIONS:
            return PolicyDecision(False, "Operation is not allow-listed")
        return PolicyDecision(True)

    def check_repo_allowed(self, target_repo: str) -> PolicyDecision:
        """Return whether the target repo is allowed by the configured allowlist."""
        if not self._allowed_repos:
            return PolicyDecision(True)
        if target_repo in self._allowed_repos:
            return PolicyDecision(True)
        return PolicyDecision(False, "Repository is not in allowlist")

    def is_branch_protected(self, branch: str) -> bool:
        """Return True if the branch should be treated as protected."""
        if self._protected_patterns:
            return any(fnmatch.fnmatch(branch, pat) for pat in self._protected_patterns)
        # Fail-safe behavior: if PR-only is enabled and protection status is unknown,
        # treat target as protected.
        return self._pr_only
