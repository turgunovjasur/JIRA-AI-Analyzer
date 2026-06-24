"""Manual UI task key normalization helpers."""
from __future__ import annotations


class MissingProjectKeySetting(ValueError):
    """Raised when numeric manual task input needs company jira_project_keys."""


def _first_project_key(raw_value: object) -> str:
    if not isinstance(raw_value, str):
        return ""
    for item in raw_value.split(","):
        project_key = item.strip().upper()
        if project_key:
            return project_key
    return ""


def normalize_manual_task_key(task_key: str, company_id: int | None) -> str:
    """Allow users to enter only the issue number when company project key is configured."""
    normalized = (task_key or "").strip().upper()
    if not normalized or "-" in normalized or not normalized.isdigit() or not company_id:
        return normalized

    try:
        from utils.auth.auth_db import get_company_settings

        settings = get_company_settings(int(company_id))
    except Exception as exc:
        raise RuntimeError("JIRA Project Key(lar) settingini o'qib bo'lmadi.") from exc

    project_key = _first_project_key(settings.get("jira_project_keys"))
    if not project_key:
        raise MissingProjectKeySetting(
            "JIRA Project Key(lar) settingi kiritilmagan. "
            "Sozlamalar -> API Kalitlar bo'limida JIRA Project Key(lar) ni kiriting."
        )
    return f"{project_key}-{normalized}"
