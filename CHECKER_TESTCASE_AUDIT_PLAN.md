# Checker & Testcase Audit — Remediation Plan

**Asl audit:** 2026-06-18
**Yangilangan:** 2026-06-23 (kodning hozirgi holatiga to'liq qayta tekshiruv)
**Asos:** checker, testcase, multi-tenant izolyatsiya, xavfsizlik va infratuzilma auditi

Har element: **muammo → joy (`file:line`) → tuzatish → qabul mezoni**. `file:line` audit paytida tasdiqlangan; implement paytida Edit'dan oldin qayta tekshiriladi.

---

## Holat jadvali (2026-06-23)

| # | Topilma | Og'irlik | Holat |
|---|---|---|---|
| **A1** | Checker webhook multi-agent'ni ishlatmaydi | 🔴 Arxitektura | ✅ **TUZATILGAN** |
| **S1** | Audit log credential'larni plaintext yozadi | 🔴 Bloker | ✅ **TUZATILGAN** |
| **S2** | Global Gemini kalitlar plaintext | 🔴 Bloker | ✅ **TUZATILGAN** |
| **S4** | Webhook auth ixtiyoriy + timing-leak | 🟠 Yuqori | ✅ **TUZATILGAN** |
| **S5** | Manual endpointlar auth'siz + decrypted kalit | 🟡 O'rta | ✅ **TUZATILGAN** |
| **P1** | DB connection pool yo'q + connection leak | 🔴 Bloker | ✅ **TUZATILGAN** (2026-06-23) |
| **P2** | Versiyalangan migratsiya yo'q + runtime DDL | 🔴 Bloker | ✅ **TUZATILGAN** (2026-06-23) |
| **S3** | Shifrlash KDF zaif + key/secret aralash | 🟠 Yuqori | 🟡 Qisman |
| **C1** | All-skipped → 0% → xato auto-return | 🟠 Yuqori | ✅ **TUZATILGAN** (2026-06-23) |
| **T1** | Agent2 JSON parse zaif/nomuvofiq | 🟠 Yuqori | ✅ **TUZATILGAN** (2026-06-23) |
| **K1** | `pr_cache` o'lik kod + tenant-scope'siz | 🟠 Yuqori | ✅ **TUZATILGAN** (2026-06-23) |
| **L1** | Log faylga kalit suffikslari yoziladi | 🟡 O'rta | ✅ **TUZATILGAN** (2026-06-23) |
| **T2** | `TestCase(...)` qurish bloki dublikat | 🟡 O'rta | ✅ **TUZATILGAN** (2026-06-23) |
| **K2** | Naive `datetime.now()` TIMESTAMPTZ ga | 🟡 O'rta | 🟡 Qisman (run-repolar TUZATILDI; task-layer follow-up) |
| **C2** | Buzilgan regex `\\s` (o'lik yo'lda) | 🟢 Past | ❌ Ochiq |
| **D1** | Run repo'larida company_id filtri yo'q | 🟡 O'rta | ❌ Ochiq (defense-in-depth) |
| **M1** | `tz_pr_checker.py` god-object + o'lik monolit | 🟡 O'rta | ✅ **TUZATILGAN** (2026-06-23, monolit o'chirildi) |
| **M2** | Frontend god-component'lar | 🟡 O'rta | ❌ Ochiq |
| **M3** | `except Exception → return None` (253) + leak | 🟡 O'rta | ❌ Ochiq |
| **M4** | Dublikat/o'lik kod (smart_patch, error-builder) | 🟢 Past | 🟡 Qisman (smart_patch o'chirildi; error-builder qoldi) |

### Test holati (2026-06-23, toza test DB bilan tekshirildi)

`make test` (toza schema): **325 passed, 7 failed**. 7 ta xato — bu sessiya tuzatishlaridan EMAS, **oldindan mavjud** (uncommitted refactor + eski test artefaktlari):

| Test | Sabab | Kim |
|---|---|---|
| `test_testcase_generator_*` (4 ta) | mock test case'lar `requirement_ids`siz; yangi multi-agent coverage validatsiyasi ularni tashlaydi (HEAD'da ham fail) | eski mock |
| `test_service1_does_not_mark_returned_when_jira_transition_fails` | mock `get_task` lambda `company_id` qabul qilmaydi (A1 refactor `get_task(company_id=)` qo'shgan) | oldingi refactor — mock yangilash kerak |
| `test_skip_code_only_checks_last_n_comments` | `skip_detector._check_skip_code` `max_comments=2` ni hurmat qilmayapti (True qaytaryapti) — **ehtimoliy REAL bug** | oldingi refactor |
| `test_returned_task_webhook_reentry_flow` | returned task qayta kelganda `task_status` 'progressing'ga reset bo'lmayapti — **ehtimoliy REAL bug** | oldingi refactor |

> **Eslatma:** ikkita "ehtimoliy real bug" (skip_code max_comments, reentry reset) bu audit doirasidan tashqari (uncommitted refactor ishidan) — alohida tekshirilishi kerak. Mahalliy eski `jira_ai_test` DB ham eskirgan (`UNIQUE(task_id)` constraint) — `dropdb jira_ai_test && make test-setup` bilan qayta yaratish tavsiya etiladi.

---

## ✅ Bajarilgan (kontekst uchun, qayta qilinmaydi)

- **A1** — webhook/UI/worker uchalasi bir xil `create_multi_agent_run` + multi-agent engine ishlatadi (`service_runner.py:119,129`, `tzpr_api.py:67,91`, `worker/main.py:127`). `execution_mode="multi_agent"` yorlig'i endi haqiqat.
- **S1** — `internal_rpc_api.py:125-157,299` `_redact_rpc_payload` audit log'da tokenlarni `***REDACTED***` qiladi.
- **S2** — `gemini_default_api_key_1/2` `_SENSITIVE_FIELDS`'da (`credential_crypto.py:35-36`); `platform_repository.py:28-43` Fernet bilan shifrlaydi/dekriptlaydi.
- **S4** — `jira_webhook_handler.py:451-471` `secrets.compare_digest` + `APP_WEBHOOK_REQUIRE_SECRET`/`APP_STRICT_MODE` gate.
- **S5** — manual endpointlar `load_api_session`+`require_company_scope` (`jira_webhook_handler.py:891-916,961-983`); `settings_api.py` kalitlarni `_mask_settings_secrets` bilan maskalaydi.
- **Project-key uniqueness** — `UNIQUE(project_key)` (`001_initial_schema.sql:102`) + `find_project_key_conflicts` saqlashda rad etadi + ko'p-moslikda fail-closed.

**Tekshirilgan va MUAMMO YO'Q:** SQL injection (parametrlangan), parol hashlash (PBKDF2 200k), CORS (aniq origin), frontend auth (httpOnly+sameSite), multi-tenant izolyatsiya (session/schema-darajada, kritik IDOR yo'q).

