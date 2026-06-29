# Testcase Generator Case Documentation (Run-Based Multi-Agent As-Is)

Bu hujjatning maqsadi: hozirgi `Test Case Generator` logikasini koddagi real branchlar bilan hujjatlashtirish.

Muhim chegaralar:
- Bu hujjat `as-is` holatni yozadi.
- Testcase generator PR ishlatmaydi.
- UI, webhook va worker runlari bir xil multi-agent testcase enginega boradi.

## 1) Kirish nuqtalari

### 1.1 Frontend API routes (UI)
Manbalar:
- `/Users/mac/Documents/projects/QA-Assistant/frontend/src/app/api/testcase/runs/route.ts`
- `/Users/mac/Documents/projects/QA-Assistant/frontend/src/app/api/testcase/runs/[runId]/route.ts`

Case-lar:
1. Sessiya yo'q/yaroqsiz -> `401`.
2. Role/module ruxsati yo'q -> `403`.
3. `task_key` bo'sh -> `400`.
4. Valid payload -> backend `/api/testcase/runs` ga yuboriladi.
5. UI run holatini `/api/testcase/runs/{runId}` orqali kuzatadi.

Payload normalize:
- `task_key` -> `trim().toUpperCase()`
- `test_types` default `[]` (backend defaultga tushadi)
- `custom_context` default `""`
- `output_profile` default `ui`

### 1.2 Backend API route
Manba: `/Users/mac/Documents/projects/QA-Assistant/services/api/testcase_api.py`

Case-lar:
1. `load_api_session` session va role tekshiradi.
2. `require_customer_scope` company/user scope aniqlaydi.
3. `normalize_manual_task_key`:
   - `DEV-1234` kabi to'liq key bo'lsa o'zidek qoladi.
   - `1234` kabi raqam bo'lsa faqat `jira_project_keys` settingdan project key olib `DEV-1234` qiladi.
   - `jira_project_keys` bo'lmasa `400` qaytadi.
4. `run_start_preflight` run yaratishdan oldingi local setup gate'ni bajaradi.
5. Valid scope va preflight OK -> `create_testcase_run`.
6. Queue yoqilgan bo'lsa job enqueue qilinadi, aks holda background task `execute_testcase_run`.
7. Kutilmagan backend exception -> `500`, `Testcase run create error: ...`.

### 1.3 Webhook path (Service2)
Manbalar:
- `/Users/mac/Documents/projects/QA-Assistant/services/webhook/jira_webhook_handler.py`
- `/Users/mac/Documents/projects/QA-Assistant/services/webhook/service_runner.py`
- `/Users/mac/Documents/projects/QA-Assistant/services/webhook/testcase_webhook_handler.py`

Service2 ishga tushish yo'llari:
1. JIRA webhook trigger -> `Service1 -> delay -> Service2`.
2. `AI_SKIP` holatida Service1 `skip` bo'lsa ham Service2 ishlashi mumkin.
3. Service1 super-admin tomonidan o'chirilgan bo'lsa, Service2 trigger statusda alohida ishlashi mumkin.
4. Manual endpointlar:
   - `/manual/testcase/{task_key}` -> faqat Service2.
   - `/manual/check/{task_key}` -> Service1 + ixtiyoriy Service2.

## 2) Run-start preflight

Manba: `/Users/mac/Documents/projects/QA-Assistant/core/module_start_preflight.py`

UI testcase runi yaratilishidan oldin:
1. `task_key_format` - `DEV-1234` format.
2. `customer_scope` - company/user scope mavjud.
3. `module_access` - company uchun `testcase_generator` yoqilgan.
4. `api_credentials` - testcase uchun `JIRA + Gemini` kerak; GitHub talab qilinmaydi.
5. `gemini_quota` - faqat global `QA ASSISTANT` Gemini key ishlatilsa, bepul kvota tugamaganini tekshiradi.

Webhook bu start-preflightdan o'tmaydi; uning gate'lari webhook endpoint va Service2 guardda bajariladi.

