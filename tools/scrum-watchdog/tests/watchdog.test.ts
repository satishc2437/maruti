import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import {
  evaluate,
  evaluateScrumDir,
  readAgentEntries,
  readStreamEvents,
  DEFAULT_CONFIG,
  type EvaluateInput,
} from '../src/watchdog.js';
import type { WorkLogEntry } from '../src/types.js';

const NOW = Date.parse('2026-08-20T22:00:00Z');

const wl = (over: Partial<WorkLogEntry> = {}): WorkLogEntry => ({
  cycle: 1,
  taskId: 'task-1',
  agentId: 'software-developer-1',
  status: 'in-progress',
  timestamp: '2026-08-20T21:59:00Z',
  timestampMs: Date.parse('2026-08-20T21:59:00Z'),
  doing: 'work',
  blockers: 'none',
  ...over,
});

const input = (entriesByAgent: Map<string, WorkLogEntry[]>, streamEvents?: EvaluateInput['streamEvents']): EvaluateInput => ({
  projectSlug: 'demo',
  entriesByAgent,
  ...(streamEvents ? { streamEvents } : {}),
});

describe('evaluate', () => {
  it('is idle when there are no tasks', () => {
    const s = evaluate(input(new Map()), DEFAULT_CONFIG, NOW);
    expect(s.state).toBe('idle');
    expect(s.tasks).toEqual([]);
    expect(s.lastEventAt).toBeNull();
    expect(s.minutesSinceLastEvent).toBeNull();
  });

  it('is complete when every task is done', () => {
    const m = new Map([['software-developer-1', [wl({ status: 'done' })]]]);
    const s = evaluate(input(m), DEFAULT_CONFIG, NOW);
    expect(s.state).toBe('complete');
    expect(s.tasks[0]!.latestStatus).toBe('done');
  });

  it('is healthy when active and recent', () => {
    const m = new Map([['software-developer-1', [wl()]]]);
    const s = evaluate(input(m), DEFAULT_CONFIG, NOW);
    expect(s.state).toBe('healthy');
    expect(s.signals).toEqual([]);
  });

  it('takes the newest entry per task for the roll-up', () => {
    const m = new Map([
      [
        'software-developer-1',
        [
          wl({ cycle: 3, status: 'blocked', blockers: 'need token' }),
          wl({ cycle: 1, status: 'in-progress' }),
        ],
      ],
    ]);
    const s = evaluate(input(m), DEFAULT_CONFIG, NOW);
    expect(s.tasks[0]!.latestCycle).toBe(3);
    expect(s.tasks[0]!.latestStatus).toBe('blocked');
    expect(s.tasks[0]!.blocker).toBe('need token');
  });

  it('flags stuck when an active run has gone silent past the threshold', () => {
    const stale = Date.parse('2026-08-20T21:50:00Z'); // 10 min ago
    const m = new Map([
      ['software-developer-1', [wl({ timestampMs: stale, timestamp: '2026-08-20T21:50:00Z' })]],
    ]);
    const s = evaluate(input(m), { heartbeatMinutes: 5, loopRepeats: 3 }, NOW);
    expect(s.state).toBe('stuck');
    expect(s.signals.some((x) => x.kind === 'stuck')).toBe(true);
    expect(s.minutesSinceLastEvent).toBe(10);
  });

  it('flags thrashing when an agent repeats the same state k times', () => {
    const same = { doing: 'retry full-repo validation', blockers: 'tests red' };
    const m = new Map([
      [
        'software-developer-1',
        [
          wl({ cycle: 3, ...same }),
          wl({ cycle: 2, ...same }),
          wl({ cycle: 1, ...same }),
        ],
      ],
    ]);
    const s = evaluate(input(m), { heartbeatMinutes: 60, loopRepeats: 3 }, NOW);
    expect(s.state).toBe('thrashing');
    const sig = s.signals.find((x) => x.kind === 'thrashing');
    expect(sig?.agentId).toBe('software-developer-1');
  });

  it('does not count done/observation entries toward thrashing', () => {
    const same = { doing: 'x', blockers: 'y' };
    const m = new Map([
      [
        'software-developer-1',
        [wl({ cycle: 3, status: 'done', ...same }), wl({ cycle: 2, status: 'done', ...same })],
      ],
    ]);
    const s = evaluate(input(m), DEFAULT_CONFIG, NOW);
    expect(s.signals.some((x) => x.kind === 'thrashing')).toBe(false);
  });

  it('detects thrashing over a stream and uses stream ts for heartbeat', () => {
    const m = new Map<string, WorkLogEntry[]>([['software-developer-1', [wl()]]]);
    const events = [
      { ts: '2026-08-20T21:59:30Z', action: 'Bash', target: 'pytest', result: 'error' },
      { ts: '2026-08-20T21:59:40Z', action: 'Bash', target: 'pytest', result: 'error' },
      { ts: '2026-08-20T21:59:50Z', action: 'Bash', target: 'pytest', result: 'error' },
    ];
    const s = evaluate(input(m, events), { heartbeatMinutes: 60, loopRepeats: 3 }, NOW);
    expect(s.signals.some((x) => x.kind === 'thrashing' && x.agentId === 'stream')).toBe(true);
    expect(s.lastEventAt).toBe('2026-08-20T21:59:50.000Z');
  });

  it('detects thrashing even when entries carry no timestamps', () => {
    const same = { doing: 'a', blockers: 'b', timestamp: null, timestampMs: null };
    const m = new Map([
      [
        'software-developer-1',
        [wl({ cycle: 3, ...same }), wl({ cycle: 2, ...same }), wl({ cycle: 1, ...same })],
      ],
    ]);
    const s = evaluate(input(m), { heartbeatMinutes: 60, loopRepeats: 3 }, NOW);
    expect(s.state).toBe('thrashing');
    expect(s.lastEventAt).toBeNull();
  });

  it('accepts numeric and rejects non-finite stream timestamps', () => {
    const m = new Map<string, WorkLogEntry[]>();
    const events = [
      { ts: NOW - 1000, action: 'a', target: 't', result: 'r' },
      { ts: Number.NaN, action: 'b', target: 't', result: 'r' },
    ];
    const s = evaluate(input(m, events), DEFAULT_CONFIG, NOW);
    expect(s.lastEventAt).toBe(new Date(NOW - 1000).toISOString());
  });

  it('prioritizes thrashing over stuck in the single state field', () => {
    const stale = Date.parse('2026-08-20T21:40:00Z');
    const same = { doing: 'a', blockers: 'b' };
    const m = new Map([
      [
        'software-developer-1',
        [
          wl({ cycle: 3, timestampMs: stale, timestamp: '2026-08-20T21:40:00Z', ...same }),
          wl({ cycle: 2, timestampMs: stale, timestamp: '2026-08-20T21:40:00Z', ...same }),
          wl({ cycle: 1, timestampMs: stale, timestamp: '2026-08-20T21:40:00Z', ...same }),
        ],
      ],
    ]);
    const s = evaluate(input(m), { heartbeatMinutes: 5, loopRepeats: 3 }, NOW);
    expect(s.state).toBe('thrashing');
    expect(s.signals.some((x) => x.kind === 'stuck')).toBe(true);
    expect(s.signals.some((x) => x.kind === 'thrashing')).toBe(true);
  });
});

