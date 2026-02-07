# services/testcase_webhook_service.py
"""
Testcase Webhook Service

Task statusiga ko'ra avtomatik test case yaratish va JIRA ga yozish.
Ready to Test statusga tushganda ishga tushadi.

Author: JASUR TURGUNOV
Version: 1.0
"""
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


async def check_and_generate_testcases(
        task_key: str,
        new_status: str
) -> Tuple[bool, str]:
    """
    Status o'zgarganda avtomatik test case yaratish va comment yozish

    Args:
        task_key: JIRA task key (masalan: DEV-1234)
        new_status: Yangi status nomi

    Returns:
        Tuple[bool, str]: (success, message)

    Flow:
    1. Settings tekshirish (auto_comment_enabled?)
    2. Status trigger bo'lsa - test case'lar yaratish
    3. JIRA ga comment yozish
    """
    from config.app_settings import get_app_settings

    settings = get_app_settings()
    tc_settings = settings.testcase_generator

    # 1. Auto-comment yoqilganmi?
    if not tc_settings.auto_comment_enabled:
        logger.info(f"[{task_key}] Testcase auto-comment disabled, skipping")
        return False, "Auto-comment disabled"

    # 2. Trigger status tekshirish
    trigger_statuses = tc_settings.get_trigger_statuses()
    if new_status not in trigger_statuses:
        logger.info(f"[{task_key}] Status '{new_status}' not in trigger list: {trigger_statuses}")
        return False, f"Status '{new_status}' is not a trigger"

    logger.info(f"[{task_key}] Generating testcases for status: {new_status}")

    try:
        # 3. Test case'lar yaratish
        from services.testcase_generator_service import TestCaseGeneratorService

        service = TestCaseGeneratorService()

        result = service.generate_test_cases(
            task_key=task_key,
            include_pr=tc_settings.default_include_pr,
            use_smart_patch=tc_settings.default_use_smart_patch,
            test_types=tc_settings.default_test_types,
            custom_context="",
            status_callback=lambda t, m: logger.info(f"[{task_key}] {t}: {m}")
        )

        if not result.success:
            error_msg = f"Test case generation failed: {result.error_message}"
            logger.error(f"[{task_key}] {error_msg}")
            return False, error_msg

        if not result.test_cases:
            logger.warning(
                "[%s] No test cases generated | pr_count=%d | tz_content_len=%d | warnings=%s",
                task_key,
                result.pr_count,
                len(result.tz_content) if result.tz_content else 0,
                result.warnings
            )
            return False, "No test cases generated"

        logger.info(f"[{task_key}] Generated {len(result.test_cases)} test cases")

        # 4. JIRA ga yozish
        success, message = _write_testcases_comment(
            task_key=task_key,
            result=result,
            use_adf=tc_settings.use_adf_format
        )

        return success, message

    except Exception as e:
        error_msg = f"Testcase generation error: {str(e)}"
        logger.exception(f"[{task_key}] {error_msg}")
        return False, error_msg


def _write_testcases_comment(
        task_key: str,
        result,
        use_adf: bool = True
) -> Tuple[bool, str]:
    """
    Test case'larni JIRA ga comment sifatida yozish

    Args:
        task_key: JIRA task key
        result: TestCaseGenerationResult
        use_adf: ADF format ishlatish

    Returns:
        Tuple[bool, str]: (success, message)
    """
    from utils.jira.jira_comment_writer import JiraCommentWriter
    from utils.jira.testcase_adf_formatter import TestcaseADFFormatter

    try:
        writer = JiraCommentWriter()
        formatter = TestcaseADFFormatter()

        # Footer text settings-dan olish
        from config.app_settings import get_app_settings as _get_settings
        _tc_footer = _get_settings().testcase_generator.testcase_footer_text

        if use_adf:
            # ADF format
            adf_doc = formatter.build_testcase_document(
                task_key=task_key,
                test_cases=result.test_cases,
                footer_text=_tc_footer
            )
            success = writer.add_comment_adf(task_key, adf_doc)

            if not success:
                # Fallback to simple format
                logger.warning(f"[{task_key}] ADF failed, falling back to simple format")
                simple_comment = formatter.build_simple_comment(
                    task_key=task_key,
                    test_cases=result.test_cases
                )
                success = writer.add_comment(task_key, simple_comment)
        else:
            # Simple format
            simple_comment = formatter.build_simple_comment(
                task_key=task_key,
                test_cases=result.test_cases
            )
            success = writer.add_comment(task_key, simple_comment)

        if success:
            message = f"Successfully wrote {len(result.test_cases)} test cases to JIRA"
            logger.info(f"[{task_key}] {message}")
            return True, message
        else:
            message = "Failed to write comment to JIRA"
            logger.error(f"[{task_key}] {message}")
            return False, message

    except Exception as e:
        message = f"Error writing to JIRA: {str(e)}"
        logger.exception(f"[{task_key}] {message}")
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
                return future.result(timeout=120)  # 2 daqiqa timeout
        else:
            return loop.run_until_complete(
                check_and_generate_testcases(task_key, new_status)
            )
    except Exception as e:
        logger.exception(f"[{task_key}] Sync execution error: {str(e)}")
        return False, f"Execution error: {str(e)}"


def is_testcase_trigger_status(status: str) -> bool:
    """
    Berilgan status testcase trigger ekanligini tekshirish

    Args:
        status: Tekshiriladigan status

    Returns:
        bool: True agar trigger status bo'lsa
    """
    from config.app_settings import get_app_settings

    settings = get_app_settings()
    tc_settings = settings.testcase_generator

    if not tc_settings.auto_comment_enabled:
        return False

    trigger_statuses = tc_settings.get_trigger_statuses()
    return status in trigger_statuses
