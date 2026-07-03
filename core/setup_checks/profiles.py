from __future__ import annotations

from typing import Iterable

CHECK_PROFILES: dict[str, list[str]] = {
    # UI checker and webhook Service1 enter the same checker engine after their
    # source-specific gates. Keep this order here so changing check order is a
    # profile edit, not an orchestrator rewrite.
    "checker_engine": [
        "jira_fetch",
        "min_tz_check",
        "pr_check",
        "tz_build",
        "figma_check",
    ],
    "testcase_engine": [
        "jira_fetch",
        "min_tz_check",
        "figma_check",
        "tz_build",
    ],
    "webhook_service2_guard": [
        "service2_db_guard",
    ],
}


def profile_from_module_policy(policy: object) -> list[str]:
    profile: list[str] = []
    if bool(getattr(policy, "jira_fetch", False)):
        profile.append("jira_fetch")
    if bool(getattr(policy, "min_tz_check", False)):
        profile.append("min_tz_check")
    if bool(getattr(policy, "pr_check", False)):
        profile.append("pr_check")
    if bool(getattr(policy, "figma_check", False)):
        profile.append("figma_check")
    if bool(getattr(policy, "tz_build", False)):
        profile.append("tz_build")
    return profile


def resolve_profile(profile: str | Iterable[str]) -> list[str]:
    if isinstance(profile, str):
        return list(CHECK_PROFILES[profile])
    return list(profile)
