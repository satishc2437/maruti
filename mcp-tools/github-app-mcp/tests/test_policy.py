"""Policy unit tests (US2).

Covers:
- repo allowlist
- operation allowlist
- protected branch patterns and PR-only fail-safe
"""

from __future__ import annotations

from github_app_mcp.policy import Policy


def test_operation_allowlist() -> None:
    policy = Policy(allowed_repos=frozenset(), pr_only=False, protected_branch_patterns=())

    assert policy.check_operation_allowed("get_repository").allowed is True
    assert policy.check_operation_allowed("totally_not_allowed").allowed is False


def test_pr_only_property_reflects_configuration() -> None:
    policy = Policy(allowed_repos=frozenset(), pr_only=True, protected_branch_patterns=())
    assert policy.pr_only is True


def test_repo_allowlist_empty_allows_any_repo() -> None:
    policy = Policy(allowed_repos=frozenset(), pr_only=False, protected_branch_patterns=())

    assert policy.check_repo_allowed("octo/repo").allowed is True
    assert policy.check_repo_allowed("other/repo").allowed is True


def test_repo_allowlist_denies_non_members() -> None:
    policy = Policy(allowed_repos=frozenset({"octo/repo"}), pr_only=False, protected_branch_patterns=())

    assert policy.check_repo_allowed("octo/repo").allowed is True
    assert policy.check_repo_allowed("other/repo").allowed is False


def test_protected_branch_patterns_match() -> None:
    policy = Policy(
        allowed_repos=frozenset(),
        pr_only=False,
        protected_branch_patterns=("main", "release/*"),
    )

    assert policy.is_branch_protected("main") is True
    assert policy.is_branch_protected("release/1.0") is True
    assert policy.is_branch_protected("feature/x") is False


def test_pr_only_fail_safe_treats_branch_as_protected_when_no_patterns() -> None:
    policy = Policy(allowed_repos=frozenset(), pr_only=True, protected_branch_patterns=())

    assert policy.is_branch_protected("main") is True
    assert policy.is_branch_protected("any-branch") is True


def test_no_patterns_and_pr_only_disabled_means_not_protected() -> None:
    policy = Policy(allowed_repos=frozenset(), pr_only=False, protected_branch_patterns=())

    assert policy.is_branch_protected("main") is False
    assert policy.is_branch_protected("any-branch") is False
