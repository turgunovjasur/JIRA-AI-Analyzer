# Test Qilish Qo'llanmasi (v4.0)

## 📋 Qilingan O'zgarishlar

### 1. **DB Tizimi**
- ✅ SQLite DB yaratildi: `data/processing.db`
- ✅ Task holatlarini saqlash
- ✅ Service1/Service2 holatlarini kuzatish
- ✅ Return count kuzatish

### 2. **Webhook Oqimi**
- ✅ DB tekshiruvi qo'shildi
- ✅ Dublikat eventlar oldini olish
- ✅ AI_SKIP sharti (faqat return_count > 0 bo'lsa)
- ✅ Service1 → Service2 ketma-ketligi
- ✅ Score threshold tekshiruvi

### 3. **Logging**
- ✅ Har bir bosqich log qilinadi
- ✅ Debug ma'lumotlari: task_id, status, return_count, score

---

## 🧪 Test Qilish Usullari

### **1. UI Browserda Test (Streamlit)**

#### A) DB Holatini Ko'rish
```bash
# Streamlit UI ni ishga tushiring
streamlit run app.py
```

**Browserda:**
1. `TZ-PR Checker` sahifasiga o'ting
2. Task key kiriting va "Check" tugmasini bosing
3. Natijalarni ko'ring

**Cheklov:** UI faqat manual check qiladi, webhook'ni to'g'ridan-to'g'ri test qilmaydi.

---

### **2. Serverda Test (Webhook Endpoint)**

#### A) Manual Check Endpoint
```bash
# Terminal'da:
curl -X POST http://localhost:8000/manual/check/DEV-1234
```

**Bu nima qiladi:**
- Service1 (TZ-PR) va Service2 (Testcase) ishlaydi
- DB holati yangilanadi
- Loglar `webhook.log` faylida ko'rinadi

#### B) Webhook Serverini Ishga Tushirish
```bash
# Terminal'da:
cd /Users/mac/Documents/projects/JIRA-AI-Analyzer
python -m services.webhook_service_minimal
```

Yoki:
```bash
uvicorn services.webhook_service_minimal:app --host 0.0.0.0 --port 8000
```

**Server ishga tushganda:**
- `http://localhost:8000/` - Service holati
- `http://localhost:8000/health` - Health check
- `http://localhost:8000/settings` - Sozlamalar
- `http://localhost:8000/webhook/jira` - Webhook endpoint (POST)

#### C) Webhook'ni Simulyatsiya Qilish
```bash
# webhook.txt faylidan misol olish
curl -X POST http://localhost:8000/webhook/jira \
  -H "Content-Type: application/json" \
  -d @webhook.txt
```

---

### **3. DB Holatini Tekshirish**

#### SQLite DB'ni Ko'rish
```bash
# Terminal'da:
sqlite3 data/processing.db

# SQL so'rovlar:
SELECT * FROM task_processing;
SELECT task_id, task_status, return_count, service1_status, service2_status, compliance_score 
FROM task_processing 
ORDER BY updated_at DESC 
LIMIT 10;
```

#### Python Script Orqali
```python
from utils.task_db import get_task

task = get_task("DEV-1234")
print(task)
```

---

### **4. Loglarni Tekshirish**

#### Real-time Loglar
```bash
# Terminal'da:
tail -f webhook.log
```

#### Log Format
```
[task_id] 📋 Webhook qabul qilindi
[task_id] 📊 DB holat tekshirildi
[task_id] ✅ DB: mark_progressing
[task_id] 🔵 Service1 (TZ-PR) boshlandi
[task_id] ✅ Service1 done: compliance_score=75%
[task_id] 🟢 Service2 (Testcase) boshlandi
[task_id] ✅ Service2 done
```

---

## ✅ Test Senaryolari

### **Senariyo 1: Birinchi Marta Task**
1. JIRA'da task'ni "Ready to Test" statusga o'tkazing
2. Webhook keladi
3. DB'da `task_status = progressing` bo'ladi
4. Service1 ishlaydi
5. Score >= threshold bo'lsa → Service2 ishlaydi
6. `task_status = completed` bo'ladi

**Tekshirish:**
```bash
sqlite3 data/processing.db "SELECT * FROM task_processing WHERE task_id='DEV-1234';"
```

### **Senariyo 2: Task Qaytarilgan (Returned)**
1. Task "Need Clarification" statusga qaytariladi
2. Keyin yana "Ready to Test" ga o'tkaziladi
3. `return_count` 1 ga oshadi
4. AI_SKIP sharti ishlaydi (agar return_count > 0 bo'lsa)

**Tekshirish:**
```bash
sqlite3 data/processing.db "SELECT return_count, task_status FROM task_processing WHERE task_id='DEV-1234';"
```

### **Senariyo 3: Score Past (Threshold dan past)**
1. Service1 ishlaydi
2. `compliance_score < threshold` bo'lsa
3. Task `returned` holatiga o'tadi
4. Service2 **bloklangan** (ishlamaydi)

**Tekshirish:**
```bash
sqlite3 data/processing.db "SELECT compliance_score, service2_status, task_status FROM task_processing WHERE task_id='DEV-1234';"
```

### **Senariyo 4: Dublikat Event**
1. Bir xil event qayta keladi
2. DB tekshiruvi dublikatni aniqlaydi
3. Event ignor qilinadi

**Tekshirish:**
- Loglarda: `⏭️ Dublikat event: ... allaqachon ishlanmoqda`

---

## 🔍 Debug Qilish

### **1. DB Holatini Ko'rish**
```python
from utils.task_db import get_task

task = get_task("DEV-1234")
if task:
    print(f"Task Status: {task['task_status']}")
    print(f"Return Count: {task['return_count']}")
    print(f"Service1: {task['service1_status']}")
    print(f"Service2: {task['service2_status']}")
    print(f"Score: {task.get('compliance_score', 'N/A')}")
```

### **2. Loglarni Filtrlash**
```bash
# Faqat bir task uchun loglar
grep "DEV-1234" webhook.log

# Faqat Service1 loglari
grep "Service1" webhook.log

# Faqat xatolar
grep "ERROR\|❌" webhook.log
```

### **3. DB'ni Tozalash (Test uchun)**
```bash
sqlite3 data/processing.db "DELETE FROM task_processing WHERE task_id='DEV-1234';"
```

---

## 📊 Kutilayotgan Natijalar

### **Muvaffaqiyatli Oqim:**
```
[DEV-1234] 📋 Webhook qabul qilindi
[DEV-1234] 📊 DB holat tekshirildi
[DEV-1234] ✅ DB: mark_progressing
[DEV-1234] 🔵 Service1 (TZ-PR) boshlandi
[DEV-1234] ✅ Service1 done: compliance_score=75%
[DEV-1234] 🟢 Service2 (Testcase) boshlandi
[DEV-1234] ✅ Service2 done
[DEV-1234] ✅ Task completed
```

### **Score Past Bo'lganda:**
```
[DEV-1234] 🔵 Service1 (TZ-PR) boshlandi
[DEV-1234] ✅ Service1 done: compliance_score=45%
[DEV-1234] ⚠️ Score past: 45% < 60%, task qaytariladi
[DEV-1234] ✅ Task returned, Service2 bloklangan
```

### **AI_SKIP Topilganda:**
```
[DEV-1234] ⏭️ Skip code 'AI_SKIP' topildi (return_count=1 > 0)
[DEV-1234] ✅ Skip detected, AI tekshirish o'chirilgan
```

---

## ⚠️ Muhim Eslatmalar

1. **Webhook server alohida ishlaydi** - Streamlit UI dan mustaqil
2. **DB avtomatik yaratiladi** - Birinchi marta import qilinganda
3. **Loglar `webhook.log` faylida** - Real-time kuzatish mumkin
4. **Manual check UI'da ishlaydi** - Lekin webhook'ni to'g'ridan-to'g'ri test qilmaydi

---

## 🚀 Tez Start

```bash
# 1. Webhook serverini ishga tushirish
python -m services.webhook_service_minimal

# 2. Boshqa terminal'da manual test
curl -X POST http://localhost:8000/manual/check/DEV-1234

# 3. Loglarni kuzatish
tail -f webhook.log

# 4. DB holatini ko'rish
sqlite3 data/processing.db "SELECT * FROM task_processing;"
```
