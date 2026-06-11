# Checker UI/TZ Specification

Bu hujjat `TZ-PR Checker` modulining hozirgi ishlashini qisqacha tahlil qiladi va keyingi product-ready UI uchun aniq TZ beradi.

Asosiy requirement hujjati:
- [docs/CHECKER_QA_REQUIREMENTS.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/docs/CHECKER_QA_REQUIREMENTS.md)
- Checker bo'yicha keyingi product qarorlar avvalo shu QA requirement baseline'ga mos bo'lishi kerak.

Muhim chegaralar:
- Bu hujjat `as-is` va `to-be` ni ajratadi.
- Design uchun kerakli ekran, blok, state va data contractlarni belgilaydi.
- Keyingi bosqichda frontend dizayn tayyor bo'lgach, backend ulash ishlari shu hujjatga tayanadi.

## 1. Maqsad

Checker sahifasi foydalanuvchiga 3 ta savolga tez javob berishi kerak:

1. Bu task kimniki, qaysi task va nima o'zgargan?
2. TZ, kod va Figma bir-biriga qanchalik mos?
3. Nima bajarilgan, nima qisman, nima umuman bajarilmagan va qayerda risk bor?

Design natijasi oddiy `score screen` emas, balki `task intelligence cockpit` bo'lishi kerak.

## 2. Hozirgi checker qanday ishlaydi (`as-is`)

Asosiy manbalar:
- `services/checkers/tz_pr_checker.py`
- `services/api/tzpr_api.py`
- `services/webhook/service_runner.py`
- `frontend/src/components/tzpr-checker.tsx`
- `docs/TZPR_CHECKER_CASES.md`

### 2.1 Kirish nuqtalari

Checker 2 yo'l bilan ishlaydi:

1. Manual UI:
   - foydalanuvchi `task_key` yuboradi
   - frontend `/api/tzpr/runs` ga run yaratish so'rovi yuboradi
   - frontend `/api/tzpr/runs/{runId}` orqali run holatini kuzatadi
   - backend run-based multi-agent checker oqimini ishga tushiradi

2. Webhook:
   - JIRA status trigger bo'lganda `Service1` sifatida ishga tushadi
   - natijaga qarab JIRA comment yozadi
   - kerak bo'lsa taskni `return_status` ga qaytaradi
   - `service1_status`, `compliance_score`, `return_reason` kabi qiymatlarni DB ga yozadi

### 2.2 Tahlil pipeline

Checker ichki oqimi quyidagicha:

1. Session va module access tekshiriladi
2. JIRA dan task details olinadi
3. PR topiladi va `merged` ekanligi tekshiriladi
4. TZ minimal uzunligi tekshiriladi
5. TZ + human comments formatlanadi
6. Developer objection/recheck konteksti ajratiladi
7. Figma linklar topiladi va summary olinadi
8. Agent1 uchun sanitized TZ/comments/Figma input quriladi
9. Agent1 requirement inventory qaytaradi
10. Agent2 har requirementni PR/code diffga nisbatan tekshiradi
11. Agent2 alohida extra-code scan qaytaradi
12. Agent3 human-readable summary/risk/recommendation qaytaradi
13. Checker verdict, score, matrix va statuslarni deterministic hisoblaydi
14. Task metadata DB ga yoziladi (`assignee`, `task_type`, `feature_name`, `technology_stack`)

### 2.3 Hozir checker nimalarni qaytara oladi

Backend response ichida hozir quyidagi foydali data bor:

- `task_key`
- `task_summary`
- `tz_content`
- `compliance_score`
- `pr_count`
- `files_changed`
- `total_additions`
- `total_deletions`
- `pr_details`
- `ai_analysis`
- `warnings`
- `figma_data`
- `comment_analysis`
- `dev_objections`
- `analysis_sections`
- `analysis_overview`
- `effective_settings`
- `status_banner`

### 2.4 Hozirgi UI nimalarni ko'rsatadi

Hozirgi checker UI quyidagilarni beradi:

1. Summary metric kartalar:
   - compliance
   - verdict
   - files
   - prompt size

2. Overview blok:
   - verdict
   - summary lines
   - figma limited/ready badge

