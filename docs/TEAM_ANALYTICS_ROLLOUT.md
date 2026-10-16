# Team Analytics rollout

## Holat

2026-10-06: Jira bilan task ro‘yxati mosligi lokal kodda tuzatildi; bu tuzatish hali productionga deploy qilinmagan. Barcha statusdagi initial import, faol sprintlarni davriy reconciliation qilish, joriy sprint/ijrochi bo‘yicha filtr va deleted/unavailable tasklarni ro‘yxatdan chiqarish qo‘shildi. Tarix saqlanadi; company yoki Jira identifikatorlari runtime kodga qotirilmaydi. Izolyatsiyalangan PostgreSQL’da 465 backend testi (webhook testlari uchun inline rejim), 27 frontend testi, typecheck va Ruff o‘tdi. Production Jira’dan faqat o‘qilgan 304 event lokal alohida tenantda replay qilindi: Sprint 72 DEV + Abdujalil bo‘yicha Jira va yangi kodda 15 tadan task; key/status/assignee/story-point qiymatlari teng, Jira task pointlari jami 0. Bu tekshiruv production bazasini o‘zgartirmadi.

2026-10-06: kunlik/haftalik limitlar (default 8/40 soat) va jadval pagination ma'lumotlari productionga deploy qilindi. `009_team_analytics_weekly_hours` migratsiyasi qo'llandi. Production build, real DB snapshot o'qishi va health tekshiruvlari o'tdi; yangi avtomatik regression testlar foydalanuvchi alohida so'ramagani sababli ishga tushirilmadi. Quyidagi oldingi test natijalari avvalgi releasega tegishli.

2026-10-06: backend, worker va frontend productionga deploy qilindi; company 1 (GWS / DEV) pilot yoqildi. Izolyatsiyalangan PostgreSQL bilan 445 backend testi, 17 frontend testi va 3 golden-set eval o'tdi. Ruff, frontend typecheck, lint (0 error, 95 mavjud warning) va production build o'tdi. Jira ma'lumotlari import qilindi, davriy sync va jonli sahifa tekshirildi. Native Jira webhook ro'yxatdan o'tkazilishi sayt administratorining huquqini kutmoqda; Jira mavjud server tokeniga HTTP 403 qaytardi.

Ish SaaS roadmapning Data Layer Migration, Multi-Tenant Isolation va operatsion barqarorlik bosqichlariga tegishli. `PROGRESS_LOG.md` o'zgartirilmaydi.

## Ulash

1. Pending migrationlar: 005–008. Startup runner ularni raqam tartibida qo'llaydi. 008 immutable eventlardan alohida task/interval/people/sprint/field-map/sync-state projection jadvallarini qo'shadi. Oldin qo'llangan migratsiyalar o'zgartirilmaydi.
2. Super-admin company modullaridan Team Analytics’ni yoqadi; AI Webhook addonini yoqish shart emas.
3. Native analytics issue created/updated/deleted va sprint lifecycle eventlarini `/webhook/jira/{company_code}/analytics`ga yuborish. Mavjud AI integratsiyasi `/webhook/jira/{company_code}`da qoladi; native analytics callback AI trigger pipeline'ga kirmaydi. Native Jira admin webhook uchun `secret` -> `X-Hub-Signature: sha256=...` ishlatiladi; raw body bounded reader va timing-safe HMAC bilan tekshiriladi. Avvalgi `X-Webhook-Secret` integratsiyalari ham ishlaydi. URLga secret kiritilmaydi. Issue JQL faqat project bilan cheklanadi, AI trigger statusi bilan emas. [Atlassian webhook docs](https://developer.atlassian.com/cloud/jira/platform/webhooks/).
4. Company-admin `/team-analytics`dagi Settings’da vaqt hisoblanadigan Jira statusi, kunlik va haftalik ish soatini saqlaydi. Default `In Progress`, 8 soat/kun va 40 soat/hafta. `009` migratsiyasi mavjud sozlamalarga haftalik 40 soatni qo'shadi; oldingi kunlik qiymatlar saqlanadi.

## Tasdiqlangan hisob

- Xom vaqt faqat tanlangan statusda yuradi. Boshqa barcha statuslarda to‘xtaydi; qaytsa oldingi yig‘indiga qo‘shilib davom etadi. Status intervallari saqlanadi; ko'rsatiladigan ishlangan vaqt esa kunlik va haftalik limitlardan keyingi qiymatdir. Bu Jira worklog yoki ish jadvali emas.
- Immutable eventlar vaqt intervalini qayta tiklashga yetadi. Bir xil ijrochi/statusdagi ketma-ket intervallar birlashtiriladi; unrelated update vaqt tarixini mayda qismlarga bo‘lmaydi. Pauza va assignee almashishi alohida intervalni boshlaydi.
- Task qatori bosilganda (yoki Enter/Space) tarix ochiladi. Sanalar Asia/Tashkent bo'yicha, yarim tundan o'tgan interval kunlarga bo'linadi. Kunlik jami va umumiy jami limitlardan keyingi vaqtni ko'rsatadi; statusdagi xom vaqt limitdan farq qilsa alohida yoziladi. Oraliq timestampi status tarixini bildiradi. Ochiq interval snapshot vaqtigacha hisoblanadi, oxiri “hozir”; Yangilash yangi snapshot oladi.
- Ijrochilar Jira signallaridan company + Jira source + account ID bo‘yicha avtomatik olinadi. Filtr Jira kabi faqat joriy ijrochiga biriktirilgan tasklarni chiqaradi. Qator, batafsil va jami hisobda tanlangan ijrochi intervallari ishlatiladi; oldingi ijrochi tarixi saqlanadi, lekin task uning joriy ro‘yxatiga qo‘shilmaydi.
- Ijrochi tanlanganda yonida Kunlik point maydoni chiqadi. Hisoblash tugmasi kiritilgan pointni jadvalga qo‘llaydi; maydonni tahrirlash avvalgi hisobni o‘zgartirmaydi, qayta Hisoblash kerak. Bu faqat komponentning vaqtinchalik state’i: APIga yuborilmaydi, DB/localStorage/cookie/URLga yozilmaydi. Boshqa ijrochi tanlansa, demo almashtirilsa yoki sahifa qayta ochilsa qiymat tozalanadi. Pagination va Yangilash davomida ochilgan hisob qiymati qoladi.
- Har ijrochining (company + Jira source + account ID) barcha tasklari Asia/Tashkent kunlariga bo'linadi. Kunlik yig'indi kunlik limit bilan cheklanadi, keyin dushanba–yakshanba haftasidagi cheklangan yig'indi haftalik limit bilan cheklanadi. Kunlik va haftalik allowance task/intervalga xom vaqtiga mutanosib ajratiladi. Masalan, bir kunda bir ijrochining ikki taski 12 soatdan bo'lsa, 8 soatlik limitda har taskka 4 soatdan ajratiladi. Overlap dedup qilinmaydi.
- Limitlar sprint va pagination filtridan oldin hisoblanadi: boshqa sahifa yoki sprintni ochish yangi allowance bermaydi. Haftalik mutanosib taqsimlash tufayli shu haftaga yangi vaqt qo'shilsa, oldingi kunlarga ajratilgan hisoblangan vaqt ham qayta taqsimlanishi mumkin. Ish kuni = limitdan keyingi jami sekundlar / (kunlik ish soati × 3600).
- Vaqtga teng point = ish kuni × kiritilgan kunlik point. Bu yopilgan task pointi yoki calendar-day productivity emas. Jira task pointi alohida ko‘rsatiladi va tasklar bo‘yicha yig‘iladi; reassigned taskning pointi ijrochiga ajratilgan individual credit sifatida talqin qilinmaydi.
- Ijrochi natijasidagi kechikish = har task uchun max(0, ishlangan sekund − task SP / qo‘llangan kunlik point × kunlik soat × 3600) yig‘indisi. Normadan oshgan tasklar soni, ortiqcha vaqt/ish kuni va ortiqcha point ko‘rsatiladi. Tez tugagan tasklar boshqa task kechikishini kamaytirmaydi; SP belgilanmagan tasklar chiqarib tashlanadi. Hisob barcha sahifalar uchun API summary.task_estimates ma’lumotiga asoslanadi; kunlik point APIga yuborilmaydi. Jira deadline ishlatilmaydi.
- Kunlik point kiritilmaganda vaqt/ish kuni/Jira pointi ko‘rinadi, vaqtga teng point “—” bo‘ladi. Hisob yaxlitlanmagan qiymatlar bilan bajariladi; ekranda 2 kasrgacha, vaqt esa to‘liq daqiqagacha ko‘rsatiladi.
- Yig‘indilar barcha sahifalarni qamrab oladi. Jadval pastida ko'rsatilayotgan qatorlar oralig'i, jami qatorlar, hozirgi sahifadagi qatorlar soni, sahifa raqami/sahifalar soni va keyingi sahifadagi qatorlar soni ko'rsatiladi.
- Kunlik yoki haftalik ish soati o‘zgarsa vaqt, ish kuni va vaqtga teng point hozirgi sozlama bo‘yicha qayta hisoblanadi; vaqt statusi effective timestampdan boshlab amal qiladi.
- Oldingi 006 migratsiyadagi norma jadvali va closed_statuses ustuni yangi hisobda ishlatilmaydi; oldingi schema/destructive migration o‘zgartirilmadi. API eski assignee_norms/closed_statuses sozlamalarini qabul qilmaydi.