describe('filesystem helpers', () => {
  let dir: string;
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'scrum-wd-'));
  });
  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  const writeAgent = (agentId: string, status: string, ts: string, cycle = 1): void => {
    const agents = join(dir, 'agents');
    mkdirSync(agents, { recursive: true });
    writeFileSync(
      join(agents, `${agentId}.md`),
      `## [Cycle ${cycle}] task-1 · ${ts}\n\n- **agentId:** ${agentId}\n- **taskId:** task-1\n- **status:** ${status}\n\n### Details\n**Doing** — go\n**Blockers** — none\n`,
    );
  };

  it('readAgentEntries returns an empty map when there is no agents dir', () => {
    expect(readAgentEntries(dir).size).toBe(0);
  });

  it('reads agent entries and evaluates the dir', () => {
    writeAgent('software-developer-1', 'in-progress', '2026-08-20T21:59:00Z');
    const s = evaluateScrumDir(dir, DEFAULT_CONFIG, NOW);
    expect(s.projectSlug).toBe(dir.split(/[\\/]/).pop());
    expect(s.tasks).toHaveLength(1);
    expect(s.state).toBe('healthy');
  });

  it('ignores non-.md files in agents/', () => {
    writeAgent('software-developer-1', 'done', '2026-08-20T21:59:00Z');
    writeFileSync(join(dir, 'agents', 'notes.txt'), 'ignore me');
    expect(readAgentEntries(dir).size).toBe(1);
  });

  it('readStreamEvents parses JSONL and skips blank/bad lines', () => {
    const p = join(dir, 'events.jsonl');
    writeFileSync(
      p,
      [
        JSON.stringify({ ts: 1, action: 'a', target: 't', result: 'r' }),
        '',
        'not json',
        JSON.stringify({ noAction: true }),
        JSON.stringify({ action: 'b' }),
      ].join('\n'),
    );
    const events = readStreamEvents(p);
    expect(events).toHaveLength(2);
    expect(events[0]!.action).toBe('a');
    expect(events[1]!.target).toBe('');
  });

  it('readStreamEvents returns [] for a missing file', () => {
    expect(readStreamEvents(join(dir, 'nope.jsonl'))).toEqual([]);
  });

  it('evaluateScrumDir folds in a stream file when provided', () => {
    writeAgent('software-developer-1', 'in-progress', '2026-08-20T21:59:00Z');
    const p = join(dir, 'events.jsonl');
    writeFileSync(
      p,
      [
        JSON.stringify({ ts: '2026-08-20T21:59:10Z', action: 'x', target: 'y', result: 'z' }),
        JSON.stringify({ ts: '2026-08-20T21:59:20Z', action: 'x', target: 'y', result: 'z' }),
      ].join('\n'),
    );
    const s = evaluateScrumDir(dir, { heartbeatMinutes: 60, loopRepeats: 2 }, NOW, p);
    expect(s.signals.some((x) => x.agentId === 'stream')).toBe(true);
  });
});
