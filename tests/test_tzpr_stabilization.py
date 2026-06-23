import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from services.checkers.tz_pr_checker import TZPRAnalysisResult, TZPRService
from services.webhook.error_handler import _classify_error
from services.webhook.jira_webhook_handler import _is_allowed_issue_type


def test_allowed_issue_type_match_is_case_insensitive():
    assert _is_allowed_issue_type("dev-bug", "DEV-BUG,DEV-TECHTASK") is True
    assert _is_allowed_issue_type("Dev-TechTask", "DEV-BUG,DEV-TECHTASK") is True
    assert _is_allowed_issue_type("Story", "DEV-BUG,DEV-TECHTASK") is False


def test_tz_min_length_uses_summary_and_description_together():
    service = TZPRService()

    assert service._is_tz_too_short(
        {"summary": "A" * 30, "description": "B" * 25},
        min_chars=50,
    ) is False
    assert service._is_tz_too_short(
        {"summary": "Short", "description": "Tiny"},
        min_chars=20,
    ) is True




def test_error_classification_treats_full_analysis_overload_as_retryable():
    assert _classify_error("AI token limit: prompt too large for full analysis") == "ai_timeout"
    assert _classify_error("To'liq tahlil bajarilmadi: O'zgarishlar hajmi AI limitidan oshdi.") == "ai_timeout"
    assert _classify_error("context length exceeded while generating response") == "ai_timeout"


def test_service1_does_not_mark_returned_when_jira_transition_fails(monkeypatch):
    import config.app_settings as app_settings_module
    from services.webhook import service_runner
    import services.checkers.tz_pr_checker as tzpr_module
    import services.webhook.error_handler as error_handler_module
    import services.webhook.jira_webhook_handler as webhook_module
    import utils.auth.auth_db as auth_db
    import utils.jira.jira_comment_writer as jira_comment_writer

    task_key = "TEST-RETURN-GUARD-001"
    result = TZPRAnalysisResult(
        task_key=task_key,
        success=True,
        task_summary="Auto return guard",
        compliance_score=40,
    )

    class FakeService:
        def __init__(self, *args, **kwargs):
            pass

        def analyze_task(self, *args, **kwargs):
            return result

    settings = SimpleNamespace(
        auto_return_enabled=True,
        return_threshold=60,
        return_status="RETURN TO DEV",
        visible_sections=["failed"],
    )
    mark_returned = MagicMock()
    set_return_reason = MagicMock()

    monkeypatch.setattr(service_runner, "get_task", lambda key: {"service1_status": "pending"})
    monkeypatch.setattr(service_runner, "set_service1_done", MagicMock())
    monkeypatch.setattr(service_runner, "mark_returned", mark_returned)
    monkeypatch.setattr(service_runner, "set_return_reason", set_return_reason)
    monkeypatch.setattr(service_runner, "_handle_auto_return", AsyncMock(return_value=False))
    monkeypatch.setattr(
        tzpr_module,
        "TZPRService",
        FakeService,
    )
    monkeypatch.setattr(
        error_handler_module,
        "_write_success_comment",
        AsyncMock(),
    )
    monkeypatch.setattr(
        webhook_module,
        "get_adf_formatter",
        lambda: object(),
    )
    monkeypatch.setattr(
        jira_comment_writer,
        "JiraCommentWriter",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        auth_db,
        "get_company_webhook_credentials",
        lambda company_id: {
            "jira_server": "https://jira.example.com",
            "jira_email": "qa@example.com",
            "jira_token": "secret",
        },
    )
    monkeypatch.setattr(
        app_settings_module,
        "get_app_settings_for_company",
        lambda company_id: SimpleNamespace(webhook_tz_pr=settings),
    )

    asyncio.run(
        service_runner.check_tz_pr_and_comment(
            task_key=task_key,
            new_status="READY TO TEST",
            company_id=1,
        )
    )

    mark_returned.assert_not_called()
    set_return_reason.assert_not_called()
    service_runner._handle_auto_return.assert_awaited_once()
