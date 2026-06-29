# TZPR Checker Case Documentation (Run-Based Multi-Agent As-Is)

Bu hujjatning maqsadi: hozirgi `TZ-PR Checker` oqimini koddagi real branchlar bilan hujjatlashtirish.

Muhim chegaralar:
- Bu hujjat `as-is` holatni yozadi.
- Source-of-truth: run-based multi-agent executor va markaziy setup checks.
- UI, webhook va worker checker runlari bir xil multi-agent executorga boradi.

## 1) Kirish nuqtalari

### 1.1 Frontend API routes (UI)
Manbalar:
- `/Users/mac/Documents/projects/QA-Assistant/frontend/src/app/api/tzpr/runs/route.ts`
- `/Users/mac/Documents/projects/QA-Assistant/frontend/src/app/api/tzpr/runs/[runId]/route.ts`

Case-lar:
1. Sessiya yo'q yoki muddati tugagan -> `401`.
2. Role/module ruxsat yo'q -> `403`.
3. `task_key` bo'sh -> `400`.
4. Valid payload -> backend `/api/tzpr/runs` ga yuboriladi.
5. UI run holatini `/api/tzpr/runs/{runId}` orqali kuzatadi.

Payload normalize:
- `task_key` -> `trim().toUpperCase()`
- `show_full_diff` default `true`
- `use_smart_patch` default `null`
- `max_files` default `null`

### 1.2 Backend API route
Manba: `/Users/mac/Documents/projects/QA-Assistant/services/api/tzpr_api.py`

Case-lar:
1. `load_api_session` session va role tekshiradi.
2. `require_customer_scope` company/user scope aniqlaydi.
3. `normalize_manual_task_key`:
   - `DEV-1234` kabi to'liq key bo'lsa o'zidek qoladi.
   - `1234` kabi raqam bo'lsa faqat `jira_project_keys` settingdan project key olib `DEV-1234` qiladi.
   - `jira_project_keys` bo'lmasa `400` qaytadi.
4. `run_start_preflight` run yaratishdan oldingi local setup gate'ni bajaradi.
5. Valid scope va preflight OK -> `create_multi_agent_run`.
6. Queue yoqilgan bo'lsa job enqueue qilinadi, aks holda background task `execute_multi_agent_run`.
7. Kutilmagan backend exception -> `500`, `TZ-PR run create error: ...`.

### 1.3 Webhook path (Service1)
Manbalar:
- `/Users/mac/Documents/projects/QA-Assistant/services/webhook/jira_webhook_handler.py`
- `/Users/mac/Documents/projects/QA-Assistant/services/webhook/service_runner.py`

Webhook checkerga task berishdan oldingi case-lar:
1. Event `jira:issue_updated` emas -> ignored.
2. `task_key` yo'q -> error.
3. Status o'zgarmagan -> ignored.
4. Company resolve bo'lmasa -> ignored.
5. Webhook secret noto'g'ri -> `401`.
6. Subscription inactive -> ignored.
7. `webhook` moduli o'chirilgan -> ignored.
8. Status trigger emas -> ignored.
9. `issue_type` allowed listda emas -> ignored.
10. `assignee` excluded listda -> ignored.
11. Dublikat/progressing/completed holat -> ignored.
12. `AI_SKIP` topilsa -> Service1 skip, Service2 ishlashi mumkin.
13. Yuqoridagilardan o'tsa -> checker queue/background orqali ishga tushadi.

## 2) Run-start preflight

Manba: `/Users/mac/Documents/projects/QA-Assistant/core/module_start_preflight.py`

UI checker runi yaratilishidan oldin:
1. `task_key_format` - `DEV-1234` format.
2. `customer_scope` - company/user scope mavjud.
3. `module_access` - company uchun `tz_pr_checker` yoqilgan.
4. `api_credentials` - checker uchun `JIRA + GitHub + Gemini` kerak.
5. `gemini_quota` - faqat global `QA ASSISTANT` Gemini key ishlatilsa, bepul kvota tugamaganini tekshiradi.

