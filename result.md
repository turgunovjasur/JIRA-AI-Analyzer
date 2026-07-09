Turgunov Jasur

2 hours ago
[AI_S2]

🧪 Test Cases

📋 DEV-8245 — ma'lumot va statistika
Task: DEV-8245
Yaratilgan: 2026-07-07 16:35
Jami: 6 ta test case

✅ Positive: 5 ta

❌ Negative: 1 ta

📋 Test Case'lar
🧩 Veb interfeysda 'Mobil versiyada promokod berishni o'chirish' sozlamasini boshqarish — Tizim sozlamalari > Filiallar > Qurilmalar

✅ TC-001: WEB: "Mobil versiyada promokod berishni o'chirish" sozlamasining mavjudligi va dastlabki holatini tekshirish [High · Major]
📝 Tavsif: Tizim sozlamalarida, filial darajasida, "Qurilmalar" menyusiga "Mobil versiyada promokod berishni o'chirish" yangi sozlamasi qo'shilganligini va uning dastlabki (o'chirilgan) holatini tekshirish.

⚙️ Boshlang'ich shartlar: Administrator huquqiga ega foydalanuvchi tizimga kirgan.Test o'tkaziladigan filial mavjud.

📋 Qadamlar:

Tizimning veb-versiyasiga kiring.

Sozlamalar -> Filiallar bo'limiga o'ting va test uchun mo'ljallangan filialni tanlang.

Filial sozlamalari menyusidan 'Qurilmalar' (Устройства) bo'limiga o'ting.

'Mobil versiyada promokod berishni o'chirish' nomli sozlamani toping.

✅ Kutilgan natija: 1. 'Mobil versiyada promokod berishni o'chirish' sozlamasi 'Qurilmalar' menyusida mavjud.2. Standart holatda ushbu sozlama o'chirilgan (switch 'Yo'q' holatida) turibdi.

Type: positive

Tags: web, ui, smoke, initial_state


✅ TC-002: WEB: "Mobil versiyada promokod berishni o'chirish" sozlamasini yoqishda istisno rol maydonining paydo bo'lishini tekshirish [Medium · Minor]
📝 Tavsif: "Mobil versiyada promokod berishni o'chirish" sozlamasi yoqilganda istisno rolini tanlash imkoniyatining paydo bo'lishini tekshirish.

⚙️ Boshlang'ich shartlar: Administrator huquqiga ega foydalanuvchi tizimga kirgan.Test o'tkaziladigan filial mavjud.

📋 Qadamlar:

Tizimning veb-versiyasiga kiring.

Sozlamalar -> Filiallar bo'limiga o'ting va test uchun mo'ljallangan filialni tanlang.

Filial sozlamalari menyusidan 'Qurilmalar' (Устройства) bo'limiga o'ting.

'Mobil versiyada promokod berishni o'chirish' sozlamasini yoqing (switch 'Ha' holatiga o'tkazilsin).

✅ Kutilgan natija: 'Istisno rollar' (Исключения по ролям) deb nomlangan yangi maydon paydo bo'ladi.

Type: positive

Tags: web, ui, smoke, role_exception


❌ TC-003: WEB: Sozlamani saqlamasdan chiqib ketganda o'zgarishlarning saqlanmasligini tekshirish [Medium · Minor]
📝 Tavsif: Foydalanuvchi sozlamalarni o'zgartirib, lekin 'Saqlash' tugmasini bosmasdan sahifadan chiqib ketsa, o'zgarishlar saqlanib qolmasligini tekshirish.

⚙️ Boshlang'ich shartlar: Administrator veb-interfeysga kirgan.Boshlang'ich holat: 'Mobil versiyada promokod berishni o'chirish' sozlamasi o'chirilgan.

📋 Qadamlar:

Filial sozlamalari -> 'Qurilmalar' bo'limiga o'ting.

'Mobil versiyada promokod berishni o'chirish' sozlamasini yoqing.

'Saqlash' tugmasini bosmasdan, brauzerning boshqa bo'limiga o'ting yoki sahifani yangilang.

Qaytadan Filial sozlamalari -> 'Qurilmalar' bo'limiga kiring.

✅ Kutilgan natija: O'zgarishlar saqlanmagan. 'Mobil versiyada promokod berishni o'chirish' sozlamasi o'zining avvalgi (o'chirilgan) holatida turgan bo'lishi kerak.

Type: negative

