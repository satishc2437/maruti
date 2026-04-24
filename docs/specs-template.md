# Spec template for MCP tools

This template defines the structure for spec documents that live under
`mcp-tools/<tool>/specs/`. Copy it into a tool's `specs/` directory and fill
it in for each meaningful change or feature (numbered `001-...md`, `002-...md`).

Keep specs **short, concrete, and durable**. A spec exists to capture
decisions; it is not a design journal.

---

## 1. Purpose

One-paragraph statement of what this spec covers and why. If the spec is for
a new capability, what user problem does it solve? If for a change, what was
wrong and what are we making right?

## 2. MCP Surface

The tool's public contract affected by this spec:

- **Tools exposed** — names, input schema (JSON Schema fragment OK), output
  schema, and what errors each can raise.
- **Resources exposed** (if any) — URIs, payload shape.
- **Breaking changes** — explicitly listed. None = say "None."

## 3. Safety & Limits

What this capability will and will not do:

- Input validation rules (path traversal, size limits, allowed schemes).
- Rate/size/time ceilings and how they're enforced.
- Secret-handling posture (never read, never log, never echo).
- Network/filesystem scope (least-privilege defaults).

## 4. Test Plan

How we'll know it works and stays working:

- Unit tests — which branches must be covered (including error paths).
- Contract tests — MCP tool I/O roundtrips.
- Integration tests — real external surfaces this touches (if any).
- Coverage target — per the repo constitution, ≥95% honest.

## 5. Open Questions

Anything you haven't decided. Leave this section in the file; future readers
need to know what was deferred. Delete only when every question is resolved.
