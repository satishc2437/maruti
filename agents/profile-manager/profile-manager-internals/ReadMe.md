# Profile-Manager

Profile-Manager is an **Organizational Role Agent** that helps you architect, design, and plan a professional personal website (About + Projects + Blog) suitable for sharing blog links on LinkedIn.

It behaves like a pragmatic website architect/product partner: it interviews quickly, proposes a few viable defaults (hosting/stack/content), records tradeoffs, and produces a small set of implementation-ready Markdown documents.

## What It Produces

It writes Markdown documents under:

- `spec/profile-website/`

Typical outputs (created as needed):
- `decisions.md` (options + tradeoffs + chosen defaults)
- `sitemap-ia.md` (navigation, URLs, page intents)
- `content-model.md` (projects + blog post schema)
- `architecture.md` (rendering/deploy model, content pipeline, permalink strategy)
- `seo-analytics-privacy.md`
- `launch-checklist.md`

## How to Use

1. Ask Profile-Manager what it needs to know about your goals/audience.
2. Review the 2–3 suggested defaults and pick one (or ask it to pick).
3. Confirm the chosen defaults.
4. Ask it to generate the design/architecture docs.

Suggested prompt:
- “Profile-Manager: brainstorm the best defaults for my personal site, then write the docs under `spec/profile-website/`.”

## Design Decisions (Rationale)

- **Brainstorm-first**: You asked to revisit earlier choices and have the agent propose defaults rather than locking in hosting/tech prematurely.
- **Docs-only**: The agent is intentionally not a scaffolding/build agent; it produces design and architecture artifacts only.
- **Stable blog permalinks**: The outputs emphasize URL strategy and canonical URLs so posts can be safely shared on LinkedIn.
- **Least privilege writes**: Write permissions are limited to `spec/**` only.

## Tooling and Permissions

- Allowed tools: `read`, `search`, `web`, `todo`, `edit`
- Prohibited by design: terminal execution, infra management, credential handling

See `profile-manager-internals/rules.json` for the enforced filesystem policy.

### `rules.json` summary

- Read: `**` (can read the repo)
- Write: `spec/**` only

If you want Profile-Manager to write somewhere else, update `rules.json` accordingly.
