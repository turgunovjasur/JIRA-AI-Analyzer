# QA-Assistant serverida alohida Namoz bot

## Maqsad

Hetzner VPS faqat QA-Assistantni emas, `Namoz vaqti` Telegram botini ham ishlatadi.
Ikki mahsulot bir serverda joylashgan, ammo application va data qatlamlarida bir-biriga
bog'lanmagan.

## Izolyatsiya chegarasi

| Narsa | QA-Assistant | Namoz bot |
|---|---|---|
| Server katalogi | `/opt/qa-assistant` | `/opt/namoz-vaqti` |
| Compose project | `qa-assistant` | `namoz-vaqti` |
| Database | PostgreSQL 16, QA volume | PostgreSQL 17, Namoz volume |
| Docker network | QA project networki | Namoz project networki |
| Host ports | Caddy 80/443 | Hech qanday port publish qilinmaydi |
| Public trafik | `qa-assistant.uz` | Telegram long polling, outbound HTTPS |

Namoz bot QA-Assistantning quyidagi resurslaridan foydalanmaydi:

- QA PostgreSQL bazasi yoki credentiallari;
- Caddy konfiguratsiyasi va domen routing;
- `app_data`, `postgres_data`, `caddy_data` volume'lari;
- frontend, backend yoki worker networki;
- QA `.env` fayli.

## Operator qoidalari

QA-Assistant amallari faqat uning katalogida bajariladi:

```bash
cd /opt/qa-assistant
docker compose ps
```

Namoz bot amallari project nomi bilan faqat o'z katalogida bajariladi:

```bash
cd /opt/namoz-vaqti
docker compose -p namoz-vaqti ps
docker compose -p namoz-vaqti logs bot --tail 100
```

Bir loyihani yangilash yoki restart qilish uchun ikkinchi loyiha Compose faylini
ishlatmang. Ayniqsa server rootida yoki `/opt` ichida project nomisiz
`docker compose down` ishlatmang.

## Resurs himoyasi

Namoz bot Compose konfiguratsiyasida alohida limitlar bor:

- bot: 0.50 CPU va 384 MB RAM;
- Namoz PostgreSQL: 0.50 CPU va 512 MB RAM;
- har container logi: 3 × 10 MB;
- tashqi host portlari: yo'q.

Bu limitlar Namoz servisidagi yuklama QA backend/worker/frontend uchun ajratilgan
resurslarni egallab olmasligini ta'minlaydi.

## QA productioniga tegmaslik

Namoz deploy paytida QA-Assistant konteynerlari rebuild, recreate yoki restart
qilinmaydi. Verifikatsiya uchun faqat read-only amallar ishlatiladi:

```bash
cd /opt/qa-assistant
docker compose ps
curl -fsS https://qa-assistant.uz/health
```

Namoz botning to'liq deploy/update/backup/rollback qo'llanmasi uning reposidagi
`DEPLOYMENT_QA_SERVER.md` faylida saqlanadi.

## Holat

- Namoz bot deploy holati: tayyorlanmoqda.
- QA-Assistant production foydalanuvchilari va ma'lumotlari deploy scope'iga kirmaydi.