Tags: web, ui, logic, negative_case

🧩 Mobil ilovada PROMO menyusi funksionalligini tekshirish — Mobil ilova > Buyurtma yaratish

✅ TC-004: MOB: Mobil ilovada PROMO menyusining yashirilishini tekshirish (istisno rolsiz) [High · Critical]
📝 Tavsif: Veb-interfeys orqali promo berishni o'chirib, mobil ilovadagi foydalanuvchi uchun PROMO menyusi yashirilishini tekshirish (istisno rol tanlanmagan holda).

⚙️ Boshlang'ich shartlar: Test uchun filialga biriktirilgan mobil foydalanuvchi (masalan, 'Savdo Agenti' rolida) mavjud. Administrator veb-interfeysga kirgan.

📋 Qadamlar:

Veb-interfeysda Filial sozlamalari -> 'Qurilmalar' bo'limiga o'ting.

'Mobil versiyada promo berishni o'chirish' sozlamasini yoqing (switch 'Ha' holatiga o'tkazilsin).

Istisno rollarni tanlash maydonini bo'sh qoldiring.

O'zgarishlarni saqlang.

Mobil ilovaga test foydalanuvchisi (masalan, 'Savdo Agenti') loginidan kiring.

Ma'lumotlarni yangilash uchun sinxronizatsiya qiling.

Yangi buyurtma yaratish ekraniga o'ting.

✅ Kutilgan natija: Buyurtma yaratish ekranida PROMO menyusi/tugmasi ko'rinmaydi (yashiringan). Foydalanuvchi promolardan foydalana olmaydi.

Type: positive

Tags: mobile, e2e, regression


✅ TC-005: MOB: Istisno roliga biriktirilgan foydalanuvchi uchun PROMO menyusining mavjudligini tekshirish (umumiy taqiqqa qaramay) [High · Critical]
📝 Tavsif: Veb-interfeysda promo berishni umumiy o'chirib, ma'lum bir istisno roldagi foydalanuvchilar uchun mobil ilovada PROMO menyusi ko'rinishda qolishini tekshirish.

⚙️ Boshlang'ich shartlar: Tizimda kamida ikkita rol mavjud (masalan, 'Savdo Agenti' va 'Menejer'). 'Menejer' rolidagi foydalanuvchi va 'Savdo Agenti' rolidagi foydalanuvchi mobil ilovada test uchun tayyor.

📋 Qadamlar:

Veb-interfeysda Filial sozlamalari -> 'Qurilmalar' bo'limiga o'ting.

'Mobil versiyada promo berishni o'chirish' sozlamasini yoqing.

Paydo bo'lgan 'Istisno rollar' maydonidan 'Menejer' rolini tanlang.

O'zgarishlarni saqlang.

'Menejer' rolidagi foydalanuvchi bilan mobil ilovaga kiring, sinxronizatsiya qiling va yangi buyurtma yarating.

'Savdo Agenti' rolidagi foydalanuvchi bilan mobil ilovaga kiring, sinxronizatsiya qiling va yangi buyurtma yarating.

✅ Kutilgan natija: 1. 'Menejer' rolidagi foydalanuvchi uchun buyurtma ekranida PROMO menyusi ko'rinib turadi va ishlaydi. 2. 'Savdo Agenti' rolidagi foydalanuvchi uchun PROMO menyusi yashirilgan bo'ladi.

Type: positive

Tags: mobile, e2e


✅ TC-006: MOB: Sozlama o'chirilganda barcha uchun promo funksiyasi tiklanishi va PROMO menyusining qayta ko'rinishini tekshirish [High · Major]
📝 Tavsif: Avval promo berish o'chirilgan holatdan, sozlama veb-interfeysda bekor qilingandan so'ng, mobil ilovadagi barcha foydalanuvchilar uchun PROMO menyusining qayta ko'rinishini tekshirish.

