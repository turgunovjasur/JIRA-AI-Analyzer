"""
Auth Database — Multi-tenant (companies + users)

Super Admin (.env): SUPER_ADMIN_USERNAME / SUPER_ADMIN_PASSWORD
Kompaniya: super_admin yaratadi — kod, nom, seat_limit, ruxsat berilgan modullar.
User (QA): super_admin kompaniyaga qo'shadi — username@company_code formati.

Jadvallar:
  companies             — kompaniya (code, name, seat_limit, is_active)
  users                 — QA user (company_id FK, username, password_hash)
  user_credentials      — user shaxsiy API kalitlari: JIRA/GitHub/Gemini (UI modullar uchun)
  user_module_settings  — user darajasidagi standalone modul sozlamalari (TZ-PR, Testcase, ...)
  company_settings      — kompaniya webhook sozlamalari: API keys, project keys, enabled_modules

Arxitektura:
  UI modullar (TZ-PR Checker, Testcase Generator, Sprint Report, Bug Analyzer):
    → har user o'z user_credentials kiritadi (bepul Gemini kalit yetarli)
  Webhook servislari (Service-1, Service-2):
    → company_settings kalitlari ishlatiladi (admin sozlaydi, pullik kalit tavsiya)

Author: JASUR TURGUNOV
"""
import sqlite3
import hashlib
import json
import os
import re
import secrets
import shutil
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

# Barcha mavjud modullar ro'yxati (super admin shu ro'yxatdan tanlaydi)
ALL_MODULES = {
    'bug_analyzer':       'Bug Analyzer',
    'statistics':         'Sprint Statistics',
    'tz_pr_checker':      'TZ-PR Checker',
    'testcase_generator': 'Test Case Generator',
    'monitoring':         'Monitoring Dashboard',
    'sprint_report':      'Sprint Report',
    'webhook':            'JIRA Webhook',
}

# Webhook sozlamalari uchun majburiy maydonlar
WEBHOOK_REQUIRED_FIELDS = ['webhook_project_keys', 'webhook_trigger_status']

DEFAULT_MODULES = {k: False for k in ALL_MODULES}

# Default seat limit — admin qo'lda oshiradi
DEFAULT_SEAT_LIMIT = 1

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUTH_DB_FILE = os.path.join(PROJECT_ROOT, 'data', 'auth.db')

# Username formati: "name@company_code"
# name qismi: lotin harflar, raqam, nuqta, tire, underscore
# company_code qismi: lotin harflar va raqam
_USERNAME_RE = re.compile(r'^[a-z0-9._-]+@[a-z0-9]+$')


