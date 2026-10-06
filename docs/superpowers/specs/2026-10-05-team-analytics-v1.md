# Team Analytics v1 — tasdiqlangan scope

Foydalanuvchi 2026-10-05 kuni ushbu scope'ni tasdiqladi va hujjatni saqlash hamda kod yozishni boshlashni so'radi.

## Product

CTO/PM uchun company-admin access bilan alohida pullik `team_analytics` moduli. Bitta company-level sozlama: vaqt hisoblanadigan Jira status nomi. Default `In Progress`. Shu statusga kirganda vaqt yuradi; boshqa istalgan statusga chiqishda to'xtaydi; qaytishda jami davom etadi. Timeout uchun alohida sozlama yoki maxsus hisoblash yo'q. Bir task boshlanishi boshqasini avtomatik to'xtatmaydi. Vaqt kalendar sekundlari sifatida hisoblanadi va soat/daqiqada ko'rsatiladi; ish kalendari, SP normasi, ogohlantirishlar v1 scope'iga kirmaydi.

## Data

Tenant va Jira manbasi bilan ajratilgan append-only voqealar: issue ID/key, loyiha, task turi/summary, status ID/nomi, assignee barqaror ID/displayName, story point, sprint snapshot, tegishli changelog old/new qiymatlar, Jira hodisa vaqti, server qabul vaqti, vaqt manbasi va deduplication kaliti. Barcha statuslar va status o'zgarmagan assignee/point/sprint update'lari AI triggerlaridan mustaqil yig'iladi. Faqat zarur maydonlar saqlanadi; token, description va kommentlar saqlanmaydi.

Tarix event-time bo'yicha qayta o'qiladi: kech/tartibsiz eventlar replay orqali hisobga olinadi, dublikatlar unique constraint orqali rad etiladi. Settings versiyalari effective timestamp bilan saqlanadi, eski hisob yangi status bilan qayta talqin qilinmaydi. Kuzatuvdan oldingi noma'lum vaqt to'qilmaydi; birinchi snapshotdan kuzatuv boshlanadi. Intervallar voqealar va settings versiyalaridan qayta tiklanadi, derived interval jadvali shart emas. Assignee almashsa interval yangi ijrochiga ajratiladi.

## Boundaries

Dashboard faqat kuzatilgan Jira task/userlarni ko'rsatadi; to'liq Jira roster emas. Dastlabki tarix importi va Jira reconciliation keyingi ish; webhookda yo'qolgan hodisalarni v1 avtomatik tiklamaydi. Qo'shimcha sozlama ko'rsatilmaydi. Modul default o'chiq, super-admin yoqadi. Analytics AI Webhook addoniga qaram emas, lekin mavjud company webhook routing/secret ishlatiladi.

## Roadmap

ROADMAP_SAAS.md P2 advanced analytics; packaging (1), data (3), tenant/access (4–5), UI (9), reliability (11). PROGRESS_LOG.md yangilanmaydi. Testlarni ishga tushirish alohida foydalanuvchi so'roviga bog'liq.
