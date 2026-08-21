/**
 * Parser for `.scrum/<slug>/agents/<agentId>.md` work-log files.
 *
 * The on-disk format is defined in the packages' SCRUM-SCHEMA.md. Entries are
 * newest-on-top; each begins with a `## [Cycle <N>] <taskId> · <timestamp>`
 * header followed by a bullet list of fields and a `### Details` block.
 */

import type { WorkLogEntry, WorkLogStatus } from './types.js';

const ENTRY_HEADER = /^##\s+\[Cycle\s+(\d+)\]\s+(\S+)\s+·\s+(.+?)\s*$/;

const VALID_STATUSES: readonly WorkLogStatus[] = [
  'in-progress',
  'blocked',
  'done',
  'observation',
];

function field(block: string, label: string): string {
  // Matches `- **label:** value` on its own line.
  const re = new RegExp(`^-\\s+\\*\\*${label}:\\*\\*\\s*(.*)$`, 'm');
  const m = block.match(re);
  return m && m[1] !== undefined ? m[1].trim() : '';
}

function detailLine(block: string, label: string): string {
  // Matches `**Label** — value` within the Details block.
  const re = new RegExp(`^\\*\\*${label}\\*\\*\\s*[—-]\\s*(.*)$`, 'm');
  const m = block.match(re);
  return m && m[1] !== undefined ? m[1].trim() : '';
}

function coerceStatus(raw: string): WorkLogStatus {
  const v = raw.toLowerCase();
  return (VALID_STATUSES as readonly string[]).includes(v)
    ? (v as WorkLogStatus)
    : 'observation';
}

/**
 * Parse a full work-log markdown file into structured entries.
 *
 * Returns entries in the order they appear in the file (newest first, matching
 * the on-disk convention). Malformed blocks that lack a recognizable header are
 * skipped; a block with a header but missing fields yields best-effort values so
 * a single bad entry never crashes a run.
 */
export function parseWorkLog(markdown: string): WorkLogEntry[] {
  const lines = markdown.split(/\r?\n/);
  const entries: WorkLogEntry[] = [];

  // Find header line indices, then slice blocks between them.
  const headerIdx: number[] = [];
  for (let i = 0; i < lines.length; i++) {
    if (ENTRY_HEADER.test(lines[i] ?? '')) headerIdx.push(i);
  }

  for (let h = 0; h < headerIdx.length; h++) {
    const start = headerIdx[h] as number;
    const end = h + 1 < headerIdx.length ? (headerIdx[h + 1] as number) : lines.length;
    const headerLine = lines[start] ?? '';
    const body = lines.slice(start + 1, end).join('\n');
    const hm = headerLine.match(ENTRY_HEADER);
    if (!hm) continue;

    const cycleFromHeader = Number.parseInt(hm[1] as string, 10);
    const taskFromHeader = (hm[2] as string).trim();
    const tsRaw = (hm[3] as string).trim();

    const cycleField = field(body, 'cycle');
    const cycle = cycleField ? Number.parseInt(cycleField, 10) : cycleFromHeader;

    const timestampMs = Date.parse(tsRaw);
    const hasTs = !Number.isNaN(timestampMs);

    entries.push({
      cycle: Number.isNaN(cycle) ? cycleFromHeader : cycle,
      taskId: field(body, 'taskId') || taskFromHeader,
      agentId: field(body, 'agentId'),
      status: coerceStatus(field(body, 'status')),
      timestamp: hasTs ? tsRaw : null,
      timestampMs: hasTs ? timestampMs : null,
      requirement: field(body, 'requirement'),
      doing: detailLine(body, 'Doing'),
      blockers: detailLine(body, 'Blockers'),
    });
  }

  return entries;
}
