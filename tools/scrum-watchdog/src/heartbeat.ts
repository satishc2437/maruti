/**
 * Heartbeat check: if the run is still active but has emitted no new event for
 * longer than the threshold, it is `stuck` (a silent hang).
 */

export interface HeartbeatResult {
  stuck: boolean;
  /** Minutes since the last event, or null if there has been no event at all. */
  minutesSinceLastEvent: number | null;
}

/**
 * Evaluate the heartbeat.
 *
 * @param lastEventMs Epoch-ms of the newest observed event, or null if none.
 * @param nowMs Epoch-ms of "now".
 * @param heartbeatMinutes Threshold in minutes.
 * @param active Whether the run still has unfinished work. A completed/idle run
 *   is never `stuck` no matter how long since the last event.
 */
export function checkHeartbeat(
  lastEventMs: number | null,
  nowMs: number,
  heartbeatMinutes: number,
  active: boolean,
): HeartbeatResult {
  if (lastEventMs === null) {
    return { stuck: false, minutesSinceLastEvent: null };
  }
  const minutes = (nowMs - lastEventMs) / 60000;
  const rounded = Math.round(minutes * 100) / 100;
  return {
    stuck: active && minutes > heartbeatMinutes,
    minutesSinceLastEvent: rounded,
  };
}