## Jira manbasi va tiklash

- Initial import: `python scripts/team_analytics_import.py --company-id <company-id> --initial`. Kompaniya konfiguratsiyasidagi projectlarning barcha statusdagi tasklari va mavjud `task_status_history` olinadi; `Done` kategoriyasi chiqarib tashlanmaydi. Birinchi muvaffaqiyatli checkpoint hali bo‘lmasa, scheduled sync ham shu to‘liq importni bajaradi. Shu operator buyrug‘i eski yopilgan sprintlar uchun qayta backfill qilishda ham ishlatiladi. Complete changelog va issue search sahifalab olinadi; katta projectning birinchi importi uzoq davom etishi mumkin.
- Field IDs global taxmin qilinmaydi: project board estimation configuration (`scrum` va team-managed `simple`) orqali topiladi, ambiguity bo'lsa fail qilinadi. Company 1 DEV uchun real mapping: points `customfield_10016`, sprint `customfield_10020`.
- Eventlar company/source/issue/stable-event-key bo'yicha idempotent. REST snapshot Jira `updated` vaqtiga biriktiriladi; o'qish paytida issue o'zgarsa bounded retry qilinadi. Availability recovery yangi statusni bosmasdan alohida bo'sh event bilan tiklanadi.
- Default status birinchi explicit settingdan oldin ham In Progress; keyingi status sozlamalari effective timestampdan boshlab amal qiladi.
- Har 5 daqiqada mavjud worker queue orqali incremental Jira sync navbatlanadi. Yaqinda o‘zgargan tasklardan tashqari shu company/source’dagi faol sprintlar barcha statuslarda tekshiriladi: eski importdan qolgan tasklar avtomatik to‘ldiriladi. O‘zgarmagan, vaqt hisobi to‘xtagan taskning changelogi qayta yuklanmaydi. Faol sprintdan qidiruvda yo‘qolgan saqlangan task qayta o‘qilib, missed move/delete yoki visibility o‘zgarishi tekshiriladi. Checkpoint faqat muvaffaqiyatdan keyin siljiydi; overlap va stable IDs duplicate/time inflationni oldini oladi. Tracked working/unavailable issue projectdan ko'chsa ham sync davom etadi. 403/404 deletion deb taxmin qilinmaydi: unavailable belgilanib timer pauza qilinadi.
- Saqlanadi: issue/project/status/assignee IDlari, point value/field ID, sprint ID/membership/metadata (board, nom, holat, boshlanish/tugash/completion), yaratish/update/resolution sanalari, priority, parent, labels/components/versions, author, source timestamp va origin. Analyticsga description/comment/attachment/token nusxalanmaydi.
- API umumiy totalsni SQLda hisoblaydi, faqat tanlangan page interval tarixi bitta batch query bilan olinadi. Frontend kunlik point faqat vaqtinchalik state'da qo'llanadi.

## Chegaralar