Webhook bu start-preflightdan o'tmaydi; uning company, secret, subscription va module gate'lari webhook endpointda bajariladi.

## 3) Checker setup profile

Manba:
- `/Users/mac/Documents/projects/QA-Assistant/core/setup_checks/profiles.py`
- `/Users/mac/Documents/projects/QA-Assistant/core/setup_checks/checks.py`
- `/Users/mac/Documents/projects/QA-Assistant/services/checkers/tzpr_orchestrator.py`

`checker_engine` tartibi:

```python
[
    "jira_fetch",
    "min_tz_check",
    "pr_check",
    "tz_build",
    "figma_check",
]
```

Case-lar:
1. `jira_fetch`
   - Webhook snapshotda task detail bo'lsa shu ishlatiladi.
   - Aks holda JIRA API orqali task olinadi.
   - Task topilmasa run blocked/error result qaytaradi.

2. `min_tz_check`
   - Faqat JIRA `description` uzunligi hisoblanadi.
   - `summary`, comment yoki boshqa maydonlar minimal uzunlikka qo'shilmaydi.
   - `description < min_tz_description_chars` bo'lsa checker to'xtaydi.

3. `pr_check`
   - `PRHelper.get_pr_full_info` orqali PR qidiriladi.
   - JIRA PR URL yoki GitHub search ishlatilishi mumkin.
   - PR topilmasa checker blocked/error result qaytaradi.
   - PR merged emas holati `PRNotMergedError` sifatida alohida qaytariladi.

4. `tz_build`
   - `read_comments_enabled=false` bo'lsa comments promptga kirmaydi.
   - `read_comments_enabled=true` bo'lsa `max_comments_to_read` bo'yicha commentlar olinadi.
   - Oldingi AI commentlar promptdan chiqarilishi mumkin.
   - `comment_analysis` Agent1ga xom holatda berilmaydi; keyingi qatlamlar uchun contextda qoladi.

5. `figma_check`
   - Figma faqat settingsdagi `ai_data_section_order` ichida `figma` bo'lsa ishlaydi.
   - Token/ruxsat/link xatosi checkerni yiqitmaydi; warning/fail-safe data qaytadi.

## 4) Multi-agent checker oqimi

Manba: `/Users/mac/Documents/projects/QA-Assistant/services/checkers/tzpr_orchestrator.py`

Case-lar:
1. `show_full_diff=false` yoki `max_files` berilgan bo'lsa:
   - multi-agent checker bloklanadi.
   - Hozir checker faqat full diff rejimida ishlaydi.
2. `use_smart_patch is None` bo'lsa:
   - `default_use_smart_patch` setting ishlatiladi.
3. Setup profile muvaffaqiyatli o'tsa:
   - Agent1 sanitized input oladi.
   - Agent1b requirement merge qiladi.
   - Agent2 PR/code diffga nisbatan verifier sifatida ishlaydi.
   - Agent3 arbiter/final verdict beradi.
4. Agent1 commentsni xom holatda olmaydi.
5. Agent3 uchun developer commentlari `CommentSeparator` orqali ajratiladi.

## 5) Recheck case-lari

Manba: `core/constants.py`

Case-lar:
1. DB `return_reason in RECHECK_REASONS` bo'lsa `is_recheck=true`.
2. Hozir `RECHECK_REASONS = {WARN_LOW_SCORE}`.
3. Faqat shu holatda developer objectionlar reanalysis contextga qo'shiladi.
4. `WARN_MIN_TZ`, `WARN_NO_PR`, `WARN_PR_NOT_MERGED`, `WARN_AI_TIMEOUT` yangi run sifatida ishlaydi.

## 6) Webhook Service1 natijani qanday talqin qiladi

