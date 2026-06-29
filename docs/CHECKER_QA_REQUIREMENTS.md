# Checker QA Requirements

Bu hujjat `TZ-PR Checker` uchun asosiy product requirement hisoblanadi.

Execution plan:
- [docs/CHECKER_QA_EXECUTION_PLAN.md](/Users/mac/Documents/projects/QA-Assistant/docs/CHECKER_QA_EXECUTION_PLAN.md)

Muhim qoida:
- Checker bo'yicha keyingi UI, UX, backend contract va promptga oid qarorlar avvalo shu hujjatdagi `QA nuqtayi nazari`ga mos kelishi kerak.
- Agar yangi taklif chiroyli ko'rinsa ham, lekin QA uchun qaror chiqarishni osonlashtirmasa, u checker uchun ustuvor yechim emas.

## 1. Asosiy user story

Men QA sifatida:
- kompaniyam JIRA'sidagi taskni tekshirmoqchiman
- checker orqali taskni `Passed` qilamanmi yoki `Return` qilamanmi, shuni tez va ishonchli hal qilmoqchiman
- xulosamni devga isbot bilan ayta olishim kerak

Checker menga AI demo emas, `qaror chiqaradigan ishchi instrument` bo'lishi kerak.

## 2. Checker QA uchun qaysi savollarga javob berishi shart

Checker har bir task bo'yicha quyidagi savollarga aniq javob berishi kerak:

1. Bu taskni `Passed` qilamanmi yoki `Return` qilamanmi?
2. Nima `bajarilgan`, nima `qisman`, nima `bajarilmagan`?
3. Shu xulosa nimaga asoslangan:
   - `TZ`
   - `comment`
   - `PR`
   - `Figma`
4. Dev bilan gaplashganda qo'limda isbot bormi?

## 3. QA uchun checkerda majburiy ko'rinishi kerak bo'lgan ma'lumotlar

### 3.1 Birinchi ekranda

QA birinchi qarashda quyidagilarni ko'rishi kerak:

- `Moslik bali`
- `Verdict`
- `Return qilish kerakmi yo'qmi`
- qisqa `Xulosa`
- `Kritik muammo bormi yo'qmi`

### 3.2 Task identity

Checker ichida task kimga tegishli ekanini yashirmaslik kerak.

Majburiy maydonlar:
- `Task key`
- `Summary`
- `Assignee`
- `Issue type`
- `Priority`
- `JIRA status`
- `Reporter`

### 3.3 Sectionlar

Checker section nomlari Gemini formatiga va settingsga 1:1 mos bo'lishi kerak.

Majburiy sectionlar:
- `Bajarilgan talablar`
- `Qisman bajarilgan`
- `Bajarilmagan talablar`
- `Potensial muammolar`
- `Figma dizayn mosligi`

Qoida:
- Settingda qanday nom ko'rinsa, checker UI'da ham o'sha nom ko'rinishi kerak.
- Gemini promptda qanday section nomi talab qilinsa, backend structured result va UI ham o'sha section nomiga tayansin.

## 4. QA uchun evidence talabi

Checker har bir xulosa uchun `evidence` ko'rsatishi kerak.

QA uchun evidence quyidagi manbalardan biri yoki bir nechtasiga bog'langan bo'lishi kerak:
- `TZ`
- `Comment`
- `PR`
- `Kod fayli`
- `Figma`

QA quyidagini ko'ra olishi kerak:
- qaysi talabdan olingan
- qaysi commentdan olingan
- qaysi PR/fayl bilan bog'liq
- Figma bilan qayeri mos yoki mos emas

## 5. Figma bo'yicha QA kutadigan narsa

Figma checker uchun ikkinchi darajali emas.

Checker:
- Figma bor bo'lsa `mos / qisman mos / mos emas` degan signal berishi kerak
- Figma yo'q bo'lsa halol aytishi kerak:
  - `Figma bo'yicha ishonchli xulosa yo'q`

QA ikkita qatlamni ko'rishni xohlaydi:
- `Figma evidence`
- `Gemini Figma verdict`

## 6. Dev bilan ishlash uchun checker nimani berishi kerak

Checker QA'ga devga qaytarish uchun tayyor argument berishi kerak.

Majburiy savollar:
- qaysi joyi bajarilmagan?
- nima yetishmayapti?
- qaysi edge case ushlanmagan?
- qaysi field, text yoki behavior mos emas?

Checker `return` qaroriga foydali bo'lishi kerak, faqat `score` ko'rsatish bilan cheklanmasligi kerak.

## 7. Commentlar bo'yicha talab

QA uchun commentlar juda muhim.

Checker quyidagilarni tushunishi kerak:
- keyingi commentlarda talab o'zgarganmi
- dev `keyin qilamiz` deganmi
- zid comment bormi
- checker scope'ni to'g'ri olganmi

Shu sabab `comment_analysis` va `dev_objections` checker experience ichida ikkinchi darajaga tushib qolmasligi kerak.

## 8. PR bo'yicha talab

QA PR ko'rmasdan qaror chiqarmasligi kerak.

Checker ichida majburiy:
- qaysi PR
- mergedmi
- qaysi fayllar o'zgargan
- kerak bo'lsa patch preview

## 9. Checker QA'ga keyingi actionni aytishi kerak

Checker faqat tahlil emas, action recommendation ham berishi kerak.

Kamida quyidagi action holatlaridan biri aniq bo'lishi kerak:
- `Passed qilish mumkin`
- `Manual review kerak`
- `Return qilish kerak`
- `Figma access yo'q, dizayn bo'yicha yakuniy qaror chiqarmang`

## 10. Raw AI'ning roli

`Raw AI` checkerning asosiy qismi emas.

QA uchun ustuvor tartib:
1. `Structured result`
2. `Evidence`
3. `Action recommendation`
4. `Raw AI` faqat debug uchun

## 11. Ideal checker workflow

Yaxshi checker quyidagi vaqt ichida natija berishi kerak:

- 10 soniyada umumiy qaror
- 30 soniyada sabablar
- 1 daqiqada devga aniq feedback yozish imkoniyati

## 12. Acceptance criteria

Checker shu hujjatga mos deyish uchun quyidagilar bajarilgan bo'lishi kerak:

1. QA birinchi fold'da `pass/return` qaroriga yaqinlashsin.
2. Section nomlari settings, Gemini format va UI o'rtasida bir xil bo'lsin.
3. `Bajarilgan / qisman / bajarilmagan / muammolar / figma` bo'yicha alohida ko'rinish bo'lsin.
4. Har bir muhim xulosa uchun evidence ko'rinib tursin.
5. Figma bo'lsa verdict, yo'q bo'lsa halol cheklov ko'rsatilishi kerak.
6. PR va fayl darajasiga tushib ko'rish imkoniyati bo'lsin.
7. Comment o'zgarishlari va objectionlar checker qaroriga ta'sir qiladigan darajada ko'rinsin.
8. `Raw AI` checkerning asosiy navigatsiyasini bosib ketmasin.

## 13. Amaliy qoida

Checker bo'yicha keyingi har qanday ishda savol shu bo'ladi:

`Bu o'zgarish QA'ga tezroq, ishonchliroq va isbotliroq qaror chiqarishga yordam beradimi?`

Agar javob `ha` bo'lsa ustuvor.
Agar javob `yo'q` bo'lsa, u checker uchun asosiy requirement emas.
