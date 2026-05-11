# Testcase Generator Case Documentation (As-Is)

Bu hujjatning maqsadi: mavjud `Testcase Generator` logikasini 1:1 hujjatlashtirish.

Muhim chegaralar:
- Bu hujjat `as-is` holatni yozadi.
- Yangi dizayn yoki refactor taklif qilmaydi.
- Mavjud branchlar, xato case'lar va natija holatlari qayd etiladi.

## 1) Kirish nuqtalari

### 1.1 Frontend API route (UI)
Manba: `/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/testcase/generate/route.ts`

Case-lar:
1. Sessiya yo'q/yaroqsiz -> `401`, `{ success:false, error:"Sessiya topilmadi..." }`.
2. Role/module ruxsati yo'q -> `403`, `{ success:false, error:"Test Case Generator uchun ruxsat yo'q." }`.
3. `task_key` bo'sh -> `400`, `{ success:false, error:"Task key majburiy." }`.
4. Valid payload -> backend `/api/testcase/generate` ga yuboradi.

Payload normalize:
- `task_key` -> `trim().toUpperCase()`
- `include_pr` default `true`
- `use_smart_patch` default `true`
- `test_types` default `['positive', 'negative']`
- `custom_context` default `""`

### 1.2 Backend API route (direct service call)
Manba: `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/testcase_api.py`

Case-lar:
1. Session/scope auth xato -> HTTPException (auth layer).
2. Valid scope -> `TestCaseGeneratorService(user_id, company_id).generate_test_cases(...)`.
3. Kutilmagan exception -> `500`, `Testcase generation error: ...`.

### 1.3 Webhook path (Service2)
Manbalar:
- `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/jira_webhook_handler.py`
- `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/service_runner.py`
- `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/testcase_webhook_handler.py`
- `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/queue_manager.py`

Service2 ishga tushish yo'llari:
1. JIRA webhook trigger -> queue orqali `Service1 -> delay -> Service2` (`_run_task_group`).
2. `AI_SKIP` holatida Service1 skip bo'lsa ham Service2 alohida ishga tushishi mumkin.
3. Manual endpoint:
   - `/manual/testcase/{task_key}` -> faqat Service2.
   - `/manual/check/{task_key}` -> Service1 + ixtiyoriy Service2.

## 2) Service2 orchestration (`_run_testcase_generation`)

Manba: `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/service_runner.py:215`

### 2.1 Service2 startdan oldingi skip case-lar
1. Task DB'da yo'q -> skip.
2. `service1_status` `done|skip|error` emas -> skip.
3. `service1_status='error'` va `service2_status!='pending'` -> skip.
4. `service2_status='done'` -> skip.
5. `company_id` yo'q -> skip/error log.
6. `compliance_score < threshold` -> skip.
7. `task_status='returned'` -> skip.

### 2.2 Service2 run natijasi case-lari
`check_and_generate_testcases()` natijasiga qarab:
1. `success=True` -> `set_service2_done(task_key)`.
2. `success=False`:
   - `error_type='ai_timeout'` -> `service2_status='blocked'`, retry delay bilan.
   - `error_type in ('pr_not_found','pr_not_merged','tz_too_short')` -> task return oqimi.
   - boshqasi -> `service2_status='error'`.

### 2.3 Queue-related case-lar
Manba: `queue_manager.py`

1. Queue `enabled=false` -> lock'siz ketma-ket chaqriq.
2. Queue `enabled=true`:
   - tenant-level lock olinadi.
   - timeout bo'lsa task `blocked` + timeout comment.
   - Service1 dan keyin `checker_testcase_delay` kutish.
3. `_can_run_service2()` shartlari:
   - `service1_status in ('done','skip')` va `score is None yoki score>=threshold` va `task_status not in ('returned','blocked')`.
   - YOKI `service1_status='error'` va `service2_status='pending'` (TZ-only imkoniyati uchun).

## 3) Testcase webhook handler (`check_and_generate_testcases`)

Manba: `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/testcase_webhook_handler.py:17`

### 3.1 Pre-check case-lar
1. `auto_comment_enabled=false` -> `(False, "Auto-comment disabled")`.
2. `new_status` trigger emas -> `(False, "Status ... is not a trigger")`.
3. `include_pr is None` -> `default_include_pr` setting ishlatiladi.

### 3.2 Service init case-lari
1. `company_id` berilgan:
   - webhook credential tekshiriladi (`get_company_webhook_credentials`).
   - credential xato -> `(False, <xatolik matni>)`.
2. Service yaratiladi -> `TestCaseGeneratorService(company_id=...)`.

### 3.3 Generation natijasi case-lari
1. `result.success=false`:
   - `error_type` klassifikatsiya qilinadi.
   - ayrim holatlarda (`pr_not_merged/pr_not_found/tz_too_short` yoki matn conditionlari) JIRA warning/error comment yozishga urinadi.
   - `(False, error_msg)` qaytaradi.
