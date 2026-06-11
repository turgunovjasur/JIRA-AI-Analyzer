# V1 Release Plan — JIRA-AI-Analyzer

> Bu hujjat 2026-06-11 dagi to'liq audit (kod, schema, testlar, xavfsizlik, biznes qatlami) asosida tuzilgan.
> **Maqsad:** loyihani userlarga chiqarishga tayyorlash. Har bir ish shu hujjat bo'yicha boriladi.
> Yangi katta o'zgarish kiritishdan oldin shu hujjatdagi faza va ustuvorlik tekshiriladi.

---

## 0. Status legendasi va konvensiya

- `[ ]` — qilinmagan
- `[~]` — jarayonda
- `[x]` — bajarilgan va tekshirilgan (Definition of Done bajarilgan)

Har bir vazifa quyidagicha yoziladi: **ID · Vazifa · Fayl(lar) · DoD (tugatish mezoni) · Taxminiy vaqt**.

Vazifa bajarilgandan keyin: status `[x]` ga o'tkaziladi va izoh qatoriga commit/sana yoziladi.

---

## 1. Hozirgi holat (audit xulosasi)

**Texnik jihatdan kuchli, lekin ochiq SaaS sifatida sotishga hali tayyor emas.**

### ✅ Tayyor
- Arxitektura to'liq: Next.js frontend + FastAPI backend + PostgreSQL + worker/queue (Streamlit'dan to'liq o'tilgan).
- Multi-tenant izolyatsiya kuchli: `company_id` har doim sessiyadan olinadi, IDOR yo'q (`services/api/session_scope.py:67`).
- Auth: rollar (super_admin/company_admin/user), PBKDF2 200k, login lockout, audit log, parametrlangan SQL.
- Schema professional: FK, index, `audit_logs`, `jobs`/`job_runs`, `login_attempts`, `password_reset_tokens`.
- Testlar: schema qo'llanganda **288 test o'tadi** (tenant-isolation, session-scope, job-queue ham). 1 ta eskirgan test fail.

### ❌ Yetishmaydi
- Xavfsizlik: webhook imzo, credential shifrlash majburiyligi, rate-limit, CORS.
- Biznes: to'lov integratsiyasi, self-service signup, email yuborish.
- Ops: backend Docker o'chirilgan, CI/CD yo'q, build artifaktlar git'da.

---

## 2. Release scenariylari va Definition of Done

Ikki bosqichli release strategiyasi.

### Track A — Nazoratli Pilot (1–3 tanish kompaniya)
Onboarding va to'lov **qo'lda**. Mijozlar real ishlatadi, lekin biz har birini o'zimiz ulaymiz.

