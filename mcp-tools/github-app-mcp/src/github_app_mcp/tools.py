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
}


@dataclass(frozen=True, slots=True)
class Runtime:
    """Per-server runtime dependencies shared across tool calls."""

    config: AppConfig
    audit: AuditLogger
    policy: Policy
    auth: GitHubAppAuth
    github: GitHubClient


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
        pr_only=config.policy.pr_only,
        protected_branch_patterns=config.policy.protected_branches,
    )
    auth = GitHubAppAuth(config=config)
    github = GitHubClient(token_provider=auth.get_installation_token, limits=config.limits)

    _RUNTIME = Runtime(config=config, audit=audit, policy=policy, auth=auth, github=github)
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
