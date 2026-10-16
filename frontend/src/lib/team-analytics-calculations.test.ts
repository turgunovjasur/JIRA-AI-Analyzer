import { describe, expect, it } from 'vitest';
import { calculateDelay, parseAssignee, summarizeTasks } from './team-analytics-calculations';
import { duration, groupIntervalsByDay } from './team-analytics-time';

describe('analytics calculations', () => {
  it('does not drop a minute due to proportional allocation precision', () => {
    expect(duration(28800 - 1e-9)).toBe('8 soat 0 daqiqa');
    expect(duration(59.9)).toBe('0 soat 0 daqiqa');
  });
  it('sums each overrun without subtracting savings and excludes missing estimates', () => {
    expect(calculateDelay([{ worked_seconds: 10 * 3600, story_points: 2 },
      { worked_seconds: 2 * 3600, story_points: 2 }, { worked_seconds: 20 * 3600, story_points: null }], 8, 2))
      .toEqual({ count: 1, seconds: 7200, workDays: 0.25, points: 0.5 });
  });
  it('keeps source and account identity together', () => {
    expect(parseAssignee('["jira","ali"]')).toEqual(['jira', 'ali']);
    expect(parseAssignee('unassigned')).toEqual(['', '']);
  });
  it('sums all tasks before pagination', () => {
    const result = summarizeTasks([{ assignee_seconds: 3600, story_points: 2, work_days: 0.125 },
      { assignee_seconds: 7200, story_points: null, work_days: 0.25 }]);
    expect(result.worked_seconds).toBe(10800);
    expect(result.task_points).toBe(2);
    expect(result.missing_points).toBe(1);
  });
  it('uses Tashkent days even when runtime timezone differs', () => {
    const previousZone = process.env.TZ;
    process.env.TZ = 'UTC';
    const result = groupIntervalsByDay([{ started_at: '2026-10-05T18:30:00Z', ended_at: '2026-10-05T19:30:00Z',
      seconds: 3600, assignee_id: 'ali', assignee_name: 'Ali', working_status: 'In Progress', is_open: false }]);
    try {
      expect(result.map(day => [day.date, day.seconds])).toEqual([['05.10.2026', 1800], ['06.10.2026', 1800]]);
    } finally {
      if (previousZone === undefined) delete process.env.TZ;
      else process.env.TZ = previousZone;
    }
  });
});
