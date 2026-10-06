BEGIN;

CREATE TABLE team_analytics_settings (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    working_status TEXT NOT NULL CHECK (length(trim(working_status)) BETWEEN 1 AND 128),
    effective_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX team_analytics_settings_company_time ON team_analytics_settings(company_id, effective_at, id);

CREATE TABLE team_analytics_events (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    jira_source TEXT NOT NULL,
    issue_id TEXT NOT NULL,
    issue_key TEXT NOT NULL,
    event_key TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    time_source TEXT NOT NULL,
    snapshot JSONB NOT NULL,
    changes JSONB NOT NULL DEFAULT '[]'::jsonb,
    UNIQUE(company_id, jira_source, issue_id, event_key)
);
CREATE INDEX team_analytics_events_replay ON team_analytics_events(company_id, jira_source, issue_id, occurred_at, id);
CREATE INDEX team_analytics_events_recent ON team_analytics_events(company_id, occurred_at DESC);

COMMIT;
