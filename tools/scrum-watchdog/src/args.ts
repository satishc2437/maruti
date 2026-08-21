/**
 * Argument parsing for the CLI, split out from the process wrapper so it is
 * pure and unit-testable.
 */

import type { WatchdogConfig } from './types.js';

export type Command = 'once' | 'watch' | 'help';

export interface ParsedArgs {
  command: Command;
  /** The `.scrum/<slug>/` directory to observe (required for once/watch). */
  scrumDir: string;
  config: WatchdogConfig;
  /** Poll interval for `watch`, in seconds. */
  intervalSec: number;
  /** Override for the status-file path (defaults under scrumDir). */
  statusFile: string | null;
  /** Optional JSON-lines event stream to fold in. */
  eventsFile: string | null;
  /** Print the full status JSON in addition to the summary. */
  json: boolean;
  /** Parse errors, if any (command falls back to help). */
  errors: string[];
}

const DEFAULTS = {
  heartbeatMinutes: 5,
  loopRepeats: 3,
  intervalSec: 20,
};

function envInt(name: string, fallback: number): number {
  const raw = process.env[name];
  if (raw === undefined) return fallback;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) ? n : fallback;
}

/**
 * Parse an argv slice (excluding node + script). Recognizes the `once`/`watch`
 * subcommands, a positional scrum dir, and long flags. Unknown flags and
 * out-of-range numbers are reported in `errors`; numeric flags fall back to
 * their defaults so the tool still runs.
 */
export function parseArgs(argv: string[]): ParsedArgs {
  const errors: string[] = [];
  const positionals: string[] = [];
  let heartbeatMinutes = envInt('SCRUM_WATCHDOG_HEARTBEAT_MIN', DEFAULTS.heartbeatMinutes);
  let loopRepeats = envInt('SCRUM_WATCHDOG_LOOP_K', DEFAULTS.loopRepeats);
  let intervalSec = envInt('SCRUM_WATCHDOG_INTERVAL_SEC', DEFAULTS.intervalSec);
  let statusFile: string | null = null;
  let eventsFile: string | null = null;
  let json = false;

  const takeNumber = (label: string, raw: string | undefined, min: number, fallback: number): number => {
    const n = Number.parseInt(raw ?? '', 10);
    if (!Number.isFinite(n) || n < min) {
      errors.push(`${label} must be an integer >= ${min}; using ${fallback}.`);
      return fallback;
    }
    return n;
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i] as string;
    switch (arg) {
      case '--heartbeat-min':
        heartbeatMinutes = takeNumber('--heartbeat-min', argv[++i], 1, DEFAULTS.heartbeatMinutes);
        break;
      case '--loop-k':
        loopRepeats = takeNumber('--loop-k', argv[++i], 2, DEFAULTS.loopRepeats);
        break;
      case '--interval-sec':
        intervalSec = takeNumber('--interval-sec', argv[++i], 1, DEFAULTS.intervalSec);
        break;
      case '--status-file':
        statusFile = argv[++i] ?? null;
        break;
      case '--events':
        eventsFile = argv[++i] ?? null;
        break;
      case '--json':
        json = true;
        break;
      case '-h':
      case '--help':
        positionals.unshift('help');
        break;
      default:
        if (arg.startsWith('--')) errors.push(`Unknown flag: ${arg}`);
        else positionals.push(arg);
    }
  }

  let command: Command = 'help';
  const first = positionals[0];
  if (first === 'once' || first === 'watch' || first === 'help') command = first;
  else if (first !== undefined) errors.push(`Unknown command: ${first}`);

  const scrumDir = positionals[1] ?? '';
  if ((command === 'once' || command === 'watch') && scrumDir === '') {
    errors.push('A .scrum/<slug> directory argument is required.');
    command = 'help';
  }

  return {
    command,
    scrumDir,
    config: { heartbeatMinutes, loopRepeats },
    intervalSec,
    statusFile,
    eventsFile,
    json,
    errors,
  };
}

/** The usage text. */
export function helpText(): string {
  return [
    'scrum-watchdog — flag silent hangs and mechanical thrashing in Scrum agent runs.',
    '',
    'Usage:',
    '  scrum-watchdog once  <scrumDir> [options]   Evaluate once, write status, print summary.',
    '  scrum-watchdog watch <scrumDir> [options]   Poll on an interval until interrupted.',
    '',
    'Arguments:',
    '  <scrumDir>   Path to a single project dir, e.g. .scrum/fix-login-typo',
    '',
    'Options:',
    '  --heartbeat-min <N>   Stuck threshold in minutes (default 5, env SCRUM_WATCHDOG_HEARTBEAT_MIN).',
    '  --loop-k <K>          Thrashing threshold: same signature K times (default 3, min 2).',
    '  --interval-sec <S>    Poll interval for watch (default 20).',
    '  --status-file <path>  Status JSON path (default <scrumDir>/watchdog-status.json).',
    '  --events <path>       Optional JSON-lines event stream to fold in.',
    '  --json                Also print the full status JSON.',
    '  -h, --help            Show this help.',
    '',
    'Exit codes (once): 0 healthy/complete/idle, 2 stuck, 3 thrashing.',
  ].join('\n');
}
