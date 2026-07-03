# TZ: Mijoz qarzdorligi bo'yicha SMS ogohlantirish

## Umumiy tavsif
Billing modulida mijoz qarzdorligi limitdan oshganda avtomatik SMS
ogohlantirish yuboriladi.

## Talablar
1. Mijoz balansi -50 000 so'mdan past bo'lsa, tizim har kuni soat 09:00 da
   SMS ogohlantirish yuborishi kerak.
2. SMS matni `sms_templates` jadvalidagi shablondan olinishi va mijoz ismi
   bilan to'ldirilishi kerak.
3. Har bir yuborilgan SMS `sms_log` jadvaliga yuborilgan vaqt va status
   bilan yozilishi kerak.
4. Qarzdorlik limitidan oshgan mijozlarga kunlik ogohlantirish xabari
   yuborilishi shart.
