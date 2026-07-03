"""Per-company oylik AI budjet cap (F2-5) feature testlari.

Real PostgreSQL talab qiladi (conftest `APP_TEST_POSTGRES_DSN` bilan; bo'lmasa skip).
"""
import logging

import pytest

import core.module_start_preflight as preflight
from core.module_errors import ModuleCheck
from core.module_start_preflight import (
    _check_monthly_budget,
    get_module_start_status,
    run_start_preflight,
)
from utils.database.runtime import connect_processing_db

_CID = 990011  # test-only company id oralig'i: 990011..990020
_CID_MAX = 990020


def _cleanup_budget_test_data():
    conn = connect_processing_db()
    try:
        conn.execute(
            "DELETE FROM ai_usage_events WHERE company_id BETWEEN %s AND %s",
            [_CID, _CID_MAX],
        )
        # companies delete -> company_settings (budjet) CASCADE bilan o'chadi.
        conn.execute(
            "DELETE FROM companies WHERE id BETWEEN %s AND %s",
            [_CID, _CID_MAX],
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def _budget_env():
    """Test kompaniyalarini yaratish + ledger/budjet qatorlarini tozalash."""
    _cleanup_budget_test_data()
    conn = connect_processing_db()
    try:
        for cid in range(_CID, _CID_MAX + 1):
            conn.execute(
                """
                INSERT INTO companies (id, company_code, company_name, seat_limit, is_active)
                VALUES (%s, %s, %s, 5, TRUE)
                ON CONFLICT (id) DO NOTHING
                """,
                [cid, f"pybudget{cid}", f"Budget Co {cid}"],
            )
        conn.commit()
    finally:
        conn.close()
    yield
    _cleanup_budget_test_data()


def _seed_event(company_id: int, cost_usd: float, module_key: str = "tz_pr_checker") -> int:
    from utils.database.ai_usage_db import record_ai_usage_event

    row = record_ai_usage_event(
        company_id=company_id,
        user_id=None,
        run_id=None,
        task_key="TEST-BUDGET",
        module_key=module_key,
        agent_key="agent1",
        source="pytest",
        model="gemini-2.5-pro",
        primary_model="gemini-2.5-pro",
        fallback_model="",
        used_fallback=False,
        usage={"total_token_count": 100},
        cost={"estimated_total_cost_usd": cost_usd},
    )
    return int(row["id"])


def _move_event_to_previous_month(event_id: int):
    conn = connect_processing_db()
    try:
        conn.execute(
            "UPDATE ai_usage_events SET created_at = created_at - INTERVAL '45 days' WHERE id = %s",
            [event_id],
        )
        conn.commit()
    finally:
        conn.close()


def _ok_credentials(gemini_source: str = "company"):
    return (
        ModuleCheck(id="api_credentials", label="API credentials", status="ok", message="ok"),
        {"jira_ok": True, "github_ok": True, "gemini_source": gemini_source},
    )


def test_monthly_cost_sums_only_current_month_and_company():
    from utils.database.ai_usage_db import get_company_monthly_cost_usd

    _seed_event(_CID, 0.03)
    _seed_event(_CID, 0.045)
    _seed_event(_CID + 1, 0.5)  # boshqa company — hisobga kirmaydi
    old_id = _seed_event(_CID, 0.9)
    _move_event_to_previous_month(old_id)  # o'tgan oy — hisobga kirmaydi

    assert get_company_monthly_cost_usd(_CID) == pytest.approx(0.075)
    assert get_company_monthly_cost_usd(_CID + 2) == 0.0


def test_budget_gate_blocks_when_spend_reaches_budget():
    from utils.auth.auth_db import get_company_ai_budget, save_company_ai_budget

    cid = _CID + 2
    assert save_company_ai_budget(cid, 0.10) is True
    assert get_company_ai_budget(cid) == pytest.approx(0.10)
    _seed_event(cid, 0.06)
    _seed_event(cid, 0.05, module_key="testcase_generator")

    chk, info = _check_monthly_budget(module_key="tz_pr_checker", company_id=cid)
    assert chk is not None and chk.status == "fail"
    assert chk.code == "BUDGET_EXCEEDED"
    assert chk.blocking is True
    assert "$0.11" in chk.message and "$0.10" in chk.message
    assert info["exceeded"] is True
    assert info["remaining_usd"] == 0.0


def test_budget_unset_or_zero_means_unlimited():
    from utils.auth.auth_db import get_company_ai_budget, save_company_ai_budget

    cid = _CID + 3
    _seed_event(cid, 5.0)

    # Budjet umuman o'rnatilmagan
    chk, info = _check_monthly_budget(module_key="tz_pr_checker", company_id=cid)
    assert chk is None
    assert info == {"enabled": False}

    # Budjet 0 = cheksiz (NULL sifatida saqlanadi)
    assert save_company_ai_budget(cid, 0) is True
    assert get_company_ai_budget(cid) is None
    chk, info = _check_monthly_budget(module_key="testcase_generator", company_id=cid)
    assert chk is None
    assert info == {"enabled": False}


def test_budget_under_limit_passes_with_info():
    from utils.auth.auth_db import save_company_ai_budget

    cid = _CID + 4
    assert save_company_ai_budget(cid, 1.00) is True
    _seed_event(cid, 0.25)

    chk, info = _check_monthly_budget(module_key="tz_pr_checker", company_id=cid)
    assert chk is None
    assert info["enabled"] is True
    assert info["spent_usd"] == pytest.approx(0.25)
    assert info["remaining_usd"] == pytest.approx(0.75)
    assert info["exceeded"] is False


def test_fail_open_when_ledger_unreachable(monkeypatch, caplog):
    import utils.database.ai_usage_db as ai_usage_db
    from utils.auth.auth_db import save_company_ai_budget

    cid = _CID + 5
    assert save_company_ai_budget(cid, 0.01) is True
    _seed_event(cid, 1.0)  # budjetdan ancha ko'p — lekin ledger o'qilmaydi

    def _boom(*args, **kwargs):
        raise RuntimeError("ledger down")

    monkeypatch.setattr(ai_usage_db, "get_company_monthly_cost_usd", _boom)
    with caplog.at_level(logging.WARNING):
        chk, info = _check_monthly_budget(module_key="tz_pr_checker", company_id=cid)
    assert chk is None  # fail-open: bloklamaymiz
    assert info is None
    assert "fail-open" in caplog.text


def test_start_status_includes_budget_and_blocks(monkeypatch):
    from utils.auth.auth_db import save_company_ai_budget

    cid = _CID + 6
    assert save_company_ai_budget(cid, 0.05) is True
    _seed_event(cid, 0.06)
    monkeypatch.setattr(preflight, "_resolve_credentials", lambda **kw: _ok_credentials())

    status = get_module_start_status(module_key="tz_pr_checker", company_id=cid, user_id=None)
    assert status["blocked"] is True
    assert status["level"] == "error"
    assert "budjet" in status["message"].lower()
    assert status["ai_budget"]["exceeded"] is True


def test_start_status_budget_info_when_under_limit(monkeypatch):
    from utils.auth.auth_db import save_company_ai_budget

    cid = _CID + 7
    assert save_company_ai_budget(cid, 2.00) is True
    _seed_event(cid, 0.10)
    monkeypatch.setattr(preflight, "_resolve_credentials", lambda **kw: _ok_credentials())

    status = get_module_start_status(module_key="testcase_generator", company_id=cid, user_id=None)
    assert status["blocked"] is False
    assert status["ai_budget"]["enabled"] is True
    assert status["ai_budget"]["exceeded"] is False


def test_run_start_preflight_budget_gate_both_modules(monkeypatch):
    from utils.auth.auth_db import save_company_ai_budget

    cid = _CID + 8
    assert save_company_ai_budget(cid, 0.05) is True
    _seed_event(cid, 0.06)
    monkeypatch.setattr(preflight, "_resolve_credentials", lambda **kw: _ok_credentials())
    monkeypatch.setattr(
        preflight, "_check_module_access",
        lambda company_id, module_key, module_label: ModuleCheck(
            id="module_access", label="Company module access", status="ok", message="ok"),
    )

    for module_key in ("tz_pr_checker", "testcase_generator"):
        result = run_start_preflight(
            module_key=module_key, task_key="TEST-1", company_id=cid, user_id=None,
        )
        assert result.ok is False
        assert "BUDGET_EXCEEDED" in [c.code for c in result.checks]
        payload = result.to_error_payload()
        assert payload["ai_budget"]["exceeded"] is True

    # Budjet oshirilsa run yana ochiladi
    assert save_company_ai_budget(cid, 100) is True
    result = run_start_preflight(
        module_key="tz_pr_checker", task_key="TEST-1", company_id=cid, user_id=None,
    )
    assert result.ok is True
    assert result.budget["exceeded"] is False
