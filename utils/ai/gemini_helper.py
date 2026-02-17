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
            log.warning(f"Settings yuklanmadi, default ishlatiladi: {e}")
            # Default values
            class DefaultSettings:
                gemini_min_interval = 6
                key_freeze_duration = 600
            _settings_cache = DefaultSettings()
    return _settings_cache


class GeminiHelper:
    """
    Gemini AI Helper - API Key Fallback + Freeze bilan

    Agar GOOGLE_API_KEY bilan xatolik bo'lsa (limit, quota, invalid),
    KEY_1 10 daqiqaga muzlatiladi va KEY_2 ga o'tiladi.
    10 daqiqa o'tgach KEY_1 ga qaytiladi.
    Agar KEY_2 ham xato bersa — xatolik raise qilinadi.
    """

    # Fallback tetiklaydigan xatolik kalit so'zlari
    FALLBACK_ERROR_KEYWORDS = [
        'resource_exhausted', '429', 'quota', 'rate limit',
        'api key', 'invalid', 'permission', 'forbidden', '403',
        'billing', 'exceeded'
    ]

    def __init__(self):
        # API kalitlar
        self.api_key_1 = os.getenv('GOOGLE_API_KEY')
        self.api_key_2 = os.getenv('GOOGLE_API_KEY_2')
        self.current_key = self.api_key_1
        self.using_fallback = False

        # KEY_1 muzlatish holati
        self._key1_frozen_until = None  # timestamp — qachon muzlatish tugaydi

        # Model nomi
        self.model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

        # Modelni sozlash
        genai.configure(api_key=self.current_key)
        self.model = genai.GenerativeModel(self.model_name)

        # Rate limiting
        self.request_count = 0
        self.last_request_time = 0

        # Log
        key_count = 2 if self.api_key_2 else 1
        log.ai_ready(self.model_name, key_count)

    def _rate_limit(self):
        """Rate limiting: max 10 req/min (settings dan)"""
        settings = _get_gemini_settings()
        min_interval = settings.gemini_min_interval

        elapsed = time.time() - self.last_request_time
        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            key_name = "KEY_2" if self.using_fallback else "KEY_1"
            log.ai_rate_limit(key_name, int(wait_time))
            time.sleep(wait_time)

        self.last_request_time = time.time()
        self.request_count += 1

    def _is_fallback_error(self, error: Exception) -> bool:
        """Xatolik fallback talab qiladimi tekshirish"""
        error_msg = str(error).lower()
        return any(kw in error_msg for kw in self.FALLBACK_ERROR_KEYWORDS)

    def _is_key1_frozen(self) -> bool:
        """KEY_1 hali muzlatilganmi?"""
        if self._key1_frozen_until is None:
            return False
        return time.time() < self._key1_frozen_until

    def _freeze_key1(self):
        """KEY_1 ni N daqiqaga muzlatish — bu vaqt ichida faqat KEY_2 ishlatiladi"""
        settings = _get_gemini_settings()
        freeze_duration = settings.key_freeze_duration
        self._key1_frozen_until = time.time() + freeze_duration
        log.warning(f"KEY_1 muzlatildi: {int(freeze_duration / 60)} daqiqaga")

    def _unfreeze_key1(self):
        """KEY_1 ni qayta faollashtirish va primary key ga qaytish"""
        self._key1_frozen_until = None
        self.using_fallback = False
        self.current_key = self.api_key_1
        genai.configure(api_key=self.current_key)
        self.model = genai.GenerativeModel(self.model_name)
        log.info("KEY_1 qayta faollashtirildi (muzlatish muddati tugadi)")

    def _switch_to_fallback(self) -> bool:
        """
        GOOGLE_API_KEY_2 ga o'tish

        Returns:
            bool: True — muvaffaqiyatli o'tdi, False — imkonsiz
        """
        if not self.api_key_2:
            log.warning("GOOGLE_API_KEY_2 .env da mavjud emas, fallback imkonsiz")
            return False

        if self.using_fallback:
            # Allaqachon fallback da — qayta o'tish imkonsiz
            return False

        # O'tish
        self.current_key = self.api_key_2
        self.using_fallback = True
        genai.configure(api_key=self.current_key)
        self.model = genai.GenerativeModel(self.model_name)

        log.ai_key_fallback("KEY_1", "KEY_2")
        return True

    def analyze(self, prompt, max_output_tokens=8192):
        """
        Gemini bilan tahlil — API Key Freeze + Fallback bilan

        Logika:
        1. KEY_1 muzlatilgan bo'lsa → KEY_2 bilan ishlash
        2. KEY_1 muzlatish muddati o'tgan bo'lsa → KEY_1 ga qaytish
        3. KEY_1 bilan so'rov yuborish
        4. KEY_1 xato → KEY_1 ni 10 daqiqaga muzlatish → KEY_2 bilan qayta urinish
        5. KEY_2 ham xato → RuntimeError raise

        Args:
            prompt: AI ga yuboriladigan prompt
            max_output_tokens: Javob uchun maksimal token soni (default: 8192)
        """
        self._rate_limit()

        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_output_tokens,
        )

        # === 1. KEY_1 muzlatilgan — faqat KEY_2 bilan ishlash ===
        if self._is_key1_frozen():
            remaining = self._key1_frozen_until - time.time()
            log.info(f"KEY_1 muzlatilgan ({int(remaining)}s qoldi), KEY_2 bilan ishlash")

            # KEY_2 ga o'tish (agar hali o'tmagan bo'lsa)
            if not self.using_fallback:
                if not self._switch_to_fallback():
                    raise RuntimeError(
                        "KEY_1 muzlatilgan, KEY_2 mavjud emas — so'rov yuborib bo'lmaydi"
                    )

            try:
                response = self.model.generate_content(prompt, generation_config=generation_config)
                return response.text
            except Exception as e:
                log.warning(f"KEY_2 xato (KEY_1 muzlatilgan): {e}")
                raise RuntimeError(
                    f"KEY_2 ham xato berdi (KEY_1 muzlatilgan): {str(e)}"
                ) from e

        # === 2. KEY_1 muzlatish muddati tugagan — qaytish ===
        if self._key1_frozen_until is not None and not self._is_key1_frozen():
            self._unfreeze_key1()

        # === 3. KEY_1 bilan normal ishlash ===
        # Agar hali fallback da bo'lsa (bu bo'lmasligi kerak, lekin himoya uchun)
        if self.using_fallback and not self._is_key1_frozen():
            self._unfreeze_key1()

        try:
            response = self.model.generate_content(prompt, generation_config=generation_config)
            return response.text
        except Exception as e:
            # === 4. KEY_1 xato — muzlatish va KEY_2 ga o'tish ===
            if self._is_fallback_error(e):
                log.warning(f"KEY_1 xato: {e}")

                # KEY_1 ni muzlatish
                self._freeze_key1()

                if self._switch_to_fallback():
                    log.info("KEY_2 bilan qayta urinish...")

                    # KEY_2 bilan qayta urinish
                    self._rate_limit()
                    try:
                        response = self.model.generate_content(prompt, generation_config=generation_config)
                        log.info("KEY_2 bilan muvaffaqiyatli!")
                        return response.text
                    except Exception as e2:
                        log.warning(f"KEY_2 ham xato berdi: {e2}")
                        raise RuntimeError(
                            f"Gemini API xatosi (ikkala key ham ishlamadi): {str(e2)}"
                        ) from e2

            # === 5. Fallback imkonsiz yoki xatolik turi boshqa ===
            raise RuntimeError(f"Gemini API xatosi: {str(e)}") from e
