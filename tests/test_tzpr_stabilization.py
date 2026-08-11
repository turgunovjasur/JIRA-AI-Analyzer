import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.checkers.tz_pr_checker import TZPRService
from services.checkers.tzpr_models import TZPRAnalysisResult
from services.webhook.error_handler import _classify_error
from services.webhook.jira_webhook_handler import _is_allowed_issue_type
from utils.jira.jira_comment_publisher import JiraCommentPublishResult


def test_allowed_issue_type_match_is_case_insensitive():
    assert _is_allowed_issue_type("dev-bug", "DEV-BUG,DEV-TECHTASK") is True
    assert _is_allowed_issue_type("Dev-TechTask", "DEV-BUG,DEV-TECHTASK") is True
    assert _is_allowed_issue_type("Story", "DEV-BUG,DEV-TECHTASK") is False


def test_tz_min_length_uses_description_only():
    # min_tz_description_chars FAQAT description uzunligini o'lchaydi —
    # summary hisobga olinmaydi (tzpr_data_fetch._get_tz_length_chars)
    service = TZPRService()

    assert service._is_tz_too_short(
        {"summary": "A" * 30, "description": "B" * 25},
        min_chars=50,
    ) is True
    assert service._is_tz_too_short(
        {"summary": "Short", "description": "B" * 60},
        min_chars=50,
    ) is False




def test_error_classification_treats_full_analysis_overload_as_retryable():
    assert _classify_error("AI token limit: prompt too large for full analysis") == "ai_timeout"
    assert _classify_error("To'liq tahlil bajarilmadi: O'zgarishlar hajmi AI limitidan oshdi.") == "ai_timeout"
    assert _classify_error("context length exceeded while generating response") == "ai_timeout"


def test_service1_does_not_mark_returned_when_jira_transition_fails(monkeypatch):
    import config.app_settings as app_settings_module
    import services.webhook.error_handler as error_handler_module
    import services.webhook.jira_webhook_handler as webhook_module
    import utils.auth.auth_db as auth_db
    import utils.jira.jira_comment_writer as jira_comment_writer
    from services.webhook import service_runner

    task_key = "TEST-RETURN-GUARD-001"
    result = TZPRAnalysisResult(
        task_key=task_key,
        success=True,
        task_summary="Auto return guard",
        compliance_score=40,
    )


    settings = SimpleNamespace(
        auto_return_enabled=True,
        return_threshold=60,
        return_status="RETURN TO DEV",
        visible_sections=["failed"],
    )
    mark_returned = MagicMock()
    set_return_reason = MagicMock()

    monkeypatch.setattr(
        service_runner, "get_task",
        lambda key, company_id=None: {"service1_status": "pending", "return_count": 0},
    )
    monkeypatch.setattr(service_runner, "set_service1_done", MagicMock())
    monkeypatch.setattr(service_runner, "mark_returned", mark_returned)
    monkeypatch.setattr(service_runner, "set_return_reason", set_return_reason)
    monkeypatch.setattr(service_runner, "_handle_auto_return", AsyncMock(return_value=False))
    import services.checkers.tzpr_multi_agent as tzpr_ma
    monkeypatch.setattr(tzpr_ma, "create_multi_agent_run", lambda **kwargs: {"run_id": 1})
    monkeypatch.setattr(tzpr_ma, "run_multi_agent_for_webhook", lambda run_id: result)
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


@pytest.mark.no_db
def test_service1_does_not_mark_done_when_jira_publication_fails(monkeypatch):
    import config.app_settings as app_settings_module
    import services.webhook.error_handler as error_handler_module
    import services.webhook.jira_webhook_handler as webhook_module
    import utils.auth.auth_db as auth_db
    import utils.jira.jira_comment_writer as jira_comment_writer
    from services.webhook import service_runner

    task_key = "TEST-COMMENT-FAIL-001"
    result = TZPRAnalysisResult(
        task_key=task_key,
        success=True,
        task_summary="Comment guard",
        compliance_score=90,
    )
    settings = SimpleNamespace(
        auto_return_enabled=False,
        return_threshold=60,
        return_status="RETURN TO DEV",
    )
    set_service1_done = MagicMock()
    set_service1_error = MagicMock()

    monkeypatch.setattr(
        service_runner,
        "get_task",
        lambda key, company_id=None: {"service1_status": "pending", "return_count": 0},
    )
    monkeypatch.setattr(service_runner, "set_service1_done", set_service1_done)
    monkeypatch.setattr(service_runner, "set_service1_error", set_service1_error)
    import services.checkers.tzpr_multi_agent as tzpr_ma

    monkeypatch.setattr(tzpr_ma, "create_multi_agent_run", lambda **kwargs: {"run_id": "run-1"})
    monkeypatch.setattr(tzpr_ma, "run_multi_agent_for_webhook", lambda run_id: result)
    monkeypatch.setattr(
        error_handler_module,
        "_write_success_comment",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(webhook_module, "get_adf_formatter", lambda: object())
    monkeypatch.setattr(jira_comment_writer, "JiraCommentWriter", lambda **kwargs: object())
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

    set_service1_done.assert_not_called()
    set_service1_error.assert_called_once_with(
        task_key,
        "S1 JIRA comment to'liq yozilmadi",
        company_id=1,
    )


@pytest.mark.no_db
def test_s1_success_comment_uses_shared_publisher_and_webhook_sections(monkeypatch):
    from services.webhook.error_handler import _write_success_comment
    from utils.jira import jira_comment_publisher

    calls: dict = {}

    class FakePublisher:
        def __init__(self, writer):
            calls["writer"] = writer

        def publish_adf(self, task_key, document, **kwargs):
            calls["task_key"] = task_key
            calls["document"] = document
            calls.update(kwargs)
            calls["simple"] = kwargs["simple_fallback"]()
            return JiraCommentPublishResult(success=True, part_count=2, split=True)

    monkeypatch.setattr(jira_comment_publisher, "JiraCommentPublisher", FakePublisher)
    result = TZPRAnalysisResult(
        task_key="DEV-1",
        success=True,
        compliance_score=90,
    )
    settings = SimpleNamespace(
        tz_pr_footer_text="footer",
        recheck_comment_text="recheck",
        agent2_extra_scan_enabled=True,
        jira_comment_sections=["summary", "failed"],
    )
    writer = MagicMock()
    formatter = MagicMock()
    formatter.build_comment_document.return_value = {"type": "doc", "content": []}
    formatter.build_simple_comment.return_value = "simple"

    success = asyncio.run(
        _write_success_comment(
            "DEV-1",
            result,
            "READY TO TEST",
            settings,
            writer,
            formatter,
        )
    )

    assert success is True
    assert calls["writer"] is writer
    assert calls["marker"] == "[AI_S1]"
    assert calls["service_name"] == "Servis-1"
    assert calls["simple"] == "simple"
    assert formatter.build_comment_document.call_args.kwargs["jira_comment_sections"] == ["summary", "failed"]
    assert formatter.build_simple_comment.call_args.kwargs["jira_comment_sections"] == ["summary", "failed"]
