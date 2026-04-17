"""
Auth Manager — Login / Logout / Session

Super Admin: .env dan SUPER_ADMIN_USERNAME + SUPER_ADMIN_PASSWORD
Company:     auth.db dagi companies jadvalidan

Session state kalit: st.session_state['auth']
  {
    'logged_in':    bool,
    'role':         'super_admin' | 'company',
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
    get_company_by_code,
    verify_password,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SUPER ADMIN CREDENTIALS (.env dan)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_SUPER_USERNAME = os.getenv('SUPER_ADMIN_USERNAME', 'superadmin')
_SUPER_PASSWORD = os.getenv('SUPER_ADMIN_PASSWORD', 'admin123')


def _check_super_admin(username: str, password: str) -> bool:
    """Super admin login tekshirish"""
    user_ok = secrets.compare_digest(username.strip(), _SUPER_USERNAME)
    pass_ok = secrets.compare_digest(password, _SUPER_PASSWORD)
    return user_ok and pass_ok


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SESSION HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _init_session():
    """Session state boshlang'ich qiymati"""
    if 'auth' not in st.session_state:
        st.session_state['auth'] = {
            'logged_in': False,
            'role': None,
            'company_id': None,
            'company_code': None,
            'company_name': None,
        }


def is_authenticated() -> bool:
    """Foydalanuvchi tizimga kirganmi?"""
    _init_session()
    return st.session_state['auth'].get('logged_in', False)


def is_super_admin() -> bool:
    """Super admin ekanini tekshirish"""
    _init_session()
    return st.session_state['auth'].get('role') == 'super_admin'


def is_company() -> bool:
    """Kompaniya sifatida kirganmi?"""
    _init_session()
    return st.session_state['auth'].get('role') == 'company'


def get_auth_info() -> dict:
    """Joriy session ma'lumotlari"""
    _init_session()
    return st.session_state['auth']


def get_company_id() -> int | None:
    """Joriy kompaniya ID si"""
    return get_auth_info().get('company_id')


def get_company_code() -> str | None:
    """Joriy kompaniya kodi"""
    return get_auth_info().get('company_code')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOGIN / LOGOUT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def login(code_or_username: str, password: str) -> tuple[bool, str]:
    """
    Tizimga kirish.

    Agar code_or_username == SUPER_ADMIN_USERNAME → super admin login.
    Aks holda → kompaniya login (company_code bo'yicha).

    Returns:
        (success: bool, error_message: str)
    """
    _init_session()

    if not code_or_username or not password:
        return False, "Login va parol kiritilishi shart"

    # Super admin tekshiruvi
    if code_or_username.strip().lower() == _SUPER_USERNAME.lower():
        if _check_super_admin(code_or_username.strip(), password):
            st.session_state['auth'] = {
                'logged_in': True,
                'role': 'super_admin',
                'company_id': None,
                'company_code': None,
                'company_name': 'Super Admin',
            }
            return True, ""
        else:
            return False, "Login yoki parol noto'g'ri"

    # Kompaniya login
    company = get_company_by_code(code_or_username)
    if not company:
        return False, "Kompaniya topilmadi"
    if not company.get('is_active', 0):
        return False, "Kompaniya faol emas. Admin bilan bog'laning."
    if not verify_password(password, company['password_hash']):
        return False, "Parol noto'g'ri"

    st.session_state['auth'] = {
        'logged_in': True,
        'role': 'company',
        'company_id': company['id'],
        'company_code': company['company_code'],
        'company_name': company['company_name'],
    }
    return True, ""


def logout():
    """Tizimdan chiqish — sessionni tozalash"""
    _init_session()
    st.session_state['auth'] = {
        'logged_in': False,
        'role': None,
        'company_id': None,
        'company_code': None,
        'company_name': None,
    }
    # Boshqa session state larni ham tozalash
    for key in ['show_settings', 'show_monitoring', 'show_sprint_report',
                'selected_page', 'settings_changed']:
        st.session_state.pop(key, None)