## 3) Service2 orchestration

Manba: `/Users/mac/Documents/projects/QA-Assistant/services/webhook/service_runner.py`

`webhook_service2_guard` profili:

```python
[
    "service2_db_guard",
]
```

`service2_db_guard` ichidagi skip/block case-lar:
1. Task DB'da yo'q -> skip.
2. `service1_status` `done|skip|error` emas -> skip.
3. `service1_status='error'` va `service2_status!='pending'` -> skip.
4. `service2_status='done'` -> skip.
5. `company_id` yo'q -> skip/error log.
6. `compliance_score < threshold` -> skip.
7. `task_status='returned'` -> skip.

`check_and_generate_testcases()` natijasiga qarab:
1. `success=True` -> `set_service2_done(task_key)`.
2. `success=False`:
   - `ai_timeout` -> `service2_status=blocked`, retry delay bilan.
   - `pr_not_found`, `pr_not_merged`, `tz_too_short` -> return oqimi uriniladi.
   - boshqasi -> `service2_status=error`.

## 4) Testcase webhook handler

Manba: `/Users/mac/Documents/projects/QA-Assistant/services/webhook/testcase_webhook_handler.py`

Pre-check case-lar:
1. `auto_comment_enabled=false` -> `(False, "Auto-comment disabled")`.
2. `new_status` trigger emas -> `(False, "Status ... is not a trigger")`.
3. `company_id` berilgan bo'lsa webhook credential tekshiriladi.
4. Credential xato -> `(False, <xatolik matni>)`.
5. `create_testcase_run + run_testcase_for_webhook` ishlaydi.

JIRA comment yozish case-lari:
1. `use_adf=true` -> ADF document yoziladi.
2. ADF fail bo'lsa simple comment fallback.
3. `use_adf=false` -> simple comment.
4. Yozish fail yoki exception -> `(False, message)`.

## 5) Testcase setup profile

Manbalar:
- `/Users/mac/Documents/projects/QA-Assistant/core/module_preflight.py`
- `/Users/mac/Documents/projects/QA-Assistant/core/setup_checks/profiles.py`
- `/Users/mac/Documents/projects/QA-Assistant/services/generators/testcase_generator.py`

Testcase modul policy:

```python
ModulePreflightPolicy(
    jira_fetch=True,
    min_tz_check=True,
    pr_check=False,
    figma_check=True,
    comment_fetch=True,
    tz_build=True,
)
```

Amaldagi tartib:

```python
[
    "jira_fetch",
    "min_tz_check",
    "figma_check",
    "tz_build",
]
```

Case-lar:
1. `jira_fetch`
   - JIRA API orqali task olinadi.
   - Task topilmasa `success=false`, `"task topilmadi"`.

2. `min_tz_check`
   - Faqat JIRA `description` uzunligi hisoblanadi.
   - `summary`, comment yoki boshqa maydonlar minimal uzunlikka qo'shilmaydi.
   - `description < min_tz_description_chars` bo'lsa `"Servis-2 to'xtatildi"`.

3. `figma_check`
   - Figma faqat `ai_data_section_order` ichida `figma` bo'lsa ishlaydi.
   - Token/ruxsat/link xatosi generatorni yiqitmaydi; warning/fail-safe data qaytadi.

4. `tz_build`
   - `read_comments_enabled=false` bo'lsa comments promptga kirmaydi.
   - `read_comments_enabled=true` bo'lsa `max_comments_to_read` bo'yicha commentlar olinadi.

## 6) Asosiy multi-agent generation oqimi

Manba: `/Users/mac/Documents/projects/QA-Assistant/services/generators/testcase_generator.py`

