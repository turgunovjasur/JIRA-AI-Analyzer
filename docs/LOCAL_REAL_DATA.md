# Real ma'lumotlar bilan lokal ishlash

2026-10-06 production snapshoti alohida lokal bazaga va data katalogiga tiklandi.
Bu SaaS roadmapning Data Layer Migration va tenant izolyatsiyasi ishlarini
real ma'lumotlar bilan tekshirish uchun lokal muhitdir. `PROGRESS_LOG.md` yangilanmadi.

## Ishga tushirish

Repository katalogida:

```bash
bash ./start.sh
```

- UI: http://127.0.0.1:3000
- Backend: http://127.0.0.1:8000
- Database: `qa_assistant_realdata_20261006` (lokal PostgreSQL).
- Faol `.env` shu bazani tanlaydi. Nusxadagi kompaniya foydalanuvchilarining
  production login/parollari lokal login uchun ham amal qiladi.
- Team Analytics demo rejimisiz real ma'lumotlarni o'qiydi. Default daily/weekly
  soatlar 8/40. Snapshot: 764 task, 11,323 event, 179 interval, 33 ijrochi,
  4 kompaniya va 5 foydalanuvchi.

Snapshot server bilan avtomatik yangilanmaydi. `START_WORKER=0` bo'lgani uchun
analytics sync ham avtomatik bajarilmaydi; kod yangilanishi bazadagi eski,
to'liq import qilinmagan Jira tasklarini o'zidan-o'zi tiklamaydi.
Lokal analytics bazasini Jira'dan yangilash uchun faqat shu kompaniyaning
analytics sync'ini alohida ishga tushiring:

```bash
./.venv/bin/python scripts/team_analytics_import.py --company-id <company-id>
```

Bu buyruq Jira'dan faqat o'qiydi va faol `.env` tanlagan lokal bazadagi
analytics ma'lumotlarini yangilaydi. Project, sprint va custom field'lar
kompaniya sozlamalari hamda Jira metadata'sidan olinadi. UI'dagi `Yangilash`
tugmasi bazadan qayta o'qiydi; Jira importini ishga tushirmaydi. Eski yopilgan
sprintlarni ham to'liq qayta import qilish kerak bo'lsa, shu buyruqqa
`--initial` qo'shiladi. Umumiy worker'ni yoqish talab qilinmaydi.

## Nusxa va izolyatsiya

- DB backup: `backups/production-copy-20261006/production.dump`.
- App data backup: `backups/production-copy-20261006/app-data.tar.gz`.
- Faol app data: `data/production-copy-20261006` (report/cache/vector kataloglari shu yerda).
- Mavjud `jira_ai_analyzer` bazasi va oldingi lokal data kataloglari saqlangan.
- Oldingi `.env`: `backups/production-copy-20261006/env.before-copy`.
- Dump, app data, credentiallar va `.env` Git/Docker contextiga kirmaydi.
  Backup katalogi 0700, `.env` va uning zaxirasi 0600 huquqda saqlanadi.
- Nusxadagi encrypted sozlamalar uchun kerakli encryption key lokal `.env`da
  moslangan; secret qiymatlari hujjat yoki logga yozilmaydi.

## Avtomatik tashqi amallar

Lokal `.env`dagi `APP_WEBHOOK_EXECUTION_MODE=queue` va `START_WORKER=0` sababli
webhook ishini avtomatik bajaruvchi worker ishga tushmaydi. `start.sh` endi
explicit `START_WORKER=0` ni queue rejimida ham hurmat qiladi. Watchdog,
retention cleanup, SMTP va Telegram bildirishnomalari lokalda o'chirilgan.

Jira sync, task tahlili yoki tashqi servisga yozuvchi amallarni bajarish uchun
ular alohida topshiriq doirasida yoqilishi kerak. UI va read-only analytics
uchun worker talab qilinmaydi.

Avtomatik testlar uchun alohida test DB ishlatilsin; ushbu real nusxa UI va
analytics tahlili uchun saqlansin. Testlar faqat foydalanuvchi so'raganda yuritiladi.
