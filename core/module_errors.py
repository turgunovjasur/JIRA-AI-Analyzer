"""Central module error payload helpers.

Run-start, preflight and later module errors should use the same JSON contract so
frontend modules can render and copy failures consistently.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ModuleCheck:
    id: str
    label: str
    status: str
    message: str = ""
    code: str = ""
    action: str = ""
    blocking: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_module_status_banner(
    *,
    code: str,
    title: str,
    message: str,
    module_key: str,
    task_key: str | None = None,
    level: str = "error",
    actions: list[str] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_meta = {
        "module_key": module_key,
        **({"task_key": task_key} if task_key else {}),
        **(meta or {}),
    }
    return {
        "level": level,
        "code": code,
        "title": title,
        "message": message,
        "meta": clean_meta,
        "actions": actions or [],
    }


def build_preflight_error_payload(
    *,
    module_key: str,
    module_label: str,
    task_key: str | None,
    checks: list[ModuleCheck],
) -> dict[str, Any]:
    failed = [check for check in checks if check.status == "fail"]
    first = failed[0] if failed else None
    code = first.code if first and first.code else "PREFLIGHT_FAILED"
    message = (
        first.message
        if first and first.message
        else f"{module_label} boshlanishidan oldingi tekshiruvdan o'tmadi."
    )
    actions = [
        check.action
        for check in failed
        if check.action
    ]
    # Preserve order while removing duplicates.
    actions = list(dict.fromkeys(actions))

    banner = build_module_status_banner(
        code=code,
        title="Run boshlanmadi",
        message=message,
        module_key=module_key,
        task_key=task_key,
        actions=actions,
        meta={
            "phase": "preflight",
            "failed_checks": len(failed),
            "total_checks": len(checks),
        },
    )
    return {
        "success": False,
        "module_key": module_key,
        "task_key": task_key,
        "run_state": "error",
        "active_phase": "preflight",
        "error": message,
        "error_message": message,
        "status_banner": banner,
        "preflight_checks": [check.to_dict() for check in checks],
    }
