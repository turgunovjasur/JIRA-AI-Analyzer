import { describe, expect, it } from 'vitest';
import { applyTaskWorkLimits } from './team-analytics-limits';
import { filterSprintTasks } from './team-analytics-sprints';
import type { AnalyticsTask } from './team-analytics-types';

function task(id: string, person: string, starts: string, ends: string): AnalyticsTask {
  const seconds = (Date.parse(ends) - Date.parse(starts)) / 1000;
  return { jira_source: 'demo', issue_id: id, issue_key: id, assignee_id: person,
    story_points: 4, is_working: false, deleted: false, total_seconds: seconds,
    assignee_seconds: seconds, work_days: seconds / 28800,
    intervals: [{ started_at: starts, ended_at: ends, seconds, assignee_id: person,
      assignee_name: person, working_status: 'In Progress', is_open: false }] };
}

describe('work limits', () => {
  it('shares the daily allowance across tasks and keeps people separate', () => {
    const result = applyTaskWorkLimits([
      task('one', 'ali', '2026-09-21T00:00:00+05:00', '2026-09-22T00:00:00+05:00'),
      task('two', 'ali', '2026-09-21T00:00:00+05:00', '2026-09-22T00:00:00+05:00'),
      task('three', 'vali', '2026-09-21T00:00:00+05:00', '2026-09-22T00:00:00+05:00'),
    ], 8, 40);
    expect(result.map(item => item.assignee_seconds)).toEqual([14400, 14400, 28800]);
  });

  it('resets the weekly allowance on Monday in Tashkent', () => {
    const result = applyTaskWorkLimits([
      task('one', 'ali', '2026-09-21T00:00:00+05:00', '2026-09-29T00:00:00+05:00'),
    ], 8, 40);
    expect(result[0].assignee_seconds).toBeCloseTo(172800); // 40 + 8 hours.
    expect(result[0].intervals).toHaveLength(8);
  });

  it('counts partial days before limiting full days', () => {
    const result = applyTaskWorkLimits([
      task('DEV-10025', 'ali', '2026-09-21T18:56:00+05:00', '2026-09-23T11:18:00+05:00'),
    ], 8, 40);
    expect(result[0].assignee_seconds).toBe(75840); // 5:04 + 8 + 8.
  });

  it('preserves shared allowances when a sprint clips a day', () => {
    const result = applyTaskWorkLimits([
      { ...task('one', 'ali', '2026-09-21T00:00:00+05:00', '2026-09-22T00:00:00+05:00'), sprint_ids: [1] },
      task('two', 'ali', '2026-09-21T00:00:00+05:00', '2026-09-22T00:00:00+05:00'),
    ], 8, 40);
    const clipped = filterSprintTasks(result, { jira_source: 'demo', id: 1, state: 'closed',
      started_at: '2026-09-21T12:00:00+05:00', completed_at: '2026-09-22T00:00:00+05:00' },
      Date.parse('2026-09-23T00:00:00+05:00'));
    expect(clipped).toHaveLength(1);
    expect(clipped[0].assignee_seconds).toBe(7200);
    expect(clipped[0].intervals[0].counted_seconds).toBe(7200);
  });
});
