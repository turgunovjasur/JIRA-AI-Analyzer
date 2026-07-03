# QA-Assistant — Chuqur Tahlil va Professional Bo'lish Yo'l Xaritasi

**Sana:** 2026-07-03
**Branch:** `dev1`
**Usul:** 6 ta mustaqil chuqur audit (backend kod sifati, frontend Next.js, test/CI, xavfsizlik qayta-tekshiruv, ops/deploy, arxitektura/mahsulot). Har topilma haqiqiy kod (`fayl:qator`) bilan tasdiqlangan.
**Kontekst:** Bu hisobot `AUDIT_HISOBOT_2026-07-02.md` ustiga quriladi — u yerda topilgan/tuzatilgan narsalarni takrorlamaydi, faqat (a) ochiq qolgan itemlarning joriy holatini tekshiradi va (b) YANGI topilmalarni beradi.

---

## 0. Bir qatorli xulosa

> Loyihaning **muhandislik poydevori kuchli** (multi-tenant izolyatsiya, DB dizayni, AI resilience, xavfsizlik gigienasi) — kechagi auditning BLOCKER'lari haqiqatan tuzatilgan va o'z joyida turibdi. Lekin **professional mahsulot** darajasiga yetish uchun yana jiddiy ish bor: eng katta xavf — **AI sifatini o'lchaydigan hech narsa yo'q** (prompt versiyalash + eval/golden-set yo'q, ya'ni prompt o'zgarishi mijozning JIRA'sidagi natijani jimgina buzishi mumkin va buni hech kim sezmaydi). Bundan tashqari: **bitta serial worker** kunlik ~1000 run talabini ko'tara olmaydi, **testlar 65% bitta faylda va Python xatti-harakati CI'da umuman gate qilinmaydi**, **frontend'da ESLint/testlar yo'q + bitta buzilgan oqim (parol reset)**, **Windows deploy'da inline rejim barcha crash-recovery'ni o'chiradi va TLS'siz internetga ochiq**.

**Umumiy baho: B− (poydevor A−, mahsulot yetukligi C).** Sotuvga texnik jihatdan "shartli tayyor", lekin quyidagi 3 narsa professional/ishonchli mahsulot uchun shart: (1) AI eval harness, (2) Python testlarini gate qilish + engine testlari, (3) deploy/ops qattiqlashtirish (worker scaling, log rotation, Windows TLS).

---

## 1. Kechagi auditning ochiq itemlari — joriy holat

Quyidagilar kechagi audit "⏳ qolgan" deb belgilagan, bugun **hali ochiq** ekani tasdiqlandi:

| Kod | Item | Holat | Dalil |
|---|---|---|---|
| **F2-5** | Per-company oylik xarajat cheklovi | ❌ Ochiq | `ai_usage_events` xarajatni yozadi (`ai_usage_repository.py:66-90`), lekin hech kim yig'indini o'qib **cap qo'ymaydi**. Yagona gate — bepul run soni (`quota_repository.py:15`). |
| **F3-14** | Webhook POST async bloklash | ❌ Ochiq (va **battar**) | `_jira_webhook_impl` (`jira_webhook_handler.py:410`) event-loop'da sinxron DB chaqiradi + `:668` **sinxron JIRA HTTP** (`requests.get`) chaqiradi — sekin JIRA barcha konkurent webhooklarni bloklaydi. |
| **F3-15** | Import-time migratsiya | 🟡 Qisman | `task_db.py:985-989` import paytida `init_db()` chaqiradi (advisory-lock bilan xavfsizroq, lekin hali import-vaqt DDL). |
| **F4-17** | Ikkita run-repository dublikat | ❌ Ochiq | `checker_run_repository.py` (396q) vs `analysis_run_repository.py` (399q) — diff atigi 97 qator, asosan mexanik rename. Birlashtirilmagan. |
| **F4-18** | String-matched error klassifikatsiya | ❌ Ochiq | `error_handler.py:30-81` hali o'zbekcha matn qidiradi (`'pr topilmadi'`, `'merged emas'`); ladder `service_runner.py`da 4 marta takrorlangan. |
| **F4-20** | ruff/mypy + ulkan funksiyalar | ❌ Ochiq | Repoda **hech qanday** linter/type/format konfig yo'q. **13 funksiya ≥150 qator** (eng yomoni `_run_agent2_per_requirement` — **421 qator, 7 daraja ichki**). |

