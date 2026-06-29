# Multi-Agent Checker Rules

Status: `Superseded by docs/MULTI_AGENT_JSON_CONTRACT.md for agent JSON formats`

Last updated: `2026-05-18`

Source of truth:
- Agent JSON contract: [docs/MULTI_AGENT_JSON_CONTRACT.md](/Users/mac/Documents/projects/QA-Assistant/docs/MULTI_AGENT_JSON_CONTRACT.md)
- SaaS roadmap: [ROADMAP_SAAS.md](/Users/mac/Documents/projects/QA-Assistant/ROADMAP_SAAS.md)
- Progress log: [PROGRESS_LOG.md](/Users/mac/Documents/projects/QA-Assistant/PROGRESS_LOG.md)

Roadmap connection:
- Stage 2 - Target Architecture: checker, agents, run lifecycle and contracts must have clear boundaries.
- Stage 4 - Multi-Tenant Isolation: every run must carry `company_id`, `user_id`, task context and settings scope.
- Stage 10 - Core Feature Stabilization: checker behavior must be deterministic around filtering, preflight, status mapping and final score.
- Stage 13 - Testing and Release Quality: missing, invalid or incomplete agent output must be caught by validators/tests.

## 1. Core Principle

Multi-agent checkerda mas'uliyatlar qat'iy ajratiladi.

- Checker = run owner, settings owner, policy owner, filter owner, preflight owner, final action owner.
- Agent1 = filtered source'lardan requirement extraction va merge.
- Agent2 = final requirement inventoryni PR/code contextga nisbatan tekshiruvchi verifier.
- Agent3 = Agent1 va Agent2 outputini audit qiluvchi arbiter va quality controller.

Asosiy qoida:

`Agentlar raw Jira/comments/Figma/settings/policy qarorlarini ko'rmaydi. Checker oldindan hamma narsani tayyorlaydi.`

## 2. Execution Modes

Allowed mode:

- `multi_agent`

`multi_agent` mode:

- Checker Agent1, Agent2 va Agent3 ishlashi uchun kerakli barcha data'ni run boshida tekshiradi.
- PR/code context majburiy.
- PR topilmasa yoki valid code context bo'lmasa, run `blocked` bo'ladi.
- Agent1 ham ishga tushmaydi, chunki keyingi Agent2 bosqichi baribir ishlay olmaydi.

## 3. Checker Responsibilities

Checker run boshida Agent1'dan oldin quyidagilarni bajaradi:

- Run context yaratadi:
  - `run_id`
  - `task_key`
  - `company_id`
  - `user_id`
  - `execution_mode`
  - `source`
- Settings oladi:
  - `read_comments_enabled`
  - `max_comments_to_read`
  - `ai_data_section_order`
  - `trusted_scope_comment_authors`
  - `return_threshold`
  - `auto_return_enabled`
- Jira taskni oladi:
  - summary
  - description/TZ
  - metadata
  - comments
  - figma links
- TZ minimal validatsiya qiladi.
- PR/code contextni preflight qiladi.
- Comment policy ishlatadi.
- Figma policy ishlatadi.
- Agent1 uchun sanitized input tayyorlaydi.

Checker qiladigan policy qarorlar:

- Comment o'qiladimi yoki yo'q.
- Qancha comment o'qiladi.
- AI-generated commentlar chiqariladimi.
- Qaysi comment author trusted hisoblanadi.
- Qaysi comment requirement source bo'la oladi.
- Figma ishlatiladimi yoki yo'q.
- Qaysi Figma text Agent1'ga borishi mumkin.
- Multi-agent run PR/code contextsiz boshlanishi mumkinmi yoki blocked bo'ladimi.

Checker Agent1'ga xom data bermaydi.

Agent1'ga berilmaydi:

- raw Jira task
- raw comments
- raw Figma summary
- raw settings
- raw policy config
- PR/code context

## 3.1 Gemini JSON Gateway

Har bir Gemini javobi agent validatoriga borishidan oldin umumiy JSON gatewaydan o'tadi:

```text
raw Gemini response
-> parse_gemini_json(raw)
-> validate_agentX_json(parsed)
```

Gateway vazifasi faqat JSON syntaxni o'qish va xavfsiz local repair qilish:

- bo'sh javobni `empty_response` deb belgilash;
- markdown `json` fence'larni olib tashlash;
- raw text ichidan JSON obyektni ajratish;
- trailing comma kabi mayda format xatolarini tuzatish;
- kesilgan quote/brace tailni balanslab ko'rish;
- parse metadata qaytarish: `used_cleanup`, `used_repair`, `repair_type`, `raw_length`, `error`.

