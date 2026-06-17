# Production Readiness Plan — JIRA-AI-Analyzer

> Maqsad: loyihani 10 → 100+ kompaniya uchun sotuvga tayyor holatga keltirish.
> Sana: 2026-06-17 | Holat: **~70% tayyor**
> Bu hujjat audit natijasi. Ishni shu yerdan davom ettiramiz.

---

## Qisqa xulosa

- **Token kalitlar aralashmaydi** — multi-tenant izolyatsiya mustahkam ✅
- **Asosiy arxitektura (queue + worker + PostgreSQL) to'g'ri qurilgan** ✅
- **100 kompaniya uchun hozircha tayyor EMAS** — bir nechta production blocker bor
- **10 kompaniya:** kichik tuzatishlardan keyin bugun chiqsa bo'ladi
- **100 kompaniya:** ~1-2 hafta ish

---

## 1. Token izolyatsiyasi — TASDIQLANGAN ✅

Asosiy xavotir ("kompaniyalar kalitlari aralashib ketadimi") — **aralashmaydi**.

| Tekshiruv | Holat | Dalil (fayl) |
|---|---|---|
| Har kompaniya kaliti alohida saqlanadi | ✅ | `company_settings` jadvali, `company_id` bilan |
| company_id to'g'ri yo'naltiriladi | ✅ | `jira_webhook_handler.py` — project key → kompaniya |
| Har webhook YANGI service instance | ✅ | `service_runner.py:98` — singleton ulashilmaydi |
| Kalitlar instance darajasida cached | ✅ | `base_service.py:_get_creds()` |
| Gemini key freeze izolyatsiyasi | ✅ | `GeminiHelper` har instance o'z `api_keys` + instance-level `_frozen_until` |

**Eslatma:** `gemini_helper.py:15` `_settings_cache` global — lekin faqat *vaqt sozlamalari* (`min_interval`, `freeze_duration`), kalit EMAS. Bu xavf emas.

---

## 2. Ishlash rejimlari (kontekst)

`APP_WEBHOOK_EXECUTION_MODE` 2 rejim:
- `inline` (default) — webhook FastAPI ichida ishlaydi. Xavfli (parallel cache, duplicate retry).
- `queue` (docker-compose buni qo'yadi ✅) — DB navbat + alohida worker. **To'g'ri production rejim.**

Worker `FOR UPDATE SKIP LOCKED` + `dedupe_key` bilan xavfsiz, gorizontal kengaytiriladi.
**Bottleneck:** worker job'larni KETMA-KET bittadan ishlaydi (`worker/main.py:204-227`) → bitta worker yetarli emas.

---

## 3. ISH REJASI — Ustuvorlik bo'yicha

### 🔴 FAZA A — KRITIK (100 kompaniyadan oldin SHART)

- [ ] **A1. DB connection pool qo'shish**
  - Muammo: `runtime.py:54-67` har so'rovda `psycopg.connect()` ochadi. PG `max_connections=100` → yuqori yukda "too many connections" → tizim qulaydi.
  - Yechim: `psycopg_pool.ConnectionPool(max_size=20)` yoki PgBouncer.
  - Fayl: `utils/database/runtime.py`

- [ ] **A2. Webhook secret'ni majburiy qilish**
  - Muammo: `jira_webhook_handler.py:445-452` — kompaniya `webhook_secret` qo'ymasa, tekshiruv o'tkazib yuboriladi. Har kim POST yuborib AI'ni ishlatib pul sarflashi mumkin.
  - Yechim: secret bo'lmasa webhook'ni rad qilish (yoki kompaniya setup'da majburiy maydon).
  - Fayl: `jira_webhook_handler.py`

- [ ] **A3. Bir nechta worker ishga tushirish**
  - Muammo: bitta worker ketma-ket ≈ 1500-2800 task/kun. 100 kompaniya × 50 = 5000 task/kun → navbat orqada qoladi.
  - Yechim: docker-compose'da worker'ni `deploy.replicas` yoki bir nechta worker konteyner. (DB navbat buni xavfsiz qiladi.)
  - Fayl: `docker-compose.yml`

### 🟡 FAZA B — MUHIM (tez orada)

- [ ] **B1. Centralized logging** — loglar lokal `data/webhook.log`'da; 100 kompaniyada muammoni topib bo'lmaydi. → ELK / CloudWatch / Loki.
- [ ] **B2. Error tracking + alerting** — Sentry yo'q; kritik xato sezdirmay o'tadi.
- [ ] **B3. Kalit shifrlashni majburiy qilish** — `credential_crypto` + `APP_CREDENTIALS_MASTER_KEY` ixtiyoriy; master key bo'lmasa plaintext saqlanadi. DB dump xavfi.
- [ ] **B4. `task_id` indeksi qo'shish** — `task_processing(task_id)` indeks yo'q; jadval o'sgani sayin qidiruv sekinlashadi.

### 🟢 FAZA C — YAXSHILASH (bloker emas)

- [ ] **C1. PR cache kalitiga company_id qo'shish** — `pr_cache.py:65` `task_key` bilan kalitlanadi. Queue+ketma-ket worker'da to'qnashuv bo'lmaydi, lekin arzon ehtiyot: `f"{company_id}:{task_key}"`.
- [ ] **C2. Data retention / arxiv siyosati** — `task_processing` + `task_status_history` cheksiz o'sadi (sekin: ~100MB/yil).
- [ ] **C3. Load test** — 100 kompaniya bir vaqtda webhook stsenariysi test qilinmagan.
- [ ] **C4. Graceful shutdown** — SIGTERM handler yo'q; in-flight job'lar uziladi.
- [ ] **C5. uvicorn `--workers`** — API faqat navbatga yozadi, shuning uchun yengil; baribir 2-4 worker yaxshi.

---

## 4. Muammo EMAS (audit oshirib yuborgan, tasdiqlangan)

- ✅ `.env` git'da YO'Q — `.gitignore:106`'da. Tokenlar oshkor bo'lmagan.
- ✅ PR cache "cross-tenant leak" — queue rejimda ketma-ket ishlov tufayli yuz bermaydi.
- ✅ `reload=True` faqat lokal run uchun; Docker CMD'da yo'q.
- ✅ Streamlit yo'q — FastAPI + Next.js.
- ✅ Parollar PBKDF2-HMAC-SHA256, 200k iteratsiya bilan hash.

---

## 5. Holat jadvali

| Jihat | Baho |
|---|---|
| Multi-tenant token izolyatsiyasi | ✅ Mustahkam |
| Asosiy arxitektura (queue, worker, DB) | ✅ To'g'ri |
| Xavfsizlik (hash, shifrlash, git) | ✅ Asoslar yaxshi (secret majburiyligi kerak) |
| Scalability (connection pool, ko'p worker) | 🔴 Tuzatish kerak |
| Operatsiya (monitoring, alerting) | 🔴 Yetishmaydi |

**Keyingi qadam:** FAZA A dan boshlaymiz (A1 → A2 → A3).
</content>
</invoke>