"use client";

import { useEffect, useMemo, useState } from 'react';
import { createAnalyticsDemo } from '@/lib/team-analytics-demo';
import { parseAssignee, summarizeTasks } from '@/lib/team-analytics-calculations';
import { filterSprintTasks, parseSprint, sprintKey, sprintWindow } from '@/lib/team-analytics-sprints';
import type { AnalyticsSnapshot, AnalyticsSettingsValue } from '@/lib/team-analytics-types';

export const ANALYTICS_PAGE_SIZE = 20;

export function useTeamAnalytics(assignee: string, offset: number, refresh: number, demo: boolean, settings: AnalyticsSettingsValue, sprint = 'all') {
  const requestKey = JSON.stringify([assignee, offset, refresh, demo, sprint]);
  const [result, setResult] = useState<{ key: string; snapshot: AnalyticsSnapshot | null; error: string }>({ key: '', snapshot: null, error: '' });
  useEffect(() => {
    if (demo) return;
    const controller = new AbortController();
    const query = new URLSearchParams({ limit: String(ANALYTICS_PAGE_SIZE), offset: String(offset) });
    if (assignee !== 'all') {
      const [source, id] = parseAssignee(assignee);
      query.set('assignee_id', id);
      if (id) query.set('jira_source', source);
    }
    if (sprint !== 'all') {
      const [source, id] = parseSprint(sprint);
      query.set('sprint_id', String(id));
      query.set('sprint_source', source);
    }
    fetch(`/api/team-analytics?${query}`, { signal: controller.signal }).then(async response => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Ma’lumot olishda xato');
      if (!Array.isArray(data.tasks) || !Array.isArray(data.assignees) || !data.summary || !(data.daily_hours > 0) || !(data.weekly_hours > 0))
        throw new Error('Analytics javobi noto‘g‘ri');
      if (!controller.signal.aborted) setResult({ key: requestKey, snapshot: data, error: '' });
    }).catch(error => {
      if (!controller.signal.aborted) setResult(previous => ({ key: requestKey, snapshot: previous.snapshot, error: error.message }));
    });
    return () => controller.abort();
  }, [assignee, offset, demo, sprint, requestKey]);

  const demoSnapshot = useMemo(() => {
    if (!demo) return null;
    const [selected, pageOffset] = JSON.parse(requestKey) as [string, number];
    const data = createAnalyticsDemo(settings.working_status, settings.daily_hours, settings.weekly_hours);
    if (sprint !== 'all') {
      const selectedSprint = data.sprints?.find(item => sprintKey(item) === sprint);
      if (selectedSprint) {
        const now = Date.parse(data.generated_at);
        const window = sprintWindow(selectedSprint, now);
        data.selected_sprint = selectedSprint;
        data.sprint_window = window ? { started_at: new Date(window[0]).toISOString(), ended_at: new Date(window[1]).toISOString() } : null;
        data.tasks = filterSprintTasks(data.tasks, selectedSprint, now);
      } else data.tasks = [];
    }
    if (selected !== 'all') {
      const [source, id] = parseAssignee(selected);
      data.tasks = data.tasks.filter(task => id ? task.jira_source === source &&
        task.assignee_id === id : !task.assignee_id);
      data.tasks = data.tasks.map(task => {
        const seconds = task.intervals.filter(interval => interval.assignee_id === id)
          .reduce((sum, interval) => sum + (interval.counted_seconds ?? interval.seconds), 0);
        return { ...task, assignee_seconds: seconds, work_days: seconds / (data.daily_hours * 3600) };
      });
    }
    data.tasks = data.tasks.map(task => ({ ...task, work_days: task.assignee_seconds / (data.daily_hours * 3600) }));
    data.summary = summarizeTasks(data.tasks);
    data.total = data.tasks.length;
    data.offset = pageOffset; data.limit = ANALYTICS_PAGE_SIZE;
    data.tasks = data.tasks.slice(pageOffset, pageOffset + ANALYTICS_PAGE_SIZE);
    return data;
    // refresh is part of requestKey, updating the fixture's observation time too.
  }, [demo, settings, requestKey, sprint]);

  return { snapshot: demo ? demoSnapshot : result.key === requestKey && !result.error ? result.snapshot : null,
    catalog: demo ? demoSnapshot : result.snapshot,
    loading: !demo && result.key !== requestKey, error: !demo && result.key === requestKey ? result.error : '' };
}
