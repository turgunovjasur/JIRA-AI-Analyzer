"""
Shared full-analysis policy helpers.

Checker va Testcase servislarida bir xil qoidani ishlatish uchun umumiy modul:
- Partial analysis taqiqlanadi
- Overload/tech xatolarda standart banner payload qaytariladi
"""

from __future__ import annotations

from typing import Any, Dict, Optional

_OVERLOAD_KEYWORDS = (
    "overloaded",
    "rate",
    "resource_exhausted",
    "429",
    "high demand",
    "token limit",
    "context length",
)


def _normalize_error(error_message: str) -> str:
    return (error_message or "").strip().lower()


def classify_full_blocked_code(error_message: str) -> str:
    text = _normalize_error(error_message)
    if any(key in text for key in _OVERLOAD_KEYWORDS):
        return "FULL_BLOCKED_OVERLOAD"
    return "FULL_BLOCKED_TECHNICAL"


def build_status_banner(
    *,
    level: str,
    code: str,
    title: str,
    message: str,
    meta: Optional[Dict[str, Any]] = None,
    actions: Optional[list[str]] = None,
) -> Dict[str, Any]:
    return {
        "level": (level or "error").strip().lower(),
        "code": code,
        "title": title,
        "message": message,
        "meta": meta or {},
        "actions": actions or [],
    }


def build_full_policy_input_violation(
    *,
    module_name: str,
    task_key: str,
    max_files: Optional[int],
    show_full_diff: bool,
) -> Dict[str, Any]:
    title = "To'liq tahlil siyosati buzildi"
    message = (
        "Servis faqat FULL rejimda ishlaydi: max_files cheklanmasligi va "
        "to'liq diff yoqilgan bo'lishi shart."
    )
    meta = {
        "module": module_name,
        "task_key": task_key,
        "max_files": max_files,
        "show_full_diff": bool(show_full_diff),
    }
    return build_status_banner(
        level="error",
        code="FULL_POLICY_INPUT_INVALID",
        title=title,
        message=message,
        meta=meta,
        actions=["Sozlamani to'g'rilang va qayta urinib ko'ring"],
    )


def build_full_analysis_blocked(
    *,
    module_name: str,
    task_key: str,
    error_message: str,
    files_total: Optional[int],
    files_included: Optional[int],
    prompt_size_chars: Optional[int],
    model: Optional[str],
) -> Dict[str, Any]:
    code = classify_full_blocked_code(error_message)
    title = "To'liq tahlil bajarilmadi"

    if code == "FULL_BLOCKED_OVERLOAD":
        message = "O'zgarishlar hajmi AI limitidan oshdi. Noto'liq tahlil berilmadi."
    else:
        message = "AI texnik xatosi sabab to'liq tahlil yakunlanmadi. Noto'liq tahlil berilmadi."

    meta = {
        "module": module_name,
        "task_key": task_key,
        "files_total": files_total,
        "files_included": files_included,
        "prompt_size_chars": prompt_size_chars,
        "model": model,
    }

    banner = build_status_banner(
        level="error",
        code=code,
        title=title,
        message=message,
        meta=meta,
        actions=["Modelni o'zgartirish", "Qayta urinish"],
    )

    detail = (
        f"{title}: {message} "
        f"(task={task_key}, files={files_included}/{files_total}, "
        f"prompt={prompt_size_chars} chars, model={model})"
    )
    return {"error_message": detail, "status_banner": banner}
