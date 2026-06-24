from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from core.logger import get_logger

log = get_logger("setup.checks")


@dataclass
class SetupCheckResult:
    id: str
    label: str
    status: str
    detail: str = ""
    message: str = ""
    action: str = ""
    blocking: bool = False
    meta: dict[str, Any] = field(default_factory=dict)

    def is_blocking_failure(self) -> bool:
        return self.status == "fail" and self.blocking


@dataclass
class SetupContext:
    task_key: str
    source: str = "manual"
    module_key: str = ""
    service_key: str = ""
    service: Any = None
    company_id: int | None = None
    user_id: int | None = None
    task_details: dict | None = None
    task_db: dict | None = None
    threshold: int | float | None = None
    min_tz_chars: int = 0
    read_comments_enabled: bool = True
    max_comments_to_read: int = 0
    figma_enabled: bool = False
    include_pr_urls: bool = False
    include_figma_links: bool = False
    use_smart_patch: bool = False
    exclude_ai_comments: bool = False
    update_status: Callable[[str, str], None] | None = None
    pr_info: dict | None = None
    figma_data: dict | None = None
    tz_content: str = ""
    task_overview: str = ""
    comment_analysis: dict = field(default_factory=dict)
    tz_chars: int = 0
    too_short: bool = False
    warnings: list = field(default_factory=list)
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    results: list[SetupCheckResult] = field(default_factory=list)
    errors: dict[str, Exception] = field(default_factory=dict)

    def notify(self, level: str, message: str) -> None:
        if self.update_status:
            self.update_status(level, message)

    def set_result(self, result: SetupCheckResult) -> None:
        self.results.append(result)
        self.checks[result.id] = {
            "status": result.status,
            "detail": result.detail,
            "message": result.message,
            "action": result.action,
            "blocking": result.blocking,
            "meta": result.meta,
        }

    def status(self, check_id: str) -> str:
        return self.checks.get(check_id, {}).get("status", "skipped")

    def failed(self, check_id: str) -> bool:
        return self.status(check_id) == "fail"

    def detail(self, check_id: str) -> str:
        return self.checks.get(check_id, {}).get("detail", "")


CheckFn = Callable[[SetupContext], SetupCheckResult]


def run_setup_checks(
    profile: Iterable[str],
    ctx: SetupContext,
    registry: dict[str, CheckFn],
    *,
    stop_on_blocking_fail: bool = True,
) -> SetupContext:
    for check_id in profile:
        check = registry.get(check_id)
        if check is None:
            result = SetupCheckResult(
                id=check_id,
                label=check_id,
                status="fail",
                detail="check registered emas",
                message=f"Setup check topilmadi: {check_id}",
                blocking=True,
            )
            ctx.set_result(result)
            if stop_on_blocking_fail:
                break
            continue

        try:
            result = check(ctx)
        except Exception as exc:
            log.error(f"setup check failed unexpectedly | check={check_id} | err={exc}", exc_info=True)
            ctx.errors[check_id] = exc
            result = SetupCheckResult(
                id=check_id,
                label=check_id,
                status="fail",
                detail=str(exc) or exc.__class__.__name__,
                message=str(exc) or f"{check_id} xato berdi",
                blocking=True,
            )
        ctx.set_result(result)
        if result.is_blocking_failure() and stop_on_blocking_fail:
            break

    return ctx
