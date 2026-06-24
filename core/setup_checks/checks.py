from __future__ import annotations

from typing import Any, Callable, Optional

from core import PRHelper, TZHelper
from core.logger import get_logger
from core.setup_checks.engine import SetupCheckResult, SetupContext

log = get_logger("setup.checks")


def ok(check_id: str, label: str, detail: str = "", **meta: Any) -> SetupCheckResult:
    return SetupCheckResult(id=check_id, label=label, status="ok", detail=detail, meta=meta)


def fail(
    check_id: str,
    label: str,
    detail: str = "",
    *,
    message: str = "",
    action: str = "",
    blocking: bool = True,
    **meta: Any,
) -> SetupCheckResult:
    return SetupCheckResult(
        id=check_id,
        label=label,
        status="fail",
        detail=detail,
        message=message or detail,
        action=action,
        blocking=blocking,
        meta=meta,
    )


def warning(check_id: str, label: str, detail: str = "", **meta: Any) -> SetupCheckResult:
    return SetupCheckResult(id=check_id, label=label, status="warning", detail=detail, meta=meta)


def skipped(check_id: str, label: str, detail: str = "", **meta: Any) -> SetupCheckResult:
    return SetupCheckResult(id=check_id, label=label, status="skipped", detail=detail, meta=meta)


def check_jira_fetch(ctx: SetupContext) -> SetupCheckResult:
    if ctx.task_details:
        ctx.notify("info", "JIRA task ma'lumotlari webhook snapshotdan olindi")
        return ok("jira_fetch", "JIRA task", "preloaded")

    if ctx.service is None:
        return fail("jira_fetch", "JIRA task", "service mavjud emas")

    ctx.notify("progress", "JIRA task ma'lumotlari olinmoqda...")
    task_details = ctx.service.jira.get_task_details(
        ctx.task_key,
        include_pr_urls=ctx.include_pr_urls,
        include_figma_links=ctx.include_figma_links,
        max_comments_to_read=int(ctx.max_comments_to_read or 0),
    )
    if not task_details:
        return fail("jira_fetch", "JIRA task", f"{ctx.task_key} topilmadi")
    ctx.task_details = task_details
    return ok("jira_fetch", "JIRA task")


def check_min_tz(ctx: SetupContext) -> SetupCheckResult:
    if not ctx.task_details:
        return skipped("min_tz_check", "Min TZ belgilari", "JIRA task yo'q")

    description = str((ctx.task_details or {}).get("description") or "").strip()
    ctx.tz_chars = len(description)
    ctx.too_short = bool(ctx.min_tz_chars > 0 and ctx.tz_chars < ctx.min_tz_chars)
    detail = f"{ctx.tz_chars}/{ctx.min_tz_chars}"
    if ctx.too_short:
        return fail("min_tz_check", "Min TZ belgilari", detail)
    return ok("min_tz_check", "Min TZ belgilari", detail)


def check_pr(ctx: SetupContext) -> SetupCheckResult:
    if not ctx.task_details:
        return skipped("pr_check", "PR ma'lumotlari", "JIRA task yo'q")

    ctx.notify("progress", "PR ma'lumotlari olinmoqda...")
    try:
        pr_helper = getattr(ctx.service, "pr_helper", None)
        if pr_helper is None:
            pr_helper = PRHelper(ctx.service.github)
        pr_info = pr_helper.get_pr_full_info(
            ctx.task_key,
            ctx.task_details,
            status_callback=ctx.update_status,
            use_smart_patch=ctx.use_smart_patch,
        )
    except Exception as exc:
        ctx.errors["pr_check"] = exc
        return fail("pr_check", "PR ma'lumotlari", str(exc) or exc.__class__.__name__)

    if not pr_info:
        return fail("pr_check", "PR ma'lumotlari", "PR topilmadi")
    ctx.pr_info = pr_info
    return ok("pr_check", "PR ma'lumotlari")


def check_figma(ctx: SetupContext) -> SetupCheckResult:
    if not ctx.figma_enabled:
        return skipped("figma_check", "Figma ma'lumotlari")
    if not ctx.task_details:
        return skipped("figma_check", "Figma ma'lumotlari", "JIRA task yo'q")

    ctx.notify("progress", "Figma ma'lumotlari olinmoqda...")
    ctx.figma_data = fetch_figma_summaries(ctx.service, ctx.task_details, ctx.notify)
    if ctx.figma_data:
        return ok("figma_check", "Figma ma'lumotlari")
    return warning("figma_check", "Figma ma'lumotlari", "Figma ma'lumoti yo'q")


