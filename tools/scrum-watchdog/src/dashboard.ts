/**
 * Synthesized status view.
 *
 * Rolls the per-project `watchdog-status.json` files up into one model and
 * renders it as a terminal table or a self-contained HTML page. The same
 * instrumentation serves the top-level lead's run and a dev-team sub-team's run
 * — every `.scrum/<slug>/` produces a status file, and the dashboard aggregates
 * whichever ones it finds under a root.
 */

import { existsSync, readdirSync, statSync } from 'node:fs';
import { basename, join } from 'node:path';

import type { WatchdogStatus } from './types.js';
import { readStatus, STATUS_FILENAME } from './statusFile.js';
import { readCycleBudget } from './plan.js';

export interface DashboardProject {
  slug: string;
  status: WatchdogStatus;
  /** Cycle budget from plan.md, or null if unknown. */
  cycleBudget: number | null;
  /** Highest cycle number observed across the project's tasks. */
  maxCycle: number;
}

export interface DashboardModel {
  generatedAt: string;
  projects: DashboardProject[];
}

function maxCycleOf(status: WatchdogStatus): number {
  return status.tasks.reduce((m, t) => Math.max(m, t.latestCycle), 0);
}

/** Build a model from already-loaded projects (pure; used by renderers/tests). */
export function buildModel(
  projects: Array<{ slug: string; status: WatchdogStatus; cycleBudget: number | null }>,
  nowMs: number,
): DashboardModel {
  return {
    generatedAt: new Date(nowMs).toISOString(),
    projects: projects
      .map((p) => ({ ...p, maxCycle: maxCycleOf(p.status) }))
      .sort((a, b) => a.slug.localeCompare(b.slug)),
  };
}

/**
 * Discover and load every `<slug>/watchdog-status.json` under a scrum root.
 *
 * If `root` itself holds a status file it is treated as a single project;
 * otherwise each immediate subdirectory that has one becomes a project.
 */
export function loadDashboard(root: string, nowMs: number): DashboardModel {
  const loaded: Array<{ slug: string; status: WatchdogStatus; cycleBudget: number | null }> = [];

  const tryDir = (dir: string): void => {
    const statusPath = join(dir, STATUS_FILENAME);
    if (existsSync(statusPath)) {
      loaded.push({
        slug: basename(dir),
        status: readStatus(statusPath),
        cycleBudget: readCycleBudget(dir),
      });
    }
  };

  if (existsSync(join(root, STATUS_FILENAME))) {
    tryDir(root);
  } else if (existsSync(root)) {
    for (const name of readdirSync(root)) {
      const full = join(root, name);
      if (statSync(full).isDirectory()) tryDir(full);
    }
  }

  return buildModel(loaded, nowMs);
}

function budgetBurn(p: DashboardProject): string {
  return p.cycleBudget === null ? `cycle ${p.maxCycle}` : `cycle ${p.maxCycle}/${p.cycleBudget}`;
}

const STATE_LABEL: Record<WatchdogStatus['state'], string> = {
  healthy: 'HEALTHY',
  stuck: 'STUCK',
  thrashing: 'THRASHING',
  idle: 'IDLE',
  complete: 'COMPLETE',
};

/** Render the model as a plain-text table for the terminal (minimal TUI). */
export function renderText(model: DashboardModel): string {
  const lines: string[] = [];
  lines.push(`Scrum status — ${model.projects.length} project(s) @ ${model.generatedAt}`);
  if (model.projects.length === 0) {
    lines.push('  (no watchdog-status.json found under the given root)');
    return lines.join('\n');
  }
  for (const p of model.projects) {
    lines.push('');
    lines.push(`▌ ${p.slug} — ${STATE_LABEL[p.status.state]} · ${budgetBurn(p)}`);
    if (p.status.tasks.length === 0) {
      lines.push('    (no tasks yet)');
    } else {
      for (const t of p.status.tasks) {
        const req = t.requirement ? ` [${t.requirement}]` : '';
        const blk = t.blocker ? ` — blocked: ${t.blocker}` : '';
        lines.push(`    ${t.taskId}${req}: ${t.latestStatus} (cycle ${t.latestCycle})${blk}`);
      }
    }
    for (const s of p.status.signals) {
      lines.push(`    ⚠ ${s.kind}(${s.agentId}): ${s.detail}`);
    }
  }
  return lines.join('\n');
}

