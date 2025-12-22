"""Phase 1 smoke tests for github-app-mcp."""

from __future__ import annotations

import json

import pytest
from github_app_mcp.server import list_resources, list_tools


@pytest.mark.asyncio
async def test_server_lists_tools_non_empty() -> None:
    tools = await list_tools()
    assert len(tools) > 0


@pytest.mark.asyncio
async def test_server_lists_resources_ok() -> None:
    resources = await list_resources()
    assert isinstance(resources, list)


@pytest.mark.asyncio
async def test_tools_do_not_emit_secrets_in_metadata() -> None:
    tools = await list_tools()
    as_json = json.dumps([t.model_dump() for t in tools], sort_keys=True)

    # Basic guardrails for obvious token markers.
    assert "ghp_" not in as_json
    assert "github_pat_" not in as_json
    assert "Bearer " not in as_json
