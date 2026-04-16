import google.generativeai as genai
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

    .env da qancha key bo'lsa hammasi avtomatik yuklanadi:
      GOOGLE_API_KEY    → KEY_1
      GOOGLE_API_KEY_2  → KEY_2
      GOOGLE_API_KEY_3  → KEY_3
      ...

    Logika:
    - Joriy key xato bersa → freeze qilinadi → keyingi mavjud key ga o'tiladi
    - Barcha keylar freeze bo'lsa → RuntimeError raise
    - Freeze muddati tugagach → o'sha key qayta ishga kiradi
    - Har doim eng kichik indeksli (birinchi) mavjud key ishlatiladi
    """

    FALLBACK_ERROR_KEYWORDS = [
        'resource_exhausted', '429', 'quota', 'rate limit',
        'api key', 'invalid', 'permission', 'forbidden', '403',
        'billing', 'exceeded'
    ]

    def __init__(self):
        # Barcha keylarni dinamik yuklash
        self.api_keys = self._load_keys()

        # Har bir key uchun freeze timestamp {index: frozen_until}
        self._frozen_until = {}

        # Joriy aktiv key indeksi
        self._current_idx = 0

        # Model nomi
        self.model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0

        # Modelni boshlang'ich key bilan sozlash
        self._configure_model(self._current_idx)

    def _load_keys(self) -> list[str]:
        """
        .env dan barcha GOOGLE_API_KEY* larni yuklash.
        GOOGLE_API_KEY, GOOGLE_API_KEY_2, GOOGLE_API_KEY_3, ...
        """
        keys = []

        # Birinchi key (GOOGLE_API_KEY)
        key1 = os.getenv('GOOGLE_API_KEY')
        if key1:
            keys.append(key1)

        # Qolgan keylar (GOOGLE_API_KEY_2, _3, _4, ...)
        i = 2
        while True:
            key = os.getenv(f'GOOGLE_API_KEY_{i}')
            if not key:
                break
            keys.append(key)
            i += 1

        if not keys:
            raise RuntimeError("Hech qanday GOOGLE_API_KEY topilmadi!")

        return keys

    def _key_name(self, idx: int) -> str:
        return f"KEY_{idx + 1}"

    def _configure_model(self, idx: int):
        """Berilgan indeksdagi key bilan modalni sozlash"""
        genai.configure(api_key=self.api_keys[idx])
        self.model = genai.GenerativeModel(self.model_name)
        self._current_idx = idx

    def _is_frozen(self, idx: int) -> bool:
        """Berilgan indeksdagi key freeze holatidami"""
        until = self._frozen_until.get(idx)
        if until is None:
            return False
        if time.time() >= until:
            # Freeze muddati tugagan — tozalash
            del self._frozen_until[idx]
            log.info(f"AI-KEY -> {self._key_name(idx)} unfrozen, available again")
            return False
        return True

    def _freeze(self, idx: int):
        """Berilgan indeksdagi keyni N daqiqaga freeze qilish"""
        settings = _get_gemini_settings()
        duration = settings.key_freeze_duration
        self._frozen_until[idx] = time.time() + duration
        log.warning(f"AI-KEY -> {self._key_name(idx)} frozen for {int(duration / 60)} min")

    def _get_best_available_idx(self) -> int | None:
        """
        Freeze bo'lmagan eng kichik indeksli keyni qaytarish.
        Hech biri mavjud bo'lmasa None qaytaradi.
        """
        for idx in range(len(self.api_keys)):
            if not self._is_frozen(idx):
                return idx
        return None

    def _rate_limit(self):
        """Rate limiting: settings.gemini_min_interval soniya interval"""
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

    def analyze(self, prompt, max_output_tokens=8192):
        """
        Gemini bilan tahlil — N ta key fallback bilan.

        1. Eng yaxshi (eng kichik indeksli, freeze bo'lmagan) key tanlanadi
        2. Joriy key o'sha key bo'lmasa — switch qilinadi
        3. So'rov yuboriladi
        4. Xato bo'lsa — key freeze → keyingi key bilan qayta urinish
        5. Barcha keylar freeze → RuntimeError
        """
        self._rate_limit()

        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_output_tokens,
        )

        # Eng yaxshi mavjud keyga switch qilish
        best_idx = self._get_best_available_idx()
        if best_idx is None:
            raise RuntimeError("Barcha API keylar freeze holatida — so'rov yuborib bo'lmaydi")

        if best_idx != self._current_idx:
            prev = self._key_name(self._current_idx)
            self._configure_model(best_idx)
            log.ai_key_fallback(prev, self._key_name(best_idx))

        # So'rov yuborish — xato bo'lsa keyingi keyga o'tib qayta urinish
        tried = set()
        while True:
            current_idx = self._current_idx
            current_name = self._key_name(current_idx)

            if current_idx in tried:
                break

            tried.add(current_idx)

            try:
                response = self.model.generate_content(prompt, generation_config=generation_config)
                return response.text

            except Exception as e:
                if not self._is_fallback_error(e):
                    raise RuntimeError(f"Gemini API error: {str(e)}") from e

                error_first_line = str(e).splitlines()[0] if str(e) else str(e)
                log.warning(f"AI -> model={self.model_name} | key={current_name} | error: {error_first_line}")

                # Joriy keyni freeze qilish
                self._freeze(current_idx)

                # Keyingi mavjud keyni topish
                next_idx = self._get_best_available_idx()
                if next_idx is None:
                    raise RuntimeError(
                        f"AI xatosi: Gemini API error (all {len(self.api_keys)} keys failed): {str(e)}"
                    ) from e

                # Keyingi key ga o'tish va qayta urinish
                self._configure_model(next_idx)
                self._rate_limit()

        raise RuntimeError("Barcha API keylarda so'rov muvaffaqiyatsiz tugadi")