- Xom vaqt Jira status tarixi bo'yicha kalendar vaqti; Jira worklog yoki xodimning tasdiqlangan faol ish vaqti emas. Kechasi/weekend/parallel In Progress tasklar ham limitga kiradigan xom vaqtni oshiradi. Soatlar limiti ish boshlanishi/tugashi yoki dam olish kunlarini aniqlamaydi.
- Import API credentiallariga ko'rinadigan task/history bilan cheklangan. Jira’da mavjud bo‘lmagan yoki credentialga ko‘rinmaydigan tasklar jadvaldan chiqariladi; event va vaqt tarixi saqlanadi. Missed deletes/visibility changes working/unavailable va saqlangan faol sprint tasklari uchun pollingda tekshiriladi; haqiqiy delete faqat deletion signali bilan belgilanadi.
- Sprint dimension joriy metadata, issue eventlar esa tarixiy sprint membershipni saqlaydi; descriptions/comments/worklogs bu release scope'iga kirmaydi.
- Source URL almashsa alohida Jira manbasi hisoblanadi. Eventlarni o‘chirish vaqt tarixiga ta’sir qiladi; retention/index maintenance keyingi operatsion ish.

## Xavfsiz deploy va rollback

Production `.env`, Compose va Caddyfile saqlanadi. Faqat QA-Assistant backend/worker/frontend build va recreate qilinadi; Postgres/Caddy va boshqa Compose loyihalariga tegilmaydi. DB pg_dump custom-format backup va eski image rollback taglari deploydan oldin saqlanadi. Yangi image qurilishi eski ishlayotgan containerlarni o'zgartirmaydi.

Rollbackda eski backend/worker/frontend imagelar ishlatiladi, 005–009 additive schema va yig'ilgan eventlar o'chirilmaydi. DB restore faqat alohida recovery qarori bilan; oddiy code rollback uchun kerak emas.

## Kunlik/haftalik limitlar deployi — 2026-10-06

- Release: `work_limits_20261006_1025`. Faqat 12 runtime fayl yuborildi; production `.env`, Compose va Caddyfile hash'lari o'zgarmadi. Backend, worker va frontend imagelari muvaffaqiyatli qurildi. Yangi image bilan migration runner va company 1 snapshot o'qishi containerlarni yangilashdan oldin bajarildi.
- `009_team_analytics_weekly_hours` qo'llandi; production snapshotda daily=8, weekly=40, 764 task, birinchi sahifada 20 qator olindi. Backend va worker `healthy`, frontend `running`; public sayt HTTP 200 qaytardi.
- Deploy oldi DB dumpi: `/opt/qa-assistant/backups/work_limits_20261006_1025.dump`, 2,011,538 byte / 333 pg_restore list qatori. Eski image rollback taglari `qa-assistant-{backend,worker,frontend}:rollback-work_limits_20261006_1025`. Source arxivi oldingi tracked commit `0e29298`dagi 10 mavjud runtime fayldan tayyorlandi. Config va container ID ro'yxatlari shu backup prefiksi bilan saqlandi.
- Postgres, Caddy, Namoz bot/database va Playwright CI bot container IDlari o'zgarmadi. Faqat QA backend/worker/frontend qayta yaratildi.
- Deploydan keyingi production dumpi lokal `qa_assistant_realdata_20261006` bazaga tiklandi; SHA-256 nusxalar uchun bir xil. Shu snapshotda 764 task, 11,323 event, 179 interval, 33 ijrochi, 4 kompaniya va 5 foydalanuvchi bor. Ilova data volume'ining taxminan 3 MB nusxasi ham alohida lokal katalogga olindi. Lokal ishlash tartibi: [LOCAL_REAL_DATA.md](LOCAL_REAL_DATA.md).

## Release dependency tekshiruvi

Builddagi audit ogohlantirishi tekshirildi: Next.js 16.2.4 affected edi. Next.js/eslint-config-next 16.3.8 va PostCSS 8.5.29 ga yangilandi, compatible transitive patchlar qo'llandi. [Maintainer advisory](https://github.com/vercel/next.js/security/advisories/GHSA-vcvr-r3jv-pc5j). `npm audit --omit=dev`: 0 vulnerabilities. Dev lint toolchain braces/fast-glob bo'yicha 5 high advisory qoladi; audit taklifidagi major downgrade qo'llanmaydi, production dependencylari ta'sirlanmaydi.

Fresh production operator processda runtime `importlib.util` implicit importga tayanishi aniqlanib explicit importga tuzatildi; `python -S` subprocess regression tekshiruvi qo'shildi.

## Production release natijasi — 2026-10-06

