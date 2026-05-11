import pytest
from fastapi import HTTPException

from services.api.internal_rpc_api import RpcRequest, _authorize_internal_rpc


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
            RpcRequest(op="save_company_webhook_module_settings", args=[999, "queue", {"checker_testcase_delay": 15}]),
        )

    assert exc.value.status_code == 403
    assert "Boshqa company scope" in str(exc.value.detail)
