import pytest
from fastapi import HTTPException

from services.api import team_analytics_api as api


def test_company_admin_cannot_request_other_tenant(monkeypatch):
    monkeypatch.setattr(
        api, "load_api_session", lambda *args, **kwargs: {"auth": {"role": "company_admin", "company_id": 3}}
    )
    with pytest.raises(HTTPException) as error:
        api.scope("session", 4)
    assert error.value.status_code == 403


def test_api_checks_current_entitlement(monkeypatch):
    monkeypatch.setattr(
        api,
        "load_api_session",
        lambda *args, **kwargs: {
            "auth": {"role": "company_admin", "company_id": 3},
            "company_modules": {"team_analytics": True},
        },
    )
    monkeypatch.setattr(api, "get_effective_company_modules", lambda company_id: {"team_analytics": False})
    with pytest.raises(HTTPException) as error:
        api.scope("session", None)
    assert error.value.status_code == 403


def test_api_rechecks_expired_subscription_before_sweep(monkeypatch):
    monkeypatch.setattr(
        api, "load_api_session", lambda *args, **kwargs: {"auth": {"role": "company_admin", "company_id": 3}}
    )
    monkeypatch.setattr(api, "get_effective_company_modules", lambda company_id: {"team_analytics": True})
    monkeypatch.setattr(api, "is_company_subscription_active", lambda company_id: (False, "expired"), raising=False)
    with pytest.raises(HTTPException) as error:
        api.scope("session", None)
    assert error.value.status_code == 403
