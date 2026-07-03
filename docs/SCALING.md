# Worker'larni gorizontal masshtablash (scaling)

Bu hujjat background worker sonini qanday va qachon oshirish kerakligini tushuntiradi.

---

## Arxitektura: nima uchun bir nechta worker xavfsiz

Job claim qatlami (`utils/database/job_queue_repository.py`, `claim_next_background_job`)
multi-worker uchun tayyor:

- `pg_advisory_xact_lock` barcha worker'larning claim'ini serializatsiya qiladi —
  ikki worker bir vaqtda bitta jobni ololmaydi (TOCTOU yo'q).
- `FOR UPDATE SKIP LOCKED` — navbatdagi job atomik olinadi.
- **Per-company concurrency = 1**: bitta kompaniya uchun bir vaqtda faqat 1 ta
  `running` job bo'ladi (`NOT EXISTS` sharti). Bu adolat (fairness) kafolati:
  bitta kompaniya 50 ta task tashlab, boshqa kompaniyalarni navbatda qoldirolmaydi.
- Har worker unikal nom bilan ishlaydi: `APP_WORKER_NAME` berilmasa
  `worker-<hostname>` (Docker'da hostname = container id, shuning uchun
  `--scale` replikalar avtomatik unikal bo'ladi).

**Muhim cheklov:** per-company concurrency = 1 bo'lgani uchun worker sonini
oshirish faqat **kompaniyalar soni ko'p bo'lganda** foyda beradi. 1 ta kompaniya
uchun 10 ta worker ham 1 ta workerdek ishlaydi.

---

## Sig'im hisobi (capacity math)

Bitta multi-agent run (S1 checker yoki S2 testcase) o'rtacha **3–8 daqiqa** davom
etadi va worker uni ketma-ket (serial) bajaradi:

```
1 worker  ≈  60 daqiqa / 3–8 daqiqa  ≈  7–20 run/soat
          ≈  180–480 run/kun (24/7 rejimda)
```

Misol yuklama: 10 kompaniya × kuniga 50 task × 2 servis (S1 + S2):

```
10 × 50 × 2 = 1000 run/kun
1000 / (180–480) ≈ 2.1–5.6  →  3–4 worker yetarli
```

Qo'shimcha omillar:
- Gemini rate limit (`queue.gemini_min_interval`, default 6s) — kalitlar soni
  kam bo'lsa, worker qo'shish AI darvozasida navbatga aylanadi.
- Ish soatlari: tasklar asosan 8 soatlik ish kunida kelsa, kunlik sig'imni
  3 ga bo'lib hisoblang (`60–160 run/ish-kuni per worker`).

---

## Qanday masshtablash

### Docker Compose (Mac/Linux deploy)

```bash
docker compose up -d --scale worker=3
```

- `worker` servisida `container_name` yo'q va port ochilmagan — replikalar
  to'qnashmaydi.
- Har replika o'z hostname'i (container id) bilan unikal worker nom oladi.
- `.env` da `APP_WORKER_NAME` **bermang** — u barcha replikalarga bir xil
  qiymat berib, monitoring/heartbeat'da nom to'qnashuviga olib keladi.

Doimiy qilish uchun (har `up` da avtomatik N replika):

```yaml
# docker-compose.override.yml
services:
  worker:
    deploy:
      replicas: 3
```

### Windows monolit deploy

Windows'dagi jonli prod monolit rejimda ishlaydi (webhook inline). U yerda
worker scaling qo'llanilmaydi — avval `APP_WEBHOOK_EXECUTION_MODE=queue` ga
o'tkazish va alohida worker jarayonlarini (har biriga unikal
`APP_WORKER_NAME`, masalan `worker-a`, `worker-b`) ishga tushirish kerak.
Bitta mashinada bir nechta `python -m services.worker.main` jarayoni ham
xavfsiz — claim DB darajasida himoyalangan.

---

## PostgreSQL `max_connections` formulasi

Har jarayon (backend + har bir worker) o'z connection pool'iga ega
(`APP_DB_POOL_MAX_SIZE`, default 10). Formula:

```
jarayonlar_soni × APP_DB_POOL_MAX_SIZE ≤ postgres max_connections − zaxira
```

Misol (postgres:16 default `max_connections = 100`, zaxira ≈ 10–20):

| Konfiguratsiya | Hisob | Holat |
|---|---|---|
| backend 1 + worker 1 | 2 × 10 = 20 | OK |
| backend 1 + worker 4 | 5 × 10 = 50 | OK |
| backend 1 + worker 8 | 9 × 10 = 90 | Chegarada — zaxira qolmaydi |

Worker soni ko'p bo'lsa: yo postgres `max_connections` ni oshiring, yo worker
uchun `APP_DB_POOL_MAX_SIZE` ni kichraytiring (worker asosan 1–2 ulanish
ishlatadi, unga 5 ham yetarli).

---

## Monitoring

- Har worker container'ida liveness healthcheck bor: worker loop har ~60s
  `/tmp/qa_worker_heartbeat` faylga touch qiladi; fayl 15 daqiqadan eskirsa
  container `unhealthy` bo'ladi (uzun run paytida heartbeat to'xtab turishi
  normal, shuning uchun chegara 15 daqiqa).
- DB darajasida: `worker_heartbeat` jadvali (`core/watchdog.py`) — qaysi worker
  qachon oxirgi marta "tirik" bo'lganini ko'rsatadi.
- Navbat holati: backend `/health` javobidagi `queue` bo'limi
  (queued/running/done/failed).
