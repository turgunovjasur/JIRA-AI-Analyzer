# Testcase Multi-Agent Refactor Plan

## Maqsad

`testcase_generator` modulidagi test case yaratish oqimini soddalashtirish, barqarorlashtirish va keyingi implementatsiya uchun aniq kontraktga keltirish.

Asosiy qarorlar:

- `max_test_cases` global limiti olib tashlanadi.
- Limit requirement darajasida boshqariladi: `testcases_per_requirement`.
- Default qiymat: `3`.
- Agent2 test case yozadi.
- Agent2 biror requirementni qoplamasa, Agent2 repair mode faqat missing requirementlar uchun qayta ishlaydi.
- Agent3 test case yozuvchi emas, auditor va organizer bo'ladi.
- Agent3 bir xil ekran, flow yoki ma'noga yaqin test case'larni `test_scenario` ichida group qiladi.
- Agent3 positive, negative, boundary, integration yoki expected resulti boshqa bo'lgan test case'larni bitta testcasega majburan merge qilmaydi.

## Roadmap bilan bog'liqlik

Bu ish `ROADMAP_SAAS.md` bo'yicha quyidagi bosqichlarga mos:

- Stage 2 - Target Architecture: agent kontraktlari va servis chegaralarini aniq qilish.
- Stage 4 - Multi-Tenant Isolation: settinglar tenant/user scope bo'yicha ishlashi.
- Stage 9 - Product UX/UI: testcase natijalarini foydalanuvchi uchun tartibli, o'qilishi oson ko'rinishga keltirish.

## Hozirgi muammo

Hozir Agent2 promptiga bir nechta manba kiritiladi:

- Agent1 ajratgan requirements.
- TZ.
- Comment summary.
- Figma summary.
- User custom context.
- Developer objections.
- `max_test_cases`.

Bu promptni kattalashtiradi va Agent2 vazifasini aralashtiradi. Testcase modulining asosiy maqsadi requirementlardan test case chiqarish bo'lgani uchun Agent2 inputini minimal va aniq qilish kerak.

Yana bir muammo: `max_test_cases` promptda bor, lekin backend finalizer global limitni qat'iy enforce qilmaydi. Shu sababli setting va natija orasida tafovut bo'lishi mumkin.

## Target Architecture

Yangi oqim:

```text
Agent1
  -> requirements

Agent2
  -> all requirements uchun flat test_cases

Backend validation #1
  -> parse, normalize, coverage, missing/underfilled requirement aniqlash

Agent2 repair mode
  -> faqat missing requirementlar uchun test case yozish
  -> faqat kerak bo'lsa ishlaydi

Backend merge
  -> initial + repair test case'larni birlashtirish
  -> deterministic dedup
  -> coverage qayta hisoblash

Agent3
  -> flat test_cases ni audit/group qiladi
  -> test_scenarios yaratadi
  -> duplicate va weak expected resultlar bo'yicha audit_findings beradi

Backend validation #2
  -> Agent3 output final tekshiruvi
  -> coverage saqlanganini tasdiqlash
  -> TC-001, TC-002 final raqamlash

Final result
  -> flat test_cases
  -> grouped test_scenarios
  -> requirement_coverage
  -> warnings
  -> audit_findings
```

## Agent2 roli

Agent2 faqat test case yozadi.

Agent2 vazifalari:

- Har bir requirement uchun test case yaratish.
- Har bir requirement uchun kamida 1 ta test case yozish.
- Har bir requirement uchun ko'pi bilan `testcases_per_requirement` ta test case yozish.
- Har bir test case'da `requirement_ids` to'ldirish.
- `steps` va `expected_result`ni aniq yozish.
- TZ va user custom contextdagi product/limit/business qoidalarni test data va expected resultga qo'llash.

Agent2 qilmasligi kerak:

- Requirementlarni qayta yaratmasin.
- Requirement IDlarni o'zgartirmasin.
- Coverage hisoblamasin.
- Scenario grouping qilmasin.
- JIRA comment/Figma/dev objections asosida yangi scope ixtiro qilmasin.

## Agent2 input contract

Agent2 faqat quyidagi inputlarni oladi:

```json
{
  "requirements": [
    {
      "id": "REQ-1",
      "text": "Foydalanuvchi username va parol bilan tizimga kira olsin",
      "source": "tz"
    }
  ],
  "tz_content": "Backend bergan real TZ matni",
  "custom_context": "User kiritgan qo'shimcha system prompt yoki kontekst",
  "testcases_per_requirement": 3
}
```

Maydonlar:

- `requirements`: Agent1 ajratgan talablar ro'yxati. Asosiy source of truth.
- `tz_content`: backend preflightdan o'tgan real TZ.
- `custom_context`: foydalanuvchi kiritgan qo'shimcha ko'rsatma. Bo'sh bo'lishi mumkin.
- `testcases_per_requirement`: har requirement uchun target va max test case soni. Default `3`.

Agent2 promptida qisqa qoida bo'ladi:

```text
Har bir REQ uchun kamida 1 ta, ko'pi bilan testcases_per_requirement ta test case yozing.
Har test case requirement_ids orqali qaysi REQ(lar)ni qoplashini ko'rsatsin.
```

## Agent2 output contract

Agent2 flat `test_cases` qaytaradi:

```json
{
  "test_cases": [
    {
      "title": "Muvaffaqiyatli login",
      "description": "Valid username va parol bilan tizimga kirishni tekshirish",
      "preconditions": "Foydalanuvchi ro'yxatdan o'tgan va login sahifasi ochilgan",
      "steps": [
        "Login sahifasini ochish",
        "Valid username kiritish",
        "Valid parol kiritish",
        "Login tugmasini bosish"
      ],
      "expected_result": "Foydalanuvchi tizimga muvaffaqiyatli kiradi va asosiy sahifaga yo'naltiriladi",
      "test_type": "positive",
      "priority": "High",
      "severity": "Major",
      "tags": ["auth", "login"],
      "requirement_ids": ["REQ-1"]
    }
  ]
}
```

Agent2 `id` qaytarishi shart emas. Backend final bosqichda `TC-001`, `TC-002` qilib raqamlaydi.

Majburiy maydonlar:

- `title`
- `steps`
- `expected_result`
- `test_type`
- `requirement_ids`

Tavsiya etilgan maydonlar:

- `description`
- `preconditions`
- `priority`
- `severity`
- `tags`

## Backend validation #1

Agent2'dan keyin backend birinchi validation qiladi. Bu validation Agent3 uchun toza input tayyorlaydi va missing requirementlarni aniqlaydi.

Tekshiruvlar:

1. JSON parse bo'ldimi.
2. `test_cases` listmi.
3. Har test case schema bo'yicha normalize qilinadimi.
4. `requirement_ids` mavjudmi.
5. `requirement_ids` ichidagi IDlar Agent1 requirements ichida bormi.
6. Har test case'da `steps` bo'sh emasmi.
7. Har test case'da `expected_result` bo'sh emasmi.
8. Har requirement kamida 1 ta test case bilan qoplanganmi.
9. Har requirement uchun test case soni `testcases_per_requirement`dan oshib ketmaganmi.
10. Semantic yoki exact duplicate bor-yo'qligi aniqlanadimi.

Validation natijasi:

```json
{
  "ok": true,
  "missing_requirement_ids": [],
  "underfilled_requirement_ids": ["REQ-3"],
  "overfilled_requirement_ids": [],
  "invalid_test_cases": [],
  "warnings": []
}
```

Muhim qoida:

- `missing_requirement_ids` bo'lsa, Agent2 repair mode ishlaydi.
- `underfilled_requirement_ids` warning sifatida ko'rsatiladi, lekin repair shart emas.
- `overfilled_requirement_ids` bo'lsa, backend deterministic tarzda ortiqcha test case'larni olib tashlaydi yoki Agent3 groupingga qoldiradi.

## Missing requirement qoidasi

Agar Agent2 barcha requirementlar uchun test case yozmasa:

```text
REQ-1 -> 2 ta testcase
REQ-2 -> 0 ta testcase
REQ-3 -> 1 ta testcase
```

Backend:

- `REQ-2` missing ekanini aniqlaydi.
- Warning yaratadi: `REQ-2 uchun testcase yozilmadi, repair mode ishga tushdi`.
- Agent2 repair mode'ni faqat `REQ-2` uchun chaqiradi.

## Agent2 repair mode

Repair mode yangi agent emas. Shu Agent2 kontraktining kichik chaqiruvi.

Repair input:

```json
{
  "requirements": [
    {
      "id": "REQ-2",
      "text": "Noto'g'ri parol uchun xato xabari ko'rsatilsin",
      "source": "tz"
    }
  ],
  "tz_content": "Backend bergan real TZ matni",
  "custom_context": "User kiritgan qo'shimcha kontekst",
  "testcases_per_requirement": 3,
  "mode": "repair_missing_requirements"
}
```

Repair prompt qoidasi:

```text
Faqat berilgan missing requirementlar uchun test case yozing.
Oldingi requirementlar uchun test case yozmang.
Har test case requirement_ids maydonida faqat berilgan REQ IDlardan foydalaning.
```