function esc(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Render a self-contained, theme-aware HTML page. Includes a meta refresh so a
 * `dashboard --watch` that regenerates the file surfaces new events in-browser.
 */
export function renderHtml(model: DashboardModel, refreshSec = 10): string {
  const cards = model.projects
    .map((p) => {
      const tasks = p.status.tasks.length
        ? p.status.tasks
            .map(
              (t) => `<tr>
  <td>${esc(t.taskId)}</td>
  <td>${esc(t.requirement || '—')}</td>
  <td><span class="s s-${t.latestStatus}">${esc(t.latestStatus)}</span></td>
  <td>${t.latestCycle}</td>
  <td>${esc(t.blocker || '')}</td>
</tr>`,
            )
            .join('\n')
        : '<tr><td colspan="5" class="muted">no tasks yet</td></tr>';
      const signals = p.status.signals
        .map((s) => `<li class="sig sig-${s.kind}">${esc(s.kind)}(${esc(s.agentId)}): ${esc(s.detail)}</li>`)
        .join('\n');
      return `<section class="card">
  <header>
    <h2>${esc(p.slug)}</h2>
    <span class="badge b-${p.status.state}">${esc(STATE_LABEL[p.status.state])}</span>
    <span class="burn">${esc(budgetBurn(p))}</span>
  </header>
  <table>
    <thead><tr><th>Task</th><th>Criterion</th><th>Status</th><th>Cycle</th><th>Blocker</th></tr></thead>
    <tbody>
${tasks}
    </tbody>
  </table>
  ${signals ? `<ul class="signals">\n${signals}\n</ul>` : ''}
</section>`;
    })
    .join('\n');

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="${refreshSec}">
<title>Scrum Status</title>
<style>
  :root {
    --bg: #f6f7f9; --fg: #1a1d21; --muted: #6b7280; --card: #ffffff; --line: #e5e7eb;
    --healthy: #16a34a; --stuck: #d97706; --thrashing: #dc2626; --idle: #6b7280; --complete: #2563eb;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0d1117; --fg: #e6edf3; --muted: #9198a1; --card: #161b22; --line: #30363d;
      --healthy: #3fb950; --stuck: #d29922; --thrashing: #f85149; --idle: #8b949e; --complete: #58a6ff;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 24px; background: var(--bg); color: var(--fg);
    font: 14px/1.5 ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
  h1 { font-size: 18px; margin: 0 0 4px; }
  .meta { color: var(--muted); margin-bottom: 20px; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 10px;
    padding: 16px; margin-bottom: 16px; }
  .card header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
  .card h2 { font-size: 15px; margin: 0; }
  .badge { font-size: 11px; font-weight: 700; letter-spacing: .04em; padding: 2px 8px;
    border-radius: 999px; color: #fff; }
  .b-healthy { background: var(--healthy); } .b-stuck { background: var(--stuck); }
  .b-thrashing { background: var(--thrashing); } .b-idle { background: var(--idle); }
  .b-complete { background: var(--complete); }
  .burn { margin-left: auto; color: var(--muted); font-variant-numeric: tabular-nums; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); }
  th { color: var(--muted); font-weight: 600; font-size: 12px; }
  .muted { color: var(--muted); }
  .s { font-weight: 600; }
  .s-in-progress { color: var(--complete); } .s-blocked { color: var(--thrashing); }
  .s-done { color: var(--healthy); } .s-observation { color: var(--muted); }
  .signals { list-style: none; padding: 0; margin: 10px 0 0; }
  .sig { padding: 6px 10px; border-radius: 6px; margin-top: 6px; font-size: 13px; }
  .sig-stuck { background: color-mix(in srgb, var(--stuck) 18%, transparent); }
  .sig-thrashing { background: color-mix(in srgb, var(--thrashing) 18%, transparent); }
</style>
</head>
<body>
  <h1>Scrum Status</h1>
  <div class="meta">${model.projects.length} project(s) · generated ${esc(model.generatedAt)} · auto-refresh ${refreshSec}s</div>
${cards || '<p class="muted">No watchdog-status.json found under the given root.</p>'}
</body>
</html>
`;
}
