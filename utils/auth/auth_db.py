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
import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from core.logger import get_logger
from utils.database.runtime import connect_auth_db
from utils.auth.company_repository import (
    fetch_company_by_id,
    fetch_company_by_code,
    fetch_all_companies,
    create_company_record,
    insert_company_module_settings,
    create_default_company_subscription,
    update_company_active_flag,
    update_company_seat_limit_value,
    delete_company_by_id,
    fetch_company_subscription,
    upsert_company_subscription,
    expire_overdue_subscriptions,
    fetch_company_settings,
    fetch_company_modules,
    upsert_company_modules,
    upsert_company_settings,
    fetch_company_by_project_key,
    find_project_key_conflicts,
)
from utils.auth.user_repository import (
    count_users_in_company as repo_count_users_in_company,
    insert_user,
    fetch_user_by_id,
    fetch_user_by_id_and_company,
    fetch_user_by_full_username,
    fetch_users_by_company,
    update_user_password_hash,
    update_user_status_value,
    update_user_role_value,
    delete_user_by_id,
    fetch_user_credentials,
    upsert_user_credentials,
    fetch_user_module_settings,
    upsert_user_module_settings,
)
from utils.auth.platform_repository import (
    fetch_global_setting,
    upsert_global_setting,
    fetch_login_attempt_state,
    delete_login_attempt,
    upsert_login_attempt,
    fetch_platform_admin_by_username,
    upsert_platform_admin,
    insert_login_audit_log,
    fetch_login_audit_logs,
    insert_password_reset_token,
    fetch_password_reset_token,
    mark_password_reset_token_used,
    insert_web_session,
    fetch_web_session,
    touch_web_session,
    revoke_web_session,
    revoke_all_user_sessions,
    cleanup_expired_web_sessions,
    insert_audit_log,
)
from utils.auth.auth_bootstrap import run_auth_bootstrap
from utils.auth.auth_config_helpers import (
    build_company_gemini_keys,
    build_company_credentials,
    build_company_webhook_credentials,
    build_user_credentials_for_service,
    build_company_webhook_config,
    validate_company_webhook_config_shape,
    parse_webhook_module_settings,
)
from utils.auth.auth_subscription_helpers import (
    normalize_iso_date,
    validate_company_subscription_data as helper_validate_company_subscription_data,
    is_company_subscription_active as helper_is_company_subscription_active,
    get_effective_company_modules as helper_get_effective_company_modules,
)

log = get_logger("auth_db")

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

SALES_READY_MODULES = {
    'tz_pr_checker',
    'testcase_generator',
    'monitoring',
    'webhook',
}

DEFERRED_MODULES = set(ALL_MODULES) - SALES_READY_MODULES

# Webhook sozlamalari uchun majburiy maydonlar
WEBHOOK_REQUIRED_FIELDS = ['webhook_project_keys', 'webhook_trigger_status']

DEFAULT_MODULES = {k: False for k in ALL_MODULES}

# Default seat limit — legacy helperlar uchun 1, UI create flow esa explicit 0 yuboradi
DEFAULT_SEAT_LIMIT = 1
USER_ROLES = {'company_admin', 'user'}
SUBSCRIPTION_STATUSES = {'trial', 'active', 'past_due', 'suspended', 'cancelled'}
DEFAULT_SUBSCRIPTION_STATUS = 'trial'
DEFAULT_BILLING_MODE = 'manual'
DEFAULT_PLAN_NAME = 'base'
DEFAULT_TRIAL_DAYS = 14
SUBSCRIPTION_ACCESS_STATUSES = {'trial', 'active', 'past_due'}
ALLOWED_BILLING_MODES = {'manual'}
PLAN_INCLUDED_MODULES = {
    'base': {'tz_pr_checker', 'testcase_generator'},
}

# Login bloklash sozlamalari
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS    = 5 * 60  # 5 daqiqa
PASSWORD_RESET_TOKEN_TTL_MINUTES = max(5, int(os.getenv("APP_PASSWORD_RESET_TOKEN_TTL_MINUTES", "60") or "60"))
WEB_SESSION_TTL_MINUTES = max(
    15,
    int(
        os.getenv("APP_WEB_SESSION_TTL_MINUTES")
        or os.getenv("APP_SESSION_TIMEOUT_MINUTES")
        or "120"
    ),
)

# Username formati: "name@company_code"
# name qismi: lotin harflar, raqam, nuqta, tire, underscore
# company_code qismi: lotin harflar va raqam
_USERNAME_RE = re.compile(r'^[a-z0-9._-]+@[a-z0-9]+$')
_PLAN_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9_-]{1,31}$')


def _get_conn():
    return connect_auth_db(timeout=30)


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


def _normalize_project_keys(raw_keys: str) -> List[str]:
    """Webhook project keylarni normalize qilish."""
    return [k.strip().upper() for k in (raw_keys or '').split(',') if k.strip()]


