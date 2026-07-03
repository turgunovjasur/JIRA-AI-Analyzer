# Windows Server Deploy Qo'llanmasi

QA-Assistant'ni Windows local serverda ishga tushirish bo'yicha to'liq yo'riqnoma.

Arxitektura: **FastAPI backend (port 8000) + Next.js frontend (port 3000) + PostgreSQL**.
`APP_WEBHOOK_EXECUTION_MODE=queue` bo'lsa alohida **worker** jarayoni ham ishlaydi.

---

## 0. Boshlashdan avval — MUHIM

- **`main` branch eng so'nggi kod ekaniga ishonch hosil qiling.** Deploy `main`dan clone
  qilinadi — yangi tuzatishlar boshqa branchda qolib ketmasin.
- Serverda **eski monolit versiya** ishlab turgan bo'lsa (masalan, `jira-ai.greenwhite.uz`),
  u ham 8000-portni band qilgan bo'lishi mumkin. Yechim: yo eski servisni to'xtating,
  yo `start.bat` boshidagi `BACKEND_PORT` / `FRONTEND_PORT` ni boshqa portlarga o'zgartiring.
- Eski monolitdan yangi versiyaga o'tishda **JIRA webhook URL o'zgaradi**
  (endi company-specific: `/webhook/jira/{company_code}` + secret header).

---

## 1. Talablar (bir marta o'rnatiladi)

| Dastur | Versiya | Yuklab olish |
|---|---|---|
| Git | oxirgi | https://git-scm.com/download/win |
| Python | 3.11+ (3.12 tavsiya) | https://www.python.org/downloads/ — **"Add Python to PATH" ni belgilang!** |
| Node.js | 20+ LTS | https://nodejs.org/ |
| PostgreSQL | 15+ (16 tavsiya) | https://www.postgresql.org/download/windows/ |