---

## FAZA A — Production stability blokerlari (sotuvdan oldin SHART, YANGI)

### P1 — DB connection pool + connection leak ✅ TUZATILGAN (2026-06-23)
- **Muammo:** `connect_postgres()` har chaqiruvda yangi `psycopg.connect()` ochardi; Pattern A repo'larda (`task_repository`, auth repolar) `try/finally` yo'q — xato bo'lsa `conn.close()` o'tkazib yuborilardi. Yuqori yuklamada PostgreSQL `max_connections` tugab tizim qulashi mumkin edi.
- **Yechim (amalga oshirildi):** `utils/database/runtime.py` to'liq qayta yozildi —
  - `psycopg_pool.ConnectionPool` global pool (lazy, DSN bo'yicha keshlangan; env: `APP_DB_POOL_MIN_SIZE`/`MAX_SIZE`/`TIMEOUT`/`MAX_IDLE`/`MAX_LIFETIME`/`APP_DB_CONNECT_TIMEOUT`; `check=check_connection` har checkout tiriklik tekshiruvi).
  - `_PooledConnection` proxy: `conn.close()` → poolga QAYTARADI (yopmaydi); `__del__` → leak himoya to'ri (Pattern A repo close'ni unutsa GC qaytaradi); `__enter__/__exit__` ham bor; har checkout'da `row_factory` to'g'ri o'rnatiladi (dict/tuple).
  - **Repo'larga TEGILMADI** — `conn = connect_*(...); conn.close()` pattern o'zgarishsiz ishlaydi (zero blast radius).
  - `close_pool()` qo'shildi; webhook `lifespan` shutdown'da chaqiriladi. `requirements.txt`'ga `psycopg_pool==3.2.6`.
