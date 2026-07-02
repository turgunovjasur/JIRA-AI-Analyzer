# QA Metrics Dashboard — Loyihalash va Tahlil Hujjati

> **Holat:** Loyiha tavsiyasi (design doc) — kod yozilmagan.
> **Sana:** 2026-07-02
> **Muallif konteksti:** QA engineer talabi — sprint/reliz kesimida bug/task metrikalari va "forma" (ekran) bo'yicha tahlil.
> **Tekshiruv manbai:** jonli Jira (`smartupx.atlassian.net`), loyiha kodbazasi, GitHub client. Barcha raqamlar va maydon nomlari real ma'lumotdan olingan.

---

## 1. Maqsad — foydalanuvchi savollari

QA engineer quyidagi savollarga javob beradigan yangi **modul (sahifa)** so'radi:

| # | Savol | Metrik |
|---|---|---|
| S1 | Sprint / relizda qancha **bug** chiqyapti? | Bug soni (sprint bo'yicha, vaqt qatori) |
| S2 | Qancha **task** qilyapmiz? | Task soni |
| S3 | Task **type**lari nima? | issuetype bo'yicha taqsimot |
| S4 | Qaysi **formalarda ishlayapmiz**? | Forma bo'yicha task soni |
| S5 | Qaysi **formalarda bug chiqyapti**? | Forma bo'yicha bug soni |
| S6 | Qaysi **formalar ishlandi** (tayyor)? | Forma × status (Closed/Done) |
| S7 | Bu relizda qaysi formalarni **ko'proq test qilish** kerak? | Risk skori (bug zichligi + churn + status) |

**Eng qiyin va butun modulni belgilaydigan savol — "forma" (S4–S7).** Chunki Jira'da forma alohida maydonda saqlanmaydi (pastda batafsil). Qolgan hammasi (S1–S3) mavjud maydonlardan to'g'ridan-to'g'ri chiqadi.

---

## 2. Ma'lumot manbalari — jonli Jira tekshiruvi (real)

Sayt: **smartupx.atlassian.net** (`cloudId=7fa56e5c-66bb-4ae5-b285-35ee5462b77f`). Asosiy loyihalar: **DEV** ("DEV BACKEND TEAM", id 10008) va **MOB** ("DEV MOBILE TEAM").

### 2.1 Nima ISHLAYDI (ishonchli o'qsa bo'ladigan maydonlar)

| Maydon | Field ID | Holat | Izoh |
|---|---|---|---|
| **Sprint** | `customfield_10020` | ✅ Faol | Qiymat: `{"id":5673,"name":"Sprint 76 BA","state":"active","startDate":...,"endDate":...}`. Board id `10`. **DEV/BA sub-track**: nom `"Sprint 66 DEV"` vs `"Sprint 76 BA"` — suffiks bo'yicha ajratiladi. Ba'zi sprintlarda `startDate/endDate` bor, "future" larda bo'sh. |
| **Issue type** | `issuetype` | ✅ Faol | DEV type'lari: `DEV-BUG`, `DEV- PROD TASK`, `DEV-TECHTASK`, `DEV-CLIENT TASK`, `AnalysisTask`, `BA-*` va h.k. |
| **Status** | `status` | ✅ Faol | Pastda 2.3 ga qarang. |
| **Yaratilgan / hal etilgan** | `created`, `resolutiondate` | ✅ Faol | Vaqt qatori uchun asos. |
| **Bug Date** | `customfield_10452` | ⚠️ Qisman | Ba'zi buglarda; `created` ishonchliroq. |
| **Story points** | `customfield_10016` | ⚠️ Qisman | Velocity uchun (bo'lsa). |
| **PR link (Development)** | `customfield_10000` | ⚠️ Qisman | Kod yozilgan taskda `pullrequest {state:"MERGED", count, provider}` rollup. Per-forma emas, faqat holat+son. |
| **Assignee** | `assignee` | ✅ Faol | Developer yuki uchun. |

### 2.2 Nima ISHLAMAYDI (bo'sh — ishonmang)

| Maydon | Holat | Xulosa |
|---|---|---|
| `fixVersions` (reliz) | ❌ 0/30 DEV, 0/25 MOB — **hamma joyda bo'sh** | **"Bug per reliz" ni fixVersion ustiga qurmang.** |
| `customfield_10582` "For Release" | ❌ 30/30 null | Reliz maydoni ishlatilmaydi. |
| `components` | ❌ 0/30 DEV, 0/25 MOB | Forma uchun mo'ljallangan, lekin **umuman ishlatilmaydi**. |
| `labels` | ❌ ~shovqin (1/30 = `"AZIM"`, mijoz nomi) | Formaga yaramaydi. |
| `parent` / Epic | ❌ 0/30 top-level bug'da parent yo'q | Bug'lar Epic/feature'ga rollup bo'lmaydi. |
| `issuelinks` | ❌ Kam (faqat `DEV-9046 clones DEV-8924`) | Bug↔task bog'lanishi ishonchsiz. |

> **Reliz uchun qaror:** Jira'da reliz maydoni yo'q → **sprint = reliz proksisi**, yoki **sana oynasi** (masalan "oxirgi 30 kun"). Ikkalasi ham modulda tanlanadigan bo'ladi.

### 2.3 Status workflow (oxirgi 100 ta DEV-BUG)

| Status | statusCategory | Son |
|---|---|---|
| `Closed` | Done (yashil) | 66 |
| `Rejected` | Done (yashil) | 22 |
| `To Do` | To Do | 7 |
| `In Progress` | In Progress | 2 |
| `Testing` | Done (yashil) | 2 |
| `MERGED` | In Progress | 1 |
| (`Pull request`) | In Progress | task'larda |

> **Muhim:** faqat `statusCategory` ga tayanmang — `Testing` va `Rejected` ikkalasi ham kategoriyada **Done**. Aniq status nomlari bilan modellashtiring:
> - **"Tayyor"** ≈ `Closed` (resolution=Done)
> - **"Test kerak"** ≈ `Testing`
> - **"Bug emas"** = `Rejected` (buglarni sanashda chiqarib tashlash mumkin)
> - **"Jarayonda"** = `In Progress` / `MERGED` / `Pull request`

### 2.4 Bug hajmi va qamrov

- **DEV `DEV-BUG`, oxirgi 90 kun = 144 ta** (~1.6 bug/kun). Oraliq: 2026-04-06 → 2026-06-30.
- **MOB `Баг` = muzlagan** (oxirgi bug 2026-02-10; 12 oyda faqat 38 ta, so'nggi 90 kunda 0). Mobil buglar endi DEV loyihasiga yozilyapti (`Мобильный дашборд...`, `MOB PROD ...`).

> **Qaror:** Bug manbai sifatida **faqat DEV loyihasiga** e'tibor bering. MOB legacy. (Kelajakda kompaniya sozlamasidagi `jira_project_keys` orqali ko'p loyiha qo'llab-quvvatlanadi.)

---

## 3. ENG MUHIM MUAMMO: "Forma" qanday aniqlanadi?

**Jira'da formani beradigan tuzilgan (structured) maydon YO'Q.** Forma **erkin matnda** yashiringan. Uni ajratib olishning yagona yo'li — matn + kod yo'llaridan **derivatsiya (extraction)**.

### 3.1 Forma qayerda "yashiringan" (real misollar)

**(a) Summary — prefiks + modul nomi (nomuvofiq):**
```
room_importdagi bug                                    → forma: room_import
BUGX - ...в модуле Продажи...                          → modul: Продажа (Sotuv)
BUGX - В тепловой карте не работает фильтр...           → modul: Тепловая карта
BUGX - Мобильный дашборд показывает неверные данные...   → modul: Мобильный дашборд (КПЭ)
Billing: Litsenziya berishda predoplatani...            → modul: Billing
BUGX: Мобилка   /   BUGX - Акция                        → foydasiz (umumiy)
```

**(b) Description — eng aniq manba (Smartup route/path bor):**
```
DEV-9080: "...в форме anor/mm/transport_level_generation_list ..."
DEV-9076: "/anor/mph/dashboards:mkpi_room_product_type_dashboard → Ui_Anor1375"
          "/trade/tph/dashboards:merchandising_dashboard → Ui_Trade296"
DEV-9077: "Yangi forma: request_limit_period_list"
DEV-9079 (BA-SPEC): "Модуль (подсистема): Продажа" + "Форма модуля: Создание заказа"
```

**(c) GitHub PR fayl yo'llari — kodda tekshirilgan aniq modul:**
Kodbaza layout'i (`utils/database/task_db.py:595` `_extract_features_from_pr_files`):
```
main/oracle/ui/{org}/{MODULE}/...          → MODULE   (masalan anor/mkw → mkw)
main/oracle/uis/form/{org}/{MODULE}/...    → MODULE   ← "form/" segmenti bor!
main/page/form/{org}/{MODULE}/...          → MODULE
```
Ya'ni "forma" tushunchasi kodda `{org}/{modul}/{forma}` route/papka strukturasiga to'g'ri keladi.

### 3.2 Prefiks lug'ati (summary boshidan — bepul signal)

| Prefiks | Ma'no |
|---|---|
| `BUGX` / `BUDX` / `BUG X` / `BUG5` | Mijozdan kelgan bug |
| `IMPX` | Improvement (yaxshilash) |
| `TECH-TASK` / `TECH - Task` | Ichki texnik task |
| `OP -` | Operatsiya |
| `AL` / `Анализ` | Analiz |
| `BA SPEC` | Biznes-analiz spetsifikatsiyasi |
| `MOB PROD` / `DEV PROD` | Ichki mahsulot task |
| `MEETING` | Yig'ilish |

### 3.3 Tavsiya: qatlamli "Form Resolver"

Formani aniqlash uchun **kaskad (birinchi topilgan yutadi)** yondashuv:

```
1-qatlam (eng aniq):  Description'dan Smartup route regex
                      r'([a-z]+/[a-z]+/[a-z_]+)' , r':([a-z_]+)' , r'Ui_([A-Za-z]+\d+)'
                      → {org}/{modul}/{forma} yoki forma_name

2-qatlam:             PR fayl yo'llari (GitHub) → modul (mkw, mm, mph, trade...)
                      [task_db._extract_features_from_pr_files allaqachon buni qiladi]

3-qatlam (keng):      Summary bo'yicha MODUL LUG'ATI (kurirovka qilingan)
                      { "Продажа|Sotuv|Заказ": "Sales", "дашборд|КПЭ": "Dashboard/KPI",
                        "тепловая карта": "Heatmap", "Billing|Litsenziya": "Billing", ... }

4-qatlam (tozalash):  Gemini AI normalizatsiya — 1–3 topolmagan yoki xom nomni
                      kanonik forma nomiga keltirish (ixtiyoriy, kvota/narx sababli)
```

Natija har issue uchun: `form_canonical` (kanonik nom) + `form_confidence` (qaysi qatlamdan) + `form_raw` (xom matn). Bu **DB'da saqlanadi va keshlanadi** — har safar qayta parse qilinmaydi.

> **Uzoq muddatli to'g'ri yechim (tashkiliy):** `components` maydonini (yoki yangi "Form" custom field) **oldinga qarab to'ldirishni boshlash** + backfill. Shunda resolver o'rniga tuzilgan maydon ishlatiladi. Buni hujjatning 11-bo'limida "ochiq qaror" sifatida qo'ydik.

---

## 4. Mavjud qayta ishlatiladigan infratuzilma

Yangi modul **noldan qurilmaydi** — quyidagilar allaqachon bor:

### 4.1 Jira/GitHub olish
- **`utils/jira/jira_client.py` → `JiraClient`**
  - `search_tasks(jql, max_results=100)` — umumiy bulk JQL (lightweight dict).
  - `get_sprint_issues_full(sprint_id)` (`:650`) — **changelog transitionlari + story points bir chaqiruvda** (dashboard uchun eng mos shablon).
  - `get_boards()`, `get_sprints(board_id, state=...)` — Agile API.
  - `get_task_details(...)` — `labels, components, pr_urls, figma_links, created, resolved` ni parse qiladi.
  - Custom field'lar sozlangan: `sprint=customfield_10020`, `story_points=customfield_10016`, `pr=customfield_10000`.
  - ⚠️ **Kamchilik:** `fixVersions` olinmaydi; sprint issue dict'ga parse qilinmaydi; **pagination loop yo'q** (`startAt` qo'shish kerak).
- **`utils/github/github_client.py` + `core/pr_helper.py`** — PR fayllari (`filename, status, patch`), faqat MERGED PR qabul qilinadi.

### 4.2 DB va agregatsiya
- **`task_processing` jadvali** (faqat **webhook orqali o'tgan** tasklar) — ustunlar: `task_type`, `assignee`, `compliance_score`, `service1/2_status`, `return_count`, `return_reason`, **`feature_name`** (PR yo'llaridan), `company_id`.
- **`task_status_history` jadvali** — `from_status, to_status, changed_at, story_points, issue_type` → time-in-status / velocity.
- **`utils/database/sprint_report_repository.py` + `services/api/sprint_report_api.py`** — `GET /api/sprint-report` allaqachon quyidagilarni qaytaradi: jami task, type bo'yicha, top feature'lar, **bug taqsimoti (feature bo'yicha)**, developer yuki. **Frontend sahifasi hali YO'Q.**
- **`services/api/monitoring_api.py`** — `get_overall_stats_df`, pandas agregatsiya.

### 4.3 Sozlama va modul tizimi
- `config/app_settings.py`: **`statistics` moduli allaqachon bor** — `ModuleVisibility.statistics_enabled=True`, `StatisticsSettings(default_chart_theme)`. (Eski `bug_analyzer` — o'lik vector-search, F4-19 da o'chirilgan.)
- **Multi-tenant:** `core/base_service.py` `BaseService(user_id yoki company_id)` → lazy `self.jira` / `self.github` (to'g'ri kompaniya kredensiallari bilan). API auth: `services/api/session_scope.py` (`load_api_session` + `require_company_scope`).

### 4.4 Frontend (⚠️ Streamlit EMAS — Next.js)
> CLAUDE.md'dagi "UI Progress animatsiyasi / `ui/components/loading.py` / `ProgressManager`" bo'limi **eskirgan**. Streamlit qatlami olib tashlangan.

- **Frontend:** Next.js 16 App Router (`frontend/src/`, React 19, TS, Tailwind v4).
- Yangi sahifa: `frontend/src/app/(app)/metrics/page.tsx` (papka nomi = route; auth `(app)/layout.tsx` orqali avtomatik).
- Navigatsiya: `components/app-shell.tsx` → `getNavItems()` (role/module gate) + `getPageMeta()`. Modul kaliti: `frontend/src/lib/product-catalog.ts` `MODULE_CATALOG`.
- UI primitivlar (tayyor): `MetricCard`, `ComplianceRing` (SVG donut), `Card`, `Badge`, `StatusPill`, `.qa-progress-bar`, semantik `<table>`.
- **Charting kutubxonasi YO'Q** — real grafik kerak bo'lsa `recharts` (bu stack uchun eng mos). KPI kartochka/ring/bar/jadval bilan oddiy dashboard dep'siz ham chiqadi.
- Server fetch: `lib/backend.ts` (`no-store`), tiplar `lib/types.ts`. Tenant: `session.auth.company_id` (UI'da company picker yo'q).

---

## 5. Arxitektura tavsiyasi

Ikki variant bor:

| Variant | Afzallik | Kamchilik |
|---|---|---|
| **A. Live JQL** (har yuklashda Jira'ga so'rov) | Doim yangi, to'liq qamrov | Sekin, rate-limit, har safar og'ir matn-parse, forma keshi yo'q |
| **B. ETL sync → DB** (davriy fon-jarayon Jira'dan tortadi, dashboard DB'dan o'qiydi) ✅ | Tez, tarixiy, forma bir marta hisoblanadi, mavjud pattern (task_processing/migrations/job_queue) ga mos | Sync jarayoni kerak, ~15 daqiqa kechikish |

**Tavsiya: B (ETL + maxsus metrik jadval).** Sabab: forma derivatsiyasi qimmat (regex + PR fetch + AI), uni har sahifa yuklashda takrorlash mumkin emas. Mavjud `task_processing` faqat webhook tasklarini qamraydi — bu yerda **to'liq DEV loyihasi** kerak.

```
[Fon sync job — har ~15 daqiqa / yoki qo'lda "Refresh"]
  JiraClient.search_tasks(  jql = "project=DEV AND updated >= -N"  , + pagination )
    → har issue: sprint(10020), issuetype, status, assignee, created, resolutiondate,
                 story_points, PR-rollup(10000), summary, description
    → FormResolver (3-bo'lim) → form_canonical + confidence
    → UPSERT  qa_metrics_issue  jadvaliga (company_id bo'yicha)

[Dashboard o'qish yo'li]
  Next.js  /app/(app)/metrics/page.tsx  (server component, requireSession)
    → lib/backend.ts.getQaMetrics({companyId, sprint|dateRange, project})
    → FastAPI  GET /api/qa-metrics  (session_scope bilan himoyalangan)
    → qa_metrics_repository.py  (SQL agregatsiya, sprint_report_repository uslubida)
    → qa_metrics_issue jadvalidan GROUP BY sprint / form / type / status
```

---

## 6. Ma'lumotlar modeli (yangi)

`database/postgresql/00N_qa_metrics.sql` (versiyalangan migratsiya orqali):

```sql
CREATE TABLE qa_metrics_issue (
    id              BIGSERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL,
    project_key     TEXT NOT NULL,           -- 'DEV'
    issue_key       TEXT NOT NULL,           -- 'DEV-9080'
    issue_type      TEXT,                    -- 'DEV-BUG', 'DEV- PROD TASK', ...
    is_bug          BOOLEAN,                 -- issue_type ⊂ bug turlaridan
    status          TEXT,                    -- 'Closed', 'Testing', ...
    status_category TEXT,                    -- 'new'|'indeterminate'|'done'
    resolution      TEXT,                    -- 'Done'|'Rejected'|NULL
    assignee        TEXT,
    sprint_id       INTEGER,                 -- customfield_10020[].id
    sprint_name     TEXT,                    -- 'Sprint 76 BA'
    sprint_track    TEXT,                    -- 'DEV' | 'BA' (nom suffiksidan)
    form_canonical  TEXT,                    -- resolver natijasi (kanonik forma/modul)
    form_raw        TEXT,                    -- xom matn
    form_confidence TEXT,                    -- 'route'|'pr_path'|'dict'|'ai'|'none'
    story_points    NUMERIC,
    has_pr          BOOLEAN,
    pr_merged       BOOLEAN,
    created_at      TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    synced_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(company_id, issue_key)
);
CREATE INDEX ix_qam_company_sprint ON qa_metrics_issue(company_id, sprint_name);
CREATE INDEX ix_qam_company_form   ON qa_metrics_issue(company_id, form_canonical);
CREATE INDEX ix_qam_created        ON qa_metrics_issue(company_id, created_at);
```

Ixtiyoriy: `qa_form_catalog` (kanonik forma lug'ati, kompaniya bo'yicha kurirovka qilinadigan) — resolver 3-qatlami shu jadvaldan o'qiydi va admin UI orqali tahrirlanadi.

---

## 7. Har bir savol → qanday javob beramiz

| Savol | SQL / agregatsiya | Grafik |
|---|---|---|
| **S1** Sprint/relizda qancha bug | `WHERE is_bug AND resolution IS DISTINCT FROM 'Rejected' GROUP BY sprint_name` | Bar (sprint bo'yicha) + trend chizig'i |
| **S2** Qancha task | `COUNT(*) GROUP BY sprint_name` | KPI kartochka + trend |
| **S3** Task type'lari | `GROUP BY issue_type` | Donut / stacked bar |
| **S4** Qaysi formada ishlayapmiz | `GROUP BY form_canonical ORDER BY count DESC` | Gorizontal bar (top-N forma) |
| **S5** Qaysi formada bug | `WHERE is_bug GROUP BY form_canonical` | Bar / heatmap (forma × sprint) |
| **S6** Qaysi formalar tayyor | `GROUP BY form_canonical, status` (Closed% hisoblab) | Stacked bar (Done/Testing/InProgress/ToDo) |
| **S7** Ko'proq test kerak | Risk skori (8-bo'lim) | Reyting jadvali + "diqqat" ro'yxati |

---

## 8. "Ko'proq test qilish kerak" — risk skori (S7)

Har forma uchun tavsiya etilgan formula (0–100), kompaniya sozlamasida vaznlar o'zgartiriladi:

```
risk(form) =  w1 * bug_density        # shu formadagi bug / jami task
            + w2 * open_bugs          # hali yopilmagan (status ≠ Closed) buglar
            + w3 * in_testing_now     # hozir 'Testing' statusdagi tasklar
            + w4 * churn              # PR o'zgarishlar hajmi (additions+deletions)
            + w5 * recent_activity    # oxirgi sprintdagi o'zgarish
            - w6 * recently_tested    # yaqinda test qilingan bo'lsa kamayadi
```

Boshlang'ich (MVP): `risk = open_bugs*2 + in_testing_now*1.5 + bug_density*10` — churn/AI keyingi bosqichda.

> Bu **QA prioritizatsiyasi** uchun: yuqori skorli formalar "bu relizda diqqat qiling" ro'yxatiga chiqadi.

---

## 9. Bosqichma-bosqich reja

### Bosqich 0 — Qaror (bu hujjat + 11-bo'lim savollari)
Reliz proksisi (sprint yoki sana), forma manbai (resolver yoki `components` to'ldirish), AI ishlatilsinmi.

### Bosqich 1 — MVP (structured savollar, forma'siz)
- `qa_metrics_issue` jadvali + migratsiya.
- Sync job: `JiraClient` + **pagination** + sprint(10020) parse + `fixVersions` maydonini olishga qo'shish (kelajak uchun).
- `qa_metrics_repository.py` + `GET /api/qa-metrics` (`session_scope` bilan).
- Next.js `/app/(app)/metrics/page.tsx`: KPI kartochkalar (S1–S3) + type donut + sprint bar. **Faqat mavjud UI primitivlari (dep'siz).**
- Nav va `product-catalog` ga `metrics` moduli.
- **Natija:** S1, S2, S3 to'liq javob.

### Bosqich 2 — Forma resolver (S4–S6)
- `FormResolver` (3.3): route-regex → PR-path → lug'at. `qa_metrics_issue.form_*` to'ldiriladi.
- Forma bo'yicha bar/heatmap; forma × status stacked bar.
- `qa_form_catalog` + admin tahrir (ixtiyoriy).
- **Natija:** S4, S5, S6.

### Bosqich 3 — Risk skori + AI tozalash (S7)
- Risk formula + "diqqat qiling" ro'yxati.
- PR churn (GitHub) qo'shish.
- Gemini normalizatsiya (resolver 4-qatlam) — kvota gate bilan.
- Agar real grafik kerak bo'lsa `recharts` qo'shiladi.

### Bosqich 4 — Sayqal
- Sprint DEV/BA track filtri, sana oynasi, eksport (CSV), avtomatik davriy sync (job_queue/cron).

---

## 10. Bir qarashda: nima bor, nima qurish kerak

| Komponent | Holat |
|---|---|
| JQL bulk fetch (`search_tasks`, `get_sprint_issues_full`) | ✅ Bor (pagination qo'shish kerak) |
| Sprint (10020) parse | ⚠️ Sozlangan, lekin issue dict'ga parse qilinmaydi → qo'shish |
| fixVersion olish | ❌ Yo'q (baribir Jira'da bo'sh) |
| DB agregatsiya patterni | ✅ `sprint_report_repository` namuna bor |
| Metrik jadval (`qa_metrics_issue`) | ❌ Qurish kerak |
| Form Resolver | ❌ Qurish kerak (PR-path qismi `_extract_features_from_pr_files` da qisman bor) |
| FastAPI `/api/qa-metrics` | ❌ Qurish (`sprint_report_api` shablon) |
| Multi-tenant / auth | ✅ `BaseService`, `session_scope` |
| Next.js sahifa + nav | ❌ Qurish (`monitoring/page.tsx` shablon) |
| Charting | ⚠️ Kutubxona yo'q — dep'siz boshlash, kerak bo'lsa `recharts` |
| `statistics` modul sozlamasi | ✅ Bor (kengaytirish) |

---

## 11. Ochiq qarorlar (foydalanuvchi tanlashi kerak)

1. **Reliz nima?** Jira'da reliz maydoni bo'sh. (a) Sprint = reliz proksisi, yoki (b) sana oynasi (masalan har 2 hafta)? — **Tavsiya: sprint, sana zaxira sifatida.**
2. **Forma manbai:** (a) darhol matn/PR resolver bilan boshlash, yoki (b) jamoa Jira'da `components`/yangi "Form" maydonini to'ldirishni boshlaydimi (uzoq muddatli toza yechim)? — **Tavsiya: (a) bilan boshlash, parallel ravishda (b) ni jamoaga tavsiya qilish.**
3. **AI (Gemini) forma normalizatsiyasi** kerakmi? Kvota/narx bor. — **Tavsiya: Bosqich 3, ixtiyoriy, kesh bilan.**
4. **Qamrov:** faqat DEV loyihasimi, yoki kompaniya `jira_project_keys` dagi barcha loyihalarmi? — **Tavsiya: DEV dan boshlab, keyin kengaytirish.**
5. **Yangilanish:** avtomatik davriy sync (har 15 daq) yoki faqat qo'lda "Refresh" tugmasi? — **Tavsiya: qo'lda + keyin cron.**

---

## 12. Xulosa

- **S1–S3 (bug/task/type)** bugun mavjud maydonlardan **ishonchli** javob beriladi — MVP tez chiqadi.
- **S4–S7 (forma)** — asosiy qiymat, lekin Jira'da tuzilgan maydon yo'q; **matn + PR yo'llaridan derivatsiya** yagona yo'l. Bu modulning "yuragi" va eng ko'p mehnat talab qiladigan qismi.
- Infratuzilma katta qismi (Jira/GitHub client, DB pattern, auth, agregatsiya API namunasi, UI primitivlar, `statistics` modul sloti) **allaqachon mavjud** — noldan qurish shart emas.
- **Reliz uchun `fixVersions` ni ishlatmang** (bo'sh) — sprint proksi.
- Bug uchun **DEV loyihasiga** e'tibor bering (MOB muzlagan).
