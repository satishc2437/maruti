#!/usr/bin/env node
/**
 * CLI entrypoint. Thin process wrapper around the pure evaluation core so the
 * logic stays testable; this file only wires argv, filesystem, timers, and
 * stdout together.
 */

import { join } from 'node:path';

import { parseArgs, helpText } from './args.js';
import { evaluateScrumDir } from './watchdog.js';
import { writeStatus, STATUS_FILENAME } from './statusFile.js';
import { summarizeStatus, stateChanged } from './summary.js';
import type { WatchdogStatus } from './types.js';

const EXIT_BY_STATE: Record<WatchdogStatus['state'], number> = {
  healthy: 0,
  complete: 0,
  idle: 0,
  stuck: 2,
  thrashing: 3,
};

async function main(): Promise<number> {
  const args = parseArgs(process.argv.slice(2));

  for (const e of args.errors) process.stderr.write(`warning: ${e}\n`);

  if (args.command === 'help') {
    process.stdout.write(`${helpText()}\n`);
    return args.errors.length > 0 ? 1 : 0;
  }

  const statusPath = args.statusFile ?? join(args.scrumDir, STATUS_FILENAME);

  const evalNow = (): WatchdogStatus => {
    const status = evaluateScrumDir(
      args.scrumDir,
      args.config,
      Date.now(),
      args.eventsFile ?? undefined,
    );
    writeStatus(statusPath, status);
    return status;
  };

  if (args.command === 'once') {
    const status = evalNow();
    process.stdout.write(`${summarizeStatus(status)}\n`);
    if (args.json) process.stdout.write(`${JSON.stringify(status, null, 2)}\n`);
    return EXIT_BY_STATE[status.state];
  }

  // watch
  process.stdout.write(
    `scrum-watchdog watching ${args.scrumDir} every ${args.intervalSec}s ` +
      `(heartbeat ${args.config.heartbeatMinutes}m, loop-k ${args.config.loopRepeats}). Ctrl-C to stop.\n`,
  );
  let prev: WatchdogStatus | null = null;
  let stop = false;
  const onSignal = (): void => {
    stop = true;
  };
  process.on('SIGINT', onSignal);
  process.on('SIGTERM', onSignal);

  while (!stop) {
    const status = evalNow();
    if (stateChanged(prev, status)) {
      process.stdout.write(`${summarizeStatus(status)}\n`);
    }
    prev = status;
    await new Promise((r) => setTimeout(r, args.intervalSec * 1000));
  }
  process.stdout.write('scrum-watchdog stopped.\n');
  return 0;
}

// Exported for integration tests; only auto-runs as a script.
export { main };

const invokedPath = process.argv[1] ?? '';
if (invokedPath.includes('cli')) {
  main()
    .then((code) => process.exit(code))
    .catch((err) => {
      process.stderr.write(`scrum-watchdog error: ${(err as Error).message}\n`);
      process.exit(1);
    });
}
