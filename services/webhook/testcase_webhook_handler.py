# services/webhook/testcase_webhook_handler.py
"""
Testcase Webhook Handler

Task statusiga ko'ra avtomatik test case yaratish va JIRA ga yozish.
Ready to Test statusga tushganda ishga tushadi.

Author: JASUR TURGUNOV
Version: 1.0
"""
from typing import Optional, Tuple
from core.logger import get_logger

log = get_logger("testcase.webhook")


async def check_and_generate_testcases(
        task_key: str,
        new_status: str,
        company_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    Status o'zgarganda avtomatik test case yaratish va comment yozish

    Args:
        task_key: JIRA task key (masalan: DEV-1234)
        new_status: Yangi status nomi
        company_id: Kompaniya ID si (None bo'lsa global settings)

    Returns:
        Tuple[bool, str]: (success, message)

    Flow:
    1. Settings tekshirish (auto_comment_enabled?)
    2. Status trigger bo'lsa - test case'lar yaratish
    3. JIRA ga comment yozish
    """
    from config.app_settings import get_app_settings, get_app_settings_for_company

    if company_id is not None:
        settings = get_app_settings_for_company(company_id)
    else:
        settings = get_app_settings()
    # Webhook uchun alohida sozlamalar (standalone testcase modulidan farqli)
    tc_settings = settings.webhook_testcase

    # 1. Auto-comment yoqilganmi?
    if not tc_settings.auto_comment_enabled:
        log.service_skipped(task_key, "TestCase", "auto-comment disabled")
        return False, "Auto-comment disabled"

    # 2. Trigger status tekshirish
    trigger_statuses = tc_settings.get_trigger_statuses()
    if new_status.lower() not in [s.lower() for s in trigger_statuses]:
        log.status_ignored(task_key, new_status, f"not in trigger list: {trigger_statuses}")
        return False, f"Status '{new_status}' is not a trigger"

    try:
        # 3. Test case'lar yaratish
        from services.generators.testcase_generator import TestCaseGeneratorService

        if company_id is not None:
            from utils.auth.auth_db import get_company_credentials
            try:
                from utils.auth.auth_db import get_company_webhook_credentials
                get_company_webhook_credentials(company_id)  # kalit yo'q bo'lsa RuntimeError
            except RuntimeError as key_err:
                log.warning(f"[{task_key}] {key_err}")
                return False, str(key_err)
            service = TestCaseGeneratorService(company_id=company_id)
        else:
            service = TestCaseGeneratorService()

        result = service.generate_test_cases(
            task_key=task_key,
            test_types=tc_settings.default_test_types,
            custom_context="",
            status_callback=lambda t, m: log.info(f"[{task_key}] {t.upper()} -> {m}")
        )

        if not result.success:
            error_msg = result.error_message or "Test case generation failed"
            from services.webhook.error_handler import _classify_error
            error_type = _classify_error(error_msg)

            # TZ yetarli emas, PR merged emas yoki boshqa bloklash holatlari — JIRA'ga Warning comment yozish
            should_write_comment = (
                "yetarli ma'lumot yo'q" in (error_msg or "")
                or "Servis-2 to'xtatildi" in (error_msg or "")
                or "Servis-1 to'xtatildi" in (error_msg or "")
                or error_type in ('pr_not_merged', 'pr_not_found', 'tz_too_short')
            )
            if should_write_comment:
                try:
                    from services.webhook.jira_webhook_handler import get_adf_formatter
                    from services.webhook.error_handler import _write_error_comment
                    from utils.jira.jira_comment_writer import JiraCommentWriter
                    from utils.auth.auth_db import get_company_credentials
                    from utils.auth.auth_db import get_company_webhook_credentials
                    _creds = get_company_webhook_credentials(company_id)
                    writer = JiraCommentWriter(
                        server=_creds['jira_server'],
                        email=_creds['jira_email'],
                        token=_creds['jira_token'],
                    )
                    adf_formatter = get_adf_formatter()
                    reason = error_msg.strip() if error_msg else (
                        "TZ (description) yetarli emas. Testcase yaratish to'xtatildi."
                    )
                    panel_type = "error" if error_type == 'pr_not_merged' else "warning"
                    await _write_error_comment(
                        task_key, reason, writer, adf_formatter,
                        service="Servis-2", panel_type=panel_type
                    )
                    log.jira_comment_added(task_key, f"{panel_type.capitalize()} ADF")
                except Exception as e:
                    log.warning(f"[{task_key}] JIRA ogohlantirish comment yozilmadi: {e}")
            return False, error_msg

        if not result.test_cases:
            details = f"pr_count={result.pr_count} | tz_len={len(result.tz_content) if result.tz_content else 0} | warnings={result.warnings}"
            log.warning(f"[{task_key}] No test cases generated | {details}")
            return False, "No test cases generated"

        # 4. JIRA ga yozish
        success, message = _write_testcases_comment(
            task_key=task_key,
            result=result,
            use_adf=tc_settings.use_adf_format,
            pr_details=result.pr_details,
            pr_count=result.pr_count,
            files_changed=result.files_changed,
            footer_text=tc_settings.testcase_footer_text,
            company_id=company_id,
        )

        return success, message

    except Exception as e:
        error_msg = f"Testcase generation error: {str(e)}"
        log.log_error(task_key, "testcase generation", str(e))
        return False, error_msg


def _write_testcases_comment(
        task_key: str,
        result,
        use_adf: bool = True,
        pr_details: list = None,
        pr_count: int = 0,
        files_changed: int = 0,
        footer_text: str = None,
        company_id: int = None,
) -> Tuple[bool, str]:
    """
    Test case'larni JIRA ga comment sifatida yozish

    Args:
        task_key: JIRA task key
        result: TestCaseGenerationResult
        use_adf: ADF format ishlatish
        footer_text: Comment footer matni (None bo'lsa global settingsdan)
        company_id: Kompaniya ID — JIRA credentials olish uchun

    Returns:
        Tuple[bool, str]: (success, message)
    """
    from utils.jira.jira_comment_writer import JiraCommentWriter
    from utils.jira.testcase_adf_formatter import TestcaseADFFormatter
    from utils.auth.auth_db import get_company_credentials

    try:
        from utils.auth.auth_db import get_company_webhook_credentials
        creds = get_company_webhook_credentials(company_id)
        writer = JiraCommentWriter(
            server=creds['jira_server'],
            email=creds['jira_email'],
            token=creds['jira_token'],
        )
        formatter = TestcaseADFFormatter()

        if footer_text is None:
            from config.app_settings import get_app_settings as _get_settings
            footer_text = _get_settings().webhook_testcase.testcase_footer_text
        _tc_footer = footer_text

        if use_adf:
            # ADF format
            adf_doc = formatter.build_testcase_document(
                task_key=task_key,
                test_cases=result.test_cases,
                footer_text=_tc_footer,
                pr_details=pr_details or [],
                pr_count=pr_count,
                files_changed=files_changed,
                test_scenarios=getattr(result, "test_scenarios", []),
            )
            success = writer.add_comment_adf(task_key, adf_doc)

            if not success:
                # Fallback to simple format
                log.warning(f"[{task_key}] ADF failed, falling back to simple format")
                simple_comment = formatter.build_simple_comment(
                    task_key=task_key,
                    test_cases=result.test_cases,
                    test_scenarios=getattr(result, "test_scenarios", []),
                )
                success = writer.add_comment(task_key, simple_comment)
        else:
            # Simple format
            simple_comment = formatter.build_simple_comment(
                task_key=task_key,
                test_cases=result.test_cases,
                test_scenarios=getattr(result, "test_scenarios", []),
            )
            success = writer.add_comment(task_key, simple_comment)

        if success:
            message = f"Successfully wrote {len(result.test_cases)} test cases to JIRA"
            return True, message
        else:
            message = "Failed to write comment to JIRA"
            log.jira_comment_failed(task_key, message)
            return False, message

    except Exception as e:
        message = f"Error writing to JIRA: {str(e)}"
        log.log_error(task_key, "JIRA comment write", str(e))
        return False, message


def generate_testcases_sync(
        task_key: str,
        new_status: str
) -> Tuple[bool, str]:
    """
    Sinxron versiya - webhook'dan chaqirish uchun

    Args:
        task_key: JIRA task key
        new_status: Yangi status

    Returns:
        Tuple[bool, str]: (success, message)
    """
    import asyncio

    try:
        # Async funksiyani sinxron chaqirish
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Agar loop allaqachon ishlayotgan bo'lsa
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    check_and_generate_testcases(task_key, new_status)
                )
                # Get timeout from settings
                try:
                    from config.app_settings import get_app_settings
                    executor_timeout = get_app_settings(force_reload=False).queue.executor_timeout
                except Exception:
                    executor_timeout = 120  # Default fallback (2 daqiqa)
                
                return future.result(timeout=executor_timeout)
        else:
            return loop.run_until_complete(
                check_and_generate_testcases(task_key, new_status)
            )
    except Exception as e:
        log.log_error(task_key, "sync execution", str(e))
        return False, f"Execution error: {str(e)}"


def is_testcase_trigger_status(status: str, app_settings=None) -> bool:
    """
    Berilgan status testcase trigger ekanligini tekshirish.

    Args:
        status: Tekshiriladigan status
        app_settings: Tayyor AppSettings (None bo'lsa global yuklanadi)

    Returns:
        bool: True agar trigger status bo'lsa
    """
    from config.app_settings import get_app_settings

    if app_settings is None:
        app_settings = get_app_settings()
    tc_settings = app_settings.webhook_testcase

    if not tc_settings.auto_comment_enabled:
        return False

    trigger_statuses = tc_settings.get_trigger_statuses()
    return status.lower() in [s.lower() for s in trigger_statuses]
