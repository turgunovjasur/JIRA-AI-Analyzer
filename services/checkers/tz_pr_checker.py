# Legacy webhook TZ-PR service.
"""
TZ-PR Moslik Tekshirish Service - Refactored Version with Figma

YANGI: Figma dizayn tahlili qo'shildi (OPTIONAL, fail-safe)

Clean Code Principles:
- Single Responsibility
- DRY (Don't Repeat Yourself)
- Clear naming
- Modularity
- Fail-safe design

Author: JASUR TURGUNOV
Version: 7.0 WITH FIGMA
"""
from typing import Any, Dict, List, Optional

# Core imports
from core import BaseService
from core.logger import get_logger

# M1 refactor: TZPRService helperlari mavzu bo'yicha mixinlarga ajratildi.
from services.checkers.tzpr_data_fetch import DataFetchMixin
from services.checkers.tzpr_result_builders import ResultBuildersMixin
from services.checkers.tzpr_text_parser import TextParserMixin

# Initialize logger
log = get_logger("tzpr.checker")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


# Canonical order in which sections appear in the prompt
_SECTION_ORDER = ['summary', 'completed', 'partial', 'failed', 'issues', 'figma']
_PRESENTATION_SECTION_KEYS = ['completed', 'failed', 'skipped', 'issues', 'figma']
_PRESENTATION_SECTION_KEY_SET = set(_PRESENTATION_SECTION_KEYS)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN SERVICE CLASS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TZPRService(BaseService, DataFetchMixin, ResultBuildersMixin, TextParserMixin):
    """TZ va PR mosligini tekshirish - With Figma Support.

    Helper metodlar mavzu bo'yicha mixinlarga ajratilgan (M1 refactor):
    DataFetchMixin (JIRA/PR/Figma/TZ olish), ResultBuildersMixin (natija/matritsa
    qurish), TextParserMixin (matn/patch parse). `self.` chaqiruvlar MRO orqali ishlaydi.
    """

    def __init__(self, company_id: int = None, user_id: int = None):
        """Initialize service.
        UI modullar: user_id bilan yarating (user_credentials ishlatadi).
        Webhook:     company_id bilan yarating (company_settings ishlatadi).
        """
        super().__init__(company_id=company_id, user_id=user_id)
        self._pr_helper = None
        self._figma_client = None  # per-file topilgan token bilan yaratiladi

    def _get_settings(self):
        """User yoki kompaniya TZ-PR sozlamalarini qaytarish.
        UI (user_id bor): tz_pr_checker — user-specific settings
        Webhook (faqat company_id): webhook_tz_pr — kompaniya webhook settings
        """
        if self._user_id is not None and self._company_id is not None:
            from config.app_settings import get_app_settings_for_user
            return get_app_settings_for_user(self._user_id, self._company_id).tz_pr_checker
        if self._company_id is not None:
            from config.app_settings import get_app_settings_for_company
            return get_app_settings_for_company(self._company_id).webhook_tz_pr
        from config.app_settings import get_app_settings
        return get_app_settings().tz_pr_checker

    def _get_canonical_analysis_sections(self) -> List[str]:
        """Gemini prompt va structured result uchun doimiy to'liq section ro'yxati."""
        return list(_SECTION_ORDER)

    def _get_visible_sections_from_settings(self) -> List[str]:
        """Ko'rinish uchun ishlatiladigan sectionlar — analysisni emas, faqat renderni boshqaradi."""
        configured = self._get_settings().visible_sections or []
        filtered = [key for key in configured if key in _PRESENTATION_SECTION_KEY_SET]
        return filtered or ['completed', 'failed', 'skipped', 'issues', 'figma']

    def _build_effective_settings(
            self,
            requested_output_profile: str = "comment",
            effective_use_smart_patch: Optional[bool] = None,
    ) -> Dict[str, Any]:
        settings = self._get_settings()
        default_use_smart_patch = bool(getattr(settings, "default_use_smart_patch", False))
        try:
            agent2_parallelism = int(getattr(settings, "agent2_parallelism", 5) or 5)
        except (TypeError, ValueError):
            agent2_parallelism = 5
        agent2_parallelism = max(1, min(16, agent2_parallelism))
        try:
            agent2_batch_size = int(getattr(settings, "agent2_batch_size", 6) or 6)
        except (TypeError, ValueError):
            agent2_batch_size = 6
        agent2_batch_size = max(1, min(20, agent2_batch_size))
        ai_data_section_order = list(
            getattr(settings, "ai_data_section_order", None) or ["tz", "comments", "figma", "code"]
        )
        try:
            agent1_coverage_threshold = float(getattr(settings, "agent1_coverage_threshold", 1.0))
        except (TypeError, ValueError):
            agent1_coverage_threshold = 1.0
        agent1_coverage_threshold = max(0.0, min(1.0, agent1_coverage_threshold))
        return {
            "visible_sections": self._get_visible_sections_from_settings(),
            "read_comments_enabled": bool(getattr(settings, "read_comments_enabled", True)),
            "max_comments_to_read": int(getattr(settings, "max_comments_to_read", 0) or 0),
            "dev_comment_source": str(getattr(settings, "dev_comment_source", "assignee_reporter") or "assignee_reporter"),
            "default_use_smart_patch": default_use_smart_patch,
            "agent2_parallelism": agent2_parallelism,
            "agent2_batch_size": agent2_batch_size,
            "agent2_extra_scan_enabled": bool(getattr(settings, "agent2_extra_scan_enabled", True)),
            "effective_use_smart_patch": (
                bool(effective_use_smart_patch)
                if effective_use_smart_patch is not None
                else default_use_smart_patch
            ),
            "ai_data_section_order": ai_data_section_order,
            "show_contradictory_comments": bool(
                getattr(settings, "show_contradictory_comments", False)
            ),
            "agent1_rules": {
                "figma_scope_enabled": "figma" in ai_data_section_order,
                "coverage_threshold": agent1_coverage_threshold,
            },
            "requested_output_profile": (requested_output_profile or "comment").strip().lower(),
        }
