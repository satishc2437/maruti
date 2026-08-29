# Project Lead — Memory & Requirements Schema

This document is the binding reference for the on-disk artifacts the Project Lead
maintains. It defines: the `.project-memory/` wiki layout and conventions, the
official `docs/requirements/` documents, the requirement lifecycle and approval
contract, and the GitHub Project / issue mapping. The `project-lead` skill and
the `Project-Lead` Copilot agent both implement exactly what is described here.

Two design rules hold everywhere:

1. **The repo is canonical for requirements.** Requirement documents live in
   `docs/requirements/` (versioned, PR-reviewable). `.project-memory/` only
   *references* them — it never becomes a second source of truth.
2. **The Lead owns the bookkeeping.** It writes and maintains every file under
   `.project-memory/`; the human curates sources, makes decisions, and approves.

---

## 1. Project Memory (`.project-memory/`)

A pure-markdown, Obsidian-readable compounding wiki. Open the folder in Obsidian
to browse the graph, follow `[[wikilinks]]`, and inspect the Lead's work.

```
.project-memory/
├── schema.md                  # conventions + workflows the Lead follows (this file, distilled, lives here in-repo)
├── index.md                   # content catalog: every page + 1-line summary, grouped by category
├── log.md                     # append-only chronology of events
├── overview.md                # the evolving project thesis / current-state synthesis
├── project-link.md            # the linked GitHub Project: number, URL, status-field + option IDs
├── requirements-register.md   # tracking index that REFERENCES docs/requirements/* + issues + Project items
└── wiki/
    ├── initiatives/           # one page per initiative/epic (links requirements → specs → issues → PRs)
    ├── decisions/             # decision records (what/why/alternatives/date)
    ├── architecture/          # accumulated system & architecture knowledge
    ├── stakeholders/          # stakeholder context, preferences, communication notes
    ├── risks/                 # risks and open questions
    └── glossary/              # domain terms
```

### Conventions

- **Wikilinks:** cross-reference pages with `[[wiki/initiatives/duplicate-detection]]`
  style links so Obsidian's graph view works.
- **Frontmatter:** every wiki page carries YAML frontmatter with at least
  `title`, `tags`, `created`, `updated` so Dataview queries work.
- **`index.md`** is content-oriented — a catalog the Lead reads first to find
  relevant pages, updated on every ingest.
- **`log.md`** is chronological and append-only. Every entry starts with a
  consistent prefix so it is greppable:

  ```
  ## [YYYY-MM-DD] <event> | <subject>
  ```

  where `<event>` ∈ `ingest | requirement | approval | handoff | sync | delivery | lint | decision`.

- **`overview.md`** holds the current synthesis: what the project is, where it
  stands, the active initiatives, and the near-term plan. Rewritten as the
  project evolves rather than appended to.

### Workflows

- **Ingest.** When the stakeholder shares a doc, decision, or context, the Lead
  reads it, files/updates the relevant wiki page(s), updates `index.md`, and
  appends a `log.md` entry. A single ingest may touch several pages
  (initiative + decision + risk + glossary).
- **Query.** To answer a stakeholder question, the Lead reads `index.md`, drills
  into relevant pages, and synthesizes an answer with citations to page paths.
  Valuable answers are filed back as new pages so explorations compound.
- **Lint.** On `/project-lead lint`, the Lead health-checks the wiki:
  contradictions between pages, stale claims superseded by newer info, orphan
  pages with no inbound links, important concepts lacking a page, missing
  cross-references. It reports findings and proposes fixes.

### `project-link.md` format

```markdown
# GitHub Project Link

- owner: <org-or-user>
- project_number: <N>
- project_url: https://github.com/orgs/<owner>/projects/<N>
- project_id: <PVT_...>            # GraphQL node id
- status_field_id: <PVTSSF_...>    # the single-select Status field
- status_options:
    Intake: <option-id>
    "In Review": <option-id>
    "Ready for Spec": <option-id>
    "In Spec": <option-id>
    "Ready for Dev": <option-id>
    "In Dev": <option-id>
    "In Review (Dev)": <option-id>
    Done: <option-id>
    Parked: <option-id>
- requirement_issue_type: <Requirement | label:requirement>   # detected capability
```

---

## 2. Requirements (`docs/requirements/` — official repo docs)

```
docs/requirements/
├── README.md                 # the official register: table of all requirements + status + links
├── _template.md              # the requirement doc template (scaffolded at bootstrap)
└── REQ-001-<slug>.md         # one official document per requirement
```

### Requirement document schema

Each `REQ-NNN-<slug>.md` is YAML frontmatter + body:

