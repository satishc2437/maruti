/**
 * Core watchdog evaluation.
 *
 * `evaluate` is a pure function over already-parsed inputs so it is trivially
 * testable; `evaluateScrumDir` is the thin filesystem wrapper that reads a
 * `.scrum/<slug>/` directory and calls it.
 */

import { readdirSync, readFileSync, existsSync, statSync } from 'node:fs';
import { basename, join } from 'node:path';

import type {
  Signal,
  StreamEvent,
  TaskStatus,
  WatchdogConfig,
  WatchdogStatus,
  WorkLogEntry,
} from './types.js';
import { parseWorkLog } from './workLog.js';
import { checkHeartbeat } from './heartbeat.js';
import {
  detectThrashing,
  streamSignature,
  workLogSignature,
} from './loopDetector.js';

export interface EvaluateInput {
  projectSlug: string;
  /** Work-log entries keyed by agent identity (file order — newest first). */
  entriesByAgent: Map<string, WorkLogEntry[]>;
  /** Optional JSON-lines event stream (already parsed). */
  streamEvents?: StreamEvent[];
}

export const DEFAULT_CONFIG: WatchdogConfig = {
  heartbeatMinutes: 5,
  loopRepeats: 3,
};

function chronological(entries: WorkLogEntry[]): WorkLogEntry[] {
  return [...entries].sort((a, b) => {
    if (a.cycle !== b.cycle) return a.cycle - b.cycle;
    return (a.timestampMs ?? 0) - (b.timestampMs ?? 0);
  });
}

/** Newest entry per taskId, excluding orchestrator observation summaries. */
function rollUpTasks(all: WorkLogEntry[]): TaskStatus[] {
  const latest = new Map<string, WorkLogEntry>();
  for (const e of all) {
    if (e.status === 'observation') continue;
    const prev = latest.get(e.taskId);
    if (
      !prev ||
      e.cycle > prev.cycle ||
      (e.cycle === prev.cycle && (e.timestampMs ?? 0) >= (prev.timestampMs ?? 0))
    ) {
      latest.set(e.taskId, e);
    }
  }
  return [...latest.values()]
    .sort((a, b) => a.taskId.localeCompare(b.taskId))
    .map((e) => ({
      taskId: e.taskId,
      agentId: e.agentId,
      latestStatus: e.status,
      latestCycle: e.cycle,
      requirement: '',
      blocker: e.status === 'blocked' ? e.blockers : '',
    }));
}

function streamEventMs(e: StreamEvent): number | null {
  if (typeof e.ts === 'number') return Number.isFinite(e.ts) ? e.ts : null;
  const parsed = Date.parse(e.ts);
  return Number.isNaN(parsed) ? null : parsed;
}

/**
 * Evaluate a run's health from parsed inputs.
 *
 * @param input Parsed work-logs (+ optional stream events).
 * @param config Thresholds.
 * @param nowMs Epoch-ms of "now" (injected for deterministic tests).
 */
