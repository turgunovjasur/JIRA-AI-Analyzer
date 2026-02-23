"""
Task Processing Database Helper

SQLite DB orqali task va servis-bosqich holatlarini boshqarish.
Webhook oqimida dublikat comment va qayta ishlashni oldini olish uchun.

Author: JASUR TURGUNOV
Date: 2026-02-09
Version: 1.0
"""
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
from core.logger import get_logger

log = get_logger("database")

# Settings import (lazy loading to avoid circular imports)
_settings_cache = None

def _get_db_settings():
    """Get DB settings from app_settings (cached)"""
    global _settings_cache
    if _settings_cache is None:
        try:
            from config.app_settings import get_app_settings
            _settings_cache = get_app_settings(force_reload=False).queue
        except Exception as e:
            log.warning(f"Settings load failed, using defaults: {e}")
            # Default values
            class DefaultSettings:
                db_busy_timeout = 30000
                db_connection_timeout = 30.0
            _settings_cache = DefaultSettings()
    return _settings_cache

# DB fayl joylashuvi - loyiha root/data papkasi
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_DIR = os.path.join(PROJECT_ROOT, 'data')
DB_FILE = os.path.join(DB_DIR, 'processing.db')


def _ensure_db_dir():
    """Data papkasini yaratish"""
    Path(DB_DIR).mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    """
    SQLite ma'lumotlar bazasini ishga tushirish va kerakli strukturani yaratish.

    Agar DB fayli mavjud bo'lmasa yaratadi. Agar jadval allaqachon mavjud bo'lsa
    (IF NOT EXISTS), hech narsa o'zgarmaydi — idempotent funksiya.

    Yaratilgan tuzilma:
        - task_processing jadvali (v3 ustunlari bilan: blocked_*, assignee, task_type)
        - WAL (Write-Ahead Logging) rejimi — parallel o'qish uchun
        - busy_timeout=30000ms — bir vaqtda yozishda kutish muddati
        - Tezlashtiruvchi indekslar: task_status, service1_status, service2_status

    WAL rejimi nima uchun:
        SQLite standard rejimda (DELETE mode) yozishda barcha o'qishlarni bloklaydi.
        WAL rejimda yozish va o'qish parallel ishlaydi — webhook server bir vaqtda
        ko'p taskni boshqarganda muhim. Natija: deadlock va timeout xatolari kamayadi.

    v2 ustunlari (meros sifatida CREATE TABLE ga kiritilgan):
        - assignee: JIRA task ijrochisi
        - task_type: task turi (product, client, bug, error, analiz, other)
        - feature_name: PR fayllaridan ajratilgan funksiya nomi
        - technology_stack: PR fayllaridan ajratilgan texnologiyalar

    v3 ustunlari (meros sifatida CREATE TABLE ga kiritilgan):
        - blocked_at: task bloklanган vaqt
        - blocked_retry_at: qayta urinish rejalashtirilgan vaqt
        - block_reason: bloklash sababi (masalan: AI 429 limit)

    Side Effects:
        - data/ katalogi yaratiladi (agar mavjud bo'lmasa)
        - data/processing.db fayli yaratiladi yoki mavjud faylga ulanadi

    Raises:
        Exception: DB fayli yaratish yoki PRAGMA bajarishda muvaffaqiyatsiz bo'lsa
    """
    try:
        _ensure_db_dir()
        settings = _get_db_settings()

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # SQLite optimizatsiyalar concurrent access uchun
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={settings.db_busy_timeout}")
        cursor.execute("PRAGMA foreign_keys=ON")

        # task_processing jadvali (v3: blocked_*, assignee, task_type ustunlari bilan)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_processing (
                task_id TEXT PRIMARY KEY,
                task_status TEXT DEFAULT 'none',
                task_update_time DATETIME,
                return_count INTEGER DEFAULT 0,
                last_jira_status TEXT,
                last_processed_at DATETIME,
                error_message TEXT NULL,
                skip_detected INTEGER DEFAULT 0,

                -- Servis-bosqich holatlari
                service1_status TEXT DEFAULT 'pending',
                service2_status TEXT DEFAULT 'pending',
                service1_error TEXT NULL,
                service2_error TEXT NULL,
                service1_done_at DATETIME NULL,
                service2_done_at DATETIME NULL,

                -- Qo'shimcha ma'lumotlar
                compliance_score INTEGER NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                -- v2: task metadata (assignee, tur, xususiyat, texnologiya)
                assignee TEXT NULL,
                task_type TEXT NULL,
                feature_name TEXT NULL,
                technology_stack TEXT NULL,

                -- v3: blocked holat boshqaruvi
                blocked_at DATETIME NULL,
                blocked_retry_at DATETIME NULL,
                block_reason TEXT NULL
            )
        """)

        # Index yaratish (tez qidirish uchun)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_status 
            ON task_processing(task_status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_service1_status 
            ON task_processing(service1_status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_service2_status 
            ON task_processing(service2_status)
        """)

        conn.commit()
        conn.close()

        log.info(f"DB initialized: {DB_FILE}")

    except Exception as e:
        log.warning(f"DB initialization error: {e}")
        raise

