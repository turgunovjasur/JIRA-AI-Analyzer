# JIRA S1 Sections and Shared Comment Splitting Design

## Muammo

Webhook Servis-1 va Servis-2 tayyorlagan ADF comment JIRA hajm limitidan
oshsa, JIRA `CONTENT_LIMIT_EXCEEDED` bilan commentni rad etadi. Hozirgi simple
fallback ham o'sha uzun mazmunni bitta comment qilib yuborgani uchun yana
yiqiladi. Natijada AI run yakunlangan bo'lsa ham to'liq S1 yoki S2 comment
taskda ko'rinmay qolishi mumkin.

S1 commentida qaysi hisobot bo'limlari JIRA'ga yozilishini kompaniya admini
webhook sozlamasidan boshqarishi ham kerak. Bu sozlama manual Checker UI
hisobotiga ta'sir qilmasligi kerak.

## Maqsad

- Webhook S1 uchun JIRA comment bo'limlarini alohida yoqish/o'chirish.
- S1 va S2 commentlari limitdan oshsa mazmunni qisqartirmasdan bo'lib yozish.
- S1 va S2 formatterlarini alohida saqlab, bo'lish/yuborish kodini umumiy
  komponentda ishlatish.
- Barcha kerakli comment qismlari yozilmaguncha servisni `done` qilmaslik.

## Scope tashqarisi

- Manual Checker UI ko'rinishini o'zgartirish.
- S2 uchun comment bo'limlari sozlamasini qo'shish.
- AI prompt, multi-agent JSON kontrakti yoki compliance score hisobini
  o'zgartirish.
- JIRA API limitini foydalanuvchi sozlaydigan maydon qilish.

## S1 webhook sozlamasi

`TZPRCheckerSettings` ichida webhook JIRA commentiga xos
`jira_comment_sections` ordered-list maydoni bo'ladi. Ruxsat etilgan qiymatlar:

1. `statistics` — PR va task statistikasi.
2. `ai_pipeline` — agentlar pipeline holati.
3. `summary` — yakuniy xulosa.
4. `completed` — bajarilgan talablar.
5. `failed` — bajarilmagan talablar.
6. `skipped` — skip qilingan talablar.
7. `issues` — qo'shimcha tekshiruv natijalari.

Default qiymatda yettala bo'lim yoqilgan. Eski kompaniya JSON sozlamasida yangi
maydon bo'lmasa ham shu default ishlaydi.

Quyidagi strukturaviy kontent sozlamadan qat'i nazar saqlanadi:

- `[AI_S1]` marker;
- checker nomi va compliance score;
- re-check belgisi va mavjud muhim run warninglari;
- bo'lingan commentdagi qism raqami;
- footer.

Sozlama zanjiri:

1. `config/app_settings.py` — default va validatsiya.
2. `services/api/settings_api.py` — webhook config read/save.
3. `frontend/src/lib/types.ts` va `frontend/src/lib/backend.ts` — payload tipi.
4. `frontend/src/app/api/settings/webhook/route.ts` — BFF payload.
5. `frontend/src/components/settings-panel.tsx` — Webhook → Servis-1 toggle'lari.
6. `docs/SETTINGS_DEPENDENCY_GUIDE.md` — sozlama faqat JIRA commentga tegishini
   qayd etish.

Mavjud checker `visible_sections` maydoni manual Checker UI contracti uchun
qoladi. Yangi webhook maydoni undan mustaqil bo'ladi.

## Umumiy comment publisher

S1 va S2 formatterlari to'liq ADF hujjat yaratishda davom etadi. Yangi umumiy
JIRA publisher/splitter tayyor hujjatni qabul qiladi:

```text
S1 JiraADFFormatter -----------\
                                +--> shared ADF publisher/splitter --> JIRA
S2 TestcaseADFFormatter -------/
```

Umumiy komponent servisga xos biznes kontentini bilmaydi. Caller unga kamida
task key, `[AI_S1]` yoki `[AI_S2]` marker, servis nomi va tayyor ADF hujjatni
beradi. Natija `success`, yozilgan qismlar soni va xato tafsilotini qaytaradi.

JIRA limitiga yaqinlashmaslik uchun komponent markazlashtirilgan konservativ
ichki targetdan foydalanadi. Bu JIRA protokol cheklovi bo'lib, user setting
emas.

## Bo'lish algoritmi