PostgreSQL o'rnatishda:
- `postgres` superuser paroli so'raladi — **yozib qo'ying**.
- Port default `5432` qoldiring.
- O'rnatib bo'lgach, `C:\Program Files\PostgreSQL\16\bin` ni Windows **PATH** ga qo'shing
  (backup uchun `pg_dump` kerak bo'ladi).

---

## 2. Loyihani clone qilish

CMD oching va:

```cmd
cd C:\
git clone https://github.com/<ORG>/QA-Assistant.git
cd QA-Assistant
```

> Private repo bo'lsa GitHub login/token so'raydi — Personal Access Token ishlating.

---

## 3. PostgreSQL da baza yaratish

CMD da (parol so'raganda `postgres` user parolini kiriting):

```cmd
psql -U postgres -c "CREATE DATABASE jira_ai_analyzer;"
```

> Jadvallarni qo'lda yaratish SHART EMAS — backend birinchi ishga tushganda
> migratsiyalar (`database/postgresql/*.sql`) avtomatik qo'llanadi.

---

## 4. Setup (bir marta)

Loyiha papkasida:

```cmd
setup.bat
```

Bu skript:
1. Python va Node.js borligini tekshiradi
2. `.venv` yaratadi va Python paketlarni o'rnatadi
3. Frontend paketlarni o'rnatadi va **production build** qiladi
4. `data/`, `logs/`, `backups/` papkalarini yaratadi
5. `.env.example` dan `.env` yaratadi (agar yo'q bo'lsa)

---

## 5. .env faylini to'ldirish

`.env` ni Notepad da oching va quyidagi **majburiy** qiymatlarni to'ldiring:

| O'zgaruvchi | Qiymat |
|---|---|
| `SUPER_ADMIN_USERNAME` / `SUPER_ADMIN_PASSWORD` | Super-admin login (kuchli parol!) |
| `APP_CREDENTIALS_MASTER_KEY` | Uzun random secret (pastdagi buyruq bilan yarating) |
| `APP_POSTGRES_DSN` | `postgresql://postgres:SIZNING_PAROL@localhost:5432/jira_ai_analyzer` |
| `GOOGLE_API_KEY` | Gemini API kaliti (global fallback) |
| `JIRA_SERVER` / `JIRA_EMAIL` / `JIRA_API_TOKEN` | Global JIRA fallback kreditlari |
| `GITHUB_TOKEN` / `GITHUB_ORG` | GitHub PR o'qish uchun |
| `APP_STRICT_MODE` | `true` (production da majburiy) |
| `APP_WEBHOOK_REQUIRE_SECRET` | `true` |
| `ALLOWED_ORIGINS` | Frontend manzili: reverse proxy bilan `https://qa.kompaniya.uz`, LAN rejimida `http://SERVER_IP:3000` |
| `APP_BASE_URL` | Xuddi shu manzil (parol tiklash linki uchun) |

Ixtiyoriy:

| O'zgaruvchi | Qiymat |
|---|---|
| `APP_BIND_HOST` | Default `127.0.0.1` (faqat localhost — xavfsiz). LAN kirish uchun `0.0.0.0` — lekin FAQAT firewall ortida (7-bo'lim). |

Master key yaratish (PowerShell da):

```powershell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

> Kompaniya-level JIRA/GitHub/Gemini kalitlari `.env` da EMAS — tizim ishga tushgach
> admin paneldan har kompaniya uchun alohida kiritiladi.

`APP_WEBHOOK_EXECUTION_MODE`:
- `inline` (default) — webhook to'g'ridan-to'g'ri backend jarayonida bajariladi
- `queue` — webhook DB navbatga yoziladi, alohida worker bajaradi (`start.bat`
  worker oynasini avtomatik ochadi). Serverda **`queue` tavsiya qilinadi**.

---

## 6. Ishga tushirish

```cmd
start.bat
```

Skript avval PostgreSQL ulanishini tekshiradi, keyin oynalar ochadi:

| Oyna | Vazifa | Port |
|---|---|---|
| `QA-Backend` | FastAPI (webhook + API) | 8000 |
| `QA-Worker` | Background worker (faqat `queue` rejimida) | — |
| `QA-Frontend` | Next.js UI (production build) | 3000 |

Tekshirish:
- Brauzerda `http://localhost:3000` — login sahifasi ochilishi kerak
- `http://localhost:8000/health` — `{"status":"healthy"}` qaytishi kerak

To'xtatish:

```cmd
stop.bat
```

> Oynalarni yopib qo'ysangiz ham servislar o'chadi — server qayta yoqilganda
> `start.bat` ni qayta ishga tushirish kerak (yoki 11-bo'limdagi avto-start).

---

## 7. Tashqi kirish — TLS reverse proxy (MAJBURIY)

> **OGOHLANTIRISH: 8000 va 3000 portlarni internetga HECH QACHON to'g'ridan-to'g'ri
> ochmang!** Backend va frontend oddiy HTTP'da ishlaydi — `X-Webhook-Secret` header,
> login parollari va session cookie'lar shifrlanmagan (cleartext) holda uzatiladi.
> 8000-port internetga ochilsa, autentifikatsiyasiz `/metrics` va `/settings`
> endpointlari ham hammaga ko'rinadi.

`start.bat` default holda servislarni faqat `127.0.0.1` ga bog'laydi — tashqaridan
umuman kirib bo'lmaydi. Tashqi kirish uchun quyidagi ikki variantdan birini tanlang.

### 7.1. Internet kirish (JIRA Cloud webhook) — TLS reverse proxy orqali

Serverga domen yo'naltirilgan bo'lishi kerak (masalan `qa.kompaniya.uz` → server IP).
Eng oddiy yo'l — **Caddy** (Let's Encrypt sertifikatni avtomatik oladi va yangilaydi):

1. https://caddyserver.com/download dan Windows amd64 binary yuklab oling →
   `C:\caddy\caddy.exe`

2. `C:\caddy\Caddyfile` yarating:

   ```
   qa.kompaniya.uz {
       # JIRA webhook — backend'ga
       handle /webhook/* {
           reverse_proxy 127.0.0.1:8000
       }

       # Qolgan hamma narsa — frontend UI
       handle {
           reverse_proxy 127.0.0.1:3000
       }
   }
   ```

   Backend'ning boshqa endpointlari (`/metrics`, `/settings`, `/manual/*`, ...)
   ataylab proxy qilinmaydi — frontend ularga server ichida `127.0.0.1:8000`
   orqali o'zi kiradi.

3. Ishga tushirish (Administrator CMD):

   ```cmd
   cd C:\caddy
   caddy run
   ```

   Doimiy ishlashi uchun: Task Scheduler'ga *At startup* trigger bilan qo'shing
   yoki [NSSM](https://nssm.cc) bilan Windows Service qiling.

4. Firewall'da faqat **443** (va Let's Encrypt sertifikat olish uchun **80**) ni
   oching — Administrator CMD:

   ```cmd
   netsh advfirewall firewall add rule name="QA-Assistant HTTPS" dir=in action=allow protocol=TCP localport=443
   netsh advfirewall firewall add rule name="QA-Assistant ACME" dir=in action=allow protocol=TCP localport=80
   ```

   **8000 va 3000 uchun firewall qoidasi QO'SHMANG.**

Muqobil variantlar (xuddi shu routing bilan — `/webhook/*` → `127.0.0.1:8000`,
qolgani → `127.0.0.1:3000`):
- **IIS** — *URL Rewrite* + *Application Request Routing (ARR)* modullari bilan
  reverse proxy; sertifikat uchun [win-acme](https://www.win-acme.com).
- **nginx for Windows** — `proxy_pass` bilan; sertifikat yana win-acme orqali.

### 7.2. Faqat lokal tarmoq (LAN) — firewall ortida

Internet kirish kerak bo'lmasa (masalan JIRA Server/DC lokal tarmoqda), `.env` ga:

```
APP_BIND_HOST=0.0.0.0
```

va firewall'da portlarni FAQAT lokal subnet uchun oching (Administrator CMD,
`192.168.1.0/24` ni o'z tarmog'ingizga moslang):

```cmd
netsh advfirewall firewall add rule name="QA-Assistant Backend (LAN)" dir=in action=allow protocol=TCP localport=8000 remoteip=192.168.1.0/24
netsh advfirewall firewall add rule name="QA-Assistant Frontend (LAN)" dir=in action=allow protocol=TCP localport=3000 remoteip=192.168.1.0/24
```

Bu rejimda ham trafik shifrlanmagan — faqat ishonchli lokal tarmoqda ishlating,
router/NAT orqali internetga port-forwarding QILMANG.

---

## 8. JIRA webhook sozlash

1. Tizimga super-admin bilan kirib, kompaniya yarating — kompaniyaga
   `company_code` va avtomatik **webhook_secret** beriladi (admin panelda ko'rinadi).
2. JIRA'da: **Settings → System → WebHooks → Create a WebHook**:
   - **URL**: `https://<DOMEN>/webhook/jira/<company_code>`
     (7.1-bo'limdagi reverse proxy domeni; LAN rejimida —
     `http://<SERVER_IP>:8000/webhook/jira/<company_code>`)
   - **Header**: `X-Webhook-Secret: <admin_paneldan_olingan_secret>`
   - **Events**: Issue → *updated*
3. JIRA Cloud ishlatilsa, server internetdan ko'rinishi shart — bu FAQAT
   7.1-bo'limdagi TLS reverse proxy orqali bo'lishi kerak. Backend portini (8000)
   to'g'ridan-to'g'ri internetga ochish yoki routerda port-forwarding qilish
   TAQIQLANADI — secret va parollar shifrlanmagan holda tarmoqqa chiqadi.

Test: JIRA da biror taskni **Testing** statusga o'tkazing → `QA-Backend` oynasida
webhook logi ko'rinadi → bir necha daqiqada JIRA taskka `[AI_S1]` comment tushadi.

---

## 9. Yangilash (yangi kod chiqqanda)

```cmd
stop.bat
update.bat
start.bat
```

`update.bat`: `git pull origin main` + Python paketlar + frontend rebuild.
DB migratsiyalar backend qayta ishga tushganda avtomatik qo'llanadi.

---

## 10. Backup

Qo'lda:

```cmd
backup_db.bat
```

Backuplar `backups\` papkasiga tushadi, 7 kundan eskilari avtomatik o'chiriladi.

Kunlik avtomatik backup — **Task Scheduler** (`taskschd.msc`):
1. *Create Basic Task* → nom: `QA-Assistant DB Backup`
2. Trigger: *Daily*, 02:00
3. Action: *Start a program* → `C:\QA-Assistant\backup_db.bat`
4. *Start in*: `C:\QA-Assistant`

---

## 11. Server qayta yoqilganda avto-start (ixtiyoriy)

**Task Scheduler** (`taskschd.msc`):
1. *Create Task* → nom: `QA-Assistant`
2. **General**: *Run only when user is logged on* (oynalar ko'rinishi uchun)
3. **Triggers**: *At log on*
4. **Actions**: *Start a program* → `C:\QA-Assistant\start.bat`,
   *Start in*: `C:\QA-Assistant`
5. Serverda auto-logon yoqilgan bo'lsa, restart dan keyin hammasi o'zi ko'tariladi.

---

## 12. Muammolarni bartaraf etish

| Muammo | Yechim |
|---|---|
| `start.bat`: "PostgreSQL ulanmayapti" | `services.msc` da *postgresql-x64-16* servisi ishlayaptimi? `.env` dagi DSN parol/port to'g'rimi? Baza yaratilganmi (3-bo'lim)? |
| Backend oynasida `Address already in use` | 8000-port band (eski monolit?). `stop.bat` yoki `start.bat` dagi portni o'zgartiring |
| Frontend ochilmayapti | `setup.bat` build muvaffaqiyatli o'tganmi? `frontend\.next\standalone\server.js` bormi? |
| JIRA webhook kelmayapti | Reverse proxy ishlayaptimi / firewall (7-bo'lim), URL da `company_code` to'g'rimi, `X-Webhook-Secret` header qo'yilganmi? |
| Webhook 401 qaytaryapti | Secret noto'g'ri yoki kompaniyada webhook_secret sozlanmagan (`APP_WEBHOOK_REQUIRE_SECRET=true`) |
| AI ishlamayapti (WARN_AI_TIMEOUT) | Gemini API kalit kvotasi tugagan yoki noto'g'ri — admin panel / `.env` `GOOGLE_API_KEY` |
| Loglarni ko'rish | `QA-Backend` / `QA-Worker` oynalari + `logs\` papkasi |

Health check: `curl http://localhost:8000/health`
