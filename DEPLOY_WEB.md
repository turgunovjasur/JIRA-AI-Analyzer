# Web Deploy

Bu hujjat `Next.js + FastAPI + Worker + PostgreSQL` stackini productionga yaqin shaklda ishga tushirish uchun qisqa yo'riqnoma beradi.

## Architecture

- `frontend`
  - `Next.js`
  - browser uchun asosiy portal
  - auth cookie va BFF (`/api/*`) route'larini boshqaradi

- `backend`
  - `FastAPI`
  - auth, monitoring, settings, checker va admin API'larini beradi
  - webhooklarni `queue` rejimida qabul qilib, DB navbatga yozadi

- `worker`
  - `python -m services.worker.main`
  - `job_queue` dan joblarni claim qiladi
  - checker, testcase va blocked retry oqimlarini bajaradi

- `postgres`
  - primary runtime DB
  - auth, sessions, task processing va job queue source-of-truth

## Local Docker Compose

```bash
docker compose up --build
```

Natija:

- `frontend`: [http://127.0.0.1:3000](http://127.0.0.1:3000)
- `backend`: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- `postgres`: container ichida `5432`

Compose ichida:

- `APP_WEBHOOK_EXECUTION_MODE=queue`
- `worker` alohida servis sifatida ko'tariladi
- `postgres` healthcheck'dan keyin `backend` va `worker` ishga tushadi

## Muhim Env'lar

`.env.example` dan namuna oling:

- umumiy:
  - `APP_USE_BACKEND_API=true`
  - `APP_WEBHOOK_EXECUTION_MODE=inline`
  - `APP_WORKER_POLL_INTERVAL_SECONDS=3`

- compose uchun Postgres:
  - `POSTGRES_DB=jira_ai_analyzer`
  - `POSTGRES_USER=jira_ai_analyzer`
  - `POSTGRES_PASSWORD=change_this_in_prod`

- frontend:
  - `BACKEND_API_BASE_URL=http://backend:8000`
  - `NEXT_PUBLIC_BACKEND_API_BASE_URL=http://backend:8000`

## Local Non-Docker Startup

Local dev uchun:

```bash
./start.sh
```

Agar `.env` ichida `APP_WEBHOOK_EXECUTION_MODE=queue` bo'lsa, `start.sh` backend bilan birga worker'ni ham avtomatik ko'taradi.

## Production Checklist

1. `.env.example` dan `.env` yarating va **barcha `CHANGE_THIS_*` qiymatlarni** almashtiring
2. `APP_STRICT_MODE=true` va kuchli `APP_CREDENTIALS_MASTER_KEY` o'rnating
3. `ALLOWED_ORIGINS` ni production domeniga o'rnating
4. `docker compose up --build -d` bilan servislarni ko'taring
5. `curl https://yourdomain.com/health` → `{"status":"healthy"}` kelishi kerak (HTTP 200)
6. Nginx reverse proxy: `deploy/nginx.conf` ni moslashtiring
   - `example.com` ni o'z domeningizga almashtiring
   - `certbot --nginx -d yourdomain.com` bilan TLS qo'shing

## DB Backup

```bash
# Qo'lda backup
make backup

# Restore
make restore FILE=backups/jira_ai_20260611_120000.sql.gz

# Kunlik avtomatik backup (crontab -e):
# 0 2 * * * cd /opt/jira-ai && bash scripts/backup_db.sh >> logs/backup.log 2>&1
```

Backuplar `./backups/` papkasida saqlanadi, 7 kundan eski fayllar avtomatik o'chiriladi.
6. SSL, backup va log rotation qo'shing
