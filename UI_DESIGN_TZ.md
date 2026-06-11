# TZ — JIRA-AI-Analyzer: Multi-agent Checker, Testcase va Monitoring uchun yangi UI

> Bu hujjat dizayn topshirig'i (design brief). Maqsad — Claude (yoki dizayner)
> uchun zamonaviy, minimalistik UI mockuplarini yaratish uchun aniq spetsifikatsiya.

---

## 1. Kontekst va maqsad

**Mahsulot:** JIRA-AI-Analyzer — JIRA task'lari "Testing" statusiga o'tganda
avtomatik ravishda GitHub PR'ni texnik topshiriq (TZ) ga moslikni AI bilan
tekshiradigan multi-tenant SaaS platforma.

**Hozirgi holat:** ilova Next.js (React) da, 3 ta asosiy ish ekrani bor:
`/tzpr` (checker), `/testcase` (testcase generator), `/monitoring`.
UI funksional, lekin eski va og'ir — zamonaviy emas.

**Vazifa:** quyidagi 3 modul uchun **zamonaviy, minimalistik, yengil va aniq**
UI redizayn:
1. **Multi-agent Checker** — TZ↔PR moslik tahlili (3 ta AI agent ketma-ket ishlaydi)
2. **Multi-agent Testcase** — test case'lar generatsiyasi
3. **Monitoring** — webhook va task'lar real-time kuzatuvi

**Asosiy talab:** uchchala modul ham AI agentlar pipeline'ini tushunarli,
jonli va chiroyli ko'rsatishi kerak — bu mahsulotning "yuzi".

---

## 2. Dizayn tamoyillari (minimalist + modern)

### Umumiy ruh
- **Minimalizm:** ortiqcha bezak yo'q. Har element funksional bo'lsin.
- **Ko'p bo'sh joy (whitespace):** elementlar nafas olsin, zичlashtirilmasin.
- **Aniqlik:** foydalanuvchi bir qarashda holatni tushunsin.
- **Yengillik:** og'ir soyalar, gradientlar, ortiqcha chegaralar yo'q.

