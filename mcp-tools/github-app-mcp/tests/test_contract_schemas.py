"""Contract/schema validation tests.

These tests ensure tool inputs are strictly validated and that secret-like inputs are rejected
without echoing sensitive values.
"""

from __future__ import annotations

import pytest
from github_app_mcp.errors import SafeError
from github_app_mcp.tools import TOOL_METADATA, validate_tool_arguments


@pytest.mark.parametrize(
    "tool_name,base_args",
    [
        ("get_repository", {"owner": "octo", "repo": "repo"}),
        ("list_branches", {"owner": "octo", "repo": "repo"}),
        ("get_file", {"owner": "octo", "repo": "repo", "path": "README.md"}),
        ("list_pull_requests", {"owner": "octo", "repo": "repo"}),
        ("list_issues", {"owner": "octo", "repo": "repo"}),
    ],
)
def test_read_tools_reject_extra_fields(tool_name: str, base_args: dict) -> None:
    args = dict(base_args)
    args["extra"] = "nope"

    with pytest.raises(SafeError) as exc:
        validate_tool_arguments(tool_name, args)

    assert "Unexpected fields" in exc.value.message


@pytest.mark.parametrize(
    "tool_name,base_args",
    [
        ("create_branch", {"owner": "octo", "repo": "repo", "base": "main", "branch": "feat"}),
        (
            "commit_changes",
            {
                "owner": "octo",
                "repo": "repo",
                "branch": "feat",
                "message": "msg",
                "changes": [{"path": "a.txt", "action": "upsert", "content": "hi"}],
            },
        ),
        (
            "open_pull_request",
            {"owner": "octo", "repo": "repo", "title": "t", "head": "feat", "base": "main"},
        ),
        ("comment_on_issue", {"owner": "octo", "repo": "repo", "issue_number": 1, "body": "hi"}),
    ],
)
def test_write_tools_reject_extra_fields(tool_name: str, base_args: dict) -> None:
    args = dict(base_args)
    args["extra"] = 123

    with pytest.raises(SafeError):
        validate_tool_arguments(tool_name, args)


def test_all_tools_have_additional_properties_false() -> None:
    for meta in TOOL_METADATA.values():
        assert meta["inputSchema"].get("additionalProperties") is False


def test_rejects_token_like_value_without_echo() -> None:
    token = "ghp_1234567890abcdef"

    # validate_tool_arguments doesn't check secrets; it should pass schema.
    validate_tool_arguments("get_repository", {"owner": "octo", "repo": "repo"})

    from github_app_mcp.safety import validate_no_secrets

    with pytest.raises(SafeError) as exc:
        validate_no_secrets({"owner": "octo", "repo": "repo", "note": token})

    assert token not in exc.value.message


def test_create_issue_schema_rejects_extra_fields() -> None:
    args = {
        "owner": "octo",
        "repo": "repo",
        "title": "t",
        "body": "b",
        "labels": ["bug"],
        "assignees": ["octocat"],
        "milestone": 1,
        "extra": "nope",
    }

    with pytest.raises(SafeError) as exc:
        validate_tool_arguments("create_issue", args)

    assert "Unexpected fields" in exc.value.message


@pytest.mark.parametrize(
    "tool_name,base_args",
    [
        ("list_project_v2_fields", {"project_id": "PVT_1"}),
        ("list_project_v2_items", {"project_id": "PVT_1"}),
        ("get_project_v2_item", {"project_id": "PVT_1", "item_id": "PVTI_1"}),
        (
            "set_project_v2_item_field_value",
            {"project_id": "PVT_1", "item_id": "PVTI_1", "field_id": "F_1", "single_select_option_id": "O_1"},
        ),
        ("get_issue", {"owner": "octo", "repo": "repo", "number": 1}),
        ("update_issue", {"owner": "octo", "repo": "repo", "number": 1}),
    ],
)
def test_us2_tools_reject_extra_fields(tool_name: str, base_args: dict) -> None:
    args = dict(base_args)
    args["extra"] = "nope"

    with pytest.raises(SafeError):
        validate_tool_arguments(tool_name, args)


@pytest.mark.parametrize(
    "tool_name,bad_args",
    [
        ("list_project_v2_fields", {"project_id": 123}),
        ("list_project_v2_items", {"project_id": "PVT_1", "page_size": "20"}),
        ("get_project_v2_item", {"project_id": "PVT_1", "item_id": 1}),
        (
            "set_project_v2_item_field_value",
            {"project_id": "PVT_1", "item_id": "PVTI_1", "field_id": "F_1", "single_select_option_id": 1},
        ),
        ("get_issue", {"owner": "octo", "repo": "repo", "number": "1"}),
        ("update_issue", {"owner": "octo", "repo": "repo", "number": "1"}),
    ],
)
def test_us2_tools_reject_invalid_types(tool_name: str, bad_args: dict) -> None:
    with pytest.raises(SafeError):
        validate_tool_arguments(tool_name, bad_args)


@pytest.mark.parametrize(
    "bad_args",
    [
        {"project_id": "PVT_1", "page_size": 0},
        {"project_id": "PVT_1", "page_size": 51},
    ],
)
def test_list_project_v2_items_rejects_page_size_out_of_range(bad_args: dict) -> None:
    with pytest.raises(SafeError) as exc:
        validate_tool_arguments("list_project_v2_items", bad_args)

    assert "page_size" in exc.value.message


@pytest.mark.parametrize(
    "bad_args,expected_substring",
    [
        ({"owner": "octo", "repo": "repo", "title": "t"}, "Missing required field"),
        (
            {"owner": "octo", "repo": "repo", "title": "t", "body": "b", "labels": "bug"},
            "labels",
        ),
        (
            {"owner": "octo", "repo": "repo", "title": "t", "body": "b", "assignees": "octocat"},
            "assignees",
        ),
        (
            {"owner": "octo", "repo": "repo", "title": "t", "body": "b", "milestone": "1"},
            "milestone",
        ),
    ],
)
def test_create_issue_schema_rejects_invalid_types(bad_args: dict, expected_substring: str) -> None:
    with pytest.raises(SafeError) as exc:
        validate_tool_arguments("create_issue", bad_args)

    assert expected_substring in exc.value.message
