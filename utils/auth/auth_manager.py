"""
Auth Manager — Login / Logout / Session

Super Admin: .env dan SUPER_ADMIN_USERNAME + SUPER_ADMIN_PASSWORD
User login:  "username@company_code" formati (masalan: olim@smartup)

Session state kalit: st.session_state['auth']
  {
    'logged_in':    bool,
    'role':         'super_admin' | 'company_admin' | 'user',
    'auth_source':  'platform_admin_db' | 'legacy_env_super_admin' | 'company_user' | None,
    'user_id':      int | None,
    'user_name':    str | None,          # "olim" (company_code siz)
    'company_id':   int | None,
    'company_code': str | None,
    'company_name': str | None,
  }

Author: JASUR TURGUNOV
"""
import os
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from utils.auth.auth_db import (
    get_user_by_full_username,
    get_company_by_id,
    get_effective_company_modules,
    SALES_READY_MODULES,
    is_company_subscription_active,
    verify_password,
    get_platform_admin_by_username,
    log_login_attempt,
    parse_username,
    validate_username_format,
    get_login_attempt_state,
    record_failed_login,
    reset_login_attempts,
    MAX_LOGIN_ATTEMPTS,
    LOCKOUT_SECONDS,
)


class _SessionRuntime:
    """Legacy session adapter without Streamlit dependency."""

    def __init__(self):
        self.session_state: dict = {}


st = _SessionRuntime()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SUPER ADMIN CREDENTIALS (.env dan)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_SUPER_USERNAME = os.getenv('SUPER_ADMIN_USERNAME')
_SUPER_PASSWORD = os.getenv('SUPER_ADMIN_PASSWORD')
_SUPER_ADMIN_CONFIGURED = bool(_SUPER_USERNAME and _SUPER_PASSWORD)
SESSION_TIMEOUT_MINUTES = max(15, int(os.getenv("APP_SESSION_TIMEOUT_MINUTES", "120") or "120"))


def _check_super_admin(username: str, password: str) -> bool:
    if not _SUPER_ADMIN_CONFIGURED:
        return False
    user_ok = secrets.compare_digest(username.strip().lower(), _SUPER_USERNAME.lower())
    pass_ok = secrets.compare_digest(password, _SUPER_PASSWORD)
    return user_ok and pass_ok


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SESSION HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_EMPTY_SESSION = {
    'logged_in': False,
    'role': None,
    'auth_source': None,
    'user_id': None,
    'user_name': None,
    'company_id': None,
    'company_code': None,
    'company_name': None,
    'session_started_at': None,
    'last_activity_at': None,
    'expires_at': None,
    'session_nonce': None,
}

_MODULE_ROLE_ACCESS = {
    'tz_pr_checker': {'company_admin', 'user'},
    'testcase_generator': {'company_admin', 'user'},
    'monitoring': {'company_admin'},
    'bug_analyzer': {'company_admin', 'user'},
    'statistics': {'company_admin', 'user'},
    'sprint_report': {'company_admin', 'user'},
    'webhook': {'company_admin'},
}


def _init_session():
    if 'auth' not in st.session_state:
        st.session_state['auth'] = dict(_EMPTY_SESSION)


def _build_authenticated_session(**overrides) -> dict:
    now = datetime.now()
    payload = dict(_EMPTY_SESSION)
    payload.update({
        'logged_in': True,
        'session_started_at': now.isoformat(),
        'last_activity_at': now.isoformat(),
        'expires_at': (now + timedelta(minutes=SESSION_TIMEOUT_MINUTES)).isoformat(),
        'session_nonce': secrets.token_urlsafe(16),
    })
    payload.update(overrides)
    return payload


def build_authenticated_session_payload(**overrides) -> dict:
    """Streamlit'dan tashqarida ham ishlatish mumkin bo'lgan auth payload builder."""
    return _build_authenticated_session(**overrides)


def apply_auth_session(auth_payload: dict | None) -> None:
    """Berilgan auth payload'ni Streamlit sessionga o'rnatish."""
    _init_session()
    st.session_state['auth'] = dict(auth_payload or _EMPTY_SESSION)


