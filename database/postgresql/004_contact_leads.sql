BEGIN;

-- 004: Landing/demo "Bepul sinab ko'ring" formasidan kelgan lidlar (potensial mijozlar).
-- Public endpoint (session yo'q) orqali yoziladi; super-admin panelida ko'riladi.
CREATE TABLE IF NOT EXISTS contact_leads (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    role TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'landing',
    status TEXT NOT NULL DEFAULT 'new',
    note TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contact_leads_created_at ON contact_leads (created_at DESC);

COMMIT;
