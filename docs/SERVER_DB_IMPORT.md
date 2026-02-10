# 📦 Serverdan DB Import Qilish

Serverda ishlab turgan webhook service ning `processing.db` faylini local kompyuterga olib monitoring qilish uchun qo'llanma.

---

## 🎯 Maqsad

Production server'dagi real task ma'lumotlarini local monitoring dashboard'da ko'rish.

---

## 📋 QADAMLAR

### 1️⃣ **Serverdan DB Faylni Olish**

#### **Option A: SCP (SSH bilan)**

```bash
# Server'dan local'ga copy qilish
scp user@server:/path/to/JIRA-AI-Analyzer/data/processing.db ~/Downloads/

# Misol:
scp root@192.168.1.100:/opt/jira-analyzer/data/processing.db ~/Downloads/
```

#### **Option B: SFTP**

```bash
sftp user@server
sftp> cd /path/to/JIRA-AI-Analyzer/data
sftp> get processing.db ~/Downloads/
sftp> exit
```

#### **Option C: Manual Download (cPanel/FTP)**

1. Server'ga login qiling
2. `/path/to/JIRA-AI-Analyzer/data/processing.db` faylni toping
3. Download qiling → `~/Downloads/processing.db`

---

### 2️⃣ **DB Faylni Import Qilish**

#### **Oddiy Import:**

```bash
cd /path/to/JIRA-AI-Analyzer

python3 utils/import_server_db.py ~/Downloads/processing.db
```

#### **Output:**

```
📦 Server DB Import Tool
============================================================
🔍 Source DB tekshirilmoqda: /Users/mac/Downloads/processing.db
✅ DB valid: 150 ta task
💾 Hozirgi DB backup qilinmoqda...
💾 Backup: data/processing_backup_20260210_123456.db
📥 Import: /Users/mac/Downloads/processing.db → data/processing.db
✅ Import muvaffaqiyatli!

============================================================
📊 STATISTIKA:
🎯   Jami tasklar: 150
  • completed: 80
  • progressing: 5
  • returned: 50
  • error: 15
============================================================
✅ Import tugadi!
ℹ️  Backup: data/processing_backup_20260210_123456.db
```

---

### 3️⃣ **Monitoring Dashboard'ni Ochish**

```bash
streamlit run app.py
```

Sidebar → **📊 Monitoring** → Real server ma'lumotlari ko'rinadi! 🎉

---

## ⚠️ XATOLIKLAR VA YECHIMLAR

### ❌ **Error: "file is not a database"**

**Sabab:** DB fayl transfer paytida buzilgan yoki incomplete.

**Yechim:**

```bash
# Dump/Restore mode (avtomatik)
python3 utils/import_server_db.py ~/Downloads/processing.db

# Tool avtomatik dump/restore qiladi
```

**Qo'lda Dump/Restore:**

```bash
# Server'da (SSH orqali):
sqlite3 /path/to/processing.db .dump > db_dump.sql
scp user@server:/path/to/db_dump.sql ~/Downloads/

# Local'da:
cd /path/to/JIRA-AI-Analyzer
sqlite3 data/processing.db < ~/Downloads/db_dump.sql
```

---

### ❌ **Error: "Integrity check failed"**

**Sabab:** DB corrupted (buzilgan).

**Yechim 1: Dump/Restore (tool avtomatik bajaradi)**

```bash
python3 utils/import_server_db.py ~/Downloads/processing.db
```

**Yechim 2: Server'dan qayta download qiling**

```bash
# Server'da webhook'ni to'xtating
sudo systemctl stop webhook  # yoki screen -X -S webhook quit

# DB ni copy qiling (lock yo'q)
scp user@server:/path/to/processing.db ~/Downloads/

# Webhook'ni qayta ishga tushiring
sudo systemctl start webhook
```

---

### ❌ **Error: "Database is locked"**

**Sabab:** Server'da webhook ishlayotgan va DB locked.

**Yechim 1: Server'da copy qiling (shadow copy)**

