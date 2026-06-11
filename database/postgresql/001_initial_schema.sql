BEGIN;

CREATE TABLE IF NOT EXISTS companies (
    id BIGSERIAL PRIMARY KEY,
    company_code VARCHAR(64) NOT NULL UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    seat_limit INTEGER NOT NULL DEFAULT 1 CHECK (seat_limit >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255),
    password_hash TEXT NOT NULL,
    role VARCHAR(32) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS company_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL UNIQUE REFERENCES companies(id) ON DELETE CASCADE,
    plan_name VARCHAR(64) NOT NULL,
    subscription_status VARCHAR(32) NOT NULL,
    billing_mode VARCHAR(32) NOT NULL,
    billing_start_date DATE,
    billing_end_date DATE,
    next_payment_date DATE,
    last_payment_date DATE,
    last_payment_note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS company_integrations (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    provider VARCHAR(64) NOT NULL,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(company_id, provider)
);

CREATE TABLE IF NOT EXISTS company_module_access (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    module_key VARCHAR(64) NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    enabled_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(company_id, module_key)
);

CREATE TABLE IF NOT EXISTS company_settings (
    company_id BIGINT PRIMARY KEY REFERENCES companies(id) ON DELETE CASCADE,
    jira_server TEXT NOT NULL DEFAULT '',
    jira_email TEXT NOT NULL DEFAULT '',
    jira_token TEXT NOT NULL DEFAULT '',
    jira_project_keys TEXT NOT NULL DEFAULT '',
    github_token TEXT NOT NULL DEFAULT '',
    github_org TEXT NOT NULL DEFAULT '',
    figma_token TEXT NOT NULL DEFAULT '',
    figma_tokens TEXT NOT NULL DEFAULT '[]',
    gemini_api_key_1 TEXT NOT NULL DEFAULT '',
    gemini_api_key_2 TEXT NOT NULL DEFAULT '',
    gemini_model TEXT NOT NULL DEFAULT '',
    webhook_jira_server TEXT NOT NULL DEFAULT '',
    webhook_jira_email TEXT NOT NULL DEFAULT '',
    webhook_jira_token TEXT NOT NULL DEFAULT '',
    webhook_github_token TEXT NOT NULL DEFAULT '',
    webhook_github_org TEXT NOT NULL DEFAULT '',
    webhook_figma_token TEXT NOT NULL DEFAULT '',
    webhook_figma_tokens TEXT NOT NULL DEFAULT '[]',
    webhook_gemini_api_key_1 TEXT NOT NULL DEFAULT '',
    webhook_gemini_api_key_2 TEXT NOT NULL DEFAULT '',
    webhook_gemini_model TEXT NOT NULL DEFAULT '',
    enabled_modules TEXT NOT NULL DEFAULT '{}',
    webhook_project_keys TEXT NOT NULL DEFAULT '',
    webhook_trigger_status TEXT NOT NULL DEFAULT '',
    webhook_trigger_aliases TEXT NOT NULL DEFAULT '',
    webhook_return_status TEXT NOT NULL DEFAULT '',
    webhook_allowed_issue_types TEXT NOT NULL DEFAULT '',
    webhook_excluded_assignees TEXT NOT NULL DEFAULT '',
    webhook_auto_return_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    webhook_return_threshold INTEGER NOT NULL DEFAULT 60,
    webhook_module_settings TEXT NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_credentials (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    jira_server TEXT NOT NULL DEFAULT '',
    jira_email TEXT NOT NULL DEFAULT '',
    jira_token TEXT NOT NULL DEFAULT '',
    jira_project_keys TEXT NOT NULL DEFAULT '',
    github_token TEXT NOT NULL DEFAULT '',
    github_org TEXT NOT NULL DEFAULT '',
    figma_token TEXT NOT NULL DEFAULT '',
    figma_tokens TEXT NOT NULL DEFAULT '[]',
    gemini_api_key_1 TEXT NOT NULL DEFAULT '',
    gemini_api_key_2 TEXT NOT NULL DEFAULT '',
    gemini_model TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_module_settings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    module_key VARCHAR(64) NOT NULL,
    settings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, module_key)
);

CREATE TABLE IF NOT EXISTS global_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS login_attempts (
    identifier TEXT PRIMARY KEY,
    failed_count INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS platform_admins (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS login_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    identifier TEXT NOT NULL,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL,
    role VARCHAR(32),
    success BOOLEAN NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_password_reset_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL,
    actor_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    actor_role VARCHAR(32),
    event_type VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id TEXT NOT NULL DEFAULT '',
    event_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jobs (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT REFERENCES companies(id) ON DELETE CASCADE,
    job_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    scheduled_for TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_runs (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    run_status VARCHAR(32) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    error_message TEXT NOT NULL DEFAULT '',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS task_processing (
    id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(128) NOT NULL UNIQUE,
    company_id BIGINT REFERENCES companies(id) ON DELETE CASCADE,
    task_status VARCHAR(32) NOT NULL DEFAULT 'none',
    task_update_time TIMESTAMPTZ,
    return_count INTEGER NOT NULL DEFAULT 0,
    return_reason VARCHAR(64),
    last_jira_status TEXT,
    last_processed_at TIMESTAMPTZ,
    error_message TEXT,
    skip_detected BOOLEAN NOT NULL DEFAULT FALSE,
    service1_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    service2_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    service1_error TEXT,
    service2_error TEXT,
    service1_done_at TIMESTAMPTZ,
    service2_done_at TIMESTAMPTZ,
    compliance_score INTEGER,
    assignee TEXT,
    task_type TEXT,
    feature_name TEXT,
    technology_stack TEXT,
    blocked_at TIMESTAMPTZ,
    blocked_retry_at TIMESTAMPTZ,
    block_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS task_status_history (
    id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(128) NOT NULL,
    company_id BIGINT REFERENCES companies(id) ON DELETE CASCADE,
    from_status TEXT,
    to_status TEXT NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL,
    assignee TEXT,
    story_points NUMERIC(10, 2),
    issue_type TEXT
);

CREATE INDEX IF NOT EXISTS idx_users_company_id ON users(company_id);
CREATE INDEX IF NOT EXISTS idx_company_subscriptions_company_status ON company_subscriptions(company_id, subscription_status);
CREATE INDEX IF NOT EXISTS idx_task_processing_company_status ON task_processing(company_id, task_status);
CREATE INDEX IF NOT EXISTS idx_task_processing_company_service1 ON task_processing(company_id, service1_status);
CREATE INDEX IF NOT EXISTS idx_task_processing_company_service2 ON task_processing(company_id, service2_status);
CREATE INDEX IF NOT EXISTS idx_task_history_task_id ON task_status_history(task_id);
CREATE INDEX IF NOT EXISTS idx_task_history_changed_at ON task_status_history(changed_at);
CREATE INDEX IF NOT EXISTS idx_login_audit_identifier_created_at ON login_audit_logs(identifier, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_password_reset_user_created_at ON user_password_reset_tokens(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_company_created_at ON audit_logs(company_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_company_status ON jobs(company_id, status);
CREATE INDEX IF NOT EXISTS idx_job_runs_job_id_started_at ON job_runs(job_id, started_at DESC);

COMMIT;