1. Tayyor ADF hujjat hajmi targetdan kichik bo'lsa bitta comment yuboriladi.
2. Targetdan katta bo'lsa barcha qismlar avval xotirada quriladi va jami `N`
   aniqlanadi.
3. Alohida qisqa hint comment yoziladi:

   ```text
   [AI_S1]
   Servis-1 hisoboti JIRA hajm limitidan oshdi.
   To'liq natija qisqartirilmasdan N ta commentga bo'lib yuboriladi.
   ```

   S2 uchun marker va servis nomi mos ravishda `[AI_S2]` va `Servis-2` bo'ladi.

4. Har bir qism `[AI_S1]`/`[AI_S2]`, task key va `Qism: i/N` sarlavhasi bilan
   yoziladi.
5. Avval top-level ADF node chegarasida bo'linadi.
6. Bitta top-level node katta bo'lsa uning child node'lari bo'yicha bo'linadi.
7. Bitta requirement/testcase paragrafi ham katta bo'lsa matn avval yangi qator
   va gap chegarasida, zarur bo'lsa Unicode-safe belgilar chegarasida bo'linadi.
8. Hech bir original matn tashlab yuborilmaydi va takrorlanmaydi. Faqat har
   qismga marker/sarlavha kabi strukturaviy metadata qo'shiladi.

JIRA lokal o'lchovdan kichik hujjatga ham `CONTENT_LIMIT_EXCEEDED` qaytarsa,
publisher hali hech qanday hisobot qismini yozmasdan kichikroq target bilan
qismlarni qayta quradi. Boshqa ADF xatosida mavjud simple-format fallback
saqlanadi; simple matn ham shu umumiy mexanizm orqali bo'lib yoziladi.

## S1 oqimi

1. Webhook kompaniya settingsini qayta yuklaydi.
2. `JiraADFFormatter` faqat `jira_comment_sections`da yoqilgan bo'limlar bilan
   to'liq S1 ADF hujjatini yaratadi.
3. Umumiy publisher uni bitta yoki bir nechta comment qilib yozadi.
4. Barcha kerakli commentlar muvaffaqiyatli yozilgandagina
   `service1_status='done'` va compliance score saqlanadi.
5. Score threshold'dan past bo'lsa mavjud `[AI_S1][WARN_LOW_SCORE]` return
   notification alohida comment bo'lib qoladi.

## S2 oqimi

S2 uchun bo'lim toggle'i bo'lmaydi. Testcase formatter barcha testcase
kontentini doim to'liq yaratadi. O'sha umumiy publisher S2 ADF yoki simple
commentini hajmga qarab bitta yoki bir nechta comment qilib yozadi. Barcha
qismlar yozilgandagina Servis-2 muvaffaqiyatli deb hisoblanadi.

## Xato boshqaruvi

- `CONTENT_LIMIT_EXCEEDED` alohida aniqlanadi va generic ADF failure sifatida
  yashirilmaydi.
- Hint va barcha qismlar muvaffaqiyatli yozilishi umumiy publication success
  sharti hisoblanadi.
- Qism yozilmasa logda task, servis, qism raqami va JIRA response turi chiqadi.
- Publication muvaffaqiyatsiz bo'lsa S1/S2 `done` qilinmaydi.
- Markerlar `[AI_S1]` va `[AI_S2]` ko'rinishini saqlaydi; CommentSeparator va
  duplicate prevention eski markerlarni tanishda davom etadi.

## Tekshiruv strategiyasi

- S1 yettala setting default yoqilgan va eski JSON bilan backward-compatible.
- Webhook settings read/save yangi ordered-listni saqlaydi va validatsiya qiladi.
- S1 formatter har bir toggle o'chirilganda faqat shu bo'limni olib tashlaydi;
  manual Checker UI contracti o'zgarmaydi.
- Kichik S1/S2 ADF bitta comment bo'lib yoziladi va hint yozilmaydi.
- Uzun S1/S2 ADF hint + `1/N ... N/N` commentlarga bo'linadi.
- Bir dona juda katta requirement/testcase ham mazmun yo'qotmasdan bo'linadi.
- JIRA `CONTENT_LIMIT_EXCEEDED` fallbacki kichikroq qismlar bilan ishlaydi.
- Simple-format fallback uzun bo'lsa ham bo'linadi.
- Bir qism muvaffaqiyatsiz bo'lsa servis `done` bo'lmaydi.
- Webhook, UI va worker bir xil checker/testcase engine ishlatishi saqlanadi;
  o'zgarish faqat webhook JIRA publication qatlamida bo'ladi.

