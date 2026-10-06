BEGIN;
ALTER TABLE team_analytics_productivity_settings
    ADD COLUMN daily_hours NUMERIC NOT NULL DEFAULT 8
    CHECK (daily_hours > 0 AND daily_hours <= 24);
COMMIT;
