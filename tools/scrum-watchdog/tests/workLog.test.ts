import { describe, it, expect } from 'vitest';
import { parseWorkLog } from '../src/workLog.js';

const entry = (over: Partial<Record<string, string>> = {}): string => `## [Cycle ${over.cycle ?? '2'}] ${over.taskId ?? 'task-1'} · ${over.ts ?? '2026-08-20T22:00:00Z'}

- **agentId:** ${over.agentId ?? 'software-developer-1'}
- **taskId:** ${over.taskId ?? 'task-1'}
- **taskName:** Name
- **taskDescription:** Desc
- **requirement:** ${over.requirement ?? 'AC-1'}
- **cycle:** ${over.cycle ?? '2'}
- **status:** ${over.status ?? 'in-progress'}

### Details
**Done** — did a thing
**Doing** — ${over.doing ?? 'next thing'}
**Blockers** — ${over.blockers ?? 'none'}
**ETA** — 1 cycle
`;

describe('parseWorkLog', () => {
  it('parses a single well-formed entry', () => {
    const [e] = parseWorkLog(entry());
    expect(e).toBeDefined();
    expect(e!.cycle).toBe(2);
    expect(e!.taskId).toBe('task-1');
    expect(e!.agentId).toBe('software-developer-1');
    expect(e!.status).toBe('in-progress');
    expect(e!.timestamp).toBe('2026-08-20T22:00:00Z');
    expect(e!.timestampMs).toBe(Date.parse('2026-08-20T22:00:00Z'));
    expect(e!.requirement).toBe('AC-1');
    expect(e!.doing).toBe('next thing');
    expect(e!.blockers).toBe('none');
  });

  it('parses multiple entries newest-first in file order', () => {
    const md = entry({ cycle: '3', status: 'blocked', blockers: 'need creds' }) + '\n' + entry({ cycle: '2' });
    const es = parseWorkLog(md);
    expect(es).toHaveLength(2);
    expect(es[0]!.cycle).toBe(3);
    expect(es[0]!.status).toBe('blocked');
    expect(es[0]!.blockers).toBe('need creds');
    expect(es[1]!.cycle).toBe(2);
  });

  it('coerces an unknown status to observation', () => {
    const [e] = parseWorkLog(entry({ status: 'weird' }));
    expect(e!.status).toBe('observation');
  });

  it('falls back to header values when field lines are missing', () => {
    const md = `## [Cycle 5] task-9 · 2026-08-20T10:00:00Z

- **agentId:** code-reviewer-1
- **status:** done
`;
    const [e] = parseWorkLog(md);
    expect(e!.cycle).toBe(5);
    expect(e!.taskId).toBe('task-9');
    expect(e!.status).toBe('done');
  });

  it('marks an unparseable timestamp as null', () => {
    const md = `## [Cycle 1] task-1 · not-a-date

- **agentId:** a
- **status:** in-progress
`;
    const [e] = parseWorkLog(md);
    expect(e!.timestamp).toBeNull();
    expect(e!.timestampMs).toBeNull();
  });

  it('returns [] for content without any entry headers', () => {
    expect(parseWorkLog('# Just a heading\n\nsome prose')).toEqual([]);
  });

  it('handles CRLF line endings', () => {
    const md = entry().replace(/\n/g, '\r\n');
    const [e] = parseWorkLog(md);
    expect(e!.agentId).toBe('software-developer-1');
    expect(e!.doing).toBe('next thing');
  });
});
