BEGIN;

-- 003 (F2-5): Per-company oylik AI xarajat limiti (USD).
-- NULL yoki 0 = cheksiz. ai_usage_events.estimated_total_cost_usd ning joriy
-- kalendar oy (UTC) yig'indisi bilan solishtiriladi
-- (core/module_start_preflight._check_monthly_budget).
ALTER TABLE company_settings
    ADD COLUMN IF NOT EXISTS ai_monthly_budget_usd NUMERIC(12, 2) NULL;

COMMIT;
