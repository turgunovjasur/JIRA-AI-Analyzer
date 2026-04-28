"""
Auth Manager — Login / Logout / Session

Super Admin: .env dan SUPER_ADMIN_USERNAME + SUPER_ADMIN_PASSWORD
User login:  "username@company_code" formati (masalan: olim@smartup)

Session state kalit: st.session_state['auth']
  {
    'logged_in':    bool,
    'role':         'super_admin' | 'user',
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
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from utils.auth.auth_db import (
    get_user_by_full_username,
    get_company_by_id,
    verify_password,
    parse_username,
    validate_username_format,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SUPER ADMIN CREDENTIALS (.env dan)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_SUPER_USERNAME = os.getenv('SUPER_ADMIN_USERNAME', 'superadmin')
_SUPER_PASSWORD = os.getenv('SUPER_ADMIN_PASSWORD', 'admin123')


def _check_super_admin(username: str, password: str) -> bool:
    user_ok = secrets.compare_digest(username.strip().lower(), _SUPER_USERNAME.lower())
    pass_ok = secrets.compare_digest(password, _SUPER_PASSWORD)
    return user_ok and pass_ok


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SESSION HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_EMPTY_SESSION = {
    'logged_in': False,
    'role': None,
    'user_id': None,
    'user_name': None,
    'company_id': None,
    'company_code': None,
    'company_name': None,
}


def _init_session():
    if 'auth' not in st.session_state:
        st.session_state['auth'] = dict(_EMPTY_SESSION)


def is_authenticated() -> bool:
    _init_session()
    return st.session_state['auth'].get('logged_in', False)


def is_super_admin() -> bool:
    _init_session()
    return st.session_state['auth'].get('role') == 'super_admin'


def is_user() -> bool:
    _init_session()
    return st.session_state['auth'].get('role') == 'user'


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

def login(full_username: str, password: str) -> tuple[bool, str]:
    """
    Tizimga kirish.

    full_username == _SUPER_USERNAME  → super admin login (.env dan tekshiradi)
    full_username == "olim@smartup"   → user login (DB dan tekshiradi)

    Returns:
        (success: bool, error_message: str)
    """
    _init_session()

    if not full_username or not password:
        return False, "Login va parol kiritilishi shart"

    username_clean = full_username.strip()

    # Super admin tekshiruvi (@ belgisi bo'lmagan holat)
    if username_clean.lower() == _SUPER_USERNAME.lower():
        if _check_super_admin(username_clean, password):
            st.session_state['auth'] = {
                'logged_in': True,
                'role': 'super_admin',
                'user_id': None,
                'user_name': _SUPER_USERNAME,
                'company_id': None,
                'company_code': None,
                'company_name': 'Super Admin',
            }
            return True, ""
        return False, "Login yoki parol noto'g'ri"

    # User login: "olim@smartup" formati tekshirish
    if not validate_username_format(username_clean):
        return False, "Login formati noto'g'ri. Masalan: olim@smartup"

    user = get_user_by_full_username(username_clean)
    if not user:
        return False, "Foydalanuvchi topilmadi"

    if not user.get('is_active', 0):
        return False, "Hisobingiz faol emas. Admin bilan bog'laning."

    if not verify_password(password, user['password_hash']):
        return False, "Parol noto'g'ri"

    # Kompaniya ma'lumotlarini yuklash
    company = get_company_by_id(user['company_id'])
    if not company:
        return False, "Kompaniya topilmadi. Admin bilan bog'laning."

    if not company.get('is_active', 0):
        return False, "Kompaniyangiz faol emas. Admin bilan bog'laning."

    # Faqat username qismini (company_code siz) olish
    user_part, _ = parse_username(username_clean)

    st.session_state['auth'] = {
        'logged_in': True,
        'role': 'user',
        'user_id': user['id'],
        'user_name': user_part,
        'company_id': company['id'],
        'company_code': company['company_code'],
        'company_name': company['company_name'],
    }
    return True, ""


def logout():
    """Tizimdan chiqish — sessionni tozalash"""
    _init_session()
    st.session_state['auth'] = dict(_EMPTY_SESSION)
    for key in ['show_settings', 'show_monitoring', 'show_sprint_report',
                'selected_page', 'settings_changed']:
        st.session_state.pop(key, None)
