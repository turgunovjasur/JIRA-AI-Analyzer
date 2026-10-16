import type { AnalyticsInterval } from "@/lib/team-analytics-types";

export function duration(seconds: number) {
  // Proportional allowances can leave a whole minute a few floating-point bits short.
  const minutes = Math.floor((Math.max(0, seconds) + 1e-7) / 60);
  return `${Math.floor(minutes / 60)} soat ${minutes % 60} daqiqa`;
}

export function numberLabel(value: number) {
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export type AnalyticsDay = {
  date: string;
  seconds: number;
  rawSeconds: number;
  intervals: { start: string; end: string; seconds: number; assigneeName: string; isOpen: boolean }[];
};

/** Split at company midnight, independently of the browser's timezone. */
export function splitIntervalByDay(interval: AnalyticsInterval, timeZone = 'Asia/Tashkent') {
  const segments: (AnalyticsInterval & { calendar_date: string; startLabel: string; endLabel: string })[] = [];
  const pad = (value: number) => String(value).padStart(2, "0");
  const formatter = new Intl.DateTimeFormat('en-GB', { timeZone, year: 'numeric', month: '2-digit',
    day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' });
  const parts = (value: Date) => Object.fromEntries(formatter.formatToParts(value)
    .filter(part => part.type !== 'literal').map(part => [part.type, Number(part.value)]));
  const offset = (value: Date) => {
    const p = parts(value);
    return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second) - Math.floor(value.getTime() / 1000) * 1000;
  };
  const clock = (value: Date) => { const p = parts(value); return `${pad(p.hour)}:${pad(p.minute)}`; };
  let cursor = new Date(interval.started_at);
  const end = new Date(interval.ended_at);
  if (!Number.isFinite(cursor.getTime()) || !Number.isFinite(end.getTime())) return segments;
  while (cursor < end) {
    const p = parts(cursor);
    const nextDate = Date.UTC(p.year, p.month - 1, p.day + 1);
    const guess = new Date(nextDate - offset(cursor));
    const midnight = new Date(nextDate - offset(guess));
    const segmentEnd = new Date(Math.min(midnight.getTime(), end.getTime()));
    const key = `${p.year}-${pad(p.month)}-${pad(p.day)}`;
    const seconds = (segmentEnd.getTime() - cursor.getTime()) / 1000;
    segments.push({ ...interval, calendar_date: key, started_at: cursor.toISOString(), ended_at: segmentEnd.toISOString(),
      seconds, counted_seconds: interval.counted_seconds === undefined ? undefined
        : seconds * interval.counted_seconds / (interval.seconds || 1),
      startLabel: clock(cursor), endLabel: segmentEnd.getTime() === midnight.getTime() ? "24:00" : clock(segmentEnd),
      is_open: interval.is_open && segmentEnd.getTime() === end.getTime() });
    cursor = segmentEnd;
  }
  return segments;
}

export function groupIntervalsByDay(intervals: AnalyticsInterval[], timeZone = 'Asia/Tashkent'): AnalyticsDay[] {
  const days = new Map<string, AnalyticsDay>();
  const sorted = [...intervals].sort((a, b) => Date.parse(a.started_at) - Date.parse(b.started_at));
  for (const interval of sorted) for (const segment of splitIntervalByDay(interval, timeZone)) {
    const key = segment.calendar_date;
    const [year, month, date] = key.split('-');
    const day: AnalyticsDay = days.get(key) ?? { date: `${date}.${month}.${year}`, seconds: 0, rawSeconds: 0, intervals: [] };
    const seconds = segment.counted_seconds ?? segment.seconds;
    day.seconds += seconds;
    day.rawSeconds += segment.seconds;
    day.intervals.push({ start: segment.startLabel, end: segment.endLabel, seconds,
      assigneeName: segment.assignee_name || 'Biriktirilmagan', isOpen: segment.is_open });
    days.set(key, day);
  }
  return Array.from(days.values());
}
