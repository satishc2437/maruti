/**
 * Shared types for the Scrum watchdog.
 *
 * The watchdog observes the on-disk work-log stream that Scrum-cadence
 * orchestrators (dev-team, pm-team) maintain under `.scrum/<slug>/agents/*.md`,
 * plus an optional JSON-lines event stream, and rolls both up into a single
 * status object it can persist and a dashboard can render.
 */

/** Lifecycle status a work-log entry can carry (mirrors SCRUM-SCHEMA.md). */
export type WorkLogStatus =
  | 'in-progress'
  | 'blocked'
  | 'done'
  | 'observation';

/** A single parsed work-log entry from an `agents/<agentId>.md` file. */
export interface WorkLogEntry {
  /** Scrum cycle number this entry belongs to. */
  cycle: number;
  /** Task identifier (e.g. `task-2`, `review-cycle-3`, `cycle-1-observation`). */
  taskId: string;
  /** Persistent agent identity (e.g. `software-developer-1`). */
  agentId: string;
  /** Entry lifecycle status. */
  status: WorkLogStatus;
  /** ISO-8601 timestamp from the entry header, or null if unparseable. */
  timestamp: string | null;
  /** Epoch milliseconds for `timestamp`, or null if unparseable. */
  timestampMs: number | null;
  /** The `requirement` field (acceptance-criterion ref, e.g. `AC-1`, or `n/a`). */
  requirement: string;
  /** The `**Doing**` line body, trimmed, if present. */
  doing: string;
  /** The `**Blockers**` line body, trimmed, if present. */
  blockers: string;
}

/** A generic event from an optional JSON-lines stream (`--events` mode). */
export interface StreamEvent {
  /** ISO-8601 timestamp or epoch-ms number. */
  ts: string | number;
  /** What the agent did (e.g. a tool name). */
  action: string;
  /** What it acted on (e.g. a file path, a command). */
  target: string;
  /** The outcome (e.g. `ok`, `error`, an error message). */
  result: string;
}

/** Watchdog tunables. */
export interface WatchdogConfig {
  /** Heartbeat threshold: no new event for this many minutes → `stuck`. */
  heartbeatMinutes: number;
  /** Loop threshold: the same signature repeating this many times → `thrashing`. */
  loopRepeats: number;
}

/** Per-task rolled-up view. */
export interface TaskStatus {
  taskId: string;
  agentId: string;
  latestStatus: WorkLogStatus;
  latestCycle: number;
  requirement: string;
  /** Newest blocker text for this task, if the latest entry is blocked. */
  blocker: string;
}

/** A single flagged condition (heartbeat or loop). */
export interface Signal {
  kind: 'stuck' | 'thrashing';
  /** Agent identity the signal is about, or 'run' for run-wide (heartbeat). */
  agentId: string;
  /** Human-readable explanation. */
  detail: string;
}

/** The rolled-up status the watchdog writes and the dashboard renders. */
export interface WatchdogStatus {
  /** Schema version for forward compatibility. */
  schemaVersion: 1;
  /** The `<project-slug>` this status describes. */
  projectSlug: string;
  /** ISO-8601 time the status was computed. */
  generatedAt: string;
  /** Overall run state derived from the signals + task states. */
  state: 'healthy' | 'stuck' | 'thrashing' | 'idle' | 'complete';
  /** The config thresholds in effect. */
  config: WatchdogConfig;
  /** Per-task roll-up. */
  tasks: TaskStatus[];
  /** Active signals (empty when healthy/complete). */
  signals: Signal[];
  /** Newest event timestamp observed (ISO-8601), or null if none. */
  lastEventAt: string | null;
  /** Minutes since the newest event, or null if none. */
  minutesSinceLastEvent: number | null;
}
