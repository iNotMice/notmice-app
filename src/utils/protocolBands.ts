/** Places journal periods on the marker chart's collection-date axis. */

const DAY_MS = 86_400_000;
const PAD_RATIO = 0.04;

export interface JournalSpan {
  id: string;
  title: string;
  startedOn: string;
  endedOn: string | null;
}

export interface DateAxis {
  start: number;
  end: number;
}

export interface LaidOutPeriod {
  id: string;
  title: string;
  lane: number;
  /** Inclusive first day, UTC midnight. */
  start: number;
  /** Inclusive last day, UTC midnight. An empty end date is `today`. */
  end: number;
}

export interface PeriodBandLayout {
  axis: DateAxis;
  periods: LaidOutPeriod[];
}

export function dayMs(iso: string): number | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso.trim());
  if (!match) {
    return null;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const utc = Date.UTC(year, month - 1, day);
  const check = new Date(utc);
  if (
    check.getUTCFullYear() !== year ||
    check.getUTCMonth() !== month - 1 ||
    check.getUTCDate() !== day
  ) {
    return null;
  }
  return utc;
}

export function localIsoDate(now: Date = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function fractionOnAxis(ms: number, axis: DateAxis): number {
  const span = axis.end - axis.start;
  if (span === 0) {
    return 0;
  }
  return (ms - axis.start) / span;
}

/** Exclusive end of the inclusive last day, so a one-day entry has width. */
export function periodDrawEnd(period: LaidOutPeriod): number {
  return period.end + DAY_MS;
}

function paddedAxis(min: number, max: number): DateAxis {
  if (max === min) {
    return { start: min - DAY_MS, end: max + DAY_MS };
  }
  const pad = Math.max((max - min) * PAD_RATIO, DAY_MS);
  return { start: min - pad, end: max + pad };
}

export function layoutPeriodBands(
  collectionDates: readonly string[],
  entries: readonly JournalSpan[],
  today: string,
): PeriodBandLayout {
  const todayMs = dayMs(today);
  const periods: LaidOutPeriod[] = [];
  for (const entry of entries) {
    const title = entry.title.trim();
    const start = dayMs(entry.startedOn);
    if (!title || start == null) {
      continue;
    }
    const writtenEnd = entry.endedOn == null || entry.endedOn.trim() === '' ? null : dayMs(entry.endedOn);
    const end = writtenEnd ?? todayMs;
    if (end == null || end < start) {
      continue;
    }
    periods.push({ id: entry.id, title, lane: 0, start, end });
  }
  periods.sort(
    (left, right) =>
      left.start - right.start ||
      left.title.localeCompare(right.title) ||
      left.id.localeCompare(right.id),
  );

  const laneEnds: number[] = [];
  for (const period of periods) {
    const lane = laneEnds.findIndex((end) => end < period.start);
    if (lane === -1) {
      period.lane = laneEnds.length;
      laneEnds.push(period.end);
    } else {
      period.lane = lane;
      laneEnds[lane] = period.end;
    }
  }

  const instants: number[] = [];
  for (const raw of collectionDates) {
    const ms = dayMs(raw);
    if (ms != null) {
      instants.push(ms);
    }
  }
  for (const period of periods) {
    instants.push(period.start, periodDrawEnd(period));
  }
  if (instants.length === 0) {
    const origin = todayMs ?? Date.UTC(1970, 0, 1);
    return { axis: paddedAxis(origin, origin), periods };
  }
  return {
    axis: paddedAxis(Math.min(...instants), Math.max(...instants)),
    periods,
  };
}