def _ensure_dir():
    Path(os.path.dirname(AUTH_DB_FILE)).mkdir(parents=True, exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(AUTH_DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    # PRAGMA journal_mode=WAL cursor'ini to'liq iste'mol qilish kerak,
    # aks holda read-lock ushlanadi va "database is locked" xatosi chiqadi.
    cur = conn.execute("PRAGMA journal_mode=WAL")
    cur.fetchone()
    cur.close()
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def validate_username_format(full_username: str) -> bool:
    """
    Foydalanuvchi nomi to'g'ri shaklda ekanligini tekshirish.
    Misol: 'olim@smartup', 'ali.qa@smartup'  →  True
           'olim', 'olim@', '@smartup'        →  False
    """
    if not full_username:
        return False
    return bool(_USERNAME_RE.match(full_username.strip().lower()))


def parse_username(full_username: str) -> Tuple[str, str]:
    """
    'olim@smartup' → ('olim', 'smartup')
    Noto'g'ri shakl bo'lsa ('', '') qaytaradi.
    """
    if not validate_username_format(full_username):
        return '', ''
    name, code = full_username.strip().lower().split('@', 1)
    return name, code


def build_full_username(name: str, company_code: str) -> str:
    """'olim', 'SMARTUP' → 'olim@smartup'"""
    return f"{name.strip().lower()}@{company_code.strip().lower()}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCHEMA DETECTION (Eski schemadan yangi schemaga o'tish)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _is_old_schema(conn: sqlite3.Connection) -> bool:
    """
    Eski schema (v3): companies.password_hash bor, users jadvali yo'q.
    Yangi schema (v4): users jadvali bor.
    """
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    has_users = c.fetchone() is not None
    if has_users:
        return False
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'")
    has_companies = c.fetchone() is not None
    return has_companies  # companies bor, users yo'q → eski schema


def _backup_old_db() -> Optional[str]:
    """Eski DB ni backup qilib nomlash. Yangi DB fayl ochiladi."""
    if not os.path.exists(AUTH_DB_FILE):
        return None
    ts = time.strftime('%Y%m%d_%H%M%S')
    backup_path = f"{AUTH_DB_FILE}.old-{ts}"
    shutil.move(AUTH_DB_FILE, backup_path)
    # WAL fayllarini ham ko'chirish
    for suffix in ('-wal', '-shm'):
        wal = AUTH_DB_FILE + suffix
        if os.path.exists(wal):
            shutil.move(wal, backup_path + suffix)
    return backup_path


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DB INIT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def init_auth_db():
    """Auth DB jadvallarini yaratish (idempotent). Eski schema aniqlansa backup + fresh."""
    _ensure_dir()

    # Eski schema aniqlash va backup
    if os.path.exists(AUTH_DB_FILE):
        try:
            conn = _get_conn()
            old = _is_old_schema(conn)
            conn.close()
            if old:
                backup = _backup_old_db()
                print(f"[auth_db] Eski schema aniqlandi. Backup: {backup}")
        except Exception:
            pass

    conn = _get_conn()
    c = conn.cursor()

    # companies — password yo'q (user layer ga ko'chgan)
    c.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            company_code TEXT    UNIQUE NOT NULL,
            company_name TEXT    NOT NULL,
            seat_limit   INTEGER DEFAULT 1,
            is_active    INTEGER DEFAULT 1,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # users — QA login, kompaniyaga bog'langan
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id    INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            is_active     INTEGER DEFAULT 1,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_company ON users(company_id)")

    # company_settings — API kalitlar, webhook, ruxsat modullar (shared)
    c.execute("""
        CREATE TABLE IF NOT EXISTS company_settings (
            company_id       INTEGER PRIMARY KEY REFERENCES companies(id) ON DELETE CASCADE,
            jira_server      TEXT DEFAULT '',
            jira_email       TEXT DEFAULT '',
            jira_token       TEXT DEFAULT '',
            github_token     TEXT DEFAULT '',
            github_org       TEXT DEFAULT '',
            figma_token      TEXT DEFAULT '',
            gemini_api_key_1 TEXT DEFAULT '',
            gemini_api_key_2 TEXT DEFAULT '',
            enabled_modules  TEXT DEFAULT '{}',
            webhook_project_keys        TEXT DEFAULT '',
            webhook_trigger_status      TEXT DEFAULT '',
            webhook_trigger_aliases     TEXT DEFAULT '',
            webhook_return_status       TEXT DEFAULT '',
            webhook_allowed_issue_types TEXT DEFAULT '',
            webhook_excluded_assignees  TEXT DEFAULT '',
            webhook_auto_return_enabled INTEGER DEFAULT 0,
            webhook_return_threshold    INTEGER DEFAULT 60,
            webhook_module_settings     TEXT DEFAULT '{}',
            updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # user_module_settings — har user o'z standalone modul sozlamalari
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_module_settings (
            user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            module_key    TEXT    NOT NULL,
            settings_json TEXT    NOT NULL DEFAULT '{}',
            updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, module_key)
        )
    """)

    # user_credentials — har user o'z UI modul API kalitlari (JIRA, GitHub, Gemini)
    # Webhook uchun emas — webhook company_settings dan foydalanadi
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_credentials (
            user_id          INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            jira_server      TEXT DEFAULT '',
            jira_email       TEXT DEFAULT '',
            jira_token       TEXT DEFAULT '',
            github_token     TEXT DEFAULT '',
            github_org       TEXT DEFAULT '',
            figma_token      TEXT DEFAULT '',
            gemini_api_key_1 TEXT DEFAULT '',
            gemini_api_key_2 TEXT DEFAULT '',
            updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    # Mavjud DB uchun migration: user_credentials jadvali yo'q bo'lsa qo'shish
    _migrate_user_credentials(conn)

    conn.close()


def _migrate_user_credentials(conn: sqlite3.Connection):
    """user_credentials jadvali mavjud emasligini tekshirib yaratish (migration)."""
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_credentials'")
    if c.fetchone() is None:
        c.execute("""
            CREATE TABLE user_credentials (
                user_id            INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                jira_server        TEXT DEFAULT '',
                jira_email         TEXT DEFAULT '',
                jira_token         TEXT DEFAULT '',
                jira_project_keys  TEXT DEFAULT '',
                github_token       TEXT DEFAULT '',
                github_org         TEXT DEFAULT '',
                figma_token        TEXT DEFAULT '',
                gemini_api_key_1   TEXT DEFAULT '',
                gemini_api_key_2   TEXT DEFAULT '',
                updated_at         DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    else:
        # Mavjud jadvalga jira_project_keys ustunini qo'shish (migration)
        c.execute("PRAGMA table_info(user_credentials)")
        cols = {row[1] for row in c.fetchall()}
        if 'jira_project_keys' not in cols:
            c.execute("ALTER TABLE user_credentials ADD COLUMN jira_project_keys TEXT DEFAULT ''")
            conn.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAROL HASH (pbkdf2 + random salt)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def hash_password(password: str) -> str:
    """Parolni xavfsiz hash qilish. Format: 'salt_hex:hash_hex'"""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode(), 200_000)
    return f"{salt}:{dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Parolni hash bilan solishtirish"""
    try:
        salt, expected = stored_hash.split(':', 1)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode(), 200_000)
        return secrets.compare_digest(dk.hex(), expected)
    except Exception:
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KOMPANIYA CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def create_company(
    company_code: str,
    company_name: str,
    seat_limit: int = DEFAULT_SEAT_LIMIT,
    enabled_modules: Optional[Dict[str, bool]] = None,
) -> Optional[Dict]:
    """
    Yangi kompaniya yaratish (parol yo'q — user layer ga tegishli).

    Args:
        company_code:    Unikal kod (smartup). Lowercase'ga aylantiriladi.
        company_name:    To'liq nom (Smartup LLC)
        seat_limit:      Userlar chegarasi (default 1)
        enabled_modules: Ruxsat berilgan modullar {module_key: bool}

    Returns: yaratilgan kompaniya dict yoki None (code allaqachon mavjud).
    """
    try:
        conn = _get_conn()
        c = conn.cursor()

        code_lower = company_code.strip().lower()
        c.execute(
            "INSERT INTO companies (company_code, company_name, seat_limit) VALUES (?,?,?)",
            (code_lower, company_name.strip(), max(1, int(seat_limit)))
        )
        company_id = c.lastrowid

        mods = {**DEFAULT_MODULES}
        if enabled_modules:
            for k, v in enabled_modules.items():
                if k in mods:
                    mods[k] = bool(v)

        c.execute(
            "INSERT INTO company_settings (company_id, enabled_modules) VALUES (?,?)",
            (company_id, json.dumps(mods))
        )

        conn.commit()
        conn.close()
        return get_company_by_code(code_lower)
    except sqlite3.IntegrityError:
        return None
    except Exception:
        return None


def get_company_by_code(company_code: str) -> Optional[Dict]:
    """Company code bo'yicha kompaniya topish (case-insensitive)"""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute(
            "SELECT * FROM companies WHERE company_code = ?",
            (company_code.strip().lower(),)
        )
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def get_company_by_id(company_id: int) -> Optional[Dict]:
    """ID bo'yicha kompaniya topish"""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def get_all_companies() -> List[Dict]:
    """Barcha kompaniyalar ro'yxati"""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM companies ORDER BY created_at DESC")
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def update_company_status(company_id: int, is_active: bool) -> bool:
    """Kompaniyani faollashtirish/o'chirish"""
    try:
        conn = _get_conn()
        conn.execute(
            "UPDATE companies SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, company_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def update_company_seat_limit(company_id: int, seat_limit: int) -> bool:
    """Kompaniyaning userlar chegarasini yangilash. Min 1."""
    try:
        conn = _get_conn()
        conn.execute(
            "UPDATE companies SET seat_limit = ? WHERE id = ?",
            (max(1, int(seat_limit)), company_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def delete_company(company_id: int) -> bool:
    """Kompaniyani o'chirish (cascade: users, settings, module_settings ham o'chadi)"""
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USER CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def count_users_in_company(company_id: int) -> int:
    """Kompaniyadagi faol+nofaol userlar soni (seat limit tekshiruvi uchun)"""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users WHERE company_id = ?", (company_id,))
        n = c.fetchone()[0]
        conn.close()
        return int(n)
    except Exception:
        return 0


def create_user(
    company_id: int,
    name: str,
    password: str,
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Kompaniyaga yangi user qo'shish.

    Args:
        company_id: Kompaniya ID si
        name:       User nomi (@ belgidan oldingi qism, masalan 'olim')
        password:   Dastlabki parol

    Returns:
        (user_dict, None) — muvaffaqiyatli
        (None, error_message) — xato (seat limit to'lgan / user mavjud / noto'g'ri format)
    """
    company = get_company_by_id(company_id)
    if not company:
        return None, "Kompaniya topilmadi"

    # Seat limit tekshiruvi
    current_count = count_users_in_company(company_id)
    seat_limit = int(company.get('seat_limit') or DEFAULT_SEAT_LIMIT)
    if current_count >= seat_limit:
        return None, (
            f"Seat limit to'lgan ({current_count}/{seat_limit}). "
            f"Super admin seat limitni oshirishi kerak."
        )

    full_username = build_full_username(name, company['company_code'])
    if not validate_username_format(full_username):
        return None, (
            f"User nomi noto'g'ri shaklda: '{full_username}'. "
            "Faqat lotin harflar, raqam, '.' '_' '-' ruxsat etilgan."
        )

    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (company_id, username, password_hash) VALUES (?,?,?)",
            (company_id, full_username, hash_password(password))
        )
        user_id = c.lastrowid
        conn.commit()
        conn.close()
        return get_user_by_id(user_id), None
    except sqlite3.IntegrityError:
        return None, f"Bu username allaqachon mavjud: '{full_username}'"
    except Exception as e:
        return None, f"Xato yuz berdi: {e}"


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """ID bo'yicha user"""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def get_user_by_full_username(full_username: str) -> Optional[Dict]:
    """'olim@smartup' bo'yicha user topish (case-insensitive)"""
    if not validate_username_format(full_username):
        return None
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute(
            "SELECT * FROM users WHERE username = ?",
            (full_username.strip().lower(),)
        )
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def get_users_by_company(company_id: int) -> List[Dict]:
    """Kompaniyadagi barcha userlar ro'yxati"""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute(
            "SELECT * FROM users WHERE company_id = ? ORDER BY created_at ASC",
            (company_id,)
        )
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def update_user_password(user_id: int, new_password: str) -> bool:
    """Userning parolini yangilash"""
    try:
        conn = _get_conn()
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), user_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def update_user_status(user_id: int, is_active: bool) -> bool:
    """Userni faollashtirish/o'chirish"""
    try:
        conn = _get_conn()
        conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, user_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def delete_user(user_id: int) -> bool:
    """Userni o'chirish (cascade: user_module_settings ham o'chadi)"""
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KOMPANIYA SOZLAMALARI (API KALITLAR + WEBHOOK + MODULLAR)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_company_settings(company_id: int) -> Dict:
    """Kompaniya sozlamalarini olish (API keys + webhook + enabled_modules)"""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM company_settings WHERE company_id = ?", (company_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception:
        return {}


def get_company_settings_by_code(company_code: str) -> Dict:
    """Company code orqali API kalitlarini olish (backward-compat shim)"""
    company = get_company_by_code(company_code)
    if not company:
        return {}
    return get_company_settings(company['id'])


def get_company_modules(company_id: int) -> Dict[str, bool]:
    """Kompaniyaga ruxsat berilgan modullar: {'tz_pr_checker': True, ...}"""
    cs = get_company_settings(company_id)
    raw = cs.get('enabled_modules', '{}')
    try:
        mods = json.loads(raw) if raw else {}
    except (json.JSONDecodeError, TypeError):
        mods = {}
    result = {**DEFAULT_MODULES}
    for k, v in mods.items():
        if k in result:
            result[k] = bool(v)
    return result


def save_company_modules(company_id: int, modules: Dict[str, bool]) -> bool:
    """Kompaniyaning ruxsat berilgan modullarini yangilash"""
    clean = {k: bool(v) for k, v in modules.items() if k in ALL_MODULES}
    full = {**DEFAULT_MODULES, **clean}
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("SELECT company_id FROM company_settings WHERE company_id = ?", (company_id,))
        exists = c.fetchone()
        now = datetime.now().isoformat()
        if exists:
            c.execute(
                "UPDATE company_settings SET enabled_modules = ?, updated_at = ? WHERE company_id = ?",
                (json.dumps(full), now, company_id)
            )
        else:
            c.execute(
                "INSERT INTO company_settings (company_id, enabled_modules) VALUES (?,?)",
                (company_id, json.dumps(full))
            )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def save_company_settings(company_id: int, settings: Dict) -> bool:
    """
    Kompaniya sozlamalarini saqlash (upsert).
    Ruxsat etilgan kalitlar: API keys, webhook_*, webhook_module_settings.
    """
    allowed_keys = {
        'jira_server', 'jira_email', 'jira_token',
        'github_token', 'github_org', 'figma_token',
        'gemini_api_key_1', 'gemini_api_key_2',
        'webhook_project_keys', 'webhook_trigger_status', 'webhook_trigger_aliases',
        'webhook_return_status', 'webhook_allowed_issue_types', 'webhook_excluded_assignees',
        'webhook_auto_return_enabled', 'webhook_return_threshold',
        'webhook_module_settings',
    }
    filtered = {k: v for k, v in settings.items() if k in allowed_keys}
    if not filtered:
        return False
    filtered['updated_at'] = datetime.now().isoformat()

    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("SELECT company_id FROM company_settings WHERE company_id = ?", (company_id,))
        exists = c.fetchone()

        if exists:
            set_clause = ", ".join(f"{k} = ?" for k in filtered)
            values = list(filtered.values()) + [company_id]
            c.execute(f"UPDATE company_settings SET {set_clause} WHERE company_id = ?", values)
        else:
            filtered['company_id'] = company_id
            cols = ", ".join(filtered.keys())
            placeholders = ", ".join("?" for _ in filtered)
            c.execute(
                f"INSERT INTO company_settings ({cols}) VALUES ({placeholders})",
                list(filtered.values())
            )

        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def has_api_keys_configured(company_id: int) -> bool:
    """Kompaniya majburiy API kalitlari sozlanganligini tekshirish"""
    cs = get_company_settings(company_id)
    return bool(
        cs.get('jira_email') and
        cs.get('jira_token') and
        cs.get('github_token') and
        cs.get('gemini_api_key_1')
    )


def get_company_gemini_keys(company_id: int) -> list:
    """Kompaniyaning Gemini API kalitlari ro'yxati"""
    cs = get_company_settings(company_id)
    keys = []
    k1 = (cs.get('gemini_api_key_1') or '').strip()
    k2 = (cs.get('gemini_api_key_2') or '').strip()
    if k1:
        keys.append(k1)
    if k2:
        keys.append(k2)
    return keys


def get_company_credentials(company_id: int) -> dict:
    """
    Kompaniyaning barcha API kredensiallarini yuklash va validatsiya qilish.

    Agar majburiy kalit(lar) kiritilmagan bo'lsa → RuntimeError.
    Hech qachon global .env kalitlariga murojaat qilmaydi.
    """
    cs = get_company_settings(company_id)
    missing = []

    jira_server = (cs.get('jira_server') or '').strip()
    jira_email  = (cs.get('jira_email')  or '').strip()
    jira_token  = (cs.get('jira_token')  or '').strip()
    github_token = (cs.get('github_token') or '').strip()
    github_org   = (cs.get('github_org')   or '').strip()
    figma_token  = (cs.get('figma_token')  or '').strip()
    gemini_k1 = (cs.get('gemini_api_key_1') or '').strip()
    gemini_k2 = (cs.get('gemini_api_key_2') or '').strip()

    if not jira_email:
        missing.append("JIRA Email")
    if not jira_token:
        missing.append("JIRA API Token")
    if not github_token:
        missing.append("GitHub Token")
    if not gemini_k1:
        missing.append("Gemini API Key")

    if missing:
        raise RuntimeError(
            f"Kompaniya (id={company_id}) API kalitlari to'liq emas: "
            f"{', '.join(missing)}. Sozlamalar → API Kalitlar bo'limini to'ldiring."
        )

    gemini_keys = [k for k in [gemini_k1, gemini_k2] if k]

    return {
        'jira_server':  jira_server or 'https://yourcompany.atlassian.net',
        'jira_email':   jira_email,
        'jira_token':   jira_token,
        'github_token': github_token,
        'github_org':   github_org,
        'figma_token':  figma_token,
        'gemini_keys':  gemini_keys,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USER CREDENTIALS (UI MODULLAR UCHUN)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_USER_CRED_FIELDS = {
    'jira_server', 'jira_email', 'jira_token', 'jira_project_keys',
    'github_token', 'github_org', 'figma_token',
    'gemini_api_key_1', 'gemini_api_key_2',
}


def get_user_credentials(user_id: int) -> Dict:
    """User o'z UI modul API kalitlarini olish."""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM user_credentials WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception:
        return {}


def save_user_credentials(user_id: int, data: Dict) -> bool:
    """User API kalitlarini saqlash (INSERT OR REPLACE)."""
    filtered = {k: v for k, v in data.items() if k in _USER_CRED_FIELDS}
    if not filtered:
        return False
    filtered['updated_at'] = datetime.now().isoformat()
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("SELECT user_id FROM user_credentials WHERE user_id = ?", (user_id,))
        exists = c.fetchone()
        if exists:
            set_clause = ", ".join(f"{k} = ?" for k in filtered)
            values = list(filtered.values()) + [user_id]
            c.execute(f"UPDATE user_credentials SET {set_clause} WHERE user_id = ?", values)
        else:
            filtered['user_id'] = user_id
            cols = ", ".join(filtered.keys())
            placeholders = ", ".join("?" for _ in filtered)
            c.execute(
                f"INSERT INTO user_credentials ({cols}) VALUES ({placeholders})",
                list(filtered.values())
            )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_user_credentials_for_service(user_id: int) -> dict:
    """
    User API kalitlarini service uchun validatsiya bilan qaytarish.
    Majburiy: jira_email, jira_token, github_token, gemini_api_key_1.
    Yetishmasa → RuntimeError.
    """
    uc = get_user_credentials(user_id)

    jira_server  = (uc.get('jira_server')  or '').strip()
    jira_email   = (uc.get('jira_email')   or '').strip()
    jira_token   = (uc.get('jira_token')   or '').strip()
    github_token = (uc.get('github_token') or '').strip()
    github_org   = (uc.get('github_org')   or '').strip()
    figma_token  = (uc.get('figma_token')  or '').strip()
    gemini_k1    = (uc.get('gemini_api_key_1') or '').strip()
    gemini_k2    = (uc.get('gemini_api_key_2') or '').strip()

    missing = []
    if not jira_email:   missing.append("JIRA Email")
    if not jira_token:   missing.append("JIRA API Token")
    if not github_token: missing.append("GitHub Token")
    if not gemini_k1:    missing.append("Gemini API Key")

    if missing:
        raise RuntimeError(
            f"API kalitlar to'liq emas: {', '.join(missing)}. "
            f"Sozlamalar → API Kalitlar bo'limini to'ldiring."
        )

    return {
        'jira_server':  jira_server or 'https://yourcompany.atlassian.net',
        'jira_email':   jira_email,
        'jira_token':   jira_token,
        'github_token': github_token,
        'github_org':   github_org,
        'figma_token':  figma_token,
        'gemini_keys':  [k for k in [gemini_k1, gemini_k2] if k],
    }


def has_user_credentials_configured(user_id: int) -> bool:
    """User majburiy API kalitlarini kiritganligini tekshirish."""
    uc = get_user_credentials(user_id)
    return bool(
        uc.get('jira_email') and
        uc.get('jira_token') and
        uc.get('jira_project_keys') and
        uc.get('github_token') and
        uc.get('gemini_api_key_1')
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WEBHOOK SOZLAMALARI (KOMPANIYA DARAJASI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_company_webhook_config(company_id: int) -> Dict:
    """Kompaniyaning webhook routing sozlamalari"""
    cs = get_company_settings(company_id)
    return {
        'webhook_project_keys':        cs.get('webhook_project_keys', ''),
        'webhook_trigger_status':      cs.get('webhook_trigger_status', ''),
        'webhook_trigger_aliases':     cs.get('webhook_trigger_aliases', ''),
        'webhook_return_status':       cs.get('webhook_return_status', ''),
        'webhook_allowed_issue_types': cs.get('webhook_allowed_issue_types', ''),
        'webhook_excluded_assignees':  cs.get('webhook_excluded_assignees', ''),
        'webhook_auto_return_enabled': bool(cs.get('webhook_auto_return_enabled', 0)),
        'webhook_return_threshold':    int(cs.get('webhook_return_threshold') or 60),
    }


def validate_company_webhook_config(company_id: int) -> List[str]:
    """Webhook sozlamalarining to'liqligini tekshirish. Bo'sh ro'yxat = OK."""
    cfg = get_company_webhook_config(company_id)
    errors = []
    if not cfg.get('webhook_project_keys', '').strip():
        errors.append("JIRA Project Key(lar) kiritilishi shart (masalan: DEV, QA)")
    if not cfg.get('webhook_trigger_status', '').strip():
        errors.append("Trigger Status kiritilishi shart (masalan: Ready to Test)")
    return errors


def get_company_webhook_module_settings(company_id: int, module_key: str = None) -> Dict:
    """
    Kompaniyaning webhook Service1/Service2 sozlamalari.

    module_key='webhook_tz_pr' yoki 'webhook_testcase' yoki 'queue'.
    None bo'lsa barcha webhook modul sozlamalari qaytariladi.

    Eslatma: Bu sozlamalar webhook server'da ishlatiladi, shuning uchun
    kompaniya darajasida (shared), user darajasida emas.
    """
    cs = get_company_settings(company_id)
    raw = cs.get('webhook_module_settings', '{}')
    try:
        all_settings = json.loads(raw) if raw else {}
    except (json.JSONDecodeError, TypeError):
        all_settings = {}
    if module_key:
        return all_settings.get(module_key, {})
    return all_settings


def save_company_webhook_module_settings(company_id: int, module_key: str, data: dict) -> bool:
    """Kompaniyaning bitta webhook modul sozlamasini saqlash"""
    cs = get_company_settings(company_id)
    raw = cs.get('webhook_module_settings', '{}')
    try:
        all_settings = json.loads(raw) if raw else {}
    except (json.JSONDecodeError, TypeError):
        all_settings = {}
    all_settings[module_key] = data
    return save_company_settings(
        company_id,
        {'webhook_module_settings': json.dumps(all_settings)}
    )


def get_company_by_project_key(project_key: str) -> Optional[Dict]:
    """JIRA project key bo'yicha kompaniyani topish (webhook routing)"""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT c.*, cs.webhook_project_keys FROM companies c
            JOIN company_settings cs ON cs.company_id = c.id
            WHERE c.is_active = 1
              AND cs.webhook_project_keys != ''
        """)
        rows = c.fetchall()
        conn.close()
        key_upper = project_key.strip().upper()
        for row in rows:
            keys = [k.strip().upper() for k in (row['webhook_project_keys'] or '').split(',') if k.strip()]
            if key_upper in keys:
                return dict(row)
        return None
    except Exception:
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USER MODULE SETTINGS (STANDALONE MODULLAR — per-user izolyatsiya)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_user_module_settings(user_id: int, module_key: str = None) -> Dict:
    """
    Userning standalone modul sozlamalari.

    module_key='tz_pr_checker' yoki 'testcase_generator' yoki 'bug_analyzer' yoki 'statistics'.
    None bo'lsa barcha modul sozlamalar {module_key: {...}, ...} shaklida qaytariladi.
    """
    try:
        conn = _get_conn()
        c = conn.cursor()
        if module_key:
            c.execute(
                "SELECT settings_json FROM user_module_settings WHERE user_id = ? AND module_key = ?",
                (user_id, module_key)
            )
            row = c.fetchone()
            conn.close()
            if not row:
                return {}
            try:
                return json.loads(row['settings_json']) or {}
            except (json.JSONDecodeError, TypeError):
                return {}
        else:
            c.execute(
                "SELECT module_key, settings_json FROM user_module_settings WHERE user_id = ?",
                (user_id,)
            )
            rows = c.fetchall()
            conn.close()
            result = {}
            for r in rows:
                try:
                    result[r['module_key']] = json.loads(r['settings_json']) or {}
                except (json.JSONDecodeError, TypeError):
                    result[r['module_key']] = {}
            return result
    except Exception:
        return {}


def save_user_module_settings(user_id: int, module_key: str, data: dict) -> bool:
    """Userning bitta modul sozlamasini saqlash (upsert)"""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO user_module_settings (user_id, module_key, settings_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, module_key) DO UPDATE SET
              settings_json = excluded.settings_json,
              updated_at    = excluded.updated_at
            """,
            (user_id, module_key, json.dumps(data or {}), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DB INIT ON IMPORT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
try:
    init_auth_db()
except Exception as _e:
    pass