3. Requirement Map:
   - `completed`
   - `failed`
   - `manual_review`
   - `issues`
   - `figma`

4. Evidence:
   - TZ content
   - Figma summary
   - PR details va patch preview
   - Agent1 requirement inventory
   - Agent2 verification evidence

5. Agent timeline/debug:
   - Agent1/Agent2/Agent3 holatlari
   - parse/validation warnings va technical failure metadata

### 2.5 Hozirgi gaplar va UX bo'shliqlar

Hozirgi sahifa texnik jihatdan foydali, lekin product nuqtayi nazaridan hali yetarli emas:

1. `Task identity` yetarli emas:
   - assignee
   - reporter
   - issue type
   - priority
   - story points
   - labels/components
   - current jira status
   - bu maydonlar hozir natijada alohida ko'rinmaydi

2. `Requirement matrix` haqiqiy jadval emas:
   - AI sectionlar bor
   - lekin har bir talab uchun `status + evidence + figma match + code files` bir joyda yo'q

3. `Figma moslik` hali yuqori signal blok emas:
   - summary text bor
   - lekin file/frame/node kesimida verdict yo'q

4. `Workflow / run lifecycle` ko'rinmaydi:
   - webhookda `service1_status`, `return_reason`, `auto_return`, `blocked` kabi semantikalar bor
   - manual UI bunga hali ulanmagan

5. `Kim bajargan / qaysi task / qaysi modul` kabi biznes ma'lumotlar bitta qarashda ko'rinmaydi

6. `Open issues` va `code changes` mavjud, lekin qaror qabul qilish uchun kerakli ustuvorlik tartibida yig'ilmagan

## 3. Yangi UI maqsadi (`to-be`)

Yangi sahifa quyidagi rolda ishlashi kerak:

1. QA uchun:
   - taskni qaytarish yoki o'tkazish qarorini tez chiqarish

2. Team lead uchun:
   - bajarilgan va bajarilmagan talablarni audit qilish

3. Developer uchun:
   - qaysi talab qaerda yiqilganini ko'rish

4. Designer/PM uchun:
   - Figma bilan nomosliklarni ko'rish

Sahifa hissi:
- audit panel
- yuqori signal
- jiddiy QA cockpit
- keraksiz dekor emas, ma'lumot ustuvor

## 4. Claude Design uchun umumiy brief

Vizual yo'nalish:

- `Quality cockpit` uslubi
- kuchli hierarchy
- bir qarashda score/verdict/task owner ko'rinsin
- ranglar ma'noli ishlasin:
  - yashil = bajarilgan
  - sariq = qisman / ehtiyot bo'lish kerak
  - qizil = bajarilmagan / blocker
  - ko'k = info / figma / diagnostics
  - kulrang = unavailable / access yo'q

Layout prinsiplari:

1. Desktop:
   - yuqorida summary strip
   - pastda chapda asosiy tahlil
   - o'ngda task info va run info sidebar

2. Mobile:
   - summary kartalar stack
   - keyin task info
   - keyin tablar / accordion sectionlar

3. `Raw AI` va juda texnik bloklar primary emas, secondary yoki advanced holatda turishi kerak

## 5. Tavsiya etilgan ekran tuzilmasi

### 5.1 Top header

Majburiy elementlar:

