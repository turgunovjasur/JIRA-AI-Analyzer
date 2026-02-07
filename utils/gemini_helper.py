import google.generativeai as genai
import os
from dotenv import load_dotenv
import time
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class GeminiHelper:
    """
    Gemini AI Helper - API Key Fallback bilan

    Agar GOOGLE_API_KEY bilan xatolik bo'lsa (limit, quota, invalid),
    avtomatik GOOGLE_API_KEY_2 ga o'tadi (agar mavjud bo'lsa).
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

        # Model nomi
        self.model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

        # Modelni sozlash
        genai.configure(api_key=self.current_key)
        self.model = genai.GenerativeModel(self.model_name)

        # Rate limiting
        self.request_count = 0
        self.last_request_time = 0

        # Log
        key_status = "1 ta key"
        if self.api_key_2:
            key_status = "2 ta key (fallback mavjud)"
        logger.info(f"Gemini AI tayyor: {self.model_name} | {key_status}")
        print(f"Gemini AI tayyor: {self.model_name} | {key_status}")

    def _rate_limit(self):
        """Rate limiting: max 10 req/min"""
        min_interval = 6  # 60/10 = 6 sekund

        elapsed = time.time() - self.last_request_time
        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            print(f"Kutish: {wait_time:.1f} sekund...")
            time.sleep(wait_time)

        self.last_request_time = time.time()
        self.request_count += 1

    def _is_fallback_error(self, error: Exception) -> bool:
        """Xatolik fallback talab qiladimi tekshirish"""
        error_msg = str(error).lower()
        return any(kw in error_msg for kw in self.FALLBACK_ERROR_KEYWORDS)

    def _switch_to_fallback(self) -> bool:
        """
        GOOGLE_API_KEY_2 ga o'tish

        Returns:
            bool: True — muvaffaqiyatli o'tdi, False — imkonsiz
        """
        if not self.api_key_2:
            logger.warning("❌ GOOGLE_API_KEY_2 .env da mavjud emas, fallback imkonsiz")
            print("❌ GOOGLE_API_KEY_2 .env da mavjud emas, fallback imkonsiz")
            return False

        if self.using_fallback:
            # Allaqachon fallback da — qayta o'tish imkonsiz
            return False

        # O'tish
        self.current_key = self.api_key_2
        self.using_fallback = True
        genai.configure(api_key=self.current_key)
        self.model = genai.GenerativeModel(self.model_name)

        logger.info("🔄 GOOGLE_API_KEY_2 ga o'tildi (fallback)")
        print("🔄 GOOGLE_API_KEY_2 ga o'tildi (fallback)")
        return True

    def analyze(self, prompt, max_output_tokens=8192):
        """
        Gemini bilan tahlil — API Key Fallback bilan

        1. Asosiy key bilan so'rov yuboriladi
        2. Xatolik bo'lsa va fallback mumkin bo'lsa — KEY_2 bilan qayta urinadi
        3. Ikkinchi key ham xato bersa — xatolik raise qilinadi

        Args:
            prompt: AI ga yuboriladigan prompt
            max_output_tokens: Javob uchun maksimal token soni (default: 8192)
        """
        self._rate_limit()

        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_output_tokens,
        )

        try:
            response = self.model.generate_content(prompt, generation_config=generation_config)
            return response.text
        except Exception as e:
            # Fallback kerakmi tekshirish
            if self._is_fallback_error(e) and self._switch_to_fallback():
                logger.warning(f"⚠️ Asosiy API key xato: {e}")
                logger.info("🔄 Fallback key bilan qayta urinish...")
                print(f"⚠️ Asosiy API key xato: {e}")
                print("🔄 Fallback key bilan qayta urinish...")

                # Fallback key bilan qayta urinish
                self._rate_limit()
                try:
                    response = self.model.generate_content(prompt, generation_config=generation_config)
                    logger.info("✅ Fallback key bilan muvaffaqiyatli!")
                    print("✅ Fallback key bilan muvaffaqiyatli!")
                    return response.text
                except Exception as e2:
                    logger.error(f"❌ Fallback key ham xato berdi: {e2}")
                    raise RuntimeError(
                        f"Gemini API xatosi (ikkala key ham ishlamadi): {str(e2)}"
                    ) from e2

            # Fallback imkonsiz yoki xatolik turi boshqa
            raise RuntimeError(f"Gemini API xatosi: {str(e)}") from e
