"""Company-admin analytics API; entitlement enforced server-side."""

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from services.api.session_scope import get_session_role, get_session_user_id, load_api_session, require_company_scope
from utils.auth.auth_db import get_effective_company_modules, is_company_subscription_active
from utils.database.team_analytics_repository import get_snapshot, save_settings

router = APIRouter(prefix="/api/team-analytics", tags=["team-analytics"])


def scope(session_id, company_id):
    session = load_api_session(session_id, allowed_roles={"company_admin", "super_admin"})
    company_id = require_company_scope(session, company_id)
    if company_id is None:
        raise HTTPException(400, "Company tanlang")
    if get_session_role(session) != "super_admin" and not get_effective_company_modules(company_id).get(
        "team_analytics"
    ):
        raise HTTPException(403, "Team Analytics moduli yoqilmagan")
    if get_session_role(session) != "super_admin" and not is_company_subscription_active(company_id)[0]:
        raise HTTPException(403, "Kompaniya obunasi faol emas")
    return session, company_id


class AnalyticsSettings(BaseModel):
    model_config = {"extra": "forbid"}
    working_status: str = Field(min_length=1, max_length=128)
    daily_hours: float = Field(default=8, gt=0, le=24, allow_inf_nan=False)
    weekly_hours: float = Field(default=40, gt=0, le=168, allow_inf_nan=False)


@router.get("/snapshot")
def snapshot(
    company_id: int | None = Query(None, ge=1),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    assignee_id: str | None = Query(None, max_length=256),
    jira_source: str | None = Query(None, max_length=2048),
    sprint_id: int | None = Query(None, ge=1, le=9223372036854775807),
    sprint_source: str | None = Query(None, max_length=2048),
    x_session_id: str | None = Header(None, alias="X-Session-ID"),
):
    _, company_id = scope(x_session_id, company_id)
    if assignee_id and not jira_source:
        raise HTTPException(422, "Ijrochi uchun Jira manbasi kerak")
    if sprint_id is not None and not sprint_source:
        raise HTTPException(422, "Sprint uchun Jira manbasi kerak")
    try:
        return get_snapshot(company_id, limit, offset, assignee_id, jira_source, sprint_id, sprint_source)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.put("/settings")
def settings(
    body: AnalyticsSettings,
    company_id: int | None = Query(None, ge=1),
    x_session_id: str | None = Header(None, alias="X-Session-ID"),
):
    session, company_id = scope(x_session_id, company_id)
    status = body.working_status.strip()
    if not status:
        raise HTTPException(422, "Status nomi bo'sh bo'lishi mumkin emas")
    actor_id = get_session_user_id(session) if get_session_role(session) == "company_admin" else None
    save_settings(company_id, status, actor_id, body.daily_hours, body.weekly_hours)
    return {"success": True, "working_status": status, "daily_hours": body.daily_hours,
            "weekly_hours": body.weekly_hours}
