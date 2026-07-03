# core/constants.py
"""
Tizim return reason kodlari.

Har bir kod nima uchun task qaytarilganini bildiradi.
DB da return_reason ustunida saqlanadi.
JIRA comment boshiga [AI_S1][KOD] ko'rinishida yoziladi.
"""

# Servis-1 tomonidan qaytarilish sabablari
WARN_LOW_SCORE      = "WARN_LOW_SCORE"       # Score threshold dan past
WARN_MIN_TZ         = "WARN_MIN_TZ"          # TZ juda qisqa (min chars)
WARN_NO_PR          = "WARN_NO_PR"           # GitHub da PR topilmadi
WARN_PR_NOT_MERGED  = "WARN_PR_NOT_MERGED"   # PR mavjud lekin merge qilinmagan

# Tizim xatoliklari (qaytarilmaydi, retry bo'ladi)
WARN_AI_TIMEOUT     = "WARN_AI_TIMEOUT"      # AI rate limit / quota / timeout
ERR_UNKNOWN         = "ERR_UNKNOWN"          # Kutilmagan tizim xatosi

# Faqat WARN_LOW_SCORE da dev objections o'qiladi (developer kod tuzatgan)
# Qolgan kodlarda task yangicha tahlil qilinadi (dev izohlar bog'liq emas)
RECHECK_REASONS = {WARN_LOW_SCORE}

# Eski STATUS_* konstantalar o'chirildi (DB qiymatlariga mos emas va ishlatilmagan).
# Status qiymatlari va tranzitsiya qoidalari: core/task_state.py (TaskStatus, ServiceStatus)