- **Tasdiq:** `tests/test_db_pool.py` (3 test) — close→reuse, per-checkout row_factory, **close'siz xatoda leak yo'q** (kichik pool + 3s timeout bilan, leak bo'lsa osilib qolardi — o'tdi). Test to'plami **63s → 21s** (3x tez, ulanish qayta ishlatish samarasi). 328 passed.
- **Eslatma:** Pattern A repo'larda `try/finally` hali yo'q (proxy `__del__` qoplaydi). To'liq tozalik uchun ularni `with` CM'ga o'tkazish — kelajak ixtiyoriy refactor (M3 bilan).

### P2 — Versiyalangan migratsiya + runtime DDL'ni olib tashlash ✅ TUZATILGAN (2026-06-23)
- **Muammo:** `schema_version` jadvali yo'q edi; run-repo `_db.py` `_connect()` HAR DB ulanishida `ensure_*_tables` (DDL) bajarardi (per-query DDL, concurrent race, overhead). Webhook lifespan umuman init chaqirmasdi — jadvallar lazy hot-path orqali yaratilardi.
- **Yechim (amalga oshirildi):**
  - **`utils/database/migrations.py`** yangi — `schema_migrations` jadvali (version, applied_at) + `run_migrations()`: `database/postgresql/NNN_*.sql` fayllarni tartib bilan bir martadan qo'llaydi (recorded), keyin runtime jadvallarni (checker_*/analysis_*/job_queue*/web_sessions) startup'da BIR MARTA `IF NOT EXISTS` bilan ensure qiladi. DSN bo'yicha keshlangan (idempotent, test'da DSN o'zgarsa qayta ishlaydi).
  - **Hot-path DDL olib tashlandi:** `checker_run_db`/`analysis_run_db`/`ai_usage_db` `_connect()` endi faqat ulanish qaytaradi (DDL yo'q) — `ensure_*` chaqiruvlari va importlari o'chirildi.
  - **Startup'ga ulandi:** webhook `lifespan` (barcha API router shu app'da), `worker/main.py`, `monitoring_api`, conftest — hammasi `run_migrations()`/`init_db()` orqali. `task_db.init_db()` endi `run_migrations()` ga delegatsiya qiladi.
- **Tasdiq:** bo'sh DB'da faqat `run_migrations()` → 30 jadval + `schema_migrations` (001 recorded). `tests/test_db_migrations.py` (3 test: baseline recorded, runtime tables created, idempotent). 331 passed.
- **Eslatma (kelajak):** company_settings yozish yo'lidagi idempotent `_ensure_company_*` ALTER'lar qoldi (kamdan-kam, IF NOT EXISTS no-op — hot-path EMAS). Kelajakda 002+.sql migratsiya fayllariga ko'chirilishi mumkin. Hozir runtime jadvallar Python `ensure_*` orqali (tested) — yangi schema o'zgarishi uchun `NNN_*.sql` fayl qo'shiladi (runner avtomatik qo'llaydi).

---

## FAZA B — Funksional buglar (yuqori og'irlik)

### C1 — All-skipped → 0% ball → xato auto-return
- **Muammo:** barcha requirement skip/technical bo'lsa `verifiable_total <= 0` → `0` qaytadi → eng yomon ball → `auto_return_enabled=True` da xato auto-return. `service_runner.py` auto-return faqat `compliance_score < threshold` ni tekshiradi, `run_state="manual_review"` ni e'tiborsiz qoldiradi. `compliance_score is not None` guard ishlamaydi (presenter har doim `int` qaytaradi).
- **Joy:** `services/checkers/tzpr_presenters.py:42-44`; auto-return `services/webhook/service_runner.py:191-204`; sentinel manbai `agent3.py:326-335` (`run_state="manual_review"`), `tzpr_result_builder.py:95-96` (`qa_recommendation.action="manual_review"`).
- **Tuzatish:** webhook auto-return'dan oldin `run_state=="manual_review"` (yoki `qa_recommendation.action`) ni tekshirish — manual_review bo'lsa auto-return qo'zg'almaydi. Yoki presenter all-skipped (verifiable=0, skipped>0) holatda sentinel (`None`) qaytarib, `service_runner` buni qaytarib bo'lmaydigan deb hisoblasin.
- **Qabul mezoni:** 3 ta requirement, hammasi qonuniy skip → auto-return qo'zg'almaydi (test bilan); haqiqatan bo'sh inventar (0 requirement) alohida holat.