Manba: `/Users/mac/Documents/projects/QA-Assistant/services/webhook/service_runner.py`

Runner oldi case-lar:
1. `service1_status == done` -> skip.
2. `company_id` yo'q -> skip/error log.
3. Company webhook settings va credentials olinadi.
4. `create_multi_agent_run + run_multi_agent_for_webhook` ishlaydi.

`result.success=false` bo'lsa:
1. `ai_timeout` -> `service1_status=blocked`, retry kutadi, warning comment yozadi.
2. `pr_not_found`, `pr_not_merged`, `tz_too_short`:
   - error/warning comment yozadi.
   - taskni `return_status`ga qaytarishga urinadi.
   - DB return reason yoziladi.
3. Boshqa xato -> `service1_status=error`, comment yozadi.

`result.success=true` bo'lsa:
1. Success comment yoziladi.
2. DB `service1_status=done`, `compliance_score` saqlanadi.
3. `auto_return_enabled=true` va `score < threshold` bo'lsa:
   - task return statusga o'tkaziladi.
   - DB `task_status=returned`.
   - `return_reason = WARN_LOW_SCORE`.

## 7) Error classification map

Manba: `/Users/mac/Documents/projects/QA-Assistant/services/webhook/error_handler.py`

String -> class:
1. `pr topilmadi/no pr found/...` -> `pr_not_found` -> `WARN_NO_PR`
2. `merged emas/not merged/...` -> `pr_not_merged` -> `WARN_PR_NOT_MERGED`
3. `tz yetarli emas/...` -> `tz_too_short` -> `WARN_MIN_TZ`
4. `timeout/429/rate limit/overloaded/...` -> `ai_timeout` -> `WARN_AI_TIMEOUT`
5. qolgani -> `unknown` -> `ERR_UNKNOWN`

## 8) Sozlamalar checker behavioriga qanday ta'sir qiladi

Asosiy settinglar:
- `read_comments_enabled`
- `max_comments_to_read`
- `min_tz_description_chars`
- `default_use_smart_patch`
- `ai_data_section_order`
- `visible_sections`
- `dev_comments_max`
- `ai_max_output_tokens`

Validation case-lari:
1. `return_threshold` 0..100 bo'lmasa -> `ValueError`.
2. `max_skip_check_comments < 1` -> `ValueError`.
3. `ai_data_section_order`da invalid qiymat bo'lsa -> `ValueError`.
4. Checker uchun `tz` va `code` data sectionlari majburiy.

## 9) "Checkerga task berilganda" qisqa indeks

A. Checkerga umuman kirmaslik case-lari:
1. UI auth/scope/module access xato.
2. Webhook event/status/company/secret/subscription/module gate'dan o'tmadi.
3. AI_SKIP topildi.
4. Dublikat/progressing holat.

B. Checker ichidagi error case-lar:
1. Full diff policy input invalid.
2. Credential/scope xato.
3. JIRA issue topilmadi/auth xato.
4. TZ description minimumdan qisqa.
5. PR topilmadi.
6. PR merged emas.
7. AI texnik xato.
8. AI overload/partial full analysis blocked.

C. Checker ichidagi success case-lar:
1. Figma yo'q, lekin TZ+code bo'yicha tahlil.
2. Figma bor va usable, to'liq tahlil.
3. Recheck mode (`WARN_LOW_SCORE`) bilan objection inobatga olingan tahlil.

## 10) O'zgarmas invariants

1. UI va webhook Service1 bir xil `checker_engine` setup profilidan foydalanadi.
2. Min TZ faqat JIRA `description` bo'yicha hisoblanadi.
3. `min_tz_check` PR tekshiruvidan oldin ishlaydi.
4. Checker FULL-only siyosatini ushlab turadi.
5. Figma fail-safe: Figma xatosi checkerni yiqitmaydi.
6. Webhookda faqat `WARN_LOW_SCORE` recheck contextini yoqadi.