Gateway domain ma'no yaratmaydi: requirement, status, evidence, recommendation yoki verdict qo'shmaydi. Bu qarorlar faqat agent-specific validator va final checker qatlamida qilinadi.

## 4. Checker Preflight Blocking Rules

Checker run quyidagi holatlarda Agent1'dan oldin to'xtaydi:

- TZ yo'q yoki yaroqsiz.
- `multi_agent` mode va PR topilmadi.
- `multi_agent` mode va PR/code diff context valid emas.
- Required tenant/user/task context yo'q.
- Settings yoki credentials run uchun yetarli emas.

Blocked run:

- `run_state = blocked`
- Agent1, Agent2, Agent3 ishlamaydi.
- Auto return qilinmaydi.
- UI'da blocked sababi ko'rsatiladi.

## 5. Sanitized Agent1 Input

Agent1 input shape:

```json
{
  "tz": "...",
  "comments": [
    "Trusted comment matni"
  ],
  "figma": [
    "Figma text/comment matni"
  ]
}
```

Input rules:

- `tz` doim bo'lishi kerak.
- `comments` faqat comment policy ruxsat bersa bo'ladi.
- `figma` faqat Figma policy ruxsat bersa bo'ladi.
- AI-generated commentlar bu inputga kirmaydi.
- Untrusted commentlar requirement source bo'lib kirmaydi.

## 6. Agent1 Rules

Agent1 faqat requirement extraction va merge qiladi.

Agent1 qiladigan ishlar:

- `tz` ichidan atomic requirementlar ajratadi.
- Agar `comments` bo'lsa, comment requirementlarini final `requirements` inventoryga merge qiladi.
- Agar `figma` bo'lsa, Figma requirementlarini final `requirements` inventoryga merge qiladi.
- Dublikat talablarni bitta canonical requirementga birlashtiradi.

Agent1 qilmaydi:

- Comment trustedmi yoki yo'qmi hal qilmaydi.
- AI-generated commentni filter qilmaydi.
- Figma ishlatish mumkinmi hal qilmaydi.
- PR/code tekshirmaydi.
- Verification status bermaydi.
- Pass/fail verdict bermaydi.
- Compliance score hisoblamaydi.

Agent1 output:

```json
{
  "requirements": [
    {
      "id": "REQ-1",
      "text": "...",
      "source": "tz"
    }
  ]
}
```

`requirements` final canonical requirement inventory hisoblanadi.

Allowed `source`:

- `tz`
- `comment`
- `figma`
- `mixed`

## 7. Effective Requirements

Agent2'ga Agent1 final `requirements` ro'yxati beriladi.

- `deferred`
- `cancelled`
- `superseded`

Non-effective talablar UI inventoryda ko'rinishi mumkin, lekin PR verification uchun Agent2'ga yuborilmaydi.

## 8. Agent2 Rules

Agent2 = PR/code verifier.

Agent2 input:

- Agent1 final `requirements`
- Checker tayyorlagan PR/code context

Agent2 har bir requirement uchun bitta verification qaytarishi shart.

Checker Agent2'ni faqat per-requirement oqimda ishlatadi:

- har requirement alohida Agent2 chaqiruvida tekshiriladi;
- checker natijalarni yig'ib, coverage validation qiladi;
- requirement chaqiruvlari `agent2_parallelism` limiti bilan parallel ishlaydi;
- shundan keyin Agent2'ga yana bitta extra-scope scan chaqiruvi yuboriladi.

Default parallelism: `agent2_parallelism = 5`.

Allowed statuses:

- `completed`
- `failed`

Status meanings:

- `completed` = talab PR'da to'liq bajarilgan.
- `failed` = talab to'liq bajarilmagan, qisman bajarilgan, PR'da topilmagan yoki evidence yetarli emas.

Taqiqlangan Agent2 fields/statuses:

- `partial`
- `unknown`
- `unverified`
- `confidence`

Strict mapping:

- Qisman bajarilgan talab = `failed`
- Evidence topilmadi = `failed`
- PR diff yetarli emas = `failed`
- Model aniq tasdiqlay olmadi = `failed`

Agent2 output:

```json
{
  "id": "REQ-1",
  "status": "completed",
  "evidence": "PR'da bu talab bajarilgani ko'rindi."
}
```

Agent2 qilmaydi:

- Final verdict bermaydi.
- Compliance score hisoblamaydi.
- Taskni return/pass qilmaydi.
- Missing verificationlarni o'zi yashirmaydi.

Agent2 bitta chaqiruvda bitta requirement oladi va bitta verification qaytarishi shart.

## 9. Agent2 Missing Verification Rule

Muhim qoida:

