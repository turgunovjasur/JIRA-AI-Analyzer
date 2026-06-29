# CLAUDE.md — QA-Assistant

Bu fayl Claude uchun loyiha arxitekturasi, qarorlar va muhim qoidalar.
Har yangi suhbatda avtomatik yuklanadi.

---

## Loyiha maqsadi

JIRA task "Testing" statusga tushganda webhook signal keladi.
Tizim 2 ta servis ketma-ket ishlatadi:
- **Servis-1** — TZ va GitHub PR mosligini Gemini AI tahlil qiladi → JIRA comment
- **Servis-2** — Test case'lar yaratadi → JIRA comment

---

## Arxitektura

```
JIRA webhook → jira_webhook_handler.py (orchestrator)
  → tizim filtrlari (status, issue type, assignee)
  → DB holat tekshiruvi (duplicate prevention)
  → AI_SKIP tekshiruvi
  → queue_manager → AI lock → rate limit wait
  → Servis-1: MULTI-AGENT checker (create_multi_agent_run + run_multi_agent_for_webhook) → JIRA comment
  → 15s kutish
  → Servis-2: MULTI-AGENT testcase (create_testcase_run + run_testcase_for_webhook) → JIRA comment
```

**MUHIM:** webhook, UI va worker — uchalasi ham AYNAN bir xil multi-agent engine'ni
ishlatadi. Checker:
agent1 (scope) → agent1b (merge) → agent2 (verify, parallel) → agent3 (arbiter).
Testcase: agent1 (reuse checker contract) → agent2 (yozish) → agent3 (audit).

---

## Asosiy fayllar

