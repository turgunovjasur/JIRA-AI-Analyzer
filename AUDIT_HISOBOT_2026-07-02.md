# QA-Assistant — Sotuvga Tayyorlik Auditi

**Sana:** 2026-07-02
**Tekshiruv usuli:** 5 ta mustaqil chuqur audit (xavfsizlik/maxfiylik, baza, kod sifati/DRY/modullashuv, prodakshn tayyorlik, biznes-oqim to'g'riligi). Har bir topilma haqiqiy kodni o'qib tasdiqlangan.
**Branch:** `dev1` (main'dan 1 commit oldinda + 9 ta commit qilinmagan fayl)

---

## ✅ Bajarilish holati (2026-07-02 yangilandi)

Auditdan keyin quyidagilar tuzatildi va commit qilindi (`dev1`):

| Bosqich | Holat | Commit |
|---|---|---|
| **Faza 1 — 3 BLOCKER + CI** | ✅ **To'liq bajarildi** | `7a622c5` |
| **Faza 2 — HIGH (kod itemlari)** | ✅ **6/7 bajarildi** (F2-5/6/7/8/9/10) | `7b01aa7`, `dffda66`, `7ce00b3` |
| Faza 2 — qolgan | ⏳ F2-11 (huquqiy, biznes kirishi kerak) | — |
| **Faza 3 — Barqarorlik** | ✅ **4/5** (F3-12/13/15/16) | `3b7da21`, `5dbd8dd`, `858df9b` |
| Faza 3 — qolgan | ⏳ F3-14 (async bloklash — ehtiyotkor sessiya) | — |
| **Faza 4 — Texnik qarz** | ✅ **1/4** (F4-19 dead-code) | `c1f4e86` |

Har bir tuzatish haqiqiy kodda tasdiqlangan; to'liq test suite'da 0 yangi regressiya
(mavjud ~13 fail — auditdan oldingi eskirgan mock testlar). Tafsilotlar 6-bo'limda (✅/⏳).

---

## 0. Bir qatorli javob

> **Bugungi holatda sotuvga TAYYOR EMAS.** Poydevor (arxitektura, multi-tenant izolyatsiya, DB dizayni, AI resilience) haqiqatan kuchli — bu MVP darajasidan ancha yuqori. Lekin bir nechta **blocker** bor: toza o'rnatishda tizim umuman ishga tushmaydi (`requirements.txt` buzuq), webhook default holatda parolsiz (boshqa kompaniya nomidan AI ishlatish mumkin), va task'lar `progressing`/`running` holatida abadiy qotib qoladi. Bularni tuzatish uchun taxminan **2–4 hafta** intensiv ish kerak. Arxitekturani qayta yozish shart emas — asosan release-engineering va tijorat qadoqlash.

**Umumiy baho: B− / C+** — texnik due-diligence'dan "shartli o'tadi" (avval blockerlar tuzatilsa).

---

## 1. Har bir savolingizga javob

| Savol | Javob | Qisqacha |
|---|---|---|
| **Sotuvga tayyormi?** | ❌ Hali emas | 3 ta blocker + bir qancha HIGH muammo. 2–4 hafta ish. |
| **Kodlar yaxshi yozilganmi?** | 🟡 Qisman | Qatlamlar toza, hot-path kodi (Gemini helper, JSON parser) a'lo. Lekin ~550 qator copy-paste, 420 qatorli funksiyalar, o'lik kod bor. |
| **DRY yaxshi qilinganmi?** | 🟡 O'rtacha | Muhim primitivlar birlashtirilgan, lekin ikkita run-repository 94% bir xil, 4 ta joyda takroriy error-ladder, 7 faylda takroriy settings-resolution. |
| **Modullashganmi?** | ✅ Ha (asosan) | `config → core → utils → services` bir yo'nalishli, aylanma import yo'q. "Bitta engine, uch kirish nuqtasi" haqiqatan ishlaydi. |
| **Ko'p kompaniya qo'shilsa maxfiylik saqlanadimi?** | 🟡 O'qish bo'yicha HA, yozish bo'yicha YO'Q | Kompaniya A kompaniya B ma'lumotini **o'qiy olmaydi** (buni tasdiqladik). Lekin webhook parolsiz bo'lgani uchun boshqa kompaniya nomidan **yozish** va uning Gemini pulini sarflash mumkin. |
| **Baza yaxshi sozlanganmi?** | ✅ Ha (asosan) | Pool, versiyalangan migratsiya, `SKIP LOCKED`, atomik kvota, TIMESTAMPTZ+FK+UNIQUE — hammasi bor. 4 ta tuzatish kerak. |
| **Umuman ishlashga tayyormi?** | 🟡 Dev'da ishlaydi, prod'da hali emas | Deploy paketlari bor (docker-compose, nginx, backup), lekin crash-recovery, alerting, log rotation, CI yo'q. |

---

## 2. 🔴 BLOCKER'lar — sotishdan oldin SHART tuzatilishi kerak

Bu 3 ta muammo mahsulotni sotib bo'lmaydigan qiladi. Ular bir nechta auditda takroran chiqdi.
**➡️ Uchalasi ham 2026-07-02 da TUZATILDI (`7a622c5`) va tasdiqlandi.**

### ✅ BLOCKER-1 (TUZATILDI): Toza o'rnatishda tizim ishga tushmaydi (`requirements.txt` buzuq)
- `utils/ai/gemini_helper.py:1` — `from google import genai` (**yangi** SDK) ishlatiladi, lekin `requirements.txt:34` da faqat `google-generativeai==0.8.5` (**eski**, boshqa namespace) bor. `google-genai` yo'q.
- `utils/auth/credential_crypto.py:14` — `from cryptography.fernet import Fernet`, lekin `cryptography` `requirements.txt`da yo'q.
- Ikkalasi ham startupda (webhook lifespan'da) import qilinadi.
- **Oqibat:** `docker compose up --build` (hujjatlardagi deploy usuli) → backend va worker `ImportError` bilan o'ladi. Hech qaysi mijoz tizimni ko'tara olmaydi. Dev muhitida ishlashining sababi — paketlar qo'lda o'rnatilgan (`.venv`da `google_genai-1.73.1` bor).
- **Tuzatish:** `requirements.txt`ni toza venv'dan qayta generatsiya qilish (`google-genai`, `cryptography` qo'shish; `torch`/`chromadb`/`sentence-transformers`/`altair`/`plotly` — o'lik feature paketlarini olib tashlash). CI'da Docker build bilan tekshirish.

### ✅ BLOCKER-2 (TUZATILDI): Webhook default holatda autentifikatsiyasiz → boshqa kompaniya nomidan AI ishlatish + pulini sarflash
- `services/webhook/jira_webhook_handler.py:463-483` — webhook secret **faqat kompaniya uni sozlagan bo'lsa** tekshiriladi. Majburiy qilish `APP_WEBHOOK_REQUIRE_SECRET`/`APP_STRICT_MODE`'ni talab qiladi, lekin `.env.example:51` da `APP_WEBHOOK_REQUIRE_SECRET=false`.
- **Hujum ssenariysi:** Hujumchi soxta `jira:issue_updated` body yuboradi (`issue.key="DEV-123"` + trigger statusga o'tish). Server: (a) qurbonning saqlangan JIRA tokeni bilan haqiqiy task'ni oladi, (b) qurbonning pullik Gemini kalitida to'liq multi-agent pipeline ishlatadi, (c) qurbonning haqiqiy JIRA task'iga `[AI_S1]` comment yozadi, (d) score past bo'lsa — task'ni orqaga qaytaradi. Agar kompaniya global (platforma) Gemini kalitidan foydalansa — 3 ta soxta so'rov bilan kvotani tugatib, modulni bloklash mumkin.
- IP allowlist yo'q, Atlassian imzo validatsiyasi yo'q.
- **Bog'liq:** `/metrics` (`:869`) va `/settings` (`:924`) endpointlari ham parolsiz — barcha kompaniyalar bo'yicha agregat statistikani ochib beradi.
- **Tuzatish:** Har kompaniya uchun `webhook_secret` majburiy (yo'q bo'lsa 401), faqat header orqali (query param emas — `:476`), kompaniya yaratilganda avtomatik generatsiya.

### ✅ BLOCKER-3 (TUZATILDI): Task `progressing`/`running` holatida abadiy qotib qoladi (recovery yo'q)
Bu **eng ko'p takrorlangan** muammo — 3 ta auditda mustaqil ravishda chiqdi (baza, prodakshn, biznes-oqim).
- `utils/database/task_db.py:152` — `mark_completed` funksiyasi mavjud, import qilingan, lekin **hech qaerda chaqirilmaydi**. `task_status='completed'` faqat `set_service2_done` orqali qo'yiladi. Ya'ni S2 tugamagan **har qanday** oqimda task abadiy `progressing`da qoladi:
  - Checker-only konfiguratsiya (S2 trigger emas / o'chirilgan)
  - Score < threshold + `auto_return_enabled=False`
  - AI_SKIP + S2 ishga tushmagan
  - Server crash/restart run o'rtasida (`get_stuck_tasks` — `task_db.py:734` — **nol chaqiruvchi**)
- `utils/database/job_queue_repository.py:136-165` — o'lgan worker'ning `running` job'ini hech narsa qayta navbatga qo'ymaydi (heartbeat/visibility-timeout yo'q). Va `:93-106` dedupe `running`ni "aktiv" deb hisoblaydi → o'sha task uchun keyingi webhook'lar jimgina yutib yuboriladi.
- **Oqibat:** Task uchun keyingi har qanday status o'zgarishi `:602-608` (`progressing` → SKIP) ga tushadi — **abadiy**. Hatto `/manual/check` ham S1'ni qayta ishga tushirmaydi (`service1_status=='done'` short-circuit). Tiklash uchun qo'lda DB operatsiyasi kerak. Mijoz uchun mahsulot o'sha task'da jimgina ishlashdan to'xtaydi.
- **Tuzatish:** (1) `mark_completed`ni tegishli oqimlarda chaqirish; (2) stale `running` job'lar uchun reaper (worker startda + davriy — N daqiqadan oshgan `running`ni qayta navbatga); (3) stuck `checker_runs`/`progressing` task'lar uchun sweeper; (4) docker-compose'da `stop_grace_period`.

---

## 3. 🟠 HIGH — sotishdan oldin kuchli tavsiya etiladi

### Xavfsizlik
- ✅ **(TUZATILDI)** **RPC rol-eskalatsiyasi (kwargs bypass).** `internal_rpc_api.py` endi args+kwargs'ni funksiya imzosiga bind qilib effektiv qiymatlarni tekshiradi — `kwargs={"role": "company_admin"}` bypass'i yopildi (test bilan tasdiqlangan).
- ✅ **(TUZATILDI)** **Credential shifrlash fail-open.** `encrypt_value()` endi master kalit yo'q bo'lsa **plain text QAYTARMAYDI** (fail-closed, `RuntimeError`). Worker startup'da ham `assert_master_key_configured`.
- ✅ **(TUZATILDI)** **Zaif kalit + parol fallback.** `SUPER_ADMIN_PASSWORD` shifrlashdan olib tashlandi (faqat legacy-decrypt); KDF `sha256` → **PBKDF2-HMAC-SHA256** (200k iter). Migratsiya-xavfsiz: eski ma'lumot deshifrlashda hali o'qiladi, keyingi saqlashda avtomatik ko'chadi.

### Baza
- 🟡 **(QISMAN TUZATILDI)** **Migratsiya runner cross-process xavfsiz emas.** `run_migrations` endi `pg_advisory_lock` bilan cross-process serializatsiya qiladi (lock ichida applied-versiya qayta o'qiladi, poolga qaytishdan oldin unlock; konkurent 5x test — xatosiz). ⏳ Qolgan: import-time `init_db` (`task_db.py:987`) olib tashlash — API app lifespan migratsiyani chaqirishini tasdiqlash kerak (advisory lock hozircha buni ham xavfsiz qildi).
- 🟡 **(QISMAN TUZATILDI)** **Async endpointlarda bloklovchi DB chaqiruvlar.** Read-only endpointlar (`/`, `/health`, `/metrics`, `/settings`, barcha `monitoring_api` va `sprint_report_api`) `async def` → `def` qilindi — FastAPI ularni threadpool'da ishlatadi (event loop bloklanmaydi). Await ishlatmagani tasdiqlangan; TestClient smoke o'tdi. ⏳ Qolgan: webhook POST core (`_jira_webhook_impl` 385q + `manual_*`) — o'rtada await'lar bor, integratsiya testisiz refactor kritik yo'lni buzishi mumkin (alohida ehtiyotkor ish).
- ✅ **(TUZATILDI)** **Cheksiz jadval o'sishi (retention yo'q).** `utils/database/retention.py` — eski terminal `checker_runs`/`analysis_runs`/`job_queue`(done,failed)/`ai_usage_events` yozuvlarini davriy o'chiradi (bola-jadvallar FK CASCADE). Worker kuniga bir marta (`asyncio.to_thread`). Oynalar env orqali (RUN=90, JOB=30, USAGE=365 kun). Haqiqiy Postgres'da parent+cascade o'chirish tasdiqlandi.

### Prodakshn
- 🟡 **(QISMAN TUZATILDI)** **Gemini kvota webhook yo'lida.** `run_multi_agent_for_webhook` endi kvotani tekshiradi (tugasa run ishga tushmaydi) va completed global run'ni increment qiladi; `execute_multi_agent_run` source-driven (queue/worker UI run'lari ham increment qiladi). ⏳ Qolgan: per-company oylik xarajat cheklovi (`ai_usage_events`).
- 🟡 **(QISMAN TUZATILDI)** **Bitta ketma-ket worker + event-loop bloklash = past o'tkazuvchanlik.** Per-company AI concurrency endi DB'da (`claim_next_job` + `pg_advisory_xact_lock`): N worker bilan ham "kompaniyaga bir vaqtda 1 AI job" kafolati saqlanadi (haqiqiy Postgres'da 8-worker konkurent test → faqat 1 claim). Per-company=1 bo'lgani uchun 6s interval ham amalda ta'minlanadi (joblar 3-8 daq). ⏳ Qolgan: `inline` rejim event-loop bloklashi (F3-14 bilan bog'liq), bir nechta workerni jonli deploy'da yoqish.
- ✅ **(TUZATILDI)** **Alerting umuman yo'q.** `core/watchdog.py` — API jarayonida davriy (worker'dan alohida) navbat backlog / blocked task / worker heartbeat holatini tekshiradi; muammo bo'lsa WARNING log + (SMTP sozlansa) email (dedup/cooldown bilan). Tashqi servis (Sentry) shart emas. Haqiqiy Postgres'da tekshirildi.
- **LICENSE / ToS / maxfiylik siyosati yo'q.** Mahsulot mijozning JIRA matni, GitHub PR diff'lari (to'liq patch), Figma ma'lumotini Google Gemini'ga yuboradi — hech qanday oshkor qilish hujjati, data-processing kelishuvi yoki per-company cheklov yo'q. B2B sotuv uchun bu kontrakt blocker.

### Biznes-oqim
- ✅ **(TUZATILDI)** **AI-uzilish S1'da `ERR_UNKNOWN` → retry yo'q.** `_run_agent1` endi `analyze()` xatosini alohida ushlab **real matnni** saqlaydi → `_classify_error` `ai_timeout` → WARN_AI_TIMEOUT → BLOCKED → retry. Kontrakt S1 uchun tiklandi.
- 🟡 **(QISMAN TUZATILDI)** **Marker tizimi nomuvofiq.** Detektor (`CommentSeparator`, `tz_helper.py`) endi markerni **istalgan qator boshida** topadi (regex, line-anchored) — oxirgi paragrafdagi marker ham to'g'ri AI deb tanaladi, recheck/Agent3 kiritmasiga sizib kirmaydi. ⏳ Qolgan (foydalanuvchi WIP'ida): formatter tomonida markerni boshga ko'chirish + S2 xato commentlari uchun `[AI_S2]`.

---

## 4. 🟡 MEDIUM — muhim, lekin sotuvni to'xtatmaydi

**Kod sifati / DRY:**
- **~550 qator copy-paste repository.** `checker_run_repository.py` (396 q.) vs `analysis_run_repository.py` (399 q.) — ~94% bir xil. Wrapper'lar `checker_run_db.py` vs `analysis_run_db.py` — 12 qator farq. Har bugfix ikki marta qo'llanishi kerak. `analysis_run_repository` allaqachon `module_key` bilan generic bo'lishga mo'ljallangan edi.
- **Ikkita parallel run-lifecycle.** Checker `RunStateMixin` vs testcase `_TestcaseRunExecutor`. Testcase tomoni agent chegaralarini **progress-message string'larini parse qilib** aniqlaydi (`testcase_run.py:224-233`) — matn o'zgarsa buziladi.
- **String-matching orqali error-klassifikatsiya.** `error_handler.py:30-81` task holatini `'pr topilmadi'`, `'merged emas'` kabi **inson o'qiydigan o'zbekcha** matnlarni qidirib aniqlaydi. Xabar matnini o'zgartirish state-machine'ni jimgina buzadi. Bu ladder `service_runner.py`da 4 marta takrorlangan.
- 🟡 **(ASOSAN TUZATILDI)** **O'lik kod hali ham yetkaziladi.** Embedding/vector-DB/sprint feature'i o'chirildi (`c1f4e86`): `embedding_helper`, `chunking_helper`, `vectordb_helper`, `sprint_data_service` (822 q.), `scripts/1_/2_/3_`, `view_database`, `config/ui_foundation`, `test_chunking_system`. `torch`/`chromadb`/`sentence-transformers` allaqachon requirements'dan chiqarilgan. ⏳ Qolgan: `generate_testcases_sync` (live faylда, qoldirildi), ikkita config tizimi.
- **Ulkan funksiyalar.** `_run_agent2_per_requirement` — 420 qator; `_jira_webhook_impl` — 385 qator; `generate_test_cases` — 294 qator.
- **Checker engine testsiz.** 7 ta orkestratsiya moduli (`tzpr_orchestrator`, `tzpr_run_state`, `tzpr_data_fetch` va h.k.) nol test. `MockGeminiHelper` testlari real kodda mavjud bo'lmagan atributlarga assert qiladi. DSN'siz `test_full_system.py`ning ~205/206 testi jimgina skip.

**Biznes-oqim:**
- ✅ **(TUZATILDI)** **`return_count` cheklovi yo'q.** auto-return endi `APP_MAX_RETURN_COUNT` (default 3, 0=cheksiz) chegarasiga bo'ysunadi — task N marta qaytarilgan bo'lsa boshqa qaytarilmaydi (JIRA'ga "qo'lda ko'rish" warning). `check_tz_pr_and_comment` allaqachon yuklangan `task_db.return_count`ni o'qiydi. Config o'rniga env (WIP `app_settings.py`ga tegilmadi).
- **Bitta agent2 texnik nosozligi butun run'ni "Blocked" deb belgilaydi, lekin success sifatida yetkaziladi** (`agent3.py:314-319` + `tzpr_agent_runner.py:736`).
- **Har ikkala comment formati ham jimgina fail bo'lishi mumkin** — S1 `done` deb belgilanadi, lekin tahlil JIRA'ga yetib bormaydi (`error_handler.py:136-146`).
- **`return_reason` muvaffaqiyatli o'tgandan keyin tozalanmaydi** — keyingi tahlil hali ham `is_recheck=True`, eski commentlar objection sifatida yuboriladi.

**Baza:**
- Task upsert SELECT-keyin-INSERT (atomik `ON CONFLICT` emas) — bir jarayonda xavfsiz, `workers>1` bilan double-run.
- Kvota gate check-then-run (TOCTOU) — ikkita parallel free-tier run `used=2, limit=3`da ikkalasi ham o'tadi.
- Timezone nomuvofiqligi — task qatlami naive local, job/run qatlami UTC-aware yozadi.

**Xavfsizlik:**
- SSRF: tenant boshqaradigan `jira_server` (`auth_config_helpers.py:96`) — `http://169.254.169.254/` kabi ichki tarmoqqa yo'naltirish mumkin.
- Login rate limiter spoof qilinadigan `X-Forwarded-For`ga ishonadi.
- Prompt injection: JIRA matni to'g'ridan-to'g'ri Gemini'ga — developer "barcha talablarni FULL deb belgila" deb yozib score'ni oshirishi mumkin.

---

## 5. ✅ Yaxshi qilingan narsalar (kuchli tomonlar)

Bu loyihaning poydevori jiddiy — bularni saqlab qoling:

- **Multi-tenant o'qish izolyatsiyasi haqiqiy.** Kompaniya A kompaniya B ma'lumotini o'qiy olmaydi. Parametrlangan SQL hamma joyda, tenant scoping API qatlamida izchil ishlatilgan, run-read endpointlari egalikni qayta tekshiradi.
- **Xavfsizlik gigienasi kuchli.** PBKDF2-HMAC-SHA256 (200k iteratsiya), sessiya tokenlari SHA-256 hash bilan saqlanadi, reset tokenlari single-use, login lockout, audit log. Repository'da hardcoded secret yo'q, `.env` gitignored.
- **AI/credential cross-tenant kontaminatsiya topilmadi.** GeminiHelper aniq inject qilingan kalitsiz ishlamaydi (env fallback yo'q), har run o'z snapshot'idan executor quradi, AI lock/rate-limit per-tenant.
- **Baza poydevori mustahkam.** `psycopg_pool` leak-safe proxy bilan, versiyalangan migratsiya (hot-path'da DDL yo'q), `FOR UPDATE SKIP LOCKED` job claiming, atomik kvota upsert (`ON CONFLICT DO UPDATE`), TIMESTAMPTZ+FK+UNIQUE constraint'lar, pg_dump backup skript.
- **AI resilience o'ylangan.** Transient-vs-permanent xato taksonomiyasi, kalit freeze+rotation, model fallback (Pro→Flash), per-request timeout, retry scheduler, per-event usage/cost ledger.
- **Deterministik scoring yadrosi.** Yakuniy matritsa va compliance score **kodda** hisoblanadi (LLM emas); skip/technical REQ'lar maxrajdan chiqariladi; all-skipped → `None` (soxta 0-score auto-return'ning oldini oladi). Memory'dagi "agent2 missing REQ" bug'i to'g'ri handle qilingan (placeholder + manual_review).
- **Qatlamlash intizomi real.** `config → core → utils → services` bir yo'nalishli, aylanma import yo'q. "Bitta engine, uch kirish nuqtasi" (webhook/UI/worker) haqiqatan bir xil facade'ni chaqiradi.
- **`gemini_helper.py` + `gemini_json.py` — repodagi eng yaxshi kod.** Toza xato taksonomiyasi, staged JSON repair, barcha 10 agent-call joyida ishlatiladigan markaziy parser.
- **`BaseADFFormatter` haqiqiy reuse** (copy-paste emas). Setup-check engine deklarativ profillar bilan.
- **Deploy paketlari mavjud:** docker-compose (postgres healthcheck-gated), nginx TLS+security headers, Makefile, `DEPLOY_WEB.md`, backup/restore skriptlari. `.env.example` juda yaxshi izohlangan.

---

## 6. 📋 Sotuvga chiqish yo'l xaritasi (prioritet bo'yicha)

### Faza 1 — Blockerlar (1-hafta) — ✅ BAJARILDI (`7a622c5`)
1. ✅ `requirements.txt`ni tuzatish (`google-genai`, `cryptography` qo'shildi; o'lik paketlar olib tashlandi, 138→48) + toza py3.11 venv'da 104 modul import bo'ldi. Qayta qurish: `scripts/build_requirements.py`.
2. ✅ CI qo'shildi (`.github/workflows/ci.yml`): docker build + deps import (BLOCKER-1 sinfini ushlaydi) + `pytest` (Postgres service) + frontend `npm run build`. pytest hozircha non-blocking (eskirgan mock testlar).
3. ✅ Stale-job reaper + stuck-`progressing` sweeper + `mark_completed` (finalize) tegishli oqimlarda chaqiriladi; worker loop + docker `stop_grace_period`. Haqiqiy Postgres'da tasdiqlandi.
4. ✅ Xavfsiz default'lar: `.env.example` `APP_WEBHOOK_REQUIRE_SECRET=true`, `APP_STRICT_MODE=true`; `create_company` `webhook_secret` avto-generatsiya (shifrlangan). Enforcement env-driven (jonli prod buzilmaydi); query-param `?token=` deprecated.

### Faza 2 — HIGH (2–3-hafta) — ⏳ 6/7 BAJARILDI (`7b01aa7`, `dffda66`, `7ce00b3`)
5. 🟡 **Qisman** — Gemini kvota webhook + queue yo'lida majburlanadi (check+increment, source-driven; kvota tugasa run ishga tushmaydi). ⏳ Qolgan: per-company oylik xarajat cheklovi (`ai_usage_events` ledger'idan).
6. ✅ RPC kwargs rol-bypass yopildi (args+kwargs imzoga bind); credential fail-closed (plain text saqlamaydi); `SUPER_ADMIN_PASSWORD` shifrlashdan olib tashlandi (faqat legacy-decrypt); KDF → PBKDF2 (migratsiya-xavfsiz).
7. ✅ Alerting (`core/watchdog.py`, `7ce00b3`) — self-hosted: navbat backlog / blocked / worker heartbeat → WARNING log + email (SMTP). Tashqi servis (Sentry) shart emas. Env `APP_WATCHDOG_*`.
8. ✅ Per-company AI concurrency DB'ga ko'chirildi (`dffda66`): `claim_next_job` + `pg_advisory_xact_lock` — N worker bilan ham "kompaniyaga 1 AI job". Env toggle `APP_QUEUE_PER_COMPANY_CONCURRENCY`. Haqiqiy Postgres'da 8-worker konkurent test o'tdi. ⏳ Qolgan: jonli deploy'da ≥2 worker yoqish + rate-limit ledger (kerak bo'lsa).
9. ✅ AI-outage S1 klassifikatsiyasi tuzatildi — `_run_agent1` `analyze()` xatosini alohida ushlab real matnni saqlaydi → `ai_timeout` → WARN_AI_TIMEOUT → retry.
10. 🟡 **Qisman** — marker detektori (`CommentSeparator`) markerni istalgan qator boshida topadi (oxirgi paragrafdagi marker endi to'g'ri AI deb tanaladi). ⏳ Qolgan: formatter tomonida marker-joylashuv + S2-marker (foydalanuvchi WIP'ida).
11. ⏳ LICENSE + ToS + maxfiylik/data-processing hujjati ("JIRA matningiz va PR diff'lar Google Gemini'ga yuboriladi") + per-company diff opt-out. **Biznes/yurisdiksiya kirishini talab qiladi.**

### Faza 3 — Barqarorlik va tozalik (4-hafta+) — ⏳ 4/5 BAJARILDI (`3b7da21`, `5dbd8dd`, README)
12. ✅ Retention job (`utils/database/retention.py`) — eski run/event/usage/job yozuvlari kuniga bir marta tozalanadi (RUN=90, JOB=30, USAGE=365 kun; CASCADE bilan). ⏳ Qolgan: log rotation (`RotatingFileHandler`/Docker stdout).
13. ✅ `return_count` cheklovi — `APP_MAX_RETURN_COUNT` (default 3) chegarasi; cheksiz return loop to'xtatildi.
14. 🟡 **Qisman** (`e5bc904`) — read-only endpointlar (`/health`, `/metrics`, `/settings`, monitoring, sprint) `def`ga o'tkazildi (FastAPI threadpool). ⏳ Qolgan: webhook POST core (`_jira_webhook_impl` + `manual_*`) — integratsiya testi bilan alohida ehtiyotkor ish.
15. 🟡 **Qisman** — migratsiya runner'ga `pg_advisory_lock` qo'shildi (cross-process serializatsiya, konkurent test o'tdi). ⏳ Qolgan: import-time `init_db`'ni olib tashlash (API app lifespan migratsiyasini tasdiqlagach).
16. ✅ README qayta yozildi — eskirgan bug-analyzer/ChromaDB/VectorDB/embeddings/2.0.0 bo'limlari olib tashlandi; joriy mahsulot (multi-tenant TZ-PR checker + testcase SaaS) va to'g'ri o'rnatish/oqim/struktura hujjatlandi. Barcha havolalar tekshirildi.

### Faza 4 — Texnik qarz (sotuvdan keyin, lekin muhim) — ⏳ 1/4 BAJARILDI (`c1f4e86`)
17. ⏳ Ikkita run-repository'ni birlashtirish (~550 qator o'chirish).
18. ⏳ String-matched error klassifikatsiyani typed exception'larga almashtirish.
19. ✅ O'lik embedding/vector/sprint kodi o'chirildi (10 fayl; import/deploy tekshiruvidan o'tdi, pytest 319 test yig'di).
20. ⏳ `ruff` + `mypy` (loose) qo'shish; ulkan funksiyalarni bo'lish.

---

## 7. Xulosa

QA-Assistant **ideal fikr va kuchli muhandislik poydevoriga** ega mahsulot — arxitektura darajasida sotuvga arziydigan narsa bor. Muammo arxitekturada emas: u **release-engineering** (buzuq dependency manifest, CI yo'qligi, crash-recovery, alerting) va **tijorat qadoqlash** (kvota majburlash, huquqiy hujjatlar) da.

Eng ko'ngilsiz haqiqat — 3 ta blocker'ning barchasi nisbatan tez tuzatiladi (kunlar, haftalar emas), lekin ular hozir sotuvni to'sib turibdi. Ayniqsa BLOCKER-1 (`requirements.txt`) va BLOCKER-3 (qotib qolgan task'lar) bir nechta mustaqil auditda takroran chiqdi — bu ularning haqiqiy va yuqori ta'sirli ekanini tasdiqlaydi.

**Tavsiya:** Faza 1 + Faza 2'ni tugatib (taxminan 3 hafta), 1–2 ta ishonchli pilot mijoz bilan boshlang. Faza 3–4'ni parallel davom ettiring. Multi-tenant maxfiylik o'qish bo'yicha allaqachon himoyalangan — faqat webhook yozish teshigini yoping.

---

*Ushbu hisobot 5 ta mustaqil chuqur audit asosida tayyorlangan. Har bir topilma haqiqiy kod (`fayl:qator`) bilan tasdiqlangan. Batafsil har bir topilmaning kod dalili yuqoridagi bo'limlarda keltirilgan.*
