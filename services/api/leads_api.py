"""Contact lead API.

- POST /api/leads  — PUBLIC (rate-limited): landing/demo formasidan lid qabul qiladi,
  DB'ga saqlaydi va Telegram'ga bildirishnoma yuboradi.
- GET  /api/leads  — faqat super_admin: lidlar ro'yxati.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.logger import get_logger
from services.api.rate_limit import check_rate_limit
from services.api.session_scope import load_api_session
from utils.database.lead_repository import create_lead, list_leads
from utils.database.runtime import connect_processing_db
from utils.notify.telegram_notifier import send_telegram_message

router = APIRouter(prefix="/api/leads", tags=["leads"])
log = get_logger("api.leads")


class LeadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=3, max_length=40)
    role: str = Field(min_length=1, max_length=120)
    source: str = Field(default="landing", max_length=40)


def _connect():
    return connect_processing_db(timeout=30.0, row_factory=True)


@router.post("")
def submit_lead(payload: LeadCreate, request: Request, _rl: None = Depends(check_rate_limit)):
    name = payload.name.strip()
    phone = payload.phone.strip()
    role = payload.role.strip()
    if not name or not phone or not role:
        raise HTTPException(status_code=400, detail="Ism, telefon va kasb majburiy")
    source = (payload.source or "landing").strip() or "landing"

    try:
        conn = _connect()
        try:
            lead = create_lead(conn, name=name, phone=phone, role=role, source=source)
        finally:
            conn.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lidni saqlab bo'lmadi: {exc}") from exc

    # Telegram bildirishnomasi — muvaffaqiyatsizligi lid saqlanishiga ta'sir qilmaydi.
    try:
        send_telegram_message(
            "🆕 <b>Yangi lid — QA-Assistant</b>\n"
            f"👤 {name}\n"
            f"📞 {phone}\n"
            f"💼 {role}\n"
            f"🌐 manba: {source}"
        )
    except Exception:
        log.warning("Telegram lid xabari yuborilmadi", exc_info=True)

    return {"success": True, "lead_id": lead.get("id")}


@router.get("")
def get_leads(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    load_api_session(x_session_id, allowed_roles={"super_admin"})
    try:
        conn = _connect()
        try:
            result = list_leads(conn, limit=limit, offset=offset)
        finally:
            conn.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lidlarni o'qib bo'lmadi: {exc}") from exc

    return {
        "success": True,
        "leads": result["leads"],
        "total": result["total"],
        "limit": limit,
        "offset": offset,
    }
