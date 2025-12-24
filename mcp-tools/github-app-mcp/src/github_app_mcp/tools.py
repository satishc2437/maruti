"""Tool registry and dispatch layer.

This module:
- defines the allow-listed tools (public contract surface)
- builds a per-server runtime from host-provided config
- creates a correlation_id per operation attempt
- performs secret/policy checks before executing any tool implementation
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

from .audit import AuditLogger, build_event, new_correlation_id
from .auth import GitHubAppAuth
from .config import AppConfig, load_config_from_env
from .errors import SafeError, internal_error, safe_error_to_result
from .github_client import GitHubClient, RequestBudget
from .github_graphql_client import GitHubGraphQLClient
from .policy import Policy
from .safety import enforce_max_bytes, validate_no_secrets

TOOL_METADATA: dict[str, dict[str, Any]] = {
    "get_repository": {
        "description": "Read repository metadata within the GitHub App installation scope.",
        "inputSchema": {
            "type": "object",
            "required": ["owner", "repo"],
            "properties": {
                "owner": {"type": "string", "minLength": 1},
                "repo": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
    },
    "list_branches": {
        "description": "List branches in a repository within the GitHub App installation scope.",
        "inputSchema": {
            "type": "object",
            "required": ["owner", "repo"],
            "properties": {
                "owner": {"type": "string", "minLength": 1},
                "repo": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
    },
    "get_file": {
        "description": "Read a single file at a given ref (size-limited).",
        "inputSchema": {
            "type": "object",
            "required": ["owner", "repo", "path"],
            "properties": {
                "owner": {"type": "string", "minLength": 1},
                "repo": {"type": "string", "minLength": 1},
                "path": {"type": "string", "minLength": 1},
                "ref": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    "list_pull_requests": {
        "description": "List pull requests for a repository (basic fields only).",
        "inputSchema": {
            "type": "object",
            "required": ["owner", "repo"],
            "properties": {
                "owner": {"type": "string", "minLength": 1},
                "repo": {"type": "string", "minLength": 1},
                "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
            },
            "additionalProperties": False,
        },
    },
    "list_issues": {
        "description": "List issues for a repository (basic fields only).",
        "inputSchema": {
            "type": "object",
            "required": ["owner", "repo"],
            "properties": {
                "owner": {"type": "string", "minLength": 1},
                "repo": {"type": "string", "minLength": 1},
                "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
            },
            "additionalProperties": False,
        },
    },
    "create_branch": {
        "description": "Create a new branch from a base ref/sha.",
        "inputSchema": {
            "type": "object",
            "required": ["owner", "repo", "base", "branch"],
            "properties": {
                "owner": {"type": "string", "minLength": 1},
                "repo": {"type": "string", "minLength": 1},
                "base": {"type": "string", "minLength": 1},
                "branch": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
    },
    "commit_changes": {
        "description": "Create a single commit on a target branch from a set of file changes.",
        "inputSchema": {
            "type": "object",
            "required": ["owner", "repo", "branch", "message", "changes"],
            "properties": {
                "owner": {"type": "string", "minLength": 1},
                "repo": {"type": "string", "minLength": 1},
                "branch": {"type": "string", "minLength": 1},
                "message": {"type": "string", "minLength": 1},
                "changes": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["path", "action"],
                        "properties": {
                            "path": {"type": "string", "minLength": 1},
                            "action": {"type": "string", "enum": ["upsert", "delete"]},
                            "content": {"type": "string"},
                            "encoding": {"type": "string", "enum": ["utf-8", "base64"], "default": "utf-8"},
                        },
                        "additionalProperties": False,
                    },
                },
            },
            "additionalProperties": False,
        },
    },
    "open_pull_request": {
        "description": "Open a pull request from a head branch to a base branch.",
        "inputSchema": {
            "type": "object",
            "required": ["owner", "repo", "title", "head", "base"],
            "properties": {
                "owner": {"type": "string", "minLength": 1},
                "repo": {"type": "string", "minLength": 1},
                "title": {"type": "string", "minLength": 1},
                "body": {"type": "string"},
                "head": {"type": "string", "minLength": 1},
                "base": {"type": "string", "minLength": 1},
                "draft": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
    },
    "comment_on_issue": {
        "description": "Comment on an issue or pull request.",
        "inputSchema": {
            "type": "object",
            "required": ["owner", "repo", "issue_number", "body"],
            "properties": {
                "owner": {"type": "string", "minLength": 1},
                "repo": {"type": "string", "minLength": 1},
                "issue_number": {"type": "integer", "minimum": 1},
                "body": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
    },

    "create_issue": {
        "description": "Create an Issue in an allowlisted repository with optional standard metadata.",
        "inputSchema": {
            "type": "object",
            "required": ["owner", "repo", "title", "body"],
            "properties": {
                "owner": {"type": "string", "minLength": 1},
                "repo": {"type": "string", "minLength": 1},
                "title": {"type": "string", "minLength": 1},
                "body": {"type": "string"},
                "labels": {"type": "array"},
                "assignees": {"type": "array"},
                "milestone": {"type": "integer"},
            },
            "additionalProperties": False,
        },
    },
    "get_project_v2_by_number": {
        "description": "Resolve a GitHub Project (Projects v2) by owner login and project number.",
        "inputSchema": {
            "type": "object",
            "required": ["owner_login", "project_number"],
            "properties": {
                "owner_login": {"type": "string", "minLength": 1},
                "project_number": {"type": "integer", "minimum": 1},
            },
            "additionalProperties": False,
        },
    },
    "add_issue_to_project_v2": {
        "description": "Add an Issue (by node id) to a GitHub Project (Projects v2) by project id.",
        "inputSchema": {
            "type": "object",
            "required": ["project_id", "issue_node_id"],
            "properties": {
                "project_id": {"type": "string", "minLength": 1},
                "issue_node_id": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
    },

    "list_project_v2_fields": {
        "description": "List GitHub Project (Projects v2) fields and single-select options.",
        "inputSchema": {
            "type": "object",
            "required": ["project_id"],
            "properties": {
                "project_id": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
    },
    "list_project_v2_items": {
        "description": "List GitHub Project (Projects v2) items with pagination and optional status filtering.",
        "inputSchema": {
            "type": "object",
            "required": ["project_id"],
            "properties": {
                "project_id": {"type": "string", "minLength": 1},
                "page_size": {"type": "integer", "minimum": 1, "maximum": 50},
                "after_cursor": {"type": "string"},
                "status_option_id": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    "get_project_v2_item": {
        "description": "Get a single GitHub Project (Projects v2) item and its linked content.",
        "inputSchema": {
            "type": "object",
            "required": ["project_id", "item_id"],
            "properties": {
                "project_id": {"type": "string", "minLength": 1},
                "item_id": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
    },
    "set_project_v2_item_field_value": {
        "description": "Set a ProjectV2 item single-select field value.",
        "inputSchema": {
            "type": "object",
            "required": ["project_id", "item_id", "field_id", "single_select_option_id"],
            "properties": {
                "project_id": {"type": "string", "minLength": 1},
                "item_id": {"type": "string", "minLength": 1},
                "field_id": {"type": "string", "minLength": 1},
                "single_select_option_id": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
    },
    "get_issue": {
        "description": "Fetch an Issue by owner/repo and issue number.",
        "inputSchema": {
            "type": "object",
            "required": ["owner", "repo", "number"],
            "properties": {
                "owner": {"type": "string", "minLength": 1},
                "repo": {"type": "string", "minLength": 1},
                "number": {"type": "integer", "minimum": 1},
            },
            "additionalProperties": False,
        },
    },
    "update_issue": {
        "description": "Update an Issue's title/body/metadata/state.",
        "inputSchema": {
            "type": "object",
            "required": ["owner", "repo", "number"],
            "properties": {
                "owner": {"type": "string", "minLength": 1},
                "repo": {"type": "string", "minLength": 1},
                "number": {"type": "integer", "minimum": 1},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "labels": {"type": "array"},
                "assignees": {"type": "array"},
                "milestone": {"type": "integer"},
                "state": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
}


_PROJECT_SCOPED_TOOLS: frozenset[str] = frozenset(
    {
        "get_project_v2_by_number",
        "add_issue_to_project_v2",
        "list_project_v2_fields",
        "list_project_v2_items",
        "get_project_v2_item",
        "set_project_v2_item_field_value",
    }
)


@dataclass(frozen=True, slots=True)
class Runtime:
    """Per-server runtime dependencies shared across tool calls."""

    config: AppConfig
    audit: AuditLogger
    policy: Policy
    auth: GitHubAppAuth
    github: GitHubClient
    graphql: GitHubGraphQLClient


_RUNTIME: Runtime | None = None


def validate_tool_arguments(tool_name: str, arguments: dict[str, Any]) -> None:
    """Validate tool arguments against the tool's declared input schema.

    This is intentionally a minimal validator that enforces:
    - required fields
    - no extra properties when additionalProperties=false
    - basic JSON types (string/integer/boolean/array/object)

    It does NOT implement full JSON Schema.
    """
    if tool_name not in TOOL_METADATA:
        raise SafeError(code="UserInput", message="Unknown tool")

    schema = TOOL_METADATA[tool_name]["inputSchema"]
    props: dict[str, Any] = schema.get("properties", {})
    required: list[str] = schema.get("required", [])
    additional = schema.get("additionalProperties", True)

    for k in required:
        if k not in arguments:
            raise SafeError(code="UserInput", message=f"Missing required field: {k}")

    if additional is False:
        extras = [k for k in arguments.keys() if k not in props]
        if extras:
            raise SafeError(code="UserInput", message="Unexpected fields are not allowed")

    # Basic type validation for declared properties.
    for k, spec in props.items():
        if k not in arguments:
            continue
        expected = spec.get("type")
        if expected is None:
            continue
        v = arguments[k]
        if expected == "string" and not isinstance(v, str):
            raise SafeError(code="UserInput", message=f"Field '{k}' must be a string")
        if expected == "integer" and not isinstance(v, int):
            raise SafeError(code="UserInput", message=f"Field '{k}' must be an integer")
        if expected == "boolean" and not isinstance(v, bool):
            raise SafeError(code="UserInput", message=f"Field '{k}' must be a boolean")
        if expected == "array" and not isinstance(v, list):
            raise SafeError(code="UserInput", message=f"Field '{k}' must be an array")
        if expected == "object" and not isinstance(v, dict):
            raise SafeError(code="UserInput", message=f"Field '{k}' must be an object")

        if expected == "string":
            min_len = spec.get("minLength")
            if isinstance(min_len, int) and len(v) < min_len:
                raise SafeError(code="UserInput", message=f"Field '{k}' must be at least {min_len} characters")

        if expected == "integer":
            minimum = spec.get("minimum")
            maximum = spec.get("maximum")
            has_min = isinstance(minimum, int)
            has_max = isinstance(maximum, int)
            if has_min and has_max and not (minimum <= v <= maximum):
                raise SafeError(code="UserInput", message=f"Field '{k}' must be between {minimum} and {maximum}")
            if has_min and not has_max and v < minimum:
                raise SafeError(code="UserInput", message=f"Field '{k}' must be >= {minimum}")
            if has_max and not has_min and v > maximum:
                raise SafeError(code="UserInput", message=f"Field '{k}' must be <= {maximum}")


def initialize_runtime_from_env() -> Runtime:
    """Initialize and cache runtime from environment.

    Called at server startup (fail-fast), and can also be used lazily.
    """
    global _RUNTIME  # pylint: disable=global-statement
    if _RUNTIME is not None:
        return _RUNTIME

    config = load_config_from_env()
    audit = AuditLogger(
        sink_path=config.audit_log_path,
        max_bytes=config.audit_max_bytes,
        max_backups=config.audit_max_backups,
    )
    policy = Policy(
        allowed_repos=config.policy.allowed_repos,
        allowed_projects=config.policy.allowed_projects,
        pr_only=config.policy.pr_only,
        protected_branch_patterns=config.policy.protected_branches,
    )
    auth = GitHubAppAuth(config=config)
    github = GitHubClient(token_provider=auth.get_installation_token, limits=config.limits)
    graphql = GitHubGraphQLClient(token_provider=auth.get_installation_token, limits=config.limits)

    _RUNTIME = Runtime(config=config, audit=audit, policy=policy, auth=auth, github=github, graphql=graphql)
    return _RUNTIME


def _budget(runtime: Runtime) -> RequestBudget:
    return RequestBudget(total_timeout_s=runtime.config.limits.total_timeout_s)


def _require_str(arguments: dict[str, Any], key: str) -> str:
    v = arguments.get(key)
    if not isinstance(v, str) or not v:
        raise SafeError(code="UserInput", message=f"Field '{key}' is required")
    return v


def _require_int(arguments: dict[str, Any], key: str) -> int:
    v = arguments.get(key)
    if not isinstance(v, int):
        raise SafeError(code="UserInput", message=f"Field '{key}' must be an integer")
    return v


_QUERY_GET_PROJECT_V2_BY_NUMBER = """
query($login: String!, $number: Int!) {
  repositoryOwner(login: $login) {
    __typename
    login
    ... on Organization {
      projectV2(number: $number) { id number title url }
    }
    ... on User {
      projectV2(number: $number) { id number title url }
    }
  }
}
""".strip()


_QUERY_PROJECT_V2_NODE_INFO = """
query($id: ID!) {
  node(id: $id) {
    __typename
    ... on ProjectV2 {
      number
      url
      owner { login }
    }
  }
}
""".strip()


_QUERY_LIST_PROJECT_V2_FIELDS = """
query($id: ID!) {
    node(id: $id) {
        __typename
        ... on ProjectV2 {
            number
            owner { login }
            fields(first: 100) {
                nodes {
                    __typename
                    ... on ProjectV2FieldCommon { id name }
                    ... on ProjectV2SingleSelectField {
                        options { id name }
                    }
                }
            }
        }
    }
}
""".strip()


_QUERY_LIST_PROJECT_V2_ITEMS = """
query($id: ID!, $first: Int!, $after: String) {
    node(id: $id) {
        __typename
        ... on ProjectV2 {
            number
            owner { login }
            items(first: $first, after: $after) {
                pageInfo { hasNextPage endCursor }
                nodes {
                    id
                    content {
                        __typename
                        ... on Issue {
                            id
                            number
                            url
                            repository { name owner { login } }
                        }
                    }
                    fieldValues(first: 20) {
                        nodes {
                            __typename
                            ... on ProjectV2ItemFieldSingleSelectValue {
                                name
                                optionId
                            }
                        }
                    }
                }
            }
        }
    }
}
""".strip()


_QUERY_GET_PROJECT_V2_ITEM = """
query($projectId: ID!, $itemId: ID!) {
    project: node(id: $projectId) {
        __typename
        ... on ProjectV2 { number owner { login } }
    }
    item: node(id: $itemId) {
        __typename
        ... on ProjectV2Item {
            id
            content {
                __typename
                ... on Issue {
                    id
                    number
                    url
                    repository { name owner { login } }
                }
            }
            fieldValues(first: 20) {
                nodes {
                    __typename
                    ... on ProjectV2ItemFieldSingleSelectValue { name optionId }
                }
            }
        }
    }
}
""".strip()


_MUTATION_ADD_ISSUE_TO_PROJECT_V2 = """
mutation($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
    item { id }
  }
}
""".strip()


_MUTATION_SET_PROJECT_V2_ITEM_FIELD_VALUE = """
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
    updateProjectV2ItemFieldValue(
        input: {
            projectId: $projectId,
            itemId: $itemId,
            fieldId: $fieldId,
            value: { singleSelectOptionId: $optionId }
        }
    ) {
        projectV2Item { id }
    }
}
""".strip()


async def _tool_create_issue(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    owner = _require_str(arguments, "owner")
    repo = _require_str(arguments, "repo")
    title = _require_str(arguments, "title")
    body = arguments["body"]
    labels = arguments.get("labels")
    assignees = arguments.get("assignees")
    milestone = arguments.get("milestone")

    enforce_max_bytes(
        data=title.encode("utf-8"),
        max_bytes=runtime.config.limits.issue_title_max_bytes,
        what="issue title",
    )
    enforce_max_bytes(
        data=body.encode("utf-8"),
        max_bytes=runtime.config.limits.issue_body_max_bytes,
        what="issue body",
    )

    payload: dict[str, Any] = {"title": title, "body": body}
    if labels is not None:
        payload["labels"] = labels
    if assignees is not None:
        payload["assignees"] = assignees
    if milestone is not None:
        payload["milestone"] = milestone

    data = await runtime.github.request_json(
        method="POST",
        path=f"/repos/{owner}/{repo}/issues",
        json_body=payload,
        budget=_budget(runtime),
    )
    if not isinstance(data, dict):
        raise SafeError(code="GitHub", message="Unexpected issue response")
    number = data.get("number")
    url = data.get("html_url")
    node_id = data.get("node_id")
    if not isinstance(number, int) or not isinstance(url, str) or not isinstance(node_id, str):
        raise SafeError(code="GitHub", message="Unexpected issue response")

    issue_obj = {
        "owner": owner,
        "repo": repo,
        "number": number,
        "url": url,
        "issue_node_id": node_id,
        "node_id": node_id,
    }
    return {"issue": issue_obj}


async def _tool_get_project_v2_by_number(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    owner_login = _require_str(arguments, "owner_login")
    project_number = _require_int(arguments, "project_number")
    if project_number < 1:
        raise SafeError(code="UserInput", message="Field 'project_number' must be >= 1")

    decision = runtime.policy.check_project_allowed(owner_login=owner_login, project_number=project_number)
    if not decision.allowed:
        raise SafeError(code="Forbidden", message="Project is not allowed")

    result = await runtime.graphql.execute(
        query=_QUERY_GET_PROJECT_V2_BY_NUMBER,
        variables={"login": owner_login, "number": project_number},
        budget=_budget(runtime),
    )
    data = result.data
    owner = data.get("repositoryOwner")
    if not isinstance(owner, dict):
        raise SafeError(code="GitHub", message="Unexpected project response")

    project = owner.get("projectV2")
    if not isinstance(project, dict):
        raise SafeError(code="UserInput", message="Project not found")

    project_id = project.get("id")
    url = project.get("url")
    title = project.get("title")
    number = project.get("number")
    login = owner.get("login")
    if not isinstance(project_id, str) or not isinstance(url, str) or not isinstance(title, str):
        raise SafeError(code="GitHub", message="Unexpected project response")
    if not isinstance(number, int) or not isinstance(login, str):
        raise SafeError(code="GitHub", message="Unexpected project response")

    return {
        "project": {
            "project_id": project_id,
            "owner_login": login,
            "project_number": number,
            "url": url,
            "title": title,
        }
    }


async def _resolve_project_v2_owner_and_number(runtime: Runtime, *, project_id: str) -> tuple[str, int]:
    result = await runtime.graphql.execute(
        query=_QUERY_PROJECT_V2_NODE_INFO,
        variables={"id": project_id},
        budget=_budget(runtime),
    )
    node = result.data.get("node")
    if not isinstance(node, dict) or node.get("__typename") != "ProjectV2":
        raise SafeError(code="UserInput", message="Project not found")

    number = node.get("number")
    owner = node.get("owner")
    login = owner.get("login") if isinstance(owner, dict) else None
    if not isinstance(number, int) or not isinstance(login, str):
        raise SafeError(code="GitHub", message="Unexpected project response")
    return login, number


async def _tool_add_issue_to_project_v2(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    project_id = _require_str(arguments, "project_id")
    issue_node_id = _require_str(arguments, "issue_node_id")

    owner_login, project_number = await _resolve_project_v2_owner_and_number(runtime, project_id=project_id)
    decision = runtime.policy.check_project_allowed(owner_login=owner_login, project_number=project_number)
    if not decision.allowed:
        raise SafeError(code="Forbidden", message="Project is not allowed")

    result = await runtime.graphql.execute(
        query=_MUTATION_ADD_ISSUE_TO_PROJECT_V2,
        variables={"projectId": project_id, "contentId": issue_node_id},
        budget=_budget(runtime),
    )

    payload = result.data.get("addProjectV2ItemById")
    item = payload.get("item") if isinstance(payload, dict) else None
    item_id = item.get("id") if isinstance(item, dict) else None
    if not isinstance(item_id, str):
        raise SafeError(code="GitHub", message="Unexpected add-to-project response")

    return {"item": {"item_id": item_id}}


def _project_allowlist_check_or_forbid(runtime: Runtime, *, owner_login: str, project_number: int) -> None:
    decision = runtime.policy.check_project_allowed(owner_login=owner_login, project_number=project_number)
    if not decision.allowed:
        raise SafeError(code="Forbidden", message="Project is not allowed")


def _extract_first_single_select_value(field_values: object) -> tuple[str | None, str | None]:
    if not isinstance(field_values, dict):
        return None, None
    nodes = field_values.get("nodes")
    if not isinstance(nodes, list):
        return None, None
    for fv in nodes:
        if not isinstance(fv, dict):
            continue
        if fv.get("__typename") != "ProjectV2ItemFieldSingleSelectValue":
            continue
        option_id = fv.get("optionId")
        name = fv.get("name")
        if isinstance(option_id, str) and isinstance(name, str):
            return option_id, name
    return None, None


def _find_single_select_value_by_option_id(field_values: object, option_id: str) -> tuple[str | None, str | None]:
    if not isinstance(field_values, dict):
        return None, None
    nodes = field_values.get("nodes")
    if not isinstance(nodes, list):
        return None, None
    for fv in nodes:
        if not isinstance(fv, dict):
            continue
        if fv.get("__typename") != "ProjectV2ItemFieldSingleSelectValue":
            continue
        oid = fv.get("optionId")
        name = fv.get("name")
        if oid == option_id and isinstance(name, str):
            return option_id, name
    return None, None


def _parse_issue_content(content: object) -> tuple[str, dict[str, Any] | None]:
    if not isinstance(content, dict) or not isinstance(content.get("__typename"), str):
        return "unknown", None

    typename: str = content["__typename"]
    if typename != "Issue":
        return typename.lower(), None

    issue_id = content.get("id")
    number_i = content.get("number")
    url = content.get("url")
    repo_obj = content.get("repository")
    repo_name = repo_obj.get("name") if isinstance(repo_obj, dict) else None
    repo_owner_obj = repo_obj.get("owner") if isinstance(repo_obj, dict) else None
    repo_owner_login = repo_owner_obj.get("login") if isinstance(repo_owner_obj, dict) else None

    if not (
        isinstance(issue_id, str)
        and isinstance(number_i, int)
        and isinstance(url, str)
        and isinstance(repo_name, str)
        and isinstance(repo_owner_login, str)
    ):
        return "issue", None

    return (
        "issue",
        {
            "owner": repo_owner_login,
            "repo": repo_name,
            "number": number_i,
            "url": url,
            "issue_node_id": issue_id,
        },
    )


async def _tool_list_project_v2_fields(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    project_id = _require_str(arguments, "project_id")

    result = await runtime.graphql.execute(
        query=_QUERY_LIST_PROJECT_V2_FIELDS,
        variables={"id": project_id},
        budget=_budget(runtime),
    )
    node = result.data.get("node")
    if not isinstance(node, dict) or node.get("__typename") != "ProjectV2":
        raise SafeError(code="UserInput", message="Project not found")

    owner = node.get("owner")
    login = owner.get("login") if isinstance(owner, dict) else None
    number = node.get("number")
    if not (isinstance(login, str) and isinstance(number, int)):
        raise SafeError(code="GitHub", message="Unexpected project response")
    _project_allowlist_check_or_forbid(runtime, owner_login=login, project_number=number)

    fields_conn = node.get("fields")
    fields_nodes = fields_conn.get("nodes") if isinstance(fields_conn, dict) else None
    if not isinstance(fields_nodes, list):
        raise SafeError(code="GitHub", message="Unexpected project fields response")

    fields: list[dict[str, Any]] = []
    for f in fields_nodes:
        if not (
            isinstance(f, dict)
            and isinstance(f.get("id"), str)
            and isinstance(f.get("name"), str)
            and isinstance(f.get("__typename"), str)
        ):
            continue
        field_id = f["id"]
        name = f["name"]
        typename = f["__typename"]
        data_type = "unknown"
        if typename == "ProjectV2SingleSelectField":
            data_type = "single_select"
        elif typename == "ProjectV2TextField":
            data_type = "text"

        out_field: dict[str, Any] = {"field_id": field_id, "name": name, "data_type": data_type}
        if typename == "ProjectV2SingleSelectField":
            opts = f.get("options")
            options_out: list[dict[str, Any]] = []
            if isinstance(opts, list):
                for o in opts:
                    if not isinstance(o, dict):
                        continue
                    oid = o.get("id")
                    oname = o.get("name")
                    if isinstance(oid, str) and isinstance(oname, str):
                        options_out.append({"option_id": oid, "name": oname})
            out_field["options"] = options_out
        fields.append(out_field)

    return {"fields": fields}


async def _tool_list_project_v2_items(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    project_id = _require_str(arguments, "project_id")
    page_size = arguments.get("page_size")
    if page_size is None:
        page_size = 20
    if not isinstance(page_size, int):
        raise SafeError(code="UserInput", message="Field 'page_size' must be an integer")
    if page_size < 1 or page_size > 50:
        raise SafeError(code="UserInput", message="page_size must be between 1 and 50")

    after_cursor = arguments.get("after_cursor")
    if after_cursor is not None and not isinstance(after_cursor, str):
        raise SafeError(code="UserInput", message="Field 'after_cursor' must be a string")

    status_option_id = arguments.get("status_option_id")
    if status_option_id is not None and not isinstance(status_option_id, str):
        raise SafeError(code="UserInput", message="Field 'status_option_id' must be a string")

    result = await runtime.graphql.execute(
        query=_QUERY_LIST_PROJECT_V2_ITEMS,
        variables={"id": project_id, "first": page_size, "after": after_cursor},
        budget=_budget(runtime),
    )
    node = result.data.get("node")
    if not isinstance(node, dict) or node.get("__typename") != "ProjectV2":
        raise SafeError(code="UserInput", message="Project not found")

    owner = node.get("owner")
    login = owner.get("login") if isinstance(owner, dict) else None
    number = node.get("number")
    if not (isinstance(login, str) and isinstance(number, int)):
        raise SafeError(code="GitHub", message="Unexpected project response")
    _project_allowlist_check_or_forbid(runtime, owner_login=login, project_number=number)

    items_conn = node.get("items")
    if not isinstance(items_conn, dict):
        raise SafeError(code="GitHub", message="Unexpected project items response")
    page_info = items_conn.get("pageInfo")
    nodes = items_conn.get("nodes")
    if not (isinstance(page_info, dict) and isinstance(nodes, list)):
        raise SafeError(code="GitHub", message="Unexpected project items response")

    has_next = page_info.get("hasNextPage")
    end_cursor = page_info.get("endCursor")
    if not isinstance(has_next, bool):
        raise SafeError(code="GitHub", message="Unexpected project items response")
    if end_cursor is not None and not isinstance(end_cursor, str):
        end_cursor = None

    items_out: list[dict[str, Any]] = []
    for it in nodes:
        if not isinstance(it, dict):
            continue
        item_id = it.get("id")
        if not isinstance(item_id, str):
            continue

        content_type, issue_obj = _parse_issue_content(it.get("content"))

        field_values = it.get("fieldValues")
        if isinstance(status_option_id, str) and status_option_id:
            status_id, status_name = _find_single_select_value_by_option_id(field_values, status_option_id)
            if status_id is None:
                continue
        else:
            status_id, status_name = _extract_first_single_select_value(field_values)

        items_out.append(
            {
                "item_id": item_id,
                "content_type": content_type,
                "status_option_id": status_id,
                "status_name": status_name,
                "issue": issue_obj,
            }
        )

    return {
        "items": items_out,
        "page_info": {"has_next_page": has_next, "end_cursor": end_cursor},
    }


async def _tool_get_project_v2_item(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    project_id = _require_str(arguments, "project_id")
    item_id = _require_str(arguments, "item_id")

    result = await runtime.graphql.execute(
        query=_QUERY_GET_PROJECT_V2_ITEM,
        variables={"projectId": project_id, "itemId": item_id},
        budget=_budget(runtime),
    )

    project = result.data.get("project")
    if not isinstance(project, dict) or project.get("__typename") != "ProjectV2":
        raise SafeError(code="UserInput", message="Project not found")
    number = project.get("number")
    owner = project.get("owner")
    login = owner.get("login") if isinstance(owner, dict) else None
    if not isinstance(number, int) or not isinstance(login, str):
        raise SafeError(code="GitHub", message="Unexpected project response")
    _project_allowlist_check_or_forbid(runtime, owner_login=login, project_number=number)

    item_node = result.data.get("item")
    if not isinstance(item_node, dict) or item_node.get("__typename") != "ProjectV2Item":
        raise SafeError(code="UserInput", message="Item not found")
    raw_item_id = item_node.get("id")
    if not isinstance(raw_item_id, str):
        raise SafeError(code="GitHub", message="Unexpected item response")

    content_type, issue_obj = _parse_issue_content(item_node.get("content"))

    status_id, status_name = _extract_first_single_select_value(item_node.get("fieldValues"))

    return {
        "item": {
            "item_id": raw_item_id,
            "content_type": content_type,
            "status_option_id": status_id,
            "status_name": status_name,
            "issue": issue_obj,
        }
    }


async def _tool_set_project_v2_item_field_value(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    project_id = _require_str(arguments, "project_id")
    item_id = _require_str(arguments, "item_id")
    field_id = _require_str(arguments, "field_id")
    option_id = _require_str(arguments, "single_select_option_id")

    # Resolve owner/number for allowlist enforcement.
    node_result = await runtime.graphql.execute(
        query=_QUERY_PROJECT_V2_NODE_INFO,
        variables={"id": project_id},
        budget=_budget(runtime),
    )
    node = node_result.data.get("node")
    if not isinstance(node, dict) or node.get("__typename") != "ProjectV2":
        raise SafeError(code="UserInput", message="Project not found")
    number = node.get("number")
    owner = node.get("owner")
    login = owner.get("login") if isinstance(owner, dict) else None
    if not isinstance(number, int) or not isinstance(login, str):
        raise SafeError(code="GitHub", message="Unexpected project response")
    _project_allowlist_check_or_forbid(runtime, owner_login=login, project_number=number)

    result = await runtime.graphql.execute(
        query=_MUTATION_SET_PROJECT_V2_ITEM_FIELD_VALUE,
        variables={"projectId": project_id, "itemId": item_id, "fieldId": field_id, "optionId": option_id},
        budget=_budget(runtime),
    )
    payload = result.data.get("updateProjectV2ItemFieldValue")
    proj_item = payload.get("projectV2Item") if isinstance(payload, dict) else None
    updated_id = proj_item.get("id") if isinstance(proj_item, dict) else None
    if not isinstance(updated_id, str):
        raise SafeError(code="GitHub", message="Unexpected set-field response")

    return {"item": {"item_id": updated_id}}


async def _tool_get_issue(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    owner = _require_str(arguments, "owner")
    repo = _require_str(arguments, "repo")
    number = _require_int(arguments, "number")
    if number < 1:
        raise SafeError(code="UserInput", message="Field 'number' must be >= 1")

    data = await runtime.github.request_json(
        method="GET",
        path=f"/repos/{owner}/{repo}/issues/{number}",
        budget=_budget(runtime),
    )
    if not isinstance(data, dict):
        raise SafeError(code="GitHub", message="Unexpected issue response")
    if "pull_request" in data:
        raise SafeError(code="UserInput", message="Pull requests are not supported")

    node_id = data.get("node_id")
    url = data.get("html_url")
    title = data.get("title")
    body = data.get("body")
    state = data.get("state")
    if not isinstance(node_id, str) or not isinstance(url, str) or not isinstance(title, str) or not isinstance(state, str):
        raise SafeError(code="GitHub", message="Unexpected issue response")
    if body is not None and not isinstance(body, str):
        body = None

    return {
        "issue": {
            "owner": owner,
            "repo": repo,
            "number": number,
            "url": url,
            "issue_node_id": node_id,
            "node_id": node_id,
            "title": title,
            "body": body,
            "state": state.lower(),
        }
    }


async def _tool_update_issue(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    owner = _require_str(arguments, "owner")
    repo = _require_str(arguments, "repo")
    number = _require_int(arguments, "number")
    if number < 1:
        raise SafeError(code="UserInput", message="Field 'number' must be >= 1")

    payload: dict[str, Any] = {}
    if "title" in arguments:
        title = arguments.get("title")
        if not isinstance(title, str):
            raise SafeError(code="UserInput", message="Field 'title' must be a string")
        enforce_max_bytes(data=title.encode("utf-8"), max_bytes=runtime.config.limits.issue_title_max_bytes, what="issue title")
        payload["title"] = title
    if "body" in arguments:
        body = arguments.get("body")
        if not isinstance(body, str):
            raise SafeError(code="UserInput", message="Field 'body' must be a string")
        enforce_max_bytes(data=body.encode("utf-8"), max_bytes=runtime.config.limits.issue_body_max_bytes, what="issue body")
        payload["body"] = body

    for k in ("labels", "assignees", "milestone"):
        if k in arguments:
            payload[k] = arguments.get(k)

    if "state" in arguments:
        state = arguments.get("state")
        if not isinstance(state, str):
            raise SafeError(code="UserInput", message="Field 'state' must be a string")
        normalized = state.strip().lower()
        if normalized not in {"open", "closed"}:
            raise SafeError(code="UserInput", message="Field 'state' must be 'open' or 'closed'")
        payload["state"] = normalized

    data = await runtime.github.request_json(
        method="PATCH",
        path=f"/repos/{owner}/{repo}/issues/{number}",
        json_body=payload,
        budget=_budget(runtime),
    )
    if not isinstance(data, dict):
        raise SafeError(code="GitHub", message="Unexpected issue response")

    node_id = data.get("node_id")
    url = data.get("html_url")
    title = data.get("title")
    body = data.get("body")
    state = data.get("state")
    if not isinstance(node_id, str) or not isinstance(url, str) or not isinstance(title, str) or not isinstance(state, str):
        raise SafeError(code="GitHub", message="Unexpected issue response")
    if body is not None and not isinstance(body, str):
        body = None

    return {
        "issue": {
            "owner": owner,
            "repo": repo,
            "number": number,
            "url": url,
            "issue_node_id": node_id,
            "node_id": node_id,
            "title": title,
            "body": body,
            "state": state.lower(),
        }
    }


async def _tool_get_repository(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    owner = _require_str(arguments, "owner")
    repo = _require_str(arguments, "repo")

    data = await runtime.github.request_json(
        method="GET",
        path=f"/repos/{owner}/{repo}",
        budget=_budget(runtime),
    )

    if not isinstance(data, dict):
        raise SafeError(code="GitHub", message="Unexpected repository response")

    repository = {
        "full_name": data.get("full_name"),
        "default_branch": data.get("default_branch"),
        "private": data.get("private"),
        "url": data.get("html_url"),
    }
    return {"repository": repository}


async def _tool_list_branches(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    owner = _require_str(arguments, "owner")
    repo = _require_str(arguments, "repo")

    repo_data = await runtime.github.request_json(
        method="GET",
        path=f"/repos/{owner}/{repo}",
        budget=_budget(runtime),
    )
    if not isinstance(repo_data, dict):
        raise SafeError(code="GitHub", message="Unexpected repository response")
    default_branch = repo_data.get("default_branch")
    if not isinstance(default_branch, str):
        default_branch = ""

    branches_data = await runtime.github.request_json(
        method="GET",
        path=f"/repos/{owner}/{repo}/branches",
        params={"per_page": "100"},
        budget=_budget(runtime),
    )
    if not isinstance(branches_data, list):
        raise SafeError(code="GitHub", message="Unexpected branches response")

    branches: list[str] = []
    for b in branches_data:
        if isinstance(b, dict) and isinstance(b.get("name"), str):
            branches.append(b["name"])

    return {"default_branch": default_branch, "branches": branches}


async def _tool_get_file(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    owner = _require_str(arguments, "owner")
    repo = _require_str(arguments, "repo")
    path = _require_str(arguments, "path")
    ref = arguments.get("ref")
    if ref is not None and not isinstance(ref, str):
        raise SafeError(code="UserInput", message="Field 'ref' must be a string")

    params = None
    if isinstance(ref, str) and ref:
        params = {"ref": ref}

    data = await runtime.github.request_json(
        method="GET",
        path=f"/repos/{owner}/{repo}/contents/{path}",
        params=params,
        budget=_budget(runtime),
    )
    if not isinstance(data, dict):
        raise SafeError(code="GitHub", message="Unexpected file response")
    if data.get("type") != "file":
        raise SafeError(code="UserInput", message="Path is not a file")

    encoding = data.get("encoding")
    content_b64 = data.get("content")
    if encoding != "base64" or not isinstance(content_b64, str):
        raise SafeError(code="GitHub", message="Unexpected file content encoding")

    decoded = base64.b64decode(content_b64.encode("utf-8"), validate=False)
    enforce_max_bytes(data=decoded, max_bytes=runtime.config.limits.get_file_max_bytes, what="file")

    try:
        text = decoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SafeError(code="UserInput", message="Binary file content is not supported") from exc

    file_obj: dict[str, Any] = {
        "path": path,
        "content": text,
        "encoding": "utf-8",
    }
    if isinstance(ref, str) and ref:
        file_obj["ref"] = ref

    return {"file": file_obj}


async def _tool_list_pull_requests(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    owner = _require_str(arguments, "owner")
    repo = _require_str(arguments, "repo")
    state = arguments.get("state") or "open"
    if not isinstance(state, str):
        raise SafeError(code="UserInput", message="Field 'state' must be a string")

    data = await runtime.github.request_json(
        method="GET",
        path=f"/repos/{owner}/{repo}/pulls",
        params={"state": state, "per_page": "30"},
        budget=_budget(runtime),
    )
    if not isinstance(data, list):
        raise SafeError(code="GitHub", message="Unexpected pull requests response")

    pull_requests: list[dict[str, Any]] = []
    for pr in data:
        if not isinstance(pr, dict):
            continue
        number = pr.get("number")
        url = pr.get("html_url")
        if isinstance(number, int) and isinstance(url, str):
            pull_requests.append({"number": number, "url": url})

    return {"pull_requests": pull_requests}


async def _tool_list_issues(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    owner = _require_str(arguments, "owner")
    repo = _require_str(arguments, "repo")
    state = arguments.get("state") or "open"
    if not isinstance(state, str):
        raise SafeError(code="UserInput", message="Field 'state' must be a string")

    data = await runtime.github.request_json(
        method="GET",
        path=f"/repos/{owner}/{repo}/issues",
        params={"state": state, "per_page": "30"},
        budget=_budget(runtime),
    )
    if not isinstance(data, list):
        raise SafeError(code="GitHub", message="Unexpected issues response")

    issues: list[dict[str, Any]] = []
    for it in data:
        if not isinstance(it, dict):
            continue
        if "pull_request" in it:
            continue
        number = it.get("number")
        url = it.get("html_url")
        if isinstance(number, int) and isinstance(url, str):
            issues.append({"number": number, "url": url})

    return {"issues": issues}


async def _resolve_base_sha(runtime: Runtime, *, owner: str, repo: str, base: str) -> str:
    # Attempt as branch ref first.
    try:
        ref_data = await runtime.github.request_json(
            method="GET",
            path=f"/repos/{owner}/{repo}/git/ref/heads/{base}",
            budget=_budget(runtime),
        )
        if not isinstance(ref_data, dict):
            raise SafeError(code="GitHub", message="Unexpected ref response")
        obj = ref_data.get("object")
        if isinstance(obj, dict) and isinstance(obj.get("sha"), str):
            return obj["sha"]
    except SafeError as exc:
        # If 404, allow treating base as SHA.
        if exc.status_code != 404:
            raise

    return base


async def _tool_create_branch(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    owner = _require_str(arguments, "owner")
    repo = _require_str(arguments, "repo")
    base = _require_str(arguments, "base")
    branch = _require_str(arguments, "branch")

    if runtime.policy.is_branch_protected(branch):
        raise SafeError(
            code="Forbidden",
            message="Creating a protected branch is not allowed",
            hint="Choose a non-protected branch name and open a pull request into the protected branch",
        )

    sha = await _resolve_base_sha(runtime, owner=owner, repo=repo, base=base)

    try:
        _ = await runtime.github.request_json(
            method="POST",
            path=f"/repos/{owner}/{repo}/git/refs",
            json_body={"ref": f"refs/heads/{branch}", "sha": sha},
            budget=_budget(runtime),
        )
    except SafeError as exc:
        if exc.status_code == 422 and exc.hint and "reference already exists" in exc.hint.lower():
            raise SafeError(code="UserInput", message="Branch already exists") from exc
        raise

    return {"ref": f"refs/heads/{branch}"}


def _decode_change_content(*, content: str, encoding: str) -> bytes:
    if encoding == "utf-8":
        return content.encode("utf-8")
    if encoding == "base64":
        return base64.b64decode(content.encode("utf-8"), validate=False)
    raise SafeError(code="UserInput", message="Unsupported encoding")


async def _tool_commit_changes(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    owner = _require_str(arguments, "owner")
    repo = _require_str(arguments, "repo")
    branch = _require_str(arguments, "branch")
    message = _require_str(arguments, "message")

    if runtime.policy.is_branch_protected(branch):
        raise SafeError(
            code="Forbidden",
            message="Direct commits to protected branches are not allowed",
            hint="Use create_branch -> commit_changes -> open_pull_request",
        )

    changes = arguments.get("changes")
    if not isinstance(changes, list) or not changes:
        raise SafeError(code="UserInput", message="Field 'changes' must be a non-empty array")
    if len(changes) > runtime.config.limits.commit_max_files:
        raise SafeError(code="UserInput", message="Too many files in commit_changes")

    decoded_changes: list[dict[str, Any]] = []
    total_bytes = 0
    for ch in changes:
        if not isinstance(ch, dict):
            raise SafeError(code="UserInput", message="Each change must be an object")
        path = ch.get("path")
        action = ch.get("action")
        if not isinstance(path, str) or not path:
            raise SafeError(code="UserInput", message="Change.path is required")
        if action not in {"upsert", "delete"}:
            raise SafeError(code="UserInput", message="Change.action must be 'upsert' or 'delete'")

        if action == "delete":
            decoded_changes.append({"path": path, "action": "delete"})
            continue

        content = ch.get("content")
        if not isinstance(content, str):
            raise SafeError(code="UserInput", message="Change.content is required for upsert")
        encoding = ch.get("encoding") or "utf-8"
        if not isinstance(encoding, str):
            raise SafeError(code="UserInput", message="Change.encoding must be a string")

        raw = _decode_change_content(content=content, encoding=encoding)
        enforce_max_bytes(
            data=raw,
            max_bytes=runtime.config.limits.commit_max_file_bytes,
            what="file",
        )
        total_bytes += len(raw)
        if total_bytes > runtime.config.limits.commit_max_total_bytes:
            raise SafeError(code="UserInput", message="Total commit_changes content exceeds limit")

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SafeError(code="UserInput", message="Binary file content is not supported") from exc

        decoded_changes.append({"path": path, "action": "upsert", "content": text})

    ref_data = await runtime.github.request_json(
        method="GET",
        path=f"/repos/{owner}/{repo}/git/ref/heads/{branch}",
        budget=_budget(runtime),
    )
    if not isinstance(ref_data, dict):
        raise SafeError(code="GitHub", message="Unexpected ref response")
    obj = ref_data.get("object")
    commit_sha = obj.get("sha") if isinstance(obj, dict) else None
    if not isinstance(commit_sha, str):
        raise SafeError(code="GitHub", message="Unexpected ref response")

    commit_data = await runtime.github.request_json(
        method="GET",
        path=f"/repos/{owner}/{repo}/git/commits/{commit_sha}",
        budget=_budget(runtime),
    )
    if not isinstance(commit_data, dict):
        raise SafeError(code="GitHub", message="Unexpected commit response")
    tree_obj = commit_data.get("tree")
    base_tree_sha = tree_obj.get("sha") if isinstance(tree_obj, dict) else None
    if not isinstance(base_tree_sha, str):
        raise SafeError(code="GitHub", message="Unexpected commit response")

    tree_entries: list[dict[str, Any]] = []
    for ch in decoded_changes:
        if ch["action"] == "delete":
            tree_entries.append({"path": ch["path"], "mode": "100644", "type": "blob", "sha": None})
            continue

        blob = await runtime.github.request_json(
            method="POST",
            path=f"/repos/{owner}/{repo}/git/blobs",
            json_body={"content": ch["content"], "encoding": "utf-8"},
            budget=_budget(runtime),
        )
        if not isinstance(blob, dict):
            raise SafeError(code="GitHub", message="Unexpected blob response")
        blob_sha = blob.get("sha")
        if not isinstance(blob_sha, str):
            raise SafeError(code="GitHub", message="Unexpected blob response")
        tree_entries.append({"path": ch["path"], "mode": "100644", "type": "blob", "sha": blob_sha})

    tree = await runtime.github.request_json(
        method="POST",
        path=f"/repos/{owner}/{repo}/git/trees",
        json_body={"base_tree": base_tree_sha, "tree": tree_entries},
        budget=_budget(runtime),
    )
    if not isinstance(tree, dict):
        raise SafeError(code="GitHub", message="Unexpected tree response")
    new_tree_sha = tree.get("sha")
    if not isinstance(new_tree_sha, str):
        raise SafeError(code="GitHub", message="Unexpected tree response")

    new_commit = await runtime.github.request_json(
        method="POST",
        path=f"/repos/{owner}/{repo}/git/commits",
        json_body={"message": message, "tree": new_tree_sha, "parents": [commit_sha]},
        budget=_budget(runtime),
    )
    if not isinstance(new_commit, dict):
        raise SafeError(code="GitHub", message="Unexpected commit-create response")
    new_commit_sha = new_commit.get("sha")
    if not isinstance(new_commit_sha, str):
        raise SafeError(code="GitHub", message="Unexpected commit-create response")

    _ = await runtime.github.request_json(
        method="PATCH",
        path=f"/repos/{owner}/{repo}/git/refs/heads/{branch}",
        json_body={"sha": new_commit_sha, "force": False},
        budget=_budget(runtime),
    )

    return {
        "commit": {
            "sha": new_commit_sha,
            "url": f"https://github.com/{owner}/{repo}/commit/{new_commit_sha}",
        }
    }


async def _tool_open_pull_request(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    owner = _require_str(arguments, "owner")
    repo = _require_str(arguments, "repo")
    title = _require_str(arguments, "title")
    head = _require_str(arguments, "head")
    base = _require_str(arguments, "base")
    body = arguments.get("body")
    if body is not None and not isinstance(body, str):
        raise SafeError(code="UserInput", message="Field 'body' must be a string")
    draft = arguments.get("draft")
    if draft is None:
        draft = False
    if not isinstance(draft, bool):
        raise SafeError(code="UserInput", message="Field 'draft' must be a boolean")

    payload: dict[str, Any] = {"title": title, "head": head, "base": base, "draft": draft}
    if isinstance(body, str):
        payload["body"] = body

    data = await runtime.github.request_json(
        method="POST",
        path=f"/repos/{owner}/{repo}/pulls",
        json_body=payload,
        budget=_budget(runtime),
    )
    if not isinstance(data, dict):
        raise SafeError(code="GitHub", message="Unexpected pull request response")
    number = data.get("number")
    url = data.get("html_url")
    if not isinstance(number, int) or not isinstance(url, str):
        raise SafeError(code="GitHub", message="Unexpected pull request response")
    return {"pull_request": {"number": number, "url": url}}


async def _tool_comment_on_issue(runtime: Runtime, arguments: dict[str, Any]) -> dict[str, Any]:
    owner = _require_str(arguments, "owner")
    repo = _require_str(arguments, "repo")
    issue_number = _require_int(arguments, "issue_number")
    body = _require_str(arguments, "body")

    data = await runtime.github.request_json(
        method="POST",
        path=f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
        json_body={"body": body},
        budget=_budget(runtime),
    )
    if not isinstance(data, dict):
        raise SafeError(code="GitHub", message="Unexpected comment response")
    comment_id = data.get("id")
    url = data.get("html_url")
    if not isinstance(comment_id, int) or not isinstance(url, str):
        raise SafeError(code="GitHub", message="Unexpected comment response")
    return {"comment": {"id": comment_id, "url": url}}


_TOOL_FUNCS: dict[str, Any] = {
    "get_repository": _tool_get_repository,
    "list_branches": _tool_list_branches,
    "get_file": _tool_get_file,
    "list_pull_requests": _tool_list_pull_requests,
    "list_issues": _tool_list_issues,
    "create_branch": _tool_create_branch,
    "commit_changes": _tool_commit_changes,
    "open_pull_request": _tool_open_pull_request,
    "comment_on_issue": _tool_comment_on_issue,
    "create_issue": _tool_create_issue,
    "get_project_v2_by_number": _tool_get_project_v2_by_number,
    "add_issue_to_project_v2": _tool_add_issue_to_project_v2,
    "list_project_v2_fields": _tool_list_project_v2_fields,
    "list_project_v2_items": _tool_list_project_v2_items,
    "get_project_v2_item": _tool_get_project_v2_item,
    "set_project_v2_item_field_value": _tool_set_project_v2_item_field_value,
    "get_issue": _tool_get_issue,
    "update_issue": _tool_update_issue,
}


def _target_repo_from_args(arguments: dict[str, Any]) -> str:
    owner = arguments.get("owner")
    repo = arguments.get("repo")
    if isinstance(owner, str) and isinstance(repo, str) and owner and repo:
        return f"{owner}/{repo}"
    return "<unknown>"


async def dispatch_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a tool call.

    Always returns an envelope that includes correlation_id.
    """
    correlation_id = new_correlation_id()
    target_repo = _target_repo_from_args(arguments)

    runtime: Runtime | None = None
    start: float | None = None

    try:
        runtime = initialize_runtime_from_env()
        start = runtime.audit.measure_start()

        validate_no_secrets(arguments)
        if name not in TOOL_METADATA:
            raise SafeError(
                code="UserInput",
                message=f"Unknown tool: {name}",
                hint=f"Available tools: {', '.join(sorted(TOOL_METADATA.keys()))}",
            )

        validate_tool_arguments(name, arguments)

        op_decision = runtime.policy.check_operation_allowed(name)
        if not op_decision.allowed:
            raise SafeError(code="Forbidden", message="Operation is not allowed")

        if name not in _PROJECT_SCOPED_TOOLS:
            repo_decision = runtime.policy.check_repo_allowed(target_repo)
            if not repo_decision.allowed:
                raise SafeError(code="Forbidden", message="Repository is not allowed")

        func = _TOOL_FUNCS.get(name)
        if func is None:
            raise SafeError(code="UserInput", message="Tool not implemented")

        result = await func(runtime, arguments)

        duration = runtime.audit.measure_duration_ms(start)
        runtime.audit.write_event(
            build_event(
                correlation_id=correlation_id,
                operation=name,
                target_repo=target_repo,
                outcome="succeeded",
                reason=None,
                duration_ms=duration,
            )
        )

        out: dict[str, Any] = {"ok": True, "correlation_id": correlation_id}
        out.update(result)
        return out

    except SafeError as err:
        outcome = "denied" if err.code in {"UserInput", "Forbidden", "Config"} else "failed"
        if runtime is not None and start is not None:
            duration = runtime.audit.measure_duration_ms(start)
            runtime.audit.write_event(
                build_event(
                    correlation_id=correlation_id,
                    operation=name,
                    target_repo=target_repo,
                    outcome=outcome,
                    reason=err.message,
                    duration_ms=duration,
                )
            )
        else:
            # Best-effort fallback: still emit an audit event to stderr when runtime could
            # not be initialized (e.g., Config failures).
            AuditLogger(sink_path=None).write_event(
                build_event(
                    correlation_id=correlation_id,
                    operation=name,
                    target_repo=target_repo,
                    outcome=outcome,
                    reason=err.message,
                    duration_ms=None,
                )
            )
        result = safe_error_to_result(err)
        result["correlation_id"] = correlation_id
        return result
    except Exception:  # pylint: disable=broad-exception-caught  # pragma: no cover
        if runtime is not None and start is not None:
            duration = runtime.audit.measure_duration_ms(start)
            runtime.audit.write_event(
                build_event(
                    correlation_id=correlation_id,
                    operation=name,
                    target_repo=target_repo,
                    outcome="failed",
                    reason="Internal error",
                    duration_ms=duration,
                )
            )
        result = internal_error("Internal error")
        result["correlation_id"] = correlation_id
        return result
