"""
Internal Test Case Generator API endpoints.
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from services.generators.testcase_generator import TestCaseGeneratorService
from services.api.session_scope import load_api_session, require_customer_scope

router = APIRouter(prefix="/api/testcase", tags=["testcase"])


class GenerateRequest(BaseModel):
    task_key: str
    user_id: int | None = None
    company_id: int | None = None
    include_pr: bool = True
    use_smart_patch: bool = False
    test_types: list[str] = Field(default_factory=list)
    custom_context: str = ""


@router.post("/generate")
async def generate_testcases(
    payload: GenerateRequest,
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
):
    try:
        session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin", "user"})
        user_id, company_id = require_customer_scope(
            session,
            payload.user_id,
            payload.company_id,
            module_key="testcase_generator",
        )
        service = TestCaseGeneratorService(user_id=user_id, company_id=company_id)
        result = service.generate_test_cases(
            task_key=payload.task_key.strip().upper(),
            include_pr=payload.include_pr,
            use_smart_patch=payload.use_smart_patch,
            test_types=payload.test_types,
            custom_context=payload.custom_context,
            status_callback=None,
        )
        return asdict(result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Testcase generation error: {exc}") from exc