# DB migrations v2 (assignee/task_type/feature_name/technology_stack ustunlari) va
# v3 (blocked_at/blocked_retry_at/block_reason ustunlari) yakunlandi va
# yuqoridagi CREATE TABLE ga kiritildi. Migration funksiyalari o'chirildi 2026-02.


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Berilgan task_id bo'yicha task ma'lumotlarini SQLite dan o'qish.

    WAL rejimda o'qishda eskirgan ma'lumot kelmasligi uchun
    ``PRAGMA synchronous=FULL`` ishlatiladi — bu SQLite ni barcha yozuvlar
    diskka to'liq tushishini kutishga majbur qiladi. Shunday qilib
    ``upsert_task()`` commit qilgandan so'ng darhol chaqirilgan ``get_task()``
    hamma vaqt yangi qiymatni qaytaradi.

    ``conn.row_factory = sqlite3.Row`` o'rnatiladi — bu SELECT natijasini
    oddiy tuple emas, balki nom orqali murojaat qilish mumkin bo'lgan
    Row obyektiga aylantiradi. ``dict(row)`` chaqiruvida to'liq kalit-qiymat
    lug'ati hosil qilinadi.

    Args:
        task_id: JIRA task identifikatori (masalan: DEV-1234, PROJ-999)

    Returns:
        Dict[str, Any]: Jadval ustunlari kalit, qiymatlari bo'lgan lug'at.
            Agar task topilmasa — None qaytadi.

    Note:
        Xato yuz berganda (masalan DB fayli yo'q) None qaytadi va
        log.warning chiqariladi — exception ko'tarilmaydi.
    """
    try:
        settings = _get_db_settings()
        conn = sqlite3.connect(DB_FILE, timeout=settings.db_connection_timeout)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # WAL mode'da fresh data o'qish uchun
        cursor.execute("PRAGMA synchronous=FULL")

        cursor.execute("""
            SELECT * FROM task_processing
            WHERE task_id = ?
        """, (task_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    except Exception as e:
        log.warning(f"[{task_id}] get_task error: {e}")
        return None


def upsert_task(task_id: str, fields: Dict[str, Any]) -> None:
    """
    Task ma'lumotlarini yangilash (UPDATE) yoki yangi yaratish (INSERT).

    Funksiya avval task mavjudligini tekshiradi: agar bor bo'lsa UPDATE,
    bo'lmasa INSERT bajaradi. ``updated_at`` maydoni har safar avtomatik
    yangilanadi.

    BEGIN IMMEDIATE transaction lock nima uchun:
        SQLite da standart ``BEGIN`` (DEFERRED) holatida bir nechta jarayon
        bir vaqtda o'qiy oladi, lekin birinchi yozuvchi lock olguncha
        boshqalar ham o'qib, keyin yozmoqchi bo'lishi mumkin — bu race
        condition ga olib keladi. ``BEGIN IMMEDIATE`` esa darhol write-lock
        oladi: boshqa yozuvchilar kutadi. Webhook server bir vaqtda bir nechta
        event qayta ishlaganda bu muhim himoya mexanizmi hisoblanadi.

    Args:
        task_id: JIRA task identifikatori (masalan: DEV-1234)
        fields: Yangilanishi kerak bo'lgan maydonlar lug'ati.
            Masalan: ``{'task_status': 'progressing', 'service1_status': 'pending'}``

    Raises:
        sqlite3.OperationalError: DB lock xatosi (masalan: database is locked).
            Lock xatosi bo'lsa log.warning chiqariladi va exception ko'tariladi.
        Exception: Boshqa kutilmagan SQLite xatolari.

    Note:
        ``fields`` lug'atidagi ``updated_at`` kaliti bu funksiya tomonidan
        avtomatik o'rnatiladi — tashqaridan berilgan qiymat ustiga yoziladi.
    """
    try:
        settings = _get_db_settings()
        conn = sqlite3.connect(DB_FILE, timeout=settings.db_connection_timeout)
        cursor = conn.cursor()

        # SQLite optimizatsiyalar
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={settings.db_busy_timeout}")

        # IMMEDIATE transaction - lock olish
        cursor.execute("BEGIN IMMEDIATE")

        # Mavjud taskni tekshirish
        cursor.execute("SELECT task_id FROM task_processing WHERE task_id = ?", (task_id,))
        exists = cursor.fetchone()

        # updated_at avtomatik yangilanadi
        fields['updated_at'] = datetime.now().isoformat()

        if exists:
            # UPDATE
            set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
            values = list(fields.values()) + [task_id]
            cursor.execute(f"UPDATE task_processing SET {set_clause} WHERE task_id = ?", values)
        else:
            # INSERT
            fields['task_id'] = task_id
            fields['created_at'] = datetime.now().isoformat()
            columns = ", ".join(fields.keys())
            placeholders = ", ".join(["?" for _ in fields])
            values = list(fields.values())
            cursor.execute(f"INSERT INTO task_processing ({columns}) VALUES ({placeholders})", values)

        conn.commit()
        conn.close()

    except sqlite3.OperationalError as e:
        log.warning(f"[{task_id}] SQLite lock error: {e}")
        if 'locked' in str(e).lower():
            log.warning(f"[{task_id}] Database locked, retry recommended")
        raise
    except Exception as e:
        log.warning(f"[{task_id}] upsert_task error: {e}")
        raise


def mark_progressing(task_id: str, jira_status: str, update_time: Optional[datetime] = None) -> None:
    """
    Task holatini ``'progressing'`` ga o'zgartirish — qayta ishlash boshlanganda chaqiriladi.

    Holat o'tishi (state transition):
        ``none`` / ``completed`` / ``error`` / ``blocked`` / ``returned``
            → ``progressing``

    Bu holat webhook handler da dublikat ishlov berishni oldini olish uchun
    ishlatiladi: agar task allaqachon ``progressing`` bo'lsa, keyingi webhook
    eventi e'tiborga olinmaydi (queue lock mexanizmi).

    Saqlanadigan ma'lumotlar:
        - ``task_status`` = ``'progressing'``
        - ``last_jira_status``: JIRA dagi joriy status nomi (masalan: ``Ready to Test``)
        - ``task_update_time``: JIRA webhook eventidagi o'zgarish vaqti
        - ``last_processed_at``: hozirgi vaqt (qayta ishlash boshlangan moment)

    Args:
        task_id: JIRA task identifikatori (masalan: DEV-1234)
        jira_status: JIRA status nomi (masalan: ``'Ready to Test'``)
        update_time: JIRA webhook eventidagi vaqt damgasi.
            Agar berilmasa — hozirgi vaqt (``datetime.now()``) ishlatiladi.
    """
    if update_time is None:
        update_time = datetime.now()
    
    upsert_task(task_id, {
        'task_status': 'progressing',
        'last_jira_status': jira_status,
        'task_update_time': update_time.isoformat(),
        'last_processed_at': datetime.now().isoformat()
    })


def mark_completed(task_id: str):
    """
    Task holatini 'completed' ga o'zgartirish
    """
    upsert_task(task_id, {
        'task_status': 'completed',
        'last_processed_at': datetime.now().isoformat()
    })


def mark_returned(task_id: str) -> None:
    """
    Task holatini ``'returned'`` ga o'zgartirish — task TZ/PR muammo sababli qaytarilganda.

    Holat o'tishi (state transition):
        ``progressing`` → ``returned``

    Nima uchun service2_status ``'pending'`` qoladi (``'error'`` emas):
        Task ``returned`` bo'lganda Service1 allaqachon ishlagan va past moslik
        bali (compliance_score) tufayli Service2 ishga tushmagan. Bu holat
        ``'error'`` emas — bu kutilgan biznes-mantiq. Shu sababli:

        - ``service1_status`` = ``'done'`` (Service1 bajarilgan, natija past)
        - ``service2_status`` = ``'pending'`` (Service2 hali ishlamagan, xato emas)
        - ``service2_error`` = None (xato xabari tozalanadi)

        Agar ``service2_status`` = ``'error'`` qilinsa, monitoring dashboardda
        noto'g'ri xato ko'rsatiladi va re-check logikasi buziladi.

    Args:
        task_id: JIRA task identifikatori (masalan: DEV-1234)
    """
    upsert_task(task_id, {
        'task_status': 'returned',
        'service1_status': 'done',  # Service1 done bo'lishi kerak (score past bo'lganda ham)
        'service2_status': 'pending',  # Service2 pending (error emas)
        'service2_error': None,
        'last_processed_at': datetime.now().isoformat()
    })


def mark_error(task_id: str, error_message: str):
    """
    Task holatini 'error' ga o'zgartirish
    
    Args:
        task_id: JIRA task key
        error_message: Xato xabari
    """
    upsert_task(task_id, {
        'task_status': 'error',
        'error_message': error_message,
        'last_processed_at': datetime.now().isoformat()
    })


def increment_return_count(task_id: str):
    """
    Return count ni 1 ga oshirish
    """
    task = get_task(task_id)
    if task:
        new_count = (task.get('return_count') or 0) + 1
        upsert_task(task_id, {'return_count': new_count})
    else:
        upsert_task(task_id, {'return_count': 1})


def set_skip_detected(task_id: str):
    """
    Skip detected flag ni True ga o'rnatish
    """
    upsert_task(task_id, {
        'skip_detected': 1,
        'task_status': 'completed',  # yoki 'skipped'
        'last_processed_at': datetime.now().isoformat()
    })


def set_service1_done(task_id: str, compliance_score: Optional[int] = None):
    """
    Service1 (TZ-PR) holatini 'done' ga o'zgartirish
    
    Args:
        task_id: JIRA task key
        compliance_score: Moslik bali (ixtiyoriy)
    """
    fields = {
        'service1_status': 'done',
        'service1_done_at': datetime.now().isoformat(),
        'service1_error': None
    }
    if compliance_score is not None:
        fields['compliance_score'] = compliance_score
    
    upsert_task(task_id, fields)


def set_service1_error(task_id: str, error_msg: str, keep_service2_pending: bool = False) -> None:
    """
    Service1 (TZ-PR checker) holatini ``'error'`` ga o'zgartirish.

    Holat o'tishi (state transition):
        ``service1_status``: ``'pending'`` / ``'progressing'`` → ``'error'``
        ``task_status``: → ``'error'``

    keep_service2_pending parametri nima uchun kerak:
        Ba'zi hollarda Service1 xatosi Service2 ni to'xtatmasligi kerak.
        Masalan, GitHub PR topilmasa Service1 xato bo'ladi, lekin Service2
        TZ-only rejimda ishlashi mumkin. Bunday holda:

        - ``keep_service2_pending=True`` — Service2 ``'pending'`` qoladi,
          Service2 keyingi bosqichda TZ ma'lumoti bilan ishlaydi.

        - ``keep_service2_pending=False`` (default) — Service1 xatosi
          Service2 ni ham bloklaydi: ``service2_status`` = ``'error'``,
          ``service2_error`` = ``'Blocked by Service1 failure'``.

    Args:
        task_id: JIRA task identifikatori (masalan: DEV-1234)
        error_msg: Xato xabari (log va DB ga yoziladi)
        keep_service2_pending: True bo'lsa Service2 ``'pending'`` holatida qoladi
            va keyingi bosqichda TZ-only rejimda ishlashga ruxsat beriladi.
            False bo'lsa (default) Service2 ham ``'error'`` ga o'tadi.
    """
    fields = {
        'service1_status': 'error',
        'service1_error': error_msg,
        'task_status': 'error',
        'last_processed_at': datetime.now().isoformat()
    }
    if keep_service2_pending:
        # Service2 ni pending ga o'rnatish (oldingi error holatini tozalash)
        fields['service2_status'] = 'pending'
        fields['service2_error'] = None
    else:
        fields['service2_status'] = 'error'
        fields['service2_error'] = 'Blocked by Service1 failure'

    upsert_task(task_id, fields)


def set_service2_done(task_id: str):
    """
    Service2 (Testcase) holatini 'done' ga o'zgartirish
    """
    upsert_task(task_id, {
        'service2_status': 'done',
        'service2_done_at': datetime.now().isoformat(),
        'service2_error': None,
        'task_status': 'completed',
        'last_processed_at': datetime.now().isoformat()
    })


def set_service2_error(task_id: str, error_msg: str):
    """
    Service2 (Testcase) holatini 'error' ga o'zgartirish
    
    Args:
        task_id: JIRA task key
        error_msg: Xato xabari
    """
    upsert_task(task_id, {
        'service2_status': 'error',
        'service2_error': error_msg,
        'task_status': 'error',
        'last_processed_at': datetime.now().isoformat()
    })


def set_task_timeout_error(task_id: str, error_msg: str):
    """
    Task queue timeout xatosi - barcha servislar error holatga

    Args:
        task_id: JIRA task key
        error_msg: Timeout xato xabari
    """
    upsert_task(task_id, {
        'task_status': 'error',
        'service1_status': 'error',
        'service2_status': 'error',
        'service1_error': error_msg,
        'service2_error': 'Blocked by timeout',
        'error_message': error_msg,
        'last_processed_at': datetime.now().isoformat()
    })


def mark_blocked(task_id: str, reason: str, retry_minutes: int = 5):
    """
    Task holatini 'blocked' ga o'zgartirish (AI timeout/429 limit)

    Args:
        task_id: JIRA task key
        reason: Bloklash sababi
        retry_minutes: Necha daqiqadan keyin qayta ishlash
    """
    now = datetime.now()
    retry_at = now + timedelta(minutes=retry_minutes)
    upsert_task(task_id, {
        'task_status': 'blocked',
        'error_message': reason,
        'blocked_at': now.isoformat(),
        'blocked_retry_at': retry_at.isoformat(),
        'block_reason': reason,
        'last_processed_at': now.isoformat()
    })


def set_service1_blocked(task_id: str, reason: str, retry_minutes: int = 5):
    """
    Service1 ni 'blocked' va task ni 'blocked' ga o'zgartirish
    Service2 'pending' qoladi

    Args:
        task_id: JIRA task key
        reason: Bloklash sababi
        retry_minutes: Necha daqiqadan keyin qayta ishlash
    """
    now = datetime.now()
    retry_at = now + timedelta(minutes=retry_minutes)
    upsert_task(task_id, {
        'service1_status': 'blocked',
        'service1_error': reason,
        'service2_status': 'pending',
        'task_status': 'blocked',
        'error_message': reason,
        'blocked_at': now.isoformat(),
        'blocked_retry_at': retry_at.isoformat(),
        'block_reason': reason,
        'last_processed_at': now.isoformat()
    })


def set_service2_blocked(task_id: str, reason: str, retry_minutes: int = 5):
    """
    Service2 ni 'blocked' va task ni 'blocked' ga o'zgartirish
    Service1 o'zgarmaydi (done yoki skip)

    Args:
        task_id: JIRA task key
        reason: Bloklash sababi
        retry_minutes: Necha daqiqadan keyin qayta ishlash
    """
    now = datetime.now()
    retry_at = now + timedelta(minutes=retry_minutes)
    upsert_task(task_id, {
        'service2_status': 'blocked',
        'service2_error': reason,
        'task_status': 'blocked',
        'error_message': reason,
        'blocked_at': now.isoformat(),
        'blocked_retry_at': retry_at.isoformat(),
        'block_reason': reason,
        'last_processed_at': now.isoformat()
    })


def set_service1_skip(task_id: str):
    """
    Service1 ni 'skip' ga o'zgartirish (AI_SKIP code topilganda)
    Score 100 qo'yiladi (threshold check o'tishi uchun)
    """
    upsert_task(task_id, {
        'service1_status': 'skip',
        'service1_done_at': datetime.now().isoformat(),
        'service1_error': None,
        'compliance_score': 100,
        'skip_detected': 1
    })


def get_blocked_tasks_ready_for_retry() -> List[Dict[str, Any]]:
    """
    Qayta urinish vaqti kelgan ``'blocked'`` tasklarni tanlash.

    So'rov mantiq:
        ``WHERE task_status = 'blocked'
           AND blocked_retry_at IS NOT NULL
           AND blocked_retry_at <= :now``

        Ya'ni: hozirgi vaqt ``blocked_retry_at`` dan katta yoki teng bo'lgan
        barcha blocked tasklar qaytariladi. Bu retry scheduler tomonidan har
        N daqiqada chaqiriladi — ``blocked_retry_at`` qiymati kelajakda
        bo'lsa, o'sha task hali tayyor emas.

    Bloklash stsenariylari (bu funksiya ular uchun ishlatiladi):
        - AI 429 (Too Many Requests) — rate limit oshilganda
        - AI timeout — Gemini javob bermasa
        - ``mark_blocked()``, ``set_service1_blocked()``, ``set_service2_blocked()``
          orqali o'rnatilgan holatlar

    Tartiblash:
        ``blocked_retry_at ASC`` — eng eski (eng uzoq kutgan) task birinchi.

    Returns:
        List[Dict[str, Any]]: Har bir task to'liq maydonlari bilan lug'at sifatida.
            Bo'sh ro'yxat qaytadi agar tayyor task yo'q bo'lsa yoki xato yuz bersa.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute("""
            SELECT * FROM task_processing
            WHERE task_status = 'blocked'
              AND blocked_retry_at IS NOT NULL
              AND blocked_retry_at <= ?
            ORDER BY blocked_retry_at ASC
        """, (now,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    except Exception as e:
        log.warning(f"get_blocked_tasks_ready_for_retry error: {e}")
        return []


def delete_task(task_id: str) -> bool:
    """
    Taskni DB dan to'liq o'chirish (transaction-safe)

    Args:
        task_id: JIRA task key

    Returns:
        True agar o'chirilsa, False agar topilmasa
    """
    conn = None
    try:
        settings = _get_db_settings()
        conn = sqlite3.connect(DB_FILE, timeout=settings.db_connection_timeout)
        cursor = conn.cursor()

        # SQLite optimizatsiyalar
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={settings.db_busy_timeout}")

        # IMMEDIATE transaction - lock olish va to'liq o'chirishni ta'minlash
        cursor.execute("BEGIN IMMEDIATE")

        # Avval taskni tekshirish
        cursor.execute("SELECT task_id FROM task_processing WHERE task_id = ?", (task_id,))
        exists = cursor.fetchone()

        if exists:
            # Taskni o'chirish
            cursor.execute("DELETE FROM task_processing WHERE task_id = ?", (task_id,))
            deleted_count = cursor.rowcount
            conn.commit()

            # WAL mode checkpoint (to'liq yozish)
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")

            # O'chirilganini tekshirish (verification)
            cursor.execute("SELECT task_id FROM task_processing WHERE task_id = ?", (task_id,))
            still_exists = cursor.fetchone()

            if still_exists:
                conn.close()
                conn = None
                log.warning(f"[{task_id}] DB-DELETE -> failed, task still exists after DELETE")
                return False
            else:
                conn.close()
                conn = None
                log.info(f"[{task_id}] DB-DELETE -> ok (count={deleted_count})")
                return True
        else:
            conn.commit()
            conn.close()
            conn = None
            log.warning(f"[{task_id}] DB-DELETE -> task not found, nothing to delete")
            return False

    except sqlite3.OperationalError as e:
        log.warning(f"[{task_id}] SQLite lock error: {e}")
        if 'locked' in str(e).lower():
            log.warning(f"[{task_id}] Database locked, retry recommended")
        if conn:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return False
    except Exception as e:
        log.warning(f"[{task_id}] delete_task error: {e}")
        if conn:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return False
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def reset_service_statuses(task_id: str) -> None:
    """
    Servis holatlarini noldan boshlash uchun qayta tiklash (re-check stsenariysida).

    Qachon chaqiriladi:
        Task ilgari ``'returned'`` yoki ``'error'`` holatida bo'lgan va
        endi qayta ``Ready to Test`` statusiga o'tganda (masalan: developer
        TZ ni to'ldirib, taskni qaytadan test uchun jo'natganda) bu funksiya
        chaqiriladi. Shunday qilib Service1 va Service2 yana yangi sikl
        sifatida boshidan boshlanadi.

    Reset qilinadigan maydonlar:
        - ``service1_status`` → ``'pending'``
        - ``service2_status`` → ``'pending'``
        - ``service1_error`` → None
        - ``service2_error`` → None
        - ``service1_done_at`` → None
        - ``service2_done_at`` → None
        - ``compliance_score`` → None

    O'zgarmaydigan maydonlar:
        - ``task_status``: chaqiruvchi funksiya tomonidan boshqariladi
        - ``return_count``: saqlab qolinadi (nechi marta qaytarilgani statistika uchun)
        - ``assignee``, ``task_type``, ``feature_name``: meta-ma'lumotlar saqlanadi

    Args:
        task_id: JIRA task identifikatori (masalan: DEV-1234)
    """
    upsert_task(task_id, {
        'service1_status': 'pending',
        'service2_status': 'pending',
        'service1_error': None,
        'service2_error': None,
        'service1_done_at': None,
        'service2_done_at': None,
        'compliance_score': None
    })


def _extract_task_type(task_details: Dict) -> str:
    """
    Extract task type from JIRA labels or issue type.

    Returns one of: product, client, bug, error, analiz, other
    """
    # Priority 1: Check labels
    labels = task_details.get('labels', [])
    labels_lower = [label.lower() for label in labels]

    type_keywords = {
        'product': ['product', 'mahsulot', 'feature'],
        'client': ['client', 'mijoz', 'customer'],
        'bug': ['bug', 'xato', 'defect'],
        'error': ['error', 'crash', 'exception'],
        'analiz': ['analiz', 'analysis', 'research']
    }

    for task_type, keywords in type_keywords.items():
        for keyword in keywords:
            if any(keyword in label for label in labels_lower):
                return task_type

    # Priority 2: Issue type name
    issue_type = task_details.get('type', '').lower()
    if 'bug' in issue_type:
        return 'bug'
    elif 'error' in issue_type:
        return 'error'
    elif 'task' in issue_type or 'story' in issue_type:
        return 'product'

    return 'other'


def _extract_features_from_pr_files(pr_files: List[Dict]) -> tuple:
    """
    Extract feature names and tech stack from PR file paths.

    Patterns:
    - main/page/form/anor/mkpi/robot_bonus_setting.html → mkpi, HTML
    - main/oracle/anor/mkpi/pkg_bonus.sql → mkpi, Oracle
    - main/app/bonus/BonusService.java → bonus, Java

    Returns:
        tuple: (feature_names_csv, tech_stack_csv) or (None, None)
    """
    import re

    features = set()
    technologies = set()

    # Technology patterns
    tech_patterns = {
        'Oracle': [r'\.sql$', r'\.pks$', r'\.pkb$', r'\.pck$', r'/oracle/'],
        'HTML': [r'\.html?$'],
        'Java': [r'\.java$'],
        'JavaScript': [r'\.jsx?$'],
        'TypeScript': [r'\.tsx?$'],
        'Python': [r'\.py$'],
    }

    # Feature extraction patterns
    feature_patterns = [
        r'main/page/form/[^/]+/([^/]+)/',    # HTML forms
        r'main/oracle/[^/]+/([^/]+)/',       # Oracle packages
        r'main/app/([^/]+)/',                 # Java app
        r'src/([^/]+)/',                      # Generic src
    ]

    for file_data in pr_files:
        filename = file_data.get('filename', '')

        # Detect technology
        for tech, patterns in tech_patterns.items():
            for pattern in patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    technologies.add(tech)
                    break

        # Extract feature
        for pattern in feature_patterns:
            match = re.search(pattern, filename)
            if match:
                feature = match.group(1)
                # Clean: lowercase, remove non-alphanumeric
                feature = re.sub(r'[^a-z0-9_]', '', feature.lower())
                if len(feature) > 2:  # Skip too short
                    features.add(feature)

    # Convert to comma-separated strings
    feature_csv = ', '.join(sorted(features)) if features else None
    tech_csv = ', '.join(sorted(technologies)) if technologies else None

    return feature_csv, tech_csv


def update_task_metadata(
    task_id: str,
    task_details: Dict,
    pr_info: Optional[Dict] = None
):
    """
    Update task metadata: assignee, task_type, feature_name, technology_stack.

    Called from TZ-PR checker after PR fetch.
    """
    try:
        # Extract from JIRA
        assignee = task_details.get('assignee', 'Unassigned')
        task_type = _extract_task_type(task_details)

        # Extract from PR files
        feature_name = None
        technology_stack = None

        if pr_info and pr_info.get('all_files'):
            feature_name, technology_stack = _extract_features_from_pr_files(
                pr_info['all_files']
            )

        # Update DB
        upsert_task(task_id, {
            'assignee': assignee,
            'task_type': task_type,
            'feature_name': feature_name,
            'technology_stack': technology_stack
        })

    except Exception as e:
        log.warning(f"[{task_id}] Metadata update error: {e}")


def get_stuck_tasks(timeout_minutes: int = 30) -> List[Dict[str, Any]]:
    """
    ``'progressing'`` holatida qolib ketgan (stuck) tasklarni topish.

    Task "stuck" hisoblanganda:
        Task ``'progressing'`` holatiga o'tgandan keyin ``timeout_minutes``
        daqiqadan ortiq vaqt o'tsa va hali ham ``'progressing'`` bo'lsa —
        bu task server crash, network uzilishi yoki kutilmagan xato sababli
        to'xtab qolgan deb hisoblanadi.

    timeout_minutes parametri nima uchun kerak:
        - Turli muhitlarda (test, staging, prod) timeout farqli bo'lishi mumkin.
        - Kichik qiymat (masalan: 5 min) — test muhitida tez aniqlash uchun.
        - Katta qiymat (masalan: 60 min) — og'ir AI operatsiyalar uchun.
        - Default: 30 daqiqa — oddiy webhook operatsiyalar uchun yetarli.

    SQL so'rovi:
        ``WHERE task_status = 'progressing'
           AND updated_at < :cutoff_time``

        ``stuck_minutes`` = ``(julianday('now') - julianday(updated_at)) * 1440``
        (julianday farqi kunlarda, x1440 → daqiqaga aylantiriladi)

    Monitoring ishlatilishi:
        Bu funksiya monitoring dashboard va cleanup scheduler tomonidan
        periodiq chaqiriladi. Topilgan stuck tasklar ``mark_error()`` orqali
        xato holatiga o'tkazilishi yoki adminга xabar yuborilishi mumkin.

    Args:
        timeout_minutes: Qancha daqiqa o'tsa task stuck deb hisoblanadi.
            Default: 30 daqiqa.

    Returns:
        List[Dict[str, Any]]: Stuck tasklar ro'yxati. Har bir element:
            - ``task_id``: JIRA task identifikatori
            - ``task_status``: ``'progressing'``
            - ``service1_status``, ``service2_status``: servis holatlari
            - ``last_processed_at``, ``updated_at``: vaqt damgalari
            - ``stuck_minutes``: necha daqiqa stuck bo'lgani (hisoblangan)
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cutoff_time = (datetime.now() - timedelta(minutes=timeout_minutes)).isoformat()

        cursor.execute("""
            SELECT task_id, task_status, service1_status, service2_status,
                   last_processed_at, updated_at,
                   ROUND((julianday('now') - julianday(updated_at)) * 1440) as stuck_minutes
            FROM task_processing
            WHERE task_status = 'progressing'
              AND updated_at < ?
            ORDER BY updated_at ASC
        """, (cutoff_time,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    except Exception as e:
        log.warning(f"get_stuck_tasks error: {e}")
        return []


# DB initialization on import
try:
    init_db()
    # migrate_db_v2()
    # migrate_db_v3()
except Exception as e:
    log.warning(f"DB initialization warning: {e}")
