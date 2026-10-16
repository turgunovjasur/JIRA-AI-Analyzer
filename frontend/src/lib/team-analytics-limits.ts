import { splitIntervalByDay } from './team-analytics-time';
import type { AnalyticsTask } from './team-analytics-types';

/** Browser demo mirrors the server's daily, then weekly proportional allowances. */
export function applyTaskWorkLimits(tasks: AnalyticsTask[], dailyHours: number, weeklyHours: number): AnalyticsTask[] {
  const dailyTotals = new Map<string, number>();
  const weeklyTotals = new Map<string, number>();
  const segments = tasks.map(task => task.intervals.flatMap(interval => splitIntervalByDay(interval).map(segment => {
    const date = new Date(`${segment.calendar_date}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() - (date.getUTCDay() + 6) % 7);
    const dayKey = JSON.stringify([task.jira_source, segment.assignee_id, segment.calendar_date]);
    const weekKey = JSON.stringify([task.jira_source, segment.assignee_id, date.toISOString().slice(0, 10)]);
    dailyTotals.set(dayKey, (dailyTotals.get(dayKey) ?? 0) + segment.seconds);
    return { segment, dayKey, weekKey };
  })));
  const dailyLimited = segments.map(items => items.map(item => {
    const seconds = item.segment.seconds * Math.min(1, dailyHours * 3600 / dailyTotals.get(item.dayKey)!);
    weeklyTotals.set(item.weekKey, (weeklyTotals.get(item.weekKey) ?? 0) + seconds);
    return { ...item, seconds };
  }));
  return tasks.map((task, index) => {
    const intervals = dailyLimited[index].map(item => ({ ...item.segment,
      counted_seconds: item.seconds * Math.min(1, weeklyHours * 3600 / weeklyTotals.get(item.weekKey)!) }));
    const seconds = intervals.reduce((sum, interval) => sum + interval.counted_seconds, 0);
    return { ...task, intervals, assignee_seconds: seconds, work_days: seconds / (dailyHours * 3600) };
  });
}