---

## 2. 🔴 Eng muhim yangi topilmalar (professional mahsulot uchun kritik)

### YANGI-1 · AI sifatini o'lchaydigan hech narsa yo'q — prompt versiyalash + eval harness yo'q · **KRITIK (AI mahsulot uchun eng katta xavf)**
- Promptlar **kod ichida f-string** sifatida yashaydi (`services/checkers/tzpr_agents/agent1.py|agent2.py|agent3.py|agent1b.py`, `testcase_agents/*`). Tashqi prompt fayli, prompt registry, prompt **versiya maydoni yo'q** — prompt o'zgarishi oddiy kod diff, run'ga versiya yozilmaydi.
- **Golden-set / eval / regression harness umuman yo'q** (`golden|eval_set|evaluation` bo'yicha qidiruv 0 natija). TZ+PR juftliklari + kutilgan verdikt/score to'plami yo'q.
- **Oqibat:** prompt yoki model o'zgarishi checker sifatini **pasaytirsa** — bu mijozning JIRA commentiga yetib borgunча **aniqlanmaydi**. Bu AI mahsuloti uchun eng jiddiy sifat xavfi.
- ✅ Kuchli tomon: token/xarajat kuzatuvi yaxshi (`usage_cost.py` + `ai_usage_events` ledger, per-`run_id/agent_key/module_key`). Lekin bu **estimate**, time-series yo'q, faqat super-admin ko'radi, cap yo'q.

### YANGI-2 · Bitta serial worker — throughput devori · **HIGH**
- DB claim qatlami gorizontal workerni **qo'llab-quvvatlaydi** (per-company advisory-lock, `job_queue_repository.py:184-224`), lekin default deploy **aynan bitta worker** ishga tushiradi (`docker-compose.yml:36-41`), va worker loop **bitta job'ni to'liq tugatib**, keyingisini oladi (`worker/main.py:305-328`).
- Hisob: 10 kompaniya × 50 task/kun × 2 run (S1+S2) ≈ **1000 run/kun**. Serial ceiling ≈ 1 run / 3–8 daq ≈ **180–480 run/kun**. Talab 2–5× yuqori → **doimiy, cheksiz backlog**. Watchdog ogohlantiradi, lekin hech narsa drenaj qilmaydi.
- Per-company `concurrency=1` + `gemini_min_interval=6s` — bu **adolat cheklovi, parallellik emas**; throughput'ni faqat worker replica oshiradi (konfiguratsiya ham, hujjat ham yo'q).

### YANGI-3 · Parol-reset yakunlash oqimi BUZILGAN · **HIGH (foydalanuvchiga tegadi)**
- `frontend/.../reset-password/page.tsx:39` `/api/auth/password-reset` ga POST qiladi, lekin `src/app/api/auth/` da faqat `login/logout/me/request-reset` bor — `password-reset/route.ts` **mavjud emas**.
- Oqibat: POST 404 → foydalanuvchi doim "Token yaroqsiz" xabarini ko'radi → **hech kim UI orqali parolini tiklay olmaydi** (so'rov yuborish qismi ishlaydi, yakunlash qismi yo'q).

### YANGI-4 · Windows deploy: inline rejim barcha crash-recovery'ni o'chiradi · **HIGH**
- Reaper, stuck-`progressing` sweeper, retention — **faqat worker loop'da** (`services/worker/main.py:84-102, 233, 267-303`). API lifespan faqat blocked-retry scheduler'ni (queue-mode EMASда) ishga tushiradi.
- `.env.example:49` default = `inline`, `setup.bat:105-114` uni o'zgartirmasdan ko'chiradi → inline Windows deploy'da **reaper/sweeper/retention umuman yo'q** — ya'ni kechagi BLOCKER-3 tuzatilishi va cheksiz jadval himoyasi jimgina yo'qoladi.

### YANGI-5 · Windows deploy TLS'siz, internetga ochiq + auth'dan oldin body parse · **HIGH (xavfsizlik)**
- `start.bat:75` uvicorn'ni `--host 0.0.0.0 --port 8000` TLS/nginx'siz ishga tushiradi; `DEPLOY_WINDOWS.md:145-167` port 8000'ni internetga ochishni aytadi. Oqibat: `X-Webhook-Secret` va login trafigi **ochiq matnda**; autentifikatsiyasiz `/metrics`+`/settings` to'g'ridan-to'g'ri ochiladi.
- `jira_webhook_handler.py:445` `body = await request.json()` **autentifikatsiyadan oldin**, hajm/chuqurlik limitisiz ishlaydi → DoS (`WebhookPayload` pydantic modeli yozilgan lekin ishlatilmaydi).

