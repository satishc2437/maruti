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

        # US1: GitHub Project task queue (MVP)
        "get_project_v2_by_number",
        "add_issue_to_project_v2",
        "create_issue",

        # US2: Work tasks from the project
        "list_project_v2_fields",
        "list_project_v2_items",
        "get_project_v2_item",
        "set_project_v2_item_field_value",
        "get_issue",
        "update_issue",
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
        allowed_projects: frozenset[str],
        pr_only: bool,
        protected_branch_patterns: tuple[str, ...],
    ) -> None:
        """Create a policy evaluator."""
        self._allowed_repos = allowed_repos
        self._allowed_projects = allowed_projects
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

    def check_project_allowed(self, *, owner_login: str, project_number: int) -> PolicyDecision:
        """Return whether the target project is allowed by the configured allowlist.

        Projects are org/user scoped and must be explicitly allowlisted. If the allowlist
        is not configured, project access is denied (fail-closed).
        """
        if not self._allowed_projects:
            return PolicyDecision(False, "Project allowlist is not configured")

        key = f"{owner_login.strip().lower()}/{project_number}"
        if key in self._allowed_projects:
            return PolicyDecision(True)
        return PolicyDecision(False, "Project is not in allowlist")

    def is_branch_protected(self, branch: str) -> bool:
        """Return True if the branch should be treated as protected."""
        if self._protected_patterns:
            return any(fnmatch.fnmatch(branch, pat) for pat in self._protected_patterns)
        # Fail-safe behavior: if PR-only is enabled and protection status is unknown,
        # treat target as protected.
        return self._pr_only