Case-lar:
1. `test_types` bo'sh bo'lsa -> `['positive', 'negative']`.
2. `testcases_per_requirement` setting 1..3 oralig'iga normalize qilinadi.
3. Figma checker kabi `ai_data_section_order` orqali boshqariladi.
4. Setup profile muvaffaqiyatli o'tsa:
   - Agent1 checker contract reuse qilib requirement ajratadi.
   - Agent2 requirementlar asosida testcase yozadi.
   - Backend validation coverage/count/schema tekshiradi.
   - Missing requirementlar bo'lsa Agent2 repair ishlaydi.
   - Agent3 audit va scenario grouping qiladi.
   - Finalizer dedup, per-requirement limit, `TC-NNN` renumber bajaradi.
5. Agent1 requirement ajrata olmasa -> `success=false`.
6. Agent2/Agent3 exception bo'lsa -> `success=false`, agent error result.

## 7) Parse va validation case-lari

1. JSON topilmasa -> parse bo'sh natija qaytarishi mumkin.
2. JSON aliaslar qo'llab-quvvatlanadi: `test_cases`, `testCases`, `tests`, `test_case_list`.
3. JSON decode xatoda local repair uriniladi.
4. Har testcase item qisman bo'lsa default maydonlar bilan `TestCase` obyekt qilinadi.
5. Validation:
   - har requirement kamida 1 testcase bilan qoplanishi kerak.
   - har requirement ko'pi bilan `testcases_per_requirement` testcase oladi.
   - ortiqcha testcase deterministik trim qilinadi.

## 8) Error classification va reason code mapping

Manba: `/Users/mac/Documents/projects/QA-Assistant/services/webhook/error_handler.py`

Mapping:
1. `pr_not_found` -> `WARN_NO_PR`
2. `pr_not_merged` -> `WARN_PR_NOT_MERGED`
3. `tz_too_short` -> `WARN_MIN_TZ`
4. `ai_timeout` -> `WARN_AI_TIMEOUT`
5. boshqa -> `ERR_UNKNOWN`

Service2 PR ishlatmasa ham mapping umumiy webhook error-handler bilan bir xil qoladi.

## 9) Sozlamalar behaviorga ta'siri

Asosiy `testcase` settinglar:
1. `default_test_types`
2. `testcases_per_requirement`
3. `ai_max_output_tokens`
4. `ai_data_section_order`
5. `read_comments_enabled`
6. `max_comments_to_read`
7. `auto_comment_enabled` (webhook trigger uchun)
8. `auto_comment_trigger_status` va aliaslari
9. `use_adf_format`
10. agent model/fallback settinglari

Validation:
1. `testcases_per_requirement` 1..3 oralig'iga clamp qilinadi.
2. `ai_data_section_order` faqat ruxsat etilgan kalitlardan bo'lishi kerak.
3. `ai_data_section_order`da `tz` bo'lishi shart.

## 10) "Testcase moduliga task berilganda" qisqa indeks

A. Modulga kirmaslik/skip holatlari:
1. UI/API auth yoki module access yo'q.
2. Webhookda `auto_comment_enabled=false`.
3. Trigger status emas.
4. Service2 guard: service1 tayyor emas, service2 done, score past, task returned.

B. Moduldagi xato holatlar:
1. JIRA task topilmadi.
2. TZ description minimaldan qisqa.
3. Figma token/ruxsat xatosi warning sifatida qoladi, blocker emas.
4. Gemini xatosi/timeout.
5. Agent1 requirement topolmadi.
6. JSON parse yoki validation natijasida yetarli testcase chiqmasa.
7. JIRA comment yozish muvaffaqiyatsiz.

C. Moduldagi success holatlar:
1. JIRA description asosida testcase generation.
2. Figma bor bo'lsa Figma signal bilan generation.
3. Custom context bor bo'lsa promptga qo'shilgan generation.
4. Commentlar yoqilgan bo'lsa comment context bilan generation.

## 11) O'zgarmas invariants

1. Testcase generator PR ishlatmaydi.
2. Min TZ faqat JIRA `description` bo'yicha hisoblanadi.
3. UI va webhook Service2 bir xil testcase run enginega boradi.
4. Service2 DB status transitionlari `service_runner`da boshqariladi.
5. Generatorning o'zi webhook task DB state machine'ni boshqarmaydi.
