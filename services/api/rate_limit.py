"""
Oddiy in-memory IP-based rate limiter.
Auth endpointlar (login, password-reset) uchun brute-force himoya.
"""
from __future__ import annotations

import asyncio
import os
import time
from collections import defaultdict

from fastapi import HTTPException, Request

_WINDOW_SECONDS = 60
_MAX_REQUESTS = 10

_counters: dict[str, list[float]] = defaultdict(list)
_lock = asyncio.Lock()


def _client_ip(request: Request) -> str:
    # X-Forwarded-For faqat APP_TRUSTED_PROXY=1 bo'lganda hisobga olinadi —
    # aks holda mijoz headerni spoof qilib limitni aylanib o'tishi mumkin.
    # Taxmin: bitta ishonchli reverse-proxy bor; u haqiqiy client IP ni
    # ro'yxat OXIRIGA qo'shadi (chapdagi qiymatlar mijoz nazoratida),
    # shuning uchun eng o'ngdagi entry olinadi.
    if os.getenv("APP_TRUSTED_PROXY", "0").strip() == "1":
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        hops = [part.strip() for part in forwarded_for.split(",") if part.strip()]
        if hops:
            return hops[-1]
    return request.client.host if request.client else "unknown"


async def check_rate_limit(request: Request) -> None:
    """429 tashlaydi agar IP so'nggi 60s da 10+ so'rov yuborgan bo'lsa."""
    ip = _client_ip(request)
    now = time.monotonic()
    async with _lock:
        timestamps = _counters[ip]
        cutoff = now - _WINDOW_SECONDS
        _counters[ip] = [t for t in timestamps if t > cutoff]
        _counters[ip].append(now)
        count = len(_counters[ip])

    if count > _MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Juda ko'p urinish. {_WINDOW_SECONDS} soniyadan so'ng qayta urinib ko'ring.",
            headers={"Retry-After": str(_WINDOW_SECONDS)},
        )
