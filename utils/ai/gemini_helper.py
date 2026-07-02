from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import time
from threading import Lock
from core.logger import get_logger
from config.token_limits import GEMINI_HELPER_DEFAULT_MAX_OUTPUT_TOKENS
from utils.ai.usage_cost import estimate_gemini_usage_cost

load_dotenv()

log = get_logger("ai.gemini")

# Settings cache (lazy loading)
_settings_cache = None

def _get_gemini_settings():
    """Get Gemini settings from app_settings (cached)"""
    global _settings_cache
    if _settings_cache is None:
        try:
            from config.app_settings import get_app_settings
            _settings_cache = get_app_settings(force_reload=False).queue
        except Exception as e:
            log.warning(f"Settings load failed, using defaults: {e}")
            class DefaultSettings:
                gemini_min_interval = 6
                key_freeze_duration = 600
                gemini_max_retries = 3
            _settings_cache = DefaultSettings()
    return _settings_cache


class GeminiHelper:
    """
    Gemini AI Helper - N ta API Key Fallback + Freeze bilan

    Logika:
    - Transient xato (503, overloaded): retry-with-backoff (5s→10s→20s) — key o'zgarmaydi
    - Permanent xato (quota, billing, 403): key freeze → keyingi keyga o'tish
    - Barcha keylar freeze bo'lsa → RuntimeError raise
    """

    # Kalit muammosi — keyingi kalitga o'tish kerak
    FALLBACK_ERROR_KEYWORDS = [
        'resource_exhausted', '429', 'quota', 'rate limit',
        'api key', 'invalid', 'permission', 'forbidden', '403',
        'billing', 'exceeded',
    ]

    # Vaqtinchalik server xatoliklari — xuddi shu kalit bilan qayta urinish
    # (kalit muammosi EMAS — freeze qilish noto'g'ri)
    TRANSIENT_ERROR_KEYWORDS = [
        '503', 'unavailable', 'overloaded', 'high demand',
        'temporarily', 'server error', '500', '502', '504',
        'timeout', 'timed out', 'deadline',
    ]

    # Transient xatolik uchun kutish vaqtlari (soniya)
    TRANSIENT_RETRY_DELAYS = [5, 10, 20]

    def __init__(
        self,
        api_keys: list = None,
        model_name: str = None,
        fallback_model_name: str = None,
        shared_state: dict | None = None,
        usage_context: dict | None = None,
    ):
        if api_keys is not None:
            if not api_keys:
                raise RuntimeError("Kompaniya Gemini API kalitlari kiritilmagan. Sozlamalar sahifasida kalit kiriting.")
            self.api_keys = [k for k in api_keys if k and k.strip()]
            if not self.api_keys:
                raise RuntimeError("Kompaniya Gemini API kalitlari bo'sh. Sozlamalar sahifasida kalit kiriting.")
            log.info(f"GeminiHelper: {len(self.api_keys)} ta kalit yuklandi")
        else:
            self.api_keys = self._load_keys()

        self._shared_state = shared_state
        if self._shared_state is not None:
            self._shared_state.setdefault("lock", Lock())
            self._shared_state.setdefault("frozen_until", {})
            self._shared_state.setdefault("last_request_time", 0.0)
            self._shared_state.setdefault("request_count", 0)
            self._frozen_until = self._shared_state["frozen_until"]
        else:
            self._frozen_until = {}
        self._current_idx = 0
        self.model_name = (model_name or os.getenv('GEMINI_MODEL', '')).strip()
        if not self.model_name:
            raise RuntimeError(
                "Gemini modeli sozlanmagan. Modul agent modelini yoki Super Admin global AI defaultini tanlang."
            )
        self._fallback_model_explicit = fallback_model_name is not None
        self.fallback_model_name = (fallback_model_name or "").strip()
        self.last_request_time = 0
        self.request_count = 0
        self.last_model_used = self.model_name
        self.last_primary_model_name = self.model_name
        self.last_fallback_model_name = self._get_fallback_model() or ""
        self.last_used_fallback = False
        self.last_cached_content_token_count = 0
        self.last_prompt_token_count = 0
        self.last_candidates_token_count = 0
        self.last_thoughts_token_count = 0
        self.last_total_token_count = 0
        self.last_usage_metadata: dict[str, int] = {}
        self.usage_context: dict = dict(usage_context or {})
        self._client = self._make_client(self._current_idx)

    def _request_timeout_ms(self) -> int:
        """Bitta Gemini so'rovi uchun timeout (millisekund). Sozlamadan, default 120s.

        Timeout bo'lmasa, javob bermagan ulanish butun run'ni cheksiz osib qo'yadi
        (generate_content ichida bloklanadi, retry sikli ham ishlamaydi).
        """
        try:
            seconds = int(getattr(_get_gemini_settings(), "gemini_request_timeout", 120) or 120)
        except Exception:
            seconds = 120
        return max(1, seconds) * 1000

    def _make_client(self, idx: int):
        return genai.Client(
            api_key=self.api_keys[idx],
            http_options=types.HttpOptions(timeout=self._request_timeout_ms()),
        )

    def _load_keys(self) -> list[str]:
        raise RuntimeError(
            "GeminiHelper: api_keys ko'rsatilmagan. "
            "Kompaniya Gemini API kalitlarini DB ga kiriting (Sozlamalar → API Kalitlar)."
        )

    def _key_name(self, idx: int) -> str:
        return f"KEY_{idx + 1}"

    def _configure_model(self, idx: int):
        self._client = self._make_client(idx)
        self._current_idx = idx

    def _is_frozen(self, idx: int) -> bool:
        until = self._frozen_until.get(idx)
        if until is None:
            return False
        if time.time() >= until:
            del self._frozen_until[idx]
            log.info(f"AI-KEY -> {self._key_name(idx)} unfrozen, available again")
            return False
        return True

    def _freeze(self, idx: int):
        settings = _get_gemini_settings()
        duration = settings.key_freeze_duration
        self._frozen_until[idx] = time.time() + duration
        log.warning(f"AI-KEY -> {self._key_name(idx)} frozen for {int(duration / 60)} min")

    def _get_best_available_idx(self) -> int | None:
        for idx in range(len(self.api_keys)):
            if not self._is_frozen(idx):
                return idx
        return None

    def _rate_limit(self):
        settings = _get_gemini_settings()
        min_interval = settings.gemini_min_interval

        if self._shared_state is not None:
            lock = self._shared_state["lock"]
            with lock:
                last_request_time = float(self._shared_state.get("last_request_time") or 0.0)
                elapsed = time.time() - last_request_time
                if elapsed < min_interval:
                    wait_time = min_interval - elapsed
                    log.ai_rate_limit(self._key_name(self._current_idx), int(wait_time))
                    time.sleep(wait_time)
                self._shared_state["last_request_time"] = time.time()
                self._shared_state["request_count"] = int(self._shared_state.get("request_count") or 0) + 1
                self.last_request_time = float(self._shared_state["last_request_time"])
                self.request_count = int(self._shared_state["request_count"])
            return

        elapsed = time.time() - self.last_request_time
        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            log.ai_rate_limit(self._key_name(self._current_idx), int(wait_time))
            time.sleep(wait_time)

        self.last_request_time = time.time()
        self.request_count += 1

    def _is_fallback_error(self, error: Exception) -> bool:
        error_msg = str(error).lower()
        return any(kw in error_msg for kw in self.FALLBACK_ERROR_KEYWORDS)

    def _is_transient_error(self, error: Exception) -> bool:
        """Vaqtinchalik server xatosi (503, overloaded, timeout) — bir oz kutib qayta urinish kerak."""
        # httpx timeout xatolari (ReadTimeout/ConnectTimeout/...) ko'pincha bo'sh xabar beradi —
        # shuning uchun tur nomini ham tekshiramiz.
        if 'timeout' in type(error).__name__.lower():
            return True
        error_msg = str(error).lower()
        return any(kw in error_msg for kw in self.TRANSIENT_ERROR_KEYWORDS)

    def _build_generation_config(
        self,
        model_name: str,
        max_output_tokens: int,
        generation_config_overrides: dict | None = None,
        system_instruction: str | None = None,
    ):
        """Model nomiga qarab to'g'ri GenerateContentConfig yaratish."""
        requires_thinking = 'flash' not in model_name.lower()
        config_kwargs = {"max_output_tokens": max_output_tokens}
        if not requires_thinking:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if generation_config_overrides:
            config_kwargs.update(dict(generation_config_overrides))
        return types.GenerateContentConfig(**config_kwargs)

    def _get_fallback_model(self) -> str | None:
        """Per-helper fallback yoki GEMINI_FALLBACK_MODEL olinadi. Asosiy model bilan bir xil bo'lsa None."""
        fallback = self.fallback_model_name
        if not self._fallback_model_explicit:
            fallback = os.getenv('GEMINI_FALLBACK_MODEL', '').strip()
        if fallback and fallback != self.model_name:
            return fallback
        return None

    def set_usage_context(self, **context) -> None:
        """Keyingi AI chaqiruv uchun usage ledger contextini yangilash."""
        self.usage_context = {
            key: value
            for key, value in dict(context or {}).items()
            if value is not None
        }

    def count_tokens(self, prompt, model_name: str | None = None) -> int:
        """Gemini API orqali real prompt token count olish."""
        self._rate_limit()
        response = self._client.models.count_tokens(
            model=model_name or self.model_name,
            contents=prompt,
        )
        return int(getattr(response, "total_tokens", 0) or 0)

    def _default_retry_delays(self) -> list[int]:
        """Transient (503/overload) retry backoff ro'yxati — `gemini_max_retries` sozlamasidan.

        N marta retry → backoff 5s, 10s, 20s, ... (har safar 2x, eng ko'pi 60s).
        Default 3 → [5, 10, 20] (eski xulq saqlanadi).
        """
        settings = _get_gemini_settings()
        n = max(1, int(getattr(settings, "gemini_max_retries", 3) or 3))
        return [min(5 * (2 ** i), 60) for i in range(n)]

    def _request(self, prompt, generation_config, model_name: str = None, retry_delays: list[int] | None = None):
        """Bitta Gemini so'rov — transient xato bo'lsa backoff bilan N marta qayta urinish.

        retry_delays=None → default (5s, 10s, 20s)
        retry_delays=[]   → retry yo'q (bitta urinish), pro modeli 503 da tezroq fallback uchun
        """
        target_model = model_name or self.model_name
        effective_delays = self._default_retry_delays() if retry_delays is None else list(retry_delays)
        last_error = None
        for attempt, delay in enumerate([0] + effective_delays):
            if delay > 0:
                log.warning(
                    f"AI -> transient xato, retry {attempt}/{len(effective_delays)} "
                    f"| {delay}s kutilmoqda | model={target_model} | key={self._key_name(self._current_idx)}"
                )
                time.sleep(delay)

            try:
                response = self._client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=generation_config,
                )
                usage = getattr(response, "usage_metadata", None)
                self._set_last_usage_metadata(usage)
                self._record_usage_event(target_model)
                return response.text
            except Exception as e:
                last_error = e
                if not self._is_transient_error(e):
                    raise  # Permanent xato — darhol yuqoriga uzatish

        # Barcha transient retry tugadi — oxirgi xatoni yuqoriga uzatish
        raise last_error

    def _requires_thinking(self) -> bool:
        """Pro modellar thinking_budget=0 qabul qilmaydi — faqat flash modellarda o'chirsa bo'ladi."""
        return 'flash' not in self.model_name.lower()

    def _reset_last_run_state(self):
        self.last_primary_model_name = self.model_name
        self.last_fallback_model_name = self._get_fallback_model() or ""
        self.last_model_used = self.model_name
        self.last_used_fallback = False
        self.last_cached_content_token_count = 0
        self.last_prompt_token_count = 0
        self.last_candidates_token_count = 0
        self.last_thoughts_token_count = 0
        self.last_total_token_count = 0
        self.last_usage_metadata = {}

    def _set_last_usage_metadata(self, usage) -> None:
        self.last_cached_content_token_count = int(getattr(usage, "cached_content_token_count", 0) or 0)
        self.last_prompt_token_count = int(getattr(usage, "prompt_token_count", 0) or 0)
        self.last_candidates_token_count = int(getattr(usage, "candidates_token_count", 0) or 0)
        self.last_thoughts_token_count = int(getattr(usage, "thoughts_token_count", 0) or 0)
        self.last_total_token_count = int(getattr(usage, "total_token_count", 0) or 0)
        self.last_usage_metadata = {
            "cached_content_token_count": self.last_cached_content_token_count,
            "prompt_token_count": self.last_prompt_token_count,
            "candidates_token_count": self.last_candidates_token_count,
            "thoughts_token_count": self.last_thoughts_token_count,
            "total_token_count": self.last_total_token_count,
        }

    def _record_usage_event(self, actual_model: str) -> None:
        context = dict(self.usage_context or {})
        if not context:
            return

        usage = dict(self.last_usage_metadata or {})
        cost = estimate_gemini_usage_cost(actual_model, usage)
        metadata = dict(context.get("metadata") or {})
        for key in ("prompt_size_chars", "estimated_prompt_tokens", "max_output_tokens", "request_kind"):
            if key in context:
                metadata[key] = context.get(key)
        metadata.update(
            {
                "model_family": cost.get("model_family"),
                "long_context_pricing": bool(cost.get("long_context_pricing")),
            }
        )
        used_fallback = bool(actual_model and actual_model != self.model_name)

        try:
            from utils.database.ai_usage_db import record_ai_usage_event

            record_ai_usage_event(
                company_id=context.get("company_id"),
                user_id=context.get("user_id"),
                run_id=context.get("run_id"),
                task_key=str(context.get("task_key") or ""),
                module_key=str(context.get("module_key") or "unknown"),
                agent_key=str(context.get("agent_key") or ""),
                source=str(context.get("source") or ""),
                model=str(actual_model or self.model_name),
                primary_model=str(self.model_name or ""),
                fallback_model=str(self._get_fallback_model() or ""),
                used_fallback=used_fallback,
                usage=usage,
                cost=cost,
                metadata=metadata,
            )
        except Exception as exc:
            log.warning(f"AI usage ledger yozilmadi: {exc}")

    def create_cache(
        self,
        content: str,
        ttl_seconds: int = 600,
        display_name: str = "",
        model_name: str | None = None,
    ) -> str:
        """Gemini explicit context cache yaratadi va cache resource name qaytaradi."""
        self._rate_limit()
        response = self._client.caches.create(
            model=model_name or self.model_name,
            config={
                "contents": str(content or ""),
                "ttl": f"{max(60, int(ttl_seconds or 600))}s",
                "display_name": display_name or "qa-assistant-cache",
            },
        )
        return str(getattr(response, "name", "") or "")

    def delete_cache(self, name: str) -> None:
        cache_name = str(name or "").strip()
        if not cache_name:
            return
        try:
            self._client.caches.delete(name=cache_name)
        except Exception as exc:
            log.warning(f"Gemini cache delete failed: {exc}")

    def analyze(
        self,
        prompt,
        max_output_tokens=GEMINI_HELPER_DEFAULT_MAX_OUTPUT_TOKENS,
        generation_config_overrides: dict | None = None,
        system_instruction: str | None = None,
        cached_content: str | None = None,
        fallback_cached_content: str | None = None,
    ):
        """
        Gemini bilan tahlil — transient retry + model fallback + key fallback bilan.

        Oqim:
          1. Asosiy model bilan urinish; cached fallback mavjud bo'lsa 503 da tez fallback qiladi
          2. Transient xato (503) → fallback model bilan retry
          3. Permanent xato (429/403) → keyingi API key bilan urinish
        """
        self._reset_last_run_state()
        self._rate_limit()

        generation_config = self._build_generation_config(
            self.model_name,
            max_output_tokens,
            generation_config_overrides=generation_config_overrides,
            system_instruction=system_instruction,
        )
        if cached_content:
            generation_config.cached_content = cached_content

        best_idx = self._get_best_available_idx()
        if best_idx is None:
            raise RuntimeError("Barcha API keylar freeze holatida — so'rov yuborib bo'lmaydi")

        if best_idx != self._current_idx:
            prev = self._key_name(self._current_idx)
            self._configure_model(best_idx)
            log.ai_key_fallback(prev, self._key_name(best_idx))

        tried = set()
        last_error = None
        while True:
            current_idx = self._current_idx
            current_name = self._key_name(current_idx)

            if current_idx in tried:
                break

            tried.add(current_idx)

            try:
                # Cached Pro call 503 bersa darhol fallback qilish uchun retry'siz urinish.
                # Cache'siz chaqiruvlar avvalgidek default retry bilan ishlaydi.
                fallback_available = bool(
                    self._get_fallback_model()
                    and cached_content
                    and fallback_cached_content
                )
                primary_retry_delays = [] if fallback_available else None
                result = self._request(prompt, generation_config, retry_delays=primary_retry_delays)
                self.last_model_used = self.model_name
                self.last_used_fallback = False
                return result

            except Exception as e:
                last_error = e

                # Transient xato (503/unavailable): kalit yaxshi, server band —
                # Explicit fallback model bo'lsa, shu model bilan urinib ko'rish.
                if self._is_transient_error(e):
                    fallback_model = self._get_fallback_model()
                    if cached_content and not fallback_cached_content:
                        fallback_model = None
                    if fallback_model:
                        log.warning(
                            f"AI -> {self.model_name} unavailable (503), "
                            f"darhol fallback: {fallback_model} bilan urinilmoqda..."
                        )
                        fallback_config = self._build_generation_config(
                            fallback_model,
                            max_output_tokens,
                            generation_config_overrides=generation_config_overrides,
                            system_instruction=system_instruction,
                        )
                        if fallback_cached_content:
                            fallback_config.cached_content = fallback_cached_content
                        try:
                            result = self._request(prompt, fallback_config, model_name=fallback_model)
                            self.last_model_used = fallback_model
                            self.last_fallback_model_name = fallback_model
                            self.last_used_fallback = True
                            log.info(f"AI -> {fallback_model} muvaffaqiyatli javob berdi")
                            return result
                        except Exception as e_fb:
                            raise RuntimeError(
                                f"model_unavailable: Gemini API: {self.model_name} ham, {fallback_model} ham ishlamadi. "
                                f"({str(e_fb)})"
                            ) from e_fb
                    raise RuntimeError(f"Gemini API xatosi ({current_name}): {str(e)}") from e

                if not self._is_fallback_error(e):
                    raise RuntimeError(f"Gemini API error: {str(e)}") from e

                error_first_line = str(e).splitlines()[0] if str(e) else str(e)
                log.warning(f"AI -> model={self.model_name} | key={current_name} | error: {error_first_line}")

                has_other_keys = any(
                    i != current_idx and not self._is_frozen(i)
                    for i in range(len(self.api_keys))
                )
                if has_other_keys:
                    self._freeze(current_idx)
                else:
                    raise RuntimeError(
                        f"Gemini API xatosi ({current_name}): {str(e)}"
                    ) from e

                next_idx = self._get_best_available_idx()
                if next_idx is None:
                    raise RuntimeError(
                        f"Barcha {len(self.api_keys)} ta kalit ishlamadi. "
                        f"Oxirgi xato: {str(e)}"
                    ) from e

                self._configure_model(next_idx)
                self._rate_limit()

        err_detail = f": {str(last_error)}" if last_error else ""
        raise RuntimeError(f"Barcha API keylarda so'rov muvaffaqiyatsiz tugadi{err_detail}")