### Vizual til
- **Rang palitrasi:** neytral asos (oq / juda och kulrang fon, dark mode'da
  chuqur kulrang-qora). **Bitta accent rang** (masalan indigo/ko'k yoki binafsha).
  Accent faqat asosiy harakatlar va faol holatlar uchun.
- **Status ranglari** (past to'yingan, "muted" — pastel emas, qichqiriq emas):
  - Muvaffaqiyat / completed → yashil
  - Ogohlantirish / partial → amber
  - Xato / failed / blocked → qizil
  - Jarayonda / running → accent rang (pulslanuvchi)
  - Kutilmoqda / pending → neytral kulrang
- **Tipografika:** bitta zamonaviy sans-serif (Inter / Geist). Aniq ierarxiya:
  sarlavha / sarlavhacha / asosiy matn / yordamchi matn. **ID, task key, kod,
  model nomi, fayl nomi uchun — monospace shrift.**
- **Burchaklar:** izchil border-radius (8–12px). Yumshoq, lekin "pufakcha" emas.
- **Chegaralar:** 1px, past-kontrast. Soyalar — minimal, faqat overlay/modal uchun.
- **Ikonkalar:** ingichka chiziqli (line icons), bir xil uslub (Lucide kabi).
- **Komponent uslubi:** card-based, lekin yengil — chegara yoki juda nozik fon farqi.

### Harakat (motion)
- Mayda, maqsadli animatsiyalar: agent holati o'zgarishi, progress ring, skeleton.
- Sahifa va holat o'tishlari silliq (150–250ms), "ko'zga urilmaydigan".
- Running agent — yumshoq pulslanish yoki aylanuvchi progress halqasi.

### Rejimlar
- **Light va Dark mode** — ikkalasi ham birinchi darajali, to'liq qo'llab-quvvatlansin.

---

## 3. Global layout va navigatsiya (app shell)

- **Chap tomonda ingichka sidebar:** logo, asosiy navigatsiya (Dashboard,
  Checker, Testcase, Monitoring, Settings, Team/Admin). Faol bo'lim accent bilan
  belgilanadi. Sidebar yig'iladigan (collapsible) bo'lsin.
- **Yuqorida yengil topbar:** sahifa nomi, qidiruv (task key bo'yicha), kompaniya
  nomi/foydalanuvchi avatari, dark/light toggle.
- **Asosiy kontent maydoni:** keng, markazlashtirilgan, max kenglik bilan.
- **Multi-tenant belgisi:** topbar'da hozirgi kompaniya nomi nozik ko'rsatilsin.
- Rollar: super admin / kompaniya admin / oddiy foydalanuvchi — navigatsiya
  ko'rinishi rolga qarab farqlanadi (admin bo'limlari faqat adminlarga).

---

## 4. EKRAN A — Multi-agent Checker (`/tzpr`)

Checker 3 ta AI agentni ketma-ket ishlatadi:
- **Agent 1 — Scope Builder:** TZ, izohlar va Figma'dan talablar (requirement) ro'yxatini ajratadi.
- **Agent 2 — Verifier:** har bir talabni kod/PR bo'yicha parallel tekshiradi.
- **Agent 3 — Arbiter:** natijalarni birlashtirib yakuniy moslik bali va xulosani beradi.

Ekran 3 holatdan iborat: **Kirish → Jonli ishlash → Natija**.

### A1. Kirish holati
- Markazda sodda kartochka: **JIRA task key** kiritish maydoni (masalan `DEV-1234`),
  monospace.
- "Tahlilni boshlash" asosiy tugmasi (accent).
- Ixtiyoriy sozlamalar (yig'ilgan holatda): Smart Patch, output rejimi.
- Pastda — **so'nggi run'lar ro'yxati** (oxirgi 10 ta): task key, sana, moslik bali
  (rangli badge), holat. Bosilganda o'sha run natijasi ochiladi.

### A2. Jonli ishlash holati (eng muhim ekran)
Bu ekran **multi-agent pipeline'ni jonli** ko'rsatadi:

- **Agent pipeline vizualizatsiyasi** — markaziy element. 3 ta agent bosqichi
  (gorizontal stepper yoki vertikal timeline):
  - Har agent uchun **node/kartochka:** agent nomi, ikona, holat indikatori,
    bajarilish vaqti (latency), ishlatilgan **model badge** (masalan `gemini-2.5-flash`).
  - **Holatlar:** `pending` (kulrang, so'nik) → `running` (accent, pulslanuvchi
    progress halqasi) → `completed` (yashil ✓) / `failed` / `blocked` (qizil).
  - Agentlar orasidagi bog'lovchi chiziqlar holatga qarab rang oladi.
- **Agent 2 maxsus ko'rinishi:** Agent 2 har talabni parallel tekshiradi —
  shu agent faol bo'lganda kichik ko'rsatkich: "12 talabdan 7 tasi tekshirildi"
  (progress bar yoki nuqtalar qatori). Parallel ishlash hissi berilsin.
- **Jonli event log** (ixtiyoriy, yig'iladigan panel): vaqt belgisi bilan
  qisqa qatorlar ("Agent1 yakunlandi — 12 talab ajratildi", "Agent2 boshlandi").
- Yuqorida: task key, umumiy o'tgan vaqt (sekundomer), bekor qilish tugmasi.
- Vizual sokin bo'lsin — "yuklanmoqda" tartibsizligi emas, ishonchli jarayon hissi.

### A3. Natija holati
Yakuniy hisobot. Tepada **xulosa zonasi**, pastda **batafsil**.

- **Moslik bali (compliance score):** katta, aniq raqam (0–100). Yonida verdict
  yorlig'i (masalan "Mos", "Qisman mos", "Past moslik") rangli. Dumaloq progress
  yoki gorizontal o'lchov bilan vizuallashtirilsin.
- **Qisqa xulosa:** Agent 3 ning 2–4 qatorli umumiy bahosi.
- **Talablar matritsasi (requirement matrix)** — asosiy jadval/ro'yxat:
  - Har qatorda: talab matni, manbasi (TZ / izoh / Figma — kichik badge),
    holati (✓ bajarilgan / ⚠ qisman / ✗ bajarilmagan), va **dalil (evidence)** —
    qaysi fayl/funksiyada topilgani (monospace).
  - Holat bo'yicha filtrlash mumkin bo'lsin.
- **Bo'limlar (kartochkalar yoki yig'iladigan panellar):**
  - ✅ Bajarilgan talablar
  - ⚠️ Qisman bajarilgan
  - ❌ Bajarilmagan talablar
  - 🐛 Potensial muammolar (kod sifati, buglar)
  - 🎨 Figma dizayn mosligi (agar Figma ma'lumoti bo'lsa)
  - **Qo'shimcha o'zgarishlar (extra / scope creep):** TZ'da yo'q, lekin kodda
    bor o'zgarishlar — risk darajasi bilan (low / medium / high).
- **Run meta-paneli** (nozik, ikkilamchi): har agent uchun model, latency,
  ogohlantirishlar; PR statistikasi (fayllar soni, +/− qatorlar); token/narx
  ko'rsatkichi (agar mavjud bo'lsa).
- **Texnik nosozliklar** bo'lsa — alohida ogohlantirish bloki.
- Yuqori o'ng burchakda: "Qayta tahlil", JIRA'da ochish, hisobotni nusxalash.

---

## 5. EKRAN B — Multi-agent Testcase (`/testcase`)

Testcase generatori TZ va PR asosida test case'lar yaratadi. Tuzilma Checker'ga
o'xshash: **Kirish → Jonli ishlash → Natija** — izchillik uchun bir xil til.

### B1. Kirish
- JIRA task key kiritish.
- **Test turlari tanlovi:** positive, negative, edge case, UI, integratsiya va h.k.
  — toggle/chip ko'rinishida ko'p tanlovli.
- Test case'lar maksimal soni (raqamli).
- "Generatsiyani boshlash" tugmasi.

### B2. Jonli ishlash
- Checker bilan bir xil uslubdagi agent/bosqich pipeline vizualizatsiyasi
  (JIRA ma'lumot olish → TZ tahlil → AI generatsiya → JSON parse → natija).
- Jonli holat: "8 test case yaratildi..." kabi hisoblagich.

### B3. Natija
- **Test case'lar ro'yxati** — har biri yig'iladigan kartochka:
  - Sarlavha, **turi** (rangli badge: positive/negative/edge...), **muhimligi**
    (priority: high/medium/low).
  - Ochilganda: oldindan shartlar, **qadamlar** (raqamlangan ro'yxat),
    **kutilgan natija**, test ma'lumotlari.
- Yuqorida: jami test case soni, turlar bo'yicha statistika (kichik diagramma
  yoki badge'lar qatori).
- Turlar/priority bo'yicha filtr.
- Eksport / nusxalash (JIRA'ga, Markdown, jadval).

---

## 6. EKRAN C — Monitoring (`/monitoring`)

Webhook orqali kelayotgan task'lar va tizim holatining real-time kuzatuvi.
Operatsion dashboard — "boshqaruv markazi" hissi, lekin baribir minimalistik.

### C1. Yuqori — holat ko'rsatkichlari (KPI qatori)
Nozik kartochkalar qatori: bugungi tekshirilgan task'lar, jarayonda, qaytarilgan,
bloklangan, xato. Har biri raqam + kichik trend/ranglik bilan.

### C2. Asosiy — task'lar oqimi (live feed)
- **Task'lar ro'yxati/jadvali**, real-time yangilanuvchi:
  - Task key (monospace), kompaniya, kelgan vaqt.
  - **Servis-1 holati** va **Servis-2 holati** — alohida kichik status indikator
    (pending / progressing / done / error / blocked / skip).
  - Moslik bali (bo'lsa), umumiy task holati.
  - Yangi kelgan qator nozik animatsiya bilan paydo bo'lsin.
- Qatorni bosganda — yon panel (drawer): o'sha task uchun to'liq xronologiya,
  agent natijalari, xato xabarlari.
- Filtr: holat, kompaniya, sana oralig'i; qidiruv task key bo'yicha.

### C3. Tizim holati paneli
- **AI queue holati:** navbatdagi/ishlayotgan, rate-limit kutuvi.
- **Gemini API kalitlari:** har kalit holati (faol / "freeze" — muzlatilgan,
  qachongacha). Kichik indikatorlar.
- **Bloklangan task'lar va retry:** keyingi qayta urinish vaqti bilan.
- **Webhook event log:** so'nggi hodisalar oqimi, vaqt belgisi bilan.

### C4. Real-time xulq-atvor
- Yangilanishlar silliq (avtomatik), butun sahifa "sakramaydi".
- "Jonli" indikatori (kichik pulslanuvchi nuqta).

---

## 7. Umumiy komponentlar (uchchala ekran uchun)

Bir butun dizayn tizimi sifatida quyidagilar bir xil uslubda bo'lsin:
- **Status badge / pill** — holat ranglari bilan (kichik, nozik).
- **Agent / bosqich node** — pipeline elementi, 4 ta holat varianti.
- **Progress indikatorlari** — halqa (ring), chiziqli, nuqtali (parallel uchun).
- **Yig'iladigan panel (accordion)** — bo'limlar uchun.
- **Yon panel (drawer)** — tafsilotlar uchun.
- **Skeleton loader** — yuklanish holati.
- **Bo'sh holat (empty state)** — do'stona illyustratsiya/ikona + qisqa matn.
- **Toast / inline ogohlantirish** — xato va muvaffaqiyat xabarlari.
- **Kod/dalil bloki** — monospace, nozik fon, fayl nomi sarlavha bilan.
- **Statistika kartochkasi (KPI)** — raqam + yorliq.

---

## 8. Holatlar (har ekran uchun ko'rsatilsin)

Har asosiy ekran uchun mockuplarda quyidagilar bo'lsin:
- **Empty** — hali ma'lumot yo'q (birinchi kirish).
- **Loading / running** — jarayon davom etmoqda.
- **Success** — to'liq natija.
- **Error / blocked** — xato (masalan PR topilmadi, AI ishlamadi, TZ qisqa) —
  aniq, ayblovsiz xabar va keyingi qadam taklifi.
- **Partial** — natija bor, lekin ogohlantirishlar bilan.

---

## 9. Responsive va accessibility

- **Responsive:** asosiy maqsad — desktop (keng ekran). Lekin layout planshet va
  tor ekranlarda ham buzilmasin (pipeline vertikalga o'tsin).
- **Accessibility:** rang faqat yagona signal bo'lmasin (ikona/matn ham qo'shilsin);
  yetarli kontrast; klaviatura bilan navigatsiya; fokus holatlari ko'rinsin.

---

## 10. Texnik kontekst (dizaynerga eslatma)

- Stek: Next.js (React) + Tailwind CSS. Komponentlar shu bilan amalga oshiriladi —
  dizayn real qiluvchan (implementable) bo'lsin, ekzotik effektlardan voz keching.
- Til: interfeys **o'zbek tilida** (matnlar o'zbekcha).
- Mavjud ma'lumotlar (designer kontekst uchun): har checker run'da run_id, task key,
  3 agent (holat, model, latency, ogohlantirishlar), talablar ro'yxati,
  verifikatsiyalar, moslik bali, verdict, extra o'zgarishlar.
- Multi-tenant: bir nechta kompaniya bir platformada — kompaniya konteksti
  ko'rinib tursin, lekin ekranni band qilmasin.

---

## 11. Dizaynerdan kutilgan natija (deliverables)

1. **Dizayn tizimi:** rang palitrasi (light + dark), tipografika shkalasi,
   spacing/grid, komponentlar kutubxonasi (7-bo'lim).
2. **Asosiy ekran mockuplari** (light + dark):
   - Checker: Kirish, Jonli ishlash, Natija
   - Testcase: Kirish, Jonli ishlash, Natija
   - Monitoring: to'liq dashboard
3. **Holat variantlari:** empty / loading / error har asosiy ekran uchun.
4. **Agent pipeline komponenti** — alohida, batafsil (4 holat + Agent 2 parallel ko'rinishi).
5. (Ixtiyoriy) asosiy o'tishlar uchun mikro-animatsiya tavsiflari.

**Eng muhim urg'u:** multi-agent jarayon — 3 ta AI agentning jonli, ishonchli va
chiroyli ko'rsatilishi mahsulotning asosiy farqlovchi jihati. Shu element
mukammal ishlansin.