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
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from core.logger import get_logger

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
    # Threshold Sozlamalari
    return_threshold: int = 60
    auto_return_enabled: bool = False

    # AI Token Sozlamalari
    ai_max_output_tokens: int = 16384  # Gemini javob uchun max token

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

    # ━━━ Comment Tartib ━━━
    # JIRA ga comment yozilish tartibini nazorat qilish
    comment_order: str = "checker_first"  # "checker_first" | "testcase_first" | "parallel"

    # ━━━ Zid Commentlar ━━━
    # Zid commentlar panelini JIRA comment'da ko'rsatish
    show_contradictory_comments: bool = True

    # ━━━ Comment Bo'limlarini Ko'rsatish ━━━
    # Faqat bu ro'yxatdagi bo'limlar JIRA comment'ga yoziladigan (token tejash)
    visible_sections: List[str] = field(default_factory=lambda: [
        'completed', 'partial', 'failed', 'issues', 'figma'
    ])

    # ━━━ Skip Code ━━━
    # AI_SKIP tekshirish uchun nechta oxirgi comment ko'riladi
    max_skip_check_comments: int = 5   # DEFAULT 5 ta comment

    # Yordam matnlari
    return_threshold_help: str = "Moslik bali shu foizdan past bo'lsa task qaytariladi (0-100)"
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
    comment_order_help: str = (
        "JIRA ga comment yozilish tartibini nazorat qilish. "
        "'checker_first' — TZ-PR tahlil birinchi, test case ikkinchi. "
        "'testcase_first' — test case birinchi, TZ-PR tahlil ikkinchi. "
        "'parallel' — ikkala servis parallel ishlaydi (tezroq)."
    )
    show_contradictory_comments_help: str = "Zid commentlar (TZ ni o'zgartiruvchi) panelini JIRA comment'da ko'rsatish"
    visible_sections_help: str = (
        "JIRA comment'ga yoziladigan bo'limlar. "
        "O'chirilgan bo'limlar comment'ga kiritmaydi (token tejash)."
    )
    max_skip_check_comments_help: str = (
        "AI_SKIP kodi qidirilayotganda JIRA ning oxirgi nechta commenti tekshiriladi. "
        "5 = oxirgi 5 ta comment. Oshirsangiz eski commentlardan ham topadi."
    )

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
    default_include_pr: bool = True
    default_use_smart_patch: bool = True
    # Faqat positive va negative test types qoldirildi (boundary va edge olib tashlandi)
    default_test_types: List[str] = field(default_factory=lambda: ['positive', 'negative'])
    # AI yaratadigan maksimal test case soni
    max_test_cases: int = 10
    # AI javob uchun maksimal token soni (truncation oldini olish uchun)
    ai_max_output_tokens: int = 16384

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
    include_pr_help: str = "GitHub PR kod o'zgarishlarini test case yaratishda hisobga olish"
    smart_patch_help: str = "Faqat o'zgargan qismlarni AI ga yuborish (tezroq va arzonroq)"
    test_types_help: str = "Default test turlari: positive (asosiy), negative (xato holatlari)"
    max_test_cases_help: str = "AI yaratadigan maksimal test case soni (1-30)"
    ai_max_output_tokens_help: str = "AI javob uchun maksimal token soni (16384 tavsiya etiladi)"
    read_comments_help: str = "JIRA task comment'larini AI ga yuborish. O'chirilsa faqat TZ asosida ishlaydi"
    max_comments_help: str = "AI ga yuborilgan comment'lar soni. 0 = barcha comment'lar"
    auto_comment_help: str = "Task Ready to Test statusga tushganda avtomatik test case yaratib JIRA ga yozish"
    trigger_status_help: str = "Qaysi statusda avtomatik test case yaratish"
    trigger_aliases_help: str = "Trigger status uchun alternativ nomlar"
    use_adf_help: str = "ADF formatda dropdown panellar bilan chiroyli comment yozish"
    testcase_footer_help: str = "Test case comment'ning pastki qismida ko'rinadigan matn"

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
    # Checker → Testcase delay (sekunda):
    # Bitta task ichida checker comment yozgandan so'ng testcasegacha kutish
    checker_testcase_delay: int = 15    # DEFAULT 15 sek
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
    # AI so'rov muvaffaqiyatsiz bo'lsa qayta urinish limiti
    ai_max_retries: int = 3            # DEFAULT 3 marta
    # Gemini ga yuboriladigan max input token soni
    ai_max_input_tokens: int = 900000  # DEFAULT 900K (Gemini 2.5 Flash limit 1M)
    # Token hisoblash koeffitsiyenti (1 token ≈ nechta belgi)
    chars_per_token: int = 4           # DEFAULT 4 belgi
    # SQLite bloklanganda kutish (millisekund)
    db_busy_timeout: int = 30000       # DEFAULT 30000 ms (30 sek)
    # SQLite ulanish timeout (sekund)
    db_connection_timeout: int = 30    # DEFAULT 30 sek
    # GitHub/API so'rov timeout (sekund)
    http_timeout: int = 30             # DEFAULT 30 sek
    # Testcase executor yakunlash timeout (sekund)
    executor_timeout: int = 120        # DEFAULT 120 sek (2 daqiqa)

    # Yordam matnlari
    queue_enabled_help: str = "Ko'p task birdan kelgan bo'lsa queue ile birma-bir tekshirish (AI rate limit himoya)"
    task_wait_timeout_help: str = (
        "Birinci task ishlanmoqda, ikkinchi keldi — ikkinchi qancha sekunda kutadi? "
        "Timeout etgan bo'lsa JIRA'ga error comment yoziladi va task manual tekshirishga qoladi."
    )
    checker_testcase_delay_help: str = (
        "Bitta task ichida checker comment yozgandan so'ng, testcase commentgacha "
        "qancha sekunda kutiladi? Bu AI rate limit'dan himoya qiladi."
    )
    blocked_retry_delay_help: str = (
        "AI timeout yoki 429 limit sabab blocked bo'lgan task necha daqiqadan keyin "
        "qayta ishga tushiriladi. Masalan: 5 daqiqa = 5 daqiqadan keyin qayta urinadi."
    )
    gemini_min_interval_help: str = (
        "Gemini AI ga ketma-ket so'rov yuborishda min kutish vaqti (sekund). "
        "Google rate limit: 10 so'rov/daqiqa = 6 sekund. "
        "Agar limitga tushsangiz bu qiymatni oshiring."
    )
    blocked_check_interval_help: str = (
        "Blocked bo'lgan tasklar uchun scheduler har necha sekundda DB ni tekshiradi. "
        "Kichik qiymat — tezroq retry, katta qiymat — kamroq DB yuklanma."
    )
    key_freeze_duration_help: str = (
        "Gemini API KEY_1 limit xatosi bo'lganda, KEY_1 necha sekundga muzlatiladi. "
        "Bu vaqt ichida faqat KEY_2 ishlatiladi. Muddat tugagach KEY_1 ga qaytiladi."
    )
    ai_max_retries_help: str = (
        "AI so'rov muvaffaqiyatsiz bo'lganda necha marta qayta urinish. "
        "Har bir urinish orasida kutish bo'ladi."
    )
    ai_max_input_tokens_help: str = (
        "Gemini AI ga yuboriladigan max input token soni. "
        "Gemini 2.5 Flash limiti 1M token. 900000 xavfsiz chegaradir. "
        "Katta TZ+PR lar uchun oshirish mumkin."
    )
    chars_per_token_help: str = (
        "Token hisoblash koeffitsiyenti — 1 token taxminan nechta belgiga teng. "
        "4 standart qiymat. O'zgartirish tavsiya etilmaydi."
    )
    db_busy_timeout_help: str = (
        "SQLite boshqa jarayon tomonidan bloklanganda qancha vaqt kutadi (millisekund). "
        "30000 = 30 sekund. Concurrent access muammosi bo'lsa oshiring."
    )
    db_connection_timeout_help: str = (
        "SQLite ga ulanish ochish timeout (sekund). "
        "Normal sharoitda 30 sekund yetarli."
    )
    http_timeout_help: str = (
        "GitHub API va boshqa HTTP so'rovlar uchun timeout (sekund). "
        "Sekin internet yoki katta repository bo'lsa oshiring."
    )
    executor_timeout_help: str = (
        "Testcase generation executor yakunlash timeout (sekund). "
        "Katta task bo'lsa va AI javob sekin bo'lsa oshiring. 120 = 2 daqiqa."
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
    testcase_generator: TestcaseGeneratorSettings = field(default_factory=TestcaseGeneratorSettings)
    queue: QueueSettings = field(default_factory=QueueSettings)


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

                # Nested dataclass'larni yaratish
                settings = AppSettings(
                    modules=ModuleVisibility(**data.get('modules', {})),
                    bug_analyzer=BugAnalyzerSettings(**data.get('bug_analyzer', {})),
                    statistics=StatisticsSettings(**data.get('statistics', {})),
                    tz_pr_checker=TZPRCheckerSettings(**data.get('tz_pr_checker', {})),
                    testcase_generator=TestcaseGeneratorSettings(**data.get('testcase_generator', {})),
                    queue=QueueSettings(**data.get('queue', {}))
                )

                return settings
            else:
                return AppSettings()
        except Exception as e:
            log.warning(f"Failed to load settings: {e}, using defaults")
            return AppSettings()

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
            'testcase_generator': clean_dict(asdict(settings.testcase_generator)),
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


def get_app_settings(force_reload: bool = False) -> AppSettings:
    """Tizim sozlamalarini olish (global funksiya)
    
    Args:
        force_reload: Agar True bo'lsa, cache'ni tozalab fayldan o'qiydi.
                     Webhook service uchun har safar fayldan o'qish uchun True qiling.
    """
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = AppSettingsManager()
    return _settings_manager.get_settings(force_reload=force_reload)


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