### T1 — Agent2 JSON parse'ni birlashtirish
- **Muammo:** Agent2 (eng muhim AI chaqiruvi) zaif `_parse_test_cases` (naive `find('{')`/`rfind('}')`) ishlatadi; Agent1/Agent3 mustahkam `parse_gemini_json` ishlatadi.
- **Joy:** `services/generators/testcase_generator.py:1108,1148-1149` (Agent2 oqimi `:314,347`); ishonchli parser `utils/ai/gemini_json` (Agent1 `:653`, Agent3 `:893`).
- **Tuzatish:** Agent2 parse'ni avval `parse_gemini_json` orqali o'tkazish, faqat muvaffaqiyatsizlikda eski repair'ga tushish.
- **Qabul mezoni:** uchala agent bir xil parser yo'lidan; prose-preamble + brace holatlarida test o'tadi.

### K1 — `pr_cache` o'lik kodini o'chirish
- **Muammo:** `get_pr_*`/`get_skip_cache` ni hech kim o'qimaydi (faqat yoziladi/tozalanadi); jarayon-xotira dict ko'p worker rejimida ishlamaydi; tenant-scope yo'q (latent cross-tenant leak).
- **Joy:** `utils/pr_cache.py`; yozuvchilar `tz_pr_checker.py:445-463,923`, `jira_webhook_handler.py:616`; tozalash `service_runner.py:328`.
- **Tuzatish:** `utils/pr_cache.py` va barcha `set_*`/`clear_task_cache` chaqiruvlarini o'chirish. (S1→S2 PR handoff kerak bo'lsa — multi-agent run snapshot'da allaqachon bor.)
- **Qabul mezoni:** modul va chaqiruvlar olib tashlangan; testlar yashil; import xatosi yo'q.

---

## FAZA C — Xavfsizlik qoldig'i

### S3 — Kript KDF'ni kuchaytirish + key/secret ajratish
- **Muammo:** Fernet kaliti salt'siz `sha256(secret)`dan olinadi (lug'at/brute-force'ga ochiq); `APP_CREDENTIALS_MASTER_KEY` yo'q bo'lsa `SUPER_ADMIN_PASSWORD` ga fallback (autentifikatsiya paroli = shifrlash kaliti).
- **Joy:** `utils/auth/credential_crypto.py:66-71` (fallback), `:120-125` (`_build_fernet` sha256).
- **Tuzatish:**
  - KDF'ni scrypt yoki PBKDF2 (statik per-install salt + yetarli iteratsiya) ga o'tkazish.
  - `SUPER_ADMIN_PASSWORD` fallback'ni olib tashlash (yoki kamida production'da bloklash) — alohida `APP_CREDENTIALS_MASTER_KEY` talab qilish.
  - Mavjud shifrlangan qiymatlar uchun re-encrypt migratsiya (`scripts/reencrypt_credentials.py`).
- **Qabul mezoni:** master key yo'q + production'da startup xato; passphrase fallback olib tashlangan; eski qiymatlar migratsiya bilan o'qiladi.

---

## FAZA D — Tozalash (o'rta-past)

### L1 — Log'dan kalit suffikslarini olib tashlash
- **Joy:** `utils/ai/gemini_helper.py:75` (api_key oxirgi 6 belgi); `utils/figma/figma_client.py:373,381` (token suffiks, `len<=6` bo'lsa TO'LIQ token).
- **Tuzatish:** kalit/token suffikslarini log'dan butunlay olib tashlash (faqat "kalit #N ishlatilmoqda" deb yozish).

### T2 — `TestCase(...)` dublikatini olib tashlash
- **Joy:** `testcase_generator.py:1178-1190` va `:1213-1225` (Agent2 yo'lida 11-maydonli qurish 2 marta); mavjud helper `_testcase_from_dict` `:877-890`.
- **Tuzatish:** Agent2 yo'lini ham `_testcase_from_dict` ga o'tkazish (T1 bilan birga).

### K2 — Timezone-aware vaqt
- **Joy:** `utils/database/analysis_run_repository.py:21-22` (`_now_iso` → `datetime.now()`).
- **Tuzatish:** `datetime.now(timezone.utc)` yoki Postgres `DEFAULT now()`.

### C2 — Buzilgan regex (yoki o'lik yo'lni o'chirish)
- **Joy:** `tz_pr_checker.py:1404,1406` — `[.!:,\\s]` raw-string ichida literal `\`+`s`.
- **Tuzatish:** `[.!:,\s]`. Bu kod A1'dan keyin o'lik yo'lda — M1 bilan birga butunlay o'chirilsa, alohida tuzatish shart emas.

---

## FAZA E — Modullashish va texnik qarz (sotuvga bloker emas)

### M1 — `tz_pr_checker.py` (2399q) tozalash
- O'lik monolit yo'lni (`analyze_task`, `_perform_ai_analysis`, `_split_analysis_sections`, `_group_analysis_items`, `_parse_requirement_item`, `_extract_compliance_score`) olib tashlash yoki alohida `tzpr_text_parser.py` ga ko'chirish. Faqat `scripts/debug_tzpr_gemini_flow.py` ushlab turibdi — skriptni ham yangilash. Ikkita score yo'lini bittaga keltirish.

### M2 — Frontend god-component'lar
- `settings-panel.tsx` (2230q, 42 `useState`), `super-admin-panel.tsx` (1760q) ni tab/card bo'yicha sub-komponentlarga bo'lish. `maskSecret` takrorini bitta util'ga.

### M3 — Xato boshqaruvi
- Repository qatlamidagi `except Exception → return None` (253) larni aniqroq qilish (topilmadi vs DB xatosi); P1 (try/finally) bilan birga.

### M4 — Dublikat va o'lik kod
- **Checker:** `compact_requirements` (`agent2.py:278`+`agent3.py:181`), `VALID_SOURCES` birlashtirish; 3 error-builder (`tzpr_agent_runner.py:1175-1288`) parametrlash; `SMART_PATCH_AVAILABLE`/`_log_smart_patch_status` (`tz_pr_checker.py:52,2356`) o'chirish; sehrli raqamlarni `tzpr_constants.py` ga.
- **Testcase:** ishlatilmaydigan `PRHelper`/`pr_helper`, `_build_figma_summary_text`, `_is_tz_absent_or_minimal`, `dev_objections` dead param olib tashlash; stale docstring yangilash.
- **Frontend:** `types.ts` (1046q) drift — backend bilan moslik tekshiruvi yoki kod-generatsiya.

### D1 — Run repo'lariga company_id filtri (defense-in-depth)
- `checker_run_repository.py:314,366` va analoglar `get_*_run`/`build_*_snapshot` ga ixtiyoriy `company_id` parametri qo'shib repository qatlovida ham cheklash.

---

## Bajarish tartibi (tavsiya)

1. **FAZA B** (C1, T1, K1) — eng katta foyda/risk nisbati, kichik diff, darrov sotuvga ta'sir qiladi.
2. **FAZA A** (P1, P2) — production barqarorlik, kattaroq ish (alohida PR).
3. **FAZA C** (S3) + **FAZA D** (L1, T2, K2, C2) — xavfsizlik qoldig'i va tozalash.
4. **FAZA E** — refactor, alohida PR'larda, test qoplamasi bilan.

**Operatsion (kod emas, deploy):** production'da `APP_STRICT_MODE=true` + `APP_CREDENTIALS_MASTER_KEY` + `APP_WEBHOOK_REQUIRE_SECRET=true` majburiy; backend 8000-portni nginx orqasiga; `PROGRESS_LOG.md` git'dan chiqarish.

Har faza yakunida: `make test-all` (DB testlari `APP_TEST_POSTGRES_DSN` bilan) + o'zgargan yo'l uchun yangi unit test.
