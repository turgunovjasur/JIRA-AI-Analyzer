"""
BaseService - Barcha service'lar uchun base class

Bu class barcha service'larda takrorlanadigan lazy loading patternni
bir joyda to'playdi. Har bir service bu classdan meros oladi va
faqat o'ziga xos logikani yozadi.

Xususiyatlari:
- JIRA, GitHub, Gemini clientlarni lazy loading
- AI limitleri va konfiguratsiya
- Status update helper method
"""

from typing import Optional, Callable
from core.logger import get_logger

# Logger instance
log = get_logger("base.service")

# Settings cache (lazy loading)
_settings_cache = None

def _get_base_settings():
    """Get base service settings from app_settings (cached)"""
    global _settings_cache
    if _settings_cache is None:
        try:
            from config.app_settings import get_app_settings
            _settings_cache = get_app_settings(force_reload=False).queue
        except Exception as e:
            # Default values
            class DefaultSettings:
                ai_max_input_tokens = 900000
                chars_per_token = 4
                ai_max_retries = 3
            _settings_cache = DefaultSettings()
    return _settings_cache


class BaseService:
    """
    Barcha service'lar uchun base class

    Umumiy funksiyalar:
    - Lazy loading: jira, github, gemini
    - Status callback management
    - AI configuration limits
    """

    def __init__(self):
        """Initialize service with lazy loading"""
        # Lazy loaded clients
        self._jira_client = None
        self._github_client = None
        self._gemini_helper = None

        # AI Configuration (settings dan)
        settings = _get_base_settings()
        self.MAX_TOKENS = settings.ai_max_input_tokens
        self.CHARS_PER_TOKEN = settings.chars_per_token
        self.MAX_RETRIES = settings.ai_max_retries

    @property
    def jira(self):
        """
        Lazy JIRA client

        Returns:
            JiraClient: JIRA API client instance
        """
        if self._jira_client is None:
            from utils.jira.jira_client import JiraClient
            self._jira_client = JiraClient()
        return self._jira_client

    @property
    def github(self):
        """
        Lazy GitHub client

        Returns:
            GitHubClient: GitHub API client instance
        """
        if self._github_client is None:
            from utils.github.github_client import GitHubClient
            self._github_client = GitHubClient()
        return self._github_client

    @property
    def gemini(self):
        """
        Lazy Gemini helper

        Returns:
            GeminiHelper: Google Gemini AI helper instance
        """
        if self._gemini_helper is None:
            from utils.ai.gemini_helper import GeminiHelper
            self._gemini_helper = GeminiHelper()
        return self._gemini_helper

    def _create_status_updater(
            self,
            status_callback: Optional[Callable[[str, str], None]] = None
    ) -> Callable[[str, str], None]:
        """
        Status update helper yaratish

        Bu method status callback va console logging uchun umumiy
        funksiya yaratadi. Har bir service o'z analyze methodida
        ishlatishi mumkin.

        Args:
            status_callback: Optional callback function (status_type, message)

        Returns:
            Update function: (status_type: str, message: str) -> None

        Example:
            >>> update_status = self._create_status_updater(callback)
            >>> update_status("info", "Processing...")
            >>> update_status("success", "Done!")
        """

        def update_status(status_type: str, message: str):
            """Status update with callback and logging"""
            if status_callback:
                status_callback(status_type, message)

            # Log based on status_type
            if status_type.lower() == "error":
                log.warning(message)
            else:
                log.info(message)

        return update_status

    def _calculate_text_length(self, text: str) -> dict:
        """
        Text hajmini hisoblash (char, token)

        Args:
            text: Tahlil qilinadigan text

        Returns:
            dict: {
                'chars': int,
                'tokens': int,
                'within_limit': bool
            }
        """
        char_count = len(text)
        token_count = char_count // self.CHARS_PER_TOKEN

        return {
            'chars': char_count,
            'tokens': token_count,
            'within_limit': token_count < self.MAX_TOKENS
        }

    def _truncate_text(self, text: str, max_tokens: Optional[int] = None) -> str:
        """
        Textni AI limit ichida qisqartirish

        Args:
            text: Qisqartirilishi kerak bo'lgan text
            max_tokens: Maksimal token soni (None = self.MAX_TOKENS)

        Returns:
            str: Qisqartirilgan text
        """
        if max_tokens is None:
            max_tokens = self.MAX_TOKENS

        max_chars = max_tokens * self.CHARS_PER_TOKEN

        if len(text) <= max_chars:
            return text

        # Qisqartirish bilan warning
        truncated = text[:max_chars]
        warning = f"\n\n[TEXT TRUNCATED: {len(text)} -> {max_chars} chars]"

        return truncated + warning