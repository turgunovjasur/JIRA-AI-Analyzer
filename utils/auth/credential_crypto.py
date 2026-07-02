"""
Credential encryption helpers.

Sensitive credential maydonlarini DB'da plain text emas, shifrlangan holda
saqlash uchun transparent helperlar.
"""
from __future__ import annotations

import base64
import hashlib
import os
from functools import lru_cache
from typing import Any, Iterable

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()

_ENCRYPTED_PREFIX = "enc::"

# KDF: yangi ma'lumot PBKDF2-HMAC-SHA256 (stretching) bilan shifrlanadi. Salt
# qat'iy (deterministik) — schema o'zgarmasdan migratsiya-xavfsiz bo'lishi uchun.
# Eski ma'lumot bare sha256 KDF bilan shifrlangan — deshifrlashda ikkalasi ham
# sinaladi, keyingi saqlashda avtomatik PBKDF2'ga ko'chiriladi (needs_reencryption).
_PBKDF2_SALT = b"qa-assistant.credential-crypto.v1"
_PBKDF2_ITERATIONS = 200_000

_SENSITIVE_FIELDS = {
    "jira_token",
    "github_token",
    "figma_token",
    "figma_tokens",
    "gemini_api_key_1",
    "gemini_api_key_2",
    "webhook_jira_token",
    "webhook_github_token",
    "webhook_figma_token",
    "webhook_figma_tokens",
    "webhook_gemini_api_key_1",
    "webhook_gemini_api_key_2",
    "webhook_secret",
    "gemini_default_api_key_1",
    "gemini_default_api_key_2",
}


def get_sensitive_credential_fields() -> set[str]:
    return set(_SENSITIVE_FIELDS)


def is_sensitive_credential_field(field_name: str) -> bool:
    return str(field_name or "").strip() in _SENSITIVE_FIELDS


def assert_master_key_configured() -> None:
    """APP_STRICT_MODE=true bo'lsa, master key yo'qligida startup xato beradi."""
    strict = os.getenv("APP_STRICT_MODE", "").strip().lower() in ("1", "true", "yes")
    production = (
        os.getenv("APP_ENV", "").strip().lower() == "production"
        or os.getenv("ENVIRONMENT", "").strip().lower() == "production"
        or os.getenv("NODE_ENV", "").strip().lower() == "production"
    )
    if not strict and not production:
        return
    if not has_configured_master_key():
        raise RuntimeError(
            "APP_STRICT_MODE=true lekin APP_CREDENTIALS_MASTER_KEY o'rnatilmagan. "
            "Tokenlar plain text saqlanadi — xavfli. "
            "APP_CREDENTIALS_MASTER_KEY ni .env ga qo'shing yoki APP_STRICT_MODE ni o'chiring."
        )


def _get_master_secret() -> str:
    """Shifrlash (ENCRYPTION) uchun master secret — FAQAT APP_CREDENTIALS_MASTER_KEY.

    SUPER_ADMIN_PASSWORD fallback shifrlashdan olib tashlandi (zaif kalit — audit F6).
    Eski ma'lumotni o'qish uchun u faqat DESHIFRLASHda ishlatiladi
    (_get_legacy_decryption_secrets).
    """
    return (os.getenv("APP_CREDENTIALS_MASTER_KEY") or "").strip()


def _get_legacy_decryption_secrets() -> list[str]:
    """Faqat DESHIFRLASH uchun eski secretlar.

    SUPER_ADMIN_PASSWORD fallback bilan (master key o'rnatilmagan paytda)
    shifrlangan eski credential'lar hali ham o'qilishi uchun. Yangi shifrlash
    hech qachon bularni ishlatmaydi.
    """
    legacy = (os.getenv("SUPER_ADMIN_PASSWORD") or "").strip()
    return [legacy] if legacy else []


def _get_old_master_secrets() -> list[str]:
    raw = (os.getenv("APP_CREDENTIALS_OLD_MASTER_KEYS") or "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def can_encrypt_credentials() -> bool:
    return bool(_get_master_secret())


def has_configured_master_key() -> bool:
    return bool((os.getenv("APP_CREDENTIALS_MASTER_KEY") or "").strip())


def has_configured_old_master_keys() -> bool:
    return bool(_get_old_master_secrets())


def is_using_super_admin_password_fallback() -> bool:
    return not has_configured_master_key() and bool((os.getenv("SUPER_ADMIN_PASSWORD") or "").strip())


def get_credential_security_status() -> dict[str, Any]:
    if has_configured_master_key():
        return {
            "status": "ok",
            "message": (
                "Credential encryption alohida APP_CREDENTIALS_MASTER_KEY bilan himoyalangan."
                + (" Old master keylar rotation uchun saqlangan." if has_configured_old_master_keys() else "")
            ),
            "rotation_ready": has_configured_old_master_keys(),
        }
    if is_using_super_admin_password_fallback():
        return {
            "status": "warning",
            "message": (
                "APP_CREDENTIALS_MASTER_KEY yo'q. SUPER_ADMIN_PASSWORD endi faqat ESKI "
                "ma'lumotni deshifrlash uchun ishlatiladi — yangi credential saqlab "
                "bo'lmaydi (fail-closed). APP_CREDENTIALS_MASTER_KEY ni o'rnating."
            ),
            "rotation_ready": False,
        }
    return {
        "status": "danger",
        "message": "APP_CREDENTIALS_MASTER_KEY yo'q. Yangi credential saqlab bo'lmaydi (fail-closed).",
        "rotation_ready": False,
    }


@lru_cache(maxsize=64)
def _fernet_from_secret(secret: str, legacy: bool) -> Fernet | None:
    """secret'dan Fernet kalit hosil qilish (cached — PBKDF2 qimmat).

    legacy=False → PBKDF2-HMAC-SHA256 (yangi, stretching bilan).
    legacy=True  → bare sha256 (eski ma'lumotni deshifrlash uchun).
    """
    if not secret:
        return None
    if legacy:
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
    else:
        digest = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), _PBKDF2_SALT, _PBKDF2_ITERATIONS)
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def _build_fernet(secret: str) -> Fernet | None:
    """Yangi shifrlash uchun Fernet (PBKDF2)."""
    return _fernet_from_secret(secret, False)


def _get_fernet() -> Fernet | None:
    return _fernet_from_secret(_get_master_secret(), False)


def _get_decryption_fernets() -> list[Fernet]:
    """Deshifrlash uchun barcha nomzod fernet'lar (tartib bo'yicha sinaladi).

    Yangi KDF (master + rotation) → eski sha256 KDF (master + rotation + super_admin
    legacy). Shu tariqa eski har qanday formatdagi ma'lumot ham o'qiladi.
    """
    fernets: list[Fernet] = []
    seen: set[tuple[str, bool]] = set()

    def _add(secret: str, legacy: bool) -> None:
        if not secret or (secret, legacy) in seen:
            return
        fernet = _fernet_from_secret(secret, legacy)
        if fernet is not None:
            fernets.append(fernet)
            seen.add((secret, legacy))

    # 1) Yangi KDF: master + rotation kalitlar
    for secret in (_get_master_secret(), *_get_old_master_secrets()):
        _add(secret, False)
    # 2) Eski sha256 KDF: master + rotation + super_admin legacy
    for secret in (_get_master_secret(), *_get_old_master_secrets(), *_get_legacy_decryption_secrets()):
        _add(secret, True)
    return fernets


def is_encrypted_value(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(_ENCRYPTED_PREFIX)


def encrypt_value(value: Any) -> Any:
    if value in (None, ""):
        return value
    if not isinstance(value, str):
        return value
    if is_encrypted_value(value):
        return value
    fernet = _get_fernet()
    if fernet is None:
        # FAIL-CLOSED: master key yo'q bo'lsa plain text QAYTARMAYMIZ. Chaqiruvchilar
        # avval can_encrypt_credentials() bilan tekshiradi; bu — mudofaa qatlami
        # (audit F6: fail-open plaintext teshigini yopadi).
        raise RuntimeError(
            "Credential shifrlash uchun APP_CREDENTIALS_MASTER_KEY o'rnatilmagan — "
            "plain text saqlash rad etildi."
        )
    token = fernet.encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{_ENCRYPTED_PREFIX}{token}"


def decrypt_value(value: Any) -> Any:
    if value in (None, ""):
        return value
    if not is_encrypted_value(value):
        return value
    fernets = _get_decryption_fernets()
    if not fernets:
        return value[len(_ENCRYPTED_PREFIX):]
    token = value[len(_ENCRYPTED_PREFIX):]
    for fernet in fernets:
        try:
            return fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError):
            continue
    return value


