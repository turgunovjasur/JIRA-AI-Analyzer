import type { AnalyticsSprint, AnalyticsTask } from './team-analytics-types';

export function sprintKey(sprint: AnalyticsSprint): string {
  return JSON.stringify([sprint.jira_source, sprint.id]);
}

export function parseSprint(value: string): [string, number] {
  const [source, id] = JSON.parse(value) as [string, number];
  if (typeof source !== 'string' || !Number.isSafeInteger(id) || id <= 0) throw new Error('Sprint tanlovi noto‘g‘ri');
  return [source, id];
}

export function sprintWindow(sprint: AnalyticsSprint, now: number): [number, number] | null {
  if (sprint.state === 'future' || sprint.state === 'deleted' || !sprint.started_at) return null;
  const endValue = sprint.state === 'closed' ? sprint.completed_at || sprint.ends_at : undefined;
  if (sprint.state === 'closed' && !endValue) return null;
  const start = Date.parse(sprint.started_at);
  const end = endValue ? Math.min(Date.parse(endValue), now) : now;
  return Number.isFinite(start) && Number.isFinite(end) && end > start ? [start, end] : null;
}

export function sprintLabel(sprint: AnalyticsSprint, duplicateName = false): string {
  const name = sprint.name?.trim() || `Nomsiz sprint (${sprint.id})`;
  const state = ({ active: 'Faol', closed: 'Yopilgan', future: 'Rejalashtirilgan' } as Record<string, string>)[sprint.state || ''];
  const date = (value?: string) => value && Number.isFinite(Date.parse(value))
    ? new Date(value).toLocaleDateString('en-GB', { timeZone: 'Asia/Tashkent' }).replaceAll('/', '.') : '';
  const dates = duplicateName ? [date(sprint.started_at), date(sprint.state === 'closed' ? sprint.completed_at || sprint.ends_at : sprint.ends_at)].filter(Boolean).join('–') : '';
  const unavailable = !sprintWindow(sprint, Date.now()) && sprint.state !== 'future' ? 'Sanalar mavjud emas' : '';
  return [name, state, dates, unavailable].filter(Boolean).join(' · ');
}

/** Demo uses the same calendar clipping as the server; real totals come from SQL. */
export function filterSprintTasks(tasks: AnalyticsTask[], sprint: AnalyticsSprint, now: number): AnalyticsTask[] {
  const window = sprintWindow(sprint, now);
  if (!window) return [];
  return tasks.filter(task => task.jira_source === sprint.jira_source && task.sprint_ids?.includes(sprint.id)).map(task => {
    const intervals = task.intervals.flatMap(interval => {
      const start = Math.max(Date.parse(interval.started_at), window[0]);
      const end = Math.min(Date.parse(interval.ended_at), window[1]);
      if (end <= start) return [];
      return [{ ...interval, started_at: new Date(start).toISOString(), ended_at: new Date(end).toISOString(),
        seconds: (end - start) / 1000,
        counted_seconds: interval.counted_seconds === undefined ? undefined
          : (end - start) / 1000 * interval.counted_seconds / (interval.seconds || 1),
        is_open: interval.is_open && end === now }];
    });
    const seconds = intervals.reduce((sum, interval) => sum + (interval.counted_seconds ?? interval.seconds), 0);
    return { ...task, intervals, total_seconds: intervals.reduce((sum, interval) => sum + interval.seconds, 0),
      assignee_seconds: seconds, is_working: intervals.some(interval => interval.is_open) };
  });
}
