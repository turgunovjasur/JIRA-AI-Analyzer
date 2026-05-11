"""
Shared backend session-scope helpers for FastAPI routes.

Bu modul customer-facing va internal API endpointlarda sessiya, role va
company scope tekshiruvlarini bitta joyda ushlaydi.
"""
from __future__ import annotations

from typing import Iterable, Optional

from fastapi import HTTPException

from utils.auth.auth_db import get_effective_company_modules, get_web_session


def load_api_session(
    x_session_id: str | None,
    *,
    allowed_roles: Optional[Iterable[str]] = None,
    touch: bool = True,
) -> dict:
    if not x_session_id:
        raise HTTPException(status_code=401, detail="Session topilmadi")

    session = get_web_session(x_session_id, touch=touch)
    auth = (session or {}).get("auth") or {}
    if not session or not auth.get("logged_in"):
        raise HTTPException(status_code=401, detail="Sessiya yaroqsiz yoki muddati tugagan")

    if allowed_roles is not None:
        role = get_session_role(session)
        if role not in set(allowed_roles):
            raise HTTPException(status_code=403, detail="Bu endpoint uchun ruxsat yo'q")

    return session


def get_session_auth(session: dict) -> dict:
    return dict((session or {}).get("auth") or {})


def get_session_role(session: dict) -> str:
    return str(get_session_auth(session).get("role") or "").strip().lower()


def get_session_company_id(session: dict) -> int | None:
    raw_value = get_session_auth(session).get("company_id")
    return int(raw_value) if raw_value not in (None, "") else None


def get_session_user_id(session: dict) -> int | None:
    raw_value = get_session_auth(session).get("user_id")
    return int(raw_value) if raw_value not in (None, "") else None


def get_session_company_modules(session: dict) -> dict[str, bool]:
    modules = (session or {}).get("company_modules")
    if isinstance(modules, dict) and modules:
        return {str(key): bool(value) for key, value in modules.items()}

    company_id = get_session_company_id(session)
    if not company_id:
        return {}
    return get_effective_company_modules(company_id)


def require_company_scope(session: dict, requested_company_id: int | None) -> int | None:
    role = get_session_role(session)
    if role == "super_admin":
        return requested_company_id

    session_company_id = get_session_company_id(session)
    if role != "company_admin" or not session_company_id:
        raise HTTPException(status_code=403, detail="Company scope uchun ruxsat yo'q")
    if requested_company_id not in (None, session_company_id):
        raise HTTPException(status_code=403, detail="Boshqa company ma'lumotiga murojaat qilib bo'lmaydi")
    return session_company_id


def require_customer_scope(
    session: dict,
    requested_user_id: int | None,
    requested_company_id: int | None,
    *,
    module_key: str | None = None,
) -> tuple[int | None, int | None]:
    role = get_session_role(session)
    if role == "super_admin":
        return requested_user_id, requested_company_id

    session_company_id = get_session_company_id(session)
    session_user_id = get_session_user_id(session)
    if role not in {"company_admin", "user"} or not session_company_id or not session_user_id:
        raise HTTPException(status_code=403, detail="Customer scope uchun ruxsat yo'q")

    if requested_company_id not in (None, session_company_id):
        raise HTTPException(status_code=403, detail="Boshqa company scope bilan ishlash mumkin emas")
    if requested_user_id not in (None, session_user_id):
        raise HTTPException(status_code=403, detail="Boshqa user scope bilan ishlash mumkin emas")

    if module_key:
        modules = get_session_company_modules(session)
        if not modules.get(module_key, False):
            raise HTTPException(status_code=403, detail=f"{module_key} moduli bu company uchun yoqilmagan")

    return session_user_id, session_company_id