### YANGI-6 · Python xatti-harakati CI'da umuman gate qilinmaydi · **HIGH**
- `ci.yml:43` `continue-on-error: true` — pytek natijasi **yutib yuboriladi**, faqat informatsion. Yagona haqiqiy gate: backend image build+import va frontend compile.
- **Muhim tuzatish (memory'dagi da'vo noto'g'ri edi):** "~13 test fail bo'lyapti" — aslida `MockGeminiHelper` testlari (`test_full_system.py:1803-1897`, 12 test) **o'tadi**, lekin **o'chirilgan** ikki-kalitli freeze modelini tekshiradi (real `GeminiHelper` N-kalitli model). Ya'ni ular soxta ishonch beradi va real kalit-rotatsiya kodida **nol qoplama** bor. `.pytest_cache` da 94 nodeid bor, lekin ko'pi endi mavjud bo'lmagan testlar — cache eskirgan.

---

## 3. Test qoplamasi — chuqur tahlil

**Raqamlar:** 24 test fayli, **318 test funksiyasi**, lekin `test_full_system.py` bitta o'zi **206 test / 2633 qator (65%)**. DSN yo'q bo'lsa `conftest.py:21-23` bularni **jim skip** qiladi → lokalda haqiqiy signal juda kichik.

**Nol qoplamali kritik modullar** (grep bilan tasdiqlangan):
- Checker engine — **8 ta yadro moduli**: `tzpr_orchestrator`, `tzpr_run_state`, `tzpr_data_fetch`, `tzpr_lifecycle`, `tzpr_multi_agent_service`, `tzpr_result_builder(s)`, `tzpr_helpers`, `tzpr_text_parser`.
- `core/watchdog.py` (F2-7, nol test), `utils/database/retention.py` (F3-12, nol test), `job_queue_repository.py` (BLOCKER-3 markazi — nol to'g'ridan-to'g'ri test).
- `gemini_helper.py` — kalit-rotatsiya/freeze/fallback logikasi (`:46-164`) uchun **nol real test**.

**Eng qimmatli yo'q testlar (prioritet):**
1. Checker orkestratsiya integratsiya suite'i (fake Gemini+Jira, to'liq run, state o'tishlari, "all-skipped→None").
2. Gemini JSON kontrakt testlari (`docs/MULTI_AGENT_JSON_CONTRACT.md` bo'yicha golden fixture'lar).
3. Real `GeminiHelper` resilience testlari + o'lik `MockGeminiHelper` blokini o'chirish.
4. Webhook end-to-end (TestClient + Postgres; 401-without-secret regression guard).
5. Task lifecycle/recovery (`mark_completed`, reaper, sweeper) — BLOCKER-3 hududi.

---

## 4. 🟠 HIGH darajali boshqa topilmalar