- Faqat backend, worker va frontend qayta yaratildi. Backend/worker health checklari o'tdi; mavjud Postgres, Caddy, Namoz bot va Playwright CI bot containerlari ishlashda davom etdi.
- Deploydan oldingi `/opt/qa-assistant/backups/team_analytics_20261006.dump` custom-format backup: 1,376,807 byte / 269 obyekt. Alohida vaqtinchalik DBga restore qilib 30 tarixiy task tekshirildi; faqat shu test DB olib tashlandi. Eski source, Compose va image IDlari shu backup prefiksi bilan saqlandi. Eski image taglari: `qa-assistant-{backend,worker,frontend}:rollback-team_analytics_20261006`.
- Initial import: 734 ochiq task + 30 server tarixidagi task − 2 takror = **762 task**, **11,286 source event**, **128 interval**, **33 ijrochi**, **162 sprint ID**. 154 sprintning to'liq metadata so'rovi muvaffaqiyatli; qolgan 8 sprintning IDsi saqlangan, to'liq metadata olinmagan. 336 joriy issue–sprint bog'lanishi saqlandi. 30 tarixiy taskning barchasi olindi; importda unavailable task yo'q.
- Jira manbasiga solishtirish: DEV-10043 jami 23,542.777 sekund, DEV-10122 3,462.088 sekund, DEV-9919 78,160.371 sekund. Tarixiy assignee almashishi hisobda saqlanadi: ijrochi filtri taskning barcha vaqtini emas, aynan shu ijrochi interval vaqtini chiqaradi.
- Workerning avtomatik sync joblari 64 va 66 hamda operator tekshiruvidagi 65 `done`, bittadan urinish, `last_error=null`. Oxirgi tekshirilgan muvaffaqiyat checkpointi `2026-10-06 08:05:51.506038 UTC`. Har 5 daqiqalik reconciliation yangi va o'tkazib yuborilgan update'larni oladi.
- Public API autentifikatsiyasiz 401 berdi. Native callback to'g'ri HMAC bilan 200/`recorded`, ayni imzo bilan o'zgartirilgan bodyga 401 berdi. Takroriy DEV-10043 importi 0 yangi event qo'shdi.
- Jonli `/team-analytics` sahifada ijrochi filtri, vaqtinchalik 2 point/kun bilan Hisoblash, pagination, barcha sahifalarning jami, yashirin ijrochi ustuni, vertikal rang belgisi, sticky header va row bosilgandagi kunlik interval tarixi tekshirildi. Screenshot: `artifacts/team-analytics-production.jpg`.

## Qolgan qadam: Jira sayt administratorining webhook sozlashi

Server credentialida `ADMINISTER_PROJECTS=true`, ammo `ADMINISTER=false`. Native admin webhook yaratish so'rovi HTTP 403 bilan rad etildi; webhook **yaratilmadi**. Analytics ishlayapti, REST reconciliation har 5 daqiqada yangilaydi; native signallar darhol kelishi uchun sayt administratori quyidagilarni ro'yxatdan o'tkazishi kerak:

- Callback URL: `https://qa-assistant.uz/webhook/jira/gws/analytics`.
- Issue eventlar: `jira:issue_created`, `jira:issue_updated`, `jira:issue_deleted`.
- Sprint eventlar: `sprint_created`, `sprint_updated`, `sprint_started`, `sprint_closed`, `sprint_deleted`.
- Issue JQL: `project in ("DEV")`; status filtri qo'shilmaydi. Body yuborilishi yoqilgan (`excludeBody=false`).
- Jira webhook `secret` maydoniga GWS uchun mavjud encrypted webhook secret xavfsiz operator jarayoni orqali beriladi. Secret chat, hujjat, URL yoki logga yozilmaydi; mavjud AI integratsiyasini buzmaslik uchun rotate qilinmaydi. Jira `X-Hub-Signature` SHA-256 imzosini yuboradi.
- Ro'yxatdan o'tkazilgach, Jira'dagi bitta haqiqiy status almashishi callbackga kelgani va yangi interval to'g'ri yozilgani tekshiriladi. Bu oxirgi native-delivery tekshiruvi hozircha bajarilmagan.

## Sprint filtri — production deploy, 2026-10-06

Foydalanuvchi qayta deploy qilishni so'ragach, sprint filtri productionga chiqarildi. Faqat commit `63ebc4b`dagi 9 runtime fayl yuborildi; `.env`, Compose, Caddy va unrelated lokal fayllar yuborilmadi. Backend/worker/frontend production imagelari build qilindi, navbatda running/queued job yo'qligi ko'rildi, so'ng shu 3 servis `--no-deps --wait` bilan yangilandi. Health checklari o'tdi; schema migratsiyasi talab qilinmadi.

