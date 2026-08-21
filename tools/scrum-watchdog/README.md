# scrum-watchdog

A small, cross-platform **watchdog + loop detector** for Scrum-cadence agent runs
(`dev-team`, `pm-team`). It makes two failure classes impossible to sustain
silently:

- **Silent hangs** → `stuck`. If a run is still active but has emitted no new
  event for longer than a heartbeat threshold, it is flagged.
- **Mechanical thrashing** → `thrashing`. If a worker repeats the same
  `(action, target, result)` — or re-emits the same "still doing X / still
  blocked on Y" work-log state — at least `K` times, it is flagged.

On either trip it writes a rolled-up **status file** and emits a visible
notification. That status file is the signal the supervisor's standing
auto-intervention reads (mark the board item `Blocked`, halt the broad work,
re-scope to targeted validation — see the governance policies in the `dev-team`
and `project-lead` packages).

It is deliberately **not** a new runtime. It observes artifacts the orchestrators
already produce — the `.scrum/<slug>/agents/*.md` work-logs (a documented,
stable, plain-markdown contract) — plus an optional JSON-lines event stream.

## Why work-logs, not a live process stream

`dev-team` dispatches its `software-developer` / `code-reviewer` / `drift-critic`
workers as **in-session sub-agents** (the `Task` tool), not headless OS
processes, so there is no separate process to attach to. The workers' observable,
cross-platform surface is the `.scrum/<slug>/agents/*.md` work-log stream the
orchestrator writes every cycle. The watchdog tails that. If you *do* run workers
with a structured event stream, dump it to JSON-lines and pass `--events` to fold
`(action, target, result)` tuples into the same loop detection.

## Install / build

```bash
cd tools/scrum-watchdog
npm install --legacy-peer-deps    # --legacy-peer-deps works around an npm v11 arborist peer-resolution bug
npm run build
```

## Usage

```bash
# One-shot: evaluate, write status, print a summary. Exit code encodes state.
node dist/cli.js once .scrum/<slug> [options]

# Continuous: poll on an interval, notify on each state change, until Ctrl-C.
node dist/cli.js watch .scrum/<slug> [options]
```

Options:

| Flag | Default | Meaning |
|---|---|---|
| `--heartbeat-min <N>` | `5` | Stuck threshold in minutes (env `SCRUM_WATCHDOG_HEARTBEAT_MIN`). |
| `--loop-k <K>` | `3` | Thrashing threshold — same signature `K` times (min 2, env `SCRUM_WATCHDOG_LOOP_K`). |
| `--interval-sec <S>` | `20` | Poll interval for `watch` (env `SCRUM_WATCHDOG_INTERVAL_SEC`). |
| `--status-file <path>` | `<scrumDir>/watchdog-status.json` | Where to write the status JSON. |
| `--events <path>` | — | Optional JSON-lines event stream to fold in. |
| `--json` | off | Also print the full status JSON. |

`once` exit codes: **0** healthy/complete/idle, **2** stuck, **3** thrashing —
so it drops straight into a shell gate or CI step.

Thresholds `N` (heartbeat) and `K` (loop) are the tunable dials the plan calls
for; both have env-var fallbacks so a CI or a launcher can set them once.

## Status file shape

```jsonc
{
  "schemaVersion": 1,
  "projectSlug": "fix-login-typo",
  "generatedAt": "2026-08-20T22:00:00.000Z",
  "state": "thrashing",            // healthy | stuck | thrashing | idle | complete
  "config": { "heartbeatMinutes": 5, "loopRepeats": 3 },
  "tasks": [
    { "taskId": "task-1", "agentId": "software-developer-1",
      "latestStatus": "in-progress", "latestCycle": 3, "requirement": "", "blocker": "" }
  ],
  "signals": [
    { "kind": "thrashing", "agentId": "software-developer-1",
      "detail": "Repeated the same state 3x (threshold 3)." }
  ],
  "lastEventAt": "2026-08-20T21:59:00.000Z",
  "minutesSinceLastEvent": 1.0
}
```

The **status view** (a sibling tool) renders this file; observability is uniform
whether it describes the top-level lead's run or `dev-team`'s internal sub-team —
point the watchdog at any `.scrum/<slug>/` directory.

## Develop

```bash
npm test              # vitest
npm run test:coverage # enforces the coverage gate (lines/functions/statements >=95, branches >=90)
npm run dev -- once .scrum/<slug>   # run from TS without building
```

The pure logic (`workLog`, `loopDetector`, `heartbeat`, `watchdog`, `summary`,
`args`, `statusFile`) is fully unit-tested; `cli.ts` is the thin process wrapper.
