# Progress Log

Bu fayl loyihada amalda bajarilgan ishlarni, qolgan ishlarni va keyingi qadamlarni kuzatish uchun yuritiladi.

## Qoidalar

- Har bir muhim texnik o'zgarishdan keyin bu fayl yangilanadi
- `Done`, `In Progress`, `Next` bo'limlari doim dolzarb saqlanadi
- Roadmap bilan bog'liq ishlar imkon qadar [ROADMAP_SAAS.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ROADMAP_SAAS.md) bosqichlari bilan yoziladi

## Holat

### Done

#### 2026-05-11 - TZPR checker Gemini oqimi tozalandi va UI structured analysis cockpitga o'tkazildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
  - Stage 10 - Core Feature Stabilization
- O'zgarish:
  - [core/tz_helper.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/core/tz_helper.py)
    - promptga yuboriladigan TZ commentlaridan eski `AI_S1` va `AI_S2` izohlari default bo'yicha chiqarib tashlanadigan qilindi
    - `comment_analysis` endi filtered AI commentlar sonini ham qaytaradi
    - comment tahlili eski AI commentlarni developer o'zgarishi deb hisoblamaydigan qilindi
  - [services/checkers/tz_pr_checker.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/checkers/tz_pr_checker.py)
    - UI uchun alohida `output_profile` oqimi qo'shildi; checker sahifasi endi `summary/completed/partial/failed/issues/figma` bo'limlarini to'liq so'raydi
    - Gemini markdown javobi backendda structured sectionlarga parse qilinadigan bo'ldi
    - `analysis_sections` va `analysis_overview` payloadi qo'shildi
    - Figma yo'q bo'lgandagi duplicate section sanitize qilindi (`## FIGMA...` va `## 🎨 FIGMA...` ikkalasi ham ushlanadi)
  - [services/api/tzpr_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/tzpr_api.py)
    - `AnalyzeRequest` kontraktiga `output_profile` qo'shildi
  - [frontend/src/app/api/tzpr/analyze/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/tzpr/analyze/route.ts)
    - browser checker chaqirig'i backendga `output_profile: "ui"` yuboradigan qilindi
  - [frontend/src/lib/types.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/types.ts)
    - structured analysis uchun yangi `TZPRAnalysisSection` va `TZPRAnalysisOverview` type'lari qo'shildi
  - [frontend/src/components/tzpr-checker.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/tzpr-checker.tsx)
    - heuristic accordion parser olib tashlandi
    - sahifa `overview / requirements / evidence / raw ai` tablari bilan task analysis cockpit ko'rinishiga o'tkazildi
    - compliance, verdict, diagnostics, requirement matrix va evidence bloklari backend structured payloadiga tayangan holda render qilinadigan bo'ldi
  - [tests/test_tzpr_ui_contract.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/tests/test_tzpr_ui_contract.py)
    - prompt cleanup, AI comment filter, UI profile section seti, Figma sanitize va structured parse uchun focused testlar qo'shildi
- Verification:
  - `./.venv/bin/python -m py_compile core/tz_helper.py services/checkers/tz_pr_checker.py services/api/tzpr_api.py`
  - `./.venv/bin/pytest -q tests/test_tzpr_ui_contract.py`
  - `cd frontend && npm run typecheck`
  - natija: muvaffaqiyatli

#### 2026-05-10 - `Checker kechikishi` webhook checker kartadan chiqarildi, faqat `Tizim` tabga biriktirildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
  - Stage 10 - Core Feature Stabilization
- O'zgarish:
  - [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx)
    - `Webhook -> Servis-1 (Checker)` kartasidan `Checker kechikishi (sekund)` maydoni olib tashlandi
  - [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts)
    - webhook save payload'dan `checker_delay_seconds` uzatish olib tashlandi
  - [services/api/settings_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/settings_api.py)
    - `checker_delay_seconds` webhook save'da optional qilindi (kelmasa queue qiymati overwrite qilinmaydi)
  - [frontend/src/lib/types.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/types.ts)
    - `WebhookSettingsSaveRequest.checker_delay_seconds` optional qilindi
- Verification:
  - `./.venv/bin/python -m py_compile services/api/settings_api.py`
  - `cd frontend && npm run typecheck`
  - natija: muvaffaqiyatli

#### 2026-05-10 - Webhook trigger soddalashtirildi: faqat `Asosiy trigger status`, qiymat user kiritganicha saqlanadi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
  - Stage 10 - Core Feature Stabilization
- O'zgarish:
  - [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx)
    - `Trigger statuslari` input olib tashlandi
    - `Asosiy trigger status` saqlandi
    - trigger qiymati endi `toUpperCase()` qilinmaydi
  - [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts)
    - trigger qiymatini normalize/uppercase qilish olib tashlandi
    - qiymat user yuborgan ko'rinishda saqlanadi
- Verification:
  - `cd frontend && npm run typecheck`
  - natija: muvaffaqiyatli

#### 2026-05-10 - Webhook tab UI: 2 servis sozlamalari alohida kartalarga ajratildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- O'zgarish:
  - [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx)
  - `Webhook` tab ichida:
    - `Servis-1: Webhook TZ-PR` alohida card
    - `Servis-2: Webhook Testcase` alohida card
  - Existing save logic va setting qiymatlari o'zgartirilmagan, faqat vizual ajratish (UX)
- Verification:
  - `cd frontend && npm run typecheck`
  - natija: muvaffaqiyatli

#### 2026-05-09 - Settings yakuniylashtirish (Phase-2): Webhook Testcase sozlamalari va to'liq ona-bola visibility

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
  - Stage 10 - Core Feature Stabilization
- O'zgarish:
  - `webhook_testcase.*` sozlamalari `webhook/config/read|save` kontraktiga qo'shildi:
    - [services/api/settings_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/settings_api.py)
  - Frontend webhook route kengaytirildi (`GET/POST`) va yangi testcase payloadlar ulandi:
    - [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts)
  - Frontend types yangilandi:
    - [frontend/src/lib/types.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/types.ts)
  - Settings UI'da `Webhook Testcase (Auto-comment)` bo'limi qo'shildi va `ona -> bola` hide/show to'liq ishlatildi:
    - [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx)
    - `testcase_auto_comment_enabled=false` bo'lsa testcase child maydonlar yashiriladi
    - `testcase_read_comments_enabled=false` bo'lsa `testcase_max_comments_to_read` yashiriladi
- Verification:
  - `./.venv/bin/python -m py_compile services/api/settings_api.py`
  - `cd frontend && npm run typecheck`
  - natija: muvaffaqiyatli

#### 2026-05-09 - Settings qatlami kengaytirildi: `Tizim` tab backend/frontend va ona-bola visibility qoidalari (Phase-1)

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
  - Stage 10 - Core Feature Stabilization
- O'zgarish:
  - Backend settings API kengaytirildi:
    - [services/api/settings_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/settings_api.py)
    - qo'shildi: `/api/settings/system/config/read`, `/api/settings/system/config/save`
    - `webhook/config/read|save` kengaytirildi (`return_status`, `allowed_issue_types`, `max_skip_check_comments`, `trigger_status_aliases` va boshqalar)
  - Frontend backend client/type kontrakti kengaytirildi:
    - [frontend/src/lib/types.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/types.ts)
    - [frontend/src/lib/backend.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/backend.ts)
  - Yangi frontend route qo'shildi:
    - [frontend/src/app/api/settings/system/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/system/route.ts)
  - Settings UI kengaytirildi:
    - [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx)
    - yangi `Tizim` tab qo'shildi
    - `ona -> bola` hide/show qoidalari joriy qilindi (`modules`, `webhook`, `system`)
    - webhook form qo'shimcha fieldlar bilan kengaydi
- Verification:
  - `./.venv/bin/python -m py_compile services/api/settings_api.py`
  - `cd frontend && npm run typecheck`
  - natija: muvaffaqiyatli

#### 2026-05-09 - Settings dependency hujjati yaratildi (Tab/Modul kesimida ONA-BOLA-MUSTAQIL)

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
  - Stage 10 - Core Feature Stabilization
- O'zgarish:
  - [docs/SETTINGS_DEPENDENCY_GUIDE.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/docs/SETTINGS_DEPENDENCY_GUIDE.md) qo'shildi
  - Hujjatda quyidagilar to'liq yozildi:
    - `AI & Integrations`, `Modullar`, `Webhook`, `Tizim` tablari bo'yicha barcha settinglar
    - Har bir setting roli: `ONA`, `BOLA`, `MUSTAQIL`, `SOFT`
    - Yakuniy `UI hide/show` qoidalari (`parent off -> child hide`)
    - Muhim istisnolar: `webhook_tz_pr.return_status` va `queue.checker_testcase_delay` doim ko'rinishi

#### 2026-05-09 - Testcase Generator `as-is case` hujjati yaratildi (mavjud logika branch-by-branch)

- Roadmap bog'lanishi:
  - Stage 10 - Core Feature Stabilization
  - Stage 11 - Jobs, Queue va Reliability
- O'zgarish:
  - [docs/TESTCASE_GENERATOR_CASES.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/docs/TESTCASE_GENERATOR_CASES.md) qo'shildi
  - Hujjatda Testcase moduliga task berilgandagi barcha asosiy va mayda case'lar yozildi:
    - UI/API kirish nuqtalari
    - Service2 webhook orchestration (`queue`, `skip`, `status gate`) branchlari
    - `generate_test_cases()` ichidagi JIRA/PR cache/TZ/comment/AI/parse branchlari
    - `FULL-only` token limit block holatlari va `status_banner` qaytish oqimi
    - `result.success` vs `0 testcase` tafovuti (generator va webhook talqini)

#### 2026-05-09 - TZPR checker `as-is case` hujjati yaratildi (mavjud logika branch-by-branch)

- Roadmap bog'lanishi:
  - Stage 10 - Core Feature Stabilization
  - Stage 11 - Jobs, Queue va Reliability
- O'zgarish:
  - [docs/TZPR_CHECKER_CASES.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/docs/TZPR_CHECKER_CASES.md) qo'shildi
  - Hujjatda checkerga task berilgandagi barcha asosiy va mayda case'lar yozildi:
    - UI/API kirish nuqtalari
    - Webhook pre-check filter va AI_SKIP holatlari
    - `analyze_task()` ichidagi FULL-only policy, JIRA/PR/TZ/comment/Figma/AI branchlari
    - Error classification va return reason mapping
    - Yakuniy success/error natija modellari

#### 2026-05-08 - Checker uchun `default_use_smart_patch` setting qo'shildi va ishga ulandi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
  - Stage 6 - Reliability
- O'zgarish:
  - [config/app_settings.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/config/app_settings.py) ichida `TZPRCheckerSettings.default_use_smart_patch: bool = True` qo'shildi
  - [services/checkers/tz_pr_checker.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/checkers/tz_pr_checker.py) da `analyze_task(..., use_smart_patch=None)` bo'lsa endi setting'dagi `default_use_smart_patch` ishlatiladi
  - [services/api/tzpr_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/tzpr_api.py) va [frontend/src/app/api/tzpr/analyze/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/tzpr/analyze/route.ts) da `use_smart_patch` nullable qilindi (`None/null` => setting ishlaydi)
  - [frontend/src/components/tzpr-checker.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/tzpr-checker.tsx) endi hardcoded `use_smart_patch: true` yubormaydi; badge matni `setting bo'yicha`ga o'zgartirildi
  - [frontend/src/lib/types.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/types.ts) da `TZPRAnalyzeRequest.use_smart_patch?: boolean | null`
- Verification:
  - `./.venv/bin/python -m py_compile config/app_settings.py services/api/tzpr_api.py services/checkers/tz_pr_checker.py`
  - `cd frontend && npm run typecheck`
  - natija: muvaffaqiyatli

#### 2026-05-08 - Checker va Testcase uchun yagona `FULL-only` AI policy joriy qilindi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
  - Stage 6 - Reliability
- Muammo:
  - Overload holatlarda checker/testcase ayrim joylarda promptni qisqartirish yoki fayllarni kamaytirish orqali partial tahlilga tushishi mumkin edi
  - bu esa noto'liq input asosida xulosa chiqish xavfini oshirardi
- Yechim:
  - umumiy policy helper qo'shildi:
    - [core/analysis_policy.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/core/analysis_policy.py)
    - `FULL_BLOCKED_OVERLOAD`, `FULL_BLOCKED_TECHNICAL`, `FULL_POLICY_INPUT_INVALID` uchun standart banner payload
  - checker:
    - [services/checkers/tz_pr_checker.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/checkers/tz_pr_checker.py)
    - `max_files != None` yoki `show_full_diff=false` bo'lsa darhol bloklanadi
    - fallback strategiyalar (faylni kamaytirish / diffsiz urinish) olib tashlandi
    - failure holatida `status_banner` + prompt/model/files meta qaytariladi
  - testcase:
    - [services/generators/testcase_generator.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/generators/testcase_generator.py)
    - prompt truncation olib tashlandi (FULL policy)
    - PR code bo'limida `pr_max_files` kesish olib tashlandi (barcha fayl)
    - AI xatoligida standart `status_banner` qaytariladi
  - frontend:
    - yangi umumiy banner komponent:
      - [frontend/src/components/analysis-status-banner.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/analysis-status-banner.tsx)
    - checker/testcase ekranlari banner payloadni bir xil formatda ko'rsatadi:
      - [frontend/src/components/tzpr-checker.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/tzpr-checker.tsx)
      - [frontend/src/components/testcase-generator.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/testcase-generator.tsx)
    - type'lar kengaytirildi:
      - [frontend/src/lib/types.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/types.ts)
- Verification:
  - `./.venv/bin/python -m py_compile core/analysis_policy.py services/checkers/tz_pr_checker.py services/generators/testcase_generator.py`
  - `cd frontend && npm run typecheck`
  - natija: muvaffaqiyatli

#### 2026-05-08 - `DEV-8220` uchun TZPR -> Gemini oqimini audit qilish scripti qo'shildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI (AI natijani userga tushunarli ko'rsatish sifati)
- Qo'shildi:
  - [scripts/debug_tzpr_gemini_flow.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/scripts/debug_tzpr_gemini_flow.py)
    - checker pipeline'ni (`TZPRService.analyze_task`) ishga tushiradi
    - Gemini `analyze(prompt, max_output_tokens)` chaqirig'ini intercept qilib prompt/response ni capture qiladi
    - frontend payload, backend payload, checker status update'lari, UI accordion projection'ini bitta reportga yig'adi
    - output:
      - `data/debug/tzpr_gemini_flow_<TASK>_<timestamp>.json`
      - `data/debug/tzpr_gemini_flow_<TASK>_<timestamp>.md`
- Verification:
  - `PYTHONPATH=. ./.venv/bin/python scripts/debug_tzpr_gemini_flow.py --task-key DEV-8220 --user-id 161 --use-env-creds`
  - report:
    - `/Users/mac/Documents/projects/JIRA-AI-Analyzer/data/debug/tzpr_gemini_flow_DEV-8220_20260508_121406.json`
    - `/Users/mac/Documents/projects/JIRA-AI-Analyzer/data/debug/tzpr_gemini_flow_DEV-8220_20260508_121406.md`
  - natija: `success=True`, `COMPLIANCE_SCORE=100`, prompt/response capture muvaffaqiyatli

#### 2026-05-08 - Login sahifasi dark mode info-kartalar ranglari tuzatildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- Muammo:
  - Login form pastidagi `Access` va `Session` kartalari `bg-white/80` ishlatgani sababli dark mode'da oq blok bo'lib ko'rinayotgan edi
- Tuzatish:
  - [frontend/src/components/login-form.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/login-form.tsx):
    - ikkala info-karta foni `bg-white/80` dan theme token asosidagi `bg-[color:var(--bg-strong)]` ga o'tkazildi
- Verification:
  - `cd frontend && npm run typecheck`
  - natija: muvaffaqiyatli

#### 2026-05-07 - Strict SaaS credential isolation: global fallbacklar olib tashlandi (Gemini chain istisno)

- Roadmap bog'lanishi:
  - Stage 4 - Multi-Tenant Isolation
  - Stage 6 - Secret Management va Security
- Talab:
  - Kompaniyalar o'zaro default sozlamalarni ishlatmasligi kerak
  - Setting bo'lmasa aniq xatolik qaytishi kerak
  - Faqat Gemini uchun fallback chain ruxsat: `user -> company(admin) -> super admin global`
- Tuzatishlar:
  - [utils/auth/auth_config_helpers.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_config_helpers.py):
    - user credential compose logikasi qat'iylashtirildi: `JIRA/GitHub/Figma` faqat company(admin) dan olinadi
    - userda faqat Gemini override ishlaydi; bo'sh bo'lsa company, keyin super admin global olinadi
  - [utils/auth/auth_db.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_db.py):
    - `has_api_keys_configured()` endi `jira_server` va `github_org` ni ham majburiy tekshiradi
    - env-based Gemini fallback (`GEMINI_DEFAULT_API_KEY`) olib tashlandi
    - helper call signaturelari tozalandi (ortiqcha `os.getenv` uzatish olib tashlandi)
    - `has_user_credentials_configured()` Gemini chain bo'yicha readinessni hisoblaydigan qilindi
  - [utils/github/github_client.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/github/github_client.py):
    - `settings.GITHUB_ORG` / `settings.GITHUB_TOKEN` default fallbacklari olib tashlandi
    - token/org bo'lmasa aniq `ValueError` qaytariladi
  - [utils/jira/jira_client.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/jira/jira_client.py):
    - `settings.JIRA_*` fallbacklari olib tashlandi, `server/email/token` majburiy qilindi
  - [utils/jira/jira_comment_writer.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/jira/jira_comment_writer.py):
    - env (`JIRA_*`) fallback olib tashlandi, explicit credential majburiy qilindi
  - [utils/jira/jira_status_manager.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/jira/jira_status_manager.py):
    - env (`JIRA_*`) fallback olib tashlandi, explicit credential majburiy qilindi
    - singleton/global manager o'rniga explicit tenant credential bilan instance yaratish qoldirildi
  - [utils/figma/figma_client.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/figma/figma_client.py):
    - env (`FIGMA_ACCESS_TOKEN`) fallback olib tashlandi, token bo'lmasa aniq xatolik qaytadi
  - [services/sprint_data_service.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/sprint_data_service.py):
    - global `JiraClient()` fallback olib tashlandi; `user_id` yoki `company_id` bo'lmasa `RuntimeError`
  - [services/webhook/service_runner.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/service_runner.py):
    - `_get_status_manager()` global fallback olib tashlandi; webhook oqimi uchun `company_id` majburiy qilindi
- Verification:
  - `./.venv/bin/python -m py_compile utils/auth/auth_config_helpers.py utils/auth/auth_db.py utils/github/github_client.py utils/jira/jira_client.py utils/jira/jira_comment_writer.py utils/jira/jira_status_manager.py utils/figma/figma_client.py services/sprint_data_service.py services/webhook/service_runner.py`
  - natija: muvaffaqiyatli

#### 2026-05-07 - `Settings` sahifasi dark mode ranglari moslashtirildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- Muammo:
  - `Settings` sahifasida `Faol modullar` kartalari va notice bloklari dark rejimda light fon bilan qolib ketayotgan edi
