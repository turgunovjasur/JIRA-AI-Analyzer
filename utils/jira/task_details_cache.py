"""Short-lived in-memory cache for normalized Jira task details.

The cache is intentionally process-local. It exists to let webhook chains such
as TZPR checker -> testcase generator reuse the same Jira issue snapshot without
making another Jira request a few seconds later.
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from typing import Any

DEFAULT_TTL_SECONDS = 300


@dataclass
class _CacheEntry:
    task_details: dict[str, Any]
    include_pr_urls: bool
    include_figma_links: bool
    stored_at: float


_CACHE: dict[tuple[str, str, str], _CacheEntry] = {}


def make_task_details_cache_key(server: str, email: str, issue_key: str) -> tuple[str, str, str]:
    return ((server or "").strip().lower(), (email or "").strip().lower(), (issue_key or "").strip().upper())


def get_cached_task_details(
    key: tuple[str, str, str],
    *,
    need_pr_urls: bool,
    need_figma_links: bool,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> dict[str, Any] | None:
    entry = _CACHE.get(key)
    if not entry:
        return None

    if time.time() - entry.stored_at > ttl_seconds:
        _CACHE.pop(key, None)
        return None

    if need_pr_urls and not entry.include_pr_urls:
        return None
    if need_figma_links and not entry.include_figma_links:
        return None

    return copy.deepcopy(entry.task_details)


def get_cached_task_details_state(
    key: tuple[str, str, str],
    *,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> tuple[dict[str, Any], bool, bool] | None:
    entry = _CACHE.get(key)
    if not entry:
        return None

    if time.time() - entry.stored_at > ttl_seconds:
        _CACHE.pop(key, None)
        return None

    return copy.deepcopy(entry.task_details), entry.include_pr_urls, entry.include_figma_links


def set_cached_task_details(
    key: tuple[str, str, str],
    task_details: dict[str, Any],
    *,
    include_pr_urls: bool,
    include_figma_links: bool,
) -> None:
    _CACHE[key] = _CacheEntry(
        task_details=copy.deepcopy(task_details),
        include_pr_urls=bool(include_pr_urls),
        include_figma_links=bool(include_figma_links),
        stored_at=time.time(),
    )


def clear_task_details_cache() -> None:
    _CACHE.clear()
