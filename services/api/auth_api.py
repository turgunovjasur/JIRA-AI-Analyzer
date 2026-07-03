"""
Internal auth API endpoints.

These endpoints provide login/password-reset and module loading for the
Next.js frontend (via the BFF proxy) while preserving the current auth logic.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from services.api.rate_limit import check_rate_limit
from services.api.session_scope import load_api_session, require_company_scope
from utils.auth.auth_db import (
    consume_password_reset_token,
    create_web_session,
    get_company_subscription,
    get_effective_company_modules,
    get_web_session,
    request_password_reset_email,
    revoke_web_session_token,
)
from utils.auth.auth_manager import authenticate_credentials

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordResetRequest(BaseModel):
    token: str
    new_password: str


class CompanyModulesRequest(BaseModel):
    company_id: int


class RequestResetRequest(BaseModel):
    username: str


class SessionLogoutRequest(BaseModel):
    session_token: str | None = None


@router.post("/login")
async def login(payload: LoginRequest, request: Request, _rl: None = Depends(check_rate_limit)):
    success, error_message, auth_payload = authenticate_credentials(payload.username, payload.password)
    if not success or not auth_payload:
        return {
            "success": False,
            "error_message": error_message,
            "auth": None,
            "company_modules": None,
        }

    company_modules = None
    company_subscription = None
    company_id = auth_payload.get("company_id")
    if company_id:
        company_modules = get_effective_company_modules(company_id)
        company_subscription = get_company_subscription(company_id)
    else:
        company_modules = {}

    session = create_web_session(auth_payload, company_modules)
    if not session:
        raise HTTPException(status_code=500, detail="Web session yaratib bo'lmadi")

    return {
        "success": True,
        "error_message": "",
        "auth": auth_payload,
        "company_modules": company_modules,
        "company_subscription": company_subscription,
        "session_token": session.get("session_token"),
        "expires_at": session.get("expires_at"),
    }


@router.post("/request-reset")
async def request_reset(payload: RequestResetRequest, request: Request, _rl: None = Depends(check_rate_limit)):
    """Userga parol tiklash emaili yuboradi. Har doim 200 qaytaradi (timing attack himoyasi)."""
    username = payload.username.strip()
    if username:
        try:
            request_password_reset_email(username)
        except Exception:
            pass
    return {"success": True}


@router.post("/password-reset")
async def password_reset(payload: PasswordResetRequest, request: Request, _rl: None = Depends(check_rate_limit)):
    ok = consume_password_reset_token(payload.token.strip(), payload.new_password)
    return {"success": ok}


@router.post("/company-modules")
async def company_modules(
    payload: CompanyModulesRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin"})
    company_id = require_company_scope(session, payload.company_id)
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")
    return {"company_modules": get_effective_company_modules(company_id)}


@router.get("/me")
async def me(x_session_id: str | None = Header(default=None, alias="X-Session-ID")):
    if not x_session_id:
        raise HTTPException(status_code=401, detail="Session topilmadi")

    session = get_web_session(x_session_id, touch=True)
    if not session or not session.get("auth", {}).get("logged_in"):
        raise HTTPException(status_code=401, detail="Sessiya yaroqsiz yoki muddati tugagan")

    auth_payload = session.get("auth") or {}
    company_id = auth_payload.get("company_id")
    company_modules = get_effective_company_modules(company_id) if company_id else {}
    company_subscription = get_company_subscription(company_id) if company_id else None

    return {
        "success": True,
        "auth": auth_payload,
        "company_modules": company_modules,
        "company_subscription": company_subscription,
        "expires_at": session.get("expires_at"),
    }


@router.post("/logout")
async def logout(
    payload: SessionLogoutRequest | None = None,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    session_token = x_session_id or (payload.session_token if payload else None)
    if not session_token:
        return {"success": True}
    return {"success": revoke_web_session_token(session_token)}
