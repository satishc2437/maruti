/**
 * Best-effort reader for a project's `plan.md` — just enough to enrich the
 * dashboard with the cycle budget (for budget-burn), without imposing a rigid
 * schema on the orchestrator-authored plan.
 */

import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * Extract the cycle-budget cap from plan markdown, or null if not found.
 *
 * Looks for the first integer following a "Cycle budget" mention, matching the
 * plan format the Scrum orchestrators emit (e.g. "Cycle budget: the cap 12 …").
 */
export function parseCycleBudget(markdown: string): number | null {
  // Non-greedy across up to ~40 chars (incl. newlines) so "Cycle budget\n\nthe
  // cap 12" and "Cycle budget: 8" both resolve to the nearby number.
  const m = markdown.match(/cycle budget[\s\S]{0,40}?(\d+)/i);
  if (!m) return null;
  const n = Number.parseInt(m[1] as string, 10);
  return Number.isFinite(n) ? n : null;
}

/** Read `<scrumDir>/plan.md` and return its cycle budget, or null if absent. */
export function readCycleBudget(scrumDir: string): number | null {
  const p = join(scrumDir, 'plan.md');
  if (!existsSync(p)) return null;
  return parseCycleBudget(readFileSync(p, 'utf8'));
}