def _expire_session(reason: str = "Sessiya muddati tugadi. Qayta kiring.") -> None:
    st.session_state['auth'] = dict(_EMPTY_SESSION)
    st.session_state['login_error'] = reason
    for key in ['show_settings', 'show_monitoring', 'show_sprint_report',
                'show_company_admin', 'selected_page', 'settings_changed', 'company_modules']:
        st.session_state.pop(key, None)


def _is_session_expired(auth_state: dict | None = None, *, now: datetime | None = None) -> bool:
    state = auth_state or {}
    expires_at_raw = state.get('expires_at')
    if not state.get('logged_in') or not expires_at_raw:
        return False
    try:
        expires_at = datetime.fromisoformat(expires_at_raw)
    except Exception:
        return True
    return expires_at <= (now or datetime.now())


def touch_session() -> bool:
    _init_session()
    auth_state = st.session_state['auth']
    if not auth_state.get('logged_in'):
        return False
    if _is_session_expired(auth_state):
        _expire_session()
        return False

    now = datetime.now()
    auth_state['last_activity_at'] = now.isoformat()
    auth_state['expires_at'] = (now + timedelta(minutes=SESSION_TIMEOUT_MINUTES)).isoformat()
    return True


def is_authenticated() -> bool:
    _init_session()
    if _is_session_expired(st.session_state['auth']):
        _expire_session()
        return False
    return st.session_state['auth'].get('logged_in', False)


def is_super_admin() -> bool:
    _init_session()
    return st.session_state['auth'].get('role') == 'super_admin'


def is_user() -> bool:
    _init_session()
    return st.session_state['auth'].get('role') in {'company_admin', 'user'}


def is_company_admin() -> bool:
    _init_session()
    return st.session_state['auth'].get('role') == 'company_admin'


def can_access_monitoring() -> bool:
    _init_session()
    return st.session_state['auth'].get('role') in {'super_admin', 'company_admin'}


def can_manage_company_users() -> bool:
    _init_session()
    return st.session_state['auth'].get('role') in {'super_admin', 'company_admin'}


def can_manage_company_integrations() -> bool:
    _init_session()
    return st.session_state['auth'].get('role') in {'super_admin', 'company_admin'}


def can_manage_subscription() -> bool:
    _init_session()
    return st.session_state['auth'].get('role') == 'super_admin'


def can_manage_company_scope(company_id: int | None) -> bool:
    """Berilgan company_id joriy sessiya uchun boshqariladigan scope ichidami."""
    _init_session()
    if not company_id:
        return False

    role = st.session_state['auth'].get('role')
    if role == 'super_admin':
        return True

    session_company_id = st.session_state['auth'].get('company_id')
    return role == 'company_admin' and session_company_id == company_id


def can_access_module(module_key: str) -> bool:
    """Role + subscription + kompaniya modul ruxsati asosida access tekshiruvi."""
    _init_session()
    if module_key not in SALES_READY_MODULES:
        return False
    role = st.session_state['auth'].get('role')
    if role == 'super_admin':
        return True

    allowed_roles = _MODULE_ROLE_ACCESS.get(module_key, set())
    if role not in allowed_roles:
        return False

    company_mods = st.session_state.get('company_modules')
    if isinstance(company_mods, dict) and company_mods:
        return bool(company_mods.get(module_key, False))

    company_id = st.session_state['auth'].get('company_id')
    if not company_id:
        return False

    try:
        mods = get_effective_company_modules(company_id)
        st.session_state['company_modules'] = mods
        return bool(mods.get(module_key, False))
    except Exception:
        return False


def get_auth_info() -> dict:
    _init_session()
    return st.session_state['auth']


def get_company_id() -> int | None:
    return get_auth_info().get('company_id')


def get_company_code() -> str | None:
    return get_auth_info().get('company_code')


def get_user_id() -> int | None:
    return get_auth_info().get('user_id')