def _find_project_key_conflicts(conn, company_id: int, project_keys: List[str]) -> List[str]:
    """Boshqa kompaniyalar bilan project key to'qnashuvlarini topish."""
    return find_project_key_conflicts(conn, company_id, project_keys, _normalize_project_keys)


def _hash_web_session_token(raw_token: str) -> str:
    return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()


def _coerce_datetime_value(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return datetime.fromisoformat(value.isoformat())
        except Exception:
            return None
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _now_matching(value: Optional[datetime]) -> datetime:
    if value is not None and value.tzinfo is not None:
        return datetime.now(tz=value.tzinfo)
    return datetime.now()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DB INIT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def init_auth_db():
    """Auth DB runtime jadvallarini yaratish (idempotent)."""
    conn = _get_conn()
    run_auth_bootstrap(
        conn,
        default_plan_name=DEFAULT_PLAN_NAME,
        default_billing_mode=DEFAULT_BILLING_MODE,
    )
    conn.close()
    seed_default_platform_admin()


def _parse_figma_tokens(raw) -> list:
    """figma_tokens JSON satrini list ga o'girish. Noto'g'ri format bo'lsa [] qaytaradi."""
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []




# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOGIN BLOKLASH (brute-force himoya)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_login_attempt_state(identifier: str) -> dict:
    """
    identifier uchun login holati.
    Returns: {failed_count, is_locked, seconds_remaining}
    """
    try:
        row = fetch_login_attempt_state(_get_conn, identifier)
        if not row:
            return {'failed_count': 0, 'is_locked': False, 'seconds_remaining': 0}
        locked_until = row.get('locked_until')
        if locked_until:
            locked_dt = _coerce_datetime_value(locked_until)
            if locked_dt is None:
                delete_login_attempt(_get_conn, identifier)
                return {'failed_count': 0, 'is_locked': False, 'seconds_remaining': 0}
            now = _now_matching(locked_dt)
            if now < locked_dt:
                remaining = int((locked_dt - now).total_seconds())
                return {'failed_count': row['failed_count'], 'is_locked': True, 'seconds_remaining': remaining}
            # Blok muddati o'tgan — tozalash
            delete_login_attempt(_get_conn, identifier)
        return {'failed_count': row['failed_count'], 'is_locked': False, 'seconds_remaining': 0}
    except Exception:
        return {'failed_count': 0, 'is_locked': False, 'seconds_remaining': 0}


def record_failed_login(identifier: str) -> dict:
    """
    Muvaffaqiyatsiz urinishni qayd qilish.
    MAX_LOGIN_ATTEMPTS ga yetganda LOCKOUT_SECONDS muddatga bloklaydi.
    Returns: {failed_count, is_locked, seconds_remaining}
    """
    try:
        row = fetch_login_attempt_state(_get_conn, identifier)
        new_count = (row['failed_count'] + 1) if row else 1
        locked_until = None
        if new_count >= MAX_LOGIN_ATTEMPTS:
            locked_until = (datetime.now() + timedelta(seconds=LOCKOUT_SECONDS)).isoformat()
        upsert_login_attempt(_get_conn, identifier, new_count, locked_until)
        is_locked = locked_until is not None
        return {
            'failed_count':      new_count,
            'is_locked':         is_locked,
            'seconds_remaining': LOCKOUT_SECONDS if is_locked else 0,
        }
    except Exception:
        return {'failed_count': 0, 'is_locked': False, 'seconds_remaining': 0}


def reset_login_attempts(identifier: str):
    """Muvaffaqiyatli logindan keyin urinishlar hisobini tiklash."""
    delete_login_attempt(_get_conn, identifier)


def log_login_attempt(
    identifier: str,
    *,
    success: bool,
    reason: str = "",
    user_id: int | None = None,
    company_id: int | None = None,
    role: str = "",
) -> bool:
    return insert_login_audit_log(
        _get_conn,
        identifier=identifier,
        success=success,
        reason=reason,
        user_id=user_id,
        company_id=company_id,
        role=role,
    )


def get_recent_login_audit_logs(
    limit: int = 50,
    *,
    success: bool | None = None,
    identifier_contains: str = "",
) -> List[Dict]:
    return fetch_login_audit_logs(
        _get_conn,
        limit=limit,
        success=success,
        identifier_contains=identifier_contains,
    )


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


def _hash_password_reset_token(raw_token: str) -> str:
    return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()


def get_platform_admin_by_username(username: str) -> Optional[Dict]:
    """DB ichidagi platform super adminni olish."""
    if not username:
        return None
    return fetch_platform_admin_by_username(_get_conn, username)


def save_platform_admin(username: str, password: str, is_active: bool = True) -> bool:
    """Platform super adminni DB'ga saqlash."""
    clean_username = (username or "").strip().lower()
    if not clean_username or not password:
        return False
    return upsert_platform_admin(_get_conn, clean_username, hash_password(password), is_active)


def seed_default_platform_admin() -> bool:
    """
    Legacy `.env` super adminni DB platform_admins jadvaliga seed qilish.

    Bu transition qadam sifatida env-based loginni DB-based modelga yaqinlashtiradi.
    """
    username = (os.getenv("SUPER_ADMIN_USERNAME") or "").strip().lower()
    password = os.getenv("SUPER_ADMIN_PASSWORD") or ""
    if not username or not password:
        return False

    existing = get_platform_admin_by_username(username)
    if existing:
        return True

    return save_platform_admin(username, password, is_active=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GLOBAL SETTINGS (super admin tomonidan belgilanadi)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_global_setting(key: str, default: str = '') -> str:
    """Global sozlamadan qiymat olish."""
    return fetch_global_setting(_get_conn, key, default)


def set_global_setting(key: str, value: str) -> bool:
    """Global sozlamani saqlash (upsert)."""
    return upsert_global_setting(_get_conn, key, value)


def get_global_gemini_defaults() -> dict:
    """Super admin tomonidan belgilangan global Gemini default sozlamalar."""
    return {
        'api_key_1': get_global_setting('gemini_default_api_key_1'),
        'api_key_2': get_global_setting('gemini_default_api_key_2'),
        'model':     get_global_setting('gemini_default_model'),
        'fallback_model': get_global_setting('gemini_default_fallback_model', 'gemini-2.5-flash'),
        'agent1_primary_model': get_global_setting('checker_agent1_primary_model', 'gemini-2.5-flash'),
        'agent1_fallback_model': get_global_setting('checker_agent1_fallback_model', 'gemini-2.5-flash'),
        'agent2_primary_model': get_global_setting('checker_agent2_primary_model', 'gemini-2.5-pro'),
        'agent2_fallback_model': get_global_setting('checker_agent2_fallback_model', 'gemini-2.5-flash'),
        'agent3_primary_model': get_global_setting('checker_agent3_primary_model', 'gemini-2.5-flash'),
        'agent3_fallback_model': get_global_setting('checker_agent3_fallback_model', 'gemini-2.5-flash'),
    }


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
        seat_limit:      Qo'shimcha userlar chegarasi (company admin bundan tashqari)
        enabled_modules: Ruxsat berilgan modullar {module_key: bool}

    Returns: yaratilgan kompaniya dict yoki None (code allaqachon mavjud).
    """
    try:
        code_lower = company_code.strip().lower()
        company_id = create_company_record(_get_conn, code_lower, company_name.strip(), seat_limit)
        if not company_id:
            log.warning(
                f"create_company failed at create_company_record | code={code_lower} | "
                f"name={company_name.strip()} | seat_limit={seat_limit}"
            )
            return None

        mods = {**DEFAULT_MODULES}
        if enabled_modules:
            for k, v in enabled_modules.items():
                if k in mods:
                    mods[k] = bool(v)

        if not insert_company_module_settings(_get_conn, company_id, json.dumps(mods)):
            log.error(
                f"create_company failed at insert_company_module_settings | "
                f"company_id={company_id} | code={code_lower}"
            )
            delete_company_by_id(_get_conn, company_id)
            return None

        if not create_default_company_subscription(
            _get_conn,
            company_id,
            DEFAULT_PLAN_NAME,
            DEFAULT_SUBSCRIPTION_STATUS,
            DEFAULT_BILLING_MODE,
            DEFAULT_TRIAL_DAYS,
        ):
            log.error(
                f"create_company failed at create_default_company_subscription | "
                f"company_id={company_id} | code={code_lower}"
            )
            delete_company_by_id(_get_conn, company_id)
            return None
        log.info(
            f"create_company success | company_id={company_id} | code={code_lower} | "
            f"seat_limit={max(0, int(seat_limit))} | webhook={bool(mods.get('webhook'))}"
        )
        return get_company_by_code(code_lower)
    except Exception as exc:
        log.error(
            f"create_company unexpected error | code={company_code.strip().lower()} | "
            f"name={company_name.strip()} | seat_limit={seat_limit} | err={exc}",
            exc_info=True,
        )
        return None


def get_company_by_code(company_code: str) -> Optional[Dict]:
    """Company code bo'yicha kompaniya topish (case-insensitive)"""
    return fetch_company_by_code(_get_conn, company_code)


def get_company_by_id(company_id: int) -> Optional[Dict]:
    """ID bo'yicha kompaniya topish"""
    return fetch_company_by_id(_get_conn, company_id)


def get_all_companies() -> List[Dict]:
    """Barcha kompaniyalar ro'yxati"""
    return fetch_all_companies(_get_conn)


def get_company_subscription(company_id: int) -> Dict:
    """Kompaniya subscription ma'lumotlarini olish."""
    return fetch_company_subscription(_get_conn, company_id)


def _normalize_iso_date(value: Any) -> tuple[str, Optional[datetime.date], str]:
    """YYYY-MM-DD sanani normalize qilish."""
    return normalize_iso_date(value)


def validate_company_subscription_data(data: Dict) -> tuple[bool, str, Dict]:
    """Subscription payloadni normalize va validate qilish."""
    return helper_validate_company_subscription_data(
        data,
        _PLAN_NAME_RE,
        SUBSCRIPTION_STATUSES,
        ALLOWED_BILLING_MODES,
        DEFAULT_BILLING_MODE,
    )


def save_company_subscription(company_id: int, data: Dict) -> bool:
    """Kompaniya subscription ma'lumotlarini saqlash."""
    allowed_keys = {
        'plan_name', 'subscription_status', 'billing_mode',
        'billing_start_date', 'billing_end_date', 'next_payment_date',
        'last_payment_date', 'last_payment_note',
    }
    filtered = {k: (v or '') for k, v in data.items() if k in allowed_keys}
    is_valid, _, normalized = validate_company_subscription_data(filtered)
    if not is_valid:
        return False
    return upsert_company_subscription(_get_conn, company_id, normalized)


def is_company_subscription_active(company_id: int) -> tuple[bool, str]:
    """Subscription holati bo'yicha login ruxsatini tekshirish."""
    return helper_is_company_subscription_active(get_company_subscription(company_id))


def expire_overdue_company_subscriptions() -> int:
    """billing_end_date o'tgan trial/active obunalarni suspended ga o'tkazadi. Worker cron uchun."""
    return expire_overdue_subscriptions(_get_conn)


def update_company_status(company_id: int, is_active: bool) -> bool:
    """Kompaniyani faollashtirish/o'chirish"""
    return update_company_active_flag(_get_conn, company_id, is_active)


def update_company_seat_limit(company_id: int, seat_limit: int) -> bool:
    """Kompaniyaning qo'shimcha userlar chegarasini yangilash. Min 0."""
    return update_company_seat_limit_value(_get_conn, company_id, seat_limit)


def delete_company(company_id: int) -> bool:
    """Kompaniyani o'chirish (cascade: users, settings, module_settings ham o'chadi)"""
    return delete_company_by_id(_get_conn, company_id)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USER CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def count_users_in_company(company_id: int) -> int:
    """Kompaniyadagi qo'shimcha `user`lar soni (company admin hisobga olinmaydi)."""
    return repo_count_users_in_company(_get_conn, company_id)


def create_user(
    company_id: int,
    name: str,
    password: str,
    role: str = 'user',
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Kompaniyaga yangi user qo'shish.

    Args:
        company_id: Kompaniya ID si
        name:       User nomi (@ belgidan oldingi qism, masalan 'olim')
        password:   Dastlabki parol
        role:       company_admin yoki user

    Returns:
        (user_dict, None) — muvaffaqiyatli
        (None, error_message) — xato (seat limit to'lgan / user mavjud / noto'g'ri format)
    """
    company = get_company_by_id(company_id)
    if not company:
        return None, "Kompaniya topilmadi"

    clean_role = (role or 'user').strip().lower()
    if clean_role not in USER_ROLES:
        return None, f"Noto'g'ri role: '{role}'"

    # Seat limit tekshiruvi
    current_count = count_users_in_company(company_id)
    raw_seat_limit = company.get('seat_limit')
    seat_limit = max(0, int(DEFAULT_SEAT_LIMIT if raw_seat_limit is None else raw_seat_limit))
    if clean_role == 'user' and current_count >= seat_limit:
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

    user_id, error = insert_user(
        _get_conn,
        company_id,
        full_username,
        hash_password(password),
        clean_role,
    )
    if not user_id:
        return None, error
    return get_user_by_id(user_id), None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """ID bo'yicha user"""
    return fetch_user_by_id(_get_conn, user_id)


def get_user_by_id_and_company(user_id: int, company_id: int) -> Optional[Dict]:
    """User aynan shu kompaniyaga tegishli ekanini tekshirib qaytarish."""
    return fetch_user_by_id_and_company(_get_conn, user_id, company_id)


def get_user_by_full_username(full_username: str) -> Optional[Dict]:
    """'olim@smartup' bo'yicha user topish (case-insensitive)"""
    if not validate_username_format(full_username):
        return None
    return fetch_user_by_full_username(_get_conn, full_username)


def get_users_by_company(company_id: int) -> List[Dict]:
    """Kompaniyadagi barcha userlar ro'yxati"""
    return fetch_users_by_company(_get_conn, company_id)


def update_user_password(user_id: int, new_password: str) -> bool:
    """Userning parolini yangilash va barcha aktiv sessiyalarini bekor qilish."""
    ok = update_user_password_hash(_get_conn, user_id, hash_password(new_password))
    if ok:
        revoke_all_user_sessions(_get_conn, user_id)
    return ok


def update_user_password_for_company(user_id: int, company_id: int, new_password: str) -> bool:
    """Faqat ko'rsatilgan kompaniyaga tegishli user parolini yangilash."""
    target_user = get_user_by_id_and_company(user_id, company_id)
    if not target_user:
        return False
    return update_user_password(user_id, new_password)


def create_password_reset_token(user_id: int, *, ttl_minutes: int | None = None) -> Optional[Dict]:
    """User uchun bir martalik password reset token yaratish."""
    user = get_user_by_id(user_id)
    if not user or not user.get("is_active", 0):
        return None

    clean_ttl = max(5, int(ttl_minutes or PASSWORD_RESET_TOKEN_TTL_MINUTES))
    raw_token = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(minutes=clean_ttl)).isoformat()
    token_hash = _hash_password_reset_token(raw_token)

    if not insert_password_reset_token(
        _get_conn,
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    ):
        return None

    return {
        "token": raw_token,
        "expires_at": expires_at,
        "user_id": user_id,
    }


def create_password_reset_token_for_username(full_username: str, *, ttl_minutes: int | None = None) -> Optional[Dict]:
    """Username orqali password reset token yaratish."""
    user = get_user_by_full_username(full_username)
    if not user:
        return None
    return create_password_reset_token(user["id"], ttl_minutes=ttl_minutes)


def request_password_reset_email(username: str) -> bool:
    """Username bo'yicha reset token yaratib, user emailiga yuboradi.
    Email topilmasa yoki SMTP sozlanmagan bo'lsa False qaytaradi.
    Xavfsizlik: user mavjud emas bo'lsa ham True qaytaradi (timing attack himoyasi).
    """
    from utils.email.email_sender import send_password_reset_email, is_email_configured
    if not is_email_configured():
        return False
    user = get_user_by_full_username(username)
    if not user or not user.get("is_active"):
        return True  # timing attack himoyasi — xato xabar bermaydi
    email = (user.get("email") or "").strip()
    if not email:
        return False
    token_data = create_password_reset_token(user["id"], ttl_minutes=30)
    if not token_data:
        return False
    return send_password_reset_email(email, username, token_data["token"])


def consume_password_reset_token(raw_token: str, new_password: str) -> bool:
    """Password reset token orqali user parolini yangilash."""
    if not raw_token or not new_password:
        return False

    token_hash = _hash_password_reset_token(raw_token)
    row = fetch_password_reset_token(_get_conn, token_hash)
    if not row or row.get("used_at"):
        return False

    expires_at_raw = row.get("expires_at") or ""
    expires_at = _coerce_datetime_value(expires_at_raw)
    if expires_at is None:
        return False
    if expires_at <= _now_matching(expires_at):
        return False

    user = get_user_by_id(int(row["user_id"]))
    if not user or not user.get("is_active", 0):
        return False

    if not update_user_password(int(row["user_id"]), new_password):
        return False
    return mark_password_reset_token_used(_get_conn, token_hash)


def create_web_session(
    auth_payload: Dict,
    company_modules: Dict[str, bool] | None = None,
    *,
    ttl_minutes: int | None = None,
) -> Optional[Dict]:
    """Backend-managed web sessiya yaratish."""
    if not auth_payload or not auth_payload.get("logged_in"):
        return None

    now = _now_matching(None)
    expires_at = now + timedelta(minutes=max(15, int(ttl_minutes or WEB_SESSION_TTL_MINUTES)))
    normalized_auth = dict(auth_payload)
    normalized_auth["last_activity_at"] = now.isoformat()
    normalized_auth["expires_at"] = expires_at.isoformat()
    company_modules = company_modules or {}

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_web_session_token(raw_token)
    ok = insert_web_session(
        _get_conn,
        session_token_hash=token_hash,
        auth_payload=json.dumps(normalized_auth),
        company_modules=json.dumps(company_modules),
        expires_at=expires_at.isoformat(),
        role=(normalized_auth.get("role") or ""),
        user_id=normalized_auth.get("user_id"),
        company_id=normalized_auth.get("company_id"),
    )
    if not ok:
        return None

    return {
        "session_token": raw_token,
        "expires_at": expires_at.isoformat(),
        "auth": normalized_auth,
        "company_modules": company_modules,
    }


def get_web_session(raw_token: str, *, touch: bool = True) -> Optional[Dict]:
    """Sessiyani token orqali topish va ixtiyoriy ravishda expiry'ni yangilash."""
    if not raw_token:
        return None

    row = fetch_web_session(_get_conn, _hash_web_session_token(raw_token))
    if not row or row.get("revoked_at"):
        return None

    expires_at_raw = row.get("expires_at") or ""
    expires_at = _coerce_datetime_value(expires_at_raw)
    if expires_at is None:
        return None
    now = _now_matching(expires_at)
    if expires_at <= now:
        revoke_web_session_token(raw_token)
        return None

    try:
        auth_payload = json.loads(row.get("auth_payload") or "{}")
    except Exception:
        auth_payload = {}
    try:
        company_modules = json.loads(row.get("company_modules") or "{}")
    except Exception:
        company_modules = {}

    if touch:
        now = _now_matching(expires_at)
        refreshed_expires_at = now + timedelta(minutes=WEB_SESSION_TTL_MINUTES)
        auth_payload["last_activity_at"] = now.isoformat()
        auth_payload["expires_at"] = refreshed_expires_at.isoformat()
        touch_web_session(
            _get_conn,
            _hash_web_session_token(raw_token),
            auth_payload=json.dumps(auth_payload),
            expires_at=refreshed_expires_at.isoformat(),
            last_seen_at=now.isoformat(),
        )
        expires_at = refreshed_expires_at

    return {
        "auth": auth_payload,
        "company_modules": company_modules,
        "expires_at": expires_at.isoformat(),
        "user_id": row.get("user_id"),
        "company_id": row.get("company_id"),
        "role": row.get("role"),
    }


def revoke_web_session_token(raw_token: str) -> bool:
    """Sessiyani revoke qilish."""
    if not raw_token:
        return False
    return revoke_web_session(_get_conn, _hash_web_session_token(raw_token))


def cleanup_expired_sessions() -> int:
    """Muddati o'tgan va bekor qilingan sessiyalarni DB'dan tozalash."""
    return cleanup_expired_web_sessions(_get_conn)


def write_audit_log(
    *,
    event_type: str,
    entity_type: str,
    entity_id: str = "",
    company_id: int | None = None,
    actor_user_id: int | None = None,
    actor_role: str = "",
    event_payload: dict | None = None,
) -> bool:
    """audit_logs jadvaliga yozish."""
    return insert_audit_log(
        _get_conn,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        company_id=company_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        event_payload=event_payload,
    )


def update_user_status(user_id: int, is_active: bool) -> bool:
    """Userni faollashtirish/o'chirish"""
    return update_user_status_value(_get_conn, user_id, is_active)


def update_user_status_for_company(user_id: int, company_id: int, is_active: bool) -> bool:
    """Faqat ko'rsatilgan kompaniyaga tegishli user statusini o'zgartirish."""
    target_user = get_user_by_id_and_company(user_id, company_id)
    if not target_user or target_user.get('role') == 'company_admin':
        return False
    return update_user_status(user_id, is_active)


def update_user_role(user_id: int, role: str) -> bool:
    """User rolini yangilash."""
    clean_role = (role or '').strip().lower()
    if clean_role not in USER_ROLES:
        return False
    return update_user_role_value(_get_conn, user_id, clean_role)


def delete_user(user_id: int) -> bool:
    """Userni o'chirish (cascade: user_module_settings ham o'chadi)"""
    return delete_user_by_id(_get_conn, user_id)


def delete_user_for_company(user_id: int, company_id: int) -> bool:
    """Faqat ko'rsatilgan kompaniyaga tegishli oddiy userni o'chirish."""
    target_user = get_user_by_id_and_company(user_id, company_id)
    if not target_user or target_user.get('role') == 'company_admin':
        return False
    return delete_user(user_id)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KOMPANIYA SOZLAMALARI (API KALITLAR + WEBHOOK + MODULLAR)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_company_settings(company_id: int) -> Dict:
    """Kompaniya sozlamalarini olish (API keys + webhook + enabled_modules)"""
    return fetch_company_settings(_get_conn, company_id)


def get_company_settings_by_code(company_code: str) -> Dict:
    """Company code orqali API kalitlarini olish (backward-compat shim)"""
    company = get_company_by_code(company_code)
    if not company:
        return {}
    return get_company_settings(company['id'])


def get_company_modules(company_id: int) -> Dict[str, bool]:
    """Kompaniyaga ruxsat berilgan modullar: {'tz_pr_checker': True, ...}"""
    return fetch_company_modules(_get_conn, company_id, DEFAULT_MODULES)


def get_effective_company_modules(company_id: int) -> Dict[str, bool]:
    """
    Kompaniyaning amaldagi modul ruxsatlari.

    `enabled_modules` ichidagi pullik modullar saqlanadi, lekin plan ichidagi
    bazaviy modullar subscription holatiga qarab avtomatik qo'shiladi.
    """
    return helper_get_effective_company_modules(
        get_company_modules(company_id),
        get_company_subscription(company_id),
        SUBSCRIPTION_ACCESS_STATUSES,
        DEFAULT_PLAN_NAME,
        PLAN_INCLUDED_MODULES,
    )


def save_company_modules(company_id: int, modules: Dict[str, bool]) -> bool:
    """Kompaniyaning ruxsat berilgan modullarini yangilash"""
    clean = {k: bool(v) for k, v in modules.items() if k in ALL_MODULES}
    return upsert_company_modules(_get_conn, company_id, clean, DEFAULT_MODULES)


def save_company_settings(company_id: int, settings: Dict) -> bool:
    """
    Kompaniya sozlamalarini saqlash (upsert).
    Ruxsat etilgan kalitlar: API keys, webhook_*, webhook_module_settings.
    """
    allowed_keys = {
        'jira_server', 'jira_email', 'jira_token', 'jira_project_keys',
        'github_token', 'github_org', 'figma_token', 'figma_tokens',
        'gemini_api_key_1', 'gemini_api_key_2', 'gemini_model',
        'webhook_jira_server', 'webhook_jira_email', 'webhook_jira_token',
        'webhook_github_token', 'webhook_github_org',
        'webhook_figma_token', 'webhook_figma_tokens',
        'webhook_gemini_api_key_1', 'webhook_gemini_api_key_2', 'webhook_gemini_model',
        'webhook_project_keys', 'webhook_trigger_status', 'webhook_trigger_aliases',
        'webhook_return_status', 'webhook_allowed_issue_types', 'webhook_excluded_assignees',
        'webhook_auto_return_enabled', 'webhook_return_threshold',
        'webhook_module_settings',
    }
    filtered = {k: v for k, v in settings.items() if k in allowed_keys}
    return upsert_company_settings(
        _get_conn,
        company_id,
        filtered,
        _find_project_key_conflicts,
        _normalize_project_keys,
    )


def debug_company_settings_save(company_id: int, settings: Dict) -> List[str]:
    """
    Company settings save yiqilganda ehtimoliy sabablarni qaytaradi.
    UI debug uchun ishlatiladi.
    """
    allowed_keys = {
        'jira_server', 'jira_email', 'jira_token', 'jira_project_keys',
        'github_token', 'github_org', 'figma_token', 'figma_tokens',
        'gemini_api_key_1', 'gemini_api_key_2', 'gemini_model',
        'webhook_jira_server', 'webhook_jira_email', 'webhook_jira_token',
        'webhook_github_token', 'webhook_github_org',
        'webhook_figma_token', 'webhook_figma_tokens',
        'webhook_gemini_api_key_1', 'webhook_gemini_api_key_2', 'webhook_gemini_model',
        'webhook_project_keys', 'webhook_trigger_status', 'webhook_trigger_aliases',
        'webhook_return_status', 'webhook_allowed_issue_types', 'webhook_excluded_assignees',
        'webhook_auto_return_enabled', 'webhook_return_threshold',
        'webhook_module_settings',
    }
    filtered = {k: v for k, v in settings.items() if k in allowed_keys}
    reasons: List[str] = []

    if not filtered:
        reasons.append("Saqlash uchun ruxsat etilgan maydon topilmadi.")
        return reasons

    try:
        from utils.auth.credential_crypto import can_encrypt_credentials, payload_requires_encryption

        if payload_requires_encryption(filtered) and not can_encrypt_credentials():
            reasons.append("Credential encryption tayyor emas yoki master key sozlanmagan.")

    except Exception as exc:
        reasons.append(f"Debug tekshiruv ham xato berdi: {exc}")

    if not reasons:
        reasons.append("Repository qatlamida noma'lum xato qaytdi. DB log yoki repository exception kerak.")
    return reasons


def has_api_keys_configured(company_id: int) -> bool:
    """Kompaniya majburiy API kalitlari sozlanganligini tekshirish"""
    cs = get_company_settings(company_id)
    global_defaults = get_global_gemini_defaults() or {}
    has_company_or_global_gemini = bool(
        cs.get('gemini_api_key_1')
        or cs.get('gemini_api_key_2')
        or global_defaults.get('api_key_1')
        or global_defaults.get('api_key_2')
    )
    return bool(
        cs.get('jira_server') and
        cs.get('jira_email') and
        cs.get('jira_token') and
        cs.get('github_token') and
        cs.get('github_org') and
        has_company_or_global_gemini
    )


def get_company_gemini_keys(company_id: int) -> list:
    """Kompaniyaning Gemini API kalitlari ro'yxati"""
    return build_company_gemini_keys(get_company_settings(company_id))


def get_company_credentials(company_id: int) -> dict:
    """
    Kompaniyaning barcha API kredensiallarini yuklash va validatsiya qilish.

    Agar majburiy kalit(lar) kiritilmagan bo'lsa → RuntimeError.
    Gemini kaliti bo'lmasa company -> global default tartibi ishlatiladi.
    """
    return build_company_credentials(
        company_id,
        get_company_settings(company_id),
        _parse_figma_tokens,
        get_global_gemini_defaults,
    )


def get_company_webhook_credentials(company_id: int) -> dict:
    """
    Webhook servislari uchun kompaniyaning alohida API kredensiallari.

    Yangi `webhook_*` maydonlari birinchi o'rinda ishlatiladi, kerak bo'lsa
    eski shared company credentiallarga fallback qilinadi.
    """
    return build_company_webhook_credentials(
        company_id,
        get_company_settings(company_id),
        _parse_figma_tokens,
        get_global_gemini_defaults,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USER CREDENTIALS (UI MODULLAR UCHUN)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_USER_CRED_FIELDS = {
    'jira_server', 'jira_email', 'jira_token', 'jira_project_keys',
    'github_token', 'github_org', 'figma_token', 'figma_tokens',
    'gemini_api_key_1', 'gemini_api_key_2', 'gemini_model',
}


def get_user_credentials(user_id: int) -> Dict:
    """User o'z UI modul API kalitlarini olish."""
    return fetch_user_credentials(_get_conn, user_id)


def save_user_credentials(user_id: int, data: Dict) -> bool:
    """User API kalitlarini saqlash (INSERT OR REPLACE)."""
    filtered = {k: v for k, v in data.items() if k in _USER_CRED_FIELDS}
    return upsert_user_credentials(_get_conn, user_id, filtered)


def get_user_credentials_for_service(user_id: int) -> dict:
    """
    User API kalitlarini service uchun validatsiya bilan qaytarish.
    Majburiy (company/admin): jira_server, jira_email, jira_token, github_token, github_org.
    Gemini: user kaliti bo'lmasa → company admin shared kaliti → super admin global default.
    Yetishmasa → RuntimeError.
    """
    return build_user_credentials_for_service(
        user_id,
        get_user_credentials(user_id),
        _parse_figma_tokens,
        get_global_gemini_defaults,
        get_user_by_id,
        get_company_settings,
    )


def has_user_credentials_configured(user_id: int) -> bool:
    """User modullardan foydalanishi uchun company (admin) credentiallar tayyormi."""
    user_row = get_user_by_id(user_id)
    if not user_row:
        return False
    cs = get_company_settings(user_row['company_id'])
    uc = get_user_credentials(user_id)
    global_defaults = get_global_gemini_defaults() or {}
    has_gemini = bool(
        (uc.get('gemini_api_key_1') or '').strip()
        or (uc.get('gemini_api_key_2') or '').strip()
        or (cs.get('gemini_api_key_1') or '').strip()
        or (cs.get('gemini_api_key_2') or '').strip()
        or (global_defaults.get('api_key_1') or '').strip()
        or (global_defaults.get('api_key_2') or '').strip()
    )
    return bool(
        cs.get('jira_server') and
        cs.get('jira_email') and
        cs.get('jira_token') and
        cs.get('github_token') and
        cs.get('github_org') and
        has_gemini
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WEBHOOK SOZLAMALARI (KOMPANIYA DARAJASI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_company_webhook_config(company_id: int) -> Dict:
    """Kompaniyaning webhook routing sozlamalari"""
    return build_company_webhook_config(get_company_settings(company_id))


def validate_company_webhook_config(company_id: int) -> List[str]:
    """Webhook sozlamalarining to'liqligini tekshirish. Bo'sh ro'yxat = OK."""
    return validate_company_webhook_config_shape(get_company_webhook_config(company_id))


def get_company_webhook_module_settings(company_id: int, module_key: str = None) -> Dict:
    """
    Kompaniyaning webhook Service1/Service2 sozlamalari.

    module_key='webhook_tz_pr' yoki 'webhook_testcase' yoki 'queue'.
    None bo'lsa barcha webhook modul sozlamalari qaytariladi.

    Eslatma: Bu sozlamalar webhook server'da ishlatiladi, shuning uchun
    kompaniya darajasida (shared), user darajasida emas.
    """
    cs = get_company_settings(company_id)
    return parse_webhook_module_settings(cs.get('webhook_module_settings', '{}'), module_key)


def save_company_webhook_module_settings(company_id: int, module_key: str, data: dict) -> bool:
    """Kompaniyaning bitta webhook modul sozlamasini saqlash"""
    cs = get_company_settings(company_id)
    all_settings = parse_webhook_module_settings(cs.get('webhook_module_settings', '{}'))
    all_settings[module_key] = data
    return save_company_settings(
        company_id,
        {'webhook_module_settings': json.dumps(all_settings)}
    )


def get_company_by_project_key(project_key: str) -> Optional[Dict]:
    """JIRA project key bo'yicha kompaniyani topish (webhook routing)"""
    return fetch_company_by_project_key(_get_conn, project_key, _normalize_project_keys)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USER MODULE SETTINGS (STANDALONE MODULLAR — per-user izolyatsiya)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_user_module_settings(user_id: int, module_key: str = None) -> Dict:
    """
    Userning standalone modul sozlamalari.

    module_key='tz_pr_checker' yoki 'testcase_generator' yoki 'bug_analyzer' yoki 'statistics'.
    None bo'lsa barcha modul sozlamalar {module_key: {...}, ...} shaklida qaytariladi.
    """
    return fetch_user_module_settings(_get_conn, user_id, module_key)


def save_user_module_settings(user_id: int, module_key: str, data: dict) -> bool:
    """Userning bitta modul sozlamasini saqlash (upsert)"""
    return upsert_user_module_settings(_get_conn, user_id, module_key, data)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DB INIT ON IMPORT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
try:
    init_auth_db()
except Exception as _e:
    pass