2. `result.success=true`, lekin `result.test_cases` bo'sh:
   - `(False, "No test cases generated")`.
3. `result.success=true` va test caselar bor:
   - `_write_testcases_comment(...)` orqali JIRA'ga yoziladi.
   - `(True, message)` yoki yozish xatosida `(False, message)`.

### 3.4 JIRA comment yozish case-lari (`_write_testcases_comment`)
1. `use_adf=true`:
   - ADF document yoziladi.
   - ADF fail bo'lsa simple comment fallback.
2. `use_adf=false`:
   - faqat simple comment yoziladi.
3. Yozish success -> `True`.
4. Yozish fail yoki exception -> `False`.

## 4) Asosiy servis oqimi (`generate_test_cases`)

Manba: `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/generators/testcase_generator.py:111`

Natija turi:
- `TestCaseGenerationResult` (`success`, `error_message`, `status_banner`, `test_cases`, `warnings`, `ai_prompt_size`, `ai_model`, `files_analyzed`, ...).

### 4.1 Input/default case-lar
1. `test_types` bo'sh bo'lsa -> `['positive','negative']`.
2. `status_callback` bo'lsa progress callback ishlaydi.

### 4.2 JIRA olish case-lari
1. `self.jira.get_task_details(task_key)` `None` -> `success=false`, `"task topilmadi"`.
2. Credential/scope xatolari (`BaseService/JiraClient`) -> outer `except` orqali `success=false`, `error_message=str(e)`.

### 4.3 Skip/PR cache case-lari
Manba: `utils/pr_cache.py`

Oqim:
1. `skip_detected=True` -> PR check butunlay o'tkazib yuboriladi.
2. `skip_detected=False` va `include_pr=True`:
   - `pr_exists_cache=False` -> darhol `success=false`, `PR topilmadi`.
   - `pr_merged_cache=False` -> darhol `success=false`, `PR merged emas`.
   - `pr_cache` bo'lsa -> shu ishlatiladi (Servis-1 topgan ma'lumot).
   - `pr_cache` yo'q bo'lsa -> `PRHelper.get_pr_full_info()` bilan mustaqil fetch.
3. `include_pr=False` -> PR fetch qilinmaydi (TZ-only mode).

### 4.4 PR fallback case-lari
`include_pr=True` bo'lsa ham:
1. PR fetch exception (`PRNotMergedError`dan tashqari) -> `pr_info=None`, warning bilan davom etadi.
2. `pr_info=None` bo'lsa generation to'xtamaydi, TZ-only tarzda davom etadi.

### 4.5 TZ minimal uzunlik case-lari
1. `min_tz_chars` kompaniya rejimida `webhook_tz_pr.min_tz_description_chars`dan olinadi.
2. Global/UI rejimida `tz_pr_checker.min_tz_description_chars`dan olinadi.
3. `description` minimaldan qisqa -> `success=false`, `"Servis-2 to'xtatildi"` xabari.

### 4.6 Comment/TZ yig'ish case-lari
1. `read_comments_enabled=false` -> `comments=[]` qilib formatlanadi.
2. `read_comments_enabled=true` va `max_comments_to_read=0` -> barcha comment.
3. `max_comments_to_read>0` -> oxirgi N comment.
4. `TZHelper.analyze_comments` natijasi `comment_analysis`ga tushadi.

### 4.7 AI bosqichi (`_generate_with_ai`) case-lari
1. Prompt `_create_test_case_prompt()` bilan quriladi.
2. Prompt hajmi `_calculate_text_length()` bilan tekshiriladi.
3. FULL-only qoida:
   - agar prompt token limitdan oshsa -> `success=false`, `"prompt too large for full analysis"`.
   - truncate qilinmaydi.
4. AI call exception -> `success=false`, `error="AI xatosi: ..."`.
5. AI success -> `raw_response` qaytariladi.

### 4.8 FULL blocked banner case
`ai_result.success=false` bo'lsa:
1. `build_full_analysis_blocked(...)` ishlatiladi.
2. Natija `TestCaseGenerationResult.success=false`, `status_banner` bilan qaytadi.
3. `ai_prompt_size`, `ai_model`, `files_analyzed` to'ldiriladi.

### 4.9 Parse case-lari (`_parse_test_cases`)
1. JSON topilmasa (`{...}` topilmadi) -> `[]`.
2. JSON parse OK:
   - list key aliaslari: `test_cases | testCases | tests | test_case_list`.
   - bo'sh list bo'lsa warning, lekin exception emas.
3. JSON decode xato:
   - `_try_repair_json()` urinishlari:
     - sanitize escape
     - `rfind('},')` asosida tiklash
     - oxirgi `}` asosida tiklash
   - tiklansa parse davom etadi, bo'lmasa `[]`.
4. Har test case item qisman bo'lsa default maydonlar bilan `TestCase` obyekt qilinadi.

### 4.10 `generate_test_cases` yakuniy return case-lari
1. Parse'dan keyin `test_cases` bo'sh bo'lsa ham servis `success=true` qaytarishi mumkin (0 ta natija bilan).
2. Statistika hisoblanadi: `by_type`, `by_priority`, `total_test_cases`.
3. `warnings` saqlanadi (PR fallback holatlar).
4. Outer exception bo'lsa `success=false`, `error_message=str(e)`.

## 5) Prompt qurilish logikasi (`_create_test_case_prompt`)

### 5.1 Dinamik bo'limlar
Doimiy bo'limlar:
1. TASK ma'lumotlari
2. TZ bo'limi
3. Test talablar
4. JSON format talabi

Shartli bo'limlar:
1. `comments_block` -> `comment_analysis.has_changes=true` bo'lsa.
2. `custom_context_block` -> `custom_context` bo'sh bo'lmasa.
3. `dev_objections_block` -> `dev_objections` bo'lsa.
4. `code_block` -> `pr_info` bo'lsa.

### 5.2 Bo'lim tartibi
- `ai_data_section_order` setting bo'yicha yig'iladi (`testcase_generator` yoki `webhook_testcase` contextiga qarab).
- Mavjud settings validatsiyasi ruxsat beradigan kalitlar: `tz, comments, custom_context, code`.
- Kodda `dev_objections` block ham bor, lekin default setting order odatda bu kalitni kiritmaydi.

### 5.3 PR code block logikasi
1. Har fayl uchun `smart_context` bo'lsa shu qo'shiladi.
2. Aks holda `patch` qo'shiladi.
3. `files_to_show = pr_info['files_changed']` (kesish yo'q, FULL modega mos).

## 6) Error classification va reason code mapping

Manba: `/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/error_handler.py`

Mapping:
1. `pr_not_found` -> `WARN_NO_PR`
2. `pr_not_merged` -> `WARN_PR_NOT_MERGED`
3. `tz_too_short` -> `WARN_MIN_TZ`
4. `ai_timeout` -> `WARN_AI_TIMEOUT`
5. boshqa -> `ERR_UNKNOWN`

Service2da bu mapping DB status va return reason yozishda ishlatiladi.

## 7) Sozlamalar behaviorga ta'siri

Asosiy `testcase` settinglar:
1. `default_include_pr`
2. `default_use_smart_patch`
3. `default_test_types`
4. `max_test_cases`
5. `ai_max_output_tokens`
6. `ai_data_section_order`
7. `read_comments_enabled`
8. `max_comments_to_read`
9. `auto_comment_enabled` (webhook trigger uchun)
10. `auto_comment_trigger_status` va aliaslari
11. `use_adf_format`

Validatsiya (`TestcaseGeneratorSettings.__post_init__`):
1. `max_test_cases` 1..50 oralig'ida bo'lishi shart.
2. `ai_data_section_order` faqat ruxsat etilgan kalitlardan bo'lishi shart.
3. `ai_data_section_order`da `tz` bo'lishi shart.

## 8) "Testcase moduliga task berilganda" to'liq case indeks

A. Modulga kirmaslik/skip holatlari:
1. UI/API auth yoki module access yo'q.
2. Webhookda `auto_comment_enabled=false`.
3. Trigger status emas.
4. Service2 orchestration pre-checklar (`service1 hali tayyor emas`, `service2 done`, `score past`, `task returned`).

B. Moduldagi xato holatlar:
1. JIRA task topilmadi.
2. PR cache bo'yicha `pr_exists=false`.
3. PR cache bo'yicha `pr_merged=false`.
4. TZ minimaldan qisqa.
5. Prompt token limiti oshgan (FULL blocked).
6. Gemini xatosi/timeout.
7. JSON parse bo'lmadi (empty case list).
8. JIRA comment yozish muvaffaqiyatsiz.

C. Moduldagi success holatlar:
1. PR bilan to'liq testcase generation.
2. PR yo'q yoki fetch xato bo'lsa TZ-only fallback generation.
3. Comment change/custom context inobatga olingan generation.

## 9) O'zgarmas invariants (hozirgi kodga ko'ra)

1. `generate_test_cases()` exception tashlamasdan `TestCaseGenerationResult` qaytarishga urinadi.
2. Prompt limit oshsa truncate qilmaydi (FULL-only yondashuv).
3. `include_pr=true` bo'lsa ham fallbackda TZ-only davom etishi mumkin (cache gate fail case-lardan tashqari).
4. `generate_test_cases()` ichida 0 testcase holati `success=true` bo'lishi mumkin; ammo webhook layer buni `failure` deb qaytaradi.
5. Service2 DB status transitionlari `service_runner`da boshqariladi, generatorning o'zi DB status yozmaydi.

