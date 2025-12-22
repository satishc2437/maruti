# Contracts: github-app-mcp

**Feature**: `002-github-app-mcp`
**Date**: 2025-12-22

This feature adds a new MCP server tool. There are no new HTTP APIs exposed by this repository.

## External API Contracts

- **New/changed HTTP APIs**: N/A (this is an MCP server over stdio)
- **New/changed GraphQL schema**: N/A

## MCP Contracts

The MCP contract for this tool is defined by the allow-listed tool names, input schemas, and output guarantees.

- Tool contract reference: `mcp-contracts.json`

Key contract constraints:

- Tools accept only high-level intent and do not provide arbitrary GitHub API passthrough.
- Secrets (private keys, JWTs, installation tokens, installation identifiers) are never returned to agents.
- Every operation returns a `correlation_id` for audit traceability.
