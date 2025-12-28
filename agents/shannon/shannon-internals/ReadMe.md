# Shannon (Contracts & SDKs Owner)

This is the repo-scoped, deterministic Shannon agent package.

## Files

- `agents/shannon/shannon.agent.md`: the agent definition
- `agents/shannon-internals/rules.json`: deterministic access rules Shannon must follow
- `agents/shannon-internals/ReadMe.md`: this file

## Determinism

Shannon must load `rules.json` at session start and enforce it deterministically:

- Deny overrides allow
- If a path is not explicitly allowed, it is forbidden
- `readWrite` implies `read`
- Unknown top-level keys in `rules.json` are ignored (forward compatible)

## Notes

`base: "repo"` means patterns are evaluated relative to the repository root that contains this agent package.
