import { describe, it, expect } from 'vitest';
import { checkHeartbeat } from '../src/heartbeat.js';

const NOW = Date.parse('2026-08-20T22:00:00Z');

describe('checkHeartbeat', () => {
  it('reports null minutes and not-stuck when there is no event', () => {
    expect(checkHeartbeat(null, NOW, 5, true)).toEqual({
      stuck: false,
      minutesSinceLastEvent: null,
    });
  });

  it('flags stuck when an active run exceeds the threshold', () => {
    const last = NOW - 6 * 60000;
    const res = checkHeartbeat(last, NOW, 5, true);
    expect(res.stuck).toBe(true);
    expect(res.minutesSinceLastEvent).toBe(6);
  });

  it('does not flag when within the threshold', () => {
    const last = NOW - 4 * 60000;
    expect(checkHeartbeat(last, NOW, 5, true).stuck).toBe(false);
  });

  it('never flags an inactive/complete run even if long idle', () => {
    const last = NOW - 60 * 60000;
    expect(checkHeartbeat(last, NOW, 5, false).stuck).toBe(false);
  });

  it('rounds minutes to two decimals', () => {
    const last = NOW - 90 * 1000; // 1.5 min
    expect(checkHeartbeat(last, NOW, 5, true).minutesSinceLastEvent).toBe(1.5);
  });
});
