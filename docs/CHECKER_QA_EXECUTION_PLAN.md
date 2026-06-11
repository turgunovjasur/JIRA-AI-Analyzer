# Checker QA Execution Plan

Bu hujjat [docs/CHECKER_QA_REQUIREMENTS.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/docs/CHECKER_QA_REQUIREMENTS.md) ni yopish uchun amaliy bajaruv planidir.

Asosiy qoida:
- Har bir phase oxirida checker QA uchun qaror chiqarishni soddalashtirishi kerak.
- Yangi UI yoki backend o'zgarishi shu plan phase'laridan biriga bog'lanadi.

## Phase 0 — Baseline Alignment

Status: `Done`

Maqsad:
- section nomlarini Gemini, settings va UI o'rtasida birxillashtirish
- checker uchun QA baseline requirement hujjatini source of truth qilish

Bajarilgan:
- QA baseline requirement hujjati yaratildi
- canonical checker section mapping yaratildi
- settings label'lari va checker UI sectionlari moslashtirildi
- mock raw AI matni `analysis_sections` dan yig'iladigan qilindi

## Phase 1 — QA First Fold

Status: `Done`

Maqsad:
- QA birinchi ekranda `pass/return/manual review` qaroriga yaqinlashsin

Bajarilgan:
- backendga `task_info` qo'shildi
- backendga `run_info` qo'shildi
- backendga `qa_recommendation` qo'shildi
- checker UI'ga `QA Decision` kartasi qo'shildi
- checker UI'da task identity maydonlari ko'rinadigan qilindi
- `Figma summary` evidence bloki `Figma evidence` semantikasiga o'tkazildi

Natija:
- QA checkerga kirib task egasi, issue type, priority, reporter va tavsiya etilgan next actionni ko'ra oladi

## Phase 2 — Requirement and Evidence Matrix

Status: `Done`

Maqsad:
- `bajarilgan / qisman / bajarilmagan` bo'limlarini paragraph emas, requirement-level audit ko'rinishiga o'tkazish

Ishlar:
- backendda requirement-level structured entity qo'shish
- har requirement uchun:
  - `status`
  - `evidence`
  - `code files`
  - `figma relation`
  - `notes`
- checker UI'da filterlanadigan matrix yoki inspection list yaratish

Bajarilgan:
- backendga `requirement_matrix` structured contracti qo'shildi
- matrix qatorlari uchun `status`, `status_label`, `requirement`, `evidence`, `code_files`, `figma_relation`, `notes` maydonlari qo'shildi
- checker UI'da filterlanadigan `Requirement matrix` inspection bloki qo'shildi
- mock payload real Gemini'ga yaqin requirement/evidence formatiga o'tkazildi
- Gemini prompt section instructionlari requirement-level bullet va evidence signaliga yaqinlashtirildi

Tayyor bo'lganda QA yutug'i:
- devga `qaysi talab`, `qaysi evidence`, `qaysi file` bilan return yozish osonlashadi

QA checkpoint:
- `Ha, QA baseline bo'yicha ketyapmiz`
- checker endi `bajarilgan / qisman / bajarilmagan` ni requirement row'lari bilan ko'rsatadi
- har row ichida evidence, code file va Figma relation bor
- PR detail va file-level audit checker ichida ochiladi
- qolgan chuqurlashtirishlar `Phase 4` ga ko'chdi

## Phase 3 — Workflow and Comment Intelligence

Status: `Done`

Maqsad:
- checker qaroriga ta'sir qiladigan process signallarini ko'rinadigan qilish

Ishlar:
- `comment_analysis` va `dev_objections` ni QA uchun ko'rinarli blokka chiqarish
- real checker uchun `workflow_info` yoki shunga teng contract qo'shish:
  - `service1_status`
  - `service2_status`
  - `return_reason`
  - `threshold`
  - `auto_return_enabled`
