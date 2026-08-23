import { describe, it, expect, afterEach } from 'vitest';
import { parseArgs, helpText } from '../src/args.js';

const clearEnv = (): void => {
  delete process.env.SCRUM_WATCHDOG_HEARTBEAT_MIN;
  delete process.env.SCRUM_WATCHDOG_LOOP_K;
  delete process.env.SCRUM_WATCHDOG_INTERVAL_SEC;
};

afterEach(clearEnv);

describe('parseArgs', () => {
  it('parses once with a scrum dir and defaults', () => {
    const a = parseArgs(['once', '.scrum/demo']);
    expect(a.command).toBe('once');
    expect(a.scrumDir).toBe('.scrum/demo');
    expect(a.config).toEqual({ heartbeatMinutes: 5, loopRepeats: 3 });
    expect(a.intervalSec).toBe(20);
    expect(a.errors).toEqual([]);
  });

  it('parses all flags', () => {
    const a = parseArgs([
      'watch', '.scrum/x',
      '--heartbeat-min', '10',
      '--loop-k', '4',
      '--interval-sec', '30',
      '--status-file', 'out.json',
      '--events', 'ev.jsonl',
      '--json',
    ]);
    expect(a.command).toBe('watch');
    expect(a.config).toEqual({ heartbeatMinutes: 10, loopRepeats: 4 });
    expect(a.intervalSec).toBe(30);
    expect(a.statusFile).toBe('out.json');
    expect(a.eventsFile).toBe('ev.jsonl');
    expect(a.json).toBe(true);
  });

  it('requires a scrum dir for once/watch', () => {
    const a = parseArgs(['once']);
    expect(a.command).toBe('help');
    expect(a.errors.some((e) => e.includes('required'))).toBe(true);
  });

  it('falls back and warns on an out-of-range number', () => {
    const a = parseArgs(['once', 'd', '--loop-k', '1']);
    expect(a.config.loopRepeats).toBe(3);
    expect(a.errors.some((e) => e.includes('--loop-k'))).toBe(true);
  });

  it('reports unknown flags and commands', () => {
    const a = parseArgs(['bogus', '--nope']);
    expect(a.errors.some((e) => e.includes('Unknown flag'))).toBe(true);
    expect(a.errors.some((e) => e.includes('Unknown command'))).toBe(true);
  });

  it('routes --help to the help command', () => {
    expect(parseArgs(['--help']).command).toBe('help');
    expect(parseArgs(['-h']).command).toBe('help');
  });

  it('defaults to help with no arguments at all', () => {
    const a = parseArgs([]);
    expect(a.command).toBe('help');
    expect(a.errors).toEqual([]);
  });

  it('handles a numeric flag given as the trailing arg with no value', () => {
    const a = parseArgs(['once', 'd', '--heartbeat-min']);
    expect(a.config.heartbeatMinutes).toBe(5);
    expect(a.errors.some((e) => e.includes('--heartbeat-min'))).toBe(true);
  });

  it('treats a trailing --status-file / --events with no value as null', () => {
    const a = parseArgs(['once', 'd', '--status-file']);
    expect(a.statusFile).toBeNull();
    const b = parseArgs(['once', 'd', '--events']);
    expect(b.eventsFile).toBeNull();
  });

  it('honors env var defaults', () => {
    process.env.SCRUM_WATCHDOG_HEARTBEAT_MIN = '7';
    process.env.SCRUM_WATCHDOG_LOOP_K = '5';
    const a = parseArgs(['once', 'd']);
    expect(a.config).toEqual({ heartbeatMinutes: 7, loopRepeats: 5 });
  });

  it('ignores a non-numeric env var', () => {
    process.env.SCRUM_WATCHDOG_LOOP_K = 'abc';
    expect(parseArgs(['once', 'd']).config.loopRepeats).toBe(3);
  });
});

describe('helpText', () => {
  it('mentions the subcommands and exit codes', () => {
    const t = helpText();
    expect(t).toContain('once');
    expect(t).toContain('watch');
    expect(t).toContain('Exit codes');
  });
});
