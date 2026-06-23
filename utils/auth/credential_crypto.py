"""
Credential encryption helpers.

Sensitive credential maydonlarini DB'da plain text emas, shifrlangan holda
saqlash uchun transparent helperlar.
"""
from __future__ import annotations

import base64
import hashlib
import os
from typing import Any, Iterable

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()

_ENCRYPTED_PREFIX = "enc::"

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
    return (
        os.getenv("APP_CREDENTIALS_MASTER_KEY")
        or os.getenv("SUPER_ADMIN_PASSWORD")
        or ""
    ).strip()


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
            "message": "Credential encryption hozir SUPER_ADMIN_PASSWORD fallback bilan ishlayapti. Production uchun alohida APP_CREDENTIALS_MASTER_KEY kiriting.",
            "rotation_ready": False,
        }
    return {
        "status": "danger",
        "message": "APP_CREDENTIALS_MASTER_KEY yo'q va fallback ham topilmadi. Yangi credentiallar plain text holatda saqlanishi mumkin.",
        "rotation_ready": False,
    }


def _build_fernet(secret: str) -> Fernet | None:
    if not secret:
        return None
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def _get_fernet() -> Fernet | None:
    return _build_fernet(_get_master_secret())


def _get_decryption_fernets() -> list[Fernet]:
    secrets_in_order = [_get_master_secret(), *_get_old_master_secrets()]
    fernets: list[Fernet] = []
    seen: set[str] = set()
    for secret in secrets_in_order:
        if not secret or secret in seen:
            continue
        fernet = _build_fernet(secret)
        if fernet is not None:
            fernets.append(fernet)
            seen.add(secret)
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
        return value
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
