# QA-Assistant — Chuqur Professional Tahlil

**Sana:** 2026-07-03
**Usul:** 6 ta mustaqil yo'nalishda parallel chuqur audit: (1) backend kod sifati, (2) frontend Next.js, (3) test va CI, (4) xavfsizlik qayta-tekshiruvi, (5) ops/deploy, (6) arxitektura va mahsulot yetukligi. Har bir topilma haqiqiy kod (`fayl:qator`) bilan tasdiqlangan.
**Bog'liqlik:** Bu hujjat `AUDIT_HISOBOT_2026-07-02.md` ning DAVOMI — u yerdagi topilmalar takrorlanmaydi, faqat ochiq qolgan itemlar holati tekshirilib, YANGI topilmalar qo'shilgan. Yo'l xaritasi ham o'sha raqamlashni davom ettiradi (Faza 5+).

---

## 0. Bir qarashda

> Kechagi audit blockerlari tuzatilgani tasdiqlandi (webhook secret, RPC bypass, fail-closed crypto, PBKDF2 — hammasi joyida). Lekin "professional mahsulot" darajasiga yetish uchun **uch qatlamda** ish bor: (a) **darhol tuzatiladigan buzuq oqimlar** (parol-reset UI orqali umuman ishlamaydi; inline rejimda crash-recovery butunlay o'chib qoladi), (b) **muhandislik intizomi** (0 ta linter, CI'da pytest natijasi e'tiborsiz, 12 ta "o'lik" test o'tib turibdi, frontend'da 0 test), (c) **AI-mahsulot intizomi** (prompt versiyalash va sifat-regressiya (eval) tizimi YO'Q — prompt o'zgarishi mijoz commentlarini jimgina buzishi mumkin).

**Eng xavfli 7 ta yangi topilma:**

| # | Topilma | Xavf |
|---|---|---|
| 1 | Parol-reset yakunlash route'i frontend'da mavjud emas — hech kim UI orqali parolini tiklay olmaydi | 🔴 Buzilgan oqim |
| 2 | `inline` rejimda reaper/sweeper/retention ISHLAMAYDI (worker'da yashaydi) — `.env.example` default = `inline` → BLOCKER-3 tuzatuvi config orqali yo'qoladi | 🔴 Regressiya xavfi |
| 3 | Windows deploy: TLS'siz `0.0.0.0:8000` internetga ochiladi; jarayon nazorati (restart-on-crash) yo'q; backup'ni restore qiladigan skript yo'q | 🔴 Jonli prod xavfi |
| 4 | Webhook body autentifikatsiyadan OLDIN to'liq parse qilinadi, hajm chegarasisiz — auth'siz DoS | 🟠 |
| 5 | `update.bat` backup'siz `git pull origin main` qiladi — yangi kod `dev1` da, rollback yo'q | 🟠 |
| 6 | CI'da pytest `continue-on-error: true` — Python xatti-harakati umuman gate qilinmaydi; 12 ta `MockGeminiHelper` testi o'chirilgan logikani "testlaydi" va doim o'tadi | 🟠 Soxta ishonch |
| 7 | Prompt versiyalash + golden-set/eval yo'q — checker sifati pasayishini mijozdan OLDIN bilishning hech qanday yo'li yo'q | 🟠 AI-sifat |

---

## 1. Oldingi audit ochiq (⏳) itemlari — hozirgi holat (kod bo'yicha tekshirildi)

| Item | Holat | Dalil |
|---|---|---|
| F2-5 per-company oylik xarajat cheklovi | ⏳ **Hali yo'q** | `ai_usage_events` ledger yozadi (`ai_usage_repository.py:90`), lekin summani HECH KIM o'qib enforce qilmaydi; yagona gate — free-run count (`quota_repository.py:15`) |
| F2-11 LICENSE/ToS/maxfiylik | ⏳ Yo'q | Biznes kirishi kutilmoqda |
| F3-12 log rotation | ⏳ **Hali yo'q** | `core/logger.py:75-112` oddiy `FileHandler` → `data/webhook.log`, rotatsiyasiz; `RotatingFileHandler` repoda umuman yo'q |
| F3-14 webhook POST async bloklash | ⏳ **Ochiq, va yozilganidan YOMONROQ** | `_jira_webhook_impl` (`jira_webhook_handler.py:410`) ichida sync DB chaqiruvlardan tashqari **sinxron tashqi HTTP** ham bor: `:668` da `requests.get` (JIRA). Sekin JIRA barcha webhooklarning event loop'ini to'xtatadi |
| F3-15 import-time `init_db` | ⏳ Ochiq | `task_db.py:985-989` hali import paytida migratsiya chaqiradi (advisory lock tufayli xavfsizroq, lekin olib tashlanmagan) |
| F4-17 ikkita run-repository | ⏳ Ochiq | `checker_run_repository.py` (396q) vs `analysis_run_repository.py` (399q) — diff faqat mexanik rename + `module_key` |
| F4-18 string-matched error klassifikatsiya | ⏳ Ochiq | `error_handler.py:30-81` hali o'zbekcha matn qidiradi; ladder `service_runner.py` da 4 marta takror |
| F4-20 ruff/mypy + ulkan funksiyalar | ⏳ Ochiq | Repoda 0 ta linter/formatter/type config; 13 ta funksiya ≥150 qator (eng katta: `_run_agent2_per_requirement` — 421 qator, 7 daraja nesting) |
| `/metrics`, `/settings` autentifikatsiyasiz | ⏳ Ochiq | `jira_webhook_handler.py:913-991` — cross-company agregat + config, auth'siz. Docker'da nginx tasodifan yashiradi (`nginx.conf:57` regex `/metrics`ni o'tkazmaydi), lekin **Windows deploy'da to'g'ridan-to'g'ri ochiq** |

---

## 2. 🔴 KRITIK yangi topilmalar (darhol tuzatish kerak)

### 2.1. Parol-reset yakunlash oqimi BUZILGAN (frontend)
`frontend/src/app/(auth)/reset-password/page.tsx:39` → `POST /api/auth/password-reset` ga yuboradi, lekin `src/app/api/auth/` da faqat `login`, `logout`, `me`, `request-reset` bor — **`password-reset/route.ts` mavjud emas**. POST 404 qaytaradi → foydalanuvchi doim "Token yaroqsiz yoki muddati tugagan" ko'radi. So'rov qismi ishlaydi, yakunlash qismi yo'q — **hech bir foydalanuvchi UI orqali parolini tiklay olmaydi**.
**Tuzatish:** BFF route q