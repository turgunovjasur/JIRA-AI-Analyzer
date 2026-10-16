import { cleanup, renderHook } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { useTeamAnalytics } from './use-team-analytics';
import type { AnalyticsSnapshot } from '@/lib/team-analytics-types';

vi.mock('@/lib/team-analytics-demo', () => ({
  createAnalyticsDemo: (): AnalyticsSnapshot => ({
    generated_at: '2026-10-06T12:00:00Z', daily_hours: 8, weekly_hours: 40,
    working_status: 'Working', assignees: [], tasks: [
      { jira_source: 'jira', issue_id: 'current', issue_key: 'TEST-1',
        assignee_id: 'ali', story_points: 3, deleted: false, is_working: false,
        total_seconds: 0, assignee_seconds: 0, work_days: 0, intervals: [] },
      { jira_source: 'jira', issue_id: 'reassigned', issue_key: 'TEST-2',
        assignee_id: 'vali', story_points: 7, deleted: false, is_working: false,
        total_seconds: 3600, assignee_seconds: 3600, work_days: 0.125,
        intervals: [{ started_at: '2026-10-05T09:00:00Z', ended_at: '2026-10-05T10:00:00Z',
          seconds: 3600, assignee_id: 'ali', assignee_name: 'Ali', working_status: 'Working', is_open: false }] },
    ],
    summary: { worked_seconds: 3600, task_points: 10, missing_points: 0, work_days: 0.125, task_estimates: [] },
    total: 2, offset: 0, limit: 20,
  }),
}));

afterEach(cleanup);

it('uses the current assignee in demo exactly as in Jira, preserving reassigned task history', () => {
  const settings = { working_status: 'Working', daily_hours: 8, weekly_hours: 40 };
  const { result } = renderHook(() => useTeamAnalytics('["jira","ali"]', 0, 0, true, settings));
  expect(result.current.snapshot?.tasks.map(task => task.issue_key)).toEqual(['TEST-1']);
  expect(result.current.snapshot?.total).toBe(1);
  expect(result.current.snapshot?.summary.task_points).toBe(3);
  const all = renderHook(() => useTeamAnalytics('all', 0, 0, true, settings));
  expect(all.result.current.snapshot?.tasks[1].intervals[0].assignee_id).toBe('ali');
});
