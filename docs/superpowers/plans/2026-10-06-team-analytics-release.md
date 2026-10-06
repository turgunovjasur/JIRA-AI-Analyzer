# Team Analytics production release implementation plan

> Execute natively using executing-plans and TDD. User approved fixes, tests/build, backup, deployment and future Jira metadata collection on 2026-10-06.

**Goal:** Deploy verified Jira-backed analytics with sprint history, historical import and recovery of missed updates.
**Architecture:** Append-only normalized events remain authoritative. Per-issue projections and normalized intervals serve SQL filtering/pagination; a Jira read-only sync service reconstructs histories and discovers project field mappings. Existing worker queue handles periodic reconciliation.
**Tech Stack:** PostgreSQL, FastAPI, requests, Next.js/React, existing Docker Compose.
**Spec:** 2026-10-05-team-analytics-v1.md plus user-approved deployment plan and scope below.

## Constraints and rulings

- Historical import: only currently open tasks in configured projects and the 30 tasks in production status history; user selected this scope.
- Temporary daily points remain browser-only. Existing UI layout and settings (working status/daily hours) stay compatible.
- Preserve task/project/status/assignee IDs, point field ID, sprint IDs and metadata, creation/resolution dates, actor and source timestamps. Do not ingest descriptions, comments, attachments or credentials as analytics data.
- Preserve immutable source events; projection rebuilds do not change them.
- Default working status applies before the first explicit setting, preventing first-delivery ordering from losing work.
- Initial import records complete changelogs before enabling the pilot company. Reconciliation repeats safely using stable event identities and pagination.
- No writes to PROGRESS_LOG.md. Preserve unrelated existing work and other server Compose projects.
- Test DSN must be isolated. Production operations occur only after verified tests/build and backup; existing deployment approval covers them.

## Review focus

- Delayed first event must not lose earlier intervals; snapshot must not override a same-time deletion.
- Imported transitions must attribute old intervals to historical assignees, not current owners.
- Sparse payloads must not reset known fields; changes support reconstruction without complete snapshots.
- Sprint membership may be multiple and change over time; empty lists clear membership.
- Read API must paginate before loading detailed interval histories; tenant/source identities must remain separated.

## Tasks

### 1. Normalize and replay trustworthy histories
Files: services/team_analytics.py, services/team_analytics_history.py, tests/test_team_analytics.py.
- [x] Write failing tests for first-event ordering, numeric tie ordering, sprint metadata, sparse changelog, historical reassignment and replay idempotency.
- [x] Run targeted tests and observe failures.
- [x] Implement normalization, deterministic replay and history reconstruction.
- [x] Run targeted tests until green.

### 2. Persist projections and source metadata
Files: database/postgresql/008_team_analytics_projection.sql, utils/database/team_analytics_repository.py, tests/test_team_analytics_repository.py.
- [x] Write DB integration tests for tenant/source isolation, late ingestion, duplicate import, filter totals across pages and settings rebuild.
- [x] Observe failures; implement task/interval/people/sprint/field-map/sync-state storage.
- [x] Query aggregate totals in SQL and hydrate intervals only for selected page.
- [x] Run DB tests until green.

### 3. Import and reconcile Jira
Files: services/team_analytics_jira.py, services/team_analytics_sync.py, services/team_analytics_ingestion.py, services/worker/main.py, scripts/team_analytics_import.py.
- [x] Test field discovery, complete changelog/search pagination, unavailable issue handling and checkpoint/retry behavior.
- [x] Implement read-only Jira client and project field discovery, initial scoped import, bounded incremental sync and existing-queue scheduling.
- [x] Store checkpoint only after successful persistence; transient errors must not advance it.
- [x] Wire webhook ingestion before AI filters and move synchronous persistence off the async event loop.

### 4. Frontend DRY and stable dates
Files: frontend/src/lib/team-analytics-calculations.ts, frontend/src/lib/team-analytics-time.ts, frontend/src/hooks/use-team-analytics.ts, frontend/src/components/team-analytics-dashboard.tsx.
- [x] Test shared totals/delay calculations and Tashkent midnight splitting.
- [x] Extract data loading/demo aggregation and formulas; use company timezone consistently without displaying a timezone label.
- [x] Verify existing ephemeral points and UI behavior.

### 5. Release verification and deployment
Files: .dockerignore, frontend/.dockerignore, docs/TEAM_ANALYTICS_ROLLOUT.md.
- [x] Exclude credentials, local data/backups and development artifacts from images.
- [x] Run complete backend suite on isolated Postgres; frontend lint/typecheck/tests/build; inspect full feature diff.
- [ ] Commit only feature release files. Build new production images without changing running containers.
- [ ] Backup DB and old image IDs; verify backup and wait for running worker jobs.
- [ ] Deploy backend, migrate, deploy worker/frontend and verify health.
- [ ] Discover fields and import selected history; enable company 1 pilot and verify persisted sprint/assignee/time data against Jira.
- [ ] Confirm periodic reconciliation, API authorization and public page. Preserve new data if code rollback becomes necessary.

## Execution ledger

- 2026-10-06: Production has no analytics module/tables. Existing history contains 52 transitions across 30 task keys, only AI trigger status transitions. Jira reads succeed for companies 1/3/4. Initial pilot is company 1 / DEV; historical scope explicitly selected by user.

- Tasks 1–4: complete. RED→GREEN engine/import/DB/frontend regressions verified. Whole feature fresh-context review completed; fixes include source snapshot timing, independently overridden credentials, expiry gate, moved task reconciliation and HMAC native Jira authentication.
- Ruling: authoritative snapshots use source updated time; availability recovery is a separate empty observation event, protecting concurrent newer webhook fields.
- Verification: 444 backend tests / 17 frontend tests / 3 eval cases green, Ruff clean, typecheck/lint/build pass. Real DEV field discovery passes; 734 open issues and existing 30 history keys are selected, as authorized.

- Ruling: production dependency audit surfaced affected Next.js; patched Next.js/eslint-config-next 16.3.8 and PostCSS 8.5.29 + compatible transitive updates, runtime audit 0. Dev-only braces chain remains upstream; unsafe major downgrade is outside release scope.
- Ruling: fresh Python operator execution exposed implicit importlib.util dependency; add explicit import and fresh-process regression coverage.
- Production backend healthy; additive 005–008 applied. Backup custom dump 1,376,807 bytes / 269 objects restored to isolated temporary DB, verified 30 history keys, temporary DB removed. Rollback images and prior source preserved under /opt/qa-assistant/backups/team_analytics_20261006*.
