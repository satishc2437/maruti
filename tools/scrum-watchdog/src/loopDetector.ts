/**
 * Loop / thrashing detector.
 *
 * Mechanical thrashing shows up as the *same* signature recurring: an agent
 * repeating the same `(action, target, result)` tuple, or re-emitting the same
 * "still doing X / still blocked on Y" work-log state cycle after cycle without
 * the text changing. We hash each observation to a signature string and flag
 * when any one signature occurs at least `k` times.
 */

import type { StreamEvent, WorkLogEntry } from './types.js';

export interface ThrashResult {
  thrashing: boolean;
  /** The signature that recurred the most. */
  signature: string;
  /** How many times that signature occurred. */
  count: number;
}

function normalize(s: string): string {
  return s.replace(/\s+/g, ' ').trim().toLowerCase();
}

/** Signature for a work-log entry: identity + status + the volatile detail text. */
export function workLogSignature(e: WorkLogEntry): string {
  return [
    e.agentId,
    e.taskId,
    e.status,
    normalize(e.doing),
    normalize(e.blockers),
  ].join('|');
}

/** Signature for a stream event: the (action, target, result) tuple. */
export function streamSignature(e: StreamEvent): string {
  return [normalize(e.action), normalize(e.target), normalize(e.result)].join('|');
}

/**
 * Detect thrashing over a sequence of signatures.
 *
 * Flags when the most frequent signature occurs `>= k` times. `k` is clamped to
 * a minimum of 2 (a single occurrence can never be a loop). An empty input is
 * never thrashing.
 */
export function detectThrashing(signatures: string[], k: number): ThrashResult {
  const threshold = Math.max(2, Math.floor(k));
  const counts = new Map<string, number>();
  let topSig = '';
  let topCount = 0;

  for (const sig of signatures) {
    const next = (counts.get(sig) ?? 0) + 1;
    counts.set(sig, next);
    if (next > topCount) {
      topCount = next;
      topSig = sig;
    }
  }

  return {
    thrashing: topCount >= threshold,
    signature: topSig,
    count: topCount,
  };
}
