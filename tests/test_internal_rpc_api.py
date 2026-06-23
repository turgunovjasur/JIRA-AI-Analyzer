import pytest
from fastapi import HTTPException

from services.api.internal_rpc_api import RpcRequest, _authorize_internal_rpc, _redact_rpc_payload


@pytest.fixture(autouse=True)
def isolate_test_databases():
    """Bu testlarda DB kerak emas; global DB fixture'ni override qilamiz."""
    yield {"task_db": None, "auth_db": None}


@pytest.fixture(autouse=True)
def ensure_db():
    """Global ensure_db fixture'ni override qilamiz."""
    yield


@pytest.fixture(autouse=True)
def cleanup_test_tasks():
    """Global cleanup fixture'ni override qilamiz."""
    yield


def _session(*, role: str = "company_admin", company_id: int | None = 321) -> dict:
    return {
        "auth": {
            "logged_in": True,
            "role": role,
            "company_id": company_id,
        }
    }


@pytest.mark.parametrize(
    "payload",
    [
        RpcRequest(op="save_company_webhook_module_settings", args=[321, "webhook_tz_pr", {"trigger_status": "READY TO TEST"}]),
        RpcRequest(op="save_company_settings", args=[321, {"webhook_trigger_status": "READY TO TEST"}]),
    ],
)
def test_company_admin_can_use_webhook_save_rpc_operations(payload: RpcRequest):
    _authorize_internal_rpc(_session(), payload)


def test_company_admin_webhook_save_rpc_blocks_foreign_company_scope():
    with pytest.raises(HTTPException) as exc:
        _authorize_internal_rpc(
            _session(company_id=321),
            RpcRequest(op="save_company_webhook_module_settings", args=[999, "queue", {"gemini_min_interval": 6}]),
        )

    assert exc.value.status_code == 403
    assert "Boshqa company scope" in str(exc.value.detail)


def test_rpc_audit_payload_redacts_nested_credentials():
    payload = _redact_rpc_payload(
        "save_company_settings",
        [
            321,
            {
                "jira_token": "jira-secret",
                "nested": {"webhook_secret": "hook-secret"},
                "safe": "visible",
            },
        ],
        {"github_token": "gh-secret"},
    )

    assert payload["args"][1]["jira_token"] == "***REDACTED***"
    assert payload["args"][1]["nested"]["webhook_secret"] == "***REDACTED***"
    assert payload["args"][1]["safe"] == "visible"
    assert payload["kwargs"]["github_token"] == "***REDACTED***"


def test_rpc_audit_payload_redacts_sensitive_global_setting_value():
    payload = _redact_rpc_payload("set_global_setting", ["gemini_default_api_key_1", "ai-secret"], {})

    assert payload["args"] == ["gemini_default_api_key_1", "***REDACTED***"]