- checker UI'da `manual review`, `return`, `blocked` holatlarini process context bilan ko'rsatish

Bajarilgan:
- backendga `comment_intelligence` structured contracti qo'shildi
- backendga `workflow_info` structured contracti qo'shildi
- checker UI'da `Comment intelligence` kartasi qo'shildi
- checker UI'da `Workflow diagnostics` kartasi qo'shildi
- `scope change`, `deferred scope`, `dev objection` signallari alohida ko'rinadigan qilindi
- `service1_status`, `service2_status`, `return_reason`, `threshold`, `auto_return_enabled` checker ichida ko'rinadigan bo'ldi

Tayyor bo'lganda QA yutug'i:
- checker qarori nima sabab process yoki scope bilan cheklanganini tushunadi

QA checkpoint:
- `Ha, QA baseline bo'yicha ketyapmiz`
- comment o'zgarishlari checker ichida ikkinchi darajaga tushmayapti
- developer objection va keyingi sprint signali checker qaroriga ta'sir qiladigan blok sifatida ko'rinadi
- workflow sabablarini ko'rib QA `manual review` yoki `return` kontekstini tezroq tushunadi

## Phase 4 — Figma and PR Evidence Deepening

Status: `Done`

Maqsad:
- Figma va PR evidence'ni AI xulosasidan ajralgan holda audit qilsa bo'ladigan darajaga olib chiqish

Ishlar:
- Figma evidence uchun file/node/source ko'rinishini boyitish
- PR detail ichida requirement bilan bog'lanadigan signallarni ko'paytirish
- Figma yo'q bo'lgandagi halol restriction holatini yanada aniq ko'rsatish

Bajarilgan:
- requirement matrix qatorlariga `code_refs` qo'shildi
- requirement matrix qatorlariga `figma_sources` qo'shildi
- checker UI'da code file badge'lari clickable source linklarga o'tdi
- checker UI'da Figma source badge'lari requirement row ichida ko'rinadigan bo'ldi
- checker UI'da patch preview, PR metadata va change stats requirement row ichida ko'rinadigan bo'ldi
- checker UI'da Figma node id va source summary requirement row ichida ko'rinadigan bo'ldi
- Figma access cheklovi checkerda alohida restriction holati sifatida ko'rsatiladigan bo'ldi

Tayyor bo'lganda QA yutug'i:
- dizayn va kod evidence'ni mustaqil ko'rib chiqishi mumkin bo'ladi

QA checkpoint:
- `Ha, QA baseline bo'yicha ketyapmiz`
- QA requirement row ichidan bevosita kod source, patch preview va Figma source'ga tushyapti
- Figma access yo'q bo'lsa checker buni yashirmayapti
- evidence endi AI xulosasidan alohida audit qilinadigan darajaga yetdi

## Phase 5 — Mock Removal and Real-Only Flow

Status: `Done`

Maqsad:
- checker UI to'liq real backend flowga qaytishi

Ishlar:
- `CHECKER_UI_MOCK_ENABLED` olib tashlanadi
- mock data fallback yoki debug-only rejimga tushiriladi
- real backend structured payload checkerning asosiy manbasi bo'ladi

Bajarilgan:
- checker UI faqat real run-based multi-agent backend flowdan foydalanadi
- mock data fallback va UI toggle olib tashlandi
- eski direct analyze route olib tashlandi

Qolgan:
- real tasklar bilan end-to-end checker smoke test o'tkazish

Tayyor bo'lganda QA yutug'i:
- checker haqiqiy tasklar bilan product-level ishchi instrument bo'ladi

## Yaqin navbat

Keyingi implementatsiya ustuvorligi:
1. Real tasklar bilan end-to-end checker smoke test

## Qaror mezoni

Har bir keyingi checker task oldidan savol:

`Bu o'zgarish QA'ga tezroq, ishonchliroq va isbotliroq qaror chiqarishga yordam beradimi?`