def check_tz_build(ctx: SetupContext) -> SetupCheckResult:
    if not ctx.task_details:
        return skipped("tz_build", "TZ content", "JIRA task yo'q")

    ctx.notify("progress", "TZ va comment'lar tahlil qilinmoqda...")
    comments_on = bool(ctx.read_comments_enabled)
    if comments_on:
        max_c = ctx.max_comments_to_read if (ctx.max_comments_to_read and ctx.max_comments_to_read > 0) else None
        ctx.tz_content, ctx.comment_analysis = TZHelper.format_tz_with_comments(
            ctx.task_details,
            max_comments=max_c,
            exclude_ai_comments=ctx.exclude_ai_comments,
        )
    else:
        task_no_comments = dict(ctx.task_details)
        task_no_comments["comments"] = []
        ctx.tz_content, ctx.comment_analysis = TZHelper.format_tz_with_comments(
            task_no_comments,
            exclude_ai_comments=ctx.exclude_ai_comments,
        )
    ctx.task_overview = TZHelper.create_task_overview(ctx.task_details, ctx.comment_analysis, None)
    if ctx.comment_analysis.get("has_changes"):
        ctx.notify("warning", ctx.comment_analysis.get("summary") or "")
    filtered_ai_comments = int(ctx.comment_analysis.get("filtered_out_ai_comments") or 0)
    if filtered_ai_comments > 0:
        ctx.notify("info", f"Promptdan {filtered_ai_comments} ta oldingi AI comment chiqarib tashlandi")
    return ok(
        "tz_build",
        "TZ content",
        comment_fetch="ok" if comments_on else "skipped",
    )


def check_service2_db_guard(ctx: SetupContext) -> SetupCheckResult:
    task_db = ctx.task_db or {}
    if not task_db:
        return fail("service2_db_guard", "Service2 DB guard", "task_not_found", blocking=True)

    service1_status = task_db.get("service1_status", "pending")
    service2_status = task_db.get("service2_status", "pending")
    compliance_score = task_db.get("compliance_score")
    task_status = task_db.get("task_status", "none")

    if service1_status not in ("done", "skip", "error"):
        return fail(
            "service2_db_guard",
            "Service2 DB guard",
            f"service1_not_ready:{service1_status}",
            blocking=True,
            service1_status=service1_status,
        )
    if service1_status == "error" and service2_status != "pending":
        return fail(
            "service2_db_guard",
            "Service2 DB guard",
            "service1_error_not_pending",
            blocking=True,
            service1_status=service1_status,
            service2_status=service2_status,
        )
    if service2_status == "done":
        return fail("service2_db_guard", "Service2 DB guard", "service2_done", blocking=True)
    if ctx.company_id is None:
        return fail("service2_db_guard", "Service2 DB guard", "company_missing", blocking=True)
    if compliance_score is not None and ctx.threshold is not None and compliance_score < ctx.threshold:
        return fail(
            "service2_db_guard",
            "Service2 DB guard",
            "score_below_threshold",
            blocking=True,
            compliance_score=compliance_score,
            threshold=ctx.threshold,
        )
    if task_status == "returned":
        return fail("service2_db_guard", "Service2 DB guard", "task_returned", blocking=True)
    return ok("service2_db_guard", "Service2 DB guard")


CHECK_REGISTRY = {
    "jira_fetch": check_jira_fetch,
    "min_tz_check": check_min_tz,
    "pr_check": check_pr,
    "figma_check": check_figma,
    "tz_build": check_tz_build,
    "service2_db_guard": check_service2_db_guard,
}


def fetch_figma_summaries(service: Any, task_details: dict, notify: Optional[Callable] = None) -> Optional[dict]:
    """Figma summary'larni olish (FAIL-SAFE). Token/ruxsat bo'lmasa None."""
    notify = notify or (lambda *_: None)
    try:
        figma_links = task_details.get("figma_links", [])
        log.info(f"Figma: task da {len(figma_links)} ta figma_link topildi")
        if not figma_links:
            return None
        summaries = []
        for link in figma_links:
            file_key = link["file_key"]
            client = _figma_client_for_file(service, file_key)
            if not client:
                notify("warning", f"Figma: {link['name']} — ishlayotgan token topilmadi")
                summaries.append({
                    "file_key": file_key,
                    "name": link["name"],
                    "url": link["url"],
                    "summary": "Token topilmadi yoki ruxsat yo'q",
                })
                continue
            try:
                summary = client.get_file_summary(file_key, node_id=link.get("node_id"))
                summaries.append({
                    "file_key": file_key,
                    "name": link["name"],
                    "url": link["url"],
                    "summary": summary,
                })
            except Exception as exc:
                notify("warning", f"Figma: {link['name']} olinmadi")
                summaries.append({
                    "file_key": file_key,
                    "name": link["name"],
                    "url": link["url"],
                    "summary": f"Error: {str(exc)}",
                })
        return {"links": figma_links, "summaries": summaries, "count": len(summaries)}
    except Exception as exc:
        notify("warning", f"Figma xatolik: {str(exc)}")
        return None


def _figma_client_for_file(service: Any, file_key: str):
    """Berilgan file_key uchun ishlayotgan tokenni topib FigmaClient qaytaradi (fail-safe)."""
    try:
        from utils.figma.figma_client import FigmaClient

        creds = service._get_creds()
        figma_tokens = creds.get("figma_tokens", [])
        log.info(
            f"Figma creds: figma_tokens={len(figma_tokens)} ta | "
            f"company_id={service._company_id} | user_id={service._user_id}"
        )
        if not figma_tokens:
            figma_token_single = creds.get("figma_token", "")
            has_old = "bor" if figma_token_single else "yoq"
            log.warning(f"Figma: figma_tokens bosh | figma_token (eski)={has_old}")
            return None
        working_token = FigmaClient.find_working_token(figma_tokens, file_key)
        if working_token:
            return FigmaClient(access_token=working_token)
        return None
    except Exception as exc:
        log.warning(f"Figma client yaratilmadi: {exc}")
        return None
