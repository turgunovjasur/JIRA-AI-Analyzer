# Repository Instructions

## Default Planning Rule

- Katta o'zgarishlar, arxitektura qarorlari yoki product-ready ishlarda avval [ROADMAP_SAAS.md](/Users/mac/Documents/projects/QA-Assistant/ROADMAP_SAAS.md) dagi bosqichlar tekshirilsin.
- Bu repo uchun ustuvor maqsad: loyihani to'liq sotuvga tayyor SaaS mahsulotga aylantirish.
- Yangi feature yoki refactor taklif qilinganda, imkon qadar roadmapdagi eng yaqin bosqich bilan bog'lab ishlansin.
- Agar ish roadmapdan tashqarida bo'lsa, u vaqtinchalik yoki ikkinchi darajali ish sifatida qayd etilsin.

## Source of Truth

- SaaS readiness bo'yicha asosiy hujjat: [ROADMAP_SAAS.md](/Users/mac/Documents/projects/QA-Assistant/ROADMAP_SAAS.md)
- Bajarilgan ishlar va keyingi qadamlar jurnali: [PROGRESS_LOG.md](/Users/mac/Documents/projects/QA-Assistant/PROGRESS_LOG.md)
- Role va access qoidalari: [PERMISSION_MATRIX.md](/Users/mac/Documents/projects/QA-Assistant/PERMISSION_MATRIX.md)

## Progress Tracking

- `PROGRESS_LOG.md` faqat foydalanuvchi alohida so'raganda yangilansin.

## Code Change Permission

- Kod yozish, fayl o'zgartirish, patch qilish, refactor yoki build/test kabi write-side effect beradigan ishlarni boshlashdan oldin foydalanuvchidan aniq ruxsat so'ralsin.
- Foydalanuvchi `ha`, `bajar`, `kirit`, `implement qil` yoki shunga teng aniq rozilik bermaguncha faqat read-only tahlil, taklif va tushuntirish berilsin.

## Testing

- Testlar faqat foydalanuvchi alohida so'raganda ishga tushirilsin.
