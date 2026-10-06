import type { AnalyticsInterval } from "@/lib/team-analytics-types";

export function duration(seconds: number) {
  const minutes = Math.floor(Math.max(0, seconds) / 60);
  return `${Math.floor(minutes / 60)} soat ${minutes % 60} daqiqa`;
}

export function numberLabel(value: number) {
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export type AnalyticsDay = {
  date: string;
  seconds: number;
  intervals: { start: string; end: string; seconds: number; assigneeName: string; isOpen: boolean }[];
};

/** Company calendar days are stable across browsers and server timezones. */
export function groupIntervalsByDay(intervals: AnalyticsInterval[], timeZone = 'Asia/Tashkent'): AnalyticsDay[] {
  const days = new Map<string, AnalyticsDay>();
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
  const sorted = [...intervals].sort((a, b) => Date.parse(a.started_at) - Date.parse(b.started_at));
  for (const interval of sorted) {
    let cursor = new Date(interval.started_at);
    const end = new Date(interval.ended_at);
    if (!Number.isFinite(cursor.getTime()) || !Number.isFinite(end.getTime())) continue;
    while (cursor < end) {
      const p = parts(cursor);
      const nextDate = Date.UTC(p.year, p.month - 1, p.day + 1);
      const guess = new Date(nextDate - offset(cursor));
      const midnight = new Date(nextDate - offset(guess));
      const segmentEnd = new Date(Math.min(midnight.getTime(), end.getTime()));
      const key = `${p.year}-${pad(p.month)}-${pad(p.day)}`;
      const day: AnalyticsDay = days.get(key) ?? {
        date: `${pad(p.day)}.${pad(p.month)}.${p.year}`,
        seconds: 0, intervals: [],
      };
      const seconds = (segmentEnd.getTime() - cursor.getTime()) / 1000;
      day.seconds += seconds;
      day.intervals.push({ start: clock(cursor), end: segmentEnd.getTime() === midnight.getTime() ? "24:00" : clock(segmentEnd),
        seconds, assigneeName: interval.assignee_name || "Biriktirilmagan",
        isOpen: interval.is_open && segmentEnd.getTime() === end.getTime() });
      days.set(key, day);
      cursor = segmentEnd;
    }
  }
  return Array.from(days.values());
}
