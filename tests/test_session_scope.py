import pytest
from fastapi import HTTPException

from services.api import session_scope


def _session(
    *,
    role: str = "company_admin",
    company_id: int | None = 321,
    user_id: int | None = 156,
    modules: dict[str, bool] | None = None,
):
    return {
        "auth": {
            "logged_in": True,
            "role": role,
            "company_id": company_id,
            "user_id": user_id,
        },
        "company_modules": modules or {},
    }


def test_load_api_session_accepts_valid_role(monkeypatch):
    monkeypatch.setattr(
        session_scope,
        "get_web_session",
        lambda token, touch=True: _session(role="company_admin"),
    )

    session = session_scope.load_api_session("token-1", allowed_roles={"company_admin"})

    assert session_scope.get_session_role(session) == "company_admin"
    assert session_scope.get_session_company_id(session) == 321


def test_require_company_scope_blocks_foreign_company():
    with pytest.raises(HTTPException) as exc:
        session_scope.require_company_scope(_session(role="company_admin", company_id=321), 8)

    assert exc.value.status_code == 403


def test_require_customer_scope_returns_session_scope_for_company_admin():
    user_id, company_id = session_scope.require_customer_scope(
        _session(role="company_admin", company_id=321, user_id=156, modules={"tz_pr_checker": True}),
        requested_user_id=None,
        requested_company_id=None,
        module_key="tz_pr_checker",
    )

    assert user_id == 156
    assert company_id == 321


def test_require_customer_scope_blocks_foreign_user_scope():
    with pytest.raises(HTTPException) as exc:
        session_scope.require_customer_scope(
            _session(role="user", company_id=321, user_id=156, modules={"testcase_generator": True}),
            requested_user_id=999,
            requested_company_id=321,
            module_key="testcase_generator",
        )

    assert exc.value.status_code == 403
