import type { AnalyticsSnapshot, AnalyticsTask } from './team-analytics-types';

export function parseAssignee(value: string): [string, string] {
  if (value === 'unassigned') return ['', ''];
  const parsed: unknown = JSON.parse(value);
  if (!Array.isArray(parsed) || parsed.length !== 2 || parsed.some(item => typeof item !== 'string'))
    throw new Error('Ijrochi identifikatori noto‘g‘ri');
  return parsed as [string, string];
}

export function summarizeTasks(tasks: Pick<AnalyticsTask, 'assignee_seconds' | 'story_points' | 'work_days' | 'jira_source' | 'assignee_id'>[] | { assignee_seconds: number; story_points: number | null; work_days: number; jira_source?: string; assignee_id?: string }[]): AnalyticsSnapshot['summary'] {
  return {
    worked_seconds: tasks.reduce((sum, task) => sum + task.assignee_seconds, 0),
    task_points: tasks.reduce((sum, task) => sum + (task.story_points ?? 0), 0),
    missing_points: tasks.filter(task => task.story_points == null).length,
    task_estimates: tasks.map(task => ({ worked_seconds: task.assignee_seconds, story_points: task.story_points ?? null })),
    work_days: tasks.reduce((sum, task) => sum + task.work_days, 0),
    assignee_count: new Set(tasks.map(task => JSON.stringify([task.jira_source ?? '', task.assignee_id ?? '']))).size,
  };
}

export function calculateDelay(tasks: AnalyticsSnapshot['summary']['task_estimates'], dailyHours: number, dailyPoints: number) {
  let count = 0, seconds = 0;
  const secondsPerPoint = dailyHours * 3600 / dailyPoints;
  for (const task of tasks) {
    if (task.story_points === null) continue;
    const extra = task.worked_seconds - task.story_points * secondsPerPoint;
    if (extra > 0) { count += 1; seconds += extra; }
  }
  const workDays = seconds / (dailyHours * 3600);
  return { count, seconds, workDays, points: workDays * dailyPoints };
}