Deploydan oldingi `/opt/qa-assistant/backups/sprint_filter_20261006.dump`: 2,009,764 byte, pg_restore ro'yxatida 333 qator. Source/Compose va oldingi image IDlari shu prefiks bilan saqlandi; image taglari `qa-assistant-{backend,worker,frontend}:rollback-sprint_filter_20261006`. Shu deployda alohida DB restore testi yoki avtomatik testlar ishga tushirilmadi.

- Yuqorida Sprint va Ijrochi dropdownlari bor; Project dropdown qo'shilmaydi. Sprintlar kompaniyaning bazaga yig'ilgan tasklari bilan joriy yoki tarixiy bog'langan IDlardan olinadi, qo'lda kiritilmaydi.
- Dropdown sprint nomi va holatini ko'rsatadi; takroriy nomlarga Tashkent bo'yicha sanalar qo'shiladi. Nomsiz metadata uchun ID faqat fallback labelda ko'rinadi. Identifikator kompaniya + Jira source + sprint ID; tenantlar va boshqa Jira manbalari aralashmaydi.
- `sprint_id` va `sprint_source` API filtri backendda ishlaydi. Jira bilan mos ro‘yxat uchun taskning joriy sprint field’i tekshiriladi; tarixiy a’zolikning o‘zi taskni ro‘yxatga qo‘shmaydi. Hisobdagi ish intervallari tanlangan sprint kalendar davriga kesiladi. Jami SQLda barcha sahifalar bo'yicha hisoblanadi; batafsil tarix ham ayni davr bilan cheklanadi. Bu sprintga tegishlilik o'zgargan har bir subintervalning alohida productivity modeli emas.
- Faol sprint: Jira startDate → snapshot vaqti; eski completed_at qolgan bo'lsa ham unga tayanilmaydi. Yopilgan sprint: startDate → actual completeDate, u bo'lmasa endDate. Hali boshlanmagan yoki sanalari yetishmaydigan sprint hisobga tanlanmaydi; taxminiy lifetime vaqti qo'yilmaydi.
- Sprint almashtirilganda page va ochilgan row tozalanadi; ijrochi va uning vaqtinchalik kunlik point hisobi saqlanadi. So'rov xatosida filtrlar ko'rinib turadi va Barcha sprintlarga qaytish mumkin. Jira task pointlari aynan mavjud Jira bahosi bo'lib qoladi, sprint kunlariga prorate qilinmaydi.
- Typecheck, Ruff va production build o'tdi; frontend lint 0 error / 95 mavjud warning. Foydalanuvchi ko'rsatmasi bo'yicha avtomatik testlar ishga tushirilmadi. Keyinchalik ishlatish uchun boundary/source/tenant/pagination regression testlari qo'shildi.
- Lokal brauzerda demo Sprint 23 + Ali + 2 point/kun tanlovi ko'rildi: 2 task, 5 soat, 1.25 vaqtga teng point; rowning kunlik tarixi ochildi.
- Production sahifada haqiqiy Jira sprint nomlari/state'lari ko'rindi. `Sprint 72 DEV` (6441), boshlanishi 21.09.2026, + `Ortiqbek Bozorboyev` tanlovida 28 task chiqdi. 13:57 snapshotida jami 161 soat 5 daqiqa, 2 point/kun bo'yicha 40.27 vaqtga teng point. Ochiq intervallar tufayli keyingi snapshotlarda vaqt oshishi kutiladi.
- DEV-10043 qatori ochilganda 29.09.2026 / 13:02–18:06 / jami 5 soat 4 daqiqa ko'rindi. Paginationning ikkinchi sahifasida 8 task, avvalgi 2 point/kun va barcha 28 taskning jami saqlandi. Brauzer console'ida tegishli error/warning ko'rilmadi. Screenshot: `/private/tmp/team-analytics-sprint-production.jpg`.
- Post-deploy backend va worker healthy, frontend running; Postgres/Caddy va boshqa loyihalar containerlari qayta yaratilmagan. Avtomatik Jira sync job 77 `done`, 1 urinish, `last_error=null`; checkpoint 06.10.2026 13:56:31 (Asia/Tashkent).