```markdown
---
id: REQ-001
title: <short title>
status: draft            # draft | in-review | approved | in-spec | specced | in-delivery | delivered | parked
priority: P2             # P0 | P1 | P2 | P3
version: 1
created: YYYY-MM-DD
updated: YYYY-MM-DD
approved_at:             # set when the requirement PR merges (or express signoff)
approved_by:             # stakeholder identity
requirement_issue:       # GitHub Requirement issue URL
links:
  requirement_pr:        # the PR that introduced/changed this doc (backfilled after `gh pr create`)
  project_item:          # GitHub Project item node id (PVTI_...) — Projects v2 items have no stable web URL
  initiative:            # [[wiki/initiatives/...]] in project memory
  specs: []              # spec PR(s) / docs/specs paths (filled by pm-team)
  child_issues: []       # Feature/Story sub-issues (filled after spec merge)
  prs: []                # dev-team PRs
---

## Problem / Context
<why this matters; the situation today>

## Desired outcome (goal)
<what "better" looks like>

## Scope — in
<what this requirement covers>

## Scope — out (non-goals)
<explicit exclusions>

## Acceptance / success criteria
<testable, verifiable criteria — the heart of the document>

## Constraints & assumptions
<technical, business, time, dependency constraints; assumptions made>

## Open questions
<unresolved items; must be empty before approval>

## Change log
- [YYYY-MM-DD] v1 — created (draft).
```

`docs/requirements/README.md` (the register) is a table the Lead keeps current:

```markdown
# Requirements Register

| ID | Title | Status | Priority | Approved | Requirement issue | Doc |
|----|-------|--------|----------|----------|-------------------|-----|
| REQ-001 | ... | approved | P1 | 2026-06-21 | #12 | [doc](REQ-001-....md) |
```

### Numbering

`REQ-NNN` is zero-padded, monotonically increasing, never reused. The Lead
derives the next number by scanning existing `docs/requirements/REQ-*.md`.

---

## 3. Requirement lifecycle

```
draft ──► in-review ──►(APPROVAL GATE)──► approved
   ──► in-spec ──► specced ──► in-delivery ──► delivered
                          (parked at any point, with a reason logged)
```

| Status | Meaning | Who advances it |
|---|---|---|
| `draft` | Captured, still being shaped | Lead |
| `in-review` | Meets Definition of Ready; requirement PR open for stakeholder review | Lead opens; stakeholder reviews |
| `approved` | Stakeholder approved (PR merged or express signoff) | Stakeholder action, Lead stamps |
| `in-spec` | Handed to pm-team; spec in progress | Lead, on `/pm-team` launch |
| `specced` | Spec PR merged; Feature/Story issues seeded | Lead, after spec merge |
| `in-delivery` | dev-team building one or more child issues | Lead, on `/dev-team` |
| `delivered` | All children done; verified against acceptance criteria | Lead, at acceptance |
| `parked` | Deferred; reason in Change log | Lead, on stakeholder direction |

### Definition of Ready (DoR)

A requirement may only move to `in-review` (i.e., be put up for approval) when
ALL of the following hold:

- [ ] Clear problem statement and desired outcome.
- [ ] **Testable** acceptance / success criteria.
- [ ] Explicit scope **in** and **out** (non-goals).
- [ ] Known constraints & assumptions recorded.
- [ ] No blocking open questions remain.

The Lead checks the DoR explicitly before opening a requirement PR.

---

## 4. Approval gate (the contract)

This is the boundary that protects pm-team from half-baked input.

- **Primary, official approval = a requirement PR.** The Lead writes/updates
  `docs/requirements/REQ-NNN.md` on a branch
  (`users/<you>/requirements/REQ-NNN-<slug>`), commits, and opens a PR titled
  `[REQ-NNN] <title>`. The stakeholder reviews and **approves/merges**. The merge
  is the auditable signoff.
- **Express signoff** (for tiny edits or when a PR is overkill): an explicit
  in-chat "approved" that the Lead records. Even then the Lead updates the doc
  frontmatter (`status`, `approved_at`, `approved_by`), the register, and
  `log.md`.
- On approval the Lead:
  1. Sets `status: approved`, stamps `approved_at` / `approved_by`, bumps the
     Change log.
  2. Creates the **Requirement issue** (see §5) and records its URL in the doc.
  3. Updates `docs/requirements/README.md` and `.project-memory/requirements-register.md`.
  4. Moves the Project item to **Ready for Spec**.
- **Hard rule:** the Lead **MUST NOT** launch or recommend `/pm-team` for a
  requirement whose status is not `approved`.
- **Change control:** any change to an `approved` (or later) requirement re-opens
  it to `in-review` via a **new requirement PR**, and requires re-approval before
  pm-team re-engages. The Change log records the version bump and the reason.
- **Acceptance signoff (optional closure):** when dev-team has delivered all
  child issues, the Lead verifies the result against the doc's acceptance
  criteria and offers the stakeholder a closing acceptance signoff before
  setting `delivered`.

---

## 5. GitHub mapping (leveraging native concepts)

### Requirement issue

Each requirement is represented by exactly one **Requirement issue**:

- **Preferred:** the org's custom **issue type "Requirement"**. Detect support
  via GraphQL (`organization.issueTypes`) or `gh issue create --type` capability.
- **Fallback:** a normal issue carrying a `requirement` label (bootstrap ensures
  the label exists).

