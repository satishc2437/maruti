/**
 * Human-readable rendering of a {@link WatchdogStatus} for terminal output and
 * for deciding when a state transition is worth notifying about.
 */

import type { WatchdogStatus } from './types.js';

const ICON: Record<WatchdogStatus['state'], string> = {
  healthy: '✓',
  stuck: '⏳',
  thrashing: '🔁',
  idle: '·',
  complete: '✔',
};

/** A one-line summary suitable for a terminal or a notification. */
export function summarizeStatus(status: WatchdogStatus): string {
  const counts = status.tasks.reduce<Record<string, number>>((acc, t) => {
    acc[t.latestStatus] = (acc[t.latestStatus] ?? 0) + 1;
    return acc;
  }, {});
  const taskBits = Object.entries(counts)
    .map(([k, v]) => `${v} ${k}`)
    .join(', ');
  const head = `${ICON[status.state]} [${status.projectSlug}] ${status.state.toUpperCase()}`;
  const tasksPart = status.tasks.length ? ` — ${taskBits}` : ' — no tasks';
  const signalPart = status.signals.length
    ? ` | ${status.signals.map((s) => `${s.kind}(${s.agentId})`).join(', ')}`
    : '';
  return head + tasksPart + signalPart;
}

/**
 * Whether the transition from `prev` to `next` warrants a fresh notification.
 * True on first observation (no prev) or whenever the overall state changes or
 * the set of signals changes.
 */
export function stateChanged(
  prev: WatchdogStatus | null,
  next: WatchdogStatus,
): boolean {
  if (prev === null) return true;
  if (prev.state !== next.state) return true;
  const key = (s: WatchdogStatus): string =>
    s.signals
      .map((x) => `${x.kind}:${x.agentId}`)
      .sort()
      .join(',');
  return key(prev) !== key(next);
}
