import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import {
  buildModel,
  loadDashboard,
  renderText,
  renderHtml,
} from '../src/dashboard.js';
import { writeStatus } from '../src/statusFile.js';
import type { WatchdogStatus } from '../src/types.js';

const NOW = Date.parse('2026-08-20T22:00:00Z');

const status = (over: Partial<WatchdogStatus> = {}): WatchdogStatus => ({
  schemaVersion: 1,
  projectSlug: 'demo',
  generatedAt: '2026-08-20T22:00:00.000Z',
  state: 'healthy',
  config: { heartbeatMinutes: 5, loopRepeats: 3 },
  tasks: [
    { taskId: 'task-1', agentId: 'software-developer-1', latestStatus: 'in-progress', latestCycle: 2, requirement: 'AC-1', blocker: '' },
  ],
  signals: [],
  lastEventAt: '2026-08-20T21:59:00.000Z',
  minutesSinceLastEvent: 1,
  ...over,
});

describe('buildModel', () => {
  it('computes maxCycle and sorts projects by slug', () => {
    const m = buildModel(
      [
        { slug: 'zeta', status: status({ tasks: [{ taskId: 't', agentId: 'a', latestStatus: 'done', latestCycle: 5, requirement: '', blocker: '' }] }), cycleBudget: 12 },
        { slug: 'alpha', status: status(), cycleBudget: null },
      ],
      NOW,
    );
    expect(m.projects.map((p) => p.slug)).toEqual(['alpha', 'zeta']);
    expect(m.projects[1]!.maxCycle).toBe(5);
    expect(m.generatedAt).toBe('2026-08-20T22:00:00.000Z');
  });
});

describe('renderText', () => {
  it('renders projects, tasks, budget burn and signals', () => {
    const m = buildModel(
      [
        {
          slug: 'demo',
          status: status({
            state: 'thrashing',
            signals: [{ kind: 'thrashing', agentId: 'software-developer-1', detail: 'looped 3x' }],
          }),
          cycleBudget: 12,
        },
      ],
      NOW,
    );
    const out = renderText(m);
    expect(out).toContain('demo — THRASHING');
    expect(out).toContain('cycle 2/12');
    expect(out).toContain('task-1 [AC-1]: in-progress');
    expect(out).toContain('thrashing(software-developer-1)');
  });

  it('shows budget burn without a cap when unknown', () => {
    const m = buildModel([{ slug: 'demo', status: status(), cycleBudget: null }], NOW);
    expect(renderText(m)).toContain('cycle 2');
    expect(renderText(m)).not.toContain('cycle 2/');
  });

  it('handles the empty and no-tasks cases', () => {
    expect(renderText(buildModel([], NOW))).toContain('no watchdog-status.json');
    const m = buildModel([{ slug: 'empty', status: status({ tasks: [] }), cycleBudget: null }], NOW);
    expect(renderText(m)).toContain('no tasks yet');
  });
});

describe('renderHtml', () => {
  it('produces a self-contained, theme-aware page', () => {
    const m = buildModel([{ slug: 'demo', status: status(), cycleBudget: 12 }], NOW);
    const html = renderHtml(m, 15);
    expect(html.startsWith('<!doctype html>')).toBe(true);
    expect(html).toContain('prefers-color-scheme: dark');
    expect(html).toContain('content="15"'); // meta refresh
    expect(html).toContain('demo');
    expect(html).toContain('b-healthy');
    expect(html).not.toContain('http://'); // no external resources
  });

  it('escapes HTML-special characters from the data', () => {
    const m = buildModel(
      [
        {
          slug: 'demo',
          status: status({
            tasks: [{ taskId: 't<x>', agentId: 'a', latestStatus: 'blocked', latestCycle: 1, requirement: 'AC & B', blocker: '"boom"' }],
          }),
          cycleBudget: null,
        },
      ],
      NOW,
    );
    const html = renderHtml(m);
    expect(html).toContain('t&lt;x&gt;');
    expect(html).toContain('AC &amp; B');
    expect(html).toContain('&quot;boom&quot;');
  });

  it('shows an empty-state message with no projects', () => {
    expect(renderHtml(buildModel([], NOW))).toContain('No watchdog-status.json');
  });

  it('renders signals and the no-tasks row for a stuck project', () => {
    const m = buildModel(
      [
        {
          slug: 'demo',
          status: status({
            state: 'stuck',
            tasks: [],
            signals: [{ kind: 'stuck', agentId: 'run', detail: 'no event for 12 min' }],
          }),
          cycleBudget: null,
        },
      ],
      NOW,
    );
    const html = renderHtml(m);
    expect(html).toContain('no tasks yet');
    expect(html).toContain('sig-stuck');
    expect(html).toContain('no event for 12 min');
  });
});

describe('loadDashboard', () => {
  let root: string;
  beforeEach(() => {
    root = mkdtempSync(join(tmpdir(), 'scrum-dash-'));
  });
  afterEach(() => {
    rmSync(root, { recursive: true, force: true });
  });

  it('aggregates every project under a .scrum root and reads budgets', () => {
    const a = join(root, 'proj-a');
    const b = join(root, 'proj-b');
    mkdirSync(a, { recursive: true });
    mkdirSync(b, { recursive: true });
    writeStatus(join(a, 'watchdog-status.json'), status({ projectSlug: 'proj-a' }));
    writeStatus(join(b, 'watchdog-status.json'), status({ projectSlug: 'proj-b', state: 'stuck' }));
    writeFileSync(join(a, 'plan.md'), 'Cycle budget: cap 9');
    // b has no plan.md → null budget
    const m = loadDashboard(root, NOW);
    expect(m.projects.map((p) => p.slug)).toEqual(['proj-a', 'proj-b']);
    expect(m.projects[0]!.cycleBudget).toBe(9);
    expect(m.projects[1]!.cycleBudget).toBeNull();
  });

  it('treats a single project dir (status file at root) as one project', () => {
    writeStatus(join(root, 'watchdog-status.json'), status({ projectSlug: 'solo' }));
    const m = loadDashboard(root, NOW);
    expect(m.projects).toHaveLength(1);
    expect(m.projects[0]!.slug).toBe(root.split(/[\\/]/).pop());
  });

  it('returns an empty model when the root does not exist', () => {
    expect(loadDashboard(join(root, 'nope'), NOW).projects).toEqual([]);
  });

  it('ignores subdirectories without a status file', () => {
    mkdirSync(join(root, 'not-a-project'), { recursive: true });
    expect(loadDashboard(root, NOW).projects).toEqual([]);
  });
});
