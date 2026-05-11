# Permission Matrix

Bu hujjat loyiha ichidagi rollar va ularning modul hamda boshqaruv huquqlarini belgilaydi.

## Rollar

- `super_admin`
- `company_admin`
- `user`

## Modul Access

| Modul | Super Admin | Company Admin | User |
|---|---|---|---|
| `TZ-PR Checker` | Ha | Ha | Ha |
| `Test Case Generator` | Ha | Ha | Ha |
| `Monitoring` | Ha | Ha, agar `Webhook` yoqilgan bo'lsa | Yo'q |
| `Webhook` | Ha | Ha, agar kompaniyaga addon yoqilgan bo'lsa | Yo'q |
| `Bug Analyzer` | Support/test uchun | Agar yoqilgan bo'lsa | Agar yoqilgan bo'lsa |
| `Sprint Statistics` | Support/test uchun | Agar yoqilgan bo'lsa | Agar yoqilgan bo'lsa |
| `Sprint Report` | Support/test uchun | Agar yoqilgan bo'lsa | Agar yoqilgan bo'lsa |

Eslatma:
- `super_admin` uchun support/test access ochiq
- `TZ-PR Checker` va `Test Case Generator` `base` plan ichida default ochiq
- `company_admin` va `user` uchun qolgan access kompaniyada modul yoqilgan bo'lsa ishlaydi
- `Webhook` pullik addon sifatida sotiladi
- `Monitoring` alohida sotilmaydi; `Webhook` yoqilganda avtomatik ochiladi
- `Webhook` faqat `company_admin` va `super_admin` uchun; oddiy `user`ga hech qachon ochilmaydi

## Company Creation Defaults

- Kompaniya yaratilganda default:
  - `tz_pr_checker = ON`
  - `testcase_generator = ON`
  - `webhook = super_admin tanloviga ko'ra`
  - `monitoring = webhook`dan hosil bo'ladi (derived)
- Kompaniya yaratilganda default akkauntlar:
  - 1 ta `company_admin` yaratiladi
  - oddiy `user` soni default `0`
- Seat qoidasi:
  - `seat_limit` oddiy `user`lar uchun limit
  - `company_admin` seat limitga kirmaydi
  - `company_admin` faqat `seat_limit` doirasida user qo'sha oladi

## Boshqaruv Huquqlari

| Amal | Super Admin | Company Admin | User |
|---|---|---|---|
| Kompaniya yaratish | Ha | Yo'q | Yo'q |
| Kompaniyani aktiv/nofaol qilish | Ha | Yo'q | Yo'q |
| Seat limit o'zgartirish | Ha | Yo'q | Yo'q |
| Pullik modul yoqish/o'chirish | Ha | Yo'q | Yo'q |
| Subscription boshqarish | Ha | Yo'q | Yo'q |
| Company userlarini boshqarish | Ha | Ha, faqat o'z kompaniyasi | Yo'q |
| Company integrations boshqarish | Ha | Ha, faqat o'z kompaniyasi | Yo'q |
| Webhook settings boshqarish | Ha | Ha, faqat `Webhook` addon yoqilgan o'z kompaniyasi | Yo'q |
| Shaxsiy API keylarni boshqarish | Ha | Ha | Ha |
| Personal modul sozlamalari | Ha | Ha | Ha |
| Monitoring task delete | Ha | Yo'q | Yo'q |

## Monitoring Policy

- `super_admin` barcha kompaniyalar monitoringini ko'radi
- `company_admin` faqat o'z kompaniyasi monitoringini ko'radi
- `user` monitoringni ko'rmaydi
- `task delete` faqat `super_admin` uchun ruxsat etilgan
- `Monitoring` access'i `Webhook` entitlement'dan hosil qilinadi

## Billing Policy

- Hozircha billing `manual`
- Subscription statuslar:
  - `trial`
  - `active`
  - `past_due`
  - `suspended`
  - `cancelled`
- `suspended` va `cancelled` holatlarida kompaniya login qila olmaydi
- `trial` va `active` obuna muddati tugasa login bloklanadi
- `trial`, `active`, `past_due` holatlari uchun `billing_end_date` majburiy
- Billing sanalari `YYYY-MM-DD` formatida saqlanishi kerak

## Integrations Policy

- `JIRA`, `GitHub`, `Figma`:
  - company-level shared konfiguratsiya → `company_admin` va `super_admin`
  - user-level shaxsiy API keylar → `company_admin`, `user`, `super_admin`
- `AI API key`:
  - ishlash tartibi: `user key` → `company admin shared key` → `super_admin default key`
  - user o'zinikini kiritsa ustun turadi

## Hozirgi Amaliy Qoidalar

- `TZ-PR Checker` va `Test Case Generator` asosiy ishchi modullar
- `Webhook` alohida pullik modul
- `Monitoring` `Webhook` addonining kuzatuv interfeysi hisoblanadi
- `TZ-PR Checker` va `Test Case Generator` bazaviy obuna entitlement'i sifatida ishlaydi
- `Monitoring` faqat operatsion va admin darajadagi ko'rish uchun
- `company_admin` customer-side operator rolini bajaradi
- `user` faqat foydalanish rolini bajaradi

## O'zgarish Qoidasi

- Keyingi permission o'zgarishlari bu hujjat bilan birga yangilansin
- Koddagi access logic imkon qadar shu matritsaga mos bo'lsin
