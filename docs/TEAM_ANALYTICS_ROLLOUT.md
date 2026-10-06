# Team Analytics rollout

## Holat

2026-10-06: release tayyorlandi. Izolyatsiyalangan PostgreSQL bilan 443 backend testi, 17 frontend testi va 3 golden-set eval o'tdi. Ruff, frontend typecheck, lint (0 error, 95 mavjud warning) va production build o'tdi. Production deploy/import natijasi quyidagi release yozuvida qayd etiladi.

Ish SaaS roadmapning Data Layer Migration, Multi-Tenant Isolation va operatsion barqarorlik bosqichlariga tegishli. `PROGRESS_LOG.md` o'zgartirilmaydi.

## Ulash

1. Pending migrationlar: 005–008. Startup runner ularni raqam tartibida qo'llaydi. 008 immutable eventlardan alohida task/interval/people/sprint/field-map/sync-state projection jadvallarini qo'shadi. Oldin qo'llangan migratsiyalar o'zgartirilmaydi.
2. Super-admin company modullaridan Team Analytics’ni yoqadi; AI Webhook addonini yoqish shart emas.
3. Jira issue created/updated/deleted va sprint lifecycle eventlarini mavjud company endpointga yuborish: `/webhook/jira/{company_code}`. Native Jira admin webhook uchun `secret` -> `X-Hub-Signature: sha256=...` ishlatiladi; raw body bounded reader va timing-safe HMAC bilan tekshiriladi. Avvalgi `X-Webhook-Secret` integratsiyalari ham ishlaydi. URLga secret kiritilmaydi. Issue JQL faqat project bilan cheklanadi, AI trigger statusi bilan emas. [Atlassian webhook docs](https://developer.atlassian.com/cloud/jira/platform/webhooks/).
4. Company-admin `/team-analytics`dagi Settings’da faqat vaqt hisoblanadigan Jira statusi va kunlik ish soatini saqlaydi. Default `In Progress`, 8 soat.

## Tasdiqlangan hisob

- Vaqt faqat tanlangan statusda yuradi. Boshqa barcha statuslarda to‘xtaydi; qaytsa oldingi yig‘indiga qo‘shilib davom etadi. Bu kalendar vaqt, Jira worklog yoki ish kalendari emas.
- Immutable eventlar vaqt intervalini qayta tiklashga yetadi. Bir xil ijrochi/statusdagi ketma-ket intervallar birlashtiriladi; unrelated update vaqt tarixini mayda qismlarga bo‘lmaydi. Pauza va assignee almashishi alohida intervalni boshlaydi.
- Task qatori bosilganda (yoki Enter/Space) tarix ochiladi. Sanalar Asia/Tashkent bo'yicha, yarim tundan o'tgan interval kunlarga bo'linadi. Vaqt zonasi matni ko'rsatilmaydi. Ochiq interval snapshot vaqtigacha hisoblanadi, oxiri “hozir”; Yangilash yangi snapshot oladi.
- Ijrochilar Jira signallaridan company + Jira source + account ID bo‘yicha avtomatik olinadi. Filtr joriy tasklarni va oldin vaqt sarflangan tasklarni chiqaradi. Qator, batafsil va jami hisobda tanlangan ijrochi intervallari ishlatiladi.
- Ijrochi tanlanganda yonida Kunlik point maydoni chiqadi. Hisoblash tugmasi kiritilgan pointni jadvalga qo‘llaydi; maydonni tahrirlash avvalgi hisobni o‘zgartirmaydi, qayta Hisoblash kerak. Bu faqat komponentning vaqtinchalik state’i: APIga yuborilmaydi, DB/localStorage/cookie/URLga yozilmaydi. Boshqa ijrochi tanlansa, demo almashtirilsa yoki sahifa qayta ochilsa qiymat tozalanadi. Pagination va Yangilash davomida ochilgan hisob qiymati qoladi.
- Ish kuni = ijrochi tasklarining jami sekundlari / (kunlik ish soati × 3600). Parallel tasklar vaqti foydalanuvchi talabiga ko‘ra qo‘shiladi, overlap dedup qilinmaydi.
- Vaqtga teng point = ish kuni × kiritilgan kunlik point. Bu yopilgan task pointi yoki calendar-day productivity emas. Jira task pointi alohida ko‘rsatiladi va tasklar bo‘yicha yig‘iladi; reassigned taskning pointi ijrochiga ajratilgan individual credit sifatida talqin qilinmaydi.
- Ijrochi natijasidagi kechikish = har task uchun max(0, ishlangan sekund − task SP / qo‘llangan kunlik point × kunlik soat × 3600) yig‘indisi. Normadan oshgan tasklar soni, ortiqcha vaqt/ish kuni va ortiqcha point ko‘rsatiladi. Tez tugagan tasklar boshqa task kechikishini kamaytirmaydi; SP belgilanmagan tasklar chiqarib tashlanadi. Hisob barcha sahifalar uchun API summary.task_estimates ma’lumotiga asoslanadi; kunlik point APIga yuborilmaydi. Jira deadline ishlatilmaydi.
- Kunlik point kiritilmaganda vaqt/ish kuni/Jira pointi ko‘rinadi, vaqtga teng point “—” bo‘ladi. Hisob yaxlitlanmagan qiymatlar bilan bajariladi; ekranda 2 kasrgacha, vaqt esa to‘liq daqiqagacha ko‘rsatiladi.
- Yig‘indilar barcha sahifalarni qamrab oladi. Kunlik ish soati o‘zgarsa ish kuni va vaqtga teng point hozirgi sozlama bo‘yicha qayta hisoblanadi; vaqt statusi effective timestampdan boshlab amal qiladi.
- Oldingi 006 migratsiyadagi norma jadvali va closed_statuses ustuni yangi hisobda ishlatilmaydi; oldingi schema/destructive migration o‘zgartirilmadi. API eski assignee_norms/closed_statuses sozlamalarini qabul qilmaydi.

## Jira manbasi va tiklash

- Initial import: `python scripts/team_analytics_import.py --company-id 1 --initial`. Faqat configured projectlardagi hozir ochiq tasklar va `task_status_history`dagi mavjud tasklar olinadi. User tanlovi: server tarixidagi 30 ta task; DEV JQL tekshiruvida 734 ochiq task topildi. Import ularning complete changeloglarini sahifalab oladi, butun projectning yopilgan tarixini izlamaydi.
- Field IDs global taxmin qilinmaydi: project board estimation configuration (`scrum` va team-managed `simple`) orqali topiladi, ambiguity bo'lsa fail qilinadi. Company 1 DEV uchun real mapping: points `customfield_10016`, sprint `customfield_10020`.
- Eventlar company/source/issue/stable-event-key bo'yicha idempotent. REST snapshot Jira `updated` vaqtiga biriktiriladi; o'qish paytida issue o'zgarsa bounded retry qilinadi. Availability recovery yangi statusni bosmasdan alohida bo'sh event bilan tiklanadi.
- Default status birinchi explicit settingdan oldin ham In Progress; keyingi status sozlamalari effective timestampdan boshlab amal qiladi.
- Har 5 daqiqada mavjud worker queue orqali incremental Jira sync navbatlanadi. Checkpoint faqat muvaffaqiyatdan keyin siljiydi; 15 daqiqa overlap, complete changelog va stable IDs duplicate/time inflationni oldini oladi. Tracked working/unavailable issue projectdan ko'chsa ham sync davom etadi. 403/404 deletion deb taxmin qilinmaydi: unavailable belgilanib timer pauza qilinadi.
- Saqlanadi: issue/project/status/assignee IDlari, point value/field ID, sprint ID/membership/metadata (board, nom, holat, boshlanish/tugash/completion), yaratish/update/resolution sanalari, priority, parent, labels/components/versions, author, source timestamp va origin. Analyticsga description/comment/attachment/token nusxalanmaydi.
- API umumiy totalsni SQLda hisoblaydi, faqat tanlangan page interval tarixi bitta batch query bilan olinadi. Frontend kunlik point faqat vaqtinchalik state'da qo'llanadi.

## Chegaralar

- Vaqt Jira status tarixi bo'yicha kalendar vaqti; Jira worklog yoki xodimning tasdiqlangan faol ish vaqti emas. Kechasi/weekend/parallel In Progress tasklar ham foydalanuvchi tasdiqlagan formula bo'yicha qo'shiladi.
- Import API credentiallariga ko'rinadigan task/history bilan cheklangan. Missed deletes/visibility changes tracked working tasklar uchun pollingda pauza qilinadi; haqiqiy delete faqat deletion signali bilan belgilanadi.
- Sprint dimension joriy metadata, issue eventlar esa tarixiy sprint membershipni saqlaydi; descriptions/comments/worklogs bu release scope'iga kirmaydi.
- Source URL almashsa alohida Jira manbasi hisoblanadi. Eventlarni o‘chirish vaqt tarixiga ta’sir qiladi; retention/index maintenance keyingi operatsion ish.

## Xavfsiz deploy va rollback

Production `.env`, Compose va Caddyfile saqlanadi. Faqat QA-Assistant backend/worker/frontend build va recreate qilinadi; Postgres/Caddy va boshqa Compose loyihalariga tegilmaydi. DB pg_dump custom-format backup va eski image rollback taglari deploydan oldin saqlanadi. Yangi image qurilishi eski ishlayotgan containerlarni o'zgartirmaydi.

Rollbackda eski backend/worker/frontend imagelar ishlatiladi, 005–008 additive schema va yig'ilgan eventlar o'chirilmaydi. DB restore faqat alohida recovery qarori bilan; oddiy code rollback uchun kerak emas.