export function evaluate(
  input: EvaluateInput,
  config: WatchdogConfig,
  nowMs: number,
): WatchdogStatus {
  const allEntries: WorkLogEntry[] = [];
  for (const entries of input.entriesByAgent.values()) allEntries.push(...entries);
  const streamEvents = input.streamEvents ?? [];

  const tasks = rollUpTasks(allEntries);
  const hasWork = tasks.length > 0;
  const active = tasks.some(
    (t) => t.latestStatus === 'in-progress' || t.latestStatus === 'blocked',
  );

  // Newest event across every observable source.
  let lastEventMs: number | null = null;
  for (const e of allEntries) {
    if (e.timestampMs !== null && (lastEventMs === null || e.timestampMs > lastEventMs)) {
      lastEventMs = e.timestampMs;
    }
  }
  for (const e of streamEvents) {
    const ms = streamEventMs(e);
    if (ms !== null && (lastEventMs === null || ms > lastEventMs)) lastEventMs = ms;
  }

  const signals: Signal[] = [];

  // Heartbeat.
  const hb = checkHeartbeat(lastEventMs, nowMs, config.heartbeatMinutes, active);
  if (hb.stuck) {
    signals.push({
      kind: 'stuck',
      agentId: 'run',
      detail: `No new event for ${hb.minutesSinceLastEvent} min (threshold ${config.heartbeatMinutes} min).`,
    });
  }

  // Loop detection — per agent over its non-terminal work-log entries.
  for (const [agentId, entries] of input.entriesByAgent) {
    const sigs = chronological(entries)
      .filter((e) => e.status === 'in-progress' || e.status === 'blocked')
      .map(workLogSignature);
    const res = detectThrashing(sigs, config.loopRepeats);
    if (res.thrashing) {
      signals.push({
        kind: 'thrashing',
        agentId,
        detail: `Repeated the same state ${res.count}x (threshold ${config.loopRepeats}).`,
      });
    }
  }

  // Loop detection — over the optional stream, keyed by (action,target,result).
  if (streamEvents.length > 0) {
    const res = detectThrashing(streamEvents.map(streamSignature), config.loopRepeats);
    if (res.thrashing) {
      signals.push({
        kind: 'thrashing',
        agentId: 'stream',
        detail: `Repeated the same (action,target,result) ${res.count}x (threshold ${config.loopRepeats}).`,
      });
    }
  }

  const thrashing = signals.some((s) => s.kind === 'thrashing');
  const stuck = signals.some((s) => s.kind === 'stuck');

  let state: WatchdogStatus['state'];
  if (!hasWork) state = 'idle';
  else if (!active) state = 'complete';
  else if (thrashing) state = 'thrashing';
  else if (stuck) state = 'stuck';
  else state = 'healthy';

  return {
    schemaVersion: 1,
    projectSlug: input.projectSlug,
    generatedAt: new Date(nowMs).toISOString(),
    state,
    config,
    tasks,
    signals,
    lastEventAt: lastEventMs === null ? null : new Date(lastEventMs).toISOString(),
    minutesSinceLastEvent: hb.minutesSinceLastEvent,
  };
}

/** Read and parse every `agents/*.md` work-log under a `.scrum/<slug>/` dir. */
export function readAgentEntries(scrumDir: string): Map<string, WorkLogEntry[]> {
  const agentsDir = join(scrumDir, 'agents');
  const byAgent = new Map<string, WorkLogEntry[]>();
  if (!existsSync(agentsDir)) return byAgent;
  for (const name of readdirSync(agentsDir)) {
    if (!name.endsWith('.md')) continue;
    const full = join(agentsDir, name);
    if (!statSync(full).isFile()) continue;
    const agentId = basename(name, '.md');
    byAgent.set(agentId, parseWorkLog(readFileSync(full, 'utf8')));
  }
  return byAgent;
}

/** Parse a JSON-lines event stream file into `StreamEvent`s (skips bad lines). */
export function readStreamEvents(eventsPath: string): StreamEvent[] {
  if (!existsSync(eventsPath)) return [];
  const out: StreamEvent[] = [];
  for (const line of readFileSync(eventsPath, 'utf8').split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      const obj = JSON.parse(trimmed) as Partial<StreamEvent>;
      if (obj && typeof obj.action === 'string') {
        out.push({
          ts: obj.ts ?? 0,
          action: obj.action,
          target: typeof obj.target === 'string' ? obj.target : '',
          result: typeof obj.result === 'string' ? obj.result : '',
        });
      }
    } catch {
      // Skip malformed lines rather than crash the watch loop.
    }
  }
  return out;
}

/**
 * Read a `.scrum/<slug>/` directory and evaluate it.
 *
 * @param scrumDir Path to a single project's scrum dir (…/.scrum/<slug>).
 * @param config Thresholds.
 * @param nowMs Epoch-ms of "now".
 * @param eventsPath Optional JSON-lines stream to fold in.
 */
export function evaluateScrumDir(
  scrumDir: string,
  config: WatchdogConfig,
  nowMs: number,
  eventsPath?: string,
): WatchdogStatus {
  const entriesByAgent = readAgentEntries(scrumDir);
  const streamEvents = eventsPath ? readStreamEvents(eventsPath) : [];
  return evaluate(
    { projectSlug: basename(scrumDir), entriesByAgent, streamEvents },
    config,
    nowMs,
  );
}