```bash
# Server'da:
cd /path/to/JIRA-AI-Analyzer/data
cp processing.db processing_copy.db
scp user@server:/path/to/processing_copy.db ~/Downloads/

# Local'da:
python3 utils/import_server_db.py ~/Downloads/processing_copy.db
```

**Yechim 2: SQLite dump ishlatish**

```bash
# Server'da (lock bo'lmaydi):
sqlite3 /path/to/processing.db .dump > /tmp/db_dump.sql
scp user@server:/tmp/db_dump.sql ~/Downloads/

# Local'da:
sqlite3 data/processing.db < ~/Downloads/db_dump.sql
```

---

## 🛡️ BEST PRACTICES

### ✅ **Server DB ni Copy Qilishdan Oldin**

1. **Webhook'ni to'xtatish** (ixtiyoriy, lekin tavsiya etiladi)
   ```bash
   # Screen session
   screen -X -S webhook quit

   # yoki systemd
   sudo systemctl stop jira-webhook
   ```

2. **DB Backup olish** (server'da)
   ```bash
   cp data/processing.db data/processing_backup.db
   ```

3. **Webhook'ni qayta ishga tushirish**
   ```bash
   screen -dmS webhook python3 services/webhook_service_minimal.py

   # yoki systemd
   sudo systemctl start jira-webhook
   ```

### ✅ **Local'da Import Qilishdan Oldin**

1. **Hozirgi DB ni backup qilish** (tool avtomatik bajaradi)
   ```bash
   cp data/processing.db data/processing_backup.db
   ```

2. **Import tool ishlatish** (safe)
   ```bash
   python3 utils/import_server_db.py ~/Downloads/processing.db
   ```

---

## 📊 MONITORING WORKFLOW

```
┌─────────────────────────────────────────────────┐
│  SERVER (Production)                            │
│  - Webhook running                              │
│  - processing.db (real data)                    │
└─────────────────┬───────────────────────────────┘
                  │
                  │ SCP / SFTP / Download
                  ↓
┌─────────────────────────────────────────────────┐
│  LOCAL (Development)                            │
│  1. Download: ~/Downloads/processing.db         │
│  2. Import: python3 utils/import_server_db.py   │
│  3. Monitor: streamlit run app.py               │
│     → Sidebar → 📊 Monitoring                   │
└─────────────────────────────────────────────────┘
```

---

## 🔧 ADVANCED: AUTOMATIC SYNC

Agar har kuni server DB ni sync qilmoqchi bo'lsangiz:

```bash
#!/bin/bash
# sync_server_db.sh

# Server ma'lumotlari
SERVER="user@192.168.1.100"
SERVER_DB="/opt/jira-analyzer/data/processing.db"
LOCAL_DOWNLOAD="~/Downloads/processing_$(date +%Y%m%d).db"

# 1. Download
echo "📥 Downloading server DB..."
scp $SERVER:$SERVER_DB $LOCAL_DOWNLOAD

# 2. Import
echo "📦 Importing to local DB..."
python3 utils/import_server_db.py $LOCAL_DOWNLOAD

echo "✅ Sync completed!"
```

**Cron job (har kun 9:00 da):**

```bash
crontab -e

# Add:
0 9 * * * /path/to/JIRA-AI-Analyzer/sync_server_db.sh
```

---

## 📝 QISQACHA

```bash
# 1. Serverdan olish
scp user@server:/path/to/processing.db ~/Downloads/

# 2. Import qilish
python3 utils/import_server_db.py ~/Downloads/processing.db

# 3. Monitoring
streamlit run app.py
# Sidebar → 📊 Monitoring
```

**Xatolik bo'lsa:** Tool avtomatik dump/restore qiladi va backup yaratadi! ✅

---

## 🆘 HELP

```bash
# Tool help
python3 utils/import_server_db.py

# DB validate faqat
python3 utils/import_server_db.py ~/Downloads/processing.db --validate-only

# Force import (validation'siz)
python3 utils/import_server_db.py ~/Downloads/processing.db --force
```

---

**Author:** JASUR TURGUNOV
**Version:** 1.0
**Date:** 2026-02-10