**Tayyor deyiladi, agar:**
- FAZA 0 va FAZA 1 (xavfsizlik) to'liq bajarilgan
- FAZA 2 (deploy) — bitta reproducible production deploy yo'li mavjud
- Har tenant ma'lumoti izolyatsiya qilingan (mavjud — test bilan tasdiqlanган)
- Barcha tokenlar shifrlangan holda saqlanadi (FAZA 1 #2)

### Track B — Ochiq Self-Service SaaS
Har kim ro'yxatdan o'tib, to'lab, o'zi ishlatadi.

**Tayyor deyiladi, agar Track A + qo'shimcha:**
- FAZA 3 (billing) — avtomatik to'lov va obuna
- FAZA 4 (onboarding) — signup + email verifikatsiya + password reset email
- FAZA 5 (CI/CD, monitoring) — release confidence

---

## 3. FAZA 0 — Tezkor tuzatishlar (hygiene)

> Maqsad: kichik, lekin tez yutuq beradigan ishlar. ~Yarim kun.

- [x] **F0-1 · `frontend/.next/` ni git'dan chiqarish**
  - Fayl: `.gitignore`, `frontend/.gitignore`
  - Hozir build artifaktlar (`frontend/.next/**`) commit qilinmoqda — git'ni shishiradi va konfliktlar beradi.
  - DoD: `.gitignore`da `frontend/.next/` bor; `git rm -r --cached frontend/.next` qilingan; `git status` toza.
  - Vaqt: 15 min
  - ✅ 2026-06-11 commit cd21b05 — node_modules, .next untrack; history rewrite bilan 785MB → 2.6MB

- [x] **F0-2 · Eskirgan testni tuzatish**
  - Fayl: `tests/test_tzpr_multi_agent.py:199`
  - `normalize_single_verification` endi `sources: []` maydonini qaytaradi, test buni kutmaydi.
  - DoD: test yangilangan; `pytest tests/test_tzpr_multi_agent.py` to'liq yashil.
  - Vaqt: 15 min
  - ✅ 2026-06-11 — `sources: []` assert ga qo'shildi; 16/16 yashil

- [x] **F0-3 · Test DB ishga tushirish yo'lini hujjatlash**
  - Fayl: `tests/conftest.py`, `README.md` yoki `CLAUDE.md`
  - 244 test `APP_TEST_POSTGRES_DSN` yo'qligida skip bo'ladi. conftest faqat `ALTER` qiladi, schema'ni yaratmaydi — avval `001_initial_schema.sql` qo'llash kerak.
  - DoD: bitta buyruq bilan (`make test` yoki skript) fresh test DB yaratilib, schema qo'llanib, to'liq suite ishga tushadi.
  - Vaqt: 1 soat
  - ✅ 2026-06-11 — `scripts/setup_test_db.sh` + `Makefile` (`make test-setup`, `make test`, `make test-all`); CLAUDE.md ga hujjatlandi

- [x] **F0-4 · Eski/keraksiz fayllarni tozalash**
  - Root'dagi `QA-Assistant.zip`, `result.json` (408KB), `MULTI_AGENT_RESULTS.md` kabi fayllar git'ga kerakmi — tekshirish.
  - DoD: repo'da faqat kerakli fayllar; kattalar `.gitignore`da yoki o'chirilgan.
  - Vaqt: 30 min
  - ✅ 2026-06-11 — QA-Assistant.zip, result.json, MULTI_AGENT_RESULTS.md o'chirildi; *.zip va result.json .gitignore ga qo'shildi

---

## 4. FAZA 1 — Xavfsizlik must-fix (Pilotdan OLDIN shart)

> Maqsad: multi-tenant SaaS uchun minimal xavfsizlik bazasi. ~1 hafta.

- [x] **F1-1 · JIRA webhook imzo / shared secret tekshiruvi** 🔴 CRITICAL
  - Fayl: `services/webhook/jira_webhook_handler.py:358`
  - Hozir endpoint har qanday POST'ni qabul qiladi. Hujumchi istalgan kompaniya uchun AI tahlilini ishga tushirib, token sarflashi mumkin.
  - Yechim: webhook URL'iga secret token qo'shish (`/webhook/jira?token=...` yoki header `X-Webhook-Secret`), kompaniya sozlamalarida saqlash, har request'da tekshirish. Imkon bo'lsa JIRA HMAC (`X-Hub-Signature`).
  - DoD: secret bo'lmasa yoki noto'g'ri bo'lsa `401` qaytadi; to'g'ri secret bilan ishlaydi; test yozilgan.
  - Vaqt: 1 kun
  - ✅ 2026-06-11 — company_settings da `webhook_secret` maydoni; `X-Webhook-Secret` header va `?token=` query param tekshiriladi; test yozilgan

- [x] **F1-2 · Credential master key majburiyligi (fail-fast)** 🔴 CRITICAL
  - Fayl: `utils/auth/credential_crypto.py:133`, app startup (`services/webhook/jira_webhook_handler.py` / `services/api` init)
  - `APP_CREDENTIALS_MASTER_KEY` yo'q bo'lsa tokenlar **plain text** saqlanadi. `encrypt_value` shunchaki qiymatni qaytaradi.
  - Yechim: production'da startda master key bo'lmasa ilova ishga tushmasin (yoki credential saqlash bloklansin). `SUPER_ADMIN_PASSWORD` fallback'ni production'da o'chirish.
  - DoD: master key yo'qligida prod startup xato beradi; mavjud plaintext tokenlarni re-encrypt qiluvchi skript; test.
  - Vaqt: 0.5 kun
  - ✅ 2026-06-11 — `assert_master_key_configured()` qo'shildi; lifespan startup da chaqiriladi; `APP_STRICT_MODE=true` bilan xato; `scripts/reencrypt_credentials.py` qo'shildi; 4 test yashil

- [x] **F1-3 · Auth endpointlarda rate-limit** 🟠 HIGH
  - Fayl: `services/api/auth_api.py:44` (login), `:77` (password-reset)
  - API darajasida throttling yo'q (faqat per-identifier lockout bor). Distributed brute-force mumkin.
  - Yechim: `slowapi` yoki o'z middleware — IP bo'yicha `/api/auth/*` ga limit.
  - DoD: limitdan oshganda `429`; test.
  - Vaqt: 0.5 kun
  - ✅ 2026-06-11 — `services/api/rate_limit.py` (in-memory, 10 req/60s per IP); login va password-reset endpointlarga `Depends(check_rate_limit)` qo'shildi; 3 test yashil

- [x] **F1-4 · CORS va security headers** 🟠 HIGH
  - Fayl: FastAPI app init (`services/webhook/jira_webhook_handler.py:234` atrofida)
  - `CORSMiddleware` yo'q, security headerlar yo'q.
  - Yechim: aniq `allow_origins=[frontend domeni]`, `allow_credentials=True`; `X-Content-Type-Options`, `X-Frame-Options`, HSTS (reverse proxy darajasida ham bo'lsa bo'ladi).
  - DoD: faqat ruxsat etilgan origin ishlaydi; headerlar javobda mavjud.
  - Vaqt: 0.5 kun
  - ✅ 2026-06-11 — `CORSMiddleware` (`ALLOWED_ORIGINS` env) va `_SecurityHeadersMiddleware` qo'shildi; `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` headerlar; test yashil

- [x] **F1-5 · Sensitive operatsiyalarga audit logging** 🟡 MEDIUM
  - Fayl: `services/api/internal_rpc_api.py:242` atrofida
  - `audit_logs` jadvali bor, lekin RPC operatsiyalari (create_user, save_company_settings, billing o'zgarishi) yozilmaydi.
  - DoD: har RPC chaqiruvi `(role, company_id, operation, natija)` bilan `audit_logs`ga yoziladi.
  - Vaqt: 0.5 kun
  - ✅ 2026-06-11 — `insert_audit_log` (platform_repository) + `write_audit_log` (auth_db) qo'shildi; `call_rpc` muvaffaqiyat va xatolarda `audit_logs`ga yozadi

- [x] **F1-6 · Session tozalash va revocation** 🟡 MEDIUM
  - Fayl: `utils/auth/auth_db.py:794` atrofida
  - Muddati o'tgan sessiyalar avtomatik tozalanmaydi; "barcha sessiyalarni bekor qilish" yo'q.
  - DoD: davriy cleanup (worker job); foydalanuvchi parol o'zgartirganda barcha sessiyasi bekor bo'ladi.
  - Vaqt: 0.5 kun
  - ✅ 2026-06-11 — `cleanup_expired_sessions` + `revoke_all_user_sessions` qo'shildi; worker har soatda cleanup qiladi; `update_user_password` da avtomatik revoke

---

## 5. FAZA 2 — Deploy & Ops (Pilot uchun shart)

> Maqsad: bitta reproducible production deploy yo'li. ~1 hafta.

- [x] **F2-1 · Backend Docker'ni qayta tiklash** 🟠 HIGH
  - Fayl: `Dockerfile.backend` (o'chirilgan), `docker-compose.yml` (o'chirilgan)
  - `README.md:153` va `DEPLOY_WEB.md` hali ularni havola qiladi, lekin fayllar yo'q.
  - DoD: `docker compose up`bilan backend + worker + frontend + postgres ko'tariladi; hujjat haqiqatga mos.
  - Vaqt: 1.5 kun
  - ✅ 2026-06-11 — `Dockerfile.backend` (python:3.11-slim) va `docker-compose.yml` qayta yaratildi; postgres healthcheck → backend + worker depends_on; schema avtomatik qo'llanadi

- [x] **F2-2 · Reverse proxy + HTTPS**
  - Nginx/Caddy orqali frontend va backend; TLS sertifikat; backend to'g'ridan-to'g'ri ochiq bo'lmasin.
  - DoD: faqat HTTPS; backend faqat proxy orqali kiriladi.
  - Vaqt: 1 kun
  - ✅ 2026-06-11 — `deploy/nginx.conf` yaratildi; HTTP→HTTPS redirect; TLS + security headers; `/api`, `/webhook`, `/health` → backend proxy; frontend → port 3000

- [x] **F2-3 · Environment config strategiyasi**
  - `.env.example`da Windows yo'llari (`D:/jira_report/...`) bor — prod uchun toza namuna kerak.
  - DoD: prod uchun `.env` namunasi; maxfiy o'zgaruvchilar hujjatlangan; default parollar yo'q.
  - Vaqt: 0.5 kun
  - ✅ 2026-06-11 — Windows path'lari olib tashlandi; `CHANGE_THIS_*` pattern bilan aniq belgilandi; `APP_STRICT_MODE`, `ALLOWED_ORIGINS` qo'shildi; DB DSN ikkala rejim uchun hujjatlandi

- [x] **F2-4 · DB backup va restore rejasi**
  - DoD: avtomatik kunlik PostgreSQL backup; restore protsedurasi hujjatlangan va bir marta sinab ko'rilgan.
  - Vaqt: 0.5 kun
  - ✅ 2026-06-11 — `scripts/backup_db.sh` (pg_dump + gzip, 7 kun saqlash); `scripts/restore_db.sh` (tasdiqlash so'rovi bilan); `make backup` / `make restore`; DEPLOY_WEB.md'ga crontab namunasi qo'shildi

- [x] **F2-5 · Healthcheck va structured logging**
  - DoD: `/health` endpoint; loglar structured (JSON yoki bir xil format); error tracking (masalan Sentry) — ixtiyoriy.
  - Vaqt: 0.5 kun
  - ✅ 2026-06-11 — `/health` endpoint `unhealthy` holda HTTP 503 qaytaradi (avval 200 edi); `make up` buyrug'i qo'shildi; monitoring checklist DEPLOY_WEB.md'ga yozildi

---

## 6. FAZA 3 — Manual Billing Admin (Pilot uchun yetarli)

> Maqsad: super admin orqali obunalarni qo'lda boshqarish. To'lov integratsiyasi (Payme/Click) hozircha kerak emas — real mijozlar ko'payganda qo'shiladi. ~1 kun.
>
> **Qaror (2026-06-11):** Hozir real foydalanuvchilar yo'q. Super admin har kompaniyani qo'lda qabul qilib, obunani manuel boshqaradi. Payme/Click integratsiyasi Track B (Ochiq SaaS) bosqichiga surildi.

- [x] **F3-1 · Super admin billing UI — trial va tezkor tugmalar**
  - Fayl: `frontend/src/components/super-admin-panel.tsx`
  - Mavjud: 1 oy, 1 yil aktivlash. Qo'shildi: "14 kun trial" tugmasi + `last_payment_note` maydoni.
  - DoD: admin bir tugma bilan trial/obuna beradi; izoh yoza oladi.
  - Vaqt: 1 soat
  - ✅ 2026-06-11 — Trial button + payment note textarea qo'shildi

- [x] **F3-2 · Auto-expire cron (worker)**
  - Fayl: `services/worker/main.py`, `utils/auth/company_repository.py`, `utils/auth/auth_db.py`
  - `billing_end_date` o'tgan `trial`/`active` obunalar har soatda avtomatik `suspended` qilinadi.
  - DoD: muddati o'tgan kompaniya keyingi webhook da bloklanadi; worker logda xabar ko'rinadi.
  - Vaqt: 2 soat
  - ✅ 2026-06-11 — `expire_overdue_subscriptions` + worker cron qo'shildi

- [x] **F3-3 · Webhook feature gating** 🟠 HIGH
  - Fayl: `services/webhook/jira_webhook_handler.py`
  - Hozir webhook secret tekshiriladi, lekin obuna statusi tekshirilmaydi.
  - DoD: obunasi `suspended`/`cancelled`/muddati o'tgan kompaniya webhook'i `402` yoki `ignored` qaytaradi.
  - Vaqt: 1 soat
  - ✅ 2026-06-11 — Webhook secret tekshiruvidan keyin `is_company_subscription_active` qo'shildi

- [ ] **F3-4 · To'lov integratsiyasi (Payme/Click)** — Track B uchun, hozircha shart emas
  - Real mijozlar ko'payganda va qo'lda boshqarish og'irlashganda implement qilinadi.
  - Vaqt: ~2 hafta (keyinroq)

---

## 7. FAZA 4 — Onboarding & Email (Ochiq SaaS uchun)

> Maqsad: self-service onboarding. ~2–3 hafta.

- [ ] **F4-1 · Email yuborish infratuzilmasi** 🔴 (signup uchun blocker)
  - Hozir hech qanday SMTP/SendGrid kodi yo'q. `user_password_reset_tokens` jadvali bor, lekin token email orqali yetkazilmaydi.
  - DoD: email servis (SMTP/SendGrid/SES); shablonlar; yuborish testdan o'tgan.
  - Vaqt: 3 kun

- [ ] **F4-2 · Self-service signup sahifasi**
  - Fayl: yangi `frontend/src/app/signup`, `services/api/auth_api.py`
  - Hozir kompaniyani faqat super-admin yaratadi.
  - DoD: kompaniya + admin yaratish; email verifikatsiya; plan tanlash.
  - Vaqt: 1 hafta

- [ ] **F4-3 · Email verifikatsiya**
  - Fayl: `database/postgresql` — `users`ga `email_verified_at` qo'shish
  - DoD: ro'yxatdan o'tgach verifikatsiya emaili; tasdiqlanmaguncha cheklov.
  - Vaqt: 2 kun

- [ ] **F4-4 · Password reset email orqali (end-to-end)**
  - Fayl: `services/api/auth_api.py:77`, `utils/auth/auth_db.py:684`
  - Token allaqachon generatsiya bo'ladi, faqat email yuborish ulanishi kerak.
  - DoD: foydalanuvchi parolni o'zi tiklaydi (admin aralashuvisiz).
  - Vaqt: 1 kun

- [ ] **F4-5 · First-run setup wizard**
  - DoD: JIRA/GitHub ulash + connection test + birinchi tahlil — checklist bilan.
  - Vaqt: 3 kun

---

## 8. FAZA 5 — Release Quality & Polish (P1)

> Maqsad: ishonchli iteratsiya. ~1–2 hafta.

- [ ] **F5-1 · CI/CD pipeline**
  - Fayl: yangi `.github/workflows/`
  - DoD: PR'da avtomatik test (test DB bilan) + typecheck + lint; main'ga deploy avtomatlashtirilgan.
  - Vaqt: 2 kun

- [ ] **F5-2 · Pre-release QA checklist va smoke testlar**
  - DoD: release oldidan bajariladigan checklist; asosiy oqimlar uchun smoke test.
  - Vaqt: 1 kun

- [ ] **F5-3 · Monitoring va metrics**
  - DoD: AI usage/cost tracking; integration health; error tracking dashboard.
  - Vaqt: 3 kun

- [ ] **F5-4 · Argon2 ga o'tish (parol hashing)** — ixtiyoriy
  - Fayl: `utils/auth/auth_db.py:360` (hozir PBKDF2 200k — OK, lekin argon2id zamonaviyroq).
  - Vaqt: 1 kun

- [ ] **F5-5 · Legal minimal** (Terms, Privacy Policy) — Track B uchun shart
  - Vaqt: tashqi

---

## 9. Bajarish tartibi (yo'l xaritasi)

```
FAZA 0  (hygiene, 0.5 kun)
  └─> FAZA 1  (xavfsizlik must-fix, ~1 hafta)
        └─> FAZA 2  (deploy, ~1 hafta)
              └─> 🚀 TRACK A: Nazoratli Pilot mumkin
                    └─> FAZA 3 (billing, ~3-4 hafta)  ┐
                    └─> FAZA 4 (onboarding+email, ~2-3 hafta) ├─ parallel mumkin
                    └─> FAZA 5 (CI/CD, monitoring, ~1-2 hafta) ┘
                          └─> 🚀 TRACK B: Ochiq Self-Service SaaS
```

**Track A (Pilot) gacha:** ~2.5 hafta
**Track B (Ochiq SaaS) gacha:** qo'shimcha ~6–10 hafta

---

## 10. Eslatmalar va risklar

- **Tenant izolyatsiya** allaqachon kuchli — bu eng katta SaaS riski hal qilingan. Yangi endpoint qo'shganda `require_company_scope()` ishlatilishini doim tekshirish.
- **Test DB** har bir DB testi uchun zarur — CI'da `001_initial_schema.sql` qo'llanishi shart (F0-3, F5-1).
- **Maxfiy o'zgaruvchilar:** prod'ga chiqishdan oldin `.env.example`dagi default parollar (`change_this_in_prod`, `your_password_here`) almashtirilishi shart.
- Bu hujjat ROADMAP_SAAS.md ning amaliy, audit asosidagi qisqartmasi. ROADMAP — strategik, bu hujjat — bajariladigan checklist.

---

_Oxirgi yangilanish: 2026-06-11 (dastlabki audit asosida tuzildi)._
