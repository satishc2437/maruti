/**
 * Persistence for the rolled-up {@link WatchdogStatus}. The status file is the
 * hand-off surface between the watchdog (writer) and the dashboard (reader), and
 * the signal the supervisor's auto-intervention reads.
 */

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';

import type { WatchdogStatus } from './types.js';

/** Default status-file name written inside a `.scrum/<slug>/` directory. */
export const STATUS_FILENAME = 'watchdog-status.json';

/** Serialize a status object to pretty JSON. */
export function serializeStatus(status: WatchdogStatus): string {
  return `${JSON.stringify(status, null, 2)}\n`;
}

/** Write the status file, creating parent directories as needed. */
export function writeStatus(path: string, status: WatchdogStatus): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, serializeStatus(status), 'utf8');
}

/** Read and parse a previously written status file. */
export function readStatus(path: string): WatchdogStatus {
  return JSON.parse(readFileSync(path, 'utf8')) as WatchdogStatus;
}