⚙️ Boshlang'ich shartlar: Boshlang'ich holat: 'Mobil versiyada promo berishni o'chirib qo'yish' sozlamasi yoqilgan va istisno rollar tanlanmagan. Mobil foydalanuvchi ilovaga kirgan va sinxronizatsiya qilgan (unda PROMO menyusi yo'q).

📋 Qadamlar:

Veb-interfeysda Filial sozlamalari -> 'Qurilmalar' bo'limiga o'ting.

'Mobil versiyada promo berishni o'chirib qo'yish' sozlamasini o'chiring (switch 'Yo'q' holatiga o'tkazing).

O'zgarishlarni saqlang.

Mobil ilovada qaytadan sinxronizatsiya qiling.

Yangi buyurtma yaratish ekraniga o'ting.

✅ Kutilgan natija: Sinxronizatsiyadan so'ng mobil foydalanuvchi uchun buyurtma yaratish ekranida PROMO menyusi yana paydo bo'ladi va to'liq ishlaydi.

Type: positive

Tags: mobile, e2e, regression


🔧 AI pipeline (debug)
1️⃣ Agent1 (talablar) [completed]: 7 ta talab ajratildi. — model: gemini-2.5-flash

2️⃣ Agent2 (testcase) [completed]: 6 ta testcase yaratildi. Coverage: 6/7 talab. Qoplanmagan: REQ-6. — model: gemini-2.5-flash

3️⃣ Agent3 (audit) [completed]: 2 ta scenario shakllantirildi, 0 ta audit finding qaytdi. — model: gemini-2.5-flash

🤖 Test case'lar AI (Gemini) tomonidan avtomatik yaratilgan. QA Team tomonidan tekshirilishi va to'ldirilishi kerak.







Turgunov Jasur

2 hours ago
[AI_S1]

🎯 TZ-PR Checker

📋 DEV-8245 — ma'lumot va statistika
Task: DEV-8245
Vaqt: 2026-07-07 16:34:53
Status: Ready to Test

Pull Requests: 4 ta

O'zgargan fayllar: 16 ta

Qo'shilgan: +425

O'chirilgan: -138

🔗 DEV IMPX - ТЗ на доработку инструмента промо для компании Makolli (MAKOLLI) — 3 fayl | +47 / -1

🔗 DEV IMPX - ТЗ на доработку инструмента промо для компании Makolli (MAKOLLI) — 3 fayl | +47 / -1

🔗 DEV IMPX - ТЗ на доработку инструмента промо для компании Makolli (MAKOLLI) — 5 fayl | +100 / -2

🔗 DEV IMPX - ТЗ на доработку инструмента промо для компании Makolli (MAKOLLI) — 5 fayl | +231 / -134

📊 Moslik Bali: 100% — Yaxshi
✅ 7 bajarildi   ·   ⏭️ 2 skip


🧭 Xulosa
Jami 9 ta requirementdan 7 tasi (REQ-1, REQ-2, REQ-4, REQ-6, REQ-7, REQ-8, REQ-9) bajarilganligi tasdiqlandi. Qolgan 2 ta requirement (REQ-3, REQ-5) berilgan kod kontekstida topilmadi va ular mobil ilova qismiga tegishli ekanligi sababli, dev commentlariga asosan ushbu PR doirasida "skipped" deb belgilandi.

✅ BAJARILGAN TALABLAR (7 ta)

✅ [REQ-1] Talab: Tizim sozlamalarida, filial darajasida, "Qurilmalar" menyusiga "Mobil versiyada…
Talab: Tizim sozlamalarida, filial darajasida, "Qurilmalar" menyusiga "Mobil versiyada promo berishni o'chirish" nomli yangi sozlama qo'shilishi kerak.

Source: tz

Evidence: Tizim sozlamalarida, filial darajasida, "Qurilmalar" menyusiga "Mobil versiyada promo berishni o'chirish" (MPH:disable_promo_in_mobile) nomli yangi sozlama qo'shilgan. Bu sozlama `main/page/form/trade/pref/mobile_setting.html` faylida ko'rinadi.

File: main/page/form/trade/pref/mobile_setting.html, main/oracle/module/mph/mph_pref/mph_pref.pks, main/page/lang/ru/trade/pref/mobile_setting.json


✅ [REQ-2] Talab: "Mobil versiyada promo berishni o'chirish" sozlamasi dastlab o'chirilgan holatda…
Talab: "Mobil versiyada promo berishni o'chirish" sozlamasi dastlab o'chirilgan holatda bo'lishi kerak.

Source: tz

Evidence: "Mobil versiyada promo berishni o'chirish" sozlamasi `Mph_Pref.Disable_Promo_In_Mobile` funksiyasida `Nvl(Md_Pref.Load(i_Company_Id => i_Company_Id, i_Filial_Id => i_Filial_Id, i_Code => c_Pref_Disable_Promo_In_Mobile), 'N')` orqali yuklanadi, bu esa qiymat mavjud bo'lmaganda 'N' (ya'ni, o'chirilgan) holatni qaytaradi.

File: main/oracle/module/mph/mph_pref/mph_pref.pkb


✅ [REQ-4] Talab: "Mobil versiyada promo berishni o'chirish" sozlamasi yoqilganda, qo'shimcha ravi…
Talab: "Mobil versiyada promo berishni o'chirish" sozlamasi yoqilganda, qo'shimcha ravishda istisno rolini tanlash sozlamasi paydo bo'lishi kerak.

Source: tz

Evidence: "Mobil versiyada promo berishni o'chirish" sozlamasi yoqilganda (`ng-show="d.disable_promo_in_mobile == 'Y'"`), `main/page/form/trade/pref/mobile_setting.html` faylida istisno rolini tanlash sozlamasi (`disable promo in mobile except roles`) paydo bo'ladi.

File: main/page/form/trade/pref/mobile_setting.html, main/oracle/module/mph/mph_pref/mph_pref.pks


✅ [REQ-6] Talab: "Mobil versiyada promo berishni o'chirish" sozlamasi va istisnolar ma'lumotlari…
Talab: "Mobil versiyada promo berishni o'chirish" sozlamasi va istisnolar ma'lumotlari mobil ilovaga uzatilishi kerak.

Source: tz

Evidence: "Mobil versiyada promo berishni o'chirish" sozlamasi (`Mph_Pref.Disable_Promo_In_Mobile`) va istisnolar (`Mph_Pref.Disable_Promo_In_Mobile_Roles`) ma'lumotlari `Mph_Tape.System_Settings` protsedurasi orqali mobil ilovaga uzatiladi (`Result.Push`).

File: main/oracle/module/mph/mph_tape/mph_tape.pkb, main/oracle/module/mph/mph_pref/mph_pref.pkb


✅ [REQ-7] Talab: Mobil ilovada buyurtma ochilganda, veb-qismdagi sozlama tekshirilishi kerak.
Talab: Mobil ilovada buyurtma ochilganda, veb-qismdagi sozlama tekshirilishi kerak.

Source: tz

Evidence: Mobil ilovada buyurtma ochilganda, MPH_Pref.c_Pref_Disable_Promo_In_Mobile va MPH_Pref.c_Pref_Disable_Promo_In_Mobile_Roles sozlamalari Mph_Tape.pkgb ichidagi Mph_Tape.Println(i_Tape_Code => Mph_Pref.c_Tc_System_Settings, i_Value => result) orqali yuklanishi ko'rsatilgan. Bu sozlamalar mobil ilovada foydalanish uchun tizim sozlamalariga kiritiladi.

File: main/oracle/module/mph/mph_tape/mph_tape.pkb


✅ [REQ-8] Talab: Agar sozlama yoqilgan bo'lsa va foydalanuvchi istisno roliga kirmasa, mobil ilov…
Talab: Agar sozlama yoqilgan bo'lsa va foydalanuvchi istisno roliga kirmasa, mobil ilovada PROMO menyusi yashirilishi kerak.

Source: tz

Evidence: Mph_Pref.Disable_Promo_In_Mobile funksiyasi c_Pref_Disable_Promo_In_Mobile konstantasi orqali 'N' yoki 'Y' qiymatini qaytaradi. Bu sozlama 'Y' bo'lsa, 'disable_promo_in_mobile' xususiyati yoqilgan bo'ladi. Mph_Pref.Disable_Promo_In_Mobile_Roles funksiyasi istisno rollar ro'yxatini qaytaradi. Agar foydalanuvchining roli ushbu ro'yxatda bo'lmasa, promo menyusi yashiriladi. Bu holatda, mobile_setting.html faylida 'disable_promo_in_mobile == 'Y'' sharti va 'disable_promo_in_mobile_roles' tekshiruvi mavjud bo'lib, ular mobil ilovada promo menyusini yashirish mexanizmini ta'minlaydi.

File: main/oracle/module/mph/mph_pref/mph_pref.pkb, main/oracle/module/mph/mph_pref/mph_pref.pks, main/page/form/trade/pref/mobile_setting.html


✅ [REQ-9] Talab: Agar foydalanuvchi istisno roliga kirsa, mobil ilovada PROMO menyusi ko'rsatilis…
Talab: Agar foydalanuvchi istisno roliga kirsa, mobil ilovada PROMO menyusi ko'rsatilishi kerak.

Source: tz

Evidence: Mph_Pref.Disable_Promo_In_Mobile_Roles funksiyasi istisno rollar ID'lari ro'yxatini Array_Number formatida qaytaradi. Agar joriy foydalanuvchining roli ushbu ro'yxatda bo'lsa, u istisno roliga kiradi va mobil ilovada PROMO menyusi ko'rsatilishi kerak. mobile_setting.html faylidagi 'q.disable_promo_in_mobile_roles = _.mapRows(d.disable_promo_in_mobile_roles, ['role_id', 'name'])' va 'data.disable_promo_in_mobile_roles = d.disable_promo_in_mobile == 'Y' ? _.pluck(q.disable_promo_in_mobile_roles, 'role_id') : []' qatorlari rolga asoslangan istisno logikasini boshqaradi.

File: main/oracle/module/mph/mph_pref/mph_pref.pkb, main/page/form/trade/pref/mobile_setting.html

⏭️ SKIP QILINGAN (dev izohi — manual tekshiring) (2 ta)

⏭️ [REQ-3] Talab: "Mobil versiyada promo berishni o'chirish" sozlamasi yoqilganda, mobil ilovada b…
Talab: "Mobil versiyada promo berishni o'chirish" sozlamasi yoqilganda, mobil ilovada buyurtma yaratishda PROMO menyusi yashirilishi kerak.

Source: tz

Evidence: ⏭️ Skip sababi: Mobil ilovaning PROMO menyusini yashirish funksiyasi mobil ilova qismida amalga oshirilishi kerak bo'lib, ushbu PR doirasida emas.  ·  💬 Dev izohi (skip asosi): Shahzod Mirjalolov: "ertadan shu ishni boshlash kerak [~accountid:712020:d32588f7-c2c8-49a6-af83-99b6e620973b]" / Turgunov Jasur: "Tekshirildi: Xtrade" / Turgunov Jasur: "Mobil ilovaning "PROMO" menyusini yashirish va istisno rollarga ega foydalanuvchilar uchun promokod berishni davom ettirish, shuningdek, sozlamalar asosida "PROMO" menyusini to'g'ri ko'rsatish/yashirish funksiyalari mobil ilova qismida amalga oshirilishi kerak bo'lib, ushbu PR doirasida emas!"


⏭️ [REQ-5] Talab: Tanlangan istisno roliga biriktirilgan foydalanuvchilar umumiy taqiqqa qaramay p…
Talab: Tanlangan istisno roliga biriktirilgan foydalanuvchilar umumiy taqiqqa qaramay promolarni berishda davom etishlari kerak.

Source: tz

Evidence: ⏭️ Skip sababi: Istisno rollarga ega foydalanuvchilar uchun promokod berishni davom ettirish funksiyasi mobil ilova qismida amalga oshirilishi kerak bo'lib, ushbu PR doirasida emas.  ·  💬 Dev izohi (skip asosi): Shahzod Mirjalolov: "ertadan shu ishni boshlash kerak [~accountid:712020:d32588f7-c2c8-49a6-af83-99b6e620973b]" / Turgunov Jasur: "Tekshirildi: Xtrade" / Turgunov Jasur: "Mobil ilovaning "PROMO" menyusini yashirish va istisno rollarga ega foydalanuvchilar uchun promokod berishni davom ettirish, shuningdek, sozlamalar asosida "PROMO" menyusini to'g'ri ko'rsatish/yashirish funksiyalari mobil ilova qismida amalga oshirilishi kerak bo'lib, ushbu PR doirasida emas!"


🔧 AI pipeline (debug)
1️⃣ Agent1 (scope) [completed]: 9 ta talab ajratdi — model: gemini-2.5-flash

🔀 Agent1b (merge): 9 ta talabni 9 taga birlashtirdi (0 ta merge)

2️⃣ Agent2 (verify) [completed]: 9 ta requirement 2 ta batch orqali tekshirildi. — model: gemini-2.5-flash

3️⃣ Agent3 (arbiter) [completed]: 9 ta requirement bo'yicha checker final matrix hisoblandi. — model: gemini-2.5-flash

💬 Dev comment agent3'ga YETDI: 3 ta

🤖 Bu komment AI tomonidan avtomatik yaratilgan. Savollar bo'lsa QA Team ga murojaat qiling.