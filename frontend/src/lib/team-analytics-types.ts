export type AnalyticsInterval = {
  started_at: string;
  ended_at: string;
  seconds: number;
  counted_seconds?: number;
  assignee_id: string;
  assignee_name: string;
  working_status: string;
  is_open: boolean;
};

export type AnalyticsTask = {
  jira_source: string;
  issue_id: string;
  issue_key: string;
  summary?: string;
  status_name?: string;
  assignee_id?: string;
  assignee_name?: string;
  story_points?: number | null;
  is_working: boolean;
  deleted: boolean;
  total_seconds: number;
  assignee_seconds: number;
  work_days: number;
  intervals: AnalyticsInterval[];
  sprint_ids?: number[];
};

export type AnalyticsSprint = {
  jira_source: string;
  id: number;
  name?: string;
  state?: string;
  started_at?: string;
  ends_at?: string;
  completed_at?: string;
  board_id?: number;
};

export type AnalyticsAssignee = {
  jira_source: string;
  assignee_id: string;
  assignee_name: string;
};

export type AnalyticsSettingsValue = {
  working_status: string;
  daily_hours: number;
  weekly_hours: number;
};

export type AnalyticsSnapshot = {
  timezone?: string;
  sync?: { jira_source: string; last_success_at: string | null; last_error: string | null }[];
  assignees: AnalyticsAssignee[];
  sprints?: AnalyticsSprint[];
  selected_sprint?: AnalyticsSprint | null;
  sprint_window?: { started_at: string; ended_at: string } | null;
  working_status: string;
  daily_hours: number;
  weekly_hours: number;
  summary: {
    assignee_count?: number;
    worked_seconds: number;
    task_points: number;
    missing_points: number;
    task_estimates: { worked_seconds: number; story_points: number | null }[];
    work_days: number;
  };
  tasks: AnalyticsTask[];
  total: number;
  limit: number;
  offset: number;
  generated_at: string;
};