- `Task key`
- task summary
- overall verdict badge
- compliance ring yoki katta foiz
- assignee avatar/name
- current JIRA status
- last run type: `Manual` yoki `Webhook`
- action buttonlar uchun joy:
  - `Tekshirish`
  - `JIRA ni ochish`
  - `GitHub PR ni ochish`
  - `Figma ni ochish` (agar bor bo'lsa)

### 5.2 Summary strip

4-6 ta high signal karta:

1. `Moslik bali`
2. `Verdict`
3. `Bajarilgan talablar soni`
4. `Qisman / bajarilmagan talablar soni`
5. `Risklar soni`
6. `Figma holati`

### 5.3 Main tabs

Yangi UI uchun tavsiya etilgan tablar:

1. `Overview`
2. `Requirement Matrix`
3. `Figma Match`
4. `Code Changes`
5. `Run Diagnostics`
6. `Raw AI` yoki `Advanced`

## 6. Har bir tab uchun aniq TZ

### 6.1 Overview

Maqsad:
- 10 soniyada umumiy holatni tushuntirish

Majburiy bloklar:

1. `Executive summary`
   - 2-5 ta qisqa xulosa
   - verdict reason
   - top 3 muammo

2. `Task info`
   - task key
   - summary
   - assignee
   - reporter
   - issue type
   - priority
   - story points
   - created date
   - resolved date
   - labels
   - components

3. `Run info`
   - analyze source: manual/webhook
   - smart patch on/off
   - comments on/off
   - comments count
   - filtered AI comments
   - prompt size
   - files analyzed
   - retry count

4. `Decision card`
   - `Ready`
   - `Partial`
   - `Need Work`
   - `Blocked`
   holatlaridan biri

5. `Open signals`
   - bajarilmagan talablar
   - qisman bajarilgan talablar
   - risklar
   - figma access
   - recheck objections

### 6.2 Requirement Matrix

Bu checkerning markaziy ekrani bo'lishi kerak.

Har bir requirement row uchun quyidagilar bo'lishi kerak:

- requirement nomi yoki qisqa matni
- status:
  - `Bajarilgan`
  - `Qisman bajarilgan`
  - `Bajarilmagan`
- score contribution yoki weight (ixtiyoriy, lekin foydali)
- AI izohi
- evidence
- bog'liq code file(lar)
- figma moslik statusi
- risk badge

Tavsiya etilgan ustunlar:

| Ustun | Tavsif |
| --- | --- |
| `Requirement` | TZ yoki commentdan olingan talab |
| `Status` | Completed / Partial / Missing |
| `Evidence` | AI qaytargan asos |
| `Code` | PR fayllari yoki snippet link |
| `Figma` | Matched / Partial / Not matched / Unavailable |
| `Notes` | Qo'shimcha gap yoki risk |

Muhim:
- bu blok oddiy paragraphlar emas, haqiqiy matrix ko'rinishida bo'lishi kerak
- status bo'yicha filter kerak
- `faqat bajarilmaganlar` va `faqat qismanlar` quick filter kerak

### 6.3 Figma Match

Maqsad:
- dizayn va implementatsiya orasidagi moslikni aniq ko'rsatish

Majburiy bloklar:

1. `Figma access summary`
   - mavjud
   - cheklangan
   - unavailable

2. Har bir Figma file/frame uchun card:
   - file name
   - source: `description` yoki `comment`
   - node id bo'lsa ko'rsatish
   - figma verdict
   - summary text
   - `matched points`
   - `mismatch points`

3. Figma bo'lmasa yoki token ishlamasa:
   - aniq bo'sh holat
   - bu task bo'yicha figma verdict chiqarib bo'lmasligi albatta ko'rsatilsin

Figma verdict statuslari:

- `Mos`
- `Qisman mos`
- `Mos emas`
- `Tekshirib bo'lmadi`

### 6.4 Code Changes

Maqsad:
- qaysi PR va qaysi fayllar asosida xulosa chiqqanini ko'rsatish

Majburiy bloklar:

1. `PR summary`
   - PR count
   - files changed
   - additions
   - deletions

2. `PR list`
   - PR title
   - PR number
   - repo/source
   - state
   - additions/deletions
   - open PR link

3. `File list`
   - filename
   - status
   - +/-
   - blob link
   - preview toggle

4. `Patch preview`
   - smart context bo'lsa uni ustun ko'rsatish
   - aks holda oddiy patch

Qo'shimcha foydali signal:
- qaysi file qaysi requirementga bog'langanini ko'rsatish uchun badge/link placeholder bo'lsin

### 6.5 Run Diagnostics

Maqsad:
- nima uchun shu verdict chiqqanini texnik darajada ko'rsatish

Majburiy bloklar:

1. `Analysis configuration`
   - output profile
   - visible sections
   - ai data order
   - effective smart patch
   - comments read settings

2. `Comment diagnostics`
   - total human comments
   - filtered AI comments
   - contradictory comments count
   - developer objections count

3. `Workflow status`
   - service1_status
   - service2_status
   - task_status
   - return_reason
   - auto_return_enabled
   - threshold

4. `Status banner`
   - full blocked
   - policy violation
   - PR not found
   - PR not merged
   - TZ too short
   - AI timeout

5. `Warnings`
   - checker warnings alohida list ko'rinishida

### 6.6 Raw AI / Advanced

Bu bo'lim primary audience uchun emas.

Ko'rsatilsin:
- raw ai analysis
- full TZ content
- contradiction summary

Tavsiya:
- default yopiq
- admin va power user uchun qulay

## 7. Global sidebar yoki right rail

O'ng sidebar uchun tavsiya etilgan bloklar:

1. `Task owner`
   - assignee
   - reporter

2. `Task meta`
   - type
   - priority
   - story points
   - labels
   - components

3. `Delivery meta`
   - feature_name
   - technology_stack
   - PR count
   - files changed

4. `Workflow`
   - manual/webhook
   - returned/not returned
   - blocked/not blocked

## 8. Holatlar va status semantikasi

### 8.1 Overall verdict

| Verdict | Ma'nosi |
| --- | --- |
| `Ready` | kritik nomoslik yo'q, o'tkazishga yaqin |
| `Partial` | qisman muammo bor, review kerak |
| `Need Work` | bajarilmagan talablar bor |
| `Blocked` | texnik sabab bilan ishonchli tahlil bo'lmadi |
| `Unknown` | ma'lumot yetarli emas |

### 8.2 Requirement status

| Status | Ma'nosi |
| --- | --- |
| `Bajarilgan` | talab to'liq bajarilgan |
| `Qisman bajarilgan` | talabning bir qismi bajarilgan |
| `Bajarilmagan` | talab yo'q yoki zid |
| `Tekshirib bo'lmadi` | data yetarli emas |

### 8.3 Figma status

| Status | Ma'nosi |
| --- | --- |
| `Mos` | dizayn va implementatsiya mos |
| `Qisman mos` | ayrim mismatch bor |
| `Mos emas` | sezilarli nomoslik bor |
| `Unavailable` | figma access yo'q yoki data olinmadi |

## 9. Empty / error / blocked state lar

Claude Design uchun bu state'lar alohida chizilishi kerak:

1. `Initial empty state`
   - task key kiriting
   - checker nimalarni tekshirishi haqida qisqa izoh

2. `Loading state`
   - skeletonlar
   - ayniqsa summary, matrix, sidebar uchun

3. `PR topilmadi`
   - qizil emas, warning holatda
   - nima qilish kerak ko'rsatilsin

4. `PR merged emas`
   - blocker holat

5. `TZ juda qisqa`
   - blocker holat

6. `FULL analysis blocked`
   - overload yoki technical failure
   - manual tekshirish tavsiya bloki

7. `Figma unavailable`
   - Figma tab yiqilmasligi kerak
   - lekin verdict cheklanganini aniq ko'rsatishi kerak

## 10. Backendga ulash uchun kerakli data contract

### 10.1 Hozir mavjud data

Hozirgi API bilan allaqachon chizsa bo'ladigan bloklar:

- overall score/verdict
- summary
- completed/partial/failed/issues/figma sectionlar
- PR summary va patchlar
- figma summary text
- comment analysis
- warnings
- raw ai

### 10.2 Yangi kerak bo'ladigan data

Yangi UI ni to'liq ishlatish uchun backend response kengayishi kerak.

Tavsiya etilgan yangi obyektlar:

### `task_info`

```json
{
  "key": "DEV-1234",
  "summary": "Task title",
  "issue_type": "DEV-BUG",
  "status": "READY TO TEST",
  "assignee": "Ali Valiyev",
  "reporter": "QA User",
  "priority": "High",
  "story_points": 3,
  "created_at": "2026-05-10",
  "resolved_at": null,
  "labels": ["billing", "ui"],
  "components": ["Checkout"]
}
```

### `run_info`

```json
{
  "source": "manual",
  "requested_output_profile": "ui",
  "smart_patch": true,
  "comments_enabled": true,
  "max_comments_to_read": 0,
  "files_analyzed": 12,
  "total_files_changed": 12,
  "prompt_size_chars": 28000,
  "ai_retry_count": 0,
  "figma_access": "limited"
}
```

### `workflow_info`

Bu ayniqsa webhook bilan ulaganda kerak bo'ladi:

```json
{
  "task_status": "returned",
  "service1_status": "done",
  "service2_status": "pending",
  "return_reason": "WARN_LOW_SCORE",
  "auto_return_enabled": true,
  "return_threshold": 60,
  "trigger_status": "READY TO TEST",
  "return_status": "NEED CLARIFICATION/RETURN TEST"
}
```

### `requirements`

Bu eng muhim yangi strukturadir. Hozir `analysis_sections` freeform. Keyingi bosqichda UI uchun requirement-level array kerak:

```json
[
  {
    "id": "req-1",
    "title": "Import tugmasi ishlashi kerak",
    "source": "tz",
    "status": "completed",
    "evidence_text": "AI code change ichida import handler borligini aniqladi",
    "code_files": ["src/modules/import/page.tsx"],
    "figma_status": "matched",
    "risk_level": "low",
    "notes": ""
  }
]
```

### `figma_checks`

```json
[
  {
    "file_key": "abc123",
    "name": "Checkout Flow",
    "url": "https://figma.com/...",
    "source": "description",
    "node_id": "1337:16",
    "access_status": "ok",
    "verdict": "partial",
    "summary": "Button text mos, lekin 2 ta field yo'q",
    "matches": ["Primary CTA text mos"],
    "mismatches": ["Secondary field ko'rinmadi"]
  }
]
```

### `risk_items`

```json
[
  {
    "id": "risk-1",
    "severity": "medium",
    "category": "edge_case",
    "title": "Validation empty state ushlanmagan",
    "description": "AI form validation branch ko'rinmaganini aytdi",
    "related_files": ["src/forms/create.tsx"],
    "related_requirement_ids": ["req-3"]
  }
]
```

### 10.3 Tavsiya etilgan backend strategiya

Backend ulashda 2 bosqich tavsiya etiladi:

1. `Phase 1`
   - mavjud response bilan yangi layoutni chiqarish
   - `task_info`, `run_info`, `workflow_info` ni qo'shish

2. `Phase 2`
   - AI yoki parser orqali `requirements`, `figma_checks`, `risk_items` kabi haqiqiy structured entity'larni qo'shish

## 11. Interaction va usability talablari

Majburiy UX talablari:

1. Task key copy qilish oson bo'lsin
2. JIRA / GitHub / Figma linklar bir clickda ochilsin
3. `Bajarilmaganlar` uchun tez filter bo'lsin
4. `Figma only`, `Risk only`, `Code only` ko'rinishlari bo'lsin
5. Long textlar default compact, lekin expand qilinadigan bo'lsin
6. Code preview monospace va horizontal scroll bilan ishlasin
7. Mobile'da matrix kartochka ko'rinishiga tushsin

## 12. Acceptance criteria

Yangi design quyidagi savollarga javob bersa, u muvaffaqiyatli hisoblanadi:

1. Foydalanuvchi 10 soniyada `qaysi task`, `kim bajargan`, `score`, `verdict` ni ko'ra oladimi?
2. QA 30 soniyada `bajarilgan / qisman / bajarilmagan` talablarni ajrata oladimi?
3. Designer `Figma moslik`ni alohida ko'ra oladimi?
4. Developer `qaysi fayl` sababli risk chiqqanini topa oladimi?
5. Tech lead `manual problem`mi yoki `technical blocked` holatmi ajrata oladimi?
6. Sahifa Figma yoki PR ma'lumoti bo'lmaganda ham yiqilmaydimi?

## 13. Qisqa xulosa

Checkerning hozirgi motori kuchli: JIRA, GitHub, comments, Figma va AI ni bitta pipeline ga yig'adi. Keyingi katta qadam bu motordan product-level `QA decision cockpit` yasash.

Design shu prinsiplarga tayansin:

- task identity birinchi qatorda
- score o'zi yetarli emas, requirement matrix markazda bo'lsin
- figma moslik alohida semantik blok bo'lsin
- risk va code evidence qaror chiqarishga xizmat qilsin
- workflow/blocked state'lar yashirinmasin