def can_decrypt_value(value: Any) -> bool:
    if value in (None, ""):
        return True
    if not is_encrypted_value(value):
        return True
    token = value[len(_ENCRYPTED_PREFIX):]
    for fernet in _get_decryption_fernets():
        try:
            fernet.decrypt(token.encode("utf-8"))
            return True
        except (InvalidToken, ValueError):
            continue
    return False


def encrypt_sensitive_fields(payload: dict[str, Any], fields: Iterable[str] | None = None) -> dict[str, Any]:
    target_fields = set(fields or _SENSITIVE_FIELDS)
    result = dict(payload)
    for field in target_fields:
        if field in result:
            result[field] = encrypt_value(result[field])
    return result


def decrypt_sensitive_fields(payload: dict[str, Any], fields: Iterable[str] | None = None) -> dict[str, Any]:
    target_fields = set(fields or _SENSITIVE_FIELDS)
    result = dict(payload)
    for field in target_fields:
        if field in result:
            result[field] = decrypt_value(result[field])
    return result


def reencrypt_sensitive_fields(payload: dict[str, Any], fields: Iterable[str] | None = None) -> dict[str, Any]:
    target_fields = set(fields or _SENSITIVE_FIELDS)
    result = dict(payload)
    for field in target_fields:
        if field not in result:
            continue
        decrypted = decrypt_value(result[field])
        result[field] = encrypt_value(decrypted)
    return result


def payload_requires_encryption(payload: dict[str, Any], fields: Iterable[str] | None = None) -> bool:
    target_fields = set(fields or _SENSITIVE_FIELDS)
    for field in target_fields:
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            return True
    return False


def mask_secret_value(value: Any, *, keep_last: int = 4, mask_char: str = "*") -> str:
    if not isinstance(value, str):
        return ""
    clean = value.strip()
    if not clean:
        return ""
    suffix = clean[-keep_last:] if len(clean) > keep_last else clean
    masked_prefix_len = max(8, len(clean) - len(suffix))
    return f"{mask_char * masked_prefix_len}{suffix}"


def resolve_secret_input(input_value: Any, existing_value: Any) -> str:
    candidate = (input_value or "").strip() if isinstance(input_value, str) else ""
    if candidate:
        return candidate
    return (existing_value or "").strip() if isinstance(existing_value, str) else ""


def merge_masked_token_rows(input_rows: list[dict[str, Any]], existing_rows: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    existing_rows = existing_rows or []
    for index, row in enumerate(input_rows):
        name = str((row or {}).get("name") or "").strip()
        token = str((row or {}).get("token") or "").strip()
        if not token and index < len(existing_rows):
            token = str((existing_rows[index] or {}).get("token") or "").strip()
        if not token:
            continue
        merged.append({
            "name": name,
            "token": token,
        })
    return merged


def needs_reencryption(value: Any) -> bool:
    if not is_encrypted_value(value):
        return False
    current_fernet = _get_fernet()
    if current_fernet is None:
        return False
    token = value[len(_ENCRYPTED_PREFIX):]
    try:
        current_fernet.decrypt(token.encode("utf-8"))
        return False
    except (InvalidToken, ValueError):
        return True


def payload_needs_reencryption(payload: dict[str, Any], fields: Iterable[str] | None = None) -> bool:
    target_fields = set(fields or _SENSITIVE_FIELDS)
    for field in target_fields:
        if field in payload and needs_reencryption(payload[field]):
            return True
    return False
