"""
Task PR ma'lumotlari uchun in-memory cache.

Service1 (TZ-PR Checker) topgan PR ni Service2 (Testcase Generator)
qayta GitHub'dan qidirmasdan ishlatishi uchun.

Logika:
  - Service1 PR topsa → cache ga saqlaydi
  - Service2 ishga tushganda → avval cache tekshiradi
  - Cache da bo'lsa → qayta qidirmaydi
  - Cache da bo'lmasa (service1 skip yoki PR topa olmagan) → o'zi qidiradi
"""
from typing import Optional, Dict

_cache: Dict[str, dict] = {}


def set_pr_cache(task_key: str, pr_info: dict) -> None:
    """Service1 topgan PR ma'lumotini cache ga saqlash"""
    _cache[task_key] = pr_info


def get_pr_cache(task_key: str) -> Optional[dict]:
    """Cache dan PR ma'lumotini olish (topilmasa None)"""
    return _cache.get(task_key)


def clear_pr_cache(task_key: str) -> None:
    """Task tugagandan keyin cache ni tozalash (ixtiyoriy)"""
    _cache.pop(task_key, None)
