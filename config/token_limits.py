"""
Platform-level AI token policy.

Barcha AI token limitlari shu yerda markaziy boshqariladi.
Tenant/user darajasida o'zgartirilmaydi.
"""

# Checker (TZ-PR) AI javobi uchun maksimal output token
CHECKER_MAX_OUTPUT_TOKENS = 16384

# Testcase generator AI javobi uchun maksimal output token
TESTCASE_MAX_OUTPUT_TOKENS = 16384

# Prompt/input hajmi uchun global limit va hisoblash koeffitsiyenti
AI_MAX_INPUT_TOKENS = 900000
CHARS_PER_TOKEN = 4

# GeminiHelper analyze() default max_output_tokens (explicit berilmasa)
GEMINI_HELPER_DEFAULT_MAX_OUTPUT_TOKENS = 32768
