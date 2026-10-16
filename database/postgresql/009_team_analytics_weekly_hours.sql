BEGIN;
ALTER TABLE team_analytics_productivity_settings
    ADD COLUMN weekly_hours NUMERIC NOT NULL DEFAULT 40
    CHECK (weekly_hours > 0 AND weekly_hours <= 168);
COMMIT;