### Arxitektura
- **State-machine markaziy emas** (`HIGH`). `task_processing` holatlari ~15 imperativ mutator (`task_db.py`) + webhook'da string if/elif (`jira_webhook_handler.py:617-649`) orqali boshqariladi. `upsert_task_record` (`task_repository.py:48-85`) — istalgan ustunni yozadigan generic writer, **`VALID_TRANSITIONS` yo'q, guard yo'q**. Noqonuniy o'tishlar (masalan `service1_status='error'` bo'lsa ham `set_service2_done`) strukturaviy mumkin. `core/constants.py:25-31` dagi `STATUS_*` konstantalar noto'g'ri va o'lik (hech qayerda ishlatilmaydi).
- **Queue: priority yo'q, DLQ yo'q, idempotency zaif** (`MEDIUM-HIGH`). Ordering faqat `scheduled_at ASC` (retry-storm interaktiv manual run'ni ochlatadi); failed job terminal va ko'rinmas (DLQ/requeue UI yo'q); dedupe faqat `queued/running` (`:113-115`) — `done` bo'lgach bir xil webhook **yangi run + yangi Gemini xarajati** yaratadi.
- **Settings: 5 manba, precedence hujjatlanmagan, per-webhook ~12 DB o'qish** (`MEDIUM-HIGH`). env + disk JSON (`data/app_settings.json`, multi-process race hazard) + global_setting + company + user. Har webhook `_apply_global_*` orqali **11 SELECT** + company settings ≈ 12 DB round-trip, TTL cache yo'q.
- **Gemini vendor lock-in** (`MEDIUM`). Vendor-neutral LLM interfeys yo'q; `GeminiHelper` 6 joyda to'g'ridan-to'g'ri quriladi; error taksonomiyasi Gemini status-kodlariga qattiq bog'langan.

### Frontend
- **God componentlar** (`HIGH`): `settings-panel.tsx` **2360 qator / 43 useState**, `super-admin-panel.tsx` 1887/27, `tzpr-checker.tsx` 1378, `testcase-generator.tsx` 1239. Har keystroke'da butun daraxt qayta render.
- **tzpr-checker ↔ testcase-generator og'ir copy-paste** (`HIGH`): polling `useEffect`, `refreshStartStatus`, `reopenRun`, `applyRunSnapshot` — ikkala ~1.3k qatorli faylda deyarli bir xil. Bitta `useRunPolling` hook bo'lishi kerak.
- **ESLint umuman yo'q + testlar yo'q** (`HIGH`): `eslint`/`jsx-a11y`/`react-hooks` yo'q, `next build` lint qilmaydi; hech qanday test freymvorki yo'q.
- ✅ Kuchli: httpOnly cookie sessiya, server-side secret masking, nol `any`/`ts-ignore`, `dangerouslySetInnerHTML` yo'q, XSS yuzasi yo'q.

### Ops/Deploy — top xavflar
- **Log rotation hech qayerda yo'q** (`HIGH`): `core/logger.py:75-112` oddiy `FileHandler` (`data/webhook.log`), `start.sh` `logs/*.log` ga cheksiz append. Disk to'ladi.
- **Windows'da process supervision yo'q** (`HIGH`): `start.bat` 3 ta `cmd /k` oynasi; crash bo'lsa hech narsa qayta ishga tushirmaydi. Auto-start faqat interaktiv login'da. NSSM/Windows Service yo'q.
- **Backup restore qilib bo'lmaydi** (`HIGH`): `backup_db.bat` `-F c` (custom) yozadi, lekin `restore_db.bat` yo'q va restore hujjatlanmagan; Linux `restore_db.sh` esa `.sql.gz` kutadi — formatlar mos emas.
- **Docker: backend/worker uchun healthcheck/restart-trigger yo'q, resource limit yo'q, log-cap yo'q** (`MEDIUM-HIGH`): hang bo'lgan backend hech qachon qayta ishga tushmaydi.
- **`update.bat` xavfsizlik** (`HIGH`): backup yo'q, migratsiya-gate yo'q, rollback yo'q; `git pull origin main` (`update.bat:17`) — lekin multi-agent kod `dev1`da, ya'ni eski monolitni yangi ustiga tortish xavfi.

---

## 5. 🟡 MEDIUM — muhim, lekin sotuvni to'xtatmaydi

**Xavfsizlik (kechagidan qolgan, tasdiqlandi ochiq):**
- SSRF: tenant boshqaradigan `jira_server` (`auth_config_helpers.py:32,96,168`) — allowlist yo'q, ichki hostga (169.254.169.254) yo'naltirish mumkin.
- Login rate-limiter spoof qilinadigan `X-Forwarded-For`ga ishonadi (`rate_limit.py:19-23`).
- Prompt injection: JIRA/PR matni to'g'ridan-to'g'ri Gemini'ga.
- Autentifikatsiyasiz `/metrics` (cross-tenant agregat) + `/settings` (`jira_webhook_handler.py:913-991`); nginx'da shadowed, lekin Windows'da to'g'ridan ochiq.
- Username enumeration + notekis lockout (`auth_manager.py:369-370`); `/metrics` xom exception matnini oshkor qiladi (`:957-958`).

**Kod sifati (yangi o'lchangan):**
- **Config sprawl:** `config/` tashqarisida **42 `os.getenv` chaqiruvi** (~15 fayl); `APP_WEBHOOK_EXECUTION_MODE` **4 joyda** bir xil parse. Ikki parallel config tizimi (`config/settings.py` legacy vs `app_settings.py`) hali birga yashaydi.
- **83 naive `datetime.now()`** vs 9 tz-aware — audit trailga naive local vaqt yoziladi, run/job qatlami UTC-aware; hisobotlar UTC-offset ga surilib ketadi.
- **Sinxron `requests.get` timeout'siz** (`skip_detector.py:161`) — worker/loop'ni cheksiz osib qo'yishi mumkin.
- **285 keng `except Exception`** + 3 bare `except:`; kvota-increment jim yutiladi (`tzpr_multi_agent.py:57`) → under-billing drift.
- **45 pyflakes topilma** (ishlatilmagan import/local, bo'sh f-string); `jira_webhook_handler.py:53` da 13 ishlatilmagan `task_db` funksiya import qilingan.
- **16 `print()`** kutubxona kodida (asosan `jira_client.py`).

**API yuzasi:**
- Versiyalash yo'q (`/api/v1` yo'q), ikki xil error envelope (`{detail}` vs `to_error_payload()`), pagination yo'q (`monitoring_api` butun DataFrame'ni materializatsiya qiladi), ownership-check har endpointda qo'lda takrorlangan.

**Baza (kechagidan):**
- Task upsert atomik `ON CONFLICT` emas; kvota gate TOCTOU; timezone nomuvofiqligi (yuqorida).

---

## 6. Eskirgan / adashtiruvchi hujjatlar (arzon tuzatish, avval qilinsin)

| Hujjat | Muammo |
|---|---|
| **CLAUDE.md:273-297** | Streamlit `ProgressManager` / `ui/components/loading.py` bo'limi — `ui/` papka **yo'q**, frontend Next.js. Har sessiyada yuklanadi, ya'ni har agentni adashtiradi. |
| **PROGRESS_LOG.md** | 532 ta havola eski `/JIRA-AI-Analyzer/` yo'liga; oxirgi yozuv ~2026-05-19; iyul auditi ishi umuman yozilmagan. |
| **PERMISSION_MATRIX.md** | `Bug Analyzer` + `Sprint Statistics`ni sotiladigan modul deb ko'rsatadi — ikkalasi ham o'chirilgan/UI yo'q. |
| **ROADMAP_SAAS.md** | "Streamlit → SaaS" ko'chirish atrofida qurilgan (allaqachon bo'lgan); Bug Analyzer'ni P0 deb sanaydi. |
| **config/app_settings.py:53-90** | `bug_analyzer_help`, `BugAnalyzerSettings`, `StatisticsSettings` — o'chirilgan feature'lar Settings UI'da hali ko'rinadi. |
| **.env.example:118-131** | `EMBEDDING_MODEL`/`VECTOR_DB_PATH`/`TOP_K_RESULTS` — o'chirilgan embedding feature'i; `setup.bat` shundan ko'chiradi. |
| Manba kommentlar | `monitoring_api.py:4`, `auth_api.py:5`, `internal_rpc_api.py:2`, `tz_helper.py:512` — "Streamlit UI'ni bo'lish" deb o'zini ta'riflaydi. |

---

## 7. Kuchli tomonlar (saqlab qolinsin)

- Multi-tenant **o'qish izolyatsiyasi haqiqiy** — barcha `services/api` endpointlari sessiya-auth + tenant scoping, IDOR bloklangan.
- Xavfsizlik gigienasi: PBKDF2-HMAC-SHA256 (200k), SHA-256 hashed session token, single-use reset, constant-time compare, hardcoded secret yo'q, `.env`/`logs`/`data` gitignored.
- Kechagi 3 BLOCKER + 4 xavfsizlik tuzatilishi **hali joyida** (tekshirildi): webhook secret majburiy, RPC kwargs-bypass yopiq, fail-closed crypto, PBKDF2.
- AI resilience: transient-vs-permanent taksonomiya, kalit freeze+rotation, Pro→Flash fallback, per-request timeout.
- Deterministik scoring yadrosi (matritsa kodda, LLM emas; all-skipped→None).
- Token/xarajat ledger (`ai_usage_events`) — kutilganidan yaxshiroq.
- Frontend BFF pattern: secret hech qachon brauzerga chiqmaydi, httpOnly cookie.
- `watchdog.py` self-hosted alerting uchun mustahkam; DB poydevori (pool, versiyalangan migratsiya, SKIP LOCKED, atomik kvota).

---

## 8. Prioritetli yo'l xaritasi

### Faza A — Tez g'alabalar (1 hafta)
1. **Buzilgan parol-reset route'ini tuzatish** (YANGI-3) — foydalanuvchiga tegadigan buzuq oqim.
2. **Eskirgan hujjatlarni tozalash** (§6) — ayniqsa CLAUDE.md Streamlit bo'limi (har agent/muhandisni adashtiradi). Arzon, katta ta'sir.
3. **`.env.example` default'ini `queue`ga** yoki `setup.bat`'da majburiy `queue` — inline crash-recovery regressiyasini yopadi (YANGI-4).
4. **Windows deploy: TLS reverse-proxy majburiy** hujjatlash yoki `127.0.0.1`ga bind (YANGI-5); webhook body auth'dan oldin hajm-cap.
5. **O'lik `MockGeminiHelper` blokini o'chirish** + `ci.yml`da eslint/typecheck wiring boshlash.

### Faza B — Ishonchlilik va sifat (2–4 hafta)
6. **AI eval harness + prompt versiyalash** (YANGI-1) — golden TZ+PR to'plami, CI'da regression; promptlarni versiyalangan store'ga. *Eng yuqori qiymatli.*
7. **Checker engine integratsiya testlari** + Gemini JSON kontrakt testlari + `continue-on-error`ni olib tashlash (Python'ni real gate qilish).
8. **Log rotation** (`RotatingFileHandler`/Docker log-driver cap) + Windows log yo'nalishini runbook bilan moslash.
9. **Frontend: ESLint (+jsx-a11y, react-hooks) + minimal test setup** + `useRunPolling` hook'ini ajratib god-component'larni bo'lish.
10. **Docker healthcheck/restart** backend+worker uchun; resource limit + log-cap.

### Faza C — Miqyoslash va professional plumbing (4 hafta+)
11. **Gorizontal worker scaling'ni haqiqiy qilish** (compose replicas + `APP_WORKER_NAME` sxemasi + capacity guide) — YANGI-2.
12. **Markaziy state-machine moduli** (enum + `ALLOWED_TRANSITIONS` + validatsiya) — B1 sinf xatolarini yopadi.
13. **DLQ + admin job konsoli** (failed job requeue/diagnostika).
14. **Per-company billing/xarajat hisoboti + budjet cap** (F2-5 yopish).
15. **API versiyalash + yagona error envelope + pagination**; distributed rate-limiting; settings TTL cache.
16. **Texnik qarz:** ikkita run-repository birlashtirish (F4-17, ~550q), string-error→typed exception (F4-18), ruff+mypy (F4-20), ulkan funksiyalarni bo'lish.

### Kelajak (mahsulot yetukligi)
- i18n framework (hozir hardcoded o'zbekcha), data export + tenant delete (GDPR), self-service onboarding, feature-flag tizimi, SLA/latency metrikalari.

---

## 9. Xulosa

QA-Assistant **kuchli poydevor + real muammoni yechadigan mahsulot**. Kechagi audit BLOCKER'lari haqiqatan tuzatilgan va joyida. Endi masshtab **muhandislik intizomi va operabilligiga** ko'chdi:

1. **AI-mahsulot intizomi** — eng katta yashirin xavf: prompt versiyalash + eval harness yo'qligi (sifat regressiyasi ko'rinmas).
2. **Ishonchlilik** — Python testlarini real gate qilish, engine testlari, log rotation, inline-rejim regressiyasi.
3. **Miqyoslash** — bitta serial worker devori (~1000 run/kun talab, ~180–480 imkoniyat).
4. **Tijorat plumbing** — billing/cost cap, DLQ, API versiyalash, i18n.

**Tavsiya:** Faza A (1 hafta) buzuq oqim + hujjat + deploy xavfsizligini yopadi. Faza B (AI eval + test gate) — professional/ishonchli mahsulot uchun eng muhim investitsiya. Faza C — miqyoslash 2+ mijozdan oldin.

---

*Ushbu hisobot 6 ta mustaqil chuqur audit asosida tayyorlangan. Har topilma haqiqiy kod (`fayl:qator`) bilan tasdiqlangan. Kechagi `AUDIT_HISOBOT_2026-07-02.md` bilan birga o'qilishi kerak — bu hisobot uni almashtirmaydi, davom ettiradi.*
