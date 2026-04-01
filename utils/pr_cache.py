"""
Task uchun in-memory cache.

Uchta mustaqil cache:
  1. skip_cache     — AI_SKIP code natijasi (webhook handler saqlaydi)
  2. pr_exists_cache — PR bor/yo'qligi (Servis-1 saqlaydi)
  3. pr_merged_cache — PR merged/emas (Servis-1 saqlaydi)
  4. pr_info_cache   — To'liq PR ma'lumoti (Servis-1 saqlaydi, Servis-2 o'qiydi)

Oqim:
  Webhook handler → set_skip_cache(task_key, True/False)
  Servis-1        → set_pr_exists_cache / set_pr_merged_cache / set_pr_info_cache
  Servis-2        → get_skip_cache → get_pr_exists_cache → get_pr_merged_cache → get_pr_info_cache
  Tugaganda       → clear_task_cache(task_key)
"""
from typing import Optional, Dict

# ── Cache saqlash joylari ──────────────────────────────────────────────────────
_skip_cache: Dict[str, bool] = {}
_pr_exists_cache: Dict[str, bool] = {}
_pr_merged_cache: Dict[str, bool] = {}
_pr_info_cache: Dict[str, dict] = {}


# ── Skip cache ─────────────────────────────────────────────────────────────────

def set_skip_cache(task_key: str, detected: bool) -> None:
    """Webhook handler: AI_SKIP natijasini saqlash (True=topildi, False=topilmadi)"""
    _skip_cache[task_key] = detected


def get_skip_cache(task_key: str) -> Optional[bool]:
    """Servis-1/2: skip natijasini o'qish (None = hali tekshirilmagan)"""
    return _skip_cache.get(task_key)


# ── PR exists cache ────────────────────────────────────────────────────────────

def set_pr_exists_cache(task_key: str, exists: bool) -> None:
    """Servis-1: PR bor/yo'qligini saqlash"""
    _pr_exists_cache[task_key] = exists


def get_pr_exists_cache(task_key: str) -> Optional[bool]:
    """Servis-2: PR bor/yo'qligini o'qish (None = tekshirilmagan)"""
    return _pr_exists_cache.get(task_key)


# ── PR merged cache ────────────────────────────────────────────────────────────

def set_pr_merged_cache(task_key: str, merged: bool) -> None:
    """Servis-1: PR merged/emasligini saqlash"""
    _pr_merged_cache[task_key] = merged


def get_pr_merged_cache(task_key: str) -> Optional[bool]:
    """Servis-2: PR merged/emasligini o'qish (None = tekshirilmagan)"""
    return _pr_merged_cache.get(task_key)


# ── PR info cache (to'liq ma'lumot) ───────────────────────────────────────────

def set_pr_cache(task_key: str, pr_info: dict) -> None:
    """Servis-1: to'liq PR ma'lumotini saqlash"""
    _pr_info_cache[task_key] = pr_info


def get_pr_cache(task_key: str) -> Optional[dict]:
    """Servis-2: to'liq PR ma'lumotini o'qish (topilmasa None)"""
    return _pr_info_cache.get(task_key)


# ── Tozalash ───────────────────────────────────────────────────────────────────

def clear_task_cache(task_key: str) -> None:
    """Task tugaganda barcha cache yozuvlarini tozalash"""
    _skip_cache.pop(task_key, None)
    _pr_exists_cache.pop(task_key, None)
    _pr_merged_cache.pop(task_key, None)
    _pr_info_cache.pop(task_key, None)


# Orqaga moslik uchun (eski import ishlatayotgan joylar buzilmasin)
def clear_pr_cache(task_key: str) -> None:
    """Eski nom — clear_task_cache ga yo'naltiradi"""
    clear_task_cache(task_key)