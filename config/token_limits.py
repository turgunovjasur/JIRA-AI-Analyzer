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

# Cost control thresholdlari.
# Gemini 2.5 Pro pricing'da long-context narx pog'onasi prompt token 200K dan boshlanadi.
AI_COST_WARNING_INPUT_TOKENS = 180000
AI_LONG_CONTEXT_PRICE_THRESHOLD_TOKENS = 200000

# GeminiHelper analyze() default max_output_tokens (explicit berilmasa)
GEMINI_HELPER_DEFAULT_MAX_OUTPUT_TOKENS = 32768
