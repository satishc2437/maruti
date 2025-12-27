# Agent-Builder

Agent-Builder creates new Copilot Agent-mode “agents” as complete, drop-in packages.

It is designed to behave like a practical clone of Copilot’s tool-using Agent workflow (plan → gather context → ask targeted questions → write files → sanity-check), but scoped specifically to **designing and generating agent packages**.

## What it Produces

For each new agent request, Agent-Builder generates exactly three files under:

- `agents/{artifact-name}/`
  - `{artifact-name}.agent.md`
  - `{artifact-name}-internals/rules.json`
  - `ReadMe.md`

## How to Use

1. Ask Agent-Builder to create a new agent.
2. It will start by asking which archetype you want:
   - Organizational Role
   - Artifact-Authoring
   - Process / Orchestration
   - Tool-Specific Companion
3. Answer the short interview questions.
4. Confirm assumptions and tool access.
5. Agent-Builder writes the three required outputs.

## Design Decisions (Rationale)

- **Archetype-first workflow**: Prevents “prompt soup” and ensures the resulting agent has coherent incentives, scope, and deliverables.
- **Least privilege by default**: The included access model focuses writes into `agents/**` and `.github/agents/**` only.
- **Confirmation before writing**: The agent should pause for explicit user confirmation prior to emitting new agent packages.
- **Operational clone behavior, scoped domain**: It mirrors the practical Copilot pattern (plan, context gathering, tool use) but stays constrained to agent package generation instead of modifying application/tool code.

## Tooling and Permissions

The agent is intended to use the following tool categories:

- Allowed: `read`, `search`, `web`, `todo`, `edit`, `vscode`, `agent`, `docker-mcp/*`
- Prohibited (by default): terminal execution and direct system-level operations (e.g., SSH/SCP)

See `agent-builder-internals/rules.json` for the explicit policy.

In multi-root workspaces, access is **repo-scoped**: the rules file is interpreted relative to the repository root that contains the agent package (so each repo can safely have its own `.github/` and agent set).

### `rules.json` keywords (v1)

- `base`: where patterns are evaluated from (`repo` | `package` | `workspace` | `absolute`).
- `fs`: filesystem rules (read vs readWrite) using `allow`/`deny` glob patterns.
- `semantics`: deterministic evaluation switches (e.g., `denyOverridesAllow`, `readWriteImpliesRead`).

## User Preference Alignment

This Agent-Builder is designed to:

- Move quickly with pragmatic defaults, but **never silently**—it summarizes assumptions before writing.
- Avoid scope creep (no extra files beyond the required three).
- Keep changes localized to the agent package output directory.

## Non-Goals

- Shipping or modifying production code.
- Managing infrastructure or credentials.
- Creating multiple alternative drafts in the repo (it should generate one final package per confirmed design).
