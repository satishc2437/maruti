# Agent Memory MCP Tool – Specification

## Tool Name

`agent-memory`

## Purpose

`agent-memory` is a deterministic **Memory Control Plane** for AI agents.

It provides a **structured, versioned, repository-backed memory system** that enables:

* Persistent agent context across sessions
* Deterministic writes and reads
* Schema enforcement
* Reuse across multiple repositories and projects

This tool deliberately separates:

* **Reasoning** (LLMs / agents)
* **Persistence** (this MCP tool)
* **Judgment** (human-in-the-loop)

---

## Design Principles

1. **Deterministic**

   * No probabilistic behavior
   * No implicit writes
   * No auto-summarization

2. **Schema-Enforced**

   * All memory follows a declared structure
   * Invalid writes are rejected

3. **Repo-Local Storage**

   * Memory lives inside the consuming Git repository
   * Git is the system of record

4. **Agent-Safe**

   * Agents may read memory freely
   * Agents may only write via explicit tool calls

5. **Human-Controlled**

   * The tool persists memory
   * Humans decide what becomes durable knowledge

---

## Repository Contract

Each consuming repository MUST contain (or allow creation of):

```
.github/
└─ agent-memory/
   └─ <agent-name>/
      ├─ logs/
      │  └─ YYYY-MM-DD.md
      ├─ _summary.md
      └─ _schema.md
```

If files or folders are missing, the tool MAY create them.

---

## Memory Schema

### `_schema.md`

The schema defines the **required structure** of all session logs.

Default schema version: **v1**

```
# Agent Memory Schema v1

## Header
- Agent Name
- Date (YYYY-MM-DD)
- Session ID

## Context
- Project
- Focus Area
- Stage

## Discussion Summary
- Key topics discussed

## Decisions
- Explicit decisions made

## Open Questions
- Unresolved issues or risks

## Next Actions
- Follow-up actions
```

The MCP tool MUST validate all writes against this schema.

---

## Capabilities

### 1. `start_session`

**Description**
Creates or opens a session log for an agent on a given date.

**Inputs**

| Field        | Type                | Required | Description                                 |
| ------------ | ------------------- | -------- | ------------------------------------------- |
| `agent_name` | string              | yes      | Logical agent identifier (e.g. `aristotle`) |
| `repo_root`  | string              | yes      | Absolute path to repository root            |
| `date`       | string (YYYY-MM-DD) | no       | Defaults to current date                    |

**Behavior**

* Ensures `.github/agent-memory/<agent_name>/logs/` exists
* Creates `YYYY-MM-DD.md` if missing
* Inserts schema-compliant header for new files
* Does NOT overwrite existing content

**Returns**

```
{
  "session_file": "path/to/YYYY-MM-DD.md",
  "created": true | false
}
```

---

### 2. `append_entry`

**Description**
Appends structured content to a specific section of the session log.

**Inputs**

| Field        | Type                | Required |
| ------------ | ------------------- | -------- |
| `agent_name` | string              | yes      |
| `repo_root`  | string              | yes      |
| `date`       | string (YYYY-MM-DD) | no       |
| `section`    | enum                | yes      |
| `content`    | string              | yes      |

Allowed `section` values:

* Context
* Discussion Summary
* Decisions
* Open Questions
* Next Actions

**Behavior**

* Validates section against schema
* Appends content under the correct heading
* Never rewrites or deletes existing content
* Preserves chronological order

**Failure Conditions**

* Invalid section name
* Missing or invalid schema
* Malformed log file

---

### 3. `read_summary`

**Description**
Reads the canonical persistent summary for an agent.

**Inputs**

| Field        | Type   | Required |
| ------------ | ------ | -------- |
| `agent_name` | string | yes      |
| `repo_root`  | string | yes      |

**Behavior**

* Reads `_summary.md`
* If missing, MAY initialize from a template

**Returns**

```
{
  "summary": "markdown content"
}
```

---

### 4. `update_summary`

**Description**
Updates a specific section of the agent summary.

**Inputs**

| Field        | Type   | Required |
| ------------ | ------ | -------- |
| `agent_name` | string | yes      |
| `repo_root`  | string | yes      |
| `section`    | string | yes      |
| `content`    | string | yes      |
| `mode`       | enum   | yes      |

Allowed `mode` values:

* `append`
* `replace`

**Behavior**

* Updates only the targeted section
* Does not modify other sections
* Summary updates are explicit and intentional

---

### 5. `list_sessions`

**Description**
Lists existing session logs for an agent.

**Inputs**

| Field        | Type   | Required |
| ------------ | ------ | -------- |
| `agent_name` | string | yes      |
| `repo_root`  | string | yes      |
| `limit`      | number | no       |

**Returns**

```
{
  "sessions": [
    "2025-01-20.md",
    "2025-01-15.md"
  ]
}
```

Ordered newest → oldest.

---

## Error Handling

Errors MUST be explicit and non-destructive.

Example:

```
{
  "error": "InvalidSection",
  "message": "Section 'Thoughts' is not defined in schema"
}
```

No silent failures.

---

## Versioning

* Tool versioning: Semantic Versioning (e.g. `v1.0.0`)
* Schema version declared in `_schema.md`
* Schema version mismatches SHOULD emit warnings
* Backward compatibility is preferred

---

## Security Constraints

* No network access required
* No execution of repository code
* File access limited to `repo_root`
* No delete operations supported (by design)

---

## Explicit Non-Goals

This tool does NOT:

* Generate summaries automatically
* Interpret or reason about content
* Decide what is important
* Store memory outside the repository
* Replace human judgment

---

## Intended Usage Pattern

1. Agent session starts
2. Agent reads summary via `read_summary`
3. Human and agent reason together
4. Important outcomes are persisted via `append_entry`
5. Durable knowledge is curated into `_summary.md`

---

## Architectural Note

This tool is intentionally **boring and deterministic**.

That is a feature.

It provides a stable foundation upon which:

* Intelligent agents
* Agent SaaS platforms
* RAG systems
* Enterprise workflows

can be built safely and repeatedly.
