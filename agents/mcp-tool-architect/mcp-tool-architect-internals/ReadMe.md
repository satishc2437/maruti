# MCP-Tool-Architect

MCP-Tool-Architect is an **Organizational Role Agent** that guides and architects a new MCP tool from user requirements.

It behaves like a senior technical lead: it runs a tight discovery interview, defines contracts and non-functional requirements, and produces durable documentation that makes implementation straightforward and regression-resistant.

When the consuming environment provides spec-drafting or plan-drafting subagents, this agent delegates first-draft work to them and integrates the outputs into final docs. Otherwise it drafts single-handed.

## What It Produces

For each new tool, it writes exactly these documents under:

- `mcp-tools/{tool-name}/specs/product-docs/`

Outputs:
- `requirements.md` — goals/non-goals, use cases, interfaces, error taxonomy
- `engineering-guardrails.md` — testability, coverage guidance, error-handling, reliability, observability, regression prevention
- `success-criteria.md` — measurable acceptance criteria, quality gates, readiness checklist

## How to Use

Suggested prompt:
- “MCP-Tool-Architect: design an MCP tool for <problem>. Ask me for the target tech baseline, then produce the docs under `mcp-tools/<tool-name>/specs/product-docs/` and use any available drafting subagents.”

During the session it will:
1. Ask you to choose the target tech baseline (language/runtime) for this tool.
2. Ask whether any spec-drafting or plan-drafting subagents are available in your environment; if so, collect their exact names.
3. Invoke those subagents via the `agent` tool, or proceed single-handed if none are available.
4. Integrate and reconcile results into the three final docs.

## Design Decisions (Rationale)

- **Role = architect/guide**: You asked for an agent that leads and architects, not one that replaces drafting subagents.
- **Docs-only outputs**: The primary deliverables are requirement spec, engineering guardrails, and success criteria.
- **Drafting delegated when possible**: When subagents are available, drafting is delegated; this agent focuses on integration and decision-making. When they're not, the agent drafts single-handed and labels the output accordingly.
- **Regression resistance first**: Guardrails emphasize testability, error handling, and coverage focused on critical branches.
- **Least-privilege writes**: Write access is restricted to the required documentation path.

## Tooling and Permissions

Allowed tools (by design):
- `read`, `search`: inspect repo patterns and existing MCP tool structures.
- `edit`: write the docs in the required folder.
- `todo`: track multi-step work.
- `agent`: invoke available drafting subagents.
- `web` (optional): consult public docs when necessary; summarize rather than quoting.

See `mcp-tool-architect-internals/rules.json` for the enforced filesystem policy.

### `rules.json` summary

- Read allowed:
  - `README.md`, `MCP_DEVELOPMENT_WORKFLOW.md`, `pyproject.toml`
  - `agents/**`, `mcp-tools/**`, `spec/**`, `specs/**`
- Write allowed:
  - `mcp-tools/*/specs/product-docs/**`
  - `agents/mcp-tool-architect/**`

If you want MCP-Tool-Architect to scaffold code (not just docs), expand write permissions accordingly.