`Agent2 outputida requirement yo'qolsa, Checker bu IDni technical failure sifatida qayd qiladi.`

Per-requirement oqimda bu holat odatda faqat quyidagi sabablarda yuz beradi:

- Gemini bo'sh javob qaytardi;
- JSON buzilgan va retry/repair ham tiklay olmadi;
- Agent2 javobidagi `id` kutilgan requirement IDga mos kelmadi.

Checker har requirement uchun alohida retry qiladi va yakunda missing/invalid IDlarni baribir sanaydi.

Bu holat requirement bajarilmagan degani emas.

Retrydan keyin ham verification yaroqsiz bo'lsa:

- Agent2 output contract buzilgan.
- Checker/backend quality control buni `technical_failures` metadata ichiga yozadi.
- Verdict odatda `manual_review` bo'ladi.

## 9.1. Agent2 Technical Failure Rule

`per_requirement` rejimida bitta requirement chaqiruvi bo'sh yoki invalid JSON qaytarsa:

- Checker shu requirementni avtomatik retry qiladi.
- Retrydan keyin ham parse bo'lmasa, bu real `failed` emas.
- Checker Agent2 contractini buzmaslik uchun `verifications` ichida shu ID uchun `status: "failed"` item saqlaydi.
- Shu bilan birga checker top-level `technical_failures` metadata ichida requirement ID, error va attempt raw excerptlarini saqlaydi.
- Agent3/backend bu IDlarni real bajarilmagan talab sifatida emas, `manual_review` sifatida final matrixga chiqaradi.

Bu holatda:

- `missing` bo'lmaydi, chunki ID qoplangan.
- `failed` ro'yxatiga faqat real evidence yetishmagan talablar kiradi.
- `technical` ro'yxatiga model texnik sabab bilan tekshira olmagan talablar kiradi.
- Agar real failed yo'q, lekin technical itemlar bor bo'lsa, verdict `manual_review` bo'ladi.

## 10. Extra Code Changes Rule

Agent2 requirementlardan tashqari PR/code o'zgarishlarini ham bildiradi.

`per_requirement` rejimida bu ish alohida bosqich:

1. Avval har requirement alohida tekshiriladi.
2. Keyin checker Agent2'ga barcha requirementlar va butun PR diffni berib, requirementlardan tashqari muhim o'zgarishlarni so'raydi.
3. Agent2 faqat `extra` array qaytaradi.

Misol:

- 10 ta talabning hammasi bajarilgan.
- Lekin PR ichida TZ'da yo'q qo'shimcha behavior yoki riskli refactor bor.

Agent2 buni `extra`ga yozadi.

Agent2 bu bo'yicha final verdict bermaydi.

Checker/backend extra code riskni baholaydi:

- `none`
- `low`
- `medium`
- `high`

Riskli extra code bo'lsa, checker final verdictni `manual_review` qilishi mumkin.

## 11. Agent3 Rules

Agent3 = human-readable summary yozuvchi arbiter.

Agent3 input:

- Agent1 final requirement inventory
- Agent2 requirement verifications
- Agent2 extra code changes

Checker/backend tekshiradi:

- Agent2 barcha effective requirementlar uchun verification qaytardimi.
- Verification ID'lar Agent1 requirement ID'lariga mosmi.
- Statuslar faqat `completed | failed`mi.
- `failed` itemlarda `evidence` bormi.
- `completed` itemlarda `evidence` bormi.
- Extra itemlar bormi.
- Agent2 output contract buzilganmi.

Agent3 output:

```json
{
  "summary": "REQ-1 bajarilgan. REQ-2 bo'yicha evidence topilmadi."
}
```

Agent3 qilmaydi:

- Compliance score hisoblamaydi.
- Webhook action qilmaydi.
- Jira taskni return/pass qilmaydi.
- Settings policy qarori qilmaydi.

Allowed verdicts:

- `pass`
- `fail`
- `manual_review`
- `blocked`

Verdict meanings:

- `pass` = barcha requirementlar `completed`, xavfli extra code yo'q.
- `fail` = kamida bitta requirement `failed`.
- `manual_review` = extra code risk, evidence sifati yoki scope signallar sabab odam tekshirishi kerak.
- `blocked` = Agent2 output contract buzilgan yoki run yakuniy xulosa uchun yaroqsiz.

## 12. Compliance Score Rule

Compliance score'ni Agent3 emas, Checker hisoblaydi.

Formula:

```text
compliance_score = completed_count / total_requirements * 100
```

