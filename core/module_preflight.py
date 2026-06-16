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
    from core import TZHelper

    ctx = PreflightContext(task_key=task_key)
    notify = update_status or (lambda *_: None)

    # ── jira_fetch ──
    if policy.jira_fetch:
        notify("progress", "JIRA task ma'lumotlari olinmoqda...")
        task_details = service.jira.get_task_details(
            task_key,
            include_pr_urls=policy.pr_check,
            include_figma_links=policy.figma_check,
        )
        if not task_details:
            ctx._set("jira_fetch", "fail", f"{task_key} topilmadi")
            return ctx
        ctx.task_details = task_details
        ctx._set("jira_fetch", "ok")
    else:
        ctx._set("jira_fetch", "skipped")

    task_details = ctx.task_details or {}

    # ── min_tz_check ── (fakt yozadi, block qarorini modul qiladi)
    if policy.min_tz_check:
        ctx.tz_chars = len((task_details.get("description") or "").strip())
        ctx.too_short = bool(min_tz_chars > 0 and ctx.tz_chars < min_tz_chars)
        ctx._set("min_tz_check", "fail" if ctx.too_short else "ok", f"{ctx.tz_chars}/{min_tz_chars}")
    else:
        ctx._set("min_tz_check", "skipped")

    # ── pr_check ── (har check o'z credential'iga bog'liq: GitHub)
    if policy.pr_check:
        notify("progress", "PR ma'lumotlari olinmoqda...")
        try:
            pr_helper = getattr(service, "pr_helper", None)
            if pr_helper is None:
                from core import PRHelper
                pr_helper = PRHelper(service.github)
            pr_info = pr_helper.get_pr_full_info(
                task_key, task_details, status_callback=update_status, use_smart_patch=use_smart_patch,
            )
            if pr_info:
                ctx.pr_info = pr_info
                ctx._set("pr_check", "ok")
            else:
                ctx._set("pr_check", "fail", "PR topilmadi")
        except Exception as exc:  # PRNotMergedError kabi — reason mapping modulda
            ctx._set("pr_check", "fail", str(exc) or exc.__class__.__name__)
    else:
        ctx._set("pr_check", "skipped")

    # ── figma_check ── (FAIL-SAFE: token/ruxsat yo'q bo'lsa block emas, warning)
    if policy.figma_check and figma_enabled:
        notify("progress", "Figma ma'lumotlari olinmoqda...")
        ctx.figma_data = fetch_figma_summaries(service, task_details, notify)
        ctx._set("figma_check", "ok" if ctx.figma_data else "warning",
                 "" if ctx.figma_data else "Figma ma'lumoti yo'q")
    else:
        ctx._set("figma_check", "skipped")

    # ── comment_fetch + tz_build ──
    # comment_analysis faqat keyingi agentlar uchun (Agent1 ga BERILMAYDI).
    if policy.tz_build:
        notify("progress", "TZ va comment'lar tahlil qilinmoqda...")
        comments_on = bool(policy.comment_fetch and read_comments_enabled)
        if comments_on:
            max_c = max_comments_to_read if (max_comments_to_read and max_comments_to_read > 0) else None
            tz_content, comment_analysis = TZHelper.format_tz_with_comments(task_details, max_comments=max_c)
        else:
            td = dict(task_details)
            td["comments"] = []
            tz_content, comment_analysis = TZHelper.format_tz_with_comments(td)
        ctx.tz_content = tz_content
        ctx.comment_analysis = comment_analysis
        ctx.task_overview = TZHelper.create_task_overview(task_details, comment_analysis, None)
        ctx._set("tz_build", "ok")
        ctx._set("comment_fetch", "ok" if comments_on else "skipped")
    else:
        ctx._set("tz_build", "skipped")
        ctx._set("comment_fetch", "skipped")

    return ctx


def fetch_figma_summaries(service: Any, task_details: dict, notify: Optional[Callable] = None) -> Optional[dict]:
    """Figma summary'larni olish (FAIL-SAFE). Token/ruxsat bo'lmasa None.

    Checker va testcase (builder orqali) UCHUN YAGONA implementatsiya — figma fetch
    boshqa joyda takrorlanmaydi. Xulq checker'ning eski _get_figma_data'si bilan bir xil.
    """
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
                    "file_key": file_key, "name": link["name"], "url": link["url"],
                    "summary": "Token topilmadi yoki ruxsat yo'q",
                })
                continue
            try:
                summary = client.get_file_summary(file_key, node_id=link.get("node_id"))
                summaries.append({
                    "file_key": file_key, "name": link["name"], "url": link["url"],
                    "summary": summary,
                })
            except Exception as exc:
                notify("warning", f"Figma: {link['name']} olinmadi")
                summaries.append({
                    "file_key": file_key, "name": link["name"], "url": link["url"],
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
        log.warning(f"Figma: ishlayotgan token topilmadi | file_key={file_key}")
    except Exception as exc:
        log.warning(f"Figma client init failed: {exc}")
    return None
