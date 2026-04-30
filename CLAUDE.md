# CLAUDE.md — JIRA-AI-Analyzer

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
  → Servis-1 (TZ-PR tahlil) → JIRA comment
  → 15s kutish
  → Servis-2 (Testcase) → JIRA comment
  → PR cache tozalash
```

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
| `services/checkers/tz_pr_checker.py` | 7-bosqichli TZ-PR AI tahlil |
| `services/generators/testcase_generator.py` | 6-bosqichli testcase generatsiya |
| `core/tz_helper.py` | TZHelper + CommentSeparator |
| `core/base_service.py` | Servislar uchun umumiy asos (lazy loading) |
| `core/pr_helper.py` | GitHub PR qidirish va olish |
| `core/constants.py` | Return reason kodlari |
| `utils/database/task_db.py` | SQLite holat boshqaruvi |
| `utils/auth/auth_db.py` | Multi-tenant kompaniya/foydalanuvchi DB |
| `utils/auth/auth_manager.py` | Streamlit session boshqaruvi |
| `utils/jira/jira_client.py` | JIRA API (task, PR link, Figma link) |
| `utils/jira/jira_comment_writer.py` | JIRA comment yozish (ADF + fallback) |
| `utils/jira/jira_status_manager.py` | JIRA task status o'zgartirish |
| `utils/jira/jira_adf_formatter.py` | S1 uchun ADF document builder |
| `utils/jira/testcase_adf_formatter.py` | S2 uchun ADF document builder |
| `utils/ai/gemini_helper.py` | Gemini AI (multi-key fallback, model fallback, retry) |
| `ui/components/loading.py` | ProgressManager — animatsiyali step-by-step progress (JS timer) |
| `utils/github/github_client.py` | GitHub PR API |
| `utils/pr_cache.py` | Jarayon ichida PR ma'lumotlari keshi |
| `config/app_settings.py` | Barcha sozlamalar (dataclass-based, JSON) |

---

## To'liq oqim (webhook → comment)

```
1. JIRA webhook POST /webhook/jira
2. Event tekshiruvi: faqat jira:issue_updated
3. Changelog: status o'zgardimi?
4. Kompaniya: project key orqali topiladi (DEV-1234 → DEV → jasur co.)
5. Trigger status: yangi status ro'yxatdami?
6. Filtrlar: issue type, assignee exclusion
7. DB: task holati tekshiruvi (duplicate, reset if needed)
8. AI_SKIP: skip_code comment da bormi? → S1 skip, S2 baribir ishlaydi
9. queue_manager: AI lock olish (timeout bo'lsa blocked)
10. Rate limit: min interval kutish (6s default)

--- Servis-1 ---
11. company credentials olish
12. return_reason DB dan o'qish → is_recheck aniqlash
13. TZPRService.analyze_task():
    a. JIRA dan task details
    b. PRHelper: GitHub PR qidirish va olish (Smart Patch ixtiyoriy)
    c. TZHelper: TZ formatlash, comment tahlili
    d. Gemini prompt yaratish (TZ + PR + dev izohlar)
    e. GeminiHelper.analyze() → retry transient, freeze permanent
    f. Compliance score ajratish (regex)
14. Muvaffaqiyatli → ADF comment yozish (fallback: simple)
15. service1_done, score DB ga
16. Score < threshold → task qaytarish + return notification comment
    → set_return_reason(WARN_LOW_SCORE)

--- Servis-2 ---
17. Shartlar tekshiruvi (S1 done, score OK, not returned)
18. TestCaseGeneratorService.generate_test_cases():
    a. JIRA task details
    b. PR cache dan foydalanish (S1 saqlagan)
    c. TZ uzunlik tekshiruvi
    d. Gemini prompt (TZ + PR + test types)
    e. JSON parse → TestCase objects
19. ADF comment yozish (fallback: simple)
20. service2_done DB ga
21. PR cache tozalash

--- Retry ---
22. _blocked_retry_scheduler() har 60s tekshiradi
23. blocked_retry_at <= NOW bo'lsa qayta urinadi
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

**Strategy fallback (tz_pr_checker):**
503/unavailable xatoda Strategy 2 va 3 o'tkazib yuboriladi — diff hajmini kamaytirish server overloadga yordam bermaydi.

---

## PR Cache (`utils/pr_cache.py`)

4 ta kesh, jarayon xotirasida, bir signal uchun ishlaydi:
- `skip_cache` — AI_SKIP topilganmi
- `pr_exists_cache` — PR bormi
- `pr_merged_cache` — PR merge qilinganmi
- `pr_info_cache` — to'liq PR ma'lumoti (S1 saqlaydi, S2 o'qiydi)

S2 tugagach `clear_task_cache()` bilan tozalanadi.

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
Webhook kelganda project key orqali kompaniya topiladi (DEV → kompaniya).
`company_id` barcha servis funksiyalariga uzatiladi.

---

## DB migratsiyalar

- v2 — assignee, task_type, feature_name, technology_stack
- v3 — blocked_at, blocked_retry_at, block_reason
- v4 — company_id (2026-02)
- v5 — return_reason (2026-04-28)

Yangi ustun qo'shilganda: CREATE TABLE ga + `_migrate_db_vN()` + chaqiruv joyiga.

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
- `testcase_generator.py` — JIRA olish, TZ tahlil, AI chaqirishdan oldin
- `tz_pr_checker.py` — AI chaqirishdan oldin
- `pr_helper.py` — PR tahlil bosqichida (mavjud)

Sahifa callbacklari `msg.lower()` orqali qaysi stepga tegishliligini aniqlaydi.

---

## Kod yozish qoidalari

- **Ssenariy tahlil qil** — yangi feature qo'shishdan avval "bu haqiqatda ishga tushadimi?" deb tekshir
- **Comment kerak emas** — kod o'zini tushuntirsin, faqat noaniq sabablar uchun
- Javoblarni O'zbek tilida ber