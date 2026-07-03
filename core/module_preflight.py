"""
Module Preflight — barcha modullar (checker, testcase, kelajakdagi yangilar)
uchun UMUMIY setup check'lar.

Maqsad: setup logikasi bir marta yoziladi. Har modul faqat policy bilan
o'ziga kerakli check'larni true/false qiladi (masalan checker: pr_check=True,
testcase: pr_check=False).

Muhim chegara:
- Builder faqat MA'LUMOT yig'adi va har check natijasini FAKT sifatida yozadi.
- Builder BLOCK qaror chiqarmaydi. Block/xato/reason-code'ni har modul o'zi
  PreflightContext.failed(...) ga qarab qaror qiladi (checker'ning maxsus reason
  kodlari buzilmasligi uchun).
- Tenant scope: builder `service` orqali ishlaydi, service esa o'z
  company_id/user_id credential'larini olib yuradi — barcha fetch shu scope'da.

Qat'iy qoida (toggle EMAS): comment_analysis Agent1 ga berilmaydi. Builder uni
keyingi agentlar (Agent2/Agent3) uchun PreflightContext.comment_analysis da
qoldiradi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from core.logger import get_logger
from core.setup_checks.checks import CHECK_REGISTRY
from core.setup_checks.engine import SetupContext, run_setup_checks
from core.setup_checks.profiles import profile_from_module_policy

log = get_logger("module.preflight")


@dataclass(frozen=True)
class ModulePreflightPolicy:
    """Modul setup profili — qaysi check'lar yoqilgan (STRUKTURAVIY).

    Bu qiymatlar modul tabiatini bildiradi va KODDA e'lon qilinadi (o'zgarmaydi).
    Sozlanadigan qiymatlar (min_tz_chars, figma on/off, comment limiti) bu yerga
    EMAS — ular settings'dan run_module_preflight() parametrlari sifatida keladi.
    """
    jira_fetch: bool = True
    min_tz_check: bool = False
    pr_check: bool = False
    figma_check: bool = False
    comment_fetch: bool = False
    tz_build: bool = True


@dataclass
class PreflightContext:
    """Builder yig'gan ma'lumot + har check natijasi (FAKT)."""
    task_key: str
    task_details: Optional[dict] = None
    tz_content: str = ""
    task_overview: str = ""
    comment_analysis: dict = field(default_factory=dict)
    figma_data: Optional[dict] = None
    pr_info: Optional[dict] = None
    tz_chars: int = 0
    too_short: bool = False
    warnings: list = field(default_factory=list)
    # {check_name: {"status": "ok|fail|warning|skipped", "detail": str}}
    checks: dict = field(default_factory=dict)

    def _set(self, name: str, status: str, detail: str = "") -> None:
        self.checks[name] = {"status": status, "detail": detail}

    def status(self, name: str) -> str:
        return self.checks.get(name, {}).get("status", "skipped")

    def failed(self, name: str) -> bool:
        return self.status(name) == "fail"

    def detail(self, name: str) -> str:
        return self.checks.get(name, {}).get("detail", "")


def run_module_preflight(
    service: Any,
    *,
    task_key: str,
    policy: ModulePreflightPolicy,
    min_tz_chars: int = 0,
    read_comments_enabled: bool = True,
    max_comments_to_read: int = 0,
    figma_enabled: bool = False,
    use_smart_patch: bool = False,
    update_status: Optional[Callable[[str, str], None]] = None,
) -> PreflightContext:
    """Modul setup check'larini policy bo'yicha bajaradi va PreflightContext qaytaradi.

    Args:
        service: BaseService merosxo'ri (jira/github/credential scope'ini olib yuradi).
        policy: qaysi check'lar yoqilgan (modul profili).
        min_tz_chars / figma_enabled / read_comments_enabled / max_comments_to_read:
            settings'dan kelgan TUNABLE qiymatlar (modul hal qiladi).
    """
    setup_ctx = SetupContext(
        task_key=task_key,
        source="module",
        service=service,
        min_tz_chars=int(min_tz_chars or 0),
        read_comments_enabled=bool(policy.comment_fetch and read_comments_enabled),
        max_comments_to_read=int(max_comments_to_read or 0),
        figma_enabled=bool(policy.figma_check and figma_enabled),
        include_pr_urls=bool(policy.pr_check),
        include_figma_links=bool(policy.figma_check),
        use_smart_patch=bool(use_smart_patch),
        update_status=update_status,
    )
    setup_ctx = run_setup_checks(
        profile_from_module_policy(policy),
        setup_ctx,
        CHECK_REGISTRY,
        stop_on_blocking_fail=True,
    )

    ctx = PreflightContext(task_key=task_key)
    ctx.task_details = setup_ctx.task_details
    ctx.tz_content = setup_ctx.tz_content
    ctx.task_overview = setup_ctx.task_overview
    ctx.comment_analysis = setup_ctx.comment_analysis
    ctx.figma_data = setup_ctx.figma_data
    ctx.pr_info = setup_ctx.pr_info
    ctx.tz_chars = setup_ctx.tz_chars
    ctx.too_short = setup_ctx.too_short
    ctx.warnings = setup_ctx.warnings
    ctx.checks = {
        key: {"status": value.get("status"), "detail": value.get("detail", "")}
        for key, value in setup_ctx.checks.items()
    }
    if setup_ctx.status("tz_build") == "ok":
        comments_on = bool(policy.comment_fetch and read_comments_enabled)
        ctx._set("comment_fetch", "ok" if comments_on else "skipped")
    elif not policy.tz_build:
        ctx._set("tz_build", "skipped")
        ctx._set("comment_fetch", "skipped")
    return ctx