The issue title is `[REQ-NNN] <title>`; its body links to the
`docs/requirements/REQ-NNN.md` doc and the requirement PR, and is the board item
for the requirement.

### Sub-issues for traceability

After the spec PR merges, pm-team seeds Feature/Story issues. The Lead makes them
**native sub-issues** of the Requirement issue, producing an end-to-end chain:

```
Requirement issue (REQ-001)
├── Feature issue (from pm-team)
│   ├── User Story issue ──► dev-team PR
│   └── User Story issue ──► dev-team PR
└── Feature issue ...
```

GitHub's Projects v2 rolls up child progress onto the Requirement item, so the
stakeholder sees completion at the requirement level on the Kanban.

### Project (v2) board

- One Project per repo (or per owner), linked in `project-link.md`.
- Single-select **Status** field with the funnel columns:
  **Intake → In Review → Ready for Spec → In Spec → Ready for Dev → In Dev → In
  Review (Dev) → Done** (plus **Parked**).
- Board items are the Requirement issues (with their sub-issues for roll-up).
  During early drafting a requirement may ride as a **draft item** until its
  Requirement issue exists, then it is converted/linked.

### Useful commands (reference)

```bash
# Projects
gh project list --owner <owner>                    # match by title first — create is NOT idempotent
gh project create --owner <owner> --title "<repo> Delivery"   # only when no matching title exists
gh project item-add <N> --owner <owner> --url <issue-url>     # response carries the item node id (PVTI_...)
gh project field-list <N> --owner <owner>          # discover Status field + option IDs
gh project item-edit --id <item-id> --field-id <status-field-id> \
  --project-id <project-id> --single-select-option-id <option-id>

# Issues / labels / types
gh label create requirement --description "Stakeholder requirement" --color 5319e7
gh issue create --title "[REQ-001] <title>" --body-file <body.md> --type Requirement
#   ^ --type works when the org has the custom "Requirement" issue type;
#     otherwise drop --type and add: --label requirement

# Sub-issues (native in gh >= ~2.9x): parent the Feature/Story under the Requirement
gh issue edit <requirement-issue> --add-sub-issue <child-issue>[,<child-issue>...]
#   or, equivalently, from the child:  gh issue edit <child> --parent <requirement-issue>
# Fallback for older gh: the GraphQL addSubIssue mutation.
```

The skill/agent contains the exact, current invocations; this section is a map,
not a frozen contract — the Lead adapts to the installed `gh` version and the
org's enabled features, always degrading to the documented fallback.

---

## 6. Distributed / multi-machine operation

When features are distributed across multiple agent sessions and machines, some
generated files merge cleanly and some do not. The rule is: **durable shared
knowledge is committed; ephemeral per-session / per-machine working state is
gitignored; and the one shared-but-append-only file uses a union merge.**
Bootstrap (§ mode: bootstrap, step 7) writes the `.gitignore` and `.gitattributes`
entries below.

### Committed (durable, shared) — all of `.project-memory/`

`overview.md`, `index.md`, `requirements-register.md`, `schema.md`,
`project-link.md`, and every page under `wiki/` are the project's brain and
record. Parallel sessions generally edit different pages, so conflicts are rare
and, when they occur, are real semantic merges to resolve by hand.
`project-link.md` holds platform/account-agnostic IDs (GraphQL node ids), not
machine-specific values, so it is safe to share.

### Gitignored (ephemeral, machine-local) — all of `.scrum/` (and `.worktrees/`)

The teams' Scrum working memory — per-agent session journals (which embed
**absolute worktree paths**), `plan.md`, `design.md`, `retrospective.md`,
`watchdog-status.json`, and the cross-project `lessons.md` — is scratch state for
one run on one machine. The deliverables of a run are its **PRs, issues, and
board items**; distributed runs coordinate through GitHub, not through `.scrum/`
files. `.gitignore` gets `.scrum/` and `.worktrees/`.

### Union-merged (shared but append-only) — `.project-memory/log.md`

The chronology is appended to by every session, which would conflict on every
merge. `.gitattributes` gets `.project-memory/log.md merge=union`, so git
concatenates both sides' entries instead of raising a conflict. Entries are
prefixed `## [YYYY-MM-DD] <event> | <subject>`; if union merge interleaves them
out of order, re-sort by date (identical duplicate lines collapse).

### Lessons stay useful without merging

Because raw `.scrum/lessons.md` is machine-local, cross-machine learning is
preserved by having the Lead **ingest notable lessons into `.project-memory/wiki/`**
(committed) rather than relying on the raw FIFO file.

### Keep the Lead single-writer where you can

By design the Lead is the **sole writer** of `.project-memory/` (Design rule 2).
If one Lead session coordinates while only `dev-team` / `pm-team` execution is
distributed, `.project-memory/` has a single writer and the union merge on
`log.md` is only a safety net. Running multiple concurrent Lead sessions against
the same wiki is supported by the rules above, but will occasionally require a
manual merge on the rewritten summary files (`overview.md`, `index.md`,
`requirements-register.md`).
