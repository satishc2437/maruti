import { describe, it, expect } from 'vitest';
import { summarizeStatus, stateChanged } from '../src/summary.js';
import type { WatchdogStatus } from '../src/types.js';

const base = (over: Partial<WatchdogStatus> = {}): WatchdogStatus => ({
  schemaVersion: 1,
  projectSlug: 'demo',
  generatedAt: '2026-08-20T22:00:00.000Z',
  state: 'healthy',
  config: { heartbeatMinutes: 5, loopRepeats: 3 },
  tasks: [
    { taskId: 'task-1', agentId: 'software-developer-1', latestStatus: 'in-progress', latestCycle: 2, requirement: '', blocker: '' },
  ],
  signals: [],
  lastEventAt: '2026-08-20T21:59:00.000Z',
  minutesSinceLastEvent: 1,
  ...over,
});

describe('summarizeStatus', () => {
  it('summarizes a healthy run with task counts', () => {
    const line = summarizeStatus(base());
    expect(line).toContain('[demo]');
    expect(line).toContain('HEALTHY');
    expect(line).toContain('1 in-progress');
  });

  it('lists signals when present', () => {
    const line = summarizeStatus(
      base({ state: 'thrashing', signals: [{ kind: 'thrashing', agentId: 'software-developer-1', detail: 'x' }] }),
    );
    expect(line).toContain('THRASHING');
    expect(line).toContain('thrashing(software-developer-1)');
  });

  it('handles the no-tasks case', () => {
    expect(summarizeStatus(base({ tasks: [], state: 'idle' }))).toContain('no tasks');
  });
});

describe('stateChanged', () => {
  it('is true on first observation', () => {
    expect(stateChanged(null, base())).toBe(true);
  });

  it('is true when the state changes', () => {
    expect(stateChanged(base(), base({ state: 'stuck' }))).toBe(true);
  });

  it('is true when the signal set changes', () => {
    const prev = base();
    const next = base({ signals: [{ kind: 'stuck', agentId: 'run', detail: 'd' }] });
    expect(stateChanged(prev, next)).toBe(true);
  });

  it('is false when nothing material changed', () => {
    expect(stateChanged(base(), base({ generatedAt: 'later' }))).toBe(false);
  });
});
