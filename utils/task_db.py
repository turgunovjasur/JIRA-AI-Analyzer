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
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# DB fayl joylashuvi
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
DB_FILE = os.path.join(DB_DIR, 'processing.db')


def _ensure_db_dir():
    """Data papkasini yaratish"""
    Path(DB_DIR).mkdir(parents=True, exist_ok=True)


def init_db():
    """
    DB va jadvalni yaratish (yoki yangilash)
    """
    try:
        _ensure_db_dir()
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # task_processing jadvali
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
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
        
        logger.info(f"✅ DB initialized: {DB_FILE}")
        
    except Exception as e:
        logger.error(f"❌ DB initialization error: {e}", exc_info=True)
        raise


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Task ma'lumotlarini olish
    
    Args:
        task_id: JIRA task key (masalan: DEV-1234)
        
    Returns:
        dict yoki None
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
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
        logger.error(f"[{task_id}] get_task error: {e}", exc_info=True)
        return None


def upsert_task(task_id: str, fields: Dict[str, Any]):
    """
    Task ma'lumotlarini yangilash yoki yaratish
    
    Args:
        task_id: JIRA task key
        fields: Yangilash kerak bo'lgan maydonlar
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
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
        
    except Exception as e:
        logger.error(f"[{task_id}] upsert_task error: {e}", exc_info=True)
        raise


def mark_progressing(task_id: str, jira_status: str, update_time: Optional[datetime] = None):
    """
    Task holatini 'progressing' ga o'zgartirish
    
    Args:
        task_id: JIRA task key
        jira_status: JIRA status nomi
        update_time: Vaqt (default: hozirgi vaqt)
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


def mark_returned(task_id: str):
    """
    Task holatini 'returned' ga o'zgartirish
    """
    upsert_task(task_id, {
        'task_status': 'returned',
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


def set_service1_error(task_id: str, error_msg: str):
    """
    Service1 (TZ-PR) holatini 'error' ga o'zgartirish
    
    Args:
        task_id: JIRA task key
        error_msg: Xato xabari
    """
    upsert_task(task_id, {
        'service1_status': 'error',
        'service1_error': error_msg,
        'task_status': 'error',
        'last_processed_at': datetime.now().isoformat()
    })


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


def reset_service_statuses(task_id: str):
    """
    Service holatlarini qayta ishlash uchun reset qilish

    Re-check vaqtida (task qaytarilgandan keyin yana Ready to Test)
    service statuslarni qayta boshlash uchun ishlatiladi.
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


# DB initialization on import
try:
    init_db()
except Exception as e:
    logger.warning(f"DB initialization warning: {e}")
