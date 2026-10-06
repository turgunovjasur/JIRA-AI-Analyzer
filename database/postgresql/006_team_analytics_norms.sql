BEGIN;
CREATE TABLE team_analytics_productivity_settings (
    company_id BIGINT PRIMARY KEY REFERENCES companies(id) ON DELETE CASCADE,
    closed_statuses JSONB NOT NULL DEFAULT '["Done", "Closed"]'::jsonb,
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL
);
CREATE TABLE team_analytics_assignee_norms (
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    jira_source TEXT NOT NULL,
    assignee_id TEXT NOT NULL CHECK (length(assignee_id) > 0),
    daily_points NUMERIC NOT NULL CHECK (daily_points > 0 AND daily_points <= 10000),
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY(company_id, jira_source, assignee_id)
);
COMMIT;