- `completed_count` checker/backend hisoblagan final statuslardan olinadi.
- `total_requirements` checker/backend normalizatsiya qilgan `requirements` ro'yxatidan olinadi.
- `total_requirements = 0` bo'lsa, score action uchun ishlatilmaydi.
- Score integer percent ko'rinishida saqlanadi.
- `quality_status != ok` bo'lsa, score auto action uchun ishlatilmaydi.
- `missing` bo'lsa, auto action qilinmaydi.

## 13. Checker Finalization

Checker Agent3 artifactdan keyin deterministic final result yaratadi.

Checker final result ichida bo'lishi kerak:

- final `requirement_inventory`
- Agent2 `verifications`
- `arbiter_summary`
- `analysis_sections`
- `analysis_overview`
- `compliance_score`
- run metadata
- agent run timeline
- warnings

UI final `requirements`ni karta ko'rinishida chizadi.

Har karta ko'rsatadi:

- requirement text
- source: `TZ/comment/Figma/mixed`
- Agent2 verification status
- evidence

## 14. UI Section Rules

Multi-agent UI visible sections:

- `completed`
- `failed`
- `issues`
- `figma`

Taqiqlangan section:

- `partial`

Reason:

- Qisman bajarilgan talab endi alohida status emas.
- Qisman bajarilgan talab `failed` hisoblanadi.

UI status mapping:

- `completed` = bajarilgan
- `failed` = bajarilmagan yoki yetarli evidence yo'q
- `manual_review` = odam tekshiruvi kerak
- `blocked` = checker/agent contract yoki preflight muammo

## 15. Webhook Action Scope

Webhook auto-return action hozircha bu rule implementation scope'iga kirmaydi.

Kelajakdagi qoida:

```text
if source == webhook
and checker.verdict == fail
and checker.quality_status == ok
and missing empty
and compliance_score < return_threshold
and auto_return_enabled:
    return task
else:
    no auto return
```

Hozirgi qoida:

- Checker score va verdictni tayyorlaydi.
- Webhook auto-return flow alohida patchda ko'riladi.

## 16. Contract Compatibility Rules

New multi-agent contractda ishlatilmaydi:

- Agent2 `partial`
- Agent2 `unknown`
- Agent2 `unverified`
- Agent2 `confidence`
- UI `partial` section
- Checker missing verificationlarni avtomatik merge/yamash

Runtime faqat `multi_agent` flowdan foydalanadi; eski alternativ execution va UI preview flowlar olib tashlangan.

## 17. Test Requirements

Preflight tests:

- `multi_agent` mode PR yo'q bo'lsa Agent1 ishlamasin va run `blocked` bo'lsin.

Checker filtering tests:

- AI-generated comments Agent1 inputiga kirmasin.
- Untrusted comments requirement source bo'lmasin.
- Figma disabled bo'lsa Agent1 inputida Figma bo'lmasin.

Agent1 tests:

- `tz` atomic `requirements`ga ajratilsin.
- Trusted `comments`/`figma` talablar canonical `requirements`ga merge qilinsin.

Agent2 tests:

- 10 talab kirsa 10 verification qaytsin.
- Evidence topilmasa `failed` bo'lsin.
- Qisman bajarilgan talab `failed` bo'lsin.
- Statuslardan `partial`, `unknown`, `unverified` chiqmasin.
- `confidence` verificationda bo'lmasin.
- TZ'dan tashqari kodlar `extra`ga tushsin.

Agent3 tests:

- Missing verificationlar aniqlansin.
- Invalid statuslar aniqlansin.
- Failed talablar bo'lsa `fail` verdict chiqsin.
- Contract buzilsa `blocked` verdict chiqsin.
- Extra code risk bo'lsa `manual_review` chiqishi mumkin.

Checker finalization tests:

- `completed_count / total_requirements * 100` score to'g'ri hisoblanadi.
- `total_requirements = 0` action uchun score ishlatilmaydi.
- Missing verification bo'lsa auto action qilinmaydi.
- UI sections ichida `partial` bo'lmaydi.

## 18. Implementation Guardrails

Har yangi patch quyidagi savollarga javob berishi kerak:

- Agent1'ga raw source yoki policy decision o'tib ketmadimi?
- Agent2 har requirement uchun verification qaytaryaptimi?
- Agent2 `partial/unknown/unverified/confidence` qaytarsa normalizer/validator nima qiladi?
- Checker Agent2 outputini yashirincha yamamayaptimi?
- Checker/backend missing/invalid verificationni ko'ryaptimi?
- Checker score'ni o'zi hisoblayaptimi?
- UI final `requirements` va Agent2 verificationni bitta karta ichida ko'rsatyaptimi?
- Webhookga tegilmagan bo'lsa, auto-return behavior o'zgarmaganmi?
