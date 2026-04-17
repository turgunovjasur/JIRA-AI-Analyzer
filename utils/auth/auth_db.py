"""
Auth Database — Kompaniyalar va sozlamalar
SQLite orqali multi-tenant auth tizimi.

Jadvallar:
  companies        — kompaniya ro'yxati (kod, nom, parol hash)
  company_settings — har kompaniyaning API kalitlari + ruxsat berilgan modullar

Author: JASUR TURGUNOV
"""
import sqlite3
import hashlib
import json
import os
import secrets
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

# Barcha mavjud modullar ro'yxati (super admin shu ro'yxatdan tanlaydi)
ALL_MODULES = {
    'bug_analyzer':       'Bug Analyzer',
    'statistics':         'Sprint Statistics',
    'tz_pr_checker':      'TZ-PR Checker',
    'testcase_generator': 'Test Case Generator',
    'monitoring':         'Monitoring Dashboard',
    'sprint_report':      'Sprint Report',
}

DEFAULT_MODULES = {k: False for k in ALL_MODULES}

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AUTH_DB_FILE = os.path.join(PROJECT_ROOT, 'data', 'auth.db')


def _ensure_dir():
    Path(os.path.dirname(AUTH_DB_FILE)).mkdir(parents=True, exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(AUTH_DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DB INIT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def init_auth_db():
    """Auth DB jadvallarini yaratish (idempotent)"""
    _ensure_dir()
    conn = _get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            company_code TEXT    UNIQUE NOT NULL,
            company_name TEXT    NOT NULL,
            password_hash TEXT   NOT NULL,
            is_active    INTEGER DEFAULT 1,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

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
            updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration: eski jadvalga enabled_modules ustunini qo'shish
    try:
        c.execute("ALTER TABLE company_settings ADD COLUMN enabled_modules TEXT DEFAULT '{}'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Ustun allaqachon mavjud

    conn.commit()
    conn.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAROL HASH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def hash_password(password: str) -> str:
    """
    Parolni xavfsiz hash qilish (pbkdf2 + random salt).
    Saqlash formati: 'salt_hex:hash_hex'
    """
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
    password: str,
    enabled_modules: Optional[Dict[str, bool]] = None
) -> Optional[Dict]:
    """
    Yangi kompaniya yaratish.

    Args:
        company_code:    Unikal kod (PEPSI)
        company_name:    To'liq nom (Pepsi Co)
        password:        Dastlabki parol
        enabled_modules: Ruxsat berilgan modullar {module_key: bool}
                         None bo'lsa barcha modullar o'chirilgan

    Returns: yaratilgan kompaniya dict yoki None (agar code allaqachon mavjud)
    """
    try:
        conn = _get_conn()
        c = conn.cursor()

        pw_hash = hash_password(password)
        c.execute(
            "INSERT INTO companies (company_code, company_name, password_hash) VALUES (?,?,?)",
            (company_code.upper(), company_name, pw_hash)
        )
        company_id = c.lastrowid

        # Modullar — faqat ruxsat berilganlari True
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

        return get_company_by_code(company_code)
    except sqlite3.IntegrityError:
        return None  # company_code allaqachon mavjud
    except Exception:
        return None


def get_company_by_code(company_code: str) -> Optional[Dict]:
    """Company code bo'yicha kompaniya topish"""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute(
            "SELECT * FROM companies WHERE company_code = ?",
            (company_code.upper(),)
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


def update_company_password(company_id: int, new_password: str) -> bool:
    """Kompaniya parolini yangilash"""
    try:
        conn = _get_conn()
        conn.execute(
            "UPDATE companies SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), company_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def delete_company(company_id: int) -> bool:
    """Kompaniyani o'chirish (cascade: settings ham o'chadi)"""
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KOMPANIYA SOZLAMALARI (API KALITLAR)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_company_settings(company_id: int) -> Dict:
    """Kompaniya API kalitlarini olish"""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM company_settings WHERE company_id = ?", (company_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return dict(row)
        return {}
    except Exception:
        return {}


def get_company_settings_by_code(company_code: str) -> Dict:
    """Company code orqali API kalitlarini olish"""
    company = get_company_by_code(company_code)
    if not company:
        return {}
    return get_company_settings(company['id'])


def get_company_modules(company_id: int) -> Dict[str, bool]:
    """
    Kompaniyaga ruxsat berilgan modullarni olish.
    Returns: {'bug_analyzer': False, 'tz_pr_checker': True, ...}
    """
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
    """
    Kompaniyaning ruxsat berilgan modullarini yangilash.
    modules: {'bug_analyzer': True, 'tz_pr_checker': True, ...}
    """
    clean = {k: bool(v) for k, v in modules.items() if k in ALL_MODULES}
    # Mavjud bo'lmagan modullarni False qilib qo'shish
    full = {**DEFAULT_MODULES, **clean}
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("SELECT company_id FROM company_settings WHERE company_id = ?", (company_id,))
        exists = c.fetchone()
        if exists:
            c.execute(
                "UPDATE company_settings SET enabled_modules = ?, updated_at = ? WHERE company_id = ?",
                (json.dumps(full), datetime.now().isoformat(), company_id)
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
    Kompaniya API kalitlarini saqlash (upsert).
    settings dict: jira_server, jira_email, jira_token,
                   github_token, github_org, figma_token,
                   gemini_api_key_1, gemini_api_key_2
    """
    allowed_keys = {
        'jira_server', 'jira_email', 'jira_token',
        'github_token', 'github_org', 'figma_token',
        'gemini_api_key_1', 'gemini_api_key_2'
    }
    filtered = {k: v for k, v in settings.items() if k in allowed_keys}
    filtered['updated_at'] = datetime.now().isoformat()

    try:
        conn = _get_conn()
        c = conn.cursor()

        # Mavjudligini tekshirish
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
    """Kompaniya majburiy API kalitlari (JIRA + GitHub + Gemini) sozlanganligini tekshirish"""
    cs = get_company_settings(company_id)
    return bool(
        cs.get('jira_email') and
        cs.get('jira_token') and
        cs.get('github_token') and
        cs.get('gemini_api_key_1')
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DB INIT ON IMPORT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
try:
    init_auth_db()
except Exception as _e:
    pass
