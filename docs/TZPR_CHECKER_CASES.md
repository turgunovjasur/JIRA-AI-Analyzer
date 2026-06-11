# TZPR Checker Case Documentation (Run-Based Multi-Agent As-Is)

Bu hujjatning maqsadi: mavjud checker logikasini 1:1 hujjatlashtirish.

Muhim chegaralar:
- Bu hujjat `as-is` holatni yozadi.
- Yangi dizayn taklif qilmaydi.
- Mavjud koddagi branchlar, xato case'lar va chiqish natijalarini qayd etadi.

## 1) Kirish nuqtalari

### 1.1 Frontend API routes (UI)
Manbalar:
- `/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/tzpr/runs/route.ts`
- `/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/tzpr/runs/[runId]/route.ts`

Case-lar:
1. Sessiya yo'q yoki muddati tugagan -> `401`, `{ success:false, error:"Sessiya topilmadi..." }`.
2. Role/module ruxsat yo'q -> `403`, `{ success:false, error:"TZ-PR Checker uchun ruxsat yo'q." }`.
3. `task_key` bo'sh -> `400`, `{ success:false, error:"Task key majburiy." }`.
4. Valid payload -> backend `/api/tzpr/runs` ga yuboradi va run yaratadi.
5. UI run holatini `/api/tzpr/runs/{runId}` orqali kuzatadi.

Payload normalize:
- `task_key` -> `trim().toUpperCase()`
- `max_files` default `null`
- `show_full_diff` default `true`
- `use_smart_patch` default `null`

### 1.2 Backend API route (run-based checker call)
Manba: `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/tzpr_api.py`

Case-lar:
1. Sessiya/scope ruxsati yo'q -> HTTPException (auth layer).
2. Valid scope -> run record yaratiladi va multi-agent checker executor ishga tushadi.
3. Kutilmagan backend exception -> `500`, `TZ-PR run error: ...`.

### 1.3 Webhook path (Service1)
Manbalar:
- `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/jira_webhook_handler.py`
- `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/service_runner.py`

Webhook checkerga task berishdan oldingi case-lar:
1. Event `jira:issue_updated` emas -> ignored.
2. `task_key` yo'q -> error.
3. Company resolve bo'lmasa -> ignored.
4. Status trigger emas -> ignored.
5. `issue_type` allowed listda emas -> ignored.
6. `assignee` excluded listda -> ignored.
7. Dublikat/progressing/completed holat -> ignored.
8. `AI_SKIP` topilsa -> Service1 skip, Service2 ishlashi mumkin.
9. Yuqoridagilardan o'tsa -> checker navbatga qo'yiladi (`check_tz_pr_and_comment` -> `analyze_task`).

## 2) Checker asosiy oqimi (`analyze_task`)

Manba:
- `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/checkers/tz_pr_checker.py:268`

Natija turi:
- `TZPRAnalysisResult` (`success`, `error_message`, `status_banner`, `ai_analysis`, `compliance_score`, `figma_data`, `comment_analysis`, `dev_objections`, ...).

### 2.1 Global precondition case-lar
1. `max_files is not None` YOKI `show_full_diff == false`:
   - FULL policy buzilgan.
   - `build_full_policy_input_violation(...)` banner.
   - `success=false` error result qaytadi.

2. `use_smart_patch is None`:
   - `default_use_smart_patch` setting ishlatiladi.

### 2.2 JIRA olish case-lari
1. `self.jira.get_task_details(task_key)` `None` qaytarsa:
   - `"task topilmadi"` error result.

