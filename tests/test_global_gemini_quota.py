"""Global (QA ASSISTANT) Gemini kalit bepul-urinish kvota feature testlari.

Real PostgreSQL talab qiladi (conftest `APP_TEST_POSTGRES_DSN` bilan; bo'lmasa skip).
"""
import pytest

import core.module_start_preflight as preflight
from core.module_start_preflight import _check_global_quota, get_module_start_status
from utils.database.quota_db import get_global_quota_status, increment_global_quota
from utils.database.quota_repository import GLOBAL_GEMINI_FREE_LIMIT
from utils.database.runtime import connect_processing_db

_CID = 880011  # test-only company id


@pytest.fixture(autouse=True)
def _clean_quota():
    """Test cid'lari uchun kvota qatorlarini tozalash (idempotent runlar uchun)."""
    def _del():
        conn = connect_processing_db()
        try:
            conn.execute(
                "DELETE FROM global_gemini_quota WHERE company_id BETWEEN 880011 AND 880020"
            )
            conn.commit()
        finally:
            conn.close()
    _del()
    yield
    _del()


def test_quota_increments_per_module_independently():
    # Checker va testcase kvotalari mustaqil (per company+module).
    base_checker = get_global_quota_status(_CID, "tz_pr_checker")["used"]
    increment_global_quota(_CID, "tz_pr_checker")
    increment_global_quota(_CID, "tz_pr_checker")
    assert get_global_quota_status(_CID, "tz_pr_checker")["used"] == base_checker + 2
    # testcase'ga ta'sir qilmaydi
    assert get_global_quota_status(_CID, "testcase_generator")["used"] == 0


def test_quota_gate_allows_then_blocks_at_limit():
    cid = _CID + 1
    chk, quota = _check_global_quota(module_key="tz_pr_checker", company_id=cid)
    assert chk is None  # 0/10 — ruxsat
    assert quota["remaining"] == GLOBAL_GEMINI_FREE_LIMIT
    for _ in range(GLOBAL_GEMINI_FREE_LIMIT):
        increment_global_quota(cid, "tz_pr_checker")
    chk, quota = _check_global_quota(module_key="tz_pr_checker", company_id=cid)
    assert chk is not None and chk.status == "fail"
    assert chk.code == "QUOTA_GLOBAL_FREE_EXHAUSTED"
    assert quota["exhausted"] is True
    # Boshqa modul (testcase) hali ham ishlaydi
    chk2, _ = _check_global_quota(module_key="testcase_generator", company_id=cid)
    assert chk2 is None


def test_start_status_global_key_shows_remaining(monkeypatch):
    cid = _CID + 2
    monkeypatch.setattr(
        preflight, "_resolve_credentials",
        lambda **kw: (
            __import__("core.module_errors", fromlist=["ModuleCheck"]).ModuleCheck(
                id="api_credentials", label="API credentials", status="ok", message="ok"),
            {"jira_ok": True, "github_ok": True, "gemini_source": "global"},
        ),
    )
    status = get_module_start_status(module_key="tz_pr_checker", company_id=cid, user_id=None)
    assert status["blocked"] is False
    assert status["level"] == "warning"
    assert "QA ASSISTANT" in status["message"]
    assert status["gemini_quota"]["using_global"] is True


def test_start_status_blocks_when_global_quota_exhausted(monkeypatch):
    cid = _CID + 3
    for _ in range(GLOBAL_GEMINI_FREE_LIMIT):
        increment_global_quota(cid, "testcase_generator")
    monkeypatch.setattr(
        preflight, "_resolve_credentials",
        lambda **kw: (
            __import__("core.module_errors", fromlist=["ModuleCheck"]).ModuleCheck(
                id="api_credentials", label="API credentials", status="ok", message="ok"),
            {"jira_ok": True, "github_ok": True, "gemini_source": "global"},
        ),
    )
    status = get_module_start_status(module_key="testcase_generator", company_id=cid, user_id=None)
    assert status["blocked"] is True
    assert status["level"] == "error"
    assert "Imtiyoz tugadi" in status["message"]


def test_start_status_own_key_no_quota(monkeypatch):
    monkeypatch.setattr(
        preflight, "_resolve_credentials",
        lambda **kw: (
            __import__("core.module_errors", fromlist=["ModuleCheck"]).ModuleCheck(
                id="api_credentials", label="API credentials", status="ok", message="ok"),
            {"jira_ok": True, "github_ok": True, "gemini_source": "user"},
        ),
    )
    status = get_module_start_status(module_key="tz_pr_checker", company_id=_CID + 4, user_id=5)
    assert status["blocked"] is False
    assert status["gemini_quota"]["using_global"] is False
    assert status["message"] == ""  # o'z kaliti — banner yo'q
