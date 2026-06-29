# QA-Assistant

AI-powered bug root cause analysis tizimi. Production buglarning asosiy sababini semantic search va Gemini AI yordamida topadi.

**Author:** Jasur Turgunov  
**Company:** Green White Solutions (SmartUpX)  
**Version:** 2.0.0

---

## ✨ Asosiy Imkoniyatlar

### 🔍 Smart Semantic Search
- **Multilingual Support**: O'zbek, Rus, Ingliz tillarida ishlaydi
- **Vector Database**: ChromaDB asosida tez qidiruv
- **Weighted Chunking**: Taskni semantic qismlarga bo'lib, har biriga vazn beradi
- **Root Cause Detection**: Bug sababini avtomatik aniqlaydi
- **Solution Extraction**: O'xshash tasklardan yechim topadi

### 🤖 AI Tahlil
- **Gemini 2.5 Flash**: So'nggi AI model
- **Context-Aware**: Task history, developer, sprint ma'lumotlarini hisobga oladi
- **Konkret Yechimlar**: Amaliy tavsiyalar beradi
- **Preventive Measures**: Kelajakda xatolarni oldini olish yo'llari

### 📈 Sprint Statistika
- **Developer Performance**: Har bir developer bo'yicha batafsil ma'lumot
- **Bug Trends**: Bug pattern'lar tahlili
- **Sprint Analysis**: Sprint samaradorligi
- **Return Analysis**: QA dan qaytgan tasklar
- **Timeline Tracking**: Task lifecycle kuzatuvi

### 🔗 GitHub Integratsiya
- **TZ-PR Checker**: Task TZ va kod mosligini tekshiradi
- **PR Analysis**: Pull Request tahlili
- **Code Review**: Kod sifati tekshiruvi
- **Auto Search**: JIRA'da link bo'lmasa GitHub'dan qidiradi

---

## 🚀 O'rnatish

### 1. Clone
```bash
git clone https://github.com/your-org/qa-assistant.git
cd qa-assistant
```

### 2. Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 3. Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Setup

`.env` fayl yarating:
```bash
# JIRA
JIRA_SERVER=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-token

# GitHub
GITHUB_TOKEN=your-github-token
GITHUB_ORG=your-organization

# Gemini AI
GOOGLE_API_KEY=your-google-api-key

# Paths
DATA_DIR=./data
EXCEL_DIR=./data/excel_reports
VECTOR_DB_PATH=./data/vector_db

# Search
MIN_SIMILARITY=0.70
TOP_K_RESULTS=20
FINAL_TOP_N=5
```

### 5. Model Download
```bash
python 1_setup_embedding.py
```

### 6. Sprint Data Yuklash

Excel reportlarni `data/excel_reports/` ga joylashtiring:
```bash
python 2_load_sprints.py
```

---

## 💻 Ishga Tushirish
```bash
./start.sh
```

Browser: `http://localhost:3000`

Izoh:
- `start.sh` endi default holatda `Next.js` frontend + `FastAPI` backendni birga ko'taradi.
- Customer, company admin va super admin oqimlari yangi web portal ichida ishlaydi.
- `.env` ichida `APP_WEBHOOK_EXECUTION_MODE=queue` bo'lsa, `start.sh` worker'ni ham avtomatik ko'taradi.
- Runtime faqat PostgreSQL bilan ishlaydi; `APP_POSTGRES_DSN` to'g'ri sozlangan bo'lishi kerak.
- `.env` ichida Windows pathlar qolgan bo'lsa, `start.sh` local session uchun ularni repo ichidagi `data/` va `models/` papkalariga almashtirib beradi.
- Yangi build'larda local backend avtomatik ko'tarishga urinadi; agar bu ishlamasa `logs/backend_api.log` ni tekshiring.
- Qo'lda ishga tushirish kerak bo'lsa:
```bash
python -m uvicorn services.webhook.jira_webhook_handler:app --host 0.0.0.0 --port 8000
python -m services.worker.main   # queue rejimi uchun
cd frontend && npm run dev
```

## 🌐 Web Portal

Customer, company admin va super admin oqimlari endi yagona `Next.js` portal ichida ishlaydi:

```bash
./start.sh
```

Asosiy fayllar:
- [frontend/README.md](/Users/mac/Documents/projects/QA-Assistant/frontend/README.md)
- [DEPLOY_WEB.md](/Users/mac/Documents/projects/QA-Assistant/DEPLOY_WEB.md)
- [ROADMAP_SAAS.md](/Users/mac/Documents/projects/QA-Assistant/ROADMAP_SAAS.md)
- [PERMISSION_MATRIX.md](/Users/mac/Documents/projects/QA-Assistant/PERMISSION_MATRIX.md)
- [PROGRESS_LOG.md](/Users/mac/Documents/projects/QA-Assistant/PROGRESS_LOG.md)

Hozirgi bosqich:
- backend-managed auth session tayyor
- `Monitoring`, `TZ-PR Checker`, `Test Case Generator`, `Settings`, `Team`, `Super Admin` sahifalari `Next.js`da real backend flow bilan ishlaydi
- `Streamlit` runtime va legacy UI qatlamlari kodbasedan chiqarildi
- Docker/compose deploy packaging qo'shildi
- worker/queue boundary va alohida worker runtime qo'shildi
- qolgan asosiy ishlar endi infra/ops bosqichida: prod deploy, billing/security polish

---

## 📁 Struktura
```
qa-assistant/
├── frontend/               # Next.js web portal
├── services/               # FastAPI API, webhook va domain services
├── utils/                  # Auth, database, helper qatlamlari
├── docker-compose.yml
├── Dockerfile.backend
├── start.sh
├── requirements.txt
├── .env
└── data/
    ├── excel_reports/
    ├── vector_db/
    └── models/
```

---

## 🎯 Funksiyalar

### Bug Analyzer

1. Bug description kiriting
2. Tizim VectorDB'dan o'xshash tasklar qidiradi
3. Gemini AI tahlil qiladi
4. Root cause va yechim ko'rsatadi

### TZ-PR Checker

1. Task key kiriting (DEV-1234)
2. JIRA'dan TZ olinadi
3. GitHub'dan PR topiladi
4. AI TZ-kod mosligini tekshiradi
5. Batafsil tahlil beradi

---

## 🔧 Sozlash

### Search Parameters

`.env`:
```bash
MIN_SIMILARITY=0.70    # Threshold
TOP_K_RESULTS=20       # Candidates
FINAL_TOP_N=5          # Final results
```

## 🧪 Testing
```bash
pytest
cd frontend && npm run typecheck && npm run build
```

**Jasur Turgunov**  
Automation QA Engineer  
Green White Solutions (SmartUp)

📧 tjasur224@gmail.com

---

## 📝 License

Private - Turgunon Jasur

---

## 🙏 Technologies

- **Claude AI** - Development assistance
- **Gemini AI** - Bug analysis
- **Sentence Transformers** - Embeddings
- **ChromaDB** - Vector database
- **Next.js** - Web frontend
- **FastAPI** - Backend API
- **PostgreSQL** - Primary runtime database