def get_user_name() -> str | None:
    """Faqat username qismi ('olim'), company_code siz"""
    return get_auth_info().get('user_name')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOGIN / LOGOUT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _lockout_message(seconds_remaining: int) -> str:
    mins = seconds_remaining // 60
    secs = seconds_remaining % 60
    return f"Hisob vaqtincha bloklangan. {mins}:{secs:02d} dan keyin urinib ko'ring."


def _attempts_left_message(failed_count: int) -> str:
    remaining = MAX_LOGIN_ATTEMPTS - failed_count
    return f" ({remaining} ta urinish qoldi)"


def authenticate_credentials(full_username: str, password: str) -> tuple[bool, str, dict | None]:
    """
    Login tekshiruvi va auth payload yaratish.

    Returns:
        (success, error_message, auth_payload)
    """
    if not full_username or not password:
        return False, "Login va parol kiritilishi shart", None

    username_clean = full_username.strip()

    platform_admin = get_platform_admin_by_username(username_clean)
    is_legacy_env_admin = bool(
        not platform_admin
        and _SUPER_USERNAME
        and username_clean.lower() == _SUPER_USERNAME.lower()
    )
    if platform_admin or is_legacy_env_admin:
        identifier = username_clean.lower()

        state = get_login_attempt_state(identifier)
        if state['is_locked']:
            log_login_attempt(identifier, success=False, reason="locked_out", role="super_admin")
            return False, _lockout_message(state['seconds_remaining']), None

        if platform_admin:
            if not platform_admin.get('is_active', 0):
                log_login_attempt(identifier, success=False, reason="inactive_platform_admin", role="super_admin")
                return False, "Super admin hisobingiz faol emas.", None
            if verify_password(password, platform_admin['password_hash']):
                reset_login_attempts(identifier)
                log_login_attempt(identifier, success=True, reason="platform_admin_login", role="super_admin")
                return True, "", build_authenticated_session_payload(
                    role='super_admin',
                    auth_source='platform_admin_db',
                    user_id=None,
                    user_name=platform_admin.get('username') or username_clean.lower(),
                    company_id=None,
                    company_code=None,
                    company_name='Super Admin',
                )
            new_state = record_failed_login(identifier)
            if new_state['is_locked']:
                log_login_attempt(identifier, success=False, reason="invalid_platform_admin_password_locked", role="super_admin")
                return False, f"Hisob {LOCKOUT_SECONDS // 60} daqiqaga bloklandi.", None
            log_login_attempt(identifier, success=False, reason="invalid_platform_admin_password", role="super_admin")
            return False, "Login yoki parol noto'g'ri." + _attempts_left_message(new_state['failed_count']), None

        if not _SUPER_ADMIN_CONFIGURED:
            log_login_attempt(identifier, success=False, reason="super_admin_not_configured", role="super_admin")
            return False, "Super admin login sozlanmagan. SUPER_ADMIN_USERNAME va SUPER_ADMIN_PASSWORD kiriting.", None

        if _check_super_admin(username_clean, password):
            reset_login_attempts(identifier)
            log_login_attempt(identifier, success=True, reason="legacy_env_super_admin_login", role="super_admin")
            return True, "", build_authenticated_session_payload(
                role='super_admin',
                auth_source='legacy_env_super_admin',
                user_id=None,
                user_name=_SUPER_USERNAME,
                company_id=None,
                company_code=None,
                company_name='Super Admin',
            )

        new_state = record_failed_login(identifier)
        if new_state['is_locked']:
            log_login_attempt(identifier, success=False, reason="invalid_super_admin_password_locked", role="super_admin")
            return False, f"Hisob {LOCKOUT_SECONDS // 60} daqiqaga bloklandi.", None
        log_login_attempt(identifier, success=False, reason="invalid_super_admin_password", role="super_admin")
        return False, "Login yoki parol noto'g'ri." + _attempts_left_message(new_state['failed_count']), None

    if not validate_username_format(username_clean):
        return False, "Login formati noto'g'ri. Masalan: olim@smartup", None

    user = get_user_by_full_username(username_clean)
    if not user:
        log_login_attempt(username_clean, success=False, reason="user_not_found", role="user")
        return False, "Foydalanuvchi topilmadi", None

    identifier = username_clean.lower()

    state = get_login_attempt_state(identifier)
    if state['is_locked']:
        log_login_attempt(identifier, success=False, reason="locked_out", user_id=user.get('id'), company_id=user.get('company_id'), role=user.get('role') or 'user')
        return False, _lockout_message(state['seconds_remaining']), None

    if not user.get('is_active', 0):
        log_login_attempt(identifier, success=False, reason="inactive_user", user_id=user.get('id'), company_id=user.get('company_id'), role=user.get('role') or 'user')
        return False, "Hisobingiz faol emas. Admin bilan bog'laning.", None

    if not verify_password(password, user['password_hash']):
        new_state = record_failed_login(identifier)
        if new_state['is_locked']:
            log_login_attempt(identifier, success=False, reason="invalid_user_password_locked", user_id=user.get('id'), company_id=user.get('company_id'), role=user.get('role') or 'user')
            return False, f"Hisob {LOCKOUT_SECONDS // 60} daqiqaga bloklandi.", None
        log_login_attempt(identifier, success=False, reason="invalid_user_password", user_id=user.get('id'), company_id=user.get('company_id'), role=user.get('role') or 'user')
        return False, "Parol noto'g'ri." + _attempts_left_message(new_state['failed_count']), None

    company = get_company_by_id(user['company_id'])
    if not company:
        log_login_attempt(identifier, success=False, reason="company_not_found", user_id=user.get('id'), company_id=user.get('company_id'), role=user.get('role') or 'user')
        return False, "Kompaniya topilmadi. Admin bilan bog'laning.", None

    if not company.get('is_active', 0):
        log_login_attempt(identifier, success=False, reason="inactive_company", user_id=user.get('id'), company_id=company.get('id'), role=user.get('role') or 'user')
        return False, "Kompaniyangiz faol emas. Admin bilan bog'laning.", None

    sub_ok, sub_msg = is_company_subscription_active(company['id'])
    if not sub_ok:
        log_login_attempt(identifier, success=False, reason="subscription_blocked", user_id=user.get('id'), company_id=company.get('id'), role=user.get('role') or 'user')
        return False, sub_msg, None

    reset_login_attempts(identifier)
    user_part, _ = parse_username(username_clean)
    log_login_attempt(identifier, success=True, reason="user_login", user_id=user.get('id'), company_id=company.get('id'), role=user.get('role') or 'user')

    return True, "", build_authenticated_session_payload(
        role=user.get('role') or 'user',
        auth_source='company_user',
        user_id=user['id'],
        user_name=user_part,
        company_id=company['id'],
        company_code=company['company_code'],
        company_name=company['company_name'],
    )


def login(full_username: str, password: str) -> tuple[bool, str]:
    """
    Tizimga kirish.

    full_username == _SUPER_USERNAME  → super admin login (.env dan tekshiradi)
    full_username == "olim@smartup"   → user login (DB dan tekshiradi)

    5 marta noto'g'ri kiritilsa → 5 daqiqa blok (DB ga saqlanadi).

    Returns:
        (success: bool, error_message: str)
    """
    _init_session()
    success, error_message, auth_payload = authenticate_credentials(full_username, password)
    if success and auth_payload:
        apply_auth_session(auth_payload)
        return True, ""
    return False, error_message


def logout():
    """Tizimdan chiqish — sessionni tozalash"""
    _init_session()
    st.session_state['auth'] = dict(_EMPTY_SESSION)
    for key in ['show_settings', 'show_monitoring', 'show_sprint_report',
                'show_company_admin',
                'selected_page', 'settings_changed', 'company_modules',
                'figma_rows', 'wh_figma_rows', 'uc_figma_rows',
                'delete_confirm_task', 'delete_success', 'delete_task_key',
                'delete_task_key_input_counter', 'custom_template', 'login_error']:
        st.session_state.pop(key, None)