| Fayl | Maqsad |
|---|---|
| `services/webhook/jira_webhook_handler.py` | Webhook endpoint, orchestrator, singleton factory |
| `services/webhook/service_runner.py` | S1 va S2 ishga tushirish logikasi |
| `services/webhook/queue_manager.py` | AI queue lock, rate limiting |
| `services/webhook/retry_scheduler.py` | Blocked tasklar uchun qayta urinish |
| `services/webhook/skip_detector.py` | AI_SKIP kodi va re-check aniqlash |
| `services/webhook/error_handler.py` | Xato aniqlash, comment yozish |
| `services/webhook/testcase_webhook_handler.py` | S2 trigger va comment yozish |
| `services/checkers/tzpr_orchestrator.py` | Multi-agent checker engine (agent1→1b→2→3) |
| `services/checkers/tzpr_agent_runner.py` | Agentlarni ishga tushirish + JSON parse |
| `services/checkers/tzpr_multi_agent.py` | create_multi_agent_run / run_multi_agent_for_webhook |
| `services/checkers/tzpr_data_fetch.py` | DataFetchMixin — JIRA/PR/Figma/TZ olish |
| `services/checkers/tzpr_result_builders.py` | ResultBuildersMixin — natija/matritsa qurish |
| `services/checkers/tzpr_text_parser.py` | TextParserMixin — matn/patch parse |
| `services/checkers/tzpr_presenters.py` | compliance score (agent3 count'laridan) + final text |
| `services/generators/testcase_generator.py` | Multi-agent testcase (agent1→2→3); PR YO'Q |
| `core/module_start_preflight.py` | Run-start gate: credential + Gemini kvota tekshiruvi |
| `core/setup_checks/` | UI/webhook setup check engine, registry va profillar |
| `core/tz_helper.py` | TZHelper + CommentSeparator |
| `core/base_service.py` | Servislar uchun umumiy asos (lazy loading) |
| `core/pr_helper.py` | GitHub PR qidirish va olish |
| `core/constants.py` | Return reason kodlari |
| `utils/database/runtime.py` | psycopg connection POOL + leak-safe proxy |
| `utils/database/migrations.py` | Versiyalangan schema migratsiya (schema_migrations) |
| `utils/database/task_db.py` | PostgreSQL holat boshqaruvi |
| `utils/database/quota_repository.py`, `quota_db.py` | Global Gemini bepul-kvota (per company+module) |
| `utils/auth/auth_db.py` | Multi-tenant DB + get_credential_readiness |
| `utils/auth/auth_config_helpers.py` | Credential resolution + gemini_source |
| `utils/jira/jira_client.py` | JIRA API (task, PR link, Figma link) |
| `utils/jira/jira_adf_formatter.py` | S1 uchun ADF document builder |
| `utils/jira/testcase_adf_formatter.py` | S2 uchun ADF document builder |
| `utils/ai/gemini_helper.py` | Gemini AI (multi-key fallback, model fallback, retry) |
| `utils/github/github_client.py` | GitHub PR API |
| `config/app_settings.py` | Barcha sozlamalar (dataclass-based, JSON) |

---

## To'liq oqim (webhook → comment)

```
1. JIRA webhook POST /webhook/jira
2. Event tekshiruvi: faqat jira:issue_updated
3. Changelog: status o'zgardimi?
4. Kompaniya: company-specific endpoint yoki JIRA Project Key(lar) mappingi orqali topiladi
5. Trigger status: yangi status ro'yxatdami?
6. Filtrlar: issue type, assignee exclusion
7. DB: task holati tekshiruvi (duplicate, reset if needed)
8. AI_SKIP: skip_code comment da bormi? → S1 skip, S2 baribir ishlaydi
9. queue_manager: AI lock olish (timeout bo'lsa blocked)
10. Rate limit: min interval kutish (6s default)

--- Servis-1 (multi-agent checker) ---
11. company credentials olish
12. return_reason DB dan o'qish → is_recheck aniqlash
13. create_multi_agent_run + run_multi_agent_for_webhook(run_id):
    a. _collect_context: `checker_engine` setup profili
       (`jira_fetch → min_tz_check → pr_check → tz_build → figma_check`)
    b. agent1 (scope) → agent1b (merge) → agent2 (verify, parallel) → agent3 (arbiter)
    c. har agent: GeminiHelper.analyze() → parse_gemini_json (markaziy parser)
    d. compliance score: agent3 count'laridan (tzpr_presenters); all-skipped → None (manual review)
14. Muvaffaqiyatli → ADF comment yozish (fallback: simple)
15. service1_done, score DB ga
16. Score < threshold → task qaytarish + return notification comment
    → set_return_reason(WARN_LOW_SCORE)

--- Servis-2 (multi-agent testcase) ---
17. Shartlar tekshiruvi (S1 done, score OK, not returned)
18. create_testcase_run + run_testcase_for_webhook(run_id):
    a. `testcase_engine` setup profili (`jira_fetch → min_tz_check → figma_check → tz_build`)
    b. agent1 (checker contract reuse) → agent2 (yozish) → agent3 (audit)
    c. parse_gemini_json → TestCase objects → deterministik finalize
19. ADF comment yozish (fallback: simple)
20. service2_done DB ga

--- Retry ---
21. _blocked_retry_scheduler() har 60s tekshiradi
22. blocked_retry_at <= NOW bo'lsa qayta urinadi
```

---

## DB sxemasi (`task_processing`, v5)

| Ustun | Qiymatlar |
|---|---|
| `task_status` | none / progressing / completed / returned / error / blocked |
| `service1_status` | pending / done / error / skip / blocked |
| `service2_status` | pending / done / error / blocked |
| `compliance_score` | 0–100 (int) |
| `return_count` | qaytarilganlar soni |
| `return_reason` | WARN_LOW_SCORE / WARN_MIN_TZ / ... (v5) |
| `blocked_at` | bloklangan vaqt |
| `blocked_retry_at` | qayta urinish vaqti |
| `company_id` | multi-tenant (v4) |

---

## Return Reason Codes (`core/constants.py`)

JIRA comment boshiga yoziladi: `[AI_S1][WARN_MIN_TZ]`
DB `return_reason` da saqlanadi.

| Kod | Sabab | Keyingi safar |
|---|---|---|
| `WARN_LOW_SCORE` | Score past | dev_objections Gemini ga → reanalysis |
| `WARN_MIN_TZ` | TZ qisqa | yangi tahlil, objections yo'q |
| `WARN_NO_PR` | PR topilmadi | yangi tahlil, objections yo'q |
| `WARN_PR_NOT_MERGED` | PR merge emas | yangi tahlil, objections yo'q |
| `WARN_AI_TIMEOUT` | AI ishlamadi | retry, objections yo'q |
| `ERR_UNKNOWN` | Kutilmagan xato | yangi tahlil, objections yo'q |

`RECHECK_REASONS = {WARN_LOW_SCORE}` — faqat shu kodda dev objections ishlatiladi.

---

## AI Comment Marker tizimi

Har AI comment boshida marker bo'ladi:
- `[AI_S1]` — Servis-1 (jira_adf_formatter.py, error_handler.py)
- `[AI_S2]` — Servis-2 (testcase_adf_formatter.py)

`CommentSeparator.separate(comments, marker='S1')`:
- `dev_before` — marker dan oldingi dev izohlar (kontekst)
- `dev_after` — marker dan keyingi dev izohlar (etirozlar)
- Bo'sh comment lar o'tkazib yuboriladi (faqat bo'sh emas shartli)

---

## Servis-1 recheck logikasi

```python
return_reason = task_db.get('return_reason')
is_recheck = return_reason in RECHECK_REASONS  # faqat WARN_LOW_SCORE

# Faqat is_recheck=True da:
# - dev_objections Gemini promptiga qo'shiladi
# - JIRA commentda "Developer izohlari — AI ko'rdi" dropdown ko'rinadi
```

---

## Servis-2 da recheck YO'Q

Servis-2 hech qachon taskni qaytarmaydi.
Task faqat Servis-1 tomonidan qaytariladi.
Servis-2 faqat Servis-1 muvaffaqiyatli o'tgandan keyin ishlaydi.
Shuning uchun Servis-2 da is_recheck / dev_objections webhook logikasi kerak emas.

---

## Gemini AI xato turlari va model fallback

**Transient (bir xil kalit bilan retry, kalit freeze EMAS):**
503, 500, 502, 504, unavailable, high demand — backoff: 5s → 10s → 20s

**Model fallback (transient retry tugagach):**
`.env` da `GEMINI_FALLBACK_MODEL` belgilangan bo'lsa, asosiy model (Pro) barcha retrydan o'tib ham 503 bersa → fallback model (Flash) bilan yana 3 marta urinadi.
```
GEMINI_MODEL=gemini-2.5-pro
GEMINI_FALLBACK_MODEL=gemini-2.5-flash
```

**Permanent (kalit freeze, keyingi kalitga o'tish):**
429, 403, quota exceeded, billing — freeze duration: 10 min (sozlanadi)

**Barcha kalitlar freeze:** RuntimeError → WARN_AI_TIMEOUT → BLOCKED

**Transient retry soni:** `queue.gemini_max_retries` sozlamasidan (default 3 → 5s,10s,20s).

---

## Global Gemini bepul-kvota (QA ASSISTANT kalit)

Kompaniya/user o'z Gemini kalitiga ega bo'lmasa, super-admin global default kalit
ishlatiladi. Har modul (checker/testcase) uchun ALOHIDA `GLOBAL_GEMINI_FREE_LIMIT`
(`quota_repository.py`, hozir 3) marta tekin run — per company_id.
- `auth_config_helpers.compute_credential_readiness` → `gemini_source` (user/company/global/none)
- `module_start_preflight`: credential gate (testcase=JIRA, checker=JIRA+GitHub) + kvota gate
- run yaratilganda global bo'lsa `increment_global_quota`; limit tugasa o'sha modul bloklanadi
- UI: `/api/{tzpr,testcase}/start-status` → banner + qolgan urinish; tugaganda run disabled

---

## Sozlamalar tuzilmasi (`config/app_settings.py`)

```
AppSettings
├── webhook_tz_pr: TZPRCheckerSettings
│   ├── trigger_status, return_threshold, auto_return_enabled
│   ├── allowed_issue_types, excluded_assignees
│   ├── min_tz_description_chars
│   ├── visible_sections (AI output filtering)
│   └── skip_code, return_status, footer texts
├── webhook_testcase: WebhookTestcaseSettings
│   ├── auto_comment_enabled, trigger_statuses
│   └── default_test_types, use_adf_format
└── queue: QueueSettings
    ├── gemini_min_interval (6s default)
    ├── task_wait_timeout, checker_testcase_delay
    └── blocked_retry_delay, key_freeze_duration
```

`get_app_settings_for_company(id)` — har webhook da qayta yuklanadi (dynamic).

---

## Multi-tenant tizim

Har bir kompaniyaning o'z API kalitlari va sozlamalari bor.
Webhook kelganda company-specific endpoint ustuvor; legacy endpointda kompaniya `jira_project_keys` mappingi orqali topiladi.
Manual UI'da `1234` kabi raqamli input faqat `jira_project_keys` settingdan project key olib `DEV-1234`ga aylantiriladi.
`company_id` barcha servis funksiyalariga uzatiladi.

---

## DB migratsiya + connection pool (2026-06-23)

**Versiyalangan migratsiya (`utils/database/migrations.py`):**
- `schema_migrations` jadvali qaysi versiya qo'llanganini saqlaydi.
- `run_migrations()` startup'da (webhook lifespan, worker, monitoring) bir marta:
  `database/postgresql/NNN_*.sql` fayllar + runtime jadvallar (checker_runs,
  analysis_runs, job_queue, ai_usage_events, global_gemini_quota, web_sessions).
- Yangi schema o'zgarishi: `database/postgresql/00N_*.sql` fayl qo'shing (runner qo'llaydi).
- **Hot-path'da DDL YO'Q** — `_connect()` endi jadval yaratmaydi.

**Connection pool (`utils/database/runtime.py`):**
- `psycopg_pool.ConnectionPool` (lazy, DSN-keyed; env: `APP_DB_POOL_MAX_SIZE` default 10).
- `connect_postgres()` pooldan ulanish qaytaradi; `conn.close()` poolga QAYTARADI.
- `_PooledConnection` proxy: `__del__` leak-himoya (close unutilsa GC qaytaradi).
- Formula: `jarayonlar × MAX_SIZE ≤ postgres max_connections − zaxira`.

---

## UI Progress animatsiyasi (`ui/components/loading.py`)

`ProgressManager` — barcha AI sahifalarida ishlatiladigan animatsiyali progress widget.

```python
progress = ProgressManager(
    total_steps=4,
    step_labels=["JIRA ma'lumot", "PR qidirish", "AI tahlil", "Natija"]
)
progress.update(1, "JIRA task olinmoqda...")   # step ko'rsatadi
progress.update(3, "AI tahlil qilinmoqda...")  # oldingi steplar ✓ bo'ladi
progress.clear()
```

- `st.components.v1.html()` ishlatadi → JavaScript timer (real-time sekundomer)
- Har step: ✓ yashil (bajarildi) / ↻ aylanuvchi (jarayonda) / raqam kulrang (kutilmoqda)
- Qadamlar orasida chiziq rangi: yashil → gradient → kulrang

**Servislar `update_status("progress", msg)` chaqirishi shart:**
- `core/setup_checks/checks.py` — JIRA, PR, Figma, TZ build bosqichlarida
- `testcase_generator.py` — agent bosqichlari va validation paytida
- `tzpr_orchestrator.py` — multi-agent run holatlari uchun
- `pr_helper.py` — PR tahlil bosqichida

Sahifa callbacklari `msg.lower()` orqali qaysi stepga tegishliligini aniqlaydi.

---

## Test DB sozlash

DB testlari `APP_TEST_POSTGRES_DSN` talab qiladi. Birinchi marta (yoki schema o'zganda):

```bash
# 1) Test DB yaratish va schema qo'llash
make test-setup              # default: jira_ai_test DB

# 2) Testlarni ishga tushirish
export APP_TEST_POSTGRES_DSN=postgresql://localhost/jira_ai_test
make test

# Yoki bir buyruqda:
make test-all
```

- `conftest.py` schema'ni yaratmaydi — faqat `ALTER` va fixture data qo'shadi.
- Schema avval `database/postgresql/001_initial_schema.sql` orqali qo'llanishi shart.
- `APP_TEST_POSTGRES_DSN` yo'qligida DB testlari `skip` bo'ladi (production DB'ga tegmaydi).
- `pytest.ini`da `no_db` marker bor — DB kerak bo'lmagan pure unit testlar uchun.

---

## Kod yozish qoidalari

- **Ssenariy tahlil qil** — yangi feature qo'shishdan avval "bu haqiqatda ishga tushadimi?" deb tekshir
- **Comment kerak emas** — kod o'zini tushuntirsin, faqat noaniq sabablar uchun
- Javoblarni O'zbek tilida ber
