// Pure helpers for turning a day's duty segments into log-sheet geometry.
// No React here so the math is easy to reason about (and reuse).

export const MINUTES_PER_DAY = 1440;

// Rows top -> bottom, matching the federal grid order.
export const ROWS = [
  { key: 'OffDuty', label: 'OFF DUTY' },
  { key: 'Sleeper', label: 'SLEEPER BERTH' },
  { key: 'Driving', label: 'DRIVING' },
  { key: 'OnDuty', label: 'ON DUTY (NOT DRIVING)' },
];

export const ROW_INDEX = { OffDuty: 0, Sleeper: 1, Driving: 2, OnDuty: 3 };

/**
 * Take the backend day segments (which cover only active time) and return a
 * gap-free 0..1440 timeline, filling every gap — and the head/tail of the day —
 * with Off Duty. Real segments keep their label; filler off-duty has none.
 */
export function fillDay(segments) {
  const sorted = [...segments].sort((a, b) => a.start_min - b.start_min);
  const filled = [];
  let cursor = 0;

  for (const seg of sorted) {
    if (seg.start_min > cursor) {
      filled.push({ duty_status: 'OffDuty', start_min: cursor, end_min: seg.start_min, label: null });
    }
    filled.push({ ...seg });
    cursor = Math.max(cursor, seg.end_min);
  }
  if (cursor < MINUTES_PER_DAY) {
    filled.push({ duty_status: 'OffDuty', start_min: cursor, end_min: MINUTES_PER_DAY, label: null });
  }
  return filled;
}

/** Per-row totals (minutes) from a filled timeline. Sums to 1440. */
export function rowTotals(filled) {
  const totals = { OffDuty: 0, Sleeper: 0, Driving: 0, OnDuty: 0 };
  for (const seg of filled) {
    totals[seg.duty_status] += seg.end_min - seg.start_min;
  }
  return totals;
}

/** "8:30" style hours:minutes from a minute count. */
export function hoursMinutes(min) {
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return `${h}:${String(m).padStart(2, '0')}`;
}
