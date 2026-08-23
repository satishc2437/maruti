import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import {
  writeStatus,
  readStatus,
  serializeStatus,
  STATUS_FILENAME,
} from '../src/statusFile.js';
import type { WatchdogStatus } from '../src/types.js';

const status: WatchdogStatus = {
  schemaVersion: 1,
  projectSlug: 'demo',
  generatedAt: '2026-08-20T22:00:00.000Z',
  state: 'healthy',
  config: { heartbeatMinutes: 5, loopRepeats: 3 },
  tasks: [],
  signals: [],
  lastEventAt: null,
  minutesSinceLastEvent: null,
};

describe('statusFile', () => {
  let dir: string;
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'scrum-wd-sf-'));
  });
  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  it('serializes to pretty JSON with a trailing newline', () => {
    const s = serializeStatus(status);
    expect(s.endsWith('\n')).toBe(true);
    expect(s).toContain('"projectSlug": "demo"');
  });

  it('round-trips through write/read, creating parent dirs', () => {
    const p = join(dir, 'nested', STATUS_FILENAME);
    writeStatus(p, status);
    expect(readStatus(p)).toEqual(status);
  });
});