2. JIRA credential/scope muammosi:
   - `BaseService._get_creds()` `RuntimeError` berishi mumkin (`user_id/company_id yo'q` yoki credential yo'q).
   - `JiraClient` init `ValueError` berishi mumkin (`server/email/token` yo'q).
   - `get_issue()` auth xatoda `RuntimeError` berishi mumkin.
   - Bular outer `try/except`da ushlanib `Kutilmagan xatolik: ...` ko'rinishida qaytadi.

3. JIRA payload tarkibi:
   - `summary`, `description`, `type`, `status`, `assignee`, `reporter`, `priority`, `story_points`, `comments`, `pr_urls`, `figma_links`, `created`, `resolved`, `labels`, `components`.

### 2.3 PR topish/tekshirish case-lari
PR oqimi `PRHelper.get_pr_full_info()` orqali.

Case-lar:
1. JIRA `pr_urls` bor -> shu ishlatiladi.
2. JIRA `pr_urls` yo'q -> GitHub search (`search_pr_by_jira_key`).
3. Hech qayerdan topilmasa -> checker `"PR topilmadi"` error result + warnings.
4. PR URL parse bo'lmasa -> `Invalid PR URL` warning, davom etadi.
5. PR info olinmasa -> `PR info not found` warning, davom etadi.
6. Natijada `pr_details` bo'sh qolsa -> `None` (PR yo'q sifatida qaytadi).
7. Topilgan PR'larning hech biri merged bo'lmasa:
   - `PRNotMergedError` raise.
   - checker `success=false`, error matn: merged talab qilinadi.
8. Mixed holat: merged + non-merged bo'lsa:
   - non-merged lar skip qilinadi, faqat merged qabul qilinadi.

Cache side-effect:
- `set_pr_exists_cache`, `set_pr_merged_cache`, `set_pr_cache` yangilanadi.

### 2.4 TZ minimum length case-lari
1. `min_tz_description_chars > 0` va `description` qisqa:
   - `"TZ yetarli emas ... Servis-1 to'xtatildi"`.
   - error result.
2. Aks holda davom etadi.

### 2.5 Comment/TZ yig'ish case-lari
Manbalar:
- `TZHelper.format_tz_with_comments`
- `CommentSeparator.separate`

Case-lar:
1. `read_comments_enabled=false`:
   - AI ga comments yuborilmaydi (`comments=[]` qilib formatlanadi).
2. `read_comments_enabled=true` va `max_comments_to_read=0`:
   - barcha commentlar TZ ichiga kiradi.
3. `max_comments_to_read>0`:
   - oxirgi N comment kiradi.
4. `analyze_comments()` o'zgarish keyword topsa:
   - status warning beriladi.
5. `CommentSeparator`:
   - `[AI_S1]/[AI_S2]` commentlar AI comment deb ajratiladi.
   - `dev_before`: oxirgi AI commentdan oldingi dev commentlar.
   - `dev_after`: oxirgi AI commentdan keyingi dev commentlar (etiroz).

### 2.6 Recheck case-lari (`return_reason`)
Manba: `core/constants.py`

Case-lar:
1. `return_reason in RECHECK_REASONS` (`WARN_LOW_SCORE`) bo'lsa:
   - `is_recheck=true`.
   - oldingi `[AI_S1]` dan reanalysis context quriladi.
   - `dev_after` objectionlar reanalysis promptga qo'shiladi.
2. Boshqa return_reason'lar:
   - reanalysis section qo'shilmaydi.

### 2.7 Figma olish case-lari (fail-safe)
Case-lar:
1. `figma_links` yo'q -> `figma_data=None` (normal).
2. `figma_tokens` topilmasa -> warning, summary: "Token topilmadi yoki ruxsat yo'q".
3. Har link uchun `get_file_summary` muvaffaqiyatli -> summary qo'shiladi.
4. Har link uchun xato -> warning, summary: `Error: ...`.
5. Global figma xato -> warning, `figma_data=None`.

Usable figma aniqlash:
- Agar summary matni `token topilmadi/ruxsat yo'q/error/olinmadi/...` markerlaridan iborat bo'lsa -> `usable=false`.

### 2.8 Prompt qurish case-lari
Prompt bloklari:
- Scope instruction
- Data sections (`ai_data_section_order`: `tz/comments/figma/code`)
- Dynamic response sections (`visible_sections`)

Case-lar:
1. Hidden sectionlar bo'lsa -> promptga "taqiqlangan bo'lim" qoidasi qo'shiladi.
2. Figma usable bo'lmasa -> promptga figma bo'yicha taxmin yozmaslik qoidasi qo'shiladi.
3. `reanalysis_section` bo'lsa -> TZdan keyin majburiy qo'shiladi.
4. Code section:
   - `use_smart_patch=true` va `smart_context` bor -> smart context.
   - bo'lmasa oddiy `patch`.

### 2.9 AI chaqiriq case-lari
`self.gemini.analyze(prompt, max_output_tokens=ai_max_output_tokens)`

Gemini ichki case-lari:
1. API keylar yo'q/bo'sh -> RuntimeError.
2. Barcha keylar freeze -> RuntimeError.
3. Transient xato (`503/overloaded/...`) -> retry/backoff, fallback model urinish.
4. Permanent xato (`429/403/quota/...`) -> key freeze va keyingi keyga o'tish.
5. Barcha urinishlar muvaffaqiyatsiz -> RuntimeError.

Checker darajasida:
- `_try_ai_analysis` exception bo'lsa `success=false`, `error="AI xatolik (attempt 0): ..."`.

### 2.10 FULL-only post-check case-lari
`_analyze_with_retry` yakunida:
1. `result.success == true` VA `files_analyzed == files_total` -> qabul qilinadi.
2. Aks holda (AI error yoki partial) -> `build_full_analysis_blocked(...)`:
   - `FULL_BLOCKED_OVERLOAD` yoki `FULL_BLOCKED_TECHNICAL`.
   - `success=false`, `status_banner` bilan qaytadi.

### 2.11 Figma sanitize case-lari
AI javobidan keyin:
1. Figma usable bo'lsa -> javob o'zgarmaydi.
2. Figma usable bo'lmasa -> javobdagi figma bo'limi almashtiriladi yoki qo'shiladi:
   - "Figma ma'lumotlari olinmadi" degan halol bo'lim majburiy bo'ladi.

### 2.12 Compliance score extraction case-lari
Regex ketma-ketligi:
1. `COMPLIANCE_SCORE: XX%`
2. `**COMPLIANCE_SCORE: XX%**`
3. `MOSLIK BALI ... XX%`
4. `compliance|bali|score|moslik` yaqinidagi `%`
5. Topilmasa `None`.

### 2.13 Yakuniy return case-lari
Success result:
- `success=true`
- `ai_analysis`
- `compliance_score` (`int` yoki `None`)
- `pr_count/files_changed/...`
- `figma_data`
- `comment_analysis`
- `dev_objections` (`is_recheck` bo'lsa)

Error result:
- `success=false`
- `error_message`
- `status_banner` (policy/full-block holatlarda)
- `warnings`
- `ai_retry_count/files_analyzed/total_prompt_size`

## 3) Webhook Service1 checker natijasini qanday talqin qiladi

Manba: `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/service_runner.py`

`analyze_task` natijasi `result.success=false` bo'lsa:
1. `error_type=ai_timeout` -> `service1_status=blocked`, retry kutadi, warning comment yozadi.
2. `error_type in (pr_not_found, pr_not_merged, tz_too_short)`:
   - warning comment yozadi
   - task `return_status` ga o'tkazishga urinadi
   - DB `returned`.
3. Boshqa xato -> `service1_status=error`, comment yozadi.

`result.success=true` bo'lsa:
1. Success comment (ADF, fallback simple).
2. DB `service1_status=done`, `compliance_score` saqlanadi.
3. `auto_return_enabled=true` va `score < threshold` bo'lsa:
   - task return statusga o'tkaziladi
   - DB `returned`
   - `return_reason = WARN_LOW_SCORE`.

## 4) Error classification map

Manba: `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/error_handler.py`

String -> class:
1. `pr topilmadi/no pr found/...` -> `pr_not_found` -> `WARN_NO_PR`
2. `merged emas/not merged/...` -> `pr_not_merged` -> `WARN_PR_NOT_MERGED`
3. `tz yetarli emas/...` -> `tz_too_short` -> `WARN_MIN_TZ`
4. `timeout/429/rate limit/overloaded/...` -> `ai_timeout` -> `WARN_AI_TIMEOUT`
5. qolgani -> `unknown` -> `ERR_UNKNOWN`

## 5) Sozlamalar checker behavioriga qanday ta'sir qiladi

Asosiy settinglar:
- `read_comments_enabled`
- `max_comments_to_read`
- `min_tz_description_chars`
- `default_use_smart_patch`
- `ai_data_section_order` (`tz` va `code` bo'lishi shart)
- `visible_sections`
- `dev_comments_max`
- `ai_max_output_tokens`

Validation case-lari (`__post_init__`):
1. `return_threshold` 0..100 bo'lmasa -> ValueError.
2. `max_skip_check_comments < 1` -> ValueError.
3. `ai_data_section_order`da invalid qiymat bo'lsa -> ValueError.
4. `ai_data_section_order`da `tz` yoki `code` yo'q bo'lsa -> ValueError.

## 6) "Checkerga task berilganda" to'liq case ro'yxati (qisqa indeks)

A. Checkerga UMUMAN kirmaslik case-lari (webhook pre-check):
1. Event noto'g'ri
2. Status trigger emas
3. Issue type filtrdan o'tmadi
4. Assignee exclude
5. AI_SKIP topildi
6. Dublikat/progressing holat

B. Checker ichidagi error case-lar:
1. FULL policy input invalid
2. Credential/scope xato
3. JIRA issue topilmadi/auth xato
4. PR topilmadi
5. PR merged emas
6. TZ minimumdan qisqa
7. AI texnik xato
8. AI overload/partial (FULL blocked)

C. Checker ichidagi success case-lar:
1. Figma yo'q, lekin TZ+code bo'yicha tahlil
2. Figma bor va usable, to'liq tahlil
3. Recheck mode (`WARN_LOW_SCORE`) bilan objection inobatga olingan tahlil

## 7) O'zgarmas invariants (hozirgi kodga ko'ra)

1. Checker `analyze_task` exception tashlamasdan `TZPRAnalysisResult` qaytarishga harakat qiladi.
2. Checker FULL-only siyosatini majburiy ushlab turadi.
3. TZ va JIRA comments checker uchun asosiy input hisoblanadi.
4. Figma fail-safe: figma xatosi checkerni yiqitmaydi.
5. `COMPLIANCE_SCORE` topilmasa ham result `success=true` bo'lishi mumkin (`score=None`).
6. Webhookda faqat `WARN_LOW_SCORE` qayta-tekshiruv (`recheck`) kontekstini yoqadi.
