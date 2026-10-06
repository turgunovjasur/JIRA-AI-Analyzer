import { describe, expect, it } from 'vitest';
import { filterSprintTasks, sprintLabel, sprintWindow } from './team-analytics-sprints';
import type { AnalyticsTask } from './team-analytics-types';

describe('sprint calendar calculations', () => {
  const start = '2026-10-01T00:00:00Z';
  const end = '2026-10-03T00:00:00Z';
  const now = Date.parse('2026-10-04T00:00:00Z');
  it('uses completion for closed sprints and now for active sprints', () => {
    expect(sprintWindow({ jira_source: 'jira', id: 1, state: 'closed', started_at: start, completed_at: end }, now))
      .toEqual([1790812800000, 1790985600000]);
    expect(sprintWindow({ jira_source: 'jira', id: 1, state: 'active', started_at: start, ends_at: end, completed_at: end }, now))
      .toEqual([1790812800000, 1791072000000]);
    expect(sprintWindow({ jira_source: 'jira', id: 1, state: 'closed', started_at: start }, now)).toBeNull();
  });
  it('clips both ends without marking historical sprint time as still running', () => {
    const task: AnalyticsTask = { jira_source: 'jira', issue_id: '1', issue_key: 'DEV-1', sprint_ids: [1],
      is_working: true, deleted: false, total_seconds: 345600, assignee_seconds: 345600, work_days: 12,
      intervals: [{ started_at: '2026-09-30T00:00:00Z', ended_at: '2026-10-04T00:00:00Z',
        seconds: 345600, assignee_id: 'ali', assignee_name: 'Ali', working_status: 'In Progress', is_open: true }] };
    const result = filterSprintTasks([task], { jira_source: 'jira', id: 1, state: 'closed', started_at: start, completed_at: end }, now);
    expect(result[0].total_seconds).toBe(172800);
    expect(result[0].intervals[0]).toMatchObject({ started_at: start.replace('Z', '.000Z'), ended_at: end.replace('Z', '.000Z'), is_open: false });
    expect(filterSprintTasks([task], { jira_source: 'other', id: 1, state: 'closed', started_at: start, completed_at: end }, now)).toEqual([]);
  });
  it('shows the name and state; duplicate names also show dates in Tashkent', () => {
    const sprint = { jira_source: 'jira', id: 1, name: 'Sprint 24', state: 'closed', started_at: start, completed_at: end };
    expect(sprintLabel(sprint)).toBe('Sprint 24 · Yopilgan');
    expect(sprintLabel(sprint, true)).toBe('Sprint 24 · Yopilgan · 01.10.2026–03.10.2026');
  });
});