Repair output ham oddiy Agent2 output bilan bir xil:

```json
{
  "test_cases": []
}
```

## Backend merge

Repairdan keyin backend:

1. Initial Agent2 test case'larini oladi.
2. Repair Agent2 test case'larini qo'shadi.
3. Invalid `requirement_ids` bo'lsa tashlaydi yoki warning qiladi.
4. Exact duplicate'larni olib tashlaydi.
5. Requirement coverage'ni qayta hisoblaydi.
6. Har requirement uchun countni qayta hisoblaydi.

Dedup uchun deterministic key:

```text
normalized(title) + normalized(steps) + normalized(expected_result)
```

Optional stronger key:

```text
requirement_ids + test_type + normalized(title) + normalized(steps) + normalized(expected_result)
```

## Agent3 roli

Agent3 test case yozmaydi. Agent3 auditor va organizer bo'ladi.

Agent3 vazifalari:

- Agent2 test case'larini o'qib chiqish.
- Bir xil ekran, flow yoki ma'nodagi test case'larni `test_scenario` ichida group qilish.
- Haqiqiy duplicate yoki juda o'xshash test case'larni merge qilish.
- Zaif `expected_result`larni aniqroq qilish bo'yicha final variant berish.
- Grouping sabablarini `audit_findings`da qaytarish.
- `requirement_ids`ni saqlash.

Agent3 qilmasligi kerak:

- Yangi requirement yaratmasin.
- Requirement IDlarni o'zgartirmasin.
- Coverage'ni kamaytirmasin.
- Positive va negative testcase'larni bitta testcasega majburan merge qilmasin.
- Boundary va integration testcase'larni bitta testcasega majburan merge qilmasin.
- Expected result boshqa bo'lgan testcase'larni bitta testcasega majburan merge qilmasin.

## Agent3 grouping qoidasi

Agent3 ikki xil ishni ajratishi kerak:

### 1. Merge

Faqat haqiqiy duplicate yoki deyarli bir xil test case'lar merge qilinadi.

Merge qilish mumkin:

```text
TC-A: Login sahifasida bo'sh parol xatosini tekshiradi.
TC-B: Login sahifasida parol bo'sh qolganda error chiqishini tekshiradi.
```

Bu ikki test case bir xil scenario bo'lsa, bitta test case qilib berilishi mumkin.

### 2. Group

Bir xil ekran yoki flowga tegishli, lekin test turi yoki expected resulti boshqa bo'lgan test case'lar merge qilinmaydi. Ular bitta `test_scenario` ichida alohida test case sifatida group qilinadi.

Group qilish kerak:

```text
TC-A: Muvaffaqiyatli login, positive.
TC-B: Noto'g'ri parol, negative.
TC-C: Bo'sh parol, boundary/negative.
```

Bular bitta `Login sahifasi validatsiyasi` scenario groupiga kirishi mumkin, lekin alohida test case bo'lib qoladi.

## Agent3 input contract

Agent3 input:

```json
{
  "requirements": [
    {
      "id": "REQ-1",
      "text": "Foydalanuvchi username va parol bilan tizimga kira olsin"
    }
  ],
  "test_cases": [
    {
      "temp_id": "TMP-001",
      "title": "Muvaffaqiyatli login",
      "description": "...",
      "preconditions": "...",
      "steps": ["..."],
      "expected_result": "...",
      "test_type": "positive",
      "priority": "High",
      "severity": "Major",
      "tags": ["auth"],
      "requirement_ids": ["REQ-1"]
    }
  ]
}
```

`temp_id` backend tomonidan Agent3 input uchun vaqtinchalik beriladi. Final `TC-001` raqami backend validation #2 dan keyin beriladi.

## Agent3 output contract

Agent3 grouped view qaytaradi:

```json
{
  "test_scenarios": [
    {
      "scenario_title": "Login sahifasi validatsiyasi",
      "screen_or_flow": "Login page",
      "requirement_ids": ["REQ-1", "REQ-2"],
      "test_cases": [
        {
          "title": "Muvaffaqiyatli login",
          "description": "Valid username va parol bilan tizimga kirishni tekshirish",
          "preconditions": "Foydalanuvchi ro'yxatdan o'tgan",
          "steps": ["Valid username kiritish", "Valid parol kiritish", "Login tugmasini bosish"],
          "expected_result": "Foydalanuvchi tizimga kiradi va asosiy sahifaga yo'naltiriladi",
          "test_type": "positive",
          "priority": "High",
          "severity": "Major",
          "tags": ["auth", "login"],
          "requirement_ids": ["REQ-1"]
        },
        {
          "title": "Noto'g'ri parol bilan login",
          "description": "Invalid parol kiritilganda xato xabarini tekshirish",
          "preconditions": "Foydalanuvchi mavjud",
          "steps": ["Valid username kiritish", "Noto'g'ri parol kiritish", "Login tugmasini bosish"],
          "expected_result": "Noto'g'ri parol haqida aniq xato xabari ko'rsatiladi",
          "test_type": "negative",
          "priority": "High",
          "severity": "Major",
          "tags": ["auth", "login", "validation"],
          "requirement_ids": ["REQ-2"]
        }
      ]
    }
  ],
  "audit_findings": [
    {
      "type": "grouped_same_flow",
      "requirement_ids": ["REQ-1", "REQ-2"],
      "reason": "Login sahifasiga tegishli positive va negative holatlar bitta scenario ichida group qilindi, lekin alohida testcase sifatida saqlandi."
    }
  ]
}
```

## Backend validation #2

Agent3'dan keyin backend final validation qiladi.

Tekshiruvlar:

1. Agent3 JSON parse bo'ldimi.
2. `test_scenarios` listmi.
3. Har scenario ichida `test_cases` listmi.
4. Har testcase `requirement_ids` saqlaganmi.
5. Har `requirement_id` validmi.
6. Coverage Agent2 merge bosqichidan keyin kamaymaganmi.
7. Har requirement kamida 1 testcase bilan qoplanganmi.
8. `steps` bo'sh emasmi.
9. `expected_result` bo'sh emasmi.
10. Haqiqiy duplicate qolganmi.
11. Final flat test case list qayta quriladimi.
12. Final `TC-001`, `TC-002` raqamlash backend tomonidan beriladimi.

Agent3 output coverage'ni buzsa:

- Backend Agent3 outputni reject qiladi.
- Backend Agent2 merge qilingan flat test case listni final fallback sifatida ishlatadi.
- Warning qo'shadi: `Agent3 grouping coverage'ni buzdi, flat testcase output ishlatildi`.

## Final result shape

`TestCaseGenerationResult` kengaytiriladi:

```json
{
  "test_cases": [],
  "test_scenarios": [],
  "requirements": [],
  "requirement_coverage": {
    "total_requirements": 0,
    "covered_count": 0,
    "uncovered_ids": []
  },
  "warnings": [],
  "audit_findings": [],
  "success": true
}
```

Ichki hisob-kitob uchun `test_cases` flat formatda qoladi.

UI/JIRA comment uchun `test_scenarios` grouped formatda ishlatiladi.

## Settings

Yangi setting:

```text
testcases_per_requirement: int = 3
```

Range:

```text
min = 1
max = 3
default = 3
```

Qoida:

- User settingdan har requirement uchun nechta testcase target qilinishini belgilaydi.
- Backend `testcases_per_requirement`ni `1..3` oralig'ida normalize qiladi.
- `max_test_cases` olib tashlanadi yoki runtime oqimda ishlatilmaydi.

Existing setting cleanup:

- `testcase_max_test_cases` UI/API/settingsda qolishi mumkin, lekin yangi oqimda ishlatilmaydi.
- Keyingi refactorda `testcase_max_test_cases` o'rniga `testcases_per_requirement` chiqariladi.

## Warning qoidalari

Backend quyidagi warninglarni chiqaradi:

```text
REQ-4 uchun Agent2 test case yozmadi. Repair mode ishga tushdi.
REQ-5 uchun 3 ta targetdan faqat 1 ta testcase yozildi.
Agent3 grouping coverage'ni buzdi, flat Agent2 output ishlatildi.
2 ta duplicate testcase olib tashlandi.
1 ta testcase expected_result bo'sh bo'lgani uchun final outputdan chiqarildi.
```

Warninglar final resultda `warnings` ichida qaytadi.

## Audit findings

Agent3 `audit_findings` qaytaradi. Bu backend warning emas, AI auditor izohi.

Finding turlari:

```text
merged_duplicate
grouped_same_flow
strengthened_expected_result
kept_separate_due_to_test_type
kept_separate_due_to_expected_result
```

Misol:

```json
{
  "type": "kept_separate_due_to_test_type",
  "requirement_ids": ["REQ-1"],
  "reason": "Positive va negative testlar bir xil login flowga tegishli, lekin test_type va expected_result farqli bo'lgani uchun alohida testcase sifatida saqlandi."
}
```

## Implementation Phases

### Phase 1 - Contracts

- `services/generators/testcase_agents/agent2_testcase.py` promptini minimal inputga o'tkazish.
- Agent2 response schema'dan `id`ni majburiylikdan chiqarish.
- `agent3_testcase_auditor.py` yangi contract modulini qo'shish.
- Agent3 prompt va response schema yaratish.

### Phase 2 - Settings

- `testcases_per_requirement` settingini qo'shish.
- Default `3` qilish.
- Runtime normalize: `min(max(value, 1), 3)`.
- UI/API setting mappingini tayyorlash.
- `max_test_cases` runtime dependencylarini olib tashlash.

### Phase 3 - Backend Validation Helpers

Yangi helperlar:

```text
parse_agent2_testcases()
validate_testcase_schema()
calculate_requirement_coverage()
find_missing_requirements()
find_underfilled_requirements()
dedupe_testcases()
merge_repair_testcases()
flatten_test_scenarios()
validate_agent3_grouping()
renumber_testcases()
```

Bu helperlar iloji boricha deterministic bo'lishi kerak.

### Phase 4 - Agent2 Repair

- Agent2 initial call'dan keyin missing requirementlarni aniqlash.
- Missing bo'lsa Agent2 repair promptini qurish.
- Repair outputni parse qilish.
- Initial + repair outputni merge qilish.
- Repair ishlaganini warninglarda ko'rsatish.

### Phase 5 - Agent3 Auditor

- Agent3 inputini flat test case listdan qurish.
- Agent3'ni Agent2 merge bosqichidan keyin chaqirish.
- Agent3 outputni parse qilish.
- `test_scenarios` grouped outputni olish.
- Agent3 output yaroqsiz bo'lsa fallback flat output ishlatish.

### Phase 6 - Result Model

- `TestCaseGenerationResult`ga `test_scenarios` va `audit_findings` qo'shish.
- Existing `test_cases`, `requirements`, `requirement_coverage`, `warnings` saqlanadi.
- Backward compatibility uchun flat `test_cases` doim qaytariladi.

### Phase 7 - UI/JIRA Formatter

- UI natija sahifasida grouped `test_scenarios` ko'rsatish.
- Flat test case statistikasini saqlash.
- JIRA comment formatter grouped scenario formatni qo'llab-quvvatlashi.
- Agar `test_scenarios` bo'lmasa, eski flat `test_cases` format bilan ishlash.

### Phase 8 - Tests

Regression testlar:

- Agent2 inputida faqat requirements, TZ, custom_context, testcases_per_requirement bor.
- Agent2 outputida `id` majburiy emas.
- Missing REQ bo'lsa Agent2 repair chaqiriladi.
- Repair faqat missing REQlar uchun ishlaydi.
- Initial + repair merge coverage'ni to'ldiradi.
- Agent3 bir xil flowdagi positive/negative testlarni group qiladi, merge qilmaydi.
- Agent3 duplicate test case'larni merge qiladi.
- Agent3 coverage'ni buzsa backend fallback qiladi.
- Final `TC-001` raqamlash backend tomonidan qilinadi.
- `testcases_per_requirement` default `3` ishlaydi.

## Open Decisions

Implementatsiya oldidan aniqlashtiriladigan masalalar:

1. `testcase_max_test_cases` settingini darhol olib tashlaymizmi yoki deprecated qilib qoldiramizmi?
2. `testcases_per_requirement` UI'da qayerda ko'rinadi: Testcase module settings ichidami yoki webhook testcase settings ichida ham alohidami?
3. JIRA commentda grouped scenario default bo'ladimi yoki user tanlaydigan format bo'ladimi?
4. Agent3 yaroqsiz output qaytarsa run warning bilan success bo'ladimi yoki error bo'ladimi?

Tavsiya:

- `testcase_max_test_cases`ni hozircha deprecated qilib qoldirish.
- `testcases_per_requirement`ni UI module settings va webhook testcase settingsga qo'shish.
- JIRA commentda grouped scenario default bo'lishi.
- Agent3 xatosi runni yiqitmasligi, flat Agent2 output fallback sifatida ishlatilishi.

## Yakuniy qaror

Implementatsiya shu modelga asoslanadi:

```text
Agent2 = testcase writer
Agent2 repair = missing requirement testcase writer
Agent3 = testcase auditor and scenario organizer
Backend = source of truth for validation, coverage, dedup, renumbering and fallback
```

Bu model Agent2 promptini soddalashtiradi, coverage nazoratini backendga o'tkazadi, Agent3'ni alohida foydali rolga ega qiladi va final natijani QA uchun o'qilishi oson grouped scenario ko'rinishiga keltiradi.
