import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { parseCycleBudget, readCycleBudget } from '../src/plan.js';

describe('parseCycleBudget', () => {
  it('extracts the cap after a "Cycle budget" mention', () => {
    expect(parseCycleBudget('## Cycle budget\n\nthe cap 12 and warn 10')).toBe(12);
  });

  it('handles inline colon form', () => {
    expect(parseCycleBudget('- **Cycle budget**: 8 (warn 6)')).toBe(8);
  });

  it('returns null when absent', () => {
    expect(parseCycleBudget('no budget mentioned here')).toBeNull();
  });
});

describe('readCycleBudget', () => {
  let dir: string;
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'scrum-plan-'));
  });
  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  it('reads from plan.md when present', () => {
    writeFileSync(join(dir, 'plan.md'), 'Cycle budget: cap 15');
    expect(readCycleBudget(dir)).toBe(15);
  });

  it('returns null when plan.md is missing', () => {
    expect(readCycleBudget(dir)).toBeNull();
  });
});
