# QA-Assistant

Multi-tenant SaaS: JIRA task "Testing" statusiga o'tganda webhook orqali ishga
tushib, **multi-agent Gemini AI** yordamida ikki servisni ketma-ket bajaradi:

1. **Servis-1 — TZ-PR Checker:** JIRA task texnik topshirig'i (TZ) va unga bog'liq
   GitHub Pull Request mosligini tahlil qiladi → moslik bali (compliance score) →
   JIRA'ga izoh. Ball chegaradan past bo'lsa task avtomatik developerga qaytariladi.
2. **Servis-2 — Test Case Generator:** TZ (va PR) asosida test-case'lar yaratadi →
   JIRA'ga izoh.

Har uchala kirish nuqtasi — **webhook, web-UI, background worker** — aynan bir xil
multi-agent engine'ni ishlatadi.

**Company:** Green White Solutions (SmartUpX)

---

## ✨ Asosiy imkoniyatlar

- **Multi-agent TZ-PR Checker** — `agent1 (scope) → agent1b (merge) → agent2 (verify)
  → agent3 (arbiter)`. Yakuniy moslik bali LLM emas, **kodda deterministik**
  hisoblanadi (skip/texnik talablar maxrajdan chiqariladi).
- **Multi-agent Test Case Generator** — `agent1 (checker kontrakti) → agent2 (yozish)
  → agent3 (audit)`.
- **Multi-tenant** — har kompaniyaning o'z JIRA/GitHub/Gemini kalitlari va sozlamalari
  (shifrlangan, DB'da izolyatsiya qilingan). Kompaniya A kompaniya B ma'lumotini
  o'qiy olmaydi.
- **AI resilience** — transient/permanent xato taksonomiyasi, ko'p-kalit fallback,
  model fallback (Pro → Flash), per-request timeout, blocked-task retry scheduler.
- **Global bepul kvota** — o'z Gemini kaliti bo'lmagan kompaniya uchun har modulga
  cheklangan tekin run (super-admin default kaliti).
- **Web portal (Next.js)** — Monitoring, TZ-PR Checker, Test Case Generator,
  Settings, Team, Super Admin sahifalari real backend flow bilan.

---

## 🏗 Arxitektura

```
JIRA webhook → jira_webhook_handler.py (orchestrator)
  → filtrlar (status, issue type, assignee) → DB holat → AI_SKIP tekshiruvi
  → queue_manager (AI lock, rate limit)
  → Servis-1: multi-agent checker → JIRA comment
  → Servis-2: multi-agent testcase → JIRA comment
```

- **Backend:** FastAPI (`services/webhook/jira_webhook_handler.py`)
- **Worker:** alohida runtime (`services/worker/main.py`) — `queue` rejimida
  joblarni DB navbatdan olib bajaradi (crash-recovery reaper/sweeper bilan)
- **Frontend:** Next.js (`frontend/`)
- **DB:** PostgreSQL (versiyalangan migratsiya, connection pool)

Batafsil: [CLAUDE.md](CLAUDE.md) — arxitektura, oqim va qarorlar.

---

## 🚀 O'rnatish (dev)

```bash
git clone <repo-url>
cd QA-Assistant

python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # sozlab chiqing (izohlar .env.example'da)
```

Talablar:
- **Python 3.11** (Docker `python:3.11-slim` bilan mos)
- **PostgreSQL** — `APP_POSTGRES_DSN` sozlangan bo'lishi shart

Migratsiya startup'da avtomatik qo'llanadi (webhook lifespan / worker / monitoring).

> Kompaniyaga xos JIRA/GitHub/Gemini kalitlari `.env`da emas — web portal
> (Settings / Super Admin) orqali kiritiladi va shifrlangan holda DB'da saqlanadi.
> `.env` faqat platforma-darajali sozlamalar uchun (`APP_POSTGRES_DSN`,
> `APP_CREDENTIALS_MASTER_KEY`, SMTP, webhook secret majburligi va h.k.).

---

## 💻 Ishga tushirish

```bash
./start.sh
```

- `start.sh` Next.js frontend + FastAPI backendni birga ko'taradi.
- `.env`da `APP_WEBHOOK_EXECUTION_MODE=queue` bo'lsa worker ham avtomatik ko'tariladi.
- Browser: `http://localhost:3000`

Qo'lda:
```bash
python -m uvicorn services.webhook.jira_webhook_handler:app --host 0.0.0.0 --port 8000
python -m services.worker.main        # queue rejimi uchun
cd frontend && npm run dev
```

Deploy (Docker): [DEPLOY_WEB.md](DEPLOY_WEB.md), `docker-compose.yml`.

---

## 📁 Struktura

```
QA-Assistant/
├── frontend/               # Next.js web portal
├── services/
│   ├── webhook/            # webhook endpoint, orchestrator, queue, retry
│   ├── checkers/           # multi-agent TZ-PR checker engine
│   ├── generators/         # multi-agent testcase engine
│   ├── worker/             # background worker runtime
│   └── api/                # UI backend API (tzpr, testcase, monitoring, rpc)
├── core/                   # base service, setup checks, preflight, helpers
├── utils/                  # ai (gemini), auth, database, jira, github
├── config/                 # app_settings (dataclass-based)
├── database/postgresql/    # versiyalangan schema migratsiyalar
├── docker-compose.yml · Dockerfile.backend · start.sh
└── requirements.txt        # qayta qurish: python scripts/build_requirements.py --write
```

---

## 🎯 Oqim

### Servis-1 — TZ-PR Checker
1. JIRA'dan TZ (summary + description) olinadi
2. GitHub'dan bog'liq PR topiladi (JIRA link yoki avto-qidiruv)
3. Multi-agent AI TZ↔kod mosligini tahlil qiladi
4. Deterministik moslik bali → JIRA izoh
5. Ball chegaradan past → task avtomatik qaytariladi (`APP_MAX_RETURN_COUNT` chegarasi bilan)

### Servis-2 — Test Case Generator
1. Servis-1 muvaffaqiyatli o'tgach ishga tushadi
2. TZ (+ PR) asosida test-case'lar yaratiladi
3. Audit agent tekshiradi → JIRA izoh

---

## 🧪 Testing

```bash
# DB testlari uchun:
make test-setup                                   # test DB + schema
export APP_TEST_POSTGRES_DSN=postgresql://localhost/jira_ai_test
make test

pytest                                            # yoki to'g'ridan-to'g'ri
cd frontend && npm run typecheck && npm run build
```

DSN bo'lmasa DB testlari `skip` bo'ladi (production DB'ga tegmaydi).

---

## 🔧 Texnologiyalar

- **Gemini AI** (multi-agent, multi-key fallback) — tahlil yadrosi
- **FastAPI** — backend API va webhook
- **Next.js** — web portal
- **PostgreSQL** — yagona runtime bazasi (pool + versiyalangan migratsiya)
- **Docker / docker-compose** — deploy paketlash

---

## 📝 License

Private — Green White Solutions (SmartUpX). Barcha huquqlar himoyalangan.
