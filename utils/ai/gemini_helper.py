from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import time
from core.logger import get_logger

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
    ]

    # Transient xatolik uchun kutish vaqtlari (soniya)
    TRANSIENT_RETRY_DELAYS = [5, 10, 20]

    def __init__(self, api_keys: list = None, model_name: str = None):
        if api_keys is not None:
            if not api_keys:
                raise RuntimeError("Kompaniya Gemini API kalitlari kiritilmagan. Sozlamalar sahifasida kalit kiriting.")
            self.api_keys = [k for k in api_keys if k and k.strip()]
            if not self.api_keys:
                raise RuntimeError("Kompaniya Gemini API kalitlari bo'sh. Sozlamalar sahifasida kalit kiriting.")
            log.info(f"GeminiHelper: {len(self.api_keys)} ta kalit yuklandi (1-kalit: ...{self.api_keys[0][-6:]})")
        else:
            self.api_keys = self._load_keys()

        self._frozen_until = {}
        self._current_idx = 0
        self.model_name = model_name or os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
        self.last_request_time = 0
        self.request_count = 0
        self._client = genai.Client(api_key=self.api_keys[self._current_idx])

    def _load_keys(self) -> list[str]:
        raise RuntimeError(
            "GeminiHelper: api_keys ko'rsatilmagan. "
            "Kompaniya Gemini API kalitlarini DB ga kiriting (Sozlamalar → API Kalitlar)."
        )

    def _key_name(self, idx: int) -> str:
        return f"KEY_{idx + 1}"

    def _configure_model(self, idx: int):
        self._client = genai.Client(api_key=self.api_keys[idx])
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
        """Vaqtinchalik server xatosi (503, overloaded) — bir oz kutib qayta urinish kerak."""
        error_msg = str(error).lower()
        return any(kw in error_msg for kw in self.TRANSIENT_ERROR_KEYWORDS)

    def _build_generation_config(self, model_name: str, max_output_tokens: int):
        """Model nomiga qarab to'g'ri GenerateContentConfig yaratish."""
        requires_thinking = 'flash' not in model_name.lower()
        if requires_thinking:
            return types.GenerateContentConfig(max_output_tokens=max_output_tokens)
        return types.GenerateContentConfig(
            max_output_tokens=max_output_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

    def _get_fallback_model(self) -> str | None:
        """GEMINI_FALLBACK_MODEL .env dan olinadi. Asosiy model bilan bir xil bo'lsa None."""
        fallback = os.getenv('GEMINI_FALLBACK_MODEL', '').strip()
        if fallback and fallback != self.model_name:
            return fallback
        return None

    def _request(self, prompt, generation_config, model_name: str = None):
        """Bitta Gemini so'rov — transient xato bo'lsa backoff bilan N marta qayta urinish."""
        target_model = model_name or self.model_name
        last_error = None
        for attempt, delay in enumerate([0] + list(self.TRANSIENT_RETRY_DELAYS)):
            if delay > 0:
                log.warning(
                    f"AI -> transient xato, retry {attempt}/{len(self.TRANSIENT_RETRY_DELAYS)} "
                    f"| {delay}s kutilmoqda | model={target_model} | key={self._key_name(self._current_idx)}"
                )
                time.sleep(delay)

            try:
                response = self._client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=generation_config,
                )
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

    def analyze(self, prompt, max_output_tokens=32768):
        """
        Gemini bilan tahlil — transient retry + model fallback + key fallback bilan.

        Oqim:
          1. Asosiy model (GEMINI_MODEL) bilan 3 marta retry (5s→10s→20s)
          2. Transient xato (503) → GEMINI_FALLBACK_MODEL bilan 3 marta retry
          3. Permanent xato (429/403) → keyingi API key bilan urinish
        """
        self._rate_limit()

        generation_config = self._build_generation_config(self.model_name, max_output_tokens)

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
                return self._request(prompt, generation_config)

            except Exception as e:
                last_error = e

                # Transient xato (503/unavailable): kalit yaxshi, server band —
                # GEMINI_FALLBACK_MODEL bilan urinib ko'rish
                if self._is_transient_error(e):
                    fallback_model = self._get_fallback_model()
                    if fallback_model:
                        log.warning(
                            f"AI -> {self.model_name} unavailable (503), "
                            f"fallback: {fallback_model} bilan urinilmoqda..."
                        )
                        fallback_config = self._build_generation_config(fallback_model, max_output_tokens)
                        try:
                            result = self._request(prompt, fallback_config, model_name=fallback_model)
                            log.info(f"AI -> {fallback_model} muvaffaqiyatli javob berdi")
                            return result
                        except Exception as e_fb:
                            raise RuntimeError(
                                f"Gemini API: {self.model_name} ham, {fallback_model} ham ishlamadi. "
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
