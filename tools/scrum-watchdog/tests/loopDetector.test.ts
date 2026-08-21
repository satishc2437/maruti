import { describe, it, expect } from 'vitest';
import {
  detectThrashing,
  workLogSignature,
  streamSignature,
} from '../src/loopDetector.js';
import type { StreamEvent, WorkLogEntry } from '../src/types.js';

const wl = (over: Partial<WorkLogEntry> = {}): WorkLogEntry => ({
  cycle: 1,
  taskId: 'task-1',
  agentId: 'software-developer-1',
  status: 'in-progress',
  timestamp: null,
  timestampMs: null,
  doing: 'retry full-repo validation',
  blockers: 'none',
  ...over,
});

describe('detectThrashing', () => {
  it('flags when a signature repeats >= k times', () => {
    const res = detectThrashing(['a', 'a', 'a'], 3);
    expect(res.thrashing).toBe(true);
    expect(res.signature).toBe('a');
    expect(res.count).toBe(3);
  });

  it('does not flag below the threshold', () => {
    expect(detectThrashing(['a', 'a', 'b'], 3).thrashing).toBe(false);
  });

  it('clamps k to a minimum of 2', () => {
    expect(detectThrashing(['a'], 1).thrashing).toBe(false);
    expect(detectThrashing(['a', 'a'], 1).thrashing).toBe(true);
  });

  it('is never thrashing on empty input', () => {
    const res = detectThrashing([], 2);
    expect(res.thrashing).toBe(false);
    expect(res.count).toBe(0);
    expect(res.signature).toBe('');
  });

  it('counts non-consecutive repeats of the same signature', () => {
    const res = detectThrashing(['a', 'b', 'a', 'c', 'a'], 3);
    expect(res.thrashing).toBe(true);
    expect(res.signature).toBe('a');
    expect(res.count).toBe(3);
  });
});

describe('workLogSignature', () => {
  it('is stable across whitespace/case differences in detail text', () => {
    const a = workLogSignature(wl({ doing: 'Retry   Full-Repo Validation' }));
    const b = workLogSignature(wl({ doing: 'retry full-repo validation' }));
    expect(a).toBe(b);
  });

  it('differs when status or task differs', () => {
    expect(workLogSignature(wl())).not.toBe(workLogSignature(wl({ status: 'blocked' })));
    expect(workLogSignature(wl())).not.toBe(workLogSignature(wl({ taskId: 'task-2' })));
  });
});

describe('streamSignature', () => {
  it('hashes the (action,target,result) tuple normalized', () => {
    const e: StreamEvent = { ts: 0, action: 'Bash', target: 'pytest  -q', result: 'ERROR' };
    expect(streamSignature(e)).toBe('bash|pytest -q|error');
  });
});
