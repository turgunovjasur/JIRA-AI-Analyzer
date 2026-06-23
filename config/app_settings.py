# config/app_settings.py
"""
Yagona Tizim Sozlamalari

Barcha modullar uchun yagona sozlamalar:
- Modul ko'rinishi (yoqish/o'chirish)
- Bug Analyzer sozlamalari
- Statistics sozlamalari
- TZ-PR Checker sozlamalari
- Testcase Generator sozlamalari

Har bir sozlama uchun yordam matni mavjud.

Author: JASUR TURGUNOV
Version: 1.0
"""
import json
import os
from dataclasses import dataclass, field, asdict, replace as dc_replace
from typing import Optional, List
from core.logger import get_logger
from config.token_limits import (
    AI_MAX_INPUT_TOKENS,
    CHARS_PER_TOKEN,
    CHECKER_MAX_OUTPUT_TOKENS,
    TESTCASE_MAX_OUTPUT_TOKENS,
)

log = get_logger("config.settings")

# Sozlamalar fayli joylashuvi
SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data',
    'app_settings.json'
)

# Eski TZ-PR sozlamalari fayli (migratsiya uchun)
OLD_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data',
    'tz_pr_settings.json'
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODUL KO'RINISHI SOZLAMALARI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class ModuleVisibility:
    """Modullarni ko'rsatish/berkitish sozlamalari"""
    bug_analyzer_enabled: bool = True
    statistics_enabled: bool = True
    tz_pr_checker_enabled: bool = True
    testcase_generator_enabled: bool = True

    # Yordam matnlari
    bug_analyzer_help: str = "Embedding model va VectorDB yuklanadi. Katta hajmli resurs."
    statistics_help: str = "Sprint statistikasi. Minimal resurs."
    tz_pr_checker_help: str = "TZ-PR moslik tekshirish. Gemini API ishlatadi."
    testcase_generator_help: str = "Test case generator. Gemini API ishlatadi."


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BUG ANALYZER SOZLAMALARI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class BugAnalyzerSettings:
    """Bug Analyzer modul sozlamalari"""
    default_top_n: int = 5
    default_min_similarity: int = 75  # foiz

    # Yordam matnlari
    top_n_help: str = "Eng yuqori o'xshashlikdagi topilgan tasklar soni (1-10)"
    min_similarity_help: str = "Minimal o'xshashlik foizi. Past qiymat - ko'proq natija, lekin kam aniqlik"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATISTICS SOZLAMALARI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class StatisticsSettings:
    """Statistics modul sozlamalari"""
    default_chart_theme: str = "Dark"

    # Yordam matnlari
    chart_theme_help: str = "Grafik uchun rang sxemasi: Dark yoki Light"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMMENT O'QISH SOZLAMALARI (TZ-PR + Testcase uchun)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class CommentReadingSettings:
    """JIRA comment o'qish sozlamalari (ikkala modul uchun ortaq)"""
    read_comments_enabled: bool = True
    max_comments_to_read: int = 0  # 0 = barcha (barchasi)

    # Yordam matnlari
    read_comments_help: str = (
        "JIRA task comment'larini AI ga yuborish yoqish/o'chirish. "
        "O'chirilgan bo'lsa comment'lar AI ga bildirilmaydi."
    )
    max_comments_help: str = (
        "AI ga yuborilgan comment'lar soni. "
        "0 = barcha comment'lar. "
        "Masalan, 5 — faqat so'nggi 5 comment o'qiladi."
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TZ-PR CHECKER SOZLAMALARI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class TZPRCheckerSettings:
    """TZ-PR Checker modul sozlamalari"""
    agent2_parallelism: int = 5
    agent2_batch_size: int = 6
    trusted_scope_comment_authors: str = ""  # deprecated — dev_comment_source bilan almashtirildi
    # Qaysi dev commentlar Agent3 (arbiter) ga beriladi: "assignee_reporter" yoki "all"
    dev_comment_source: str = "assignee_reporter"
    agent1_coverage_threshold: float = 1.0
    agent1_primary_model: str = ""
    agent1_fallback_model: str = ""
    agent2_primary_model: str = ""
    agent2_fallback_model: str = ""
    agent3_primary_model: str = ""
    agent3_fallback_model: str = ""

    # Threshold Sozlamalari
    return_threshold: int = 60
    auto_return_enabled: bool = False

    # AI Token Sozlamalari
    ai_max_output_tokens: int = CHECKER_MAX_OUTPUT_TOKENS  # Gemini javob uchun max token

    # Status Nomlari
    trigger_status: str = "READY TO TEST"
    trigger_status_aliases: str = "READY TO TEST,Ready To Test"
    return_status: str = "NEED CLARIFICATION/RETURN TEST"

    # Comment Formati (HARDCODED - UI dan o'zgartirib bo'lmaydi)
    # Quyidagi sozlamalar doim True, chunki barcha JIRA comment'larda
    # ADF dropdown format, statistika va moslik bali ko'rsatilishi shart.
    use_adf_format: bool = True             # Har doim ADF dropdown format
    # Har doim statistika ko'rsatiladi
    show_statistics: bool = True
    # Har doim moslik bali ko'rsatiladi
    show_compliance_score: bool = True

    # ━━━ Sozlanadigan Matnlar ━━━
    # TZ-PR comment footer
    tz_pr_footer_text: str = (
        "🤖 Bu komment AI tomonidan avtomatik yaratilgan. "
        "Savollar bo'lsa QA Team ga murojaat qiling."
    )
    # Moslik bali past bo'lsa qaytarish notification paneli
    return_notification_text: str = (
        "TZ-PR tekshiruvi past natija ko'rsatdi. "
        "Iltimos, TZ talablarini to'liq bajarilganligini tekshiring "
        "va qaytadan PR bering."
    )
    # DEV yozadigan skip kodi (kommentga yozilsa AI tekshirish o'chiladi)
    skip_code: str = "AI_SKIP"
    # Skip code topilganda JIRA ga yoziladigan xabar
    skip_comment_text: str = (
        "⏭️ AI tekshirish o'chirilgan. "
        "Dev tomanidan skip ko'rsatma berilgan. "
        "Manual tekshirish tavsiya etiladi."
    )
    # Re-check vaqtida (task qaytarildigan so'ng yana Ready to Test) AI xabari
    recheck_comment_text: str = (
        "🔄 Re-check: Task qaytarildigan so'ng qaytadan tekshirilmoqda..."
    )

    # ━━━ Comment O'qish ━━━
    read_comments_enabled: bool = True
    max_comments_to_read: int = 0  # 0 = barcha

    # ━━━ Zid Commentlar ━━━
    # Zid commentlar panelini JIRA comment'da ko'rsatish
    show_contradictory_comments: bool = True

    # ━━━ Comment Bo'limlarini Ko'rsatish ━━━
    # UI final report va JIRA comment bir xil canonical bo'lim contractidan foydalanadi.
    visible_sections: List[str] = field(default_factory=lambda: [
        'completed', 'failed', 'skipped', 'issues', 'figma'
    ])

    # ━━━ Webhook Filtrlari ━━━
    # Faqat bu issue type'lar uchun servislar ishga tushadi (vergul bilan)
    # Bo'sh qolsa — barcha type'lar uchun ishlaydi
    allowed_issue_types: str = "DEV- PROD TASK,DEV-BUG,DEV-TECHTASK,DEV-CLIENT TASK"
    allowed_issue_types_help: str = (
        "Faqat bu issue type'lar uchun webhook servislar ishga tushadi. "
        "Vergul bilan ajrating: 'DEV-BUG,DEV-TECHTASK,DEV- PROD TASK,DEV-CLIENT TASK'. "
        "Bo'sh qolsa — barcha type'lar uchun ishlaydi (filter o'chiq)."
    )
    # Bu ro'yxatdagi assignee'lar (displayName) uchun barcha servislar skip bo'ladi
    # Bo'sh qolsa — filter o'chiq (hammaga ishlaydi)
    excluded_assignees: str = ""
    excluded_assignees_help: str = (
        "Bu ro'yxatdagi assignee'lar uchun barcha servislar ishga tushmaydi (skip). "
        "JIRA displayName bo'yicha, vergul bilan: 'Alisher Karimov, Bobur Toshmatov'. "
        "Bo'sh qolsa — filter o'chiq (hammaga ishlaydi)."
    )

    # ━━━ TZ Minimal Uzunlik ━━━
    # Ikkala servis (Servis-1 va Servis-2) uchun: summary + description shu belgidan qisqa bo'lsa
    # task qaytariladi va error comment yoziladi.
    min_tz_description_chars: int = 50
    min_tz_description_chars_help: str = (
        "Task summary + description shu belgidan qisqa bo'lsa ikkala servis ham to'xtatiladi: "
        "JIRA'ga error comment yoziladi va task qaytariladi. "
        "50 = bo'sh yoki faqat sarlavha bo'lsa servislar ishlamaydi."
    )

    # ━━━ Skip Code ━━━
    # AI_SKIP tekshirish uchun nechta oxirgi comment ko'riladi
    max_skip_check_comments: int = 5   # DEFAULT 5 ta comment

    # ━━━ AI ga ma'lumotlar tartibi (darajasi) ━━━
    # Sozlamadagi tartib bo'yicha AI promtiga bo'limlar qo'shiladi. Servis SHU tartibga qat'iy amal qiladi.
    # Bo'limlar: tz, comments, figma, code
    ai_data_section_order: List[str] = field(default_factory=lambda: ["tz", "comments", "figma", "code"])

    # ━━━ PR Fayl Cheklovlari ━━━
    # analyze_task() da max fayl soni (full strategiya)
    pr_max_files: int = 3              # DEFAULT: 3 ta fayl ko'rsatiladi
    excluded_file_patterns: str = (
        "package-lock.json,yarn.lock,pnpm-lock.yaml,"
        ".next/*,dist/*,build/*,coverage/*,node_modules/*,vendor/*,"
        "*.min.*,*.map,*.generated.*,*.gen.*,generated/*,__generated__/*"
    )
    # Oxirgi N ta developer comment AI ga yuboriladi
    dev_comments_max: int = 5          # DEFAULT: oxirgi 5 ta comment

    # Yordam matnlari
    ai_data_section_order_help: str = (
        "AI ga ma'lumotlar qaysi tartibda berilishi. Birinchi o'rinda eng ustun. "
        "TZ = texnik topshiriq, comments = developer izohlari, figma = dizayn, code = kod o'zgarishlari. "
        "Sozlamaga AI qat'iy amal qiladi."
    )
    pr_max_files_help: str = (
        "AI ga yuboriladigan maksimal PR fayl soni. "
        "Token tejash uchun - ko'p fayl = ko'p token. 3 tavsiya etiladi."
    )
    excluded_file_patterns_help: str = (
        "AI diff kontekstidan chiqarib tashlanadigan fayl patternlari. "
        "Vergul bilan ajrating: package-lock.json, dist/*, *.min.*"
    )
    dev_comments_max_help: str = (
        "AI ga yuboriladigan oxirgi N ta developer comment soni. "
        "5 = oxirgi 5 ta comment. Ko'p berish token sarfini oshiradi."
    )
    return_threshold_help: str = "Moslik bali shu foizdan past bo'lsa task qaytariladi (0-100)"
    trusted_scope_comment_authors_help: str = (
        "Faqat shu JIRA displayName ro'yxatidagi authorlar comment orqali scope'ni o'zgartira oladi. "
        "Vergul bilan ajrating. Bo'sh qolsa hech bir comment scope'ni o'zgartirmaydi."
    )
    agent1_coverage_threshold_help: str = "Agent1 TZ coverage re-prompt threshold qiymati (0.0-1.0). Default: 1.0 = 100%."
    agent2_extra_scan_enabled: bool = True
    agent2_extra_scan_enabled_help: str = (
        "Agent2 extra scan (TZ da yo'q qo'shimcha kod o'zgarishlarni aniqlash) yoqilganmi. "
        "False = extra scan o'chiriladi, faqat talablar tekshiriladi."
    )
    agent2_parallelism_help: str = (
        "Agent2 per-requirement rejimida bir vaqtda nechta Gemini chaqiruv ishlashi. "
        "1 = sequential, 5 = default."
    )
    agent2_batch_size_help: str = (
        "Agent2 bir Gemini chaqiruvida nechta requirement tekshirishi. "
        "1 = eski per-requirement rejim, 6 = default batch."
    )
    agent1_primary_model_help: str = "Agent1 Scope Builder primary modeli. Bo'sh bo'lsa global default meros olinadi; global ham bo'sh bo'lsa modul ishga tushmaydi."
    agent1_fallback_model_help: str = "Agent1 Scope Builder fallback modeli. Bo'sh bo'lsa global default meros olinadi; global ham bo'sh bo'lsa fallback ishlamaydi."
    agent2_primary_model_help: str = "Agent2 Verifier primary modeli. Bo'sh bo'lsa global default meros olinadi; global ham bo'sh bo'lsa modul ishga tushmaydi."
    agent2_fallback_model_help: str = "Agent2 Verifier fallback modeli. Bo'sh bo'lsa global default meros olinadi; global ham bo'sh bo'lsa fallback ishlamaydi."
    agent3_primary_model_help: str = "Agent3 Arbiter primary modeli. Bo'sh bo'lsa global default meros olinadi; global ham bo'sh bo'lsa modul ishga tushmaydi."
    agent3_fallback_model_help: str = "Agent3 Arbiter fallback modeli. Bo'sh bo'lsa global default meros olinadi; global ham bo'sh bo'lsa fallback ishlamaydi."
    auto_return_help: str = "Moslik past bo'lganda avtomatik Return statusga o'tkazish"
    trigger_status_help: str = "Qaysi statusda TZ-PR tekshirish boshlanadi"
    trigger_aliases_help: str = "Trigger status uchun alternativ nomlar (vergul bilan ajrating)"
    return_status_help: str = "Moslik past bo'lganda qaysi statusga qaytarish"
    use_adf_help: str = "ADF formatda dropdown/collapsible panellar ishlatish"
    show_statistics_help: str = "PR statistikasini comment'da ko'rsatish"
    show_compliance_help: str = "Moslik balini comment'da ko'rsatish"
    tz_pr_footer_help: str = "TZ-PR comment'ning pastki qismida ko'rinadigan matn"
    return_notification_help: str = "Moslik bali past bo'lsa qaytarish notification panelida ko'rinadigan matn"
    skip_code_help: str = "DEV bu kodini comment'ga yozsa AI tekshirish o'chadi. Masalan: AI_SKIP"
    skip_comment_help: str = "Skip code topilganda JIRA ga yoziladigan xabar"
    recheck_comment_help: str = "Task qaytarildigan so'ng yana tekshirilayotgan bo'lganda ko'rinadigan xabar"
    read_comments_help: str = "JIRA task comment'larini AI ga yuborish. O'chirilsa faqat TZ asosida ishlaydi"
    max_comments_help: str = "AI ga yuborilgan comment'lar soni. 0 = barcha comment'lar"
    show_contradictory_comments_help: str = (
        "Legacy flag. Checker final report UI va webhook commentda bir xil canonical section contract orqali render qilinadi."
    )
    visible_sections_help: str = (
        "Checker final report bo'limlari: UI HTML ko'rinishida, webhook esa JIRA comment ko'rinishida bir xil contractni render qiladi."
    )
    max_skip_check_comments_help: str = (
        "AI_SKIP kodi qidirilayotganda JIRA ning oxirgi nechta commenti tekshiriladi. "
        "5 = oxirgi 5 ta comment. Oshirsangiz eski commentlardan ham topadi."
    )

    _AI_DATA_ORDER_ALLOWED = ("tz", "comments", "figma", "code")
    _VISIBLE_SECTIONS_ALLOWED = ("completed", "failed", "skipped", "issues", "figma")

    def __post_init__(self):
        """Sozlamalar validatsiyasi — noto'g'ri qiymatlar exception chiqaradi"""
        if not 0 <= self.return_threshold <= 100:
            raise ValueError(
                f"return_threshold {self.return_threshold}% noto'g'ri: 0-100 oralig'ida bo'lishi kerak"
            )
        if not 0 <= float(self.agent1_coverage_threshold) <= 1:
            raise ValueError(
                f"agent1_coverage_threshold {self.agent1_coverage_threshold} noto'g'ri: 0.0-1.0 oralig'ida bo'lishi kerak"
            )
        if int(self.agent2_parallelism) < 1:
            raise ValueError("agent2_parallelism noto'g'ri: 1 yoki undan katta bo'lishi kerak")
        if int(self.agent2_batch_size) < 1:
            raise ValueError("agent2_batch_size noto'g'ri: 1 yoki undan katta bo'lishi kerak")
        if self.max_skip_check_comments < 1:
            raise ValueError(
                f"max_skip_check_comments {self.max_skip_check_comments} noto'g'ri: 1 dan katta bo'lishi kerak"
            )
        visible_sections = []
        for item in self.visible_sections or []:
            key = str(item or "").strip()
            if key in {"partial", "contradictory_comments"} or not key or key in visible_sections:
                continue
            if key not in self._VISIBLE_SECTIONS_ALLOWED:
                raise ValueError(
                    f"visible_sections noto'g'ri: {key}. Ruxsat: {list(self._VISIBLE_SECTIONS_ALLOWED)}"
                )
            visible_sections.append(key)
        self.visible_sections = visible_sections or ["completed", "failed", "skipped", "issues", "figma"]
        # ai_data_section_order: faqat ruxsat etilgan qiymatlar, takrorlanishsiz
        order = list(dict.fromkeys(self.ai_data_section_order or []))
        invalid = [x for x in order if x not in self._AI_DATA_ORDER_ALLOWED]
        if invalid:
            raise ValueError(
                f"ai_data_section_order noto'g'ri: {invalid}. Ruxsat: {list(self._AI_DATA_ORDER_ALLOWED)}"
            )
        if "tz" not in order or "code" not in order:
            raise ValueError(
                "ai_data_section_order da 'tz' va 'code' bo'lishi shart"
            )
        self.ai_data_section_order = order if order else ["tz", "comments", "figma", "code"]

    def get_trigger_statuses(self) -> List[str]:
        """Barcha trigger statuslarni qaytarish"""
        statuses = [self.trigger_status]
        if self.trigger_status_aliases:
            aliases = [s.strip() for s in self.trigger_status_aliases.split(',')]
            statuses.extend(aliases)
        return list(set(statuses))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTCASE GENERATOR SOZLAMALARI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class TestcaseGeneratorSettings:
    """Testcase Generator modul sozlamalari"""
    # Default qiymatlar
    # Faqat positive va negative test types qoldirildi (boundary va edge olib tashlandi)
    default_test_types: List[str] = field(default_factory=lambda: ['positive', 'negative'])
    # Har requirement uchun target/maksimum test case soni
    testcases_per_requirement: int = 3
    # AI javob uchun maksimal token soni (truncation oldini olish uchun)
    ai_max_output_tokens: int = TESTCASE_MAX_OUTPUT_TOKENS
    agent1_primary_model: str = ""
    agent1_fallback_model: str = ""
    agent2_primary_model: str = ""
    agent2_fallback_model: str = ""
    agent3_primary_model: str = ""
    agent3_fallback_model: str = ""

    # ━━━ AI ga ma'lumotlar tartibi (darajasi) ━━━
    # Sozlamadagi tartib bo'yicha AI promtiga bo'limlar qo'shiladi. Servis SHU tartibga qat'iy amal qiladi.
    # Bo'limlar: tz, comments, custom_context, figma, code
    # "figma" — checker kabi Figma'ni yoqish/o'chirish flagi (ro'yxatda bo'lsa Figma olinadi).
    ai_data_section_order: List[str] = field(default_factory=lambda: ["tz", "comments", "custom_context", "figma", "code"])

    # ━━━ Comment O'qish ━━━
    read_comments_enabled: bool = True
    max_comments_to_read: int = 0  # 0 = barcha

    # JIRA avtomatik comment
    auto_comment_enabled: bool = False
    auto_comment_trigger_status: str = "READY TO TEST"
    auto_comment_trigger_aliases: str = "Ready To Test,READY TO TEST"
    # ADF format (FIXED VALUE - not configurable by design)
    # Always use ADF (Atlassian Document Format) for professional dropdown panels
    use_adf_format: bool = True

    # ━━━ Sozlanadigan Matnlar ━━━
    # Testcase comment footer
    testcase_footer_text: str = (
        "🤖 Test case'lar AI (Gemini) tomonidan avtomatik yaratilgan. "
        "QA Team tomonidan tekshirilishi va to'ldirilishi kerak."
    )

    # Yordam matnlari
    test_types_help: str = "Default test turlari: positive (asosiy), negative (xato holatlari)"
    testcases_per_requirement_help: str = "Har bir talab uchun yoziladigan test case soni (1-3). Default: 3"
    ai_max_output_tokens_help: str = "AI javob uchun maksimal token soni (platform policy bo'yicha boshqariladi)"
    agent1_primary_model_help: str = "Testcase Agent1 Requirements primary modeli. Bo'sh bo'lsa global default meros olinadi; global ham bo'sh bo'lsa modul ishga tushmaydi."
    agent1_fallback_model_help: str = "Testcase Agent1 Requirements fallback modeli. Bo'sh bo'lsa global default meros olinadi; global ham bo'sh bo'lsa fallback ishlamaydi."
    agent2_primary_model_help: str = "Testcase Agent2 Generator primary modeli. Bo'sh bo'lsa global default meros olinadi; global ham bo'sh bo'lsa modul ishga tushmaydi."
    agent2_fallback_model_help: str = "Testcase Agent2 Generator fallback modeli. Bo'sh bo'lsa global default meros olinadi; global ham bo'sh bo'lsa fallback ishlamaydi."
    agent3_primary_model_help: str = "Testcase Agent3 Auditor primary modeli. Bo'sh bo'lsa global default meros olinadi; global ham bo'sh bo'lsa modul ishga tushmaydi."
    agent3_fallback_model_help: str = "Testcase Agent3 Auditor fallback modeli. Bo'sh bo'lsa global default meros olinadi; global ham bo'sh bo'lsa fallback ishlamaydi."
    ai_data_section_order_help: str = (
        "AI ga ma'lumotlar qaysi tartibda berilishi. Birinchi o'rinda eng ustun. "
        "tz = TZ, comments = comment'lar, custom_context = qo'shimcha kontekst, "
        "figma = Figma'ni yoqish (ro'yxatda bo'lsa Figma olinadi), code = kod statistikasi. "
        "Sozlamaga AI qat'iy amal qiladi."
    )
    read_comments_help: str = "JIRA task comment'larini AI ga yuborish. O'chirilsa faqat TZ asosida ishlaydi"
    max_comments_help: str = "AI ga yuborilgan comment'lar soni. 0 = barcha comment'lar"
    auto_comment_help: str = "Task Ready to Test statusga tushganda avtomatik test case yaratib JIRA ga yozish"
    trigger_status_help: str = "Qaysi statusda avtomatik test case yaratish"
    trigger_aliases_help: str = "Trigger status uchun alternativ nomlar"
    use_adf_help: str = "ADF formatda dropdown panellar bilan chiroyli comment yozish"
    testcase_footer_help: str = "Test case comment'ning pastki qismida ko'rinadigan matn"

    _AI_DATA_ORDER_ALLOWED = ("tz", "comments", "custom_context", "figma", "code")

    def __post_init__(self):
        """Sozlamalar validatsiyasi — noto'g'ri qiymatlar exception chiqaradi"""
        try:
            self.testcases_per_requirement = int(self.testcases_per_requirement)
        except (TypeError, ValueError):
            self.testcases_per_requirement = 3
        if self.testcases_per_requirement < 1:
            self.testcases_per_requirement = 1
        if self.testcases_per_requirement > 3:
            self.testcases_per_requirement = 3
        # ai_data_section_order: faqat ruxsat etilgan qiymatlar
        order = list(dict.fromkeys(self.ai_data_section_order or []))
        invalid = [x for x in order if x not in self._AI_DATA_ORDER_ALLOWED]
        if invalid:
            raise ValueError(
                f"ai_data_section_order noto'g'ri: {invalid}. Ruxsat: {list(self._AI_DATA_ORDER_ALLOWED)}"
            )
        if "tz" not in order:
            raise ValueError("ai_data_section_order da 'tz' bo'lishi shart")
        self.ai_data_section_order = order if order else ["tz", "comments", "custom_context", "figma", "code"]

    def get_trigger_statuses(self) -> List[str]:
        """Barcha trigger statuslarni qaytarish"""
        statuses = [self.auto_comment_trigger_status]
        if self.auto_comment_trigger_aliases:
            aliases = [s.strip() for s in self.auto_comment_trigger_aliases.split(',')]
            statuses.extend(aliases)
        return list(set(statuses))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AI QUEUE SOZLAMALARI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class QueueSettings:
    """AI Queue — rate limit himoya sozlamalari"""
    queue_enabled: bool = True
    # Task kutish vaqti (sekunda):
    # Birinci task ishlanmoqda, ikkinchi keldi → ikkinchi qancha kutadi?
    # Timeout etgan → JIRA'ga error comment yoziladi
    task_wait_timeout: int = 60         # DEFAULT 60 sek
    # Legacy no-op: checker → testcase delay olib tashlangan.
    # Eski settings JSON/DB payloadlari buzilmasligi uchun field saqlanadi.
    checker_testcase_delay: int = 0
    # Blocked task qayta ishlash vaqti (daqiqa):
    # AI timeout/429 sabab blocked bo'lgan task necha daqiqadan keyin qayta run
    blocked_retry_delay: int = 5        # DEFAULT 5 daqiqa

    # ━━━ AI va Tizim Sozlamalari ━━━
    # Gemini so'rovlar orasidagi min kutish vaqti (sekund)
    gemini_min_interval: int = 6        # DEFAULT 6 sek (10 req/min = 60/10)
    # Blocked task scheduler tekshirish oraligi (sekund)
    blocked_check_interval: int = 30   # DEFAULT 30 sek
    # API KEY muzlatish muddati — limit xatosida (sekund)
    key_freeze_duration: int = 600     # DEFAULT 600 sek (10 daqiqa)
    # Gemini vaqtinchalik xato (503/overload) bersa, necha marta qayta urinish
    gemini_max_retries: int = 3        # DEFAULT 3 marta
    # Gemini ga yuboriladigan max input token soni
    ai_max_input_tokens: int = AI_MAX_INPUT_TOKENS  # DEFAULT 900K (Gemini 2.5 Flash limit 1M)
    # Token hisoblash koeffitsiyenti (1 token ≈ nechta belgi)
    chars_per_token: int = CHARS_PER_TOKEN           # DEFAULT 4 belgi
    # DB ulanish (pool'dan bo'sh ulanish kutish) timeout (sekund)
    db_connection_timeout: int = 30    # DEFAULT 30 sek
    # GitHub/API so'rov timeout (sekund)
    http_timeout: int = 30             # DEFAULT 30 sek
    # Testcase executor yakunlash timeout (sekund)
    executor_timeout: int = 120        # DEFAULT 120 sek (2 daqiqa)

    # Yordam matnlari (UI'da har sozlama yonida ko'rsatiladi — sodda, misol bilan)
    queue_enabled_help: str = (
        "Bir kompaniyada ko'p task birdan 'Testing'ga tushsa, ularni birma-bir (navbat bilan) "
        "tekshirish. Yoqilgan (tavsiya): Gemini'ni urib qulashdan saqlaydi. O'chirilgan: "
        "hammasi birdan ishlaydi — faqat juda kuchli Gemini kvotasi bo'lsa."
    )
    task_wait_timeout_help: str = (
        "Navbatda turgan task eng ko'p necha SEKUND kutadi. Shu vaqtda ham navbat bo'shamasa, "
        "task 'blocked' bo'ladi va keyinroq avtomatik qayta urinadi (yo'qolmaydi). "
        "Misol: 60 = 1 daqiqa kutadi."
    )
    checker_testcase_delay_help: str = (
        "Legacy/no-op: checker → testcase delay olib tashlangan. Gemini chaqiriqlari orasidagi "
        "tanaffusni `gemini_min_interval` boshqaradi."
    )
    blocked_retry_delay_help: str = (
        "Gemini band bo'lib (timeout yoki 429 kvota) bloklangan task necha DAQIQAdan keyin qayta urinadi. "
        "Misol: 5 = 5 daqiqadan keyin yana sinab ko'radi."
    )
    gemini_min_interval_help: str = (
        "Gemini'ga ketma-ket so'rovlar orasida eng kam necha SEKUND tanaffus. "
        "Google bepul limiti: 10 so'rov/daqiqa = har 6 soniyada 1 ta. "
        "Tez-tez '429 limit' ko'rsangiz bu qiymatni oshiring."
    )
    blocked_check_interval_help: str = (
        "Bloklangan tasklarni qayta urinish uchun tizim har necha SEKUNDda tekshirib turadi. "
        "Kichik = tezroq qayta urinadi (DB'ga ko'proq yuk); katta = kamroq tekshiradi."
    )
    key_freeze_duration_help: str = (
        "Bir Gemini kaliti '429 kvota' xatosi bersa, o'sha kalit necha SEKUNDga 'dam oladi' (muzlatiladi). "
        "Shu vaqt ichida boshqa kalit ishlatiladi. Misol: 600 = 10 daqiqa."
    )
    gemini_max_retries_help: str = (
        "Gemini vaqtincha band bo'lsa (503/overload), so'rov necha MARTA qayta urinadi "
        "(har urinish orasida ko'payib boruvchi tanaffus: 5s → 10s → 20s). Misol: 3 = 3 marta sinaydi."
    )
    ai_max_input_tokens_help: str = (
        "Gemini'ga yuboriladigan matn (TZ + PR) eng ko'p necha TOKEN bo'lishi mumkin. "
        "Gemini 2.5 limiti ~1M token. Juda katta TZ/PR kesilmasligi uchun oshirish mumkin."
    )
    chars_per_token_help: str = (
        "Matn uzunligini token soniga taxminan o'girish koeffitsiyenti (1 token ≈ shuncha belgi). "
        "Odatda 4. Faqat token hisobini aniqlashtirish uchun."
    )
    db_connection_timeout_help: str = (
        "Bazaga ulanish (pool'dan bo'sh ulanish) olishda eng ko'p necha SEKUND kutiladi. "
        "Hammasi band bo'lsa shuncha kutib, bo'lmasa xato beradi. Odatda 30 yetarli."
    )
    http_timeout_help: str = (
        "Tashqi xizmatlarga (GitHub, JIRA, Figma) HTTP so'rovlar uchun timeout (SEKUND). "
        "Sekin internet yoki katta repository/fayl bo'lsa oshiring. Odatda 30 yetarli."
    )
    executor_timeout_help: str = (
        "Testcase yaratish jarayoni eng ko'p necha SEKUND ishlashi mumkin. "
        "Katta task va sekin AI javobida oshiring. Misol: 120 = 2 daqiqa."
    )

    def __post_init__(self):
        """Sozlamalar validatsiyasi — noto'g'ri qiymatlar exception chiqaradi"""
        if self.task_wait_timeout <= 0:
            raise ValueError(
                f"task_wait_timeout {self.task_wait_timeout}s noto'g'ri: 0 dan katta bo'lishi kerak"
            )
        if self.blocked_retry_delay <= 0:
            raise ValueError(
                f"blocked_retry_delay {self.blocked_retry_delay} daqiqa noto'g'ri: 0 dan katta bo'lishi kerak"
            )
        if self.gemini_min_interval <= 0:
            raise ValueError(
                f"gemini_min_interval {self.gemini_min_interval}s noto'g'ri: 0 dan katta bo'lishi kerak"
            )
        if self.key_freeze_duration <= 0:
            raise ValueError(
                f"key_freeze_duration {self.key_freeze_duration}s noto'g'ri: 0 dan katta bo'lishi kerak"
            )
        if self.gemini_max_retries <= 0:
            raise ValueError(
                f"gemini_max_retries {self.gemini_max_retries} noto'g'ri: 0 dan katta bo'lishi kerak"
            )
        if not 0 < self.ai_max_input_tokens <= 2_000_000:
            raise ValueError(
                f"ai_max_input_tokens {self.ai_max_input_tokens} noto'g'ri: 1-2,000,000 oralig'ida bo'lishi kerak"
            )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# YAGONA SOZLAMALAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class AppSettings:
    """Yagona tizim sozlamalari"""
    modules: ModuleVisibility = field(default_factory=ModuleVisibility)
    bug_analyzer: BugAnalyzerSettings = field(default_factory=BugAnalyzerSettings)
    statistics: StatisticsSettings = field(default_factory=StatisticsSettings)
    tz_pr_checker: TZPRCheckerSettings = field(default_factory=TZPRCheckerSettings)
    # Webhook orqali TZ-PR tekshiruvi uchun alohida sozlamalar.
    # tz_pr_checker — standalone modul (alohida sotiladi), webhook_tz_pr — webhook trigger (alohida sotiladi).
    webhook_tz_pr: TZPRCheckerSettings = field(default_factory=TZPRCheckerSettings)
    testcase_generator: TestcaseGeneratorSettings = field(default_factory=TestcaseGeneratorSettings)
    # Webhook orqali avtomatik test case yaratish uchun alohida sozlamalar.
    # testcase_generator — QA moduli (manual), webhook_testcase — webhook auto-comment.
    webhook_testcase: TestcaseGeneratorSettings = field(default_factory=TestcaseGeneratorSettings)
    queue: QueueSettings = field(default_factory=QueueSettings)


def _enforce_token_policy(settings: AppSettings) -> AppSettings:
    """Platform token policy ni AppSettings obyektiga majburan qo'llash."""
    settings.tz_pr_checker.ai_max_output_tokens = CHECKER_MAX_OUTPUT_TOKENS
    settings.webhook_tz_pr.ai_max_output_tokens = CHECKER_MAX_OUTPUT_TOKENS
    settings.testcase_generator.ai_max_output_tokens = TESTCASE_MAX_OUTPUT_TOKENS
    settings.webhook_testcase.ai_max_output_tokens = TESTCASE_MAX_OUTPUT_TOKENS
    settings.queue.ai_max_input_tokens = AI_MAX_INPUT_TOKENS
    settings.queue.chars_per_token = CHARS_PER_TOKEN
    return settings


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SOZLAMALAR MANAGER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AppSettingsManager:
    """Sozlamalarni boshqarish - Singleton pattern"""

    _instance: Optional['AppSettingsManager'] = None
    _settings: Optional[AppSettings] = None

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize - faqat birinchi marta"""
        if self._settings is None:
            self._migrate_old_settings()
            self._settings = self._load_settings()

    def _ensure_data_dir(self):
        """Data papkasini yaratish"""
        data_dir = os.path.dirname(SETTINGS_FILE)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

    def _migrate_old_settings(self):
        """Eski TZ-PR sozlamalarini yangi formatga o'tkazish"""
        if os.path.exists(OLD_SETTINGS_FILE) and not os.path.exists(SETTINGS_FILE):
            try:
                with open(OLD_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)

                # Yangi sozlamalar yaratish
                new_settings = AppSettings()

                # TZ-PR sozlamalarini o'tkazish
                if 'return_threshold' in old_data:
                    new_settings.tz_pr_checker.return_threshold = old_data['return_threshold']
                if 'auto_return_enabled' in old_data:
                    new_settings.tz_pr_checker.auto_return_enabled = old_data['auto_return_enabled']
                if 'trigger_status' in old_data:
                    new_settings.tz_pr_checker.trigger_status = old_data['trigger_status']
                if 'trigger_status_aliases' in old_data:
                    new_settings.tz_pr_checker.trigger_status_aliases = old_data['trigger_status_aliases']
                if 'return_status' in old_data:
                    new_settings.tz_pr_checker.return_status = old_data['return_status']
                if 'use_adf_format' in old_data:
                    new_settings.tz_pr_checker.use_adf_format = old_data['use_adf_format']
                if 'show_statistics' in old_data:
                    new_settings.tz_pr_checker.show_statistics = old_data['show_statistics']
                if 'show_compliance_score' in old_data:
                    new_settings.tz_pr_checker.show_compliance_score = old_data['show_compliance_score']

                # Yangi formatda saqlash
                self._settings = new_settings
                self.save_settings(new_settings)
                log.info("Settings migration completed successfully")

            except Exception as e:
                log.warning(f"Settings migration failed: {e}")

    def _load_settings(self) -> AppSettings:
        """Sozlamalarni fayldan yuklash"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Eski comment_reading dan migratsiya
                old_comment = data.pop('comment_reading', None)
                if old_comment:
                    # Eski comment sozlamalarini har bir modulga ko'chirish
                    tz_data = data.get('tz_pr_checker', {})
                    tc_data = data.get('testcase_generator', {})
                    if 'read_comments_enabled' not in tz_data:
                        tz_data['read_comments_enabled'] = old_comment.get('read_comments_enabled', True)
                        tz_data['max_comments_to_read'] = old_comment.get('max_comments_to_read', 0)
                        data['tz_pr_checker'] = tz_data
                    if 'read_comments_enabled' not in tc_data:
                        tc_data['read_comments_enabled'] = old_comment.get('read_comments_enabled', True)
                        tc_data['max_comments_to_read'] = old_comment.get('max_comments_to_read', 0)
                        data['testcase_generator'] = tc_data
                    log.info("Comment reading settings migrated to modules")

                # min_tz_description_chars migratsiyasi: testcase_generator → tz_pr_checker
                tc_data = data.get('testcase_generator', {})
                if 'min_tz_description_chars' in tc_data:
                    tz_data = data.get('tz_pr_checker', {})
                    if 'min_tz_description_chars' not in tz_data:
                        tz_data['min_tz_description_chars'] = tc_data.pop('min_tz_description_chars')
                        data['tz_pr_checker'] = tz_data
                    else:
                        tc_data.pop('min_tz_description_chars')
                    data['testcase_generator'] = tc_data
                    log.info("min_tz_description_chars testcase_generator → tz_pr_checker ga ko'chirildi")

                for checker_key in ('tz_pr_checker', 'webhook_tz_pr'):
                    checker_data = data.get(checker_key, {})
                    if isinstance(checker_data, dict):
                        checker_data.pop('agent1_figma_scope_enabled', None)
                        checker_data.pop('checker_execution_mode', None)
                        data[checker_key] = checker_data

                # Eski settings fayllarida webhook_* bo'limlari yo'q edi.
                # Bunday holatda eski xulq saqlanishi uchun webhook sozlamalari
                # standalone modul sozlamalaridan boshlang'ich qiymat oladi.
                if 'webhook_tz_pr' not in data:
                    data['webhook_tz_pr'] = dict(data.get('tz_pr_checker', {}))
                if 'webhook_testcase' not in data:
                    data['webhook_testcase'] = dict(data.get('testcase_generator', {}))

                testcase_legacy_keys = (
                    'max_test_cases',
                    'default_include_pr',
                    'default_include_comments',
                    'default_include_code',
                    'default_include_figma',
                )
                for testcase_key in ('testcase_generator', 'webhook_testcase'):
                    testcase_data = data.get(testcase_key, {})
                    if isinstance(testcase_data, dict):
                        for legacy_key in testcase_legacy_keys:
                            testcase_data.pop(legacy_key, None)
                        data[testcase_key] = testcase_data

                # Saqlangan dict'da olib tashlangan/eski kalitlar bo'lishi mumkin
                # (masalan eski ai_max_retries/db_busy_timeout). Faqat dataclass tan
                # oladigan maydonlarni o'tkazamiz — aks holda butun blok default'ga tushadi.
                def _kw(cls, key):
                    raw = data.get(key, {})
                    if not isinstance(raw, dict):
                        return {}
                    valid = set(cls.__dataclass_fields__)
                    return {k: v for k, v in raw.items() if k in valid}

                # Nested dataclass'larni yaratish
                settings = AppSettings(
                    modules=ModuleVisibility(**_kw(ModuleVisibility, 'modules')),
                    bug_analyzer=BugAnalyzerSettings(**_kw(BugAnalyzerSettings, 'bug_analyzer')),
                    statistics=StatisticsSettings(**_kw(StatisticsSettings, 'statistics')),
                    tz_pr_checker=TZPRCheckerSettings(**_kw(TZPRCheckerSettings, 'tz_pr_checker')),
                    webhook_tz_pr=TZPRCheckerSettings(**_kw(TZPRCheckerSettings, 'webhook_tz_pr')),
                    testcase_generator=TestcaseGeneratorSettings(**_kw(TestcaseGeneratorSettings, 'testcase_generator')),
                    webhook_testcase=TestcaseGeneratorSettings(**_kw(TestcaseGeneratorSettings, 'webhook_testcase')),
                    queue=QueueSettings(**_kw(QueueSettings, 'queue')),
                )

                return _enforce_token_policy(settings)
            else:
                return _enforce_token_policy(AppSettings())
        except Exception as e:
            log.warning(f"Failed to load settings: {e}, using defaults")
            return _enforce_token_policy(AppSettings())

    def _settings_to_dict(self, settings: AppSettings) -> dict:
        """Settings'ni dictionary'ga o'tkazish (help matnlarsiz)"""
        def clean_dict(d: dict) -> dict:
            """Help matnlarini olib tashlash"""
            return {k: v for k, v in d.items() if not k.endswith('_help')}

        return {
            'modules': clean_dict(asdict(settings.modules)),
            'bug_analyzer': clean_dict(asdict(settings.bug_analyzer)),
            'statistics': clean_dict(asdict(settings.statistics)),
            'tz_pr_checker': clean_dict(asdict(settings.tz_pr_checker)),
            'webhook_tz_pr': clean_dict(asdict(settings.webhook_tz_pr)),
            'testcase_generator': clean_dict(asdict(settings.testcase_generator)),
            'webhook_testcase': clean_dict(asdict(settings.webhook_testcase)),
            'queue': clean_dict(asdict(settings.queue))
        }

    def save_settings(self, settings: AppSettings) -> bool:
        """Sozlamalarni faylga saqlash"""
        try:
            self._ensure_data_dir()

            # Help matnlarsiz saqlash
            data = self._settings_to_dict(settings)

            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Cache'ni yangilash (yoki tozalash - har safar fayldan o'qish uchun)
            self._settings = settings
            log.info("Settings saved successfully")
            return True
        except Exception as e:
            log.error(f"Failed to save settings: {e}")
            return False

    def get_settings(self, force_reload: bool = False) -> AppSettings:
        """Joriy sozlamalarni olish
        
        Args:
            force_reload: Agar True bo'lsa, cache'ni tozalab fayldan o'qiydi
        """
        if force_reload or self._settings is None:
            self._settings = self._load_settings()
        return self._settings
    
    def reload_settings(self) -> AppSettings:
        """Sozlamalarni qayta yuklash (cache'ni tozalash)"""
        self._settings = None
        return self._load_settings()

    def is_module_enabled(self, module_name: str) -> bool:
        """Modul yoqilganligini tekshirish"""
        settings = self.get_settings()
        module_map = {
            'bug_analyzer': settings.modules.bug_analyzer_enabled,
            'statistics': settings.modules.statistics_enabled,
            'tz_pr_checker': settings.modules.tz_pr_checker_enabled,
            'testcase_generator': settings.modules.testcase_generator_enabled
        }
        return module_map.get(module_name, False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GLOBAL FUNKSIYALAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_settings_manager: Optional[AppSettingsManager] = None

_CHECKER_AGENT_MODEL_DEFAULTS = {
    "agent1_primary_model": "",
    "agent1_fallback_model": "",
    "agent2_primary_model": "",
    "agent2_fallback_model": "",
    "agent3_primary_model": "",
    "agent3_fallback_model": "",
}

_CHECKER_AGENT_MODEL_GLOBAL_KEYS = {
    field_name: f"checker_{field_name}"
    for field_name in _CHECKER_AGENT_MODEL_DEFAULTS
}

_TESTCASE_AGENT_MODEL_DEFAULTS = {
    "agent1_primary_model": "",
    "agent1_fallback_model": "",
    "agent2_primary_model": "",
    "agent2_fallback_model": "",
    "agent3_primary_model": "",
    "agent3_fallback_model": "",
}

_TESTCASE_AGENT_MODEL_GLOBAL_KEYS = {
    field_name: f"testcase_{field_name}"
    for field_name in _TESTCASE_AGENT_MODEL_DEFAULTS
}

_AGENT_MODEL_OVERRIDE_FIELDS = set(_CHECKER_AGENT_MODEL_DEFAULTS) | set(_TESTCASE_AGENT_MODEL_DEFAULTS)
_QUEUE_COMPANY_OVERRIDE_FIELDS = set()


def _company_queue_overrides(raw_queue: dict) -> dict:
    if not isinstance(raw_queue, dict):
        return {}
    return {key: value for key, value in raw_queue.items() if key in _QUEUE_COMPANY_OVERRIDE_FIELDS}


def _parse_positive_int_or_default(raw: str, default: int) -> int:
    try:
        value = int(str(raw).strip())
        return value if value > 0 else default
    except Exception:
        return default


def _apply_global_queue_overrides(settings: AppSettings) -> AppSettings:
    """
    Platform-level (super admin) queue override qiymatlarini qo'llash.

    Bu override'lar global_setting jadvalidan o'qiladi va platform queue
    fieldlari uchun company override'larini chetlab o'tadi.
    """
    try:
        from utils.auth.auth_db import get_global_setting
    except Exception:
        return settings

    current = settings.queue
    queue_overrides = {
        "queue_enabled": True,
        "task_wait_timeout": _parse_positive_int_or_default(
            get_global_setting("queue_task_wait_timeout_sec", str(current.task_wait_timeout)),
            current.task_wait_timeout,
        ),
        "blocked_retry_delay": _parse_positive_int_or_default(
            get_global_setting("queue_blocked_retry_delay_min", str(current.blocked_retry_delay)),
            current.blocked_retry_delay,
        ),
        "gemini_min_interval": _parse_positive_int_or_default(
            get_global_setting("queue_gemini_min_interval_sec", str(current.gemini_min_interval)),
            current.gemini_min_interval,
        ),
        "blocked_check_interval": _parse_positive_int_or_default(
            get_global_setting("queue_blocked_check_interval_sec", str(current.blocked_check_interval)),
            current.blocked_check_interval,
        ),
        "gemini_max_retries": _parse_positive_int_or_default(
            get_global_setting("queue_gemini_max_retries", str(current.gemini_max_retries)),
            current.gemini_max_retries,
        ),
        "key_freeze_duration": _parse_positive_int_or_default(
            get_global_setting("queue_key_freeze_duration_sec", str(current.key_freeze_duration)),
            current.key_freeze_duration,
        ),
        "db_connection_timeout": _parse_positive_int_or_default(
            get_global_setting("queue_db_connection_timeout_sec", str(current.db_connection_timeout)),
            current.db_connection_timeout,
        ),
        "http_timeout": _parse_positive_int_or_default(
            get_global_setting("queue_http_timeout_sec", str(current.http_timeout)),
            current.http_timeout,
        ),
        "executor_timeout": _parse_positive_int_or_default(
            get_global_setting("queue_executor_timeout_sec", str(current.executor_timeout)),
            current.executor_timeout,
        ),
    }

    settings.queue = dc_replace(current, **queue_overrides)
    return settings


def _apply_global_checker_overrides(settings: AppSettings) -> AppSettings:
    """
    Platform-level (super admin) TZ-PR agent model defaultlarini qo'llash.

    Company/user settings bo'sh string qoldirsa, bu global qiymatlar meros bo'lib
    ishlaydi. Global qiymat ham bo'sh bo'lsa hardcoded modelga tushilmaydi.
    Yangi Gemini model nomlari kod validatsiyasisiz saqlanishi mumkin.
    """
    try:
        from utils.auth.auth_db import get_global_setting
    except Exception:
        return settings

    overrides: dict[str, str] = {}
    for field_name, setting_key in _CHECKER_AGENT_MODEL_GLOBAL_KEYS.items():
        default_value = _CHECKER_AGENT_MODEL_DEFAULTS[field_name]
        overrides[field_name] = str(get_global_setting(setting_key, default_value) or "").strip()

    settings.tz_pr_checker = dc_replace(settings.tz_pr_checker, **overrides)
    settings.webhook_tz_pr = dc_replace(settings.webhook_tz_pr, **overrides)
    return settings


def _apply_global_testcase_overrides(settings: AppSettings) -> AppSettings:
    """
    Platform-level (super admin) Testcase agent model defaultlarini qo'llash.

    Company/user settings bo'sh string qoldirsa, bu global qiymatlar meros bo'lib
    ishlaydi. Global qiymat ham bo'sh bo'lsa hardcoded modelga tushilmaydi.
    Checker kabi model nomlari kod validatsiyasisiz saqlanadi.
    """
    try:
        from utils.auth.auth_db import get_global_setting
    except Exception:
        return settings

    overrides: dict[str, str] = {}
    for field_name, setting_key in _TESTCASE_AGENT_MODEL_GLOBAL_KEYS.items():
        default_value = _TESTCASE_AGENT_MODEL_DEFAULTS[field_name]
        overrides[field_name] = str(get_global_setting(setting_key, default_value) or "").strip()

    settings.testcase_generator = dc_replace(settings.testcase_generator, **overrides)
    settings.webhook_testcase = dc_replace(settings.webhook_testcase, **overrides)
    return settings


def get_app_settings(force_reload: bool = False) -> AppSettings:
    """Tizim sozlamalarini olish (global funksiya)
    
    Args:
        force_reload: Agar True bo'lsa, cache'ni tozalab fayldan o'qiydi.
                     Webhook service uchun har safar fayldan o'qish uchun True qiling.
    """
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = AppSettingsManager()
    settings = _settings_manager.get_settings(force_reload=force_reload)
    return _apply_global_testcase_overrides(_apply_global_checker_overrides(_apply_global_queue_overrides(settings)))


def save_app_settings(settings: AppSettings) -> bool:
    """Tizim sozlamalarini saqlash (global funksiya)"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = AppSettingsManager()
    return _settings_manager.save_settings(settings)


def get_settings_manager() -> AppSettingsManager:
    """Settings manager instance olish"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = AppSettingsManager()
    return _settings_manager


def is_module_enabled(module_name: str) -> bool:
    """Modul yoqilganligini tekshirish (global funksiya)"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = AppSettingsManager()
    return _settings_manager.is_module_enabled(module_name)


def get_app_settings_for_company(company_id: int) -> AppSettings:
    """
    Kompaniyaga xos AppSettings olish.

    Ishlash tartibi:
    1. Global default sozlamalar yuklanadi (app_settings.json)
    2. DB dan kompaniyaning module_settings JSON o'qiladi
    3. Kompaniya sozlamalari global default ustiga yoziladi (queue platform fieldlari bundan mustasno)
    4. AppSettings qaytariladi

    Agar kompaniyada modul sozlamalari bo'lmasa — global default qaytariladi.
    """
    from dataclasses import replace as dc_replace, fields as dc_fields

    base = get_app_settings(force_reload=False)

    try:
        from utils.auth.auth_db import get_company_webhook_module_settings
        company_wh = get_company_webhook_module_settings(company_id)
    except Exception:
        return base

    if not company_wh:
        return base

    def _merge(base_obj, override_dict: dict):
        if not override_dict:
            return base_obj
        known = {f.name for f in dc_fields(base_obj)}
        clean = {
            k: v
            for k, v in override_dict.items()
            if (
                k in known
                and not k.endswith('_help')
                and not k.startswith('_')
                and not (k in _AGENT_MODEL_OVERRIDE_FIELDS and str(v or "").strip() == "")
            )
        }
        if not clean:
            return base_obj
        try:
            return dc_replace(base_obj, **clean)
        except Exception:
            return base_obj

    merged_webhook_tz_pr = _merge(base.webhook_tz_pr, company_wh.get('webhook_tz_pr', {}))
    merged_webhook_tz_pr.use_adf_format = True
    merged_webhook_testcase = _merge(base.webhook_testcase, company_wh.get('webhook_testcase', {}))
    merged_webhook_testcase.use_adf_format = True

    settings = AppSettings(
        modules=base.modules,
        bug_analyzer=base.bug_analyzer,
        statistics=base.statistics,
        tz_pr_checker=base.tz_pr_checker,
        webhook_tz_pr=merged_webhook_tz_pr,
        testcase_generator=base.testcase_generator,
        webhook_testcase=merged_webhook_testcase,
        queue=_merge(base.queue,                       _company_queue_overrides(company_wh.get('queue', {}))),
    )
    return _enforce_token_policy(settings)


def get_app_settings_for_user(user_id: int, company_id: int) -> AppSettings:
    """
    User uchun AppSettings olish (multi-tenant).

    Ishlash tartibi:
    - Standalone modullar (tz_pr_checker, testcase_generator, bug_analyzer, statistics)
      → user_module_settings DB dan (har user izolyatsiyalangan)
    - Webhook modullar (webhook_tz_pr, webhook_testcase, queue tenant fieldlari)
      → company_settings.webhook_module_settings DB dan (kompaniya uchun umumiy)
    - Modul ko'rinishi → company enabled_modules dan
    - Agar DB da topilmasa → global default (app_settings.json) ishlatiladi
    """
    from dataclasses import replace as dc_replace, fields as dc_fields

    base = get_app_settings(force_reload=False)

    def _merge(base_obj, override_dict: dict):
        if not override_dict:
            return base_obj
        known = {f.name for f in dc_fields(base_obj)}
        clean = {
            k: v
            for k, v in override_dict.items()
            if (
                k in known
                and not k.endswith('_help')
                and not k.startswith('_')
                and not (k in _AGENT_MODEL_OVERRIDE_FIELDS and str(v or "").strip() == "")
            )
        }
        if not clean:
            return base_obj
        try:
            return dc_replace(base_obj, **clean)
        except Exception:
            return base_obj

    try:
        from utils.auth.auth_db import (
            get_user_module_settings,
            get_company_webhook_module_settings,
        )
        user_mods    = get_user_module_settings(user_id)
        company_wh   = get_company_webhook_module_settings(company_id)
    except Exception:
        return base

    merged_webhook_tz_pr = _merge(base.webhook_tz_pr, company_wh.get('webhook_tz_pr', {}))
    merged_webhook_tz_pr.use_adf_format = True
    merged_webhook_testcase = _merge(base.webhook_testcase, company_wh.get('webhook_testcase', {}))
    merged_webhook_testcase.use_adf_format = True

    settings = AppSettings(
        modules=base.modules,
        bug_analyzer=_merge(base.bug_analyzer,            user_mods.get('bug_analyzer', {})),
        statistics=_merge(base.statistics,                user_mods.get('statistics', {})),
        tz_pr_checker=_merge(base.tz_pr_checker,          user_mods.get('tz_pr_checker', {})),
        webhook_tz_pr=merged_webhook_tz_pr,
        testcase_generator=_merge(base.testcase_generator, user_mods.get('testcase_generator', {})),
        webhook_testcase=merged_webhook_testcase,
        queue=_merge(base.queue,                          _company_queue_overrides(company_wh.get('queue', {}))),
    )
    return _enforce_token_policy(settings)
