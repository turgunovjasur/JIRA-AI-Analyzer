"""
Internal TZ-PR API endpoints.
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from services.checkers.tz_pr_checker import TZPRService
from services.api.session_scope import load_api_session, require_customer_scope

router = APIRouter(prefix="/api/tzpr", tags=["tz-pr"])


class AnalyzeRequest(BaseModel):
    task_key: str
    user_id: int | None = None
    company_id: int | None = None
    max_files: int | None = None
    show_full_diff: bool = True
    use_smart_patch: bool | None = None
    output_profile: str | None = None


@router.post("/analyze")
async def analyze_tzpr(
    payload: AnalyzeRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    try:
        session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin", "user"})
        user_id, company_id = require_customer_scope(
            session,
            payload.user_id,
            payload.company_id,
            module_key="tz_pr_checker",
        )
        service = TZPRService(user_id=user_id, company_id=company_id)
        result = service.analyze_task(
            task_key=payload.task_key.strip().upper(),
            max_files=payload.max_files,
            show_full_diff=payload.show_full_diff,
            use_smart_patch=payload.use_smart_patch,
            status_callback=None,
            output_profile=(payload.output_profile or "comment").strip().lower(),
        )
        return asdict(result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TZ-PR analyze error: {exc}") from exc
