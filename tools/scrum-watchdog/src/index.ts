/** Public API for the Scrum watchdog. */

export * from './types.js';
export { parseWorkLog } from './workLog.js';
export {
  detectThrashing,
  workLogSignature,
  streamSignature,
  type ThrashResult,
} from './loopDetector.js';
export { checkHeartbeat, type HeartbeatResult } from './heartbeat.js';
export {
  evaluate,
  evaluateScrumDir,
  readAgentEntries,
  readStreamEvents,
  DEFAULT_CONFIG,
  type EvaluateInput,
} from './watchdog.js';
export {
  writeStatus,
  readStatus,
  serializeStatus,
  STATUS_FILENAME,
} from './statusFile.js';
export { summarizeStatus, stateChanged } from './summary.js';
export { parseCycleBudget, readCycleBudget } from './plan.js';
export {
  buildModel,
  loadDashboard,
  renderText,
  renderHtml,
  type DashboardModel,
  type DashboardProject,
} from './dashboard.js';
