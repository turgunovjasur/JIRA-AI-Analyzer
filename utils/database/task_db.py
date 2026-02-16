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
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

# DB fayl joylashuvi - loyiha root/data papkasi
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_DIR = os.path.join(PROJECT_ROOT, 'data')
DB_FILE = os.path.join(DB_DIR, 'processing.db')


def _ensure_db_dir():
    """Data papkasini yaratish"""
    Path(DB_DIR).mkdir(parents=True, exist_ok=True)


def init_db():
    """
    DB va jadvalni yaratish (yoki yangilash)
    WAL mode va busy_timeout concurrent access uchun
    """
    try:
        _ensure_db_dir()

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # SQLite optimizatsiyalar concurrent access uchun
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")  # 30s
        cursor.execute("PRAGMA foreign_keys=ON")

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


def migrate_db_v2():
    """
    Migrate DB to v2: add assignee, task_type, feature_name, technology_stack
    Idempotent - safe to run multiple times
    """
    try:
        _ensure_db_dir()
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Check if already migrated
        cursor.execute("PRAGMA table_info(task_processing)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'assignee' in columns:
            logger.info("✅ DB already migrated to v2")
            conn.close()
            return

        logger.info("🔄 DB migration to v2...")

        # Add new columns
        cursor.execute("ALTER TABLE task_processing ADD COLUMN assignee TEXT NULL")
        cursor.execute("ALTER TABLE task_processing ADD COLUMN task_type TEXT NULL")
        cursor.execute("ALTER TABLE task_processing ADD COLUMN feature_name TEXT NULL")
        cursor.execute("ALTER TABLE task_processing ADD COLUMN technology_stack TEXT NULL")

        # Indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_type
            ON task_processing(task_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assignee
            ON task_processing(assignee)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feature_name
            ON task_processing(feature_name)
        """)

        conn.commit()
        conn.close()
        logger.info("✅ DB migration v2 completed!")

    except Exception as e:
        logger.error(f"❌ DB migration error: {e}", exc_info=True)
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
    Task ma'lumotlarini yangilash yoki yaratish (transaction-safe)

    Args:
        task_id: JIRA task key
        fields: Yangilash kerak bo'lgan maydonlar
    """
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        # SQLite optimizatsiyalar
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")

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
        logger.error(f"[{task_id}] SQLite lock error: {e}", exc_info=True)
        if 'locked' in str(e).lower():
            logger.error(f"[{task_id}] Database locked, retry recommended")
        raise
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
    Service2 ham avtomatik bloklangan holatga o'tadi

    Args:
        task_id: JIRA task key
        error_msg: Xato xabari
    """
    upsert_task(task_id, {
        'service1_status': 'error',
        'service1_error': error_msg,
        'service2_status': 'error',
        'service2_error': 'Blocked by Service1 failure',
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

        logger.info(
            f"[{task_id}] Metadata: {assignee}, {task_type}, "
            f"{feature_name or 'N/A'}, {technology_stack or 'N/A'}"
        )

    except Exception as e:
        logger.error(f"[{task_id}] Metadata update error: {e}")


def get_stuck_tasks(timeout_minutes: int = 30) -> List[Dict[str, Any]]:
    """
    'progressing' statusda timeout minutdan ortiq turgan tasklarni topish

    Args:
        timeout_minutes: Task stuck hisoblanadigan muddat (daqiqa)

    Returns:
        Stuck task'lar ro'yxati [{'task_id': 'DEV-123', 'stuck_minutes': 45, ...}, ...]
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
        logger.error(f"get_stuck_tasks error: {e}", exc_info=True)
        return []


# DB initialization on import
try:
    init_db()
    migrate_db_v2()  # ✅ Auto-migrate to v2
except Exception as e:
    logger.warning(f"DB initialization warning: {e}")
