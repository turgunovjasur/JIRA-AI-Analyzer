"""Telegram bot orqali oddiy matnli bildirishnoma (lidlar uchun).

Konfiguratsiya env orqali:
  TELEGRAM_BOT_TOKEN — @BotFather bergan token
  TELEGRAM_CHAT_ID   — xabar boradigan chat/user id (bot bilan avval /start qilinishi shart)

Token yoki chat id sozlanmagan bo'lsa — jimgina o'tkazib yuboriladi
(lid baribir DB'ga yozilaveradi, faqat bildirishnoma bo'lmaydi).
"""
from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

from core.logger import get_logger

load_dotenv()

log = get_logger("notify.telegram")


def is_configured() -> bool:
    return bool((os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()) and bool(
        (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    )


def send_telegram_message(text: str) -> bool:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if not token or not chat_id:
        log.info("Telegram sozlanmagan (TELEGRAM_BOT_TOKEN/CHAT_ID yo'q) — xabar yuborilmadi")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            log.warning(f"Telegram sendMessage {resp.status_code}: {resp.text[:200]}")
            return False
        return True
    except Exception:
        log.warning("Telegram sendMessage xato", exc_info=True)
        return False
