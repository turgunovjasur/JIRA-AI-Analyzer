"""
Subscription and entitlement helper functions.

`auth_db.py` ichidagi billing access va module entitlement logikalarini
ajratish uchun yordamchi modul.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional

SUBSCRIPTION_SUPPORT_MESSAGE = "Super admin bilan bog'laning yoki +998936026869 raqamiga murojaat qiling."


def normalize_iso_date(value: Any) -> tuple[str, Optional[datetime.date], str]:
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            parsed = value if hasattr(value, "year") and not isinstance(value, datetime) else value.date()
            return parsed.isoformat(), parsed, ""
        except Exception:
            pass
    text = str(value or "").strip()
    if not text:
        return "", None, ""
    try:
        parsed = datetime.fromisoformat(text).date()
        return parsed.isoformat(), parsed, ""
    except ValueError:
        return text, None, f"Sana formati noto'g'ri: {text}. YYYY-MM-DD ishlating."


def validate_company_subscription_data(
    data: Dict,
    plan_name_re: re.Pattern,
    subscription_statuses: set[str],
    allowed_billing_modes: set[str],
    default_billing_mode: str,
) -> tuple[bool, str, Dict]:
    plan_name = str(data.get("plan_name") or "").strip().lower()
    if not plan_name:
        return False, "Plan nomi bo'sh bo'lishi mumkin emas.", {}
    if not plan_name_re.match(plan_name):
        return False, "Plan nomi faqat kichik harf, raqam, `_`, `-` bilan bo'lsin.", {}

    status = str(data.get("subscription_status") or "").strip().lower()
    if status not in subscription_statuses:
        return False, "Subscription status noto'g'ri.", {}

    billing_mode = str(data.get("billing_mode") or default_billing_mode).strip().lower()
    if billing_mode not in allowed_billing_modes:
        return False, "Billing mode noto'g'ri.", {}

    normalized: Dict[str, Any] = {
        "plan_name": plan_name,
        "subscription_status": status,
        "billing_mode": billing_mode,
        "last_payment_note": str(data.get("last_payment_note") or "").strip(),
    }

    parsed_dates: Dict[str, Optional[datetime.date]] = {}
    for field in ("billing_start_date", "billing_end_date", "next_payment_date", "last_payment_date"):
        normalized_value, parsed_value, error = normalize_iso_date(data.get(field))
        if error:
            return False, error, {}
        normalized[field] = normalized_value
        parsed_dates[field] = parsed_value

    start_date = parsed_dates["billing_start_date"]
    end_date = parsed_dates["billing_end_date"]
    next_date = parsed_dates["next_payment_date"]
    last_date = parsed_dates["last_payment_date"]

    if status in {"trial", "active", "past_due"} and not end_date:
        return False, "Trial, active va past_due holatlari uchun billing end date kiritilishi shart.", {}
    if status in {"trial", "active"} and end_date and end_date < datetime.now().date():
        return False, "Trial va active holatlari uchun billing end date bugungi sanadan oldin bo'lishi mumkin emas.", {}
    if start_date and end_date and start_date > end_date:
        return False, "Billing start date billing end datedan keyin bo'lishi mumkin emas.", {}
    if last_date and next_date and last_date > next_date:
        return False, "Last payment date next payment datedan keyin bo'lishi mumkin emas.", {}

    return True, "", normalized


def is_company_subscription_active(subscription: Dict) -> tuple[bool, str]:
    if not subscription:
        return True, ""

    status = (subscription.get("subscription_status") or "active").strip().lower()
    if status in {"suspended", "cancelled"}:
        return False, f"Obuna holati: {status}. {SUBSCRIPTION_SUPPORT_MESSAGE}"

    raw_end_date = subscription.get("billing_end_date")
    end_date = raw_end_date.isoformat() if hasattr(raw_end_date, "isoformat") and not isinstance(raw_end_date, str) else str(raw_end_date or "").strip()
    if status in {"trial", "active", "past_due"} and not end_date:
        return False, f"Obuna sanalari sozlanmagan. {SUBSCRIPTION_SUPPORT_MESSAGE}"
    if end_date and status in {"trial", "active"}:
        try:
            if datetime.now().date() > datetime.fromisoformat(end_date).date():
                return False, f"Obuna muddati tugagan. {SUBSCRIPTION_SUPPORT_MESSAGE}"
        except ValueError:
            return False, f"Obuna sanasi noto'g'ri sozlangan. {SUBSCRIPTION_SUPPORT_MESSAGE}"

    return True, ""


def get_effective_company_modules(
    base_modules: Dict[str, bool],
    subscription: Dict,
    access_statuses: set[str],
    default_plan_name: str,
    plan_included_modules: Dict[str, set[str]],
) -> Dict[str, bool]:
    """Kompaniyaning amaldagi modul ruxsatlari.

    Manba — `enabled_modules` (super-admin saqlagan). Plan endi modullarni
    MAJBURAN yoqmaydi: asosiy modullar `DEFAULT_MODULES` orqali default yoqiq,
    super-admin esa ularni alohida o'chira oladi.

    Qoidalar:
    - Obuna faol bo'lmasa — hech qanday modul ruxsati yo'q.
    - Webhook sub-servislari (service1/service2) faqat `webhook` addon
      yoqilganda amal qiladi.
    - `webhook` faqat kamida bitta servis yoqilgan bo'lsagina amalda ishlaydi.
    - `monitoring` har doim webhook holatidan kelib chiqadi.

    `default_plan_name` / `plan_included_modules` parametrlari signatura
    barqarorligi uchun saqlangan (endi force-yoqish uchun ishlatilmaydi).
    """
    result = dict(base_modules)

    # Obuna gate: faol bo'lmasa hech narsa ko'rinmaydi.
    if subscription:
        status = (subscription.get("subscription_status") or "").strip().lower()
        if status not in access_statuses:
            return {key: False for key in result}

    webhook_enabled = bool(result.get("webhook", False))
    service1 = webhook_enabled and bool(result.get("webhook_service1", False))
    service2 = webhook_enabled and bool(result.get("webhook_service2", False))
    # Webhook faqat kamida bitta servis yoqiq bo'lsagina amalda ishlaydi.
    webhook_effective = webhook_enabled and (service1 or service2)

    result["webhook"] = webhook_effective
    result["webhook_service1"] = service1
    result["webhook_service2"] = service2
    result["monitoring"] = webhook_effective
    return result