- Tuzatish:
  - [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
    - `Faol modullar` va `No Modules` kartalari foni `bg-slate-*` dan token-based `bg-layer` ga o'tkazildi
  - [frontend/src/components/ui/notice.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/ui/notice.tsx):
    - `error/success/warning/info` tone ranglari hardcoded light palitradan theme tokenlar asosiga o'tkazildi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: muvaffaqiyatli

#### 2026-05-07 - `Test Case Generator` dark mode ranglari moslashtirildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- Muammo:
  - `testcase` sahifasida ayrim elementlar (`textarea`, test-type chiplar va ba'zi shared input/select komponentlar) dark rejimda light fon bilan qolib ketayotgan edi
- Tuzatish:
  - [frontend/src/components/testcase-generator.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/testcase-generator.tsx):
    - test type chip foni `bg-slate-50` dan token-based `bg-layer` foniga o'tkazildi
  - [frontend/src/components/ui/textarea.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/ui/textarea.tsx):
    - `bg-white` -> `bg-card`
  - [frontend/src/components/ui/select.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/ui/select.tsx):
    - `bg-white` -> `bg-card`
  - [frontend/src/components/ui/status-pill.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/ui/status-pill.tsx):
    - tone ranglari hardcoded light palitradan theme tokenlar asosiga o'tkazildi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: muvaffaqiyatli

#### 2026-05-07 - Dark mode’da oq qolayotgan elementlar token-based ranglarga o'tkazildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- Muammo:
  - `TZ-PR Checker` dark rejimda ayrim bloklar (`input`, `soft card`, `compliance card`, nested detail cardlar) light fon bilan qolayotgan edi
- Tuzatish:
  - [frontend/src/components/ui/input.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/ui/input.tsx):
    - `bg-white` -> `bg-card` (theme token)
  - [frontend/src/components/ui/card.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/ui/card.tsx):
    - `tone="soft"` va `tone="accent"` fonlari hardcoded rangdan token-based fonlarga o'tkazildi
  - [frontend/src/components/ui/badge.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/ui/badge.tsx):
    - `default/success/warning/danger` tone ranglari token-based qilindi
  - [frontend/src/components/tzpr-checker.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/tzpr-checker.tsx):
    - Figma summary card foni `bg-slate-50/80` dan `bg-layer` tokeniga o'tkazildi
  - [frontend/src/components/pr-details-stack.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/pr-details-stack.tsx):
    - nested file details foni token-based qilindi
  - [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
    - `.dark .qa-compliance-card` override qo'shildi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: muvaffaqiyatli

#### 2026-05-07 - UI uchun Light/Dark mode toggle qayta tiklandi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- Muammo:
  - Sidebar ichidagi theme toggle ko'rinmay qolgan, foydalanuvchi light/darkni almashtira olmayotgan edi
- Tuzatish:
  - [frontend/src/components/app-shell.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/app-shell.tsx) ichida:
    - `Tema` toggle qayta qo'shildi (`Light` / `Dark`)
    - tanlangan tema `localStorage` (`qa_theme_mode`) ga saqlanadi
    - sahifa ochilganda saved yoki system (`prefers-color-scheme`) asosida tema tiklanadi
  - [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css) ichida:
    - `.dark .qa-topbar` override qo'shilib dark rejimda topbar fon rangi moslashtirildi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: muvaffaqiyatli

#### 2026-05-07 - Checker `Gemini tahlili` bo'limi Claude UI dagi dropdown (accordion) ko'rinishiga moslashtirildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- Talab:
  - `AI Analysis` natijasi `Ijobiy jihatlari / Kamchiliklar / Tavsiyalar / Developer izohlari` ko'rinishida alohida ochilib-yopiladigan bloklarda chiqishi kerak edi
- Tuzatish:
  - [frontend/src/components/tzpr-checker.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/tzpr-checker.tsx) ichida:
    - `ai_analysis` matni 4 ta canonical bo'limga parse qilinadigan qilindi
    - bo'limlar `details/summary` accordion sifatida render qilinadi
    - birinchi bo'lim (`Ijobiy jihatlari`) default ochiq holatda chiqadi
  - [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css) ichida:
    - `qa-ai-accordion`, `qa-ai-detail-*` classlar qo'shilib, screenshotga mos dropdown stil berildi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: muvaffaqiyatli

#### 2026-05-07 - Checker modulida `Gemini tahlili` matni chiroyli formatga o'tkazildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- Muammo:
  - `AI Analysis` blokida markdown belgilar (`##`, `-`, `**`) raw ko'rinib, o'qish qiyin edi
- Tuzatish:
  - [frontend/src/components/tzpr-checker.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/tzpr-checker.tsx) ichida:
    - `ai_analysis` text sectionlarga parse qilinadigan qilindi
    - heading, paragraf, bullet list va `COMPLIANCE_SCORE` satri alohida vizual elementlarda render qilinadi
  - [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css) ichida:
    - `qa-ai-*` classlar qo'shilib, AI tahlil kartalari uchun yangi tipografiya va spacing berildi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: muvaffaqiyatli

#### 2026-05-07 - Super Admin kompaniya `Faol/Nofaol` tugmasi Postgresda ishlashi tiklandi

- Roadmap bog'lanishi:
  - Stage 10 - Reliability
  - Stage 9 - Product UX/UI
- Root cause:
  - `is_active` ustuni Postgresda `boolean`, lekin repository qatlami `1/0` (smallint) yuborayotgan edi
  - natijada `DatatypeMismatch` sabab `update_company_status` `False` qaytarib, UI'da status o'zgarmasdan qolardi
- Tuzatish:
  - [utils/auth/company_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/company_repository.py) ichida `update_company_active_flag()` parametri `bool(is_active)` bo'ldi
  - bir xil xato boshqa oqimlarda qaytmasligi uchun:
    - [utils/auth/user_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/user_repository.py) `update_user_status_value()`
    - [utils/auth/platform_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/platform_repository.py) `upsert_platform_admin()`
    ham `bool(...)` bilan yozadigan qilindi
  - [frontend/src/app/api/super-admin/companies/[companyId]/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/super-admin/companies/[companyId]/route.ts) ichida `success:false` holatlar uchun aniq error matnlari qaytariladigan qilindi (generic xabar o'rniga)
- Verification:
  - `./.venv/bin/python` orqali live tekshiruv: `update_company_status(321, False)` va `update_company_status(321, True)` ikkalasi ham `True` qaytardi va DB qiymati real almashdi
  - live endpoint sinovi:
    - `PATCH /api/super-admin/companies/321` (`action=status`) -> `{"success": true}` (`false` va `true` holatlarda ham)
    - `psql` tekshiruvda `companies.is_active` qiymati mos ravishda almashdi
  - `./.venv/bin/python -m py_compile utils/auth/company_repository.py utils/auth/user_repository.py utils/auth/platform_repository.py`
  - `cd frontend && npm run typecheck`
  - natija: muvaffaqiyatli

#### 2026-05-07 - Super Admin `Avg score` kartasi nomi va ma'nosi moslashtirildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- [frontend/src/components/super-admin-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/super-admin-panel.tsx) ichida:
  - `Avg score` labeli `Faollik foizi` ga o'zgartirildi
  - helper matni `Faol tenantlar ulushi` ga o'zgartirildi
  - hisoblash o'zgaruvchisi `avgScore` dan `activeRate` ga nomlandi (`active / total * 100`)
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: muvaffaqiyatli

#### 2026-05-07 - Super Admin sidebaridan `Settings` va `Monitoring` chiqarildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- [frontend/src/components/app-shell.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/app-shell.tsx) ichida:
  - `super_admin` uchun `Settings` nav elementi olib tashlandi
  - `Monitoring` nav elementi endi faqat `company_admin` va `monitoring` modul yoqilgan bo'lsa ko'rinadi
  - `super_admin` sidebar endi faqat adminga kerakli bo'limlarni ko'rsatadi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: muvaffaqiyatli

#### 2026-05-07 - Super Admin sidebaridan `Dashboard` chiqarildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- [frontend/src/components/app-shell.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/app-shell.tsx) ichida:
  - `super_admin` uchun `Dashboard` nav elementi olib tashlandi
  - sabab: `super_admin` uchun `/dashboard` allaqachon `/admin`ga yo'naltiriladi va duplicate UX berardi
  - `company_admin/user` uchun `Dashboard` oldingi holatda qoldi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: muvaffaqiyatli

#### 2026-05-07 - Super Admin sidebaridan checker/testcase modullari olib tashlandi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- [frontend/src/components/app-shell.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/app-shell.tsx) ichida:
  - `super_admin` role uchun sidebar navdan:
    - `TZ-PR Checker`
    - `Test Case Generator`
    chiqarildi
  - boshqa rollar uchun mavjud modulga qarab ko'rinish logikasi saqlab qolindi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: muvaffaqiyatli

#### 2026-05-07 - AI Key 1 saqlash oqimi live tekshirildi va UI'da "bo'shab ketish" hissi bartaraf qilindi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
  - Stage 10 - Reliability
- Live tekshiruv:
  - running instance (`127.0.0.1:3000`) orqali super-admin login + `/api/super-admin/ai-defaults` POST sinovi bajarildi
  - route `{"success": true}` qaytardi va `global_settings.gemini_default_api_key_1` qiymati yangilanishi tasdiqlandi
- UX tuzatish:
  - [frontend/src/components/super-admin-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/super-admin-panel.tsx) ichida `loadOverview()` API key inputlarni avtomatik bo'shatib yubormasligi uchun state merge qilindi
  - API key inputlarida `placeholder` endi saqlangan holatni aniq ko'rsatadi:
    - `Saqlangan (yangilash uchun yangi key kiriting)`
- Backend route oldingi fix holatida saqlanib qoldi:
  - bo'sh key submit bo'lsa mavjud kalitni o'chirmaydi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: muvaffaqiyatli

#### 2026-05-07 - AI defaults API key saqlanishi tuzatildi (bo'sh submit kalitni o'chirmaydi)

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
  - Stage 10 - Reliability
- Root cause:
  - [frontend/src/app/api/super-admin/ai-defaults/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/super-admin/ai-defaults/route.ts) bo'sh `api_key_1/api_key_2` ni ham `set_global_setting` bilan yozib yuborardi
  - UI'da key inputlar "Saqlangan (yangilash uchun kiriting)" deb bo'sh turadi; shu holatda `Saqlash` bosilsa mavjud kalit o'chib ketayotgan edi
- Tuzatish:
  - API keylar faqat `trim()`dan keyin qiymat bo'lsa update qilinadigan qilindi
  - bo'sh yuborilganda saqlangan kalitlar saqlanib qoladi
  - model, fallback model va freeze minutes avvalgidek yangilanadi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: muvaffaqiyatli

#### 2026-05-07 - Super Admin kompaniya yaratishdagi noto'g'ri "kod band" xabari tuzatildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
  - Stage 10 - Reliability
- Root cause:
  - Postgres sxemasida `companies.seat_limit` uchun check constraint `>= 1` mavjud
  - UI'dan `seat_limit=0` yuborilganda insert yiqilar edi, lekin frontend route buni noto'g'ri "kod band" deb ko'rsatardi
- Tuzatishlar:
  - [frontend/src/app/api/super-admin/companies/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/super-admin/companies/route.ts):
    - `seat_limit < 1` uchun aniq validatsiya qo'shildi (`User limiti kamida 1 bo'lishi kerak`)
    - create fallback xabari disambiguatsiya qilindi:
      - haqiqiy duplicate bo'lsa: `Bu kompaniya kodi band`
      - boshqa holatda: umumiy create xatosi
  - [frontend/src/app/api/super-admin/companies/[companyId]/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/super-admin/companies/[companyId]/route.ts):
    - `seat_limit` yangilash ham `>=1` ga moslashtirildi
  - [frontend/src/components/super-admin-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/super-admin-panel.tsx):
    - create forma `seat_limit` defaulti `1` qilindi
    - seat limit inputlarida `min=1` qo'yildi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: muvaffaqiyatli

#### 2026-05-07 - Super Admin kompaniya kartasi ichidagi click kartani yopib yuborish muammosi tuzatildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- [frontend/src/components/super-admin-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/super-admin-panel.tsx) ichida:
  - accordion toggle handler `details`dan `summary`ga ko'chirildi
  - endi kompaniya kartasi ochilgandan keyin ichki form/button/input bosilganda karta yopilib ketmaydi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: muvaffaqiyatli

#### 2026-05-07 - Claude UI bilan full frontend audit qilindi va Super Admin nozik farqlari moslandi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- `QA-Assistant (1)` ichidagi Claude UI manbalari (`QA-Assistant-v2.html`, `new_frontend`, `qa_ui_update`) bilan amaldagi `frontend/src` file-by-file solishtirildi.
- [frontend/src/components/super-admin-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/super-admin-panel.tsx) ichida screenshotga mos nozik vizual farqlar yopildi:
  - `AI Sozlamalar` tabida API key ko'rsatish/yashirish tugmalari `Show/Hide` matnidan eye ikonkalarga o'tkazildi
  - `Platform Admin` tab sarlavhasidagi ortiqcha source badge olib tashlandi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: ikkalasi ham muvaffaqiyatli

#### 2026-05-07 - Super Admin `Kompaniyalar` tabida accordion boshqaruv bloklari qayta tiklandi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- [frontend/src/components/super-admin-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/super-admin-panel.tsx) ichida:
  - kompaniya row ustiga bosilganda ochiladigan `details` oqimi qaytarildi
  - ochilganda quyidagi bo'limlar ishlaydi:
    - `Seat Limit va Status`
    - `Modullar`
    - `Billing`
    - `Kompaniyani o'chirish`
- [frontend/src/app/api/super-admin/companies/[companyId]/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/super-admin/companies/[companyId]/route.ts) ichida `modules` action whitelist kengaytirildi:
  - endi faqat paid addon emas, `MODULE_CATALOG`dagi barcha modullar saqlanadi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: ikkalasi ham muvaffaqiyatli o'tdi

#### 2026-05-07 - `Unknown internal RPC op: get_global_setting` xatosi tuzatildi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
  - Stage 10 - Reliability
- Root cause:
  - `Super Admin` overview route yangi `get_global_setting` RPC op chaqirayotgan edi
  - lekin [services/api/internal_rpc_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/internal_rpc_api.py) ichidagi whitelist `_OPERATIONS` da bu op yo'q edi
- Tuzatish:
  - `get_global_setting` import qilindi
  - `_OPERATIONS` mappingga `"get_global_setting": get_global_setting` qo'shildi
- Verification:
  - `./.venv/bin/python -m py_compile services/api/internal_rpc_api.py`
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: barchasi muvaffaqiyatli

#### 2026-05-07 - Super Admin tablar Claude screenshot oqimiga soddalashtirib moslandi

- Roadmap bog'lanishi:
  - Stage 9 - Product UX/UI
- [frontend/src/components/super-admin-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/super-admin-panel.tsx) qayta yozildi:
  - `Kompaniyalar` tabi endi faqat:
    - 4 ta statistik karta (`Jami`, `Faol`, `Jami users`, `Avg score`)
    - `+ Yangi kompaniya` tugmasi
    - sodda tenant ro'yxati
  - oldingi ortiqcha boshqaruv bloklari (seat/module/billing/delete accordion tafsilotlari) bu tabdan olib tashlandi
  - `Yangi kompaniya` alohida modal forma orqali ishlaydi
  - `AI Sozlamalar` tabi bitta card oqimiga keltirildi (`Gemini Model`, `Fallback Model`, `API Key 1/2`, `Key freeze`, `Saqlash`)
  - `Platform Admin` tabi ham soddalashtirildi (faqat parol yangilash formasi)
- AI tabdagi yangi maydonlar backend contractga qo'shildi:
  - [frontend/src/lib/types.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/types.ts) ichida `GlobalAiDefaults` kengaytirildi (`fallback_model`, `key_freeze_minutes`)
  - [frontend/src/app/api/super-admin/overview/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/super-admin/overview/route.ts) endi shu qiymatlarni ham qaytaradi
  - [frontend/src/app/api/super-admin/ai-defaults/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/super-admin/ai-defaults/route.ts) endi shu qiymatlarni saqlaydi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: ikkalasi ham muvaffaqiyatli o'tdi

#### 2026-05-07 - Super Admin UI Claude prototype’dagi tab ko‘rinishiga qayta moslandi

- Roadmap bog'lanishi:
  - Stage 9 — Product UX/UI
- [frontend/src/components/super-admin-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/super-admin-panel.tsx) ichida `Super Admin` sahifasi endi screenshot/prototype’dagi kabi 3 tab bilan ishlaydi:
  - `🏢 Kompaniyalar`
  - `🤖 AI Sozlamalar`
  - `🔐 Platform Admin`
- Root cause aniqligi:
  - aktiv frontendga oldin `qa_ui_update` ichidagi ishlaydigan `super-admin-panel.tsx` ulangan edi
  - u variant functional bo'lsa ham tabli prototype emas, balki bitta uzun unified page edi
  - foydalanuvchi yuborgan ko'rinish esa `QA-Assistant-v2.html` prototipidagi tabli super admin variantiga mos edi
- Functional behavior o'zgarmadi, faqat layout screenshotdagi UX oqimiga moslab qayta bo'lindi:
  - `Kompaniyalar` tabiga tenant yaratish va kompaniya/billing boshqaruvi
  - `AI Sozlamalar` tabiga global Gemini defaultlari
  - `Platform Admin` tabiga security, super admin password va audit loglar
- verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`
  - natija: ikkalasi ham muvaffaqiyatli o'tdi

#### 2026-05-07 - `start.sh` local run uchun qayta yozildi va self-healing startup qo'shildi

- Roadmap bog'lanishi:
  - Stage 0 — Foundation Audit
  - Stage 10 — Reliability / local operability
- [start.sh](/Users/mac/Documents/projects/JIRA-AI-Analyzer/start.sh) soddalashtirildi va local startup uchun quyidagilar qo'shildi:
  - `--check` preflight rejimi
  - Mac default `bash` bilan ishlashi uchun `mapfile`ga bog'liqlik olib tashlandi
  - `.env`dagi Windows pathlar local session uchun repo ichidagi `data/` va `models/` yo'llariga override qilinadi
  - `APP_DB_BACKEND=postgres` bo'lsa, Postgres ulanmasa mavjud `data/auth.db` va `data/processing.db` bilan avtomatik `sqlite` fallback qilinadi
  - backend ishga tushishidan oldin `init_auth_db()` va `init_db()` preflight orqali DB bootstrap qilinadi
  - `FORCE_RESTART_BACKEND=1` va `FORCE_RESTART_FRONTEND=1` bilan band portdagi local processni tozalab qayta ko'tarish mumkin
- [README.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/README.md) ichidagi startup izohlariga yangi local fallback qoidalari qo'shildi
- verification:
  - `bash -n start.sh`
  - `bash ./start.sh --check`
  - `bash ./start.sh`
  - natija: precheck o'tdi, local muhitda `postgres` ulanmaganda `sqlite` fallback ishladi; haqiqiy local verifikatsiyada backend tayyor bo'ldi va `Next.js` `http://localhost:3000` da ishga tushdi

#### 2026-05-07 - Keraksiz planning va integratsiya `.md` fayllar tozalandi

- Roadmap bog'lanishi:
  - Stage 0 — Foundation Audit
  - Stage 10 — Reliability / repo hygiene
- Asosiy source-of-truth hujjatlar saqlandi:
  - `AGENTS.md`
  - `README.md`
  - `ROADMAP_SAAS.md`
  - `PROGRESS_LOG.md`
  - `PERMISSION_MATRIX.md`
  - `DEPLOY_WEB.md`
- Bir martalik yoki vaqtinchalik planning/integration hujjatlar olib tashlandi:
  - `ARCHITECTURE_MIGRATION_STRATEGY.md`
  - `CURRENT_STATE_ARCHITECTURE.md`
  - `TARGET_ARCHITECTURE.md`
  - `NEXTJS_FRONTEND_MIGRATION_PLAN.md`
  - `POSTGRESQL_MIGRATION_PLAN.md`
  - `WEBHOOK_MONITORING_ADDON_PLAN.md`
  - `QA-Assistant (1)/INTEGRATION_GUIDE.md`
  - `database/postgresql/SETUP.md`
- [README.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/README.md) ichidagi broken linklar tozalandi va web portal bo'limi soddalashtirildi
- [database/postgresql/README.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/database/postgresql/README.md) ichiga minimal setup ma'lumoti ko'chirildi

#### 2026-05-07 - `start.sh` `.env` dagi ixtiyoriy key yo'qligida darrov yiqiladigan bug tuzatildi

- Roadmap bog'lanishi:
  - Stage 9 — Product UX/UI
  - Stage 10 — Reliability / local operability
- `start.sh` ichidagi `read_dotenv_value()` helper `set -euo pipefail` ostida `APP_WEBHOOK_EXECUTION_MODE` topilmasa butun scriptni `exit 1` qilayotgan edi
- Helper endi `.env` ichida key yo'q bo'lsa ham xavfsiz tarzda bo'sh qiymat qaytaradi va script default `inline` rejimga tushadi
- Natija:
  - `./start.sh` endi `APP_WEBHOOK_EXECUTION_MODE` `.env` ichida yozilmagan local muhitlarda ham darrov yiqilmaydi
  - local startup diagnostikasi keyingi bosqichlargacha yetib boradi
- Verification:
  - `bash -x ./start.sh`

#### 2026-05-07 - `QA-Assistant (1)` UI aktiv frontendga ishlaydigan holatda ulandi

- Roadmap bog'lanishi:
  - Stage 9 — Product UX/UI
- `QA-Assistant (1)/qa_ui_update` dagi loyiha-mos UI variant aktiv `frontend` bilan sinxron qilindi:
  - `frontend/src/components/app-shell.tsx`
  - `frontend/src/components/tzpr-checker.tsx`
  - `frontend/src/components/testcase-generator.tsx`
  - `frontend/src/app/(app)/monitoring/page.tsx`
  - `frontend/src/app/globals.css`
- Nimalar qilindi:
  - shell/sidebar/topbar ko'rinishi Claude bergan `QA-Assistant` variantiga qaytarildi
  - `TZ-PR Checker` va `Test Case Generator` ekranlari mavjud `/api/tzpr/analyze` va `/api/testcase/generate` oqimlariga UI o'zgartirmasdan qayta ulandi
  - monitoring sahifasi `getMonitoringSnapshot()` orqali ishlaydigan Tailwind/shadcn variantiga moslandi
  - global background va visual layerlar `QA-Assistant` dizayniga yaqinlashtirildi
- Cheklovlar:
  - `QA-Assistant (1)/qa_ui_update` paketida `team/company-admin` uchun alohida yangi UI varianti yo'q, shu sabab `Team` sahifasi hozirgi loyiha versiyasida qoldi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`

#### 2026-05-06 - Frontendning asosiy sahifalari Tailwind/shadcn utility-first layoutga ko'chirildi

- `frontend/src/components/ui/` ichiga yuqori darajali layout primitive'lar qo'shildi:
  - `page-intro.tsx`
  - `metric-card.tsx`
  - `section-header.tsx`
  - `status-pill.tsx`
- Quyidagi sahifalar va komponentlarda utility-first layout joriy qilindi:
  - `frontend/src/components/app-shell.tsx`
  - `frontend/src/app/page.tsx`
  - `frontend/src/app/login/page.tsx`
  - `frontend/src/components/login-form.tsx`
  - `frontend/src/app/(app)/dashboard/page.tsx`
  - `frontend/src/app/(app)/monitoring/page.tsx`
  - `frontend/src/components/settings-panel.tsx`
  - `frontend/src/components/tzpr-checker.tsx`
  - `frontend/src/components/testcase-generator.tsx`
  - `frontend/src/components/company-admin-panel.tsx`
  - `frontend/src/components/super-admin-panel.tsx`
  - `frontend/src/components/pr-details-stack.tsx`
- Natija:
  - landing, auth, shell, dashboard, monitoring va tool sahifalarida inline Tailwind layout ustun bo'ldi
  - reusable section/metric/status patternlar paydo bo'ldi
  - `Tailwind + shadcn` foundation endi real product ekranlarida ishlay boshladi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`

#### 2026-05-06 - Tailwind CSS v4 va shadcn-compatible foundation frontendga qo'shildi

- `frontend/package.json` ichiga yangi UI foundation dependency'lari o'rnatildi:
  - `tailwindcss`
  - `@tailwindcss/postcss`
  - `postcss`
  - `class-variance-authority`
  - `clsx`
  - `tailwind-merge`
  - `lucide-react`
  - `@radix-ui/react-slot`
- Tailwind/shadcn setup fayllari qo'shildi:
  - `frontend/postcss.config.mjs`
  - `frontend/components.json`
  - `frontend/src/lib/utils.ts`
- `frontend/src/lib/cn.ts` endi `clsx + tailwind-merge` orqali ishlaydi
- `frontend/src/app/globals.css` ichiga Tailwind import va semantic theme token mapping qo'shildi
- Reusable primitive'lar Tailwind/shadcn uslubiga o'tkazildi:
  - `frontend/src/components/ui/button.tsx`
  - `frontend/src/components/ui/card.tsx`
  - `frontend/src/components/ui/input.tsx`
  - `frontend/src/components/ui/textarea.tsx`
  - `frontend/src/components/ui/select.tsx`
  - `frontend/src/components/ui/badge.tsx`
  - `frontend/src/components/ui/field.tsx`
  - `frontend/src/components/ui/notice.tsx`
- `frontend/src/components/app-shell.tsx` ichida `Lucide` iconlar bilan nav birinchi bosqichda polish qilindi
- Natija:
  - yangi komponentlar endi `Tailwind + shadcn` yo'liga mos foundation bilan yoziladi
  - eski sahifalarni asta-sekin utility classlarga ko'chirish uchun tayyor baza hosil bo'ldi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`

#### 2026-05-06 - Portal UI clean enterprise yo'nalishida qayta yig'ildi

- `frontend/src/app/globals.css` ichida portalning umumiy vizual tili qayta ishlatildi:
  - iliq/bej dekorativ theme o'rniga neytral enterprise palette joriy qilindi
  - card, button, badge, notice, table va details bloklarining surface/border/shadowlari soddalashtirildi
  - sidebar, topbar, stat-card va filter ko'rinishlari product UX tomonga tozalandi
- Foydalanuvchiga ko'rinadigan copy migration tilidan product tiliga o'tkazildi:
  - `frontend/src/app/page.tsx`
  - `frontend/src/app/login/page.tsx`
  - `frontend/src/components/login-form.tsx`
  - `frontend/src/components/app-shell.tsx`
  - `frontend/src/app/(app)/dashboard/page.tsx`
  - `frontend/src/components/settings-panel.tsx`
  - `frontend/src/components/tzpr-checker.tsx`
  - `frontend/src/components/testcase-generator.tsx`
  - `frontend/src/components/company-admin-panel.tsx`
  - `frontend/src/components/super-admin-panel.tsx`
  - `frontend/src/app/(app)/monitoring/page.tsx`
- Access denied sahifalari ham yangi `Card` primitive bilan bir xil ko'rinishga keltirildi:
  - `frontend/src/app/(app)/team/page.tsx`
  - `frontend/src/app/(app)/tzpr/page.tsx`
  - `frontend/src/app/(app)/testcase/page.tsx`
- Metadata ham yangilandi:
  - `frontend/src/app/layout.tsx`
- Natija:
  - portal ko'rinishi ancha toza va tushunarli bo'ldi
  - foydalanuvchi ko'radigan sahifalarda texnik/migration jargon kamaydi
  - admin, monitoring va quality-tool sahifalari bir xil product uslubga yaqinlashdi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`

#### 2026-05-06 - Team va Super Admin formalarining qolgan qismi UI primitive systemga ko'chirildi

- `frontend/src/components/company-admin-panel.tsx` ichidagi qolgan user management formalar primitive’larga o'tkazildi:
  - user create
  - password update
  - reset token action
  - delete confirm action
- `frontend/src/components/super-admin-panel.tsx` ichidagi qolgan platform formalar primitive’larga o'tkazildi:
  - AI defaults
  - create company
  - platform admin password
  - seat limit / status
  - addon modules
  - billing / subscription
  - company delete confirm
- Yangi UI primitive’lar bu sahifalarda ham standart qatlamga aylandi:
  - `Card`
  - `Badge`
  - `Button`
  - `Field`
  - `Input`
  - `Select`
  - `Textarea`
  - `Notice`
- Natija:
  - admin va company admin formalar ham bitta reusable UI bazaga o'tdi
  - eski `primary-button`, `ghost-button`, `field`, `pill`, `notice` patternlari admin formalarda deyarli qolmadi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`

#### 2026-05-06 - Core product sahifalari reusable UI primitive’larga ko'chirildi

- `Settings`, `TZ-PR Checker`, `Test Case Generator` va `Monitoring` sahifalarida asosiy UI elementlar yangi primitive systemga o'tkazildi:
  - `frontend/src/components/settings-panel.tsx`
  - `frontend/src/components/tzpr-checker.tsx`
  - `frontend/src/components/testcase-generator.tsx`
  - `frontend/src/app/(app)/monitoring/page.tsx`
- `frontend/src/components/pr-details-stack.tsx` ham yangi `Badge` primitive bilan moslashtirildi
- Qaysi elementlar ko'chdi:
  - `Card`
  - `Badge`
  - `Button`
  - `Field`
  - `Input`
  - `Textarea`
  - `Notice`
- Natija:
  - customer-facing asosiy modullar endi bir xil UI bazadan foydalanadi
  - form/action/result/error patternlari turli sahifalarda bir xilroq bo'ldi
  - keyingi admin sahifalarni migrate qilish osonlashdi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`

#### 2026-05-06 - Reusable UI primitive qatlam qo'shildi

- `frontend/src/components/ui/` ichida bazaviy komponentlar yaratildi:
  - `button.tsx`
  - `input.tsx`
  - `textarea.tsx`
  - `select.tsx`
  - `card.tsx`
  - `badge.tsx`
  - `notice.tsx`
  - `field.tsx`
- `frontend/src/lib/cn.ts` qo'shilib, className birlashtirish uchun yengil helper yaratildi
- `frontend/src/app/globals.css` ichida reusable `ui-*` classlar qo'shildi:
  - `ui-button`
  - `ui-input`
  - `ui-select`
  - `ui-textarea`
  - `ui-card`
  - `ui-badge`
  - `ui-notice`
- yangi primitive’lar birinchi real sahifalarda ishlatila boshladi:
  - `frontend/src/components/login-form.tsx`
  - `frontend/src/components/app-shell.tsx`
  - `frontend/src/app/page.tsx`
  - `frontend/src/app/(app)/dashboard/page.tsx`
- Natija:
  - button/input/card/badge/notice endi bitta source orqali boshqariladi
  - keyingi sahifalarni bir xil UI systemga ko'chirish ancha soddalashdi
- Verification:
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run build`

#### 2026-05-06 - UI Foundation va app shell birinchi polish bosqichi yakunlandi

- `frontend/src/app/globals.css` ichida global visual foundation yangilandi:
  - rang tokenlari, radius, shadow va background layerlari tizimli qilindi
  - input/button/focus/notice holatlari bir xil uslubga keltirildi
  - panel, card, stats, table va details komponentlari uchun common visual language mustahkamlandi
- `frontend/src/components/app-shell.tsx` product shell sifatida qayta ishlatildi:
  - sidebar navigatsiyasi `Workspace` va `Administration` bo'limlariga ajratildi
  - nav item'lar endi qisqa description bilan ko'rinadi
  - topbar sahifa kontekstini, role va active module ma'lumotini aniqroq ko'rsatadi
  - sessiya scope va tenant summary shell ichiga olib chiqildi
- landing va auth first impression yaxshilandi:
  - `frontend/src/app/page.tsx`
  - `frontend/src/app/login/page.tsx`
  - login yoniga product scope va runtime haqida qisqa spotlight qo'shildi
- `frontend/src/app/(app)/dashboard/page.tsx` haqiqiy workspace ko'rinishiga yaqinlashtirildi:
  - hero summary
  - quick access card'lar
  - session/backend/module overview bloklari
- Verification:
  - `cd frontend && npm run build`
  - `cd frontend && npm run typecheck`

#### 2026-05-06 - Worker/queue boundary ajratildi va production deploy stack kengaytirildi

- `Roadmap 5. Async Processing / Worker Boundary` va deploy tayyorgarligi bo'yicha yangi DB-backed queue qatlami qo'shildi:
  - `utils/database/job_queue_repository.py`
  - `job_queue` va `job_runs` jadvallari `sqlite` va `postgres` uchun bir xil contract bilan yaratildi
  - webhook/manual triggerlar uchun `enqueue`, worker uchun `claim`, `done/retry/failed` lifecycle helperlar qo'shildi
- `services/worker/main.py` bilan alohida worker runtime qo'shildi:
  - `run_task_group`
  - `run_checker_only`
  - `run_testcase_generation`
  - `retry_blocked_task`
  - `manual_check`
  job turlarini mavjud business logic bilan bajaradi
- `services/webhook/jira_webhook_handler.py` `inline|queue` execution mode bilan kengaytirildi:
  - `APP_WEBHOOK_EXECUTION_MODE=queue` bo'lsa webhooklar ishni darhol bajarish o'rniga DB navbatga yozadi
  - `/health` ichiga queue snapshot qo'shildi
  - `manual check` va `manual testcase` endpointlari ham queue-aware bo'ldi
- `start.sh` va `start.bat` queue rejimida worker'ni avtomatik ko'taradigan qilindi
- `docker-compose.yml` productionga yaqin 4-servis stackka o'tdi:
  - `postgres`
  - `backend`
  - `worker`
  - `frontend`
  - compose ichida `backend` va `worker` `postgres` DSN bilan ishlaydi
- deploy/env hujjatlari yangilandi:
  - `DEPLOY_WEB.md`
  - `.env.example`
  - `README.md`
  - `frontend/README.md`
- Verification:
  - `python -m py_compile services/webhook/jira_webhook_handler.py services/worker/main.py utils/database/job_queue_repository.py utils/database/task_db.py tests/conftest.py`
  - `bash -n start.sh`
  - `./.venv/bin/pytest -q tests/test_job_queue.py`
  - `./.venv/bin/pytest -q tests/test_session_scope.py`

#### 2026-05-06 - PostgreSQL primary runtime qilindi va tenant-safe API gate qo'shildi

- `Roadmap 3. Data Layer Migration` va `Roadmap 4. Multi-Tenant Isolation` bo'yicha asosiy runtime `PostgreSQL`ga o'tkazildi:
  - `.env` va `.env.example` defaulti `APP_DB_BACKEND=postgres` bo'ldi
  - `utils/database/runtime.py` endi `PostgreSQL`ni primary, `SQLite`ni backup sifatida hujjatlashtiradi
- auth/session qatlamidagi Postgres compatibility yopildi:
  - timezone-aware `web_sessions`, `login_attempts`, `password_reset_tokens` datetime ishlovi to'g'rilandi
  - `platform_admins`, `user_password_reset_tokens`, `web_sessions` jadvallari Postgres runtime bootstrapga qo'shildi
- repository qatlamidagi schema driftlar yopildi:
  - `subscriptions` va `company_subscriptions` fallbacki
  - `company_settings` yo'q bo'lsa `company_integrations` / `company_module_access` / `company_webhook_settings` dan rekonstruksiya
  - encrypted `user_credentials` columnlari bilan legacy field mapping
  - `task_status_history.company_id` yozuvi va Postgres-compatible monitoring boolean querylari
- backend endpointlar endi sessiya va tenant scope bilan himoyalandi:
  - `settings`, `monitoring`, `tzpr`, `testcase`, `auth/company-modules`, `internal-rpc`
  - `company_admin` endi boshqa tenant `company_id` bilan backend chaqira olmaydi
  - `internal-rpc` operationlarida role-based gate qo'shildi
- `Next.js` backend client avtomatik `X-Session-ID` yuboradigan bo'ldi, shu sabab BFF route'lar backendning yangi scope tekshiruvlari bilan mos ishlaydi
- Verification:
  - `python -m py_compile` relevant backend modullar uchun o'tdi
  - `cd frontend && npm run typecheck` o'tdi
  - in-process `FastAPI TestClient` smoke test `APP_DB_BACKEND=postgres` bilan o'tdi:
    - `jasur@gws` login/session/settings/monitoring/internal-rpc `200`
    - tenant mismatch chaqiriqlari `403`
    - `super_admin` monitoring va internal-rpc `200`

#### 2026-05-05 - Streamlit runtime va legacy UI qatlamlari kodbasedan chiqarildi

- `start.sh` va `start.bat` web-only qilindi:
  - endi faqat `Next.js + FastAPI` startup yo'li qoldi
  - `--streamlit` fallback olib tashlandi
- `app.py` va `ui/` legacy source qatlamlari olib tashlandi
- `utils/auth/auth_manager.py` endi `streamlit` paketini import qilmaydi:
  - ichki yengil session adapter bilan ishlaydi
  - backend auth route'lar uchun dependency qoldig'i yopildi
- yangi shared UI constantlar moduli qo'shildi:
  - `config/ui_foundation.py`
  - testlar shu foundationga ko'chirildi
- `requirements.txt` dan `streamlit` olib tashlandi
- `README.md`, `frontend/README.md`, `DEPLOY_WEB.md`, `CURRENT_STATE_ARCHITECTURE.md`, `NEXTJS_FRONTEND_MIGRATION_PLAN.md` web-only holatga yangilandi
- Natija:
  - kodbase darajasida primary va legacy `Streamlit` runtime qolmadi
  - asosiy UI qatlami endi faqat `Next.js`
- Verification:
  - `bash -n start.sh`
  - `npm run build`
  - `npm run typecheck`
  - `python -m py_compile utils/auth/auth_manager.py`

#### 2026-05-05 - Super Admin ham Next.js web portalga ko'chirildi

- yangi `super_admin` API route'lari qo'shildi:
  - `frontend/src/app/api/super-admin/overview/route.ts`
  - `frontend/src/app/api/super-admin/companies/route.ts`
  - `frontend/src/app/api/super-admin/companies/[companyId]/route.ts`
  - `frontend/src/app/api/super-admin/ai-defaults/route.ts`
  - `frontend/src/app/api/super-admin/platform-admin/password/route.ts`
- yangi `super admin` web UI qo'shildi:
  - `frontend/src/app/(app)/admin/page.tsx`
  - `frontend/src/components/super-admin-panel.tsx`
- `frontend/src/components/app-shell.tsx`, login redirectlari va root redirectlar role-aware qilindi:
  - `super_admin` endi `/admin` ga tushadi
  - customer rolelar dashboardga tushadi
- Natija:
  - kompaniya yaratish
  - company status / seat limit
  - addon module boshqaruvi
  - manual billing / subscription boshqaruvi
  - global AI defaults
  - DB-based platform admin password update
  - login audit ko'rinishi
  endi `Next.js` ichida ishlaydi
- Verification:
  - `npm run build`
  - `npm run typecheck`

#### 2026-05-05 - Web-first startup va deploy packaging qo'shildi

- `start.sh` endi default holatda `Next.js + FastAPI` portalni ko'taradi
- legacy fallback uchun `./start.sh --streamlit` qo'shildi
- `app.py` ichida handoff qatlami kengaytirildi:
  - endi `super_admin` sessiyasi ham web portalga yo'naltiriladi
  - `APP_CUSTOMER_UI_MODE` default `nextjs` bo'ldi
- deploy fayllari qo'shildi:
  - `frontend/Dockerfile`
  - `Dockerfile.backend`
  - `docker-compose.yml`
  - `.dockerignore`
  - `frontend/.dockerignore`
  - `DEPLOY_WEB.md`
- `frontend/next.config.ts` `standalone` outputga o'tkazildi
- Verification:
  - `./.venv/bin/python -m py_compile app.py`
  - `bash -n start.sh`
  - `npm run build`
  - `npm run typecheck`

#### 2026-05-05 - Next.js frontend dependency, typecheck va production build tayyorlandi

- `frontend` ichida `npm install` bajarildi va `package-lock.json` yaratildi
- `frontend/tsconfig.json` releasega moslashtirildi:
  - `ignoreDeprecations` qo'shildi
  - `Next.js` auto-config qilgan `jsx` va `.next/dev/types` include'lari saqlandi
- `frontend/src/app/layout.tsx` va `frontend/src/app/globals.css` yangilandi:
  - Google Fonts olib tashlandi
  - local/offline-safe font stack ishlatiladigan qilindi
- Verification:
  - `npm run typecheck`
  - `npm run build`
- Qo'shimcha kuzatuv:
  - `./start.sh --web` startup oqimi sandbox ichida port bind cheklovi sabab to'liq smoke-test bo'lmadi
  - build va startup skriptning o'zi tayyor, real local muhitda ishga tushirish kerak

#### 2026-05-05 - Streamlit customer handoff va web startup rejimi qo'shildi

- `app.py` ichiga customer handoff qatlami qo'shildi:
  - `APP_CUSTOMER_UI_MODE=nextjs|web` bo'lsa `user` va `company_admin` roli `Next.js` portalga yo'naltiriladi
  - `APP_CUSTOMER_WEB_URL` orqali customer portal manzili boshqariladi
  - `APP_ALLOW_STREAMLIT_CUSTOMER_FALLBACK=true` bilan vaqtinchalik legacy fallback qoldirish mumkin
- `start.sh` kengaytirildi:
  - `./start.sh --web` rejimi qo'shildi
  - `Next.js` customer portalni backend bilan birga ko'taradi
  - `Streamlit` rejimida ham customer portal URL env'i uzatiladi
- `README.md`, `frontend/README.md` va [NEXTJS_FRONTEND_MIGRATION_PLAN.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/NEXTJS_FRONTEND_MIGRATION_PLAN.md) startup va handoff oqimlariga mos yangilandi
- Natija:
  - customer traffic'ni `Streamlit`dan ajratish uchun releasega yaqin handoff rejimi tayyor bo'ldi
  - endi customer web uchun alohida startup yo'li mavjud
  - keyingi asosiy texnik blok frontend dependency/build tekshiruvi bo'lib qoldi
- Verification:
  - `./.venv/bin/python -m py_compile app.py`
  - `bash -n start.sh`

#### 2026-05-05 - Next.js Company Admin team management sahifasi real flow bilan ishlay boshladi

- `frontend/src/app/api/company-admin/*` route'lari qo'shildi:
  - team overview
  - user create
  - user status toggle
  - password update
  - reset token yaratish
  - user delete
- `frontend/src/lib/backend.ts` ichiga generic `callInternalRpc()` helper qo'shildi
- `frontend/src/components/company-admin-panel.tsx` va `frontend/src/app/(app)/team/page.tsx` qo'shildi:
  - kompaniya userlarini ko'rish
  - yangi user qo'shish
  - userni faollashtirish/nofaollashtirish
  - parolni yangilash
  - reset token yaratish
  - oddiy userni o'chirish
- `frontend/src/components/app-shell.tsx` navigatsiyasi yangilanib, `company_admin` uchun `Team` route qo'shildi
- `frontend/src/app/globals.css` team management kartalari va action layoutlari bilan kengaytirildi
- Natija:
  - customer web ichida yana bir katta admin slice `Next.js`ga ko'chdi
  - `Company Admin` kundalik user boshqaruvi endi `Next.js -> Next API route -> FastAPI internal RPC` zanjirida ishlaydi
  - `Streamlit`ga qaram customer/admin surface yana qisqardi
- Verification:
  - internal RPC tayanchi mavjudligi va kerakli ops lar tekshirildi
  - `npm install` va `next build/typecheck` hali yugurtirilmadi

#### 2026-05-05 - Next.js Settings sahifasi real customer API keys flow bilan ishlay boshladi

- `frontend/src/app/api/settings/shared/route.ts` qo'shildi:
  - sessiyadan user/company scope ni aniqlaydi
  - backend settings API bilan gaplashadi
  - browserga faqat sanitizatsiya qilingan settings view qaytaradi
  - save vaqtida role-based allowed fieldlarni saqlaydi
- `frontend/src/lib/types.ts` va `frontend/src/lib/backend.ts` ichiga settings contract/helperlar qo'shildi
- `frontend/src/components/settings-panel.tsx` qo'shildi:
  - `company_admin` uchun kompaniya `JIRA/GitHub/Gemini` kalitlarini o'qish va saqlash
  - oddiy `user` uchun shaxsiy `Gemini` kalitlari va modelini boshqarish
  - integration status va module access ko'rinishi
- `frontend/src/app/(app)/settings/page.tsx` endi shell emas, haqiqiy settings panelni render qiladi
- `frontend/src/app/globals.css` settings form/layout state'lari bilan kengaytirildi
- Natija:
  - customer web ichida to'rtinchi real feature slice ishlay boshladi
  - `Settings`ning customer-facing qismi `Next.js -> Next API route -> FastAPI` zanjiriga o'tdi
  - `Streamlit`dagi `Unified Settings`dan customer uchun kerakli API keys oqimi ajralib chiqdi
- Verification:
  - settings route contracti va role-based field scope qo'lda audit qilindi
  - `npm install` va `next build/typecheck` hali yugurtirilmadi

#### 2026-05-05 - Next.js Test Case Generator sahifasi real generate flow bilan ishlay boshladi

- `frontend/src/app/api/testcase/generate/route.ts` qo'shildi:
  - frontend sessiyasini tekshiradi
  - role va `testcase_generator` module accessini tekshiradi
  - requestni backend `/api/testcase/generate` endpointiga scoped payload bilan uzatadi
- `frontend/src/lib/types.ts` va `frontend/src/lib/backend.ts` ichiga testcase generation uchun typed contract/helperlar qo'shildi
- `frontend/src/app/(app)/testcase/page.tsx` va `frontend/src/components/testcase-generator.tsx` qo'shildi:
  - task key yuborish
  - optional custom context berish
  - default `positive` va `negative` test type flowini yuborish
  - generated testcase, overview, TZ va PR tafsilotlarini ko'rsatish
- `frontend/src/components/pr-details-stack.tsx` qo'shildi va `TZ-PR` ham shu shared PR/code details komponentiga o'tkazildi
- `frontend/src/components/app-shell.tsx` navigatsiyasi yangilanib, `Test Case Generator` yangi customer web route sifatida qo'shildi
- Natija:
  - customer web ichida uchinchi real feature slice ishlay boshladi
  - `Next.js -> Next API route -> FastAPI -> TestCaseGeneratorService` zanjiri tayyor bo'ldi
  - `Streamlit`ga qaram bo'lmagan customer functionality yana kengaydi
- Verification:
  - testcase backend route contracti va frontend access oqimi qo'lda audit qilindi
  - `npm install` va `next build/typecheck` hali yugurtirilmadi

#### 2026-05-05 - Next.js TZ-PR Checker sahifasi real analyze flow bilan ishlay boshladi

- `frontend/src/app/api/tzpr/analyze/route.ts` qo'shildi:
  - frontend sessiyasini tekshiradi
  - role va `tz_pr_checker` module accessini tekshiradi
  - requestni backend `/api/tzpr/analyze` endpointiga scoped payload bilan uzatadi
- `frontend/src/lib/types.ts` ichiga TZ-PR natijalari uchun typed modellari qo'shildi
- `frontend/src/lib/backend.ts` ichiga `analyzeTzprWithBackend()` helper qo'shildi
- `frontend/src/app/(app)/tzpr/page.tsx` va `frontend/src/components/tzpr-checker.tsx` qo'shildi:
  - task key yuborish
  - AI analysis, compliance, warning, figma summary va PR tafsilotlarini ko'rsatish
  - smart patch/default analyze rejimi saqlab qolindi
- `frontend/src/components/app-shell.tsx` navigatsiyasi yangilanib, `TZ-PR Checker` yangi customer web route sifatida qo'shildi
- `frontend/src/app/globals.css` ichiga result/details/code preview stillari qo'shildi
- Natija:
  - `Monitoring`dan keyin ikkinchi real customer feature slice `Next.js`ga ko'chdi
  - browser endi `Next.js -> Next API route -> FastAPI -> TZPRService` zanjiri orqali ishlaydi
  - `Streamlit`siz ishlaydigan customer flow maydoni kengaydi
- Verification:
  - frontend route/access oqimi va backend contract qo'lda audit qilindi
  - `npm install` va `next build/typecheck` hali yugurtirilmadi

#### 2026-05-05 - Next.js monitoring sahifasi real backend snapshot bilan ishlay boshladi

- `frontend/src/lib/types.ts` ichiga monitoring uchun typed response modellari qo'shildi
- `frontend/src/lib/backend.ts` ichiga `getMonitoringSnapshot()` helper qo'shildi
- `frontend/src/app/(app)/monitoring/page.tsx` placeholder holatdan chiqarildi:
  - backend snapshot o'qiydi
  - role bo'yicha access tekshiradi
  - `company_admin` uchun sessiyadagi `company_id` bilan scope qo'llaydi
  - status filter, recent tasks, error log va blocked queue ni render qiladi
- `frontend/src/app/globals.css` ichiga monitoring cards/table/filter UI stillari qo'shildi
- Natija:
  - `Next.js` customer web ichida birinchi real feature page paydo bo'ldi
  - `Monitoring` endi faqat shell emas, backenddagi haqiqiy ma'lumotlarni ko'rsatadi
  - keyingi feature migratsiyalari uchun page pattern tayyor bo'ldi
- Verification:
  - monitoring backend response shape'i va frontend render contracti qo'lda audit qilindi
  - `npm install` va `next build/typecheck` hali yugurtirilmadi

#### 2026-05-05 - Next.js auth contract hardening boshlandi

- `FastAPI` auth API kengaytirildi:
  - `/api/auth/login` endi backend-managed `session_token` qaytaradi
  - `/api/auth/me` qo'shildi
  - `/api/auth/logout` qo'shildi
- Auth schema/bootstrap qatlamiga `web_sessions` migration qo'shildi
- `utils/auth/auth_db.py` ichiga web session helperlar qo'shildi:
  - session yaratish
  - sessionni olish va touch qilish
  - sessionni revoke qilish
- `frontend/src/lib/session.ts` endi auth payloadni to'g'ridan-to'g'ri saqlamaydi; faqat backend session tokenni `httpOnly` cookie orqali ushlaydi
- `frontend/src/lib/backend.ts` ichiga backend session resolve/logout requestlari qo'shildi
- `frontend/src/app/api/auth/login|me|logout` route'lari yangi backend session contractga o'tkazildi
- Natija:
  - `Next.js` auth endi vaqtinchalik local session dump emas
  - session holati backend tomonidan boshqariladi
  - protected sahifalar sessiyani backend orqali validatsiya qiladi

#### 2026-05-05 - Next.js customer frontend migration boshlandi

- [NEXTJS_FRONTEND_MIGRATION_PLAN.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/NEXTJS_FRONTEND_MIGRATION_PLAN.md) qo'shildi va full migration bosqichlari hujjatlashtirildi
- Repo ichida yangi `frontend/` Next.js skeleton yaratildi:
  - `package.json`
  - `tsconfig.json`
  - `next.config.ts`
  - `src/app` App Router tuzilmasi
- Transitional frontend foundation qo'shildi:
  - `frontend/src/lib/backend.ts` — FastAPI bilan typed fetch layer
  - `frontend/src/lib/session.ts` — session bridge
  - `frontend/src/lib/types.ts` — auth/session/backend tiplar
- Minimal customer-facing sahifalar qo'shildi:
  - `frontend/src/app/login/page.tsx`
  - `frontend/src/app/(app)/dashboard/page.tsx`
  - `frontend/src/app/(app)/settings/page.tsx`
  - `frontend/src/app/(app)/monitoring/page.tsx`
- Next route handlers qo'shildi:
  - `frontend/src/app/api/auth/login/route.ts`
  - `frontend/src/app/api/auth/logout/route.ts`
- Natija:
  - repo ichida `Streamlit`dan mustaqil customer web kod bazasi paydo bo'ldi
  - login `FastAPI` auth endpointiga ulanadigan bridge tayyor
  - keyingi bosqichlarda feature-by-feature port qilish uchun app shell tayyor
- Verification:
  - `package.json` va `tsconfig.json` JSON parse tekshiruvi o'tkaziladi
  - frontend file structure yaratildi va route/layout skeleton tayyorlandi
- Bu o'zgarish [ROADMAP_SAAS.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ROADMAP_SAAS.md) dagi `2. Target Architecture`, `5. Authentication va Authorization` hamda `9. Product UX/UI` bosqichlariga mos

#### 2026-05-05 - Frontend/backend split qattiqlashtirildi: active Streamlit flowlar endi backend qatlamini bevosita import qilmaydi

- `services/api/internal_rpc_api.py` qo'shilib, qolgan admin/setup/settings oqimlari uchun whitelisted internal RPC boundary yaratildi
- `ui/backend_proxy.py`, `ui/session_auth.py`, `ui/constants.py`, `ui/secret_utils.py` orqali frontend uchun alohida proxy/session/helper qatlamlari ajratildi
- Active Streamlit sahifalarining backend bilan bog'lanishi tozalandi:
  - `login`, `monitoring`, `api_setup`, `company_admin`, `super_admin`, `sidebar`, `unified_settings`, `TZ-PR Checker`, `Test Case Generator`
  - bu sahifalar endi `utils.auth.*`, `utils.database.*`, `services.*` persistence/service qatlamlarini to'g'ridan-to'g'ri import qilmaydi
- `Monitoring` UI endi to'liq backend API orqali ishlaydi; backendga `source-info` endpoint qo'shildi va task delete/check oqimi ham API orqali qattiqlashtirildi
- `TZ-PR Checker` va `Test Case Generator` UI endi natijani frontend-side lightweight objectga yig'adi; direct service fallback yo'li olib tashlandi
- `Unified Settings` ichidagi company/webhook/module save oqimlari va inline auth/db importlar proxy/session qatlamiga ko'chirildi
- `ui/components.py` va secret input helperlar ham yengillashtirildi, shuning bilan oddiy UI importlar backend resurslarini tepadan tortib kelmaydigan bo'ldi
- Natija:
  - faol sotuv scope oqimlari uchun frontend va backend orasida aniq API boundary mavjud
  - Streamlit endi amalda frontend rolida, `FastAPI` esa backend boundary rolida ishlaydi
  - eski `Bug Analyzer` va `Sprint Report` kodlari repo ichida qolgan, lekin hozirgi sotuv scope va route'larda aktiv emas
- Verification:
  - `./.venv/bin/python -m py_compile ...` muvaffaqiyatli o'tdi
  - active frontend modullarining import smoke-check'i o'tdi (`imports-ok`)
- Bu o'zgarish [ROADMAP_SAAS.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ROADMAP_SAAS.md) dagi `2. Target Architecture`, `4. Multi-Tenant Isolation`, `5. Authentication va Authorization`, `6. Secret Management va Security` hamda `9. Product UX/UI` bosqichlariga mos

#### 2026-05-05 - Local backend auto-start qo'shildi

- `ui/api_client.py` yangilanib, `127.0.0.1/localhost` backend URL ishlatilganda `FastAPI` backend avtomatik ko'tarishga urinadigan qilindi
- Auto-start `uvicorn services.webhook.jira_webhook_handler:app` orqali ishga tushadi va loglar `logs/backend_api.log` ga yoziladi
- Backend bind host endi `APP_BACKEND_API_BIND_HOST` orqali boshqariladi; default `0.0.0.0`
- `README.md` ishga tushirish bo'limi ham yangilandi: split arxitektura uchun backend + frontend startup aniq ko'rsatildi

#### 2026-05-05 - macOS/Linux uchun `start.sh` qo'shildi

- Yangi [start.sh](/Users/mac/Documents/projects/JIRA-AI-Analyzer/start.sh:1) qo'shildi
- Script:
  - `.venv` va `.env` ni tekshiradi
  - backend portini tekshiradi
  - kerak bo'lsa `FastAPI` backend'ni `nohup` bilan ko'taradi
  - `APP_USE_BACKEND_API=true` bilan `Streamlit` frontendni ishga tushiradi
  - backend logini `logs/backend_api.log` ga yozadi
  - frontend yopilganda, script o'zi ko'targan backendni ham tozalab yopadi

#### 2026-05-05 - Frontend/backend split yakunlandi: auth, TZ-PR va Testcase flowlari ham API-first qilindi

- `utils/auth/auth_manager.py` refactor qilinib, auth tekshiruv logikasi `authenticate_credentials()` va `apply_auth_session()` ko'rinishida ajratildi
- `services/api/auth_api.py` qo'shildi:
  - `/api/auth/login`
  - `/api/auth/password-reset`
  - `/api/auth/company-modules`
- `services/api/tzpr_api.py` qo'shildi va `TZPRService.analyze_task()` uchun backend endpoint ochildi
- `services/api/testcase_api.py` qo'shildi va `TestCaseGeneratorService.generate_test_cases()` uchun backend endpoint ochildi
- `services/webhook/jira_webhook_handler.py` ichiga auth, tz-pr va testcase routerlari ulab qo'yildi
- `ui/api_client.py` ichiga yangi feature flag helperlar qo'shildi:
  - `APP_USE_AUTH_API`
  - `APP_USE_TZPR_API`
  - `APP_USE_TESTCASE_API`
- `ui/pages/login.py` endi auth API yoqilganda login va password reset oqimlarini backend orqali bajaradi; muvaffaqiyatli login bo'lsa Streamlit session backend qaytargan auth payload bilan tiklanadi
- `ui/pages/tz_pr_checker.py` endi API mode'da `FastAPI` orqali tahlil yuboradi va natijani mavjud `TZPRAnalysisResult` obyektiga qayta yig'adi
- `ui/pages/testcase_generator.py` endi API mode'da `FastAPI` orqali generatsiya yuboradi va natijani mavjud `TestCaseGenerationResult`/`TestCase` obyektlariga qayta yig'adi
- `app.py` ichidagi company modules yuklash oqimi ham auth API mode bo'lsa backend orqali ishlaydi
- Natija: asosiy customer-facing flowlar (`login`, `monitoring`, `settings api keys`, `TZ-PR`, `testcase`) endi API-first boundary orqali yurishi mumkin; API o'chirilgan holatda eski direct fallback saqlanib qoldi
- Verification:
  - `./.venv/bin/python -m py_compile ...` muvaffaqiyatli o'tdi
  - auth/tzpr/testcase router prefix importlari tekshirildi
  - `authenticate_credentials` helper import/smoke check qilindi
- Bu o'zgarish [ROADMAP_SAAS.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ROADMAP_SAAS.md) dagi `2. Target Architecture`, `4. Multi-Tenant Isolation`, `5. Authentication va Authorization`, `6. Secret Management va Security` hamda `9. Product UX/UI` bosqichlariga mos

#### 2026-05-05 - Frontend/backend split davom etdi: Unified Settings API keys oqimi API slice sifatida ajratildi

- `services/api/settings_api.py` qo'shildi va `Unified Settings` ichidagi API kalitlar uchun ichki `FastAPI` endpointlar yaratildi:
  - shared/company API keys o'qish
  - shared/company API keys saqlash
  - webhook API keys o'qish
  - webhook API keys saqlash
- `services/webhook/jira_webhook_handler.py` ichiga settings router ulab qo'yildi
- `ui/api_client.py` ichiga `APP_USE_SETTINGS_API` flag'i va settings API enable helper qo'shildi
- `ui/pages/unified_settings.py` yangilanib, `API keys` bilan bog'liq o'qish/saqlash oqimlari endi avval `FastAPI` orqali ishlashga urinadi
- Backward-compatible fallback saqlandi: settings API yoqilmagan bo'lsa yoki backend API vaqtincha ishlamasa, eski direct `auth_db` yo'li bilan ishlash davom etadi
- Bu bosqichda faqat `API keys` slice ajratildi; modul va webhook tuning sozlamalari hozircha direct save/read rejimida qoldi
- Verification:
  - `./.venv/bin/python -m py_compile ...` muvaffaqiyatli o'tdi
  - `./.venv/bin/python -c "from services.api.settings_api import router; print(router.prefix)"` orqali router importi tekshirildi
- Bu o'zgarish [ROADMAP_SAAS.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ROADMAP_SAAS.md) dagi `2. Target Architecture`, `5. Authentication va Authorization`, `6. Secret Management va Security` hamda `9. Product UX/UI` bosqichlariga xizmat qiladi

#### 2026-05-05 - Frontend/backend split boshlandi: Monitoring birinchi API slice sifatida ajratildi

- `services/api/monitoring_api.py` qo'shildi va monitoring uchun ichki `FastAPI` endpointlar yaratildi:
  - snapshot olish
  - monitoring storage bootstrap qilish
  - task delete-check
  - task delete
- `services/webhook/jira_webhook_handler.py` ichiga monitoring router ulab qo'yildi, shuning bilan mavjud backend process ichida yangi API boundary paydo bo'ldi
- `ui/api_client.py` yaratildi; Streamlit sahifalari uchun `FastAPI`ga server-side HTTP chaqiriq helperlari qo'shildi
- `ui/pages/monitoring_dashboard.py` yangilanib, monitoring sahifasi endi `APP_USE_MONITORING_API` yoki umumiy `APP_USE_BACKEND_API` yoqilganda `FastAPI` orqali ishlaydi
- Shu sahifada backward-compatible fallback saqlandi: API yoqilmagan bo'lsa eski direct DB/repository yo'li bilan ishlash davom etadi
- Bu o'zgarish hozirgi ishlayotgan tizimni buzmasdan frontend/backend ajratishning birinchi real slice'ini yaratdi
- Verification:
  - `./.venv/bin/python -m py_compile ...` muvaffaqiyatli o'tdi
  - `./.venv/bin/pytest -q tests/test_repository_refactors.py` ishga tushirildi, lekin monitoringga aloqasiz bo'lgan 3 ta oldindan mavjud auth/subscription regression test yiqildi
- Bu o'zgarish [ROADMAP_SAAS.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ROADMAP_SAAS.md) dagi `2. Target Architecture`, `3. Data Layer Migration` va `9. Product UX/UI` bosqichlariga tayanch bo'ladi

#### 2026-05-05 - API kalitlar input UX va webhook credential isolation tuzatildi

- `ui/components/secret_input.py` yangilanib, secret/key inputlar doim editable bo'ladigan qilindi; qiymatlar faqat `Saqlash` bosilganda persist bo'ladi
- token/key maydonlariga ishlaydigan `ko'z` toggle qo'shildi; hidden holatda masklangan preview ko'rsatiladi, reveal qilinganda to'liq qiymat ochiladi
- `Unified Settings` ichida `Kompaniya API Kalitlari` va `Webhook API Kalitlari` save/load oqimlari ajratildi, endi biri ikkinchisini bosib ketmaydi
- `Sozlamalar` sidebar ichida text-link ko'rinishidagi 3 ta top-level selector va mos sub-selectorlar bilan ishlaydigan qilindi; `page` qismida faqat tanlangan bo'lim contenti ko'rsatiladi
- `company_settings` uchun alohida `webhook_*` credential maydonlari va migration qo'shildi; webhook runtime endi shu dedicated credentiallardan foydalanadi
- SQLite regression testlar bilan shared credentiallar va webhook credentiallar alohida encrypt qilinib saqlanishi tasdiqlandi
- Bu o'zgarish [ROADMAP_SAAS.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ROADMAP_SAAS.md) dagi `6. Secret Management va Security` hamda `9. Product UX/UI` bosqichlariga mos
#### 2026-05-04 - Admin credential settings input UX bugfix qilindi

- `admin/company_admin` credential inputlaridagi state boshqaruvi yaxshilandi
- Saqlangan secret maydonlar endi umuman `block` bo'lmaydi va har safar to'g'ridan-to'g'ri edit qilish mumkin
- Secret inputlar uchun `ko'z` belgisi aktiv input ichida ishlaydigan qilindi
- `API Setup` va `Unified Settings` ichidagi kompaniya/shared hamda webhook credential maydonlari bir xil helper orqali ishlaydigan qilindi
- Bu o'zgarish [ROADMAP_SAAS.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ROADMAP_SAAS.md) dagi `9. Product UX/UI` va `6. Secret Management va Security` bosqichlariga mos

#### 2026-05-02 - SaaS roadmap va foundation planning

- Loyiha uchun SaaS roadmap hujjati yaratildi: [ROADMAP_SAAS.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ROADMAP_SAAS.md)
- Repo uchun yo'riqnoma yaratildi: [AGENTS.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/AGENTS.md)
- Product scope aniqlashtirildi:
  - universal B2B SaaS
  - asosiy MVP modullar: `TZ-PR Checker`, `Test Case Generator`, `Monitoring`
  - `Monitoring` alohida pullik modul
  - `JIRA`, `GitHub`, `Figma` integratsiyalarini mijoz o'zi ulaydi
  - `AI API key` default holatda platformanikidan ishlaydi, ixtiyoriy mijozniki ham bo'lishi mumkin
- Role modeli aniqlandi:
  - `Super Admin`
  - `Company Admin`
  - `User`

#### 2026-05-02 - Company admin foundation implement qilindi

- `users` jadvaliga `role` ustuni qo'shildi
- `company_admin` rolini qo'llash uchun DB migration qo'shildi
- Login/session logikasi `company_admin`ni taniydigan qilindi
- `is_company_admin()` helper qo'shildi
- `is_user()` logikasi `company_admin`ni ham qamrab oladigan qilindi
- Super admin yangi kompaniya yaratganda birinchi `company admin` yaratish oqimi qo'shildi
- Super admin panelida `company_admin` alohida ko'rinadigan qilindi
- `company_admin` o'chirilmaydigan va asosiy admin sifatida ko'rsatiladigan qilindi
- Yangi sahifa qo'shildi: [ui/pages/company_admin.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/company_admin.py)
- `company_admin` uchun quyidagi imkoniyatlar qo'shildi:
  - kompaniya userlarini ko'rish
  - yangi user qo'shish
  - user parolini almashtirish
  - userni aktiv/nofaol qilish
  - userni o'chirish
- Sidebar ga `Team` sahifasi qo'shildi
- `company_admin` checker/testcase va user-level modullardan foydalana oladigan qilindi

#### 2026-05-02 - Manual billing foundation qo'shildi

- `company_subscriptions` jadvali qo'shildi
- Eski kompaniyalar uchun subscription ma'lumotlari avtomatik backfill qilinadigan qilindi
- Yangi kompaniyalar default `trial` obuna bilan yaratiladigan qilindi
- Subscription helperlar qo'shildi:
  - kompaniya subscriptionini olish
  - subscriptionni saqlash
  - login vaqtida subscription holatini tekshirish
- `suspended` va `cancelled` subscriptionlar loginni bloklaydigan qilindi
- Trial/active obuna muddat tugashi bo'yicha tekshiruv qo'shildi
- Super admin panelga `Billing / Subscription` boshqaruvi qo'shildi
- Super admin endi qo'lda:
  - plan nomini
  - subscription statusni
  - billing sanalarini
  - payment note ni
  boshqara oladi

#### 2026-05-02 - Monitoring access policy aniqlashtirildi

- `Monitoring` endi faqat `super_admin` va `company_admin` uchun ko'rinadi
- Oddiy `user` monitoringni ko'rmaydi
- `company_admin` monitoringda faqat o'z kompaniyasi ma'lumotlarini ko'radi
- `Task delete` bo'limi faqat `super_admin`ga qoldirildi

#### 2026-05-02 - Permission matrix hujjatlashtirildi

- Role va access qoidalari alohida hujjatga yozildi: [PERMISSION_MATRIX.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/PERMISSION_MATRIX.md)
- `auth_manager`ga keyingi access tekshiruvlari uchun helperlar qo'shildi

#### 2026-05-02 - Modul access helperga birlashtirildi

- `role + enabled_modules` tekshiruvi uchun `can_access_module()` helper qo'shildi
- Sidebar va asosiy route'lar endi modul accessni bitta helper orqali tekshiradi
- `Monitoring` va `Sprint Report` ham access helperga o'tkazildi

#### 2026-05-03 - Subscription entitlement access qo'shildi

- `TZ-PR Checker` va `Test Case Generator` uchun `base` plan entitlement modeli qo'shildi
- `get_effective_company_modules()` helperi yaratildi
- Endi amaldagi modul access:
  - subscription ichidagi bazaviy modullar
  - super admin yoqqan pullik modullar
  ikkalasini birlashtirib hisoblanadi
- `company_modules` session cache endi effective module set bilan to'ldiriladi
- `Monitoring` alohida pullik modul sifatida saqlab qolindi

#### 2026-05-03 - Super admin billing/module UI aniqlashtirildi

- Super admin panelda `base` plan ichidagi modullar va pullik addonlar ajratib ko'rsatildi
- Kompaniya yaratish formasi endi faqat pullik addonlarni tanlashga mo'ljallandi
- Kompaniya kartasida `included` va `addon` modullar alohida badge ko'rinishida chiqadigan qilindi
- Subscription bo'limida plan entitlement va paid addon boshqaruvi orasidagi farq aniq ko'rsatildi

#### 2026-05-03 - Billing validation kuchaytirildi

- Subscription saqlashdan oldin backend validation qo'shildi
- `plan_name` bo'sh yoki noto'g'ri formatda bo'lsa saqlanmaydigan qilindi
- `billing_end_date` `trial`, `active`, `past_due` statuslar uchun majburiy qilindi
- Billing sanalari `YYYY-MM-DD` formatida tekshiriladigan qilindi
- `billing_start_date <= billing_end_date` va `last_payment_date <= next_payment_date` tekshiruvlari qo'shildi
- Login paytida noto'g'ri yoki to'ldirilmagan subscription sanalari bloklanadigan qilindi

#### 2026-05-03 - Company admin user boshqaruvi company-scope bilan mustahkamlandi

- `company_admin` user operatsiyalari uchun company-scoped DB helperlar qo'shildi
- User parolini almashtirish faqat o'z kompaniyasidagi userlar uchun ishlaydigan qilindi
- Userni aktiv/nofaol qilish faqat o'z kompaniyasidagi oddiy userlar uchun ishlaydigan qilindi
- Userni o'chirish faqat o'z kompaniyasidagi oddiy userlar uchun ishlaydigan qilindi
- `company_admin` boshqa kompaniya userlariga amaliyot qila olmaydigan qilindi
- `Team Management` sahifasi route darajasida ham faqat `company_admin` uchun ruxsatli qilindi

#### 2026-05-03 - Company-level settings scope markazlashtirildi

- `can_manage_company_scope(company_id)` helperi qo'shildi
- Webhook va company-level settings saqlash joylari endi shu helper orqali tekshiriladi
- `Unified Settings` ichida webhook tab faqat joriy kompaniya scope ichida ko'rsatiladigan qilindi
- `API Setup` ichidagi company-level Figma sync ham session company scope bilan cheklangan qilindi

#### 2026-05-03 - Monitoring scope audit qilindi va qattiqlashtirildi

- Monitoring querylari va CSV export allaqachon `company_id` bo'yicha filtrlanishi tasdiqlandi
- Monitoring uchun markaziy scope helper qo'shildi
- `company_admin` monitoringi endi faqat sessiondagi o'z kompaniya scope'i bilan ishlaydi
- Monitoring CSV fayl nomiga ham company scope qo'shildi

#### 2026-05-03 - Billing holati ko'rinishi kuchaytirildi

- Super admin panelda billing health metrikalari qo'shildi
- Kompaniya kartalarida subscription risk banner ko'rsatiladigan qilindi
- `trial`, `past_due`, `suspended`, muddati tugayotgan va noto'g'ri sana holatlari alohida signal bilan chiqadi
- Subscription bo'limida ham joriy billing holati rangli indikator bilan ko'rsatiladigan qilindi

#### 2026-05-03 - PostgreSQL migratsiya rejalashtirildi

- `SQLite`ga bog'langan asosiy fayl va oqimlar audit qilindi
- `auth.db` va `processing.db` uchun target `PostgreSQL` schema yo'nalishi yozildi
- migratsiya fazalari va birinchi o'zgartiriladigan fayllar hujjatlashtirildi
- yangi hujjat yaratildi: [POSTGRESQL_MIGRATION_PLAN.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/POSTGRESQL_MIGRATION_PLAN.md)

#### 2026-05-03 - DB abstraction layer boshlandi

- yangi runtime helper yaratildi: [utils/database/runtime.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/database/runtime.py)
- auth DB path va connection ochish `runtime` orqali ishlaydigan qilindi
- processing DB path va connection ochish `runtime` orqali ishlaydigan qilindi
- monitoring dashboard ham endi umumiy DB runtime helperdan foydalanadi
- `auth_db.py`, `task_db.py`, `monitoring_dashboard.py` ichida to'g'ridan-to'g'ri `sqlite3.connect(...)` qolmadi

#### 2026-05-03 - Monitoring repository layer boshlandi

- yangi repository qo'shildi: [utils/database/monitoring_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/database/monitoring_repository.py)
- monitoring dashboard ichidagi asosiy read querylar UI'dan repository qatlamiga ko'chirildi
- `monitoring_dashboard.py` endi ko'proq render logic bilan shug'ullanadi
- delete verify/check querylari ham repositoryga ko'chirildi
- `monitoring_dashboard.py` ichida to'g'ridan-to'g'ri SQL query qolmadi

#### 2026-05-03 - Auth repository split boshlandi

- yangi repository qo'shildi: [utils/auth/company_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/company_repository.py)
- `company`, `subscription`, `company_settings`, `company_modules` querylari repository qatlamiga ajratila boshlandi
- `auth_db.py` ichidagi mos wrapper funksiyalar repository orqali ishlaydigan qilindi

#### 2026-05-03 - User repository split boshlandi

- yangi repository qo'shildi: [utils/auth/user_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/user_repository.py)
- `user CRUD` querylari repository qatlamiga ko'chirildi
- `user_credentials` va `user_module_settings` querylari repository qatlamiga ko'chirildi
- `auth_db.py` ichidagi user wrapper funksiyalar endi repository orqali ishlaydi

#### 2026-05-03 - Webhook routing querylari repositoryga o'tdi

- `get_company_by_project_key()` ichidagi DB query repository qatlamiga ko'chirildi
- `auth_db.py` ichida webhook/integration resolution uchun asosan business logic qoldi

#### 2026-05-03 - Platform repository split boshlandi

- yangi repository qo'shildi: [utils/auth/platform_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/platform_repository.py)
- `login_attempts` querylari repository qatlamiga ko'chirildi
- `global_settings` querylari repository qatlamiga ko'chirildi

#### 2026-05-03 - Company mutation querylari repositoryga o'tdi

- `get_company_by_code()` repository orqali ishlaydigan qilindi
- `create/update/delete company` querylari repository qatlamiga ko'chirildi
- `auth_db.py` ichida company bo'limida asosan business logic qoldi

#### 2026-05-03 - Sprint Report API DB runtime helperga o'tdi

- `services/api/sprint_report_api.py` ichidagi `processing.db` path hisoblash markazlashtirildi
- Sprint Report API endi to'g'ridan-to'g'ri `sqlite3.connect(...)` o'rniga umumiy `connect_processing_sqlite()` helperidan foydalanadi
- Production koddagi qolgan bevosita `sqlite3.connect(...)` chaqiruvlar servis/UI qatlamida tugatildi

#### 2026-05-03 - Sprint Report querylari repository qatlamiga ajratildi

- yangi repository qo'shildi: [utils/database/sprint_report_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/database/sprint_report_repository.py)
- `Sprint Report API` ichidagi analytics SQL querylari endpoint'dan repository qatlamiga ko'chirildi
- `services/api/sprint_report_api.py` endi ko'proq auth, validation va response mapping bilan shug'ullanadi

#### 2026-05-03 - Task DB repository split boshlandi

- yangi repository qo'shildi: [utils/database/task_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/database/task_repository.py)
- `task_db.py` ichidagi markaziy persistence querylari repository qatlamiga ajratila boshlandi
- `get_task()`, `upsert_task()`, `delete_task()`, retry/stuck/history querylari endi repository helperlar orqali ishlaydi
- `task_db.py` ichida business-state helperlar saqlanib, DB access qatlamini ajratish uchun zamin yaratildi

#### 2026-05-03 - Refactor regression testlari qo'shildi

- yangi alohida test fayl qo'shildi: [tests/test_repository_refactors.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/tests/test_repository_refactors.py)
- bu testlar mavjud katta suite'ga tegmasdan repository split qilingan `task_db` va `sprint_report` oqimlarini tekshiradi
- yangi regression testlar `4 passed` natija bilan tasdiqlandi

#### 2026-05-04 - Auth company/subscription querylari repositoryga davom ettirildi

- `auth_db.py` ichida qolgan company-level raw SQL bo'laklari yana qisqartirildi
- default trial subscription yaratish logikasi repository qatlamiga ko'chirildi
- webhook `project key` conflict tekshiruvi repository helperga ajratildi
- `tests/test_repository_refactors.py` ichiga shu refactor uchun auth company regression testlari qo'shildi
- bu qadam `Roadmap 3. Data Layer Migration` ichidagi DB access qatlamini `PostgreSQL`ga tayyorlash ishini davom ettiradi

#### 2026-05-04 - Auth lockout regression mustahkamlandi

- `record_failed_login()` oqimi uchun kerakli `timedelta` importi tiklandi
- login attempt lockout/reset behavior'i uchun alohida regression testi qo'shildi
- repository refactor regression suite `.venv` orqali qayta ishga tushirildi va `31 passed` bilan tasdiqlandi

#### 2026-05-04 - Monitoring SQLite runtime helperga ajratildi

- `utils/database/runtime.py` ichiga SQLite read/checkpoint helperlari qo'shildi
- `ui/pages/monitoring_dashboard.py` ichidagi bevosita `PRAGMA` chaqiriqlari runtime helperga ko'chirildi
- monitoring UI endi backend-spetsifik DB amallarini kamroq biladi va `PostgreSQL` migratsiyasiga yaqinlashdi
- regression suite kengaytirildi va `.venv` orqali `33 passed` bilan tasdiqlandi

#### 2026-05-04 - Database repository common helper birlashtirildi

- yangi umumiy helper qo'shildi: [utils/database/repository_common.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/database/repository_common.py)
- `task_repository`, `monitoring_repository`, `sprint_report_repository` ichidagi takroriy placeholder/row adapter logikasi shu helperga birlashtirildi
- DB repository qatlamida `SQLite` va `PostgreSQL` farqlarini boshqarish nuqtalari qisqardi
- regression suite kengaytirildi va `.venv` orqali `35 passed` bilan tasdiqlandi

#### 2026-05-04 - Postgres backend switch smoke testlari qo'shildi

- `connect_auth_db()` va `connect_processing_db()` uchun backend-aware delegation testlari qo'shildi
- `run_postgres_migration_bundle()` schema va import SQL ni to'g'ri ketma-ket qo'llashini tekshiruvchi smoke test qo'shildi
- `APP_DB_BACKEND=postgres` oqimi real DB talab qilmasdan regression darajada tekshiriladigan bo'ldi
- regression suite kengaytirildi va `.venv` orqali `38 passed` bilan tasdiqlandi

#### 2026-05-04 - Local PostgreSQL dry-run amalda tasdiqlandi

- alohida dry-run baza yaratildi: `jira_ai_analyzer_dryrun_20260504`
- `run_postgres_migration_bundle.py` local Postgres bazada muvaffaqiyatli ishga tushirildi
- target schema va import SQL amalda qo'llanib, asosiy row countlar tasdiqlandi:
  - `companies`: 5
  - `users`: 4
  - `subscriptions`: 5
  - `task_processing`: 38
  - `task_status_history`: 382
- `legacy-import` company va orphan task backfill'i ham amalda tekshirildi

#### 2026-05-04 - Tenant isolation regressionlari kuchaytirildi

- cross-company user mutation'lar uchun regression testlar qo'shildi
- `company_admin` akkauntini company-scoped delete/deactivate qilish bloklanishi test bilan tasdiqlandi
- inactive kompaniya webhook project key routing'dan chiqib ketishi regression test bilan yopildi
- repository regression suite `.venv` orqali qayta ishga tushirildi va `41 passed` bilan tasdiqlandi

#### 2026-05-04 - Credential storage hardening boshlandi

- yangi helper qo'shildi: [utils/auth/credential_crypto.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/credential_crypto.py)
- `user_credentials` va `company_settings` ichidagi sensitive token maydonlari endi repository qatlamida avtomatik encrypt/decrypt qilinadi
- legacy plain text qiymatlar backward-compat saqlangan holda o'qilaveradi
- `.env.example` ga `APP_CREDENTIALS_MASTER_KEY` qo'shildi
- regression suite kengaytirildi va `.venv` orqali `44 passed` bilan tasdiqlandi

#### 2026-05-04 - Credential security visibility qo'shildi

- master key holatini aniqlovchi security status helper qo'shildi
- super admin panel endi credential encryption `ok / warning / danger` holatini banner bilan ko'rsatadi
- `APP_CREDENTIALS_MASTER_KEY` yo'qligi production risk sifatida UI'da yashirin qolmaydigan bo'ldi
- regression suite qayta ishga tushirildi va `.venv` orqali `45 passed` bilan tasdiqlandi

#### 2026-05-04 - Master key bo'lmasa credential save bloklanadigan qilindi

- credential repository qatlamida encryption secret mavjudligini tekshiruvchi guard qo'shildi
- `APP_CREDENTIALS_MASTER_KEY` ham, fallback secret ham yo'q bo'lsa yangi sensitive credentiallarni saqlash rad etiladi
- plain text credential yozilib qolish xavfi amaliy darajada kamaytirildi
- regression suite kengaytirildi va `.venv` orqali `47 passed` bilan tasdiqlandi

#### 2026-05-04 - DB-based super admin foundation qo'shildi

- yangi jadval foundation qo'shildi: `platform_admins`
- startup paytida legacy `.env` super adminni DB'ga seed qilish qatlami qo'shildi
- login oqimi endi DB ichidagi platform super adminni taniydi, env fallback esa backward-compat sifatida saqlanib turibdi
- bu qadam `.env`ga to'liq bog'liqlikni kamaytirib, SaaS auth modeliga yaqinlashtirdi
- regression suite kengaytirildi va `.venv` orqali `49 passed` bilan tasdiqlandi

#### 2026-05-04 - Login audit foundation qo'shildi

- yangi jadval foundation qo'shildi: `login_audit_logs`
- platform repository ichiga login audit yozish va o'qish helperlari qo'shildi
- `auth_manager.login()` endi asosiy success/failure holatlarini audit logga yozadi
- security/support uchun login izlari saqlanadigan bo'ldi
- regression suite kengaytirildi va `.venv` orqali `50 passed` bilan tasdiqlandi

#### 2026-05-04 - Platform admin UI boshlandi

- super admin panelga yangi `Platform Admin` bo'limi qo'shildi
- DB-based super admin parolini panel ichidan yangilash foundation qo'shildi
- so'nggi login audit yozuvlarini super admin UI'da ko'rish imkoniyati qo'shildi
- platform admin password rotation regression bilan tasdiqlandi
- regression suite kengaytirildi va `.venv` orqali `51 passed` bilan tasdiqlandi

#### 2026-05-04 - Super admin auth source visibility qo'shildi

- sessiya ichida `auth_source` maydoni qo'shildi
- super admin panel endi joriy sessiya `DB-based admin` yoki `legacy env fallback` ekanini ko'rsatadi
- legacy fallback bilan kirilgan holatda DB-based platform admin paroliga o'tish bo'yicha aniq warning chiqadi
- regression suite kengaytirildi va `.venv` orqali `52 passed` bilan tasdiqlandi

#### 2026-05-04 - DB platform admin uchun env fallback cheklov qo'shildi

- agar shu username uchun `platform_admins` yozuvi mavjud bo'lsa, login endi faqat DB hash orqali tekshiriladi
- eski `.env` super admin paroli endi DB-based platform adminni aylanib o'ta olmaydi
- legacy env fallback faqat DB platform admin yozuvi yo'q bo'lganda ishlaydi
- regression suite kengaytirildi va `.venv` orqali `54 passed` bilan tasdiqlandi

#### 2026-05-04 - Login audit UI filter va export qo'shildi

- super admin paneldagi login audit bo'limiga success filter, identifier qidiruvi va limit tanlovi qo'shildi
- login audit yozuvlarini CSV ko'rinishida yuklab olish imkoni qo'shildi
- login audit foundation endi support/security ishlari uchun amaliy boshqaruv vositasiga yaqinlashdi
- regression suite kengaytirildi va `.venv` orqali `55 passed` bilan tasdiqlandi

#### 2026-05-03 - Auth schema init/migration qatlami ajratildi

- yangi modul qo'shildi: [utils/auth/auth_schema.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_schema.py)
- `auth_db.py` ichidagi asosiy table yaratish va migration funksiyalari schema helper moduliga ko'chirildi
- `init_auth_db()` endi business logic markazi bo'lib qoldi, schema/migration tafsilotlari alohida qatlamga ajratildi
- regression testlar auth schema uchun ham kengaytirildi va umumiy natija `5 passed` bilan tasdiqlandi

#### 2026-05-03 - Auth config helperlari ajratildi

- yangi helper modul qo'shildi: [utils/auth/auth_config_helpers.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_config_helpers.py)
- `auth_db.py` ichidagi company/user credential composition va webhook config shaping logikalari alohida helper qatlamiga ko'chirildi
- Gemini fallback precedence va webhook config parsing uchun regression testlar qo'shildi
- alohida regression suite endi `7 passed` natija bilan tasdiqlandi

#### 2026-05-03 - Subscription va entitlement helperlari ajratildi

- yangi helper modul qo'shildi: [utils/auth/auth_subscription_helpers.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_subscription_helpers.py)
- `auth_db.py` ichidagi subscription validation, access check va effective module entitlement logikalari helper qatlamiga ko'chirildi
- billing end-date validation va plan entitlement hisoblash uchun regression testlar qo'shildi
- alohida regression suite endi `9 passed` natija bilan tasdiqlandi

#### 2026-05-03 - Arxitektura va platforma yo'nalishi hujjatlashtirildi

- hozirgi tizim holati yozildi: [CURRENT_STATE_ARCHITECTURE.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/CURRENT_STATE_ARCHITECTURE.md)
- target architecture hujjati yaratildi: [TARGET_ARCHITECTURE.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/TARGET_ARCHITECTURE.md)
- arxitektura o'tish ketma-ketligi yozildi: [ARCHITECTURE_MIGRATION_STRATEGY.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ARCHITECTURE_MIGRATION_STRATEGY.md)
- `Streamlit`ning final roli, `FastAPI` backend roli, `Next.js` frontend roli va worker boundary yozib qo'yildi

#### 2026-05-03 - PostgreSQL target schema artefakti yaratildi

- yangi schema papkasi qo'shildi: [database/postgresql](/Users/mac/Documents/projects/JIRA-AI-Analyzer/database/postgresql)
- birinchi target schema yaratildi: [database/postgresql/001_initial_schema.sql](/Users/mac/Documents/projects/JIRA-AI-Analyzer/database/postgresql/001_initial_schema.sql)
- schema ichiga auth, billing, integrations, audit, jobs va processing jadvallari kiritildi
- DB runtime helperga backend config va `postgres` DSN helperlari qo'shildi

#### 2026-05-03 - SQLite export poydevori qo'shildi

- yangi export script qo'shildi: [utils/tools/export_sqlite_for_postgres.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/tools/export_sqlite_for_postgres.py)
- script `auth.db` va `processing.db` jadvallarini JSON ko'rinishida export qila oladi
- `manifest.json` orqali qaysi jadvaldan nechta row chiqqani yoziladi
- PostgreSQL README ichiga export yo'li ham qo'shildi

#### 2026-05-03 - PostgreSQL import SQL generator qo'shildi

- yangi generator qo'shildi: [utils/tools/generate_postgres_import_sql.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/tools/generate_postgres_import_sql.py)
- export JSON fayllardan `PostgreSQL` uchun `INSERT` script generatsiya qilinadigan bo'ldi
- import load order auth va processing bog'liqligiga mos ravishda yozildi
- regression testga import SQL generator tekshiruvi ham qo'shildi

#### 2026-05-03 - PostgreSQL import script amaliyroq qilindi

- generatsiya qilinadigan `import.sql` ichiga `TRUNCATE ... CASCADE` qo'shildi
- explicit `id` bilan insert qilingandan keyin sequence reset SQL qo'shildi
- import script qayta ishlatiladigan migration artifactga yaqinlashtirildi

#### 2026-05-03 - PostgreSQL migration bundle validator qo'shildi

- yangi validator qo'shildi: [utils/tools/validate_postgres_migration_bundle.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/tools/validate_postgres_migration_bundle.py)
- schema SQL, export manifest va generated import SQL bir-biriga mosligi tekshiriladigan bo'ldi
- migration artifactlar orasidagi moslikni oldindan ushlash uchun regression test qo'shildi

#### 2026-05-03 - PostgreSQL runtime skeleton qo'shildi

- `runtime.py` ichiga postgres driver availability check va backend-aware connect helperlar qo'shildi
- yangi migration runner qo'shildi: [utils/tools/run_postgres_migration_bundle.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/tools/run_postgres_migration_bundle.py)
- driver yo'q muhitda tushunarli xato berish uchun regression test qo'shildi

#### 2026-05-03 - PostgreSQL driver o'rnatildi

- `.venv` ichiga `psycopg[binary]` o'rnatildi
- dependency ro'yxatiga `psycopg[binary]==3.3.4` qo'shildi
- runtime test endi driver bor holatda `DSN` yo'q bo'lsa ham tushunarli xato qaytarishini tekshiradi

#### 2026-05-03 - PostgreSQL readiness preflight qo'shildi

- yangi checker qo'shildi: [utils/tools/check_postgres_ready.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/tools/check_postgres_ready.py)
- yangi setup yo'riqnomasi qo'shildi: [database/postgresql/SETUP.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/database/postgresql/SETUP.md)
- checker driver, DSN, schema, export manifest va import SQL mavjudligini tekshiradi
- regression testga readiness checker holati ham qo'shildi

#### 2026-05-03 - Local PostgreSQL migration dry-run muvaffaqiyatli o'tdi

- `generate_postgres_import_sql.py` endi:
  - `SQLite`dagi boolean qiymatlarni `TRUE/FALSE`ga moslaydi
  - bo'sh date/timestamp qiymatlarni `NULL`ga aylantiradi
  - `company_id` yo'q legacy tasklar uchun avtomatik `legacy-import` company va subscription yaratadi
- local `jira_ai_analyzer` `PostgreSQL` bazasiga schema + import bundle muvaffaqiyatli qo'llandi
- tekshiruvda asosiy row countlar tasdiqlandi:
  - `companies`: 5
  - `users`: 4
  - `subscriptions`: 5
  - `task_processing`: 38
  - `task_status_history`: 382
- regression suite kengaydi va yashil:
  - `tests/test_repository_refactors.py` -> `18 passed`

#### 2026-05-03 - Monitoring repository backend-aware qilindi

- [utils/database/monitoring_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/database/monitoring_repository.py) endi:
  - `sqlite` va `postgres` placeholder formatlarini moslashtiradi
  - `pandas.read_sql_query` o'rniga backend-agnostic cursor fetch ishlatadi
  - delete-check natijasini dict ko'rinishida qaytaradi
- [ui/pages/monitoring_dashboard.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/monitoring_dashboard.py):
  - `connect_processing_db()` orqali ulanadigan qilindi
  - `PRAGMA` va file-path tekshiruvlari faqat `sqlite` backendda ishlaydi
  - monitoring UI endi DB backend haqida aniqroq status ko'rsatadi
- regression suite kengaydi va yashil:
  - `tests/test_repository_refactors.py` -> `20 passed`

#### 2026-05-03 - Task repository asosiy oqimlari backend-aware qilindi

- [utils/database/runtime.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/database/runtime.py):
  - `connect_postgres(row_factory=True)` qo'llab-quvvatlandi
  - `connect_auth_db()` va `connect_processing_db()` endi `postgres` uchun dict-row ulanish bera oladi
- [utils/database/task_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/database/task_repository.py):
  - placeholder adapter (`?` / `%s`) qo'shildi
  - CRUD/history/stuck/retry querylari `sqlite` va `postgres` connection bilan ishlay oladigan qilindi
  - `stuck_minutes` hisobi `postgres` uchun ham alohida query bilan moslashtirildi
- [utils/database/task_db.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/database/task_db.py):
  - `get_task()`, `upsert_task()`, `delete_task()`, blocked retry, stuck task, status history oqimlari `connect_processing_db()`ga o'tdi
  - `sqlite-only` bo'lib qolgan qism asosan schema/init/migration helperlarda qoldi
- regression suite hali ham yashil:
  - `tests/test_repository_refactors.py` -> `20 passed`

#### 2026-05-03 - Processing schema helper task_db dan ajratildi

- yangi modul qo'shildi: [utils/database/processing_schema.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/database/processing_schema.py)
- `task_db.py` ichidan quyidagi `sqlite-only` bo'laklar ajratildi:
  - `PRAGMA` optimizatsiyalari
  - `task_processing` schema yaratish
  - `task_status_history` schema yaratish
  - `company_id` va `return_reason` migration helperlari
- [utils/database/task_db.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/database/task_db.py) endi schema/init detalidan yengillashdi va ko'proq orchestration/business layer vazifasida qoldi
- regression suite kengaydi va yashil:
  - `tests/test_repository_refactors.py` -> `21 passed`

#### 2026-05-03 - Auth repository qatlamining asosiy consumerlari backend-aware qilindi

- yangi umumiy adapter qo'shildi: [utils/auth/repository_common.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/repository_common.py)
  - `?` / `%s` placeholder moslashuvi
  - row -> dict helper
- [utils/auth/platform_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/platform_repository.py),
  [utils/auth/company_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/company_repository.py),
  [utils/auth/user_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/user_repository.py)
  endi umumiy adapter orqali ishlaydi
- [utils/auth/auth_db.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_db.py):
  - `_get_conn()` endi `connect_auth_db()` orqali ulanadi
  - `sqlite`ga xos `PRAGMA` va old-schema backup oqimi faqat `sqlite` backendda ishlaydi
- regression suite kengaydi va yashil:
  - `tests/test_repository_refactors.py` -> `23 passed`

#### 2026-05-03 - Auth bootstrap oqimi auth_db dan ajratildi

- yangi modul qo'shildi: [utils/auth/auth_bootstrap.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_bootstrap.py)
- `auth_db.py` ichidan quyidagilar ajratildi:
  - legacy schema aniqlash
  - eski `auth.db` backup oqimi
  - schema + migration orchestration bootstrap
- [utils/auth/auth_db.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_db.py) endi init bosqichida ko'proq orchestration/business entry-point vazifasida qoldi
- regression suite yana kengaydi va yashil:
  - `tests/test_repository_refactors.py` -> `24 passed`

#### 2026-05-03 - Sprint Report API backend-aware qilindi

- [utils/database/sprint_report_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/database/sprint_report_repository.py)
  endi `sqlite` va `postgres` cursor placeholderlarini moslashtira oladi
- [services/api/sprint_report_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/sprint_report_api.py)
  endi `connect_processing_db()` orqali ulanadi
- DB file mavjudligi tekshiruvi faqat `sqlite` backendda ishlaydi
- regression suite yana kengaydi va yashil:
  - `tests/test_repository_refactors.py` -> `25 passed`

#### 2026-05-03 - Sales scope 3 ta modulga qisqartirildi

- sotuv uchun tayyor modul scope qat'iy belgilandi:
  - `tz_pr_checker`
  - `testcase_generator`
  - `monitoring`
- [ui/pages/sidebar.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/sidebar.py) endi faqat shu 3 modulni ko'rsatadi
- [app.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/app.py) da:
  - `Bug Analyzer`
  - `Sprint Statistics`
  - `Sprint Report`
  stale route bilan ochilsa `hali tayyor emas` xabari chiqadi
- [ui/pages/super_admin.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/super_admin.py) endi kompaniya modul boshqaruvida faqat sales-ready modullarni ko'rsatadi
- [utils/auth/auth_manager.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_manager.py) unsupported modullar uchun access bermaydi
- regression suite kengaydi va yashil:
  - `tests/test_repository_refactors.py` -> `26 passed`

#### 2026-05-04 - Unified settings va app branding sales scope'ga moslandi

- [ui/pages/unified_settings.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/unified_settings.py)
  endi user va super-admin settings oqimida `Bug Analyzer` va `Statistics` tablarini ko'rsatmaydi
- modul visibility bo'limi endi faqat:
  - `TZ-PR Checker`
  - `Test Case Generator`
  standalone modullarini boshqaradi
- [app.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/app.py) user-facing nomlari `QA Assistant` scope'iga moslashtirildi
- regression suite hali ham yashil:
  - `tests/test_repository_refactors.py` -> `26 passed`

#### 2026-05-04 - API setup onboarding 3 modul scope'iga soddalashtirildi

- [ui/pages/api_setup.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/api_setup.py)
  endi onboardingda faqat 3 modulga kerak bo'ladigan oqimni ko'rsatadi
- `Figma` onboarding bloki vaqtincha olib tashlandi
- JIRA/GitHub majburiy, Gemini optional oqimi soddalashtirildi
- [ui/pages/login.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/login.py)
  subtitle va helper matnlari joriy product scope'iga moslandi
- regression suite hali ham yashil:
  - `tests/test_repository_refactors.py` -> `26 passed`

#### 2026-05-04 - Company Admin team flow product tiliga moslandi

- [ui/pages/company_admin.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/company_admin.py)
  sahifa matnlari va action label'lari soddalashtirildi
- Team sahifasida:
  - seat usage progress ko'rsatkichi qo'shildi
  - bo'sh joy soni alohida ko'rsatildi
  - user qo'shish oqimi product tilida aniqroq qilindi
- regression suite hali ham yashil:
  - `tests/test_repository_refactors.py` -> `26 passed`

#### 2026-05-04 - Monitoring modulining customer-facing matnlari polish qilindi

- [ui/pages/monitoring_dashboard.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/monitoring_dashboard.py)
  ichidagi texnik `DB` markazli matnlar product tiliga moslashtirildi
- overview, error, retry queue va export bo'limlari aniqroq user-facing matnlar bilan yangilandi
- super admin uchun task delete bo'limi `Advanced` cleanup sifatida aniqroq ajratildi
- regression suite hali ham yashil:
  - `tests/test_repository_refactors.py` -> `26 passed`

#### 2026-05-04 - Light/Dark va 3 til uchun UI foundation qo'shildi

- yangi i18n helper qo'shildi: [ui/i18n.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/i18n.py)
  - qo'llab-quvvatlanadigan tillar:
    - `uz`
    - `en`
    - `ru`
- yangi UI preferences helper qo'shildi: [ui/preferences.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/preferences.py)
  - theme tanlovi:
    - `dark`
    - `light`
  - til tanlovi session orqali boshqariladi
- [app.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/app.py) endi session-based theme apply ishlatadi
- [ui/pages/login.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/login.py) va [ui/pages/sidebar.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/sidebar.py)
  ga language/theme preferences ulab chiqildi
- keyingi tarjima ishlari endi shu foundation ustida bosqichma-bosqich qilinadi
- regression suite kengaydi va yashil:
  - `tests/test_repository_refactors.py` -> `28 passed`

### In Progress

#### Frontend release hardening

- `./start.sh` local end-to-end smoke test sandbox port cheklovi sabab to'liq tasdiqlanmadi
- frontend production env, reverse proxy va deploy packaging hali hujjatlashtirilishi kerak

#### Streamlit decommission boundary

- legacy `Streamlit` fallback hali mavjud
- to'liq removal uchun real prod rolloutdan keyin entrypointlarni o'chirish mumkin

### Next

- real local/prod muhitda `./start.sh` startup smoke test
- frontend production env va reverse proxy config'ini yakunlash
- `PostgreSQL`ni final source-of-truth qilish
- worker/queue va prod ops qatlamini yakunlash

## Keyingi Muhim Bosqichlar

- Permission layer
- Subscription/billing data modeli
- Multi-tenant security mustahkamlash
- PostgreSQL migratsiya rejalash

#### 2026-05-04 - Postgres auth schema app-compatible qilindi

- `PostgreSQL` target schema amaldagi repository querylari bilan moslashtirildi:
  - `subscriptions` o'rniga `company_subscriptions`
  - `company_webhook_settings` o'rniga to'liq `company_settings`
  - `platform_admins` jadvali qo'shildi
  - `user_credentials` va `company_settings` ichida plain column nomlari (`jira_token`, `github_token`, ...) saqlandi
- migration bundle yangilandi:
  - `export_sqlite_for_postgres.py` endi `platform_admins` va `login_audit_logs` ni ham export qiladi
  - `generate_postgres_import_sql.py` endi `company_settings`, `company_subscriptions`, `platform_admins`, `login_audit_logs` ni import qiladi
  - company-level va user-level encrypted credential qiymatlar migration paytida tushib qolmaydigan bo'ldi
- validator va regression testlar yangilandi
- verification:
  - `./.venv/bin/python -m pytest tests/test_repository_refactors.py`
  - natija: `55 passed`

#### 2026-05-04 - Postgres migration bundle real auth sync bilan qayta tekshirildi

- migration bundle ichida yana ikki real muammo tuzatildi:
  - `user_credentials` uchun Postgres schema plain column nomlari bilan sync qilindi
  - `login_audit_logs` importida mavjud bo'lmagan `user_id/company_id` FK'lari `NULL`ga tushiriladigan qilindi
- export/import artifactlar qayta generatsiya qilindi va local dry-run Postgres bazaga qayta urildi
- yakuniy dry-run natijalari:
  - `companies`: 135
  - `users`: 51
  - `company_subscriptions`: 135
  - `company_settings`: 134
  - `platform_admins`: 23
  - `login_audit_logs`: 14
  - `user_credentials`: 15
  - `task_processing`: 38
  - `task_status_history`: 416
- regression suite kengaydi:
  - orphan `login_audit_logs` FK reference import behavior uchun test qo'shildi
  - `tests/test_repository_refactors.py` -> `56 passed`

#### 2026-05-04 - Password reset foundation va session timeout qo'shildi

- `Authentication va Authorization` roadmap bosqichi uchun yangi foundation qo'shildi:
  - `user_password_reset_tokens` jadvali yaratildi
  - bir martalik reset token yaratish helperlari qo'shildi
  - token orqali parolni bir marta yangilash oqimi qo'shildi
  - ishlatilgan yoki muddati o'tgan token qayta ishlamasligi yopildi
- session hardening uchun auth session ichiga quyidagi metadata qo'shildi:
  - `session_started_at`
  - `last_activity_at`
  - `expires_at`
  - `session_nonce`
- `APP_SESSION_TIMEOUT_MINUTES` asosidagi timeout helper qo'shildi:
  - sessiya eskirsa login sahifasiga qaytariladi
  - `login_error` orqali "sessiya muddati tugadi" xabari ko'rsatiladi
- Postgres migration bundle ham yangi auth jadval bilan sync qilindi:
  - `user_password_reset_tokens` schema, export, import va validatorga qo'shildi
- verification:
  - `./.venv/bin/python -m pytest tests/test_repository_refactors.py`
  - natija: `60 passed`
  - `./.venv/bin/python utils/tools/validate_postgres_migration_bundle.py ...`
  - natija: `ok: true`

#### 2026-05-04 - Password reset UI oqimi ulab chiqildi

- `super_admin` va `company_admin` user boshqaruvi ichiga `Reset Token` tugmasi qo'shildi
- admin endi user uchun bir martalik reset token yaratib, uni xavfsiz kanal orqali ulasha oladi
- login sahifasiga token bilan parolni tiklash formasi qo'shildi
- bu oqim email infrastrukturasiz ham ishlaydi va oldingi password reset foundation'ga ulanadi
- verification:
  - `./.venv/bin/python -m pytest tests/test_repository_refactors.py`
  - natija: `60 passed`

#### 2026-05-04 - Secret masking UX qo'shildi

- `credential_crypto.py` ichiga secret masking helperlari qo'shildi:
  - `mask_secret_value`
  - `resolve_secret_input`
  - `merge_masked_token_rows`
- `api_setup` va `unified_settings` ichida mavjud tokenlar endi plain qiymat bilan preload qilinmaydi
- secret fieldlar endi:
  - masklangan placeholder ko'rsatadi
  - bo'sh qoldirilsa oldingi saqlangan qiymatni saqlab qoladi
  - Figma token ro'yxatida ham blank row existing tokenni tasodifan o'chirmaydi
- verification:
  - `./.venv/bin/python -m pytest tests/test_repository_refactors.py`
  - natija: `61 passed`

#### 2026-05-04 - Credential key rotation foundation qo'shildi

- `credential_crypto.py` endi `APP_CREDENTIALS_OLD_MASTER_KEYS` ni ham tushunadi
- yangi master key bilan yozish, eski master keylar bilan o'qish foundation'i qo'shildi
- `needs_reencryption()` helperi orqali eski key bilan shifrlangan qiymatlarni aniqlash mumkin bo'ldi
- super admin security banner endi key rotation holati (`rotation_ready`) ni ham ko'rsatadi
- `.env.example` ga eski keylar uchun namuna env qo'shildi
- verification:
  - `./.venv/bin/python -m pytest tests/test_repository_refactors.py`
  - natija: `62 passed`

#### 2026-05-04 - Credential re-encrypt utility qo'shildi

- yangi tool qo'shildi: [utils/tools/reencrypt_credentials.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/tools/reencrypt_credentials.py)
- utility quyidagini qiladi:
  - `user_credentials` va `company_settings` ichidagi secret maydonlarni skan qiladi
  - `needs_reencryption()` bo'yicha eski key bilan shifrlangan qiymatlarni topadi
  - `--apply` bilan ularni joriy master key bilan qayta shifrlaydi
- `credential_crypto.py` ichiga `reencrypt_sensitive_fields()` va `payload_needs_reencryption()` helperlari qo'shildi
- verification:
  - `./.venv/bin/python -m pytest tests/test_repository_refactors.py`
  - natija: `64 passed`
  - dry-run:
    - `user_credentials`: `22 scanned`, `0 updated`, `19 blocked`
    - `company_settings`: `196 scanned`, `0 updated`, `17 blocked`

#### 2026-05-04 - Rotation blocker aniqlandi

- real dry-run shuni ko'rsatdi:
  - joriy muhit `APP_CREDENTIALS_MASTER_KEY` bilan emas, `SUPER_ADMIN_PASSWORD` fallback bilan ishlayapti
  - shu sabab eski master key bilan shifrlangan credentiallar qayta shifrlanmayapti
- `reencrypt_credentials.py` endi `updated` va `blocked` holatlarini alohida ko'rsatadi
- xulosa:
  - rotation utility tayyor
  - lekin haqiqiy apply qilish uchun avval `APP_CREDENTIALS_MASTER_KEY` va kerakli `APP_CREDENTIALS_OLD_MASTER_KEYS` berilishi kerak

#### 2026-05-04 - Test-generated tenantlar auth DB'dan tozalandi

- foydalanuvchi ehtiyoji bo'yicha faqat quyidagi tenantlar qoldirildi:
  - `xasan`
  - `moxir`
  - `jasur`
- auth DB cleanup natijasi:
  - `206` ta test company o'chirildi
  - `87` ta test user o'chirildi
  - bog'liq `company_settings`, `company_subscriptions`, `user_credentials`, `user_password_reset_tokens` yozuvlari ham tozalandi
- backup yaratildi:
  - `data/auth.db.cleanup_backup_20260504_keepers_xyz`

#### 2026-05-04 - Shared company credential modeli user oqimiga tushirildi

- `company_admin` kiritgan `JIRA`, `GitHub` va `Figma` tokenlari endi company-level manbadan olinadi
- qo'shimcha `user`lar bu shared integratsiyalarni ishlatadi, lekin ularni UI orqali o'zgartira olmaydi
- oddiy `user` uchun faqat shaxsiy `Gemini` API key override saqlash imkoniyati qoldirildi
- `build_user_credentials_for_service()` company-shared integratsiyalarni ustun qo'yadi, eski user-level credentiallar uchun backward compatibility saqlanib qoldi
- verification:
  - `./.venv/bin/python -m pytest tests/test_repository_refactors.py`
  - natija: `66 passed`

#### 2026-05-04 - Yangi kompaniya create flow qo'shimcha user modeliga moslandi

- super admin uchun `Yangi Kompaniya` formasida `Qo'shimcha User Limiti` default qiymati `0` qilindi
- `company_admin` seat limitga kirmaydi, seat limiti faqat qo'shimcha `user`lar uchun ishlaydi
- bepul `base` modullar (`TZ-PR Checker`, `Test Case Generator`) create formda default yoqilgan ko'rinadi
- pullik addonlar default holatda tanlanmagan bo'lib qoladi
- super admin va company admin panellaridagi seat statistikasi `qo'shimcha user` semantikasiga moslandi
- verification:
  - `./.venv/bin/python -m pytest tests/test_repository_refactors.py`
  - natija: `67 passed`

#### 2026-05-04 - Auth testlar izolyatsiyalangan vaqtinchalik DB'ga o'tkazildi

- `tests/conftest.py` endi har test uchun alohida temp `auth.db` yaratadi
- repository refactor testlari real `data/auth.db`ga yozmaydi, shu sabab test company/userlar production-like bazada qolib ketmaydi
- shared fixturega qattiq bog'langan bir nechta testlar mustaqil seed bilan mustahkamlandi
- verification:
  - `./.venv/bin/python -m pytest tests/test_repository_refactors.py`
  - natija: `67 passed`

#### 2026-05-04 - API setup save xatolari uchun debug diagnostika qo'shildi

- `API Kalitlarni Sozlang` sahifasida save yiqilganda endi `🔧 Debug ma'lumot` expander ko'rinadi
- unda save target, role, company/user id, normalized project keylar, project key conflict, credential security holati va ehtimoliy sabablar ko'rsatiladi
- exception bo'lsa `exception_type` va `exception_message` ham alohida chiqariladi
- tokenlarning o'zi emas, faqat mavjudlik holati ko'rsatiladi
- verification:
  - `./.venv/bin/python -m pytest tests/test_repository_refactors.py`
  - natija: `67 passed`

#### 2026-05-04 - Company admin JIRA project key webhook routingdan ajratildi

- `company_settings` ichiga alohida `jira_project_keys` maydoni qo'shildi
- `API Kalitlarni Sozlang` va company admin API settings endi checker/testcase uchun shu maydonga yozadi
- `webhook_project_keys` faqat paid webhook routing uchun qoldi va unique conflict tekshiruvi faqat shu maydonga tegishli
- `has_user_credentials_configured()` endi company-level `jira_project_keys` ni tekshiradi
- real `auth.db` schema migration ham yugurtirildi
- verification:
  - `./.venv/bin/python -m pytest tests/test_repository_refactors.py`
  - natija: `67 passed`

#### 2026-05-04 - Role-specific copy va per-user module settings izolyatsiyasi tekshirildi

- `company_admin` team sahifasidan `Monitoring` eslatmasi olib tashlandi
- `API Kalitlar` bo'limidagi izoh matnlari `company_admin` va oddiy `user` uchun alohida qilindi
- oddiy `user` endi JIRA/GitHub/Figma emas, faqat shaxsiy `Gemini` override boshqarishini aniq ko'radi
- regression test bilan bir kompaniya ichida admin va user standalone modul sozlamalarini mustaqil saqlashi tasdiqlandi
- verification:
  - `./.venv/bin/python -m pytest tests/test_repository_refactors.py`
  - natija: `68 passed`
#### 2026-05-04 - Webhook addon policy va monitoring derive qoidasi hujjatlashtirildi

- yangi qaror hujjati qo'shildi: [WEBHOOK_MONITORING_ADDON_PLAN.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/WEBHOOK_MONITORING_ADDON_PLAN.md)
- product qoida aniqlandi: `Webhook` pullik addon sifatida sotiladi
- `Monitoring` alohida sotilmaydi; `Webhook` yoqilgan kompaniyada avtomatik ochiladigan hosila modul sifatida belgilandi
- `PERMISSION_MATRIX.md` ichida role va access policy shu modelga moslashtirildi
- keyingi implementatsiya uchun entitlement helper, super admin addon UI, webhook settings gate va regression test nuqtalari aniq yozib chiqildi

#### 2026-05-04 - Webhook addon policy kodga o'tkazildi

- [utils/auth/auth_subscription_helpers.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_subscription_helpers.py) ichida `monitoring` access endi har doim `webhook` addonidan derive qilinadi
- [utils/auth/auth_db.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_db.py) ichida `webhook` sales-ready entitlement sifatida qo'shildi
- [ui/pages/super_admin.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/super_admin.py) ichida `Monitoring` mustaqil addon editoridan chiqarildi, `Webhook` yoqilganda derived badge ko'rsatiladigan qilindi
- [ui/pages/unified_settings.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/unified_settings.py) ichida webhook company-level save va API key bo'limlari `Webhook` addon entitlement'iga bog'landi

#### 2026-05-06 - Tanlangan kompaniyalar SQLite'dan PostgreSQL target bazaga sync qilindi

- yangi selektiv migrator qo'shildi: [utils/tools/sync_selected_companies_to_postgres.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/tools/sync_selected_companies_to_postgres.py)
- script `xasan`, `moxir`, `jasur`, `gws` kompaniyalarini va ularning bog'liq `users`, `subscriptions/company_subscriptions`, `company settings`, `user credentials`, `user module settings`, `login audit logs`, `task_processing`, `task_status_history` yozuvlarini Postgresga `upsert` qiladi
- real target baza `postgresql:///jira_ai_analyzer`da amalda yugurtirildi
- verifikatsiya natijasi:
  - `companies`: `6/xasan`, `7/moxir`, `8/jasur`, `321/gws` mavjud
  - `users`: `xasan@xasan`, `moxir@moxir`, `jasur@jasur`, `jasur@gws`, `mohir@gws` mavjud
  - `subscriptions`: 4 ta kompaniya uchun yozuvlar mavjud
  - `task_processing`: `company_id=8` uchun 37 ta task sync bo'ldi
  - `company_integrations`, `company_module_access`, `company_webhook_settings` ham selected companylar uchun sync qilindi

#### 2026-05-05 - Web startup stale backendni force-restart qila oladigan qilindi

- [start.sh](/Users/mac/Documents/projects/JIRA-AI-Analyzer/start.sh) ichiga `FORCE_RESTART_BACKEND=1` rejimi qo'shildi
- endi `8000` portda eski `uvicorn` process turib qolsa, script uni to'xtatib hozirgi kod bilan backendni qayta ko'tara oladi
- oddiy startupda esa eslatma chiqadi: login auth muammolarida `FORCE_RESTART_BACKEND=1 ./start.sh` ishlatish kerak
- real tekshiruvda root cause tasdiqlandi: eski backend `/api/auth/login` javobida `session_token` qaytarmayotgan edi, shu sabab `Next.js` login route `401` qaytarayotgan bo'lgan

#### 2026-05-04 - Webhook routing company-specific endpointga yangilandi

- `project key` global unique bo'lishi shart emasligi hisobga olindi
- [services/webhook/jira_webhook_handler.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/jira_webhook_handler.py) ichida yangi endpoint qo'shildi: `/webhook/jira/{company_code}`
- legacy `/webhook/jira` endpoint backward compatibility uchun qoldi, lekin duplicate project key holatida ambiguous bo'lishi mumkin
- [utils/auth/company_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/company_repository.py) ichida global `webhook_project_keys` conflict bloki olib tashlandi
- [ui/pages/unified_settings.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/unified_settings.py) webhook URL ko'rsatmasi company-specific endpointga yangilandi

#### 2026-05-04 - Figma yo'q bo'lsa taxminiy dizayn xulosasi yozilishiga blok qo'yildi

- [services/checkers/tz_pr_checker.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/checkers/tz_pr_checker.py) ichida Figma ma'lumoti bo'lmasa promptga qat'iy taqiq qo'shildi
- AI endi `Figma bo'lmasa ham kodga qarab mos deb aytish mumkin` kabi taxminiy gaplarni yozmasligi kerak
- qo'shimcha himoya sifatida, Figma data bo'lmaganda AI yozib yuborgan `FIGMA DIZAYN MOSLIGI` bo'limi javobdan avtomatik olib tashlanadi

#### 2026-05-04 - Figma bo'limi endi yashirilmaydi, halol status ko'rsatadi

- [services/checkers/tz_pr_checker.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/checkers/tz_pr_checker.py) ichida Figma ma'lumoti bo'lmasa `FIGMA DIZAYN MOSLIGI` bo'limi saqlanadigan qilindi
- bu bo'lim endi taxminiy dizayn xulosasi emas, balki `Figma ma'lumotlari olinmadi` va `xulosa berib bo'lmaydi` degan aniq status xabarini ko'rsatadi

#### 2026-05-04 - Sidebar profil matnlari role-ga moslashtirildi

- [ui/pages/sidebar.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/sidebar.py) ichida sidebar header endi rolega qarab profil kartasi ko'rsatadi
- `super_admin`, `company_admin`, `user` uchun alohida subtitle va identity textlar qo'shildi
- [ui/i18n.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/i18n.py) ichiga role/profile copy uchun yangi translation kalitlari qo'shildi

#### 2026-05-04 - Figma access xatolari endi "usable data" deb hisoblanmaydi

- [services/checkers/tz_pr_checker.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/checkers/tz_pr_checker.py) ichiga `_has_usable_figma_data()` helper qo'shildi
- `token topilmadi`, `ruxsat yo'q`, `access yo'q`, `Error:` kabi Figma summary'lar endi real dizayn ma'lumoti sifatida qabul qilinmaydi
- shu sabab bunday holatda AI Figma bo'limi uchun taxminiy moslik xulosasi emas, faqat halol status xabari ko'rsatishi kerak

#### 2026-05-04 - Company admin Figma token formasi DB bilan qayta sync qilinadigan qilindi

- [ui/pages/unified_settings.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/unified_settings.py) ichida `uc_figma_rows` va `wh_figma_rows` uchun signature-based sync qo'shildi
- endi company admin yoki webhook Figma tokenlari saqlangandan keyin settings qayta ochilganda stale session cache emas, DB'dagi yangilangan qiymatlar ko'rinishi kerak

#### 2026-05-05 - Sozlamalar sidebar nav iyerarxiyasi vizual ravishda ajratildi

- [ui/pages/sidebar.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/sidebar.py) ichida `⚙️ Sozlamalar` toggle ko'rinishida qoldirildi va child linklar faqat bosilganda chiqadigan qilindi
- [ui/pages/unified_settings.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/ui/pages/unified_settings.py) ichida settings nav `columns`siz bitta vertikal daraxt ko'rinishiga o'tkazildi; top-level linklar `Sozlamalar` ostida, sub-linklar esa tanlangan top-level ostida yanada ichkarida chiqadi

#### 2026-05-07 - Gemini default fallback oqimi user/profile path uchun aniqlashtirildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx) ichida qo'shib yuborilgan dublikat `Profil Gemini AI (Admin)` bloki olib tashlandi; UI yana bitta standart `Gemini AI` kartasi bilan qoldi
- [frontend/src/app/api/settings/shared/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/shared/route.ts) `personal_*` vaqtinchalik maydonlaridan tozalandi va shared settings save/read kontrakti soddalashtirildi
- [services/api/settings_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/settings_api.py) ichida scope qattiqlashtirildi:
  - `company_admin` `is_company_admin=false` yo'lida faqat o'z user credentials'ini o'qiy/saqlay oladi
- [utils/auth/auth_config_helpers.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_config_helpers.py) ichida `build_user_credentials_for_service()` Gemini tanlash tartibi yangilandi:
  - avval user (profil) key
  - bo'sh bo'lsa super admin global default (`global_settings`)
  - legacy fallback sifatida `GEMINI_DEFAULT_API_KEY` env

#### 2026-05-07 - Company admin Settings sahifasi Claude UI tab layoutga o'tkazildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx) to'liq qayta ishlanib, `company_admin` uchun tablar qo'shildi:
  - `Webhook`
  - `AI & Integrations`
  - `Modullar`
- `AI & Integrations` bo'limi Claude UI oqimiga moslandi:
  - JIRA URL/email/token
  - GitHub token/organization
  - Gemini uchun info notice (`har bir foydalanuvchi o'zi kiritadi`)
- `Webhook` bo'limi real read/save bilan ulandi:
  - trigger status
  - return threshold
  - min TZ belgilar
  - checker kechikishi
  - istisno assigneelar
  - skip kodi
  - auto-return on/off
- yangi Next route qo'shildi: [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts)
- backend bridge helperlar qo'shildi: [frontend/src/lib/backend.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/backend.ts)
- FastAPI settings router kengaytirildi:
  - `POST /api/settings/webhook/config/read`
  - `POST /api/settings/webhook/config/save`
  - fayl: [services/api/settings_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/settings_api.py)

#### 2026-05-07 - Admin Settings'dagi "Not Found" xatosi webhook save/read oqimida tuzatildi

- [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts) ichida webhook read/save backend chaqiruvlari `internal RPC`ga o'tkazildi:
  - `get_app_settings_for_company`
  - `save_company_webhook_module_settings`
  - `save_company_settings`
- natija: backend yangi `/api/settings/webhook/config/*` route'lari restart bo'lmagan holatda ham `company_admin` settings save oqimi `404 Not Found` bermaydi

#### 2026-05-07 - Company Admin Settingsdan "Modullar" tabi olib tashlandi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx) ichida `company_admin` tablari `Webhook` va `AI & Integrations` bilan cheklandi
- `Modullar` tabi va unga tegishli render bo'limi olib tashlandi (bu qism super admin oqimida qoladi)
- [frontend/src/app/(app)/settings/page.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/(app)/settings/page.tsx) ichida endi `moduleFlags` prop uzatilmaydi

#### 2026-05-07 - Admin token inputlari saqlagandan keyin mask ko'rinishda saqlanadigan qilindi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx) ichida `JIRA Token` va `GitHub Token` oqimi yangilandi:
  - saqlangandan keyin input qiymati bo'shab ketmaydi
  - token `*` bilan masklanadi va faqat oxirgi 4 ta belgi ko'rinadi
  - inputlar edit qilinadigan holatda qoladi (focusda yangi token kiritish mumkin, bo'sh qoldirilsa oldingi mask qayta tiklanadi)
- [frontend/src/app/api/settings/shared/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/shared/route.ts) ichida `jira_token_mask` va `github_token_mask` maydonlari response'ga qo'shilib, frontendga xavfsiz ko'rinishda uzatildi
- [frontend/src/lib/types.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/types.ts) ichida shared settings response tiplari token mask maydonlari bilan kengaytirildi

#### 2026-05-07 - Company lifecycle + module/access qoidalari product talablarga moslashtirildi

- Super admin create company oqimi yangilandi:
  - [frontend/src/app/api/super-admin/companies/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/super-admin/companies/route.ts) ichida `seat_limit` endi `0`dan boshlanishi mumkin (`0+`)
  - create form defaulti `seat_limit=0` va webhook addon toggle bilan ishlaydi
  - fayl: [frontend/src/components/super-admin-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/super-admin-panel.tsx)
- Module boshqaruvi qattiqlashtirildi:
  - bazaviy modullar (`tz_pr_checker`, `testcase_generator`) doim plan orqali ON
  - `monitoring` webhookdan hosil bo'ladigan derived modul sifatida qoldirildi
  - super admin patch route faqat pullik addon (`webhook`)ni toggle qiladi
  - fayl: [frontend/src/app/api/super-admin/companies/[companyId]/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/super-admin/companies/[companyId]/route.ts)
- Webhook access policy enforce qilindi:
  - [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts) endi `get_effective_company_modules().webhook` bo'yicha tekshiradi
  - webhook yoqilmagan company uchun `403`
  - settings UI webhook tabi ham modul holatiga qarab ko'rsatiladi
  - fayllar:
    - [frontend/src/app/(app)/settings/page.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/(app)/settings/page.tsx)
    - [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx)
- Monitoring access ham modulga bog'landi:
  - [frontend/src/app/(app)/monitoring/page.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/(app)/monitoring/page.tsx) da `company_admin` uchun `monitoring` modul yoqilmagan bo'lsa page bloklanadi
- Integrations va Gemini fallback zanjiri requirementga moslashtirildi:
  - admin settingsga `Figma Token` va shared `Gemini` maydonlari qo'shildi
  - user credential oqimi: `user key` → `company shared key` → `super admin default` → `env legacy`
  - fayllar:
    - [frontend/src/app/api/settings/shared/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/shared/route.ts)
    - [frontend/src/lib/types.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/types.ts)
    - [utils/auth/auth_config_helpers.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_config_helpers.py)
    - [utils/auth/auth_db.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_db.py)

#### 2026-05-07 - Company create xatolari uchun debug logging qo'shildi

- [frontend/src/app/api/super-admin/companies/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/super-admin/companies/route.ts) ichida company create oqimiga `debugId` qo'shildi:
  - start/success/fail bosqichlari `console`ga aniq yoziladi
  - generic xato holatida response'ga `Debug ID` qaytariladi
  - qo'shimcha ravishda `data/company_create_debug.log` fayliga ham yoziladi (persistent)
- [utils/auth/auth_db.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/auth_db.py) ichida `create_company()` bosqichma-bosqich loglanadi:
  - `create_company_record` yiqilishi
  - `insert_company_module_settings` yiqilishi
  - `create_default_company_subscription` yiqilishi
  - muvaffaqiyatli create holati
- [utils/auth/company_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/company_repository.py) ichida swallow bo'lib ketayotgan exceptionlar endi `exc_info=True` bilan loglanadi:
  - `create_company_record`
  - `insert_company_module_settings`
  - `create_default_company_subscription`
- natija: UI'da generic “Kompaniya yaratilmadi” ko'rinsa ham, `data/webhook.log` va server loglarda aniq sabab trace qilinadi

#### 2026-05-07 - Company create `seat_limit=0` PostgreSQL constraint muammosi bartaraf etildi

- Debug ID `124ca109` bo'yicha aniqlangan root-cause:
  - company create `duplicate=false` bo'lsa ham `create_company` `None` qaytgan
  - PostgreSQL `companies` jadvalida legacy check constraint `seat_limit >= 1` bo'lgani uchun `seat_limit=0` insert yiqilgan
- Runtime fix:
  - DB constraint qo'lda yangilandi: `companies_seat_limit_check => seat_limit >= 0`
  - fayl: [utils/auth/company_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/company_repository.py) ichida auto-compat helper qo'shildi:
    - `_ensure_companies_seat_limit_allows_zero(conn)`
    - `create_company_record()` va `update_company_seat_limit_value()` oldidan ishga tushadi
- Initial PostgreSQL schema ham yangilandi:
  - [database/postgresql/001_initial_schema.sql](/Users/mac/Documents/projects/JIRA-AI-Analyzer/database/postgresql/001_initial_schema.sql) da `CHECK (seat_limit >= 0)`

#### 2026-05-08 - Company Admin Settingsga Modules tab qayta qo'shildi (Checker + Testcase)

- `company_admin` settings paneliga yangi `🧩 Modules` tabi qo'shildi:
  - fayl: [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx)
  - `TZ-PR Checker` bo'limi:
    - `default_use_smart_patch` (checker run payload defaultini settingdan boshqarish)
    - `Comment Bo'limlarini Ko'rsatish` (`visible_sections`)
    - `AI ga ma'lumotlar darajasi (tartibi)` (`ai_data_section_order`)
    - `Comment O'qish` (`read_comments_enabled`, `max_comments_to_read`)
  - `Test Case Generator` bo'limi:
    - `Default Sozlamalar` (`default_include_pr`, `default_use_smart_patch`, `default_test_types`, `max_test_cases`)
    - `AI ga ma'lumotlar darajasi (tartibi)` (`ai_data_section_order`)
    - `Comment O'qish` (`read_comments_enabled`, `max_comments_to_read`)

- Modul sozlamalari uchun yangi backend API qo'shildi:
  - fayl: [services/api/settings_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/settings_api.py)
  - endpointlar:
    - `POST /api/settings/modules/config/read`
    - `POST /api/settings/modules/config/save`
  - checker/testcase uchun allowed qiymatlar validatsiyasi qo'shildi
  - save oqimi `user_module_settings` bilan merge-upsert qiladi (oldingi boshqa fieldlar yo'qolmaydi)

- Frontend server route va backend connector qo'shildi:
  - [frontend/src/app/api/settings/modules/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/modules/route.ts)
  - [frontend/src/lib/backend.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/backend.ts)
  - [frontend/src/lib/types.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/types.ts)

- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-11 - Number inputda `0-100` badge va spinner overlap muammosi yakuniy tuzatildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `NumberField` ichidagi inline `paddingRight` olib tashlandi.
  - `max` bor holatlar uchun `input-with-bound` klassi qo'shildi.
- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.num-bound` `right: 44px` ga surildi.
  - `.num-field .input[type="number"].input-with-bound` uchun `padding-right: 110px` berildi.

#### 2026-05-11 - Number input global spinner override rollback qilindi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `::-webkit-inner-spin-button` va `::-webkit-outer-spin-button` uchun global override olib tashlandi.
  - Oddiy number inputlar browser default spinner joylashuviga qaytarildi.

#### 2026-05-11 - Number input strelkalari ko'rinishi tiklandi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.num-bound` o'ngdan `32px` ga surildi va `pointer-events: none` berildi.
  - `type="number"` inputga `padding-right: 78px` berilib, spinner uchun joy ajratildi.
  - WebKit spinner pseudo-elementlari uchun `opacity: 1` qo'yildi.

#### 2026-05-11 - Text input va strelkali number input o'lchamlari bir xil qilindi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `NumberField` ichidagi `type="number"` inputga `settings-form-input` klassi qo'shildi.
  - Natijada text input va number input balandligi/radius/padding qiymatlari bir xil bo'ldi.

#### 2026-05-11 - Webhook Servis-1 va Servis-2 subtitle osti spacing 1:1 tenglashtirildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `Servis-2: Webhook Testcase` ichidagi ortiqcha wrapper (`ssec mt-4 border-none pt-0`) olib tashlandi.
  - Natijada `Servis-1` va `Servis-2`da subtitle'dan birinchi ichki kartgacha bo'lgan masofa bir xil bo'ldi.

#### 2026-05-11 - Webhook kartalarda sarlavha va ichki kart oralig'i bir xil qilindi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.ssec.border-none` uchun `margin-top: 8px` berilib, text va keyingi blok orasidagi bo'shliq qisqartirildi.
  - `.webhook-family-stack` `margin-top` qiymati `14px`dan `8px`ga tushirildi.

#### 2026-05-11 - Webhook servis kart rangi och yashilga yangilandi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.webhook-service-card--main` light mode gradienti och yashil tonlarga almashtirildi.
  - Border va shadow qiymatlari yangi och yashil fon bilan uyg'unlashtirildi.

#### 2026-05-11 - Settings kartlardagi keraksiz gorizontal chiziqlar olib tashlandi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.ssec.border-none` override qo'shilib, `ssec` bloklarida keraksiz `border-top` chiziq chiqishi to'xtatildi.
  - `.ssec.pt-0` override qo'shilib, `pt-0` berilgan joylarda `padding-top` nolga tushirildi.

#### 2026-05-11 - Webhook Testcase sarlavha yozuvi olib tashlandi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `Servis-2: Webhook Testcase` kartidagi `Webhook Testcase (Auto-comment)` sarlavha matni olib tashlandi.

#### 2026-05-11 - Webhook Testcase kartida Trigger bo'limi birinchi qilindi, alias input olib tashlandi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `Servis-2: Webhook Testcase` ichida `Trigger sozlamalari` karti `Auto-comment oilasi` kartidan yuqoriga ko'chirildi.
  - `Trigger aliaslar (vergul bilan)` inputi UI'dan olib tashlandi.
  - `Asosiy trigger status` inputi saqlab qolindi.

#### 2026-05-08 - `setting_UI` asosida Admin Settings (Modules + Webhook) UI 1:1 ulab chiqildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx) ichida `Modules` va `Webhook` tablari `setting_UI/QA-Assistant-v2.html` dagi dizayn asosida qayta yig'ildi:
  - `scard` header bloklari (ikon + title + description)
  - `Toggle` row, `CheckGroup`, `OrderPills` (drag reorder), `NumberField`, `TagInput` UI patternlari
  - `dirty` indikatorlar va `save-footer` holati
  - webhook preview bloki (`trigger`, `auto_return`, `threshold`, `delay`, `skip_code`)
- Trigger status tag input 1:1 ishlashi uchun webhook save oqimi status ro'yxatini ham saqlaydigan qilindi:
  - [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx) POST payloadga `trigger_statuses` qo'shildi
  - [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts) ichida `trigger_status_aliases` hisoblanib `webhook_tz_pr` settingga saqlanadi
- Mavjud backend API contract saqlab qolindi:
  - `/api/settings/modules` va `/api/settings/webhook` payloadlari o'zgarmadi
  - UI yangi ko'rinishga ulansa ham mavjud save/read logika ishlaydi
- Validatsiya frontda ko'rsatildi:
  - modules: max test case (1-50), checker/testcase order majburiy elementlari
  - webhook: threshold (0-100), delay (>=1), min_tz (>=0)
- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css) ga settings redesign uchun kerakli classlar qo'shildi:
  - `tog-*`, `chk-*`, `order-*`, `num-*`, `tag-*`, `scard-*`, `ssec`, `dirty-badge`, `save-footer`, `err-text`
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅
- Admin Settings `Webhook` tab UI elementlari umumiy settings bilan bir xil ko'rinishga keltirildi:
  - `Trigger statuslari`, `Asosiy trigger status`, `Istisno assigneelar`, `Skip kodi` bloklari `Field` komponentiga o'tkazildi
  - webhook formdagi matn/label/hint tipografiyasi qolgan settings bo'limlari bilan bir xil bo'ldi
  - `TagInput` ichki input uchun font/height va `-webkit-autofill` override qo'shildi (oq fon chiqib ketishi bartaraf etildi)
  - fayllar: [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx), [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css)

#### 2026-05-08 - Checker uchun Figma text va comment extraction qo'shildi

- [utils/figma/figma_client.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/figma/figma_client.py) yangilandi:
  - `get_text_snippets()` qo'shildi:
    - `node-id` bo'yicha `/files/{file_key}/nodes?ids=...&depth=12` orqali subtree ichidagi `TEXT` layer'lar olinadi
    - text tozalanadi (whitespace normalize), dublikatlar qisqartiriladi
  - `get_file_comments()` qo'shildi:
    - `/files/{file_key}/comments` orqali Figma comment'lar olinadi
    - author/message/node_id maydonlari AI-friendly formatga keltiriladi
  - `get_file_summary()` endi faqat frame metadata emas, balki:
    - `📝 FIGMA MATNLARI`
    - `💬 FIGMA COMMENT'LAR`
    bo'limlarini ham qaytaradi
- [services/checkers/tz_pr_checker.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/checkers/tz_pr_checker.py) Figma prompt ko'rsatmalari yangilandi:
  - AI endi frame bilan birga Figma text/comment talablarini ham tahlil qiladi
- Real tekshiruv (DEV-8220 link, `node-id=1337:16`)da quyidagilar tasdiqlandi:
  - `Import funksiyasida xam shablonga 8 qatoriga Коментарии...`
  - `Nastroykada xam qoshib korsatish kerak`
  - `150/150`
  matnlari extractor natijasida chiqdi.

#### 2026-05-08 - SQLite fallback butunlay o'chirildi (Postgres-only)

- `start.sh` dagi `choose_database_backend()` logikasi yangilandi:
  - `APP_DB_BACKEND` endi faqat `postgres` bo'lishi mumkin
  - PostgreSQL ulanmasa endi `sqlite`ga fallback qilinmaydi, servis start to'xtaydi
- [utils/database/runtime.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/database/runtime.py) da runtime darajasida qat'iy cheklov qo'shildi:
  - `APP_DB_BACKEND != postgres` bo'lsa `RuntimeError` bilan to'xtaydi
  - `connect_auth_db()` va `connect_processing_db()` endi doim `connect_postgres()` ishlatadi
- Natija: tizim kod darajasida ham, startup darajasida ham `postgres-only` rejimga o'tdi.

#### 2026-05-08 - Company admin uchun webhook settings save ruxsati tiklandi (Internal RPC)

- Muammo: company admin `Settings -> Webhook` da saqlash paytida
  `save_company_webhook_module_settings operation company admin uchun ruxsat etilmagan`
  xatosi chiqayotgan edi.
- Sabab: [services/api/internal_rpc_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/internal_rpc_api.py) dagi
  `_COMPANY_ADMIN_COMPANY_ARG0_OPS` whitelist ichida webhook save operatsiyalari yo'q edi.
- Tuzatish:
  - `save_company_webhook_module_settings`
  - `save_company_settings`
  operatsiyalari company-admin scoped whitelist'ga qo'shildi.
- Testlar:
  - yangi test fayl: [tests/test_internal_rpc_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/tests/test_internal_rpc_api.py)
  - tekshiradi:
    - company admin o'z company scope'ida webhook save RPC chaqira oladi
    - boshqa company scope bloklanadi (`403`)
  - run: `./.venv/bin/pytest -q tests/test_internal_rpc_api.py` ✅ (`3 passed`)

#### 2026-05-08 - Webhook settings route `internal_rpc` save bog'liqligidan chiqarildi

- Muammo qayta kuzatildi: ayrim running backend instance'larda `save_company_webhook_module_settings` RPC whitelist xatosi davom etayotgan edi.
- [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts) yangilandi:
  - `GET /api/settings/webhook` endi webhook config'ni `readWebhookConfigWithBackend` orqali (`/api/settings/webhook/config/read`) oladi.
  - `POST /api/settings/webhook` endi saqlashni `saveWebhookConfigWithBackend` orqali (`/api/settings/webhook/config/save`) bajaradi.
  - Natija: webhook save oqimi `internal_rpc` whitelist'ga to'g'ridan-to'g'ri bog'liq bo'lmay qoldi.
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-10 - Webhook sozlamalari 3-kartga ajratildi (Checker / Testcase / Shared)

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx) ichida Webhook UI tuzilmasi yangilandi:
  - `Servis-1: Webhook TZ-PR` kartida faqat checkerga xos trigger va return logikalari qoldirildi.
  - `Servis-2: Webhook Testcase` karti testcase auto-comment/generatsiya sozlamalari uchun alohida qoldi.
  - yangi `Servislar uchun umumiy` karti qo'shildi va ikkala servisga birdek taalluqli filtrlar shu yerga ko'chirildi:
    - `allowed_issue_types`
    - `excluded_assignees`
    - `skip_code`
    - `max_skip_check_comments`
    - `min_tz_description_chars`
- Eslatma: faqat UI joylashuvi o'zgardi, webhook save/read payload va backend logikasi o'zgarmadi.
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-10 - Checker kartiga `AI_SKIP xabar matni` qaytarildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `Skip boshqaruvi` bo'limida `AI_SKIP xabar matni` (`skip_comment_text`) qo'shildi.
  - `Skip kodi` yoqilgan (bo'sh emas) holatda child field sifatida ko'rinadi.
- [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts):
  - `GET /api/settings/webhook` javobiga `skip_comment_text` qo'shildi.
  - `POST /api/settings/webhook` saqlash payload'iga `skip_comment_text` uzatish qo'shildi.
- [frontend/src/lib/types.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/types.ts):
  - `WebhookSettingsView` va `WebhookSettingsSaveRequest` tiplariga `skip_comment_text` qo'shildi.
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-10 - `SKIP xabar matni` inputiga default qiymat avtomatik yozilishi yoqildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `skip_comment_text` default qiymati bo'sh emas qilib yangilandi.
  - Webhook read natijasida `skip_comment_text` bo'sh bo'lsa, input default matn bilan to'ldiriladi.
- [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts):
  - `GET /api/settings/webhook` da `skip_comment_text` bo'sh bo'lsa default matn qaytariladi.
  - `POST /api/settings/webhook` da foydalanuvchi bo'sh yuborsa default matn saqlashga ketadi.
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-10 - Webhook Checker settings kengaytirildi (Modules tabdan mustaqil)

- Webhook `Servis-1 (Checker)` uchun quyidagi sozlamalar UI + API oqimiga qo'shildi:
  - `📝 Comment Bo'limlarini Ko'rsatish` (`show_contradictory_comments`, `visible_sections`)
  - `📊 AI ga ma'lumotlar darajasi (tartibi)` (`ai_data_section_order`)
  - `📖 Comment O'qish` (`read_comments_enabled`, `max_comments_to_read`)
  - `🎨 Comment Format` (`use_adf_format`)
  - `Qaytarish Notification Matn` (`return_notification_text`)
  - `Re-check Xabari` (`recheck_comment_text`)
  - `TZ-PR Comment Footer` (`tz_pr_footer_text`)
- Backend:
  - [services/api/settings_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/settings_api.py) dagi
    `webhook/config/read` va `webhook/config/save` endpointlari ushbu maydonlarni o'qish/saqlashni qo'llab-quvvatlaydi.
  - Saqlash `webhook_tz_pr` scope ichida qoladi (user-level `modules` checker sozlamalaridan alohida).
- Frontend:
  - [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts) yangi checker maydonlarini backendga uzatadi.
  - [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx) da webhook checker kartiga alohida bo'limlar qo'shildi.
  - [frontend/src/lib/types.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/lib/types.ts) tiplar yangilandi.
- Tekshiruv:
  - `./.venv/bin/python -m py_compile services/api/settings_api.py` ✅
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-10 - SaaS scope leak tuzatildi (UI vs Webhook, Checker/Testcase)

- `UI` va `Webhook` sozlamalari aralashib ketayotgan 2 ta nuqta tuzatildi:
  1. [services/webhook/skip_detector.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/skip_detector.py)
     - `max_skip_check_comments` endi global `tz_pr_checker`dan olinmaydi.
     - qiymat `jira_webhook_handler`dan `webhook_tz_pr.max_skip_check_comments` sifatida uzatiladi.
  2. [services/generators/testcase_generator.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/generators/testcase_generator.py)
     - UI testcase oqimida `min_tz_description_chars` endi `get_app_settings_for_user(...).tz_pr_checker`dan olinadi.
     - Webhook testcase oqimida esa `get_app_settings_for_company(...).webhook_tz_pr` saqlanib qoladi.
- [services/webhook/jira_webhook_handler.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/jira_webhook_handler.py):
  - `_check_skip_code()` chaqiruvida `max_comments=settings.max_skip_check_comments` berilishi qo'shildi.
- Tekshiruv:
  - `./.venv/bin/python -m py_compile services/webhook/skip_detector.py services/webhook/jira_webhook_handler.py services/generators/testcase_generator.py` ✅

#### 2026-05-10 - `Zid commentlar` alohida toggle o'rniga `Comment bo'limlari` ichiga qo'shildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `📝 Comment bo'limlari` checklistiga `contradictory_comments` (`Zid commentlar`) itemi qo'shildi.
  - `show_contradictory_comments` endi shu item tanlanishiga bog'landi.
- [services/api/settings_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/settings_api.py):
  - webhook checker `visible_sections` uchun `contradictory_comments` ruxsat etildi.
  - `show_contradictory_comments` va `visible_sections` o'rtasida read/save paytida sinxronizatsiya qo'shildi.
- Tekshiruv:
  - `./.venv/bin/python -m py_compile services/api/settings_api.py` ✅
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-11 - Webhook Testcase kartasi Checker uslubidagi ona-bola oilaviy ko'rinishga moslashtirildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `Servis-2: Webhook Testcase` ichida `Auto-comment oilasi` saqlanib, trigger sozlamalari alohida `Trigger oilasi` sifatida vertikal ona-bola ko'rinishga ajratildi.
  - `Asosiy trigger status` to'ldirilgandagina `Trigger aliaslar` maydoni ko'rsatiladigan shart qo'shildi.
  - Testcase input qiymatlari (`trigger status`, `trigger aliases`, `footer`) uchun `?? ""` qo'llanib controlled/uncontrolled input ogohlantirishi xavfi yopildi.
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-11 - Webhook kartlar spacing/rang ierarxiyasi standartlashtirildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - Webhook bo'limiga yangi vizual classlar ulandi: `webhook-cards-grid`, `webhook-service-card`, `webhook-service-card--checker`, `webhook-family-stack`, `webhook-family-card`, `webhook-family-item`.
  - `Servis-1: Webhook TZ-PR` kartasi alohida `webhook-service-card--checker` bilan belgilandi (asosiy karta to'qroq).
  - Checker va Testcase ichidagi oilaviy kart stacklari bir xil spacingga keltirildi.
- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - Webhook uchun card ierarxiyasi bo'yicha yangi stillar qo'shildi:
    - asosiy servis kart,
    - checker asosiy kart (toqroq),
    - oilaviy kart,
    - bola setting kart.
  - Light va dark mavzular uchun alohida rang balanslari berildi.
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-11 - Webhook kart rang kontrasti kuchaytirildi (aniq ko'rinadigan farq)

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `webhook-service-card`, `webhook-service-card--checker`, `webhook-family-card`, `webhook-family-item` ranglari kuchaytirildi.
  - `Checker` asosiy karta aniqroq to'q qilib ajratildi (border + shadow ham kuchaytirildi).
  - Stil override bo'lib ketmasligi uchun webhook kart qatlamlarida kerakli joylarda `!important` qo'llandi.
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-11 - Faqat asosiy webhook karta bo'yashga qaytarildi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `webhook-family-card` va `webhook-family-item` rang override'lari olib tashlandi (bola settinglar default rangga qaytdi).
  - `webhook-service-card` default kart rangiga qaytarildi.
  - `webhook-service-card--checker` rangli qoldirildi (asosiy checker karta ajralib turadi).
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-11 - Checkerdagi qo'shimcha bo'limlar ham oilaviy kichik kartlarga o'tkazildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `Asosiy trigger status` (`Trigger sozlamalari`) alohida `webhook-family-card` ichiga olindi.
  - `📝 Comment bo'limlari` alohida kichik kartga o'raldi.
  - `📊 AI ga ma'lumotlar darajasi (tartibi)` alohida kichik kartga o'raldi.
  - `Mustaqil settinglar` alohida kichik kartga o'ralib, ichidagi `Re-check Xabari` va `TZ-PR Comment Footer` `webhook-family-item` bilan bir xil family uslubga keltirildi.
  - Natijada checker ichida oilaviy va sanab o'tilgan qo'shimcha bo'limlar bir xil kart ierarxiyasida ko'rinadi.
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-11 - Webhook Testcase kartasi checkerga mos oilaviy bo'linishga keltirildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `Auto-comment oilasi` ichidan `Asosiy trigger status` bo'limi ajratilib, alohida `Trigger sozlamalari` oilaviy kartiga o'tkazildi.
  - `📊 AI ga ma'lumotlar darajasi (tartibi)` alohida oilaviy kartga ajratildi.
  - `Mustaqil settinglar` ichida `Default test turlari` blokining ichki section stili oilaviy item stiliga moslashtirildi.
  - Barcha bo'linmalar `webhook-family-card` + `webhook-family-item` ko'rinishida bir xil ierarxiyada qoldi.
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-11 - Webhook asosiy kartlar rangi bir xillashtirildi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `webhook-service-card--testcase` rangi `webhook-service-card--checker` bilan bir xil qilindi (light/dark mode ikkalasida ham).
  - Asosiy kartlar endi yagona vizual stilga ega.
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-11 - Webhook asosiy kartlar bitta classga birlashtirildi (100% bir xil stil)

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `Servis-1` va `Servis-2` asosiy kartlari `webhook-service-card--main` classiga o'tkazildi.
- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `webhook-service-card--checker` va `webhook-service-card--testcase` o'rniga yagona `webhook-service-card--main` ishlatildi.
  - Dark mode uchun ham yagona `.dark .webhook-service-card--main` qoldirildi.
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-11 - Asosiy webhook kart rangi kuchaytirildi (oq ko'rinishni bartaraf etish)

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `webhook-service-card--main` light ranglari to'qroq gradientga o'tkazildi.
  - Border va shadow kontrasti oshirildi.
  - Dark mode ranglari ham biroz kuchaytirildi.
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-11 - Webhook Checker `Comment format (ADF)` sozlamasi olib tashlandi va `True` ga qotirildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - Webhook Checker ichidagi `Comment format (ADF)` toggle UI'dan olib tashlandi.
  - Webhook settings yuklash/saqlashda checker uchun `use_adf_format` qiymati doim `true` yuboriladigan qilindi.
- [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts):
  - `GET` va `POST` oqimida checker `use_adf_format` maydoni majburan `true` qilindi.
- [services/api/settings_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/settings_api.py):
  - `webhook/config/read` checker `use_adf_format`ni doim `True` qaytaradi.
  - `webhook/config/save` checker `use_adf_format`ni doim `True` saqlaydi.
- [config/app_settings.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/config/app_settings.py):
  - Company/user scope merge bosqichida `webhook_tz_pr.use_adf_format` qiymati doim `True` ga qotirildi (oldin DB da `false` bo'lsa ham runtime `true` ishlaydi).
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅
  - `./.venv/bin/python -m py_compile services/api/settings_api.py config/app_settings.py` ✅

#### 2026-05-11 - Webhook Testcase `ADF format` sozlamasi olib tashlandi va `True` ga qotirildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - Webhook Testcase ichidagi `ADF format` toggle UI'dan olib tashlandi.
  - Testcase webhook settings load/save oqimida `testcase_use_adf_format` doim `true` qilib yuboriladigan qilindi.
- [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts):
  - `GET` va `POST` oqimida `testcase_use_adf_format` maydoni majburan `true` qilindi.
- [services/api/settings_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/settings_api.py):
  - `webhook/config/read` da `testcase_use_adf_format` doim `True` qaytariladi.
  - `webhook/config/save` da webhook testcase `use_adf_format` doim `True` saqlanadi.
- [config/app_settings.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/config/app_settings.py):
  - Company/user scope merge bosqichida `webhook_testcase.use_adf_format` doim `True` ga qotirildi (DB'da eski `false` bo'lsa ham runtime `true` ishlaydi).
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅
  - `./.venv/bin/python -m py_compile services/api/settings_api.py config/app_settings.py` ✅

#### 2026-05-11 - Webhook Testcase `AI max output tokens` sozlamasi olib tashlandi va `16384` ga qotirildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - Webhook Testcase ichidagi `AI max output tokens` inputi UI'dan olib tashlandi.
  - Webhook settings load/save oqimida `testcase_ai_max_output_tokens` doim `16384` bo'lib yuboriladi.
- [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts):
  - `GET` va `POST` oqimida `testcase_ai_max_output_tokens` majburan `16384` qilindi.
- [services/api/settings_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/settings_api.py):
  - `webhook/config/read` da `testcase_ai_max_output_tokens` doim `16384` qaytariladi.
  - `webhook/config/save` da webhook testcase `ai_max_output_tokens` doim `16384` saqlanadi.
- [config/app_settings.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/config/app_settings.py):
  - Company/user scope merge bosqichida `webhook_testcase.ai_max_output_tokens` doim `16384` ga qotirildi (DB'da eski boshqa qiymat bo'lsa ham runtime `16384` ishlaydi).
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅
  - `./.venv/bin/python -m py_compile services/api/settings_api.py config/app_settings.py` ✅

#### 2026-05-11 - Token limitlar markaziy boshqaruvga o'tkazildi (single source policy)

- [config/token_limits.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/config/token_limits.py):
  - Yangi markaziy policy qo'shildi:
    - `CHECKER_MAX_OUTPUT_TOKENS`
    - `TESTCASE_MAX_OUTPUT_TOKENS`
    - `AI_MAX_INPUT_TOKENS`
    - `CHARS_PER_TOKEN`
    - `GEMINI_HELPER_DEFAULT_MAX_OUTPUT_TOKENS`
- [config/app_settings.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/config/app_settings.py):
  - Dataclass default token qiymatlari markaziy policy constantlariga ulandi.
  - `_enforce_token_policy()` qo'shilib, global/company/user scope settingslarida token limitlar majburan bir xil qo'llanadigan qilindi.
- [services/api/settings_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/settings_api.py):
  - Webhook testcase output token qiymati markaziy policydan qaytariladi/saqlanadi.
  - System config (`ai_max_input_tokens`, `chars_per_token`) read/save oqimlari markaziy policyga qotirildi (payload bilan o'zgarmaydi).
- [core/base_service.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/core/base_service.py):
  - Fallback defaultlar (`ai_max_input_tokens`, `chars_per_token`) ham markaziy policyga ulandi.
- [utils/ai/gemini_helper.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/ai/gemini_helper.py):
  - `analyze()` default `max_output_tokens` qiymati markaziy policy constantiga ulandi.
- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - System tabdagi `AI max input tokens` va `Chars per token` inputlari UI'dan olib tashlandi.
  - Webhook testcase `AI max output tokens` inputi oldinroq olib tashlangan holat davom ettirildi.
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅
  - `./.venv/bin/python -m py_compile config/token_limits.py config/app_settings.py services/api/settings_api.py core/base_service.py utils/ai/gemini_helper.py` ✅

#### 2026-05-11 - `settings-panel.tsx` token qoldiq maydonlari tozalandi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `WebhookFormState` dan keraksiz maydonlar olib tashlandi:
    - `use_adf_format`
    - `testcase_ai_max_output_tokens`
    - `testcase_use_adf_format`
  - `SystemFormState` dan keraksiz maydonlar olib tashlandi:
    - `ai_max_input_tokens`
    - `chars_per_token`
  - `EMPTY_WEBHOOK_FORM` va `EMPTY_SYSTEM_FORM` defaultlaridan shu maydonlar chiqarildi.
  - Webhook/System load mapping (API payload type + `setWebhookForm`/`setSystemForm`) dan keraksiz token maydonlar tozalandi.
  - UI olib tashlangan bo'lsa-da backend policy uchun kerak bo'lgan qiymatlar `saveWebhook` payloadida hardcoded qolgan.
- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅

#### 2026-05-11 - Number input global spinner override rollback qilindi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  -  uchun global override olib tashlandi.
  - Oddiy number inputlar browser default spinner joylashuviga qaytarildi.

#### 2026-05-11 - Return threshold input ichidagi `0-100` badge olib tashlandi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `NumberField` ichidagi `num-bound` (`0-max`) badge renderi olib tashlandi.
- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `num-bound` va `input-with-bound` bilan bog'liq CSS qoidalari olib tashlandi.
  - Diapazon ma'lumoti endi faqat hint matnida ko'rsatiladi.

#### 2026-05-11 - `Max commentlar` kartidagi pastki ortiqcha bo'shliq qisqartirildi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.webhook-family-item` uchun padding `10px 12px` qilib ixchamlashtirildi.
  - Hint matndan keyingi pastki bo'shliq kamaytirildi va oilaviy kart ichki spacinglari bir xilga yaqinlashtirildi.

#### 2026-05-11 - Webhook family item ichida `field` pastki margini nolga tushirildi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.webhook-family-item .field { margin-bottom: 0; }` qo'shildi.
  - `Max commentlar` blokidagi hintdan keyingi ortiqcha pastki bo'shliq bartaraf etildi.

#### 2026-05-11 - `Servislar uchun umumiy` karti birinchi o'ringa olindi va gorizontal yoyildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - Webhook kartlar ichida `Servislar uchun umumiy` bloki yuqoriga (birinchi) ko'chirildi.
- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.webhook-shared-card { grid-column: 1 / -1; }` qo'shilib, kart ikki ustunni to'liq egallaydigan qilindi.

#### 2026-05-11 - `Min TZ belgilari` hintidan keyingi ortiqcha pastki bo'shliq olib tashlandi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.webhook-cards-grid .rounded-lg > .field { margin-bottom: 0; }` qo'shildi.
  - `Servislar uchun umumiy` kartidagi `Min TZ belgilari` blokida hintdan keyin qoladigan ortiqcha joy bartaraf etildi.

#### 2026-05-11 - `Servislar uchun umumiy` ichki bloklari webhook oilasi spacingiga tenglashtirildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `Ruxsat etilgan issue type'lar`, `Istisno assigneelar`, `Min TZ belgilari` bloklariga `webhook-family-item` klassi qo'shildi.
  - Ichki padding va hintdan keyingi pastki bo'shliq boshqa kartlar bilan bir xilga keltirildi.

#### 2026-05-11 - Settings inputlari oq fon rangga birxillashtirildi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.input`, `.select`, `.settings-form-input`, `.settings-form-select` foni oq (`#fff`) qilindi.
  - `num-field/select/tag-input` uchun ko'kimtir gradient override olib tashlanib oq fonga o'tkazildi.
  - Dark override'larda ham shu inputlar oq fon bilan bir xil ko'rinadigan qilindi.

#### 2026-05-11 - `Joriy konfiguratsiya ko'rinishi` preview bloki olib tashlandi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - Webhook bo'limidagi `Joriy konfiguratsiya ko'rinishi` (`analysis-block`) sectioni to'liq olib tashlandi.

#### 2026-05-11 - Dark mode input fonlari qayta tiklandi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.dark .input, .dark .select` oq foni olib tashlanib `var(--bg-strong)`ga qaytarildi.
  - Dark mode `num-field/select/tag-input` foni to'q gradient holatiga qaytarildi.
  - Light mode inputlar oq fon holatida saqlab qolindi.

#### 2026-05-11 - Dark mode uchun `settings-form-input` oq fon override'i tuzatildi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.dark .settings-form-input, .dark .settings-form-select` uchun `background: var(--bg-strong) !important` qo'shildi.
  - Light mode oq inputlar saqlanib, dark mode inputlar to'q fon bilan ko'rinadigan bo'ldi.

#### 2026-05-11 - Settings input foni tema-variable ga qaytarildi (light/dark auto)

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `settings-form-input/select` foni `#fff`dan `var(--surface-strong)`ga qaytarildi.
  - `.dark .settings-form-*` override olib tashlandi; rang endi theme variable orqali avtomatik boshqariladi.

#### 2026-05-11 - System sozlamalari scope'i ajratildi (company admin -> super admin)

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `Company Admin > Settings > Tizim` bo'limidan platform-level bo'lgan maydonlar olib tashlandi:
    - `ai_max_retries`, `key_freeze_duration`, `db_busy_timeout`, `db_connection_timeout`, `http_timeout`, `executor_timeout`
  - Company admin tizim bo'limida faqat tenant-level queue oqimiga bevosita ta'sir qiladigan maydonlar qoldirildi.

- [frontend/src/components/super-admin-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/super-admin-panel.tsx):
  - Super admin panelga yangi `System` tabi qo'shildi.
  - Platform-level 6 ta runtime maydon uchun alohida form va saqlash oqimi qo'shildi.

- [frontend/src/app/api/super-admin/system/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/super-admin/system/route.ts):
  - Yangi `GET/POST` route qo'shildi.
  - Sozlamalar `global_settings` orqali saqlanadi va o'qiladi (`queue_*` kalitlar).

- [config/app_settings.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/config/app_settings.py):
  - `get_app_settings()`ga platform-level queue override qatlami qo'shildi.
  - Super admindan saqlangan `queue_*` global qiymatlar runtime `queue` settingsga qo'llanadi.

- Tekshiruv:
  - `cd frontend && npm run build` ✅

#### 2026-05-11 - Company admin `Tizim` settinglariga soddalashtirilgan izohlar qo'shildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - Qolgan tizim maydonlari uchun hint/description matnlari real casega yaqin, sodda tilda yangilandi:
    - `queue_enabled`
    - `task_wait_timeout`
    - `checker_testcase_delay`
    - `gemini_min_interval`
    - `blocked_retry_delay`
    - `blocked_check_interval`
  - Maqsad: admin settinglarning amaliy ta'sirini tez tushunishi.

#### 2026-05-11 - Queue timeout uchun hardcoded retry olib tashlandi

- [services/webhook/queue_manager.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/webhook/queue_manager.py):
  - `mark_blocked(..., retry_minutes=5)` bo'lgan 2 ta joy `queue_settings.blocked_retry_delay`ga almashtirildi.
  - Endi queue timeout holatlarida ham retry muddati admin `Tizim` settingidan olinadi.

#### 2026-05-11 - Webhook `testcase_auto_comment_enabled` saqlanishi barqarorlashtirildi

- [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts):
  - `testcase_auto_comment_enabled` parsing mustahkamlandi.
  - Payloadda field yo'q holatda qiymat majburan `false`ga tushib ketmasligi uchun avval joriy backend qiymati o'qilib fallback sifatida ishlatiladi.
  - Natija: toggle saqlashda tasodifiy `off`ga qaytib ketish riski kamaytirildi.

- Tekshiruv:
  - `cd frontend && npm run build` ✅

#### 2026-05-11 - `testcase_auto_comment_enabled` revert bug root-cause fix (legacy table sync)

- [utils/auth/company_repository.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/utils/auth/company_repository.py):
  - `upsert_company_settings()` ichida `company_settings` jadvali yangilanganda,
    `company_webhook_settings` jadvali mavjud bo'lsa webhook maydonlar ham sync qilinadigan qilindi.
  - Asosiy sabab: ayrim muhitlarda o'qish `company_webhook_settings.module_settings_json` dan kelgani uchun,
    faqat `company_settings.webhook_module_settings` yangilanishi yetarli emas edi.
  - Natija: `webhook_testcase.auto_comment_enabled` saqlangan qiymat reload/tab qayta ochilganda yo'qolmaydi.

- Qo'shimcha tekshiruv:
  - `./.venv/bin/python -m py_compile utils/auth/company_repository.py` ✅

#### 2026-05-11 - `Auto-comment` toggle uchun UI debug xabari qo'shildi

- [frontend/src/app/api/settings/webhook/route.ts](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/api/settings/webhook/route.ts):
  - `GET /api/settings/webhook` va `POST /api/settings/webhook` javobiga `debug` obyekt qo'shildi.
  - `testcase_auto_comment_enabled` uchun `expected/effective/raw_module/has_block` ko'rsatkichlari chiqariladi.

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - Webhook bo'limida backenddan kelgan `debug.message` `Notice` ko'rinishida chiqariladigan qilindi.
  - Save va reloaddan keyin ham debug xabar yangilanadi.

- Tekshiruv:
  - `cd frontend && npm run build` ✅

#### 2026-05-11 - Webhook save atomik qilindi (`webhook_module_settings` overwrite muammosi)

- [services/api/settings_api.py](/Users/mac/Documents/projects/JIRA-AI-Analyzer/services/api/settings_api.py):
  - `/webhook/config/save` ichidagi `webhook_tz_pr`, `webhook_testcase`, `queue` uchun 3 ta ketma-ket save olib tashlandi.
  - Endi barcha webhook modul sozlamalari birlashtirilib bitta `save_company_settings(..., webhook_module_settings=...)` bilan saqlanadi.
  - Maqsad: oxirgi save oldingi blokni bosib yuborish (masalan `auto_comment_enabled` yo'qolishi) holatini oldini olish.

- Tekshiruv:
  - `./.venv/bin/python -m py_compile services/api/settings_api.py utils/auth/company_repository.py` ✅

#### 2026-05-11 - Company admin `Tizim` tabi `Webhook` ichiga ko'chirildi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `SettingsTab`dan alohida `system` tabi olib tashlandi.
  - `Tizim sozlamalari` karti endi `Webhook` tabi ichida ko'rsatiladi.
  - `Webhook` tab dirty-indikatori `whDirty || systemDirty` bo'yicha ishlaydigan qilindi.

- Tekshiruv:
  - `cd frontend && npm run build` ✅

#### 2026-05-11 - Settings kartalari uchun base komponent refactor qilindi

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - `CardStatusStack` qo'shildi: `edit/error/success` xabarlarining yagona formati.
  - `SettingsBaseCard` qo'shildi: karta sarlavhasi, body, statuslar va save footer bitta bazaviy komponentga birlashtirildi.
  - 4 ta karta bazaga o'tkazildi:
    - `Servislar uchun umumiy`
    - `Servis-1: Webhook TZ-PR`
    - `Servis-2: Webhook Testcase`
    - `Tizim sozlamalari`
  - Natija: karta UI/logic formatlari bitta joydan boshqariladigan bo'ldi.

- Tekshiruv:
  - `cd frontend && npm run build` ✅

#### 2026-05-11 - Webhook Servis kartalarida rang override muammosi tuzatildi

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.webhook-service-card` va `.webhook-service-card--main` (hamda dark variantlari) dagi `background/border` override olib tashlandi.
  - Natija: `Servis-1` va `Servis-2` kartalarda rang endi `SettingsBaseCard` (`settings-base-card--*`) tomonidan boshqariladi.

- Tekshiruv:
  - `cd frontend && npm run build` ✅

#### 2026-05-11 - Settings card system alohida komponentlarga ajratildi

- [frontend/src/components/settings/base-card-system.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings/base-card-system.tsx) yaratildi:
  - `SettingsBaseCard`
  - `SettingsCardSection`
  - `SettingsCardItem`
  - `SettingsInnerCard`
  - `ToggleRow`
  - `NumberField`
  - `BaseInputField` (keyingi bosqichlarda qo'llash uchun)

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - yuqoridagi komponentlar lokal funksiyalardan olib tashlanib `settings/base-card-system` importiga o'tkazildi.
  - `Settings` kartalarida card/toggle/number/section/item/inner-card ishlari yagona base tizimdan boshqariladigan bo'ldi.

- Tekshiruv:
  - `cd frontend && npm run build` ✅

#### 2026-05-11 - Settings card ichki elementlari ham base systemga ko‘chirildi

- [frontend/src/components/settings/base-card-system.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings/base-card-system.tsx):
  - `BaseActionRow` va `BaseStatusStack` qo‘shildi (`save + dirty/error/success` yagona footer logikasi).
  - `SettingsBaseCard`ga `showCustomizer` qo‘shildi (ichki child kartalarda gear ko‘rinishini boshqarish uchun).
  - `BaseInputField` `onFocus/onBlur` qo‘llab-quvvatlash bilan kengaytirildi.
  - `BaseCheckGroup`, `BaseOrderPills`, `BaseTagInput` qo‘shildi (karta ichidagi checklist/reorder/tag input ham base qatlamga o‘tdi).
  - Alias exportlar qo‘shildi: `BaseSection`, `BaseGroupCard`, `BaseToggleRow`, `BaseNumberField`.

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - Lokal `CheckGroup`, `OrderPills`, `TagInput` funksiyalari olib tashlanib base komponent importiga o‘tkazildi.
  - `Field/Input/raw input` ishlatilgan joylar to‘liq `BaseInputField`ga o‘tkazildi (jumladan token maydonlari `onFocus/onBlur` mask logikasi bilan).
  - Webhook ichidagi `webhook-family-item` wrapperlar `SettingsCardItem`ga o‘tkazildi.
  - Natija: webhook/module/user kartalaridagi ichki UI elementlar ham endi bitta base card system orqali boshqariladi.

- Tekshiruv:
  - `cd frontend && npm run build` ✅

#### 2026-05-11 - Base card system `super-admin` va `company-admin` panellarga kengaytirildi

- [frontend/src/components/settings/base-card-system.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings/base-card-system.tsx):
  - `BaseFieldShell` qo‘shildi (custom child bilan label/hint wrapper).
  - `BaseSelectField` qo‘shildi (`select` maydonlarini base qatlamdan boshqarish uchun).

- [frontend/src/components/company-admin-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/company-admin-panel.tsx):
  - Top-level `Card`lar `SettingsBaseCard`ga o‘tkazildi.
  - `Username/Parol/Yangi parol` maydonlari `BaseInputField`ga o‘tkazildi.
  - Natija: add-user va user-password kartalari ham base design system’dan foydalanadi.

- [frontend/src/components/super-admin-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/super-admin-panel.tsx):
  - `Card` wrapperlar `SettingsBaseCard`ga o‘tkazildi (`companies`, `ai`, `platform`, `system`, `create-company modal`).
  - `AI` bo‘limida model/fallback `BaseSelectField`, key freeze `NumberField`, API key wrapperlari `BaseFieldShell` bilan birlashtirildi.
  - `Platform admin` bo‘limidagi inputlar `BaseInputField`ga o‘tkazildi.
  - `System defaults` bo‘limidagi sonli maydonlar `NumberField`ga o‘tkazildi.
  - `Create company` modal inputlari `BaseInputField/NumberField`ga o‘tkazildi.
  - `Billing` subsectionda `plan/status/date` maydonlari `BaseInputField/BaseSelectField`ga o‘tkazildi.

- Tekshiruv:
  - `cd frontend && npm run build` ✅

#### 2026-05-11 - `BaseInputField` kengaytirildi (right-slot support)

- [frontend/src/components/settings/base-card-system.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings/base-card-system.tsx):
  - `BaseInputField`ga `rightSlot` qo‘shildi.
  - Natija: input ichidagi ko‘rsat/yashir (eye) kabi icon-buttonlar ham base input orqali boshqariladi.

- [frontend/src/components/super-admin-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/super-admin-panel.tsx):
  - AI API key maydonlari `BaseFieldShell + Input` dan `BaseInputField(rightSlot=eye-btn)` ga o‘tkazildi.

- Tekshiruv:
  - `cd frontend && npm run build` ✅

#### 2026-05-11 - Super admindagi qolgan raw inline field va checkboxlar ham base systemga o‘tkazildi

- [frontend/src/components/settings/base-card-system.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings/base-card-system.tsx):
  - `BaseInlineActionField` qo‘shildi (`input + action button` patterni uchun).

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.base-inline-action-field` class qo‘shildi (inline input/action layout).

- [frontend/src/components/super-admin-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/super-admin-panel.tsx):
  - `Seat limit` va `Delete confirmation` satrlari `BaseInlineActionField`ga o‘tkazildi.
  - Kompaniya modul tanlovi (details ichida) `BaseCheckGroup`ga o‘tkazildi.
  - Create-company modal modul tanlovi ham `BaseCheckGroup`ga o‘tkazildi.
  - Natija: super-admin panelda raw `Input/Select/Field/Card/checkbox` ishlatilishi amalda yo‘q, base system komponentlari bilan boshqariladi.

- Tekshiruv:
  - `cd frontend && npm run build` ✅

#### 2026-05-11 - `testcase-generator` va `tzpr-checker` to‘liq base card systemga o‘tkazildi

- [frontend/src/components/settings/base-card-system.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings/base-card-system.tsx):
  - `BaseTextAreaField` qo‘shildi (`Textarea` + label/hint base wrapper).

- [frontend/src/components/testcase-generator.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/testcase-generator.tsx):
  - Top form kartasi `SettingsBaseCard`ga o‘tkazildi.
  - `Task Key` -> `BaseInputField`, `Qo‘shimcha buyruq` -> `BaseTextAreaField`ga o‘tkazildi.
  - Test type raw checkboxlari `BaseCheckGroup`ga o‘tkazildi.
  - Natija bloklaridagi barcha `Card`lar `SettingsBaseCard`ga o‘tkazildi (priority/warnings/overview/testcases/code/spec/error kartalari).

- [frontend/src/components/tzpr-checker.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/tzpr-checker.tsx):
  - Top form kartasi `SettingsBaseCard`ga o‘tkazildi.
  - `Task Key` -> `BaseInputField`ga o‘tkazildi.
  - Natija bloklaridagi barcha `Card`lar `SettingsBaseCard`ga o‘tkazildi (warnings/AI/figma/PR/error kartalari).
  - Compliance summary kartasi ham `SettingsBaseCard` asosida ishlaydigan qilindi.

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `.qa-compliance-card` style `SettingsBaseCard` strukturasi bilan mos ishlashi uchun yangilandi (`.settings-base-card__body` target).

- Tekshiruv:
  - `cd frontend && npm run build` ✅

#### 2026-05-11 - `testcase` va `tzpr` kartalarida gear (customizer) to‘liq yoqildi

- [frontend/src/components/testcase-generator.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/testcase-generator.tsx):
  - Barcha `SettingsBaseCard`lardan `showCustomizer={false}` olib tashlandi.

- [frontend/src/components/tzpr-checker.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/tzpr-checker.tsx):
  - Barcha `SettingsBaseCard`lardan `showCustomizer={false}` olib tashlandi.

- Natija:
  - `testcase-generator` va `tzpr-checker` sahifalaridagi barcha base kartalarda yuqori o‘ngdagi `gear` sozlama tugmasi ko‘rinadi.

- Tekshiruv:
  - `cd frontend && npm run build` ✅

#### 2026-05-11 - Base karta texnik qarzlari yopildi (persist, horizontal layout, inner-card gear, webhook shell)

- [frontend/src/components/settings/base-card-system.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings/base-card-system.tsx):
  - `SettingsBaseCard`ga `customizerId` qo‘shildi.
  - Card customizer (`tone/layout`) holati `localStorage`ga persist qilinadigan bo‘ldi (reloaddan keyin saqlanadi).
  - `SettingsInnerCard` ichki kartalarida `showCustomizer={false}` yoqildi (inner cardlarda gear ko‘rinmaydi).

- [frontend/src/app/globals.css](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/app/globals.css):
  - `horizontal` layout real 2-column ko‘rinishga o‘tkazildi (`header/customizer` va `body` yonma-yon).
  - `horizontal` holatda `save-footer` to‘liq kenglikda qoladigan qilindi.
  - Mobil (<=900px) uchun avtomatik 1-column fallback qo‘shildi.
  - Eski `webhook-shell` wrapperga bog‘liq CSS olib tashlandi.

- [frontend/src/components/settings-panel.tsx](/Users/mac/Documents/projects/JIRA-AI-Analyzer/frontend/src/components/settings-panel.tsx):
  - Webhook tabdagi ko‘rinmas tashqi `SettingsBaseCard` (`webhook-shell`) olib tashlandi.
  - Webhookdagi 4 asosiy karta uchun aniq `customizerId` berildi:
    - `settings-webhook-shared`
    - `settings-webhook-service1`
    - `settings-webhook-service2`
    - `settings-webhook-system`

- Tekshiruv:
  - `cd frontend && npm run typecheck` ✅
  - `cd frontend && npm run build` ✅
