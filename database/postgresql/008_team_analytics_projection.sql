BEGIN;
ALTER TABLE team_analytics_events ADD COLUMN actor_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN actor_name TEXT NOT NULL DEFAULT '',
    ADD COLUMN origin TEXT NOT NULL DEFAULT 'webhook';

CREATE TABLE team_analytics_tasks (
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    jira_source TEXT NOT NULL, issue_id TEXT NOT NULL, issue_key TEXT NOT NULL,
    assignee_id TEXT NOT NULL DEFAULT '', story_points DOUBLE PRECISION,
    snapshot JSONB NOT NULL, last_event_at TIMESTAMPTZ NOT NULL,
    projected_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(company_id,jira_source,issue_id)
);
CREATE INDEX team_analytics_tasks_page ON team_analytics_tasks(company_id,last_event_at DESC);
CREATE INDEX team_analytics_tasks_assignee ON team_analytics_tasks(company_id,jira_source,assignee_id);
CREATE INDEX team_analytics_tasks_metadata ON team_analytics_tasks USING GIN(snapshot);

CREATE TABLE team_analytics_intervals (
    company_id BIGINT NOT NULL, jira_source TEXT NOT NULL, issue_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL, started_at TIMESTAMPTZ NOT NULL, ended_at TIMESTAMPTZ,
    assignee_id TEXT NOT NULL DEFAULT '', assignee_name TEXT NOT NULL DEFAULT '',
    working_status TEXT NOT NULL,
    CHECK(ended_at IS NULL OR ended_at >= started_at),
    PRIMARY KEY(company_id,jira_source,issue_id,ordinal),
    FOREIGN KEY(company_id,jira_source,issue_id) REFERENCES team_analytics_tasks ON DELETE CASCADE
);
CREATE INDEX team_analytics_intervals_person ON team_analytics_intervals(company_id,jira_source,assignee_id,issue_id);

CREATE TABLE team_analytics_people (
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    jira_source TEXT NOT NULL, assignee_id TEXT NOT NULL, assignee_name TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY(company_id,jira_source,assignee_id)
);
CREATE TABLE team_analytics_sprints (
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    jira_source TEXT NOT NULL, sprint_id BIGINT NOT NULL, metadata JSONB NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY(company_id,jira_source,sprint_id)
);
CREATE TABLE team_analytics_task_sprints (
    company_id BIGINT NOT NULL, jira_source TEXT NOT NULL, issue_id TEXT NOT NULL, sprint_id BIGINT NOT NULL,
    PRIMARY KEY(company_id,jira_source,issue_id,sprint_id),
    FOREIGN KEY(company_id,jira_source,issue_id) REFERENCES team_analytics_tasks ON DELETE CASCADE,
    FOREIGN KEY(company_id,jira_source,sprint_id) REFERENCES team_analytics_sprints ON DELETE CASCADE
);
CREATE TABLE team_analytics_jira_fields (
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    jira_source TEXT NOT NULL, project_key TEXT NOT NULL,
    points_field TEXT NOT NULL, sprint_field TEXT NOT NULL,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(company_id,jira_source,project_key)
);
CREATE TABLE team_analytics_sync_state (
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    jira_source TEXT NOT NULL, last_success_at TIMESTAMPTZ,
    last_error TEXT, last_attempt_at TIMESTAMPTZ,
    PRIMARY KEY(company_id,jira_source)
);
COMMIT;
