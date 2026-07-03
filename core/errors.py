# core/errors.py
"""
Tizim uchun typed exception taksonomiyasi.

Xato klassifikatsiyasi ilgari faqat matn qidiruv (substring) bilan ishlardi —
endi xato kelib chiqqan joyda typed exception yaratiladi va webhook oqimidagi
`_classify_error` avval turini tekshiradi (matn qidiruv legacy fallback).

Xabar matni (Uzbek) saqlanadi — JIRA commentlar o'sha matnni ko'rsatadi.

error_type  — webhook oqimidagi klassifikatsiya kaliti ('pr_not_found', ...)
reason_code — DB return_reason / JIRA comment kodi (core/constants.py)
"""
from __future__ import annotations

from core.constants import (
    ERR_UNKNOWN,
    WARN_AI_TIMEOUT,
    WARN_MIN_TZ,
    WARN_NO_PR,
    WARN_PR_NOT_MERGED,
)


class QAServiceError(Exception):
    """Bazaviy xato — barcha typed servis xatolari shundan meros oladi."""

    error_type: str = "unknown"
    reason_code: str = ERR_UNKNOWN


class PRNotFoundError(QAServiceError):
    """Task uchun GitHub/JIRA da PR topilmadi (Servis-2 TZ-only rejimda ishlashi mumkin)."""

    error_type = "pr_not_found"
    reason_code = WARN_NO_PR


class PRNotMergedError(QAServiceError):
    """
    PR topildi, lekin hech biri merged emas (open yoki closed/cancelled).
    Faqat merged statusdagi PR'lar qabul qilinadi.
    """

    error_type = "pr_not_merged"
    reason_code = WARN_PR_NOT_MERGED


class MinTZError(QAServiceError):
    """TZ (description) belgilangan minimal chegaradan qisqa."""

    error_type = "tz_too_short"
    reason_code = WARN_MIN_TZ


class AITimeoutError(QAServiceError, RuntimeError):
    """
    Gemini AI ishlamadi: rate limit / quota / barcha kalitlar freeze.
    RuntimeError'dan ham meros oladi — mavjud `except RuntimeError` yo'llari buzilmaydi.
    Task 'blocked' holatga tushadi va retry scheduler keyinroq qayta urinadi.
    """

    error_type = "ai_timeout"
    reason_code = WARN_AI_TIMEOUT
