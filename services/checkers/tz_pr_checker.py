# services/tz_pr_service.py - FIGMA INTEGRATION ADDED
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
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
import re

# Core imports
from core import BaseService, PRHelper, PRNotMergedError, TZHelper, CommentSeparator, WARN_LOW_SCORE, RECHECK_REASONS
from core.analysis_policy import (
    build_full_analysis_blocked,
    build_full_policy_input_violation,
)
from core.logger import get_logger

# Initialize logger
log = get_logger("tzpr.checker")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SMART_PATCH_AVAILABLE = True

# AI Prompt - O'ZBEK TILIDA! (sozlama tartibida ma'lumotlar + scope qoidasi)
AI_PROMPT_TEMPLATE_UZ = """
╔══════════════════════════════════════════════════════════════════╗
║ 🎯 VAZIFA: TZ VA KOD MOSLIGINI TAHLIL QILISH                     ║
╚══════════════════════════════════════════════════════════════════╝

📋 TASK: {task_key}
📝 SUMMARY: {task_summary}

{scope_instruction}

{data_sections_body}

╔══════════════════════════════════════════════════════════════════╗
║ 📝 TAHLIL QILISH TARTIBI                                         ║
╚══════════════════════════════════════════════════════════════════╝

1. **TZ TALABLARI BAJARILISHI**
   - TZ da ko'rsatilgan har bir talabni tekshir
   - Kod shu talabni bajaradimi?
   - Qaysi talablar to'liq bajarilgan, qaysilari qisman, qaysilari yo'q?

2. **KOD SIFATI**
   - Kod yaxshi yozilganmi (clean code)?
   - Potensial buglar bormi?
   - Edge case'lar handled qilinganmi?
   - Error handling to'g'rimi?

3. **ORTIQCHA O'ZGARISHLAR**
   - TZ da yo'q, lekin kodda bor narsalar bormi?
   - Bu o'zgarishlar zarurmi yoki ortiqchami?

{figma_analysis_section}

╔══════════════════════════════════════════════════════════════════╗
║ 📊 JAVOB FORMATI (ANIQ SHU FORMATDA YOZ!)                        ║
╚══════════════════════════════════════════════════════════════════╝

{response_format_sections}

## 📊 MOSLIK BALI
[0-100% oralig'ida baho. Format: **COMPLIANCE_SCORE: XX%**]

⚠️ MUHIM: Javobingiz oxirida ALBATTA **COMPLIANCE_SCORE: XX%** formatida baho yoz!
Bu qatorni HECH QACHON tashlab ketma, aks holda natija noto'g'ri bo'ladi.

╚══════════════════════════════════════════════════════════════════╝
"""

# Developer comment'da "keyin qilinadi" / "keyingi sprint" deb yozilganda faqat shu PR da kutilgan ishlar bo'yicha baho
SCOPE_INSTRUCTION_UZ = """
─────────────────────────────────────────────────────────────────────
⚠️ MUHIM: DEVELOPER IZOHLARI BO'YICHA TEKSHRUV DOIRASI
─────────────────────────────────────────────────────────────────────

Agar developer (izohlar bo'limida) TZ dagi ba'zi talablarni "keyingi sprintda qilinadi", "keyin qilinadi", "kelishdik shunday qilamiz" va sh.k. deb yozgan bo'lsa:
- Faqat SHU PR da bajarilishi kerak bo'lgan talablar bo'yicha moslikni baholang.
- Keyinga qoldirilgan talablarni "bajarilmagan" deb hisoblamang — ular bu PR doirasida emas.
- Masalan: TZ da 10 ta ish, kodda 5 ta, dev "5 ta qilindi, qolgani keyingi sprintda" deb yozsa → faqat 5 ta ishni tekshiring, moslikni shu 5 ta bo'yicha bering.

"""

# Re-tahlil kontekst bo'limi — task qaytarilib, dev etirozlar yozganda qo'shiladi
REANALYSIS_CONTEXT_TEMPLATE_UZ = """
─────────────────────────────────────────────────────────────────────
🔄 RE-TAHLIL: TASK AVVAL QAYTARILGAN, DEVELOPER JAVOB YOZGAN
─────────────────────────────────────────────────────────────────────

📋 AVVALGI TAHLILING XULOSASI:
{previous_analysis}

💬 DEVELOPER ETIROZLARI (tahlildan KEYIN yozilgan):
{dev_objections}

⚠️ MUHIM KO'RSATMA:
- Developer izohlari TEXNIK jihatdan to'g'rimi — kodni QAYTADAN ko'rib chiq.
- Agar developer haqqoniy izoh bergan bo'lsa → COMPLIANCE_SCORE ni OSHIR va sababini tushuntir.
- Agar izoh asossiz yoki kodni to'g'ri ifodalamasa → avvalgi balga yaqin qoldir va nima uchunligini ayt.
- Ikki holat uchun ham xulosangni "Avvalgi baho: XX% → Yangi baho: YY%" ko'rinishida yoz.

"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VISIBLE SECTIONS → AI OUTPUT FORMAT MAPPING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Keys must match TZPRCheckerSettings.visible_sections values
_SECTION_PROMPT_BLOCKS = {
    'summary': (
        "## 🧭 XULOSA\n"
        "[2-4 qatorda umumiy verdict, asosiy sabab va eng muhim keyingi signal]\n"
    ),
    'completed': (
        "## ✅ BAJARILGAN TALABLAR\n"
        "[TZ dan olingan har bir talab va uning bajarilish holati]\n"
    ),
    'partial': (
        "## ⚠️ QISMAN BAJARILGAN\n"
        "[Qisman bajarilgan talablar va nimasi yetishmayotgani]\n"
    ),
    'failed': (
        "## ❌ BAJARILMAGAN TALABLAR\n"
        "[TZ da bor, lekin kodda yo'q narsalar]\n"
    ),
    'issues': (
        "## 🐛 POTENSIAL MUAMMOLAR\n"
        "[Kod sifati, buglar, edge case'lar, error handling]\n"
    ),
}

# Canonical order in which sections appear in the prompt
_SECTION_ORDER = ['summary', 'completed', 'partial', 'failed', 'issues', 'figma']

UI_VISIBLE_SECTIONS = ['summary', 'completed', 'partial', 'failed', 'issues', 'figma']
COMMENT_VISIBLE_SECTION_KEYS = {'completed', 'partial', 'failed', 'issues', 'figma'}

_ANALYSIS_TITLE_TO_KEY = {
    'summary': 'summary',
    'xulosa': 'summary',
    'bajarilgan': 'completed',
    'qisman': 'partial',
    'bajarilmagan': 'failed',
    'muammo': 'issues',
    'potensial': 'issues',
    'figma': 'figma',
    'moslik bali': 'score',
    'compliance_score': 'score',
}


def _build_response_format_sections(
        visible_sections: List[str],
        figma_response_section: str
) -> str:
    """
    visible_sections sozlamasi asosida AI javob formati bo'limlarini dinamik yigit.

    COMPLIANCE_SCORE bo'limi har doim alohida template'da qoladi, bu funksiya uni qo'shmasdan.

    Args:
        visible_sections: Yoqilgan bo'limlar ro'yxati (masalan: ['completed', 'partial'])
        figma_response_section: Figma bo'limi (allaqachon _build_figma_prompt_section'dan tayyorlangan)

    Returns:
        str: Barcha yoqilgan bo'limlarni o'z ichiga olgan formatli string
    """
    blocks = []
    for key in _SECTION_ORDER:
        if key not in visible_sections:
            continue
        if key == 'figma':
            # Figma section is already built by _build_figma_prompt_section
            if figma_response_section:
                blocks.append(figma_response_section)
        else:
            blocks.append(_SECTION_PROMPT_BLOCKS[key])
    return "\n".join(blocks)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATA CLASSES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class TZPRAnalysisSection:
    """Frontend uchun strukturalashtirilgan AI bo'limi."""
    key: str
    title: str
    lines: List[str] = field(default_factory=list)
    items: List[str] = field(default_factory=list)
    item_count: int = 0
    empty: bool = False


@dataclass
class TZPRAnalysisOverview:
    """Frontend checker header/summary uchun qisqa overview."""
    verdict: str = "unknown"
    verdict_label: str = "Unknown"
    verdict_reason: str = ""
    summary_lines: List[str] = field(default_factory=list)
    section_counts: Dict[str, int] = field(default_factory=dict)
    missing_figma_access: bool = False
    requested_sections: List[str] = field(default_factory=list)


@dataclass
class TZPRAnalysisResult:
    """Tahlil natijasi"""
    task_key: str
    task_summary: str = ""
    tz_content: str = ""
    pr_count: int = 0
    files_changed: int = 0
    total_additions: int = 0
    total_deletions: int = 0
    pr_details: List[Dict] = field(default_factory=list)
    ai_analysis: str = ""
    compliance_score: Optional[int] = None
    success: bool = True
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)
    status_banner: Optional[Dict] = None

    # AI retry info
    ai_retry_count: int = 0
    files_analyzed: int = 0
    total_prompt_size: int = 0

    figma_data: Optional[Dict] = None  # Figma ma'lumotlari (optional)

    comment_analysis: Optional[Dict] = None  # TZHelper.analyze_comments() natijasi (zid commentlar)

    dev_objections: List[Dict] = field(default_factory=list)  # [AI_S1] dan keyin yozilgan dev comment'lar
    analysis_sections: List[TZPRAnalysisSection] = field(default_factory=list)
    analysis_overview: Optional[TZPRAnalysisOverview] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN SERVICE CLASS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TZPRService(BaseService):
    """TZ va PR mosligini tekshirish - With Figma Support"""

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

    def _get_visible_sections_for_profile(self, output_profile: str) -> List[str]:
        """UI checker uchun to'liq section set, comment profile uchun esa konfiguratsiya."""
        if output_profile == "ui":
            return list(UI_VISIBLE_SECTIONS)

        configured = self._get_settings().visible_sections or []
        filtered = [key for key in configured if key in COMMENT_VISIBLE_SECTION_KEYS]
        return filtered or ['partial', 'failed', 'figma']

    @property
    def pr_helper(self):
        """Lazy PR Helper"""
        if self._pr_helper is None:
            self._pr_helper = PRHelper(self.github)
        return self._pr_helper

    def _get_figma_client_for_file(self, file_key: str):
        """Berilgan file_key uchun ishlayotgan tokenni topib FigmaClient qaytaradi (fail-safe)."""
        try:
            from utils.figma.figma_client import FigmaClient
            creds = self._get_creds()
            figma_tokens = creds.get('figma_tokens', [])
            log.info(f"Figma creds: figma_tokens={len(figma_tokens)} ta | company_id={self._company_id} | user_id={self._user_id}")
            if not figma_tokens:
                figma_token_single = creds.get('figma_token', '')
                has_old = "bor" if figma_token_single else "yoq"
                log.warning(f"Figma: figma_tokens bosh | figma_token (eski)={has_old}")
                return None
            working_token = FigmaClient.find_working_token(figma_tokens, file_key)
            if working_token:
                return FigmaClient(access_token=working_token)
            log.warning(f"Figma: ishlayotgan token topilmadi | file_key={file_key}")
        except Exception as e:
            log.warning(f"Figma client init failed: {e}")
        return None

    def analyze_task(
            self,
            task_key: str,
            max_files: Optional[int] = None,
            show_full_diff: bool = True,
            use_smart_patch: Optional[bool] = None,
            status_callback: Optional[Callable[[str, str], None]] = None,
            return_reason: Optional[str] = None,
            output_profile: str = "comment",
    ) -> TZPRAnalysisResult:
        """
        TZ-PR moslik tahlilining asosiy funksiyasi — 7 bosqichli pipeline.

        Bu funksiya JIRA task kaliti bo'yicha to'liq TZ-PR tahlilini amalga oshiradi
        va natijani TZPRAnalysisResult sifatida qaytaradi. Webhook handler tomonidan
        check_tz_pr_and_comment() orqali chaqiriladi.

        Ishlash bosqichlari:
            1. JIRA'dan task tafsilotlarini olish (TZ, priority, assignee, figma_links).
            2. TZ kontentini formatlash va zid comment'larni aniqlash (TZHelper).
            3. GitHub'dan PR ma'lumotlarini olish; PR topilmasa — 'pr_not_found' xatosi.
            3.5 Figma havolalarini ajratib olish va Figma API'dan ma'lumot olish (ixtiyoriy,
               muvaffaqiyatsizlik bo'lsa ham asosiy jarayon to'xtatilmaydi).
            4. AI tahlilini amalga oshirish (FULL-only policy).
            5. Moslik balini ajratib olish (_extract_compliance_score() orqali 4 regex).
            6. Task meta-ma'lumotlarini DB'ga saqlash (assignee, task_type, feature_name).
            7. TZPRAnalysisResult natijasini qaytarish.

        Args:
            task_key (str): JIRA task identifikatori (masalan: 'DEV-1234').
            max_files (Optional[int]): AI promtiga qo'shiladigan maksimal fayl soni.
                None bo'lsa — barcha o'zgargan fayllar qo'shiladi.
            show_full_diff (bool): True bo'lsa — har bir fayl uchun to'liq diff/patch
                AI promtiga kiritiladi. False bo'lsa — faqat fayl nomi va statistika.
            use_smart_patch (Optional[bool]): True bo'lsa — standart diff o'rniga smart_context
                (to'liq kontekst) ishlatiladi. None bo'lsa setting'dagi
                `default_use_smart_patch` qiymati ishlatiladi.
            status_callback (Optional[Callable[[str, str], None]]): Ixtiyoriy.
                Progress yangilanishi uchun callback(level, message).
                UI progress bar yoki logging uchun ishlatiladi.

        Returns:
            TZPRAnalysisResult:
                success=True holatida:
                    - compliance_score: 0-100 oralig'idagi moslik bali.
                    - ai_analysis: AI tomonidan yozilgan to'liq tahlil matni.
                    - figma_data: Figma fayl xulosalari (mavjud bo'lsa).
                    - comment_analysis: Zid comment'lar tahlili.
                success=False holatida:
                    - error_message: Xatolik sababi (PR topilmadi, AI xato va h.k.).
                    - warnings: Qo'shimcha ogohlantirishlar ro'yxati.

        Raises:
            Exception: Ichki barcha xatoliklar ushlanib, success=False natijaga
                aylantiriladi — funksiya hech qachon exception ko'tarmaydi.

        Side Effects:
            - DB'da task meta-ma'lumotlari yangilanadi (update_task_metadata()).
            - status_callback chaqiriladi (agar berilgan bo'lsa).
        """

        update_status = self._create_status_updater(status_callback)

        try:
            # Full-only policy: partial analysis taqiqlanadi
            if max_files is not None or not show_full_diff:
                banner = build_full_policy_input_violation(
                    module_name="TZ-PR Checker",
                    task_key=task_key,
                    max_files=max_files,
                    show_full_diff=show_full_diff,
                )
                return self._create_error_result(
                    task_key=task_key,
                    error_message=banner["message"],
                    status_banner=banner,
                )

            effective_use_smart_patch = (
                use_smart_patch
                if use_smart_patch is not None
                else bool(getattr(self._get_settings(), "default_use_smart_patch", True))
            )

            # Step 1: Get task details
            task_details = self._get_task_details(task_key, update_status)
            if not task_details:
                return self._create_error_result(
                    task_key,
                    f"❌ {task_key} topilmadi. JIRA da task mavjudligini va API kalitlarini tekshiring."
                )

            # Step 2: PR bor? merged? (birinchi tekshiruv — keraksiz ishni oldini olish)
            from utils.pr_cache import set_pr_exists_cache, set_pr_merged_cache
            try:
                pr_info = self._get_pr_info(task_key, task_details, update_status, effective_use_smart_patch)
            except PRNotMergedError as e:
                set_pr_exists_cache(task_key, True)
                set_pr_merged_cache(task_key, False)
                return self._create_error_result(
                    task_key,
                    str(e),
                    task_summary=task_details['summary'],
                )
            if not pr_info:
                set_pr_exists_cache(task_key, False)
                return self._create_error_result(
                    task_key,
                    "Bu task uchun PR topilmadi (JIRA va GitHub'da)",
                    task_summary=task_details['summary'],
                    warnings=["JIRA da PR link yo'q", "GitHub search natija bermadi"]
                )
            set_pr_exists_cache(task_key, True)
            set_pr_merged_cache(task_key, True)

            # Step 3: TZ uzunlik tekshiruvi
            min_tz = self._get_settings().min_tz_description_chars
            if min_tz > 0 and self._is_tz_too_short(task_details, min_tz):
                actual_chars = len((task_details.get('description') or '').strip())
                msg = (
                    f"TZ yetarli emas. "
                    f"(mavjud: {actual_chars} belgi, min: {min_tz} belgi). Servis-1 to'xtatildi."
                )
                update_status("error", msg)
                return self._create_error_result(
                    task_key, msg,
                    task_summary=task_details['summary']
                )

            # Faqat WARN_LOW_SCORE da dev objections o'qiladi
            is_recheck = return_reason in RECHECK_REASONS

            # Step 4: Get TZ content + dev/AI comment separation
            tz_content, comment_analysis = self._get_tz_content(
                task_details,
                update_status
            )
            comment_separated = CommentSeparator.separate(task_details.get('comments', []))

            # Step 5: Get Figma data (OPTIONAL, FAIL-SAFE)
            figma_data = self._get_figma_data(task_details, update_status)

            # Step 6: AI analysis (with Figma if available)
            update_status("progress", "AI tahlil qilinmoqda...")
            ai_result = self._perform_ai_analysis(
                task_key,
                task_details,
                tz_content,
                pr_info,
                figma_data,
                max_files,
                show_full_diff,
                effective_use_smart_patch,
                update_status,
                is_recheck=is_recheck,
                comment_separated=comment_separated,
                output_profile=output_profile,
            )

            if not ai_result['success']:
                return self._create_error_result(
                    task_key,
                    ai_result['error'],
                    tz_content=tz_content,
                    task_summary=task_details['summary'],
                    pr_info=pr_info,
                    warnings=ai_result.get('warnings', []),
                    figma_data=figma_data,
                    status_banner=ai_result.get("status_banner"),
                    ai_retry_count=ai_result.get("retry_count", 0),
                    files_analyzed=ai_result.get("files_analyzed", 0),
                    total_prompt_size=ai_result.get("prompt_size", 0),
                )

            # Step 5: Extract compliance score
            compliance_score = self._extract_compliance_score(ai_result['analysis'])
            analysis_sections, analysis_overview = self._build_structured_analysis(
                ai_result['analysis'],
                compliance_score=compliance_score,
                output_profile=output_profile,
                figma_data=figma_data,
            )

            # Step 6: Update metadata (assignee, task_type, features)
            try:
                from utils.database.task_db import update_task_metadata
                update_task_metadata(task_key, task_details, pr_info)
            except Exception as e:
                log.warning(f"[{task_key}] Metadata update failed: {e}")

            # Step 7: Return result
            return TZPRAnalysisResult(
                task_key=task_key,
                task_summary=task_details['summary'],
                tz_content=tz_content,
                pr_count=pr_info['pr_count'],
                files_changed=pr_info['files_changed'],
                total_additions=pr_info['total_additions'],
                total_deletions=pr_info['total_deletions'],
                pr_details=pr_info['pr_details'],
                ai_analysis=ai_result['analysis'],
                compliance_score=compliance_score,
                success=True,
                warnings=ai_result.get('warnings', []),
                ai_retry_count=ai_result.get('retry_count', 0),
                files_analyzed=ai_result.get('files_analyzed', 0),
                total_prompt_size=ai_result.get('prompt_size', 0),
                figma_data=figma_data,
                comment_analysis=comment_analysis,
                dev_objections=comment_separated.get('dev_after', []) if is_recheck else [],
                analysis_sections=analysis_sections,
                analysis_overview=analysis_overview,
            )

        except Exception as e:
            return self._create_error_result(
                task_key,
                f"Kutilmagan xatolik: {str(e)}"
            )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FIGMA METHODS (NEW, FAIL-SAFE)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _get_figma_data(self, task_details: Dict, update_status) -> Optional[Dict]:
        """
        Figma ma'lumotlarini olish (FAIL-SAFE)

        Returns:
            Dict or None: Figma data yoki None (xatolik bo'lsa)
        """
        try:
            figma_links = task_details.get('figma_links', [])
            log.info(f"Figma: task da {len(figma_links)} ta figma_link topildi")

            if not figma_links:
                # No Figma links - bu normal holat, xatolik emas
                return None

            # Collect summaries — har bir fayl uchun ishlayotgan token qidiriladi
            summaries = []
            for link in figma_links:
                file_key = link['file_key']
                client = self._get_figma_client_for_file(file_key)
                if not client:
                    update_status("warning", f"Figma: {link['name']} — ishlayotgan token topilmadi")
                    summaries.append({
                        'file_key': file_key,
                        'name': link['name'],
                        'url': link['url'],
                        'summary': "Token topilmadi yoki ruxsat yo'q"
                    })
                    continue
                try:
                    node_id = link.get('node_id')
                    summary = client.get_file_summary(file_key, node_id=node_id)
                    summaries.append({
                        'file_key': file_key,
                        'name': link['name'],
                        'url': link['url'],
                        'summary': summary
                    })
                except Exception as e:
                    update_status("warning", f"Figma: {link['name']} olinmadi")
                    summaries.append({
                        'file_key': file_key,
                        'name': link['name'],
                        'url': link['url'],
                        'summary': f"Error: {str(e)}"
                    })

            return {
                'links': figma_links,
                'summaries': summaries,
                'count': len(summaries)
            }

        except Exception as e:
            # Global Figma error - log but don't fail
            update_status("warning", f"Figma xatolik: {str(e)}")
            return None

    def _build_figma_prompt_section(self, figma_data: Optional[Dict]) -> tuple:
        """
        Figma uchun prompt section yaratish

        Returns:
            tuple: (figma_section, figma_analysis_section, figma_response_section)
        """
        if not self._has_usable_figma_data(figma_data):
            # No Figma data - return empty sections
            return ("", "", "")

        # Build Figma section for prompt
        figma_lines = [
            "",
            "─────────────────────────────────────────────────────────────────────",
            "🎨 FIGMA DIZAYN MA'LUMOTLARI",
            "─────────────────────────────────────────────────────────────────────",
            ""
        ]

        for summary_data in figma_data['summaries']:
            figma_lines.append(summary_data['summary'])
            figma_lines.append("")

        figma_section = "\n".join(figma_lines)

        # Add Figma analysis instruction
        figma_analysis_section = """
5. **FIGMA DIZAYN MOSLIGI**
   - Yuqorida Figma frame, matn va comment ma'lumotlari berilgan — shu asosda tahlil qil.
   - TZ da ko'rsatilgan UI elementlar hamda matn talablar Figma'dagi real yozuvlarga mos keladimi?
   - Figma'dagi comment'larda yozilgan aniq talablar (masalan import, ustun, limit) kodda implement qilinganmi?
   - Qaysi Figma frame/matn/comment talablari bajarilgan, qaysilari yo'q?
"""

        # Add Figma response section
        figma_response_section = """
## 🎨 FIGMA DIZAYN MOSLIGI
[Figma frame, matn va comment'lardagi aniq talablar asosida moslikni tahlil qil. "Figma'ga kirish imkoni yo'q" iborasini ISHLATMA — Figma ma'lumotlari yuqorida berilgan.]
"""

        return (figma_section, figma_analysis_section, figma_response_section)

    def _has_usable_figma_data(self, figma_data: Optional[Dict]) -> bool:
        """Figma summary'lar ichida real frame/file ma'lumoti bormi."""
        if not figma_data or not figma_data.get('summaries'):
            return False

        unusable_markers = (
            "token topilmadi",
            "ruxsat yo'q",
            "access yo'q",
            "error:",
            "olinmadi",
            "summary error",
        )
        for item in figma_data.get('summaries', []):
            summary = str(item.get('summary') or '').strip().lower()
            if summary and not any(marker in summary for marker in unusable_markers):
                return True
        return False

    def _sanitize_ai_analysis_for_missing_figma(self, analysis: str, figma_data: Optional[Dict]) -> str:
        """
        Figma ma'lumoti bo'lmasa, Figma bo'limini halol status xabariga almashtiradi.
        """
        if self._has_usable_figma_data(figma_data):
            return analysis

        replacement = (
            "## 🎨 FIGMA DIZAYN MOSLIGI\n"
            "Figma ma'lumotlari olinmadi.\n\n"
            "- Figma token yoki ruxsat mavjud emas, yoki faylga access bo'lmadi.\n"
            "- Shu sabab Figma dizayni bilan moslik bo'yicha ishonchli xulosa berib bo'lmaydi.\n"
            "- Quyidagi bajarilgan/bajarilmagan xulosalar faqat TZ va kod o'zgarishlariga asoslangan.\n"
        )

        sanitized = re.sub(
            r'\n*##\s*(?:🎨\s*)?FIGMA\s*DIZAYN\s*MOSLIGI.*?(?=\n##\s*(?:🧭|✅|⚠|❌|🐛|📊|🎨)|\Z)',
            f'\n{replacement}\n',
            analysis,
            flags=re.IGNORECASE | re.DOTALL,
        )
        sanitized = re.sub(
            r'(?im)^\s*5\.\s*\*\*FIGMA\s+DIZAYN\s+MOSLIGI\*\*.*$',
            '',
            sanitized,
        )
        if "## 🎨 FIGMA DIZAYN MOSLIGI" not in sanitized:
            sanitized = sanitized.strip() + "\n\n" + replacement
        return sanitized.strip()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP METHODS (UPDATED)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _get_task_details(self, task_key: str, update_status):
        """JIRA dan task ma'lumotlarini olish"""
        return self.jira.get_task_details(task_key)

    def _get_tz_content(self, task_details: Dict, update_status):
        """TZ kontentini olish"""
        tz_settings = self._get_settings()

        if not tz_settings.read_comments_enabled:
            # Comments o'chirilgan: bo'sh comment list ile chaqirish
            task_no_comments = dict(task_details)
            task_no_comments['comments'] = []
            tz_content, comment_analysis = TZHelper.format_tz_with_comments(
                task_no_comments,
                exclude_ai_comments=True,
            )
        else:
            max_c = tz_settings.max_comments_to_read if tz_settings.max_comments_to_read > 0 else None
            tz_content, comment_analysis = TZHelper.format_tz_with_comments(
                task_details,
                max_comments=max_c,
                exclude_ai_comments=True,
            )

        if comment_analysis['has_changes']:
            update_status("warning", comment_analysis['summary'])
        filtered_ai_comments = int(comment_analysis.get('filtered_out_ai_comments') or 0)
        if filtered_ai_comments > 0:
            update_status(
                "info",
                f"Promptdan {filtered_ai_comments} ta oldingi AI comment chiqarib tashlandi",
            )

        return tz_content, comment_analysis

    def _build_dev_comments_section(self, task_details: Dict, separated: Optional[Dict] = None) -> str:
        """
        AI konteksti uchun developer comment'larini formatlash.

        CommentSeparator.separate() natijasidan foydalanadi:
        - dev_before: tahlildan oldingi dev comment'lar (kontekst)
        - dev_after: tahlildan keyingi dev comment'lar (etirozlar) — recheck bo'lmasa ham qo'shiladi

        Returns:
            str: AI promtiga qo'shishga tayyor formatlangan comment'lar bloki.
        """
        if separated is None:
            separated = CommentSeparator.separate(task_details.get('comments', []))

        max_dev = self._get_settings().dev_comments_max

        dev_before = separated.get('dev_before', [])
        dev_after = separated.get('dev_after', [])

        # Agar hech qanday dev comment yo'q bo'lsa
        if not dev_before and not dev_after:
            return ""

        lines = []

        if dev_before:
            lines += [
                "",
                "─────────────────────────────────────────────────────────────────────",
                "💬 DEVELOPER IZOHLAR (KONTEKST)",
                "─────────────────────────────────────────────────────────────────────",
                "",
                "Developerlar quyidagi izohlarni qoldirgan. Ularni tahlilda hisobga oling:",
                ""
            ]
            for comment in dev_before[-max_dev:]:
                lines.append(f"👤 {comment.get('author', 'Unknown')} ({comment.get('created', '')}):")
                lines.append(f"   {comment.get('body', '').strip()}")
                lines.append("")

        if dev_after:
            lines += [
                "",
                "─────────────────────────────────────────────────────────────────────",
                "⚡ DEVELOPER ETIROZLARI (tahlildan KEYIN yozilgan — alohida e'tibor ber!)",
                "─────────────────────────────────────────────────────────────────────",
                ""
            ]
            for comment in dev_after[-max_dev:]:
                lines.append(f"👤 {comment.get('author', 'Unknown')} ({comment.get('created', '')}):")
                lines.append(f"   {comment.get('body', '').strip()}")
                lines.append("")

        return "\n".join(lines)

    def _build_reanalysis_section(self, separated: Dict) -> str:
        """
        Re-tahlil kontekst bo'limini qurish.

        Faqat is_recheck=True va last_ai_s1 bor bo'lganda chaqiriladi.
        Avvalgi AI tahlilini va developer etirozlarini REANALYSIS_CONTEXT_TEMPLATE_UZ ga joylaydi.
        """
        last_ai = separated.get('last_ai_s1')
        dev_after = separated.get('dev_after', [])

        if not last_ai and not dev_after:
            return ""

        prev_analysis = ""
        if last_ai:
            body = last_ai.get('body', '').strip()
            # [AI_S1] markerini olib tashlash
            if body.startswith('[AI_S1]'):
                body = body[len('[AI_S1]'):].strip()
            # Juda uzun bo'lsa qisqartirish (2000 belgi yetarli)
            prev_analysis = body[:2000] + ("..." if len(body) > 2000 else "")

        objections = ""
        if dev_after:
            obj_lines = []
            for c in dev_after:
                obj_lines.append(f"👤 {c.get('author', 'Unknown')} ({c.get('created', '')}):")
                obj_lines.append(f"   {c.get('body', '').strip()}")
                obj_lines.append("")
            objections = "\n".join(obj_lines)

        if not prev_analysis and not objections:
            return ""

        return REANALYSIS_CONTEXT_TEMPLATE_UZ.format(
            previous_analysis=prev_analysis or "(avvalgi tahlil topilmadi)",
            dev_objections=objections or "(developer etirozlari yo'q)"
        )

    def _build_ordered_data_sections(
            self,
            order: List[str],
            tz_content: str,
            dev_comments_section: str,
            reanalysis_section: str,
            figma_section: str,
            code_changes: str
    ) -> str:
        """
        Sozlamadagi ai_data_section_order bo'yicha ma'lumotlar bo'limlarini birlashtirish.
        reanalysis_section bor bo'lsa TZ dan keyin, code dan oldin qo'shiladi.
        """
        blocks = []
        sep = "\n─────────────────────────────────────────────────────────────────────\n"
        for key in order:
            if key == "tz":
                blocks.append(sep + "📄 TEXNIK TOPSHIRIQ (TZ)\n" + sep + "\n" + (tz_content or "").strip())
                # Re-tahlil bo'limi TZ dan keyin darhol qo'shiladi (order ga bog'liq emas)
                if (reanalysis_section or "").strip():
                    blocks.append((reanalysis_section or "").strip())
            elif key == "comments":
                if (dev_comments_section or "").strip():
                    blocks.append((dev_comments_section or "").strip())
            elif key == "figma":
                if (figma_section or "").strip():
                    blocks.append((figma_section or "").strip())
            elif key == "code":
                blocks.append(sep + "💻 GITHUB KOD O'ZGARISHLARI\n" + sep + "\n" + (code_changes or "").strip())
        return "\n\n".join(blocks)

    def _is_tz_too_short(self, task_details: Dict, min_chars: int) -> bool:
        """TZ (description) belgilangan minimal uzunlikdan qisqami aniqlash."""
        description = task_details.get('description') or ''
        return len(description.strip()) < min_chars

    def _get_pr_info(self, task_key: str, task_details: Dict, update_status, use_smart_patch):
        """PR ma'lumotlarini olish va cache ga saqlash"""
        pr_info = self.pr_helper.get_pr_full_info(
            task_key,
            task_details,
            update_status,
            use_smart_patch=use_smart_patch
        )

        # Service2 qayta qidirmasin deb cache ga saqlaymiz
        if pr_info:
            try:
                from utils.pr_cache import set_pr_cache
                set_pr_cache(task_key, pr_info)
            except Exception:
                pass

        return pr_info

    def _perform_ai_analysis(
            self,
            task_key: str,
            task_details: Dict,
            tz_content: str,
            pr_info: Dict,
            figma_data: Optional[Dict],
            max_files: Optional[int],
            show_full_diff: bool,
            use_smart_patch: bool,
            update_status,
            is_recheck: bool = False,
            comment_separated: Optional[Dict] = None,
            output_profile: str = "comment",
    ) -> Dict:
        """
        AI tahlil bosqichini boshqaruvchi oraliq funksiya.

        Bu funksiya ikki ish bajaradi:
            1. Developer comment'larni filtrlaydi (_build_dev_comments_section()).
            2. Natijani _analyze_with_retry() ga uzatib, 3 strategiyali AI tahlilini ishga tushiradi.

        analyze_task() va _analyze_with_retry() o'rtasidagi ko'prik vazifasini o'taydi:
        parametrlarni tartibga soladi va dev_comments_section ni dinamik ravishda qurib,
        retry mexanizmi uchun tayyor holga keltiradi.

        Args:
            task_key (str): JIRA task identifikatori (masalan: 'DEV-1234').
            task_details (Dict): JIRA'dan olingan task ma'lumotlari (summary, comments, va h.k.).
            tz_content (str): Formatlangan TZ kontenti.
            pr_info (Dict): GitHub PR ma'lumotlari (files, diff, statistika).
            figma_data (Optional[Dict]): Figma fayl xulosalari yoki None.
            max_files (Optional[int]): AI promtiga qo'shiladigan maksimal fayl soni.
            show_full_diff (bool): Har bir fayl uchun to'liq diff qo'shilsinmi.
            use_smart_patch (bool): Smart patch rejimi yoqilganmi.
            update_status: Progress yangilanishi uchun callback(level, message).

        Returns:
            Dict: _analyze_with_retry() formatidagi natija:
                {
                    'success': bool,
                    'analysis': str,       # AI tahlil matni
                    'retry_count': int,    # Qayta urinishlar soni
                    'files_analyzed': int,
                    'prompt_size': int,
                    'warnings': List[str]
                }
        """
        separated = comment_separated or CommentSeparator.separate(task_details.get('comments', []))
        dev_comments_section = self._build_dev_comments_section(task_details, separated)
        reanalysis_section = self._build_reanalysis_section(separated) if is_recheck else ""

        return self._analyze_with_retry(
            task_key=task_key,
            task_details=task_details,
            tz_content=tz_content,
            pr_info=pr_info,
            figma_data=figma_data,
            dev_comments_section=dev_comments_section,
            reanalysis_section=reanalysis_section,
            max_files=max_files,
            show_full_diff=show_full_diff,
            use_smart_patch=use_smart_patch,
            status_callback=update_status,
            output_profile=output_profile,
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # AI ANALYSIS (FULL-ONLY POLICY)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _analyze_with_retry(
            self,
            task_key: str,
            task_details: Dict,
            tz_content: str,
            pr_info: Dict,
            figma_data: Optional[Dict],
            dev_comments_section: str,
            reanalysis_section: str,
            max_files: Optional[int],
            show_full_diff: bool,
            use_smart_patch: bool,
            status_callback,
            output_profile: str = "comment",
    ) -> Dict:
        """
        AI tahlili: FULL-only policy.

        Qoidalar:
            1. Faqat bitta urinish: barcha fayllar va to'liq diff.
            2. Faylni kamaytirish yoki diffni o'chirish taqiqlanadi.
            3. AI xatoligida partial natija qaytmaydi; standart block xabari qaytadi.

        Args:
            task_key (str): JIRA task identifikatori (masalan: 'DEV-1234').
            task_details (Dict): JIRA'dan olingan task ma'lumotlari (summary, comments, va h.k.).
            tz_content (str): Formatlangan TZ kontenti (AI promtiga qo'shiladi).
            pr_info (Dict): GitHub PR ma'lumotlari (files, diff, statistika).
            figma_data (Optional[Dict]): Figma fayl xulosalari (None bo'lishi mumkin).
            dev_comments_section (str): Filtered developer comment'lar bloki
                (_build_dev_comments_section() tomonidan tayyorlanadi).
            max_files (Optional[int]): 1-strategiyada ishlatiladigan maksimal fayl soni.
            show_full_diff (bool): 1- va 2-strategiyalarda diff qo'shilsinmi.
            use_smart_patch (bool): Smart patch rejimi yoqilganmi.
            status_callback: Progress yangilanishi uchun callback(level, message).

        Returns:
            Dict: _try_ai_analysis() formatidagi natija:
                {
                    'success': bool,
                    'analysis': str,          # AI tahlil matni (muvaffaqiyatli holatda)
                    'error': str,             # Xatolik xabari (muvaffaqiyatsiz holatda)
                    'retry_count': int,       # Nechi strategiya ishlatilgani (0, 1 yoki 2)
                    'files_analyzed': int,    # Tahlil qilingan fayllar soni
                    'prompt_size': int,       # Promtning belgilar soni
                    'warnings': List[str]     # Qo'shimcha ogohlantirishlar
                }
        """

        # Build Figma sections
        figma_section, figma_analysis, figma_response = self._build_figma_prompt_section(figma_data)

        # Read visible_sections from settings
        visible_sections = self._get_visible_sections_for_profile(output_profile)

        # Build dynamic response format (respects visible_sections)
        response_format_sections = _build_response_format_sections(
            visible_sections, figma_response
        )

        # Full attempt: all files + full diff
        result = self._try_ai_analysis(
            task_key=task_key,
            task_details=task_details,
            tz_content=tz_content,
            pr_info=pr_info,
            figma_data=figma_data,
            figma_section=figma_section,
            figma_analysis=figma_analysis,
            dev_comments_section=dev_comments_section,
            reanalysis_section=reanalysis_section,
            response_format_sections=response_format_sections,
            max_files=max_files,
            show_full_diff=show_full_diff,
            use_smart_patch=use_smart_patch,
            retry_attempt=0,
            output_profile=output_profile,
        )

        files_total = pr_info.get('files_changed', 0)
        files_included = result.get('files_analyzed')
        prompt_size = result.get('prompt_size')
        model_name = result.get('model_name')

        if result['success'] and files_included == files_total:
            return result

        # Any failure/partial -> block (standardized)
        blocked = build_full_analysis_blocked(
            module_name="TZ-PR Checker",
            task_key=task_key,
            error_message=result.get("error", "AI full analysis failed"),
            files_total=files_total,
            files_included=files_included,
            prompt_size_chars=prompt_size,
            model=model_name,
        )
        return {
            "success": False,
            "error": blocked["error_message"],
            "warnings": [],
            "retry_count": result.get("retry_count", 0),
            "files_analyzed": files_included,
            "prompt_size": prompt_size,
            "status_banner": blocked["status_banner"],
            "model_name": model_name,
        }

    def _try_ai_analysis(
            self,
            task_key: str,
            task_details: Dict,
            tz_content: str,
            pr_info: Dict,
            figma_data: Optional[Dict],
            figma_section: str,
            figma_analysis: str,
            dev_comments_section: str,
            reanalysis_section: str,
            response_format_sections: str,
            max_files: Optional[int],
            show_full_diff: bool,
            use_smart_patch: bool,
            retry_attempt: int,
            output_profile: str = "comment",
    ) -> Dict:
        """Single AI analysis attempt."""

        try:
            # Build code changes
            code_changes = self._build_code_changes_section(
                pr_info,
                max_files,
                show_full_diff,
                use_smart_patch
            )

            # Sozlamadagi tartib bo'yicha ma'lumotlar bo'limini yig'ish (AI qat'iy amal qiladi)
            tz_settings = self._get_settings()
            order = tz_settings.ai_data_section_order or ["tz", "comments", "figma", "code"]
            data_sections_body = self._build_ordered_data_sections(
                order=order,
                tz_content=tz_content,
                dev_comments_section=dev_comments_section,
                reanalysis_section=reanalysis_section,
                figma_section=figma_section,
                code_changes=code_changes
            )

            # Yashirilgan bo'limlar uchun qat'iy taqiq qo'shish
            _section_names_uz = {
                'completed': 'BAJARILGAN TALABLAR',
                'partial':   'QISMAN BAJARILGAN',
                'failed':    'BAJARILMAGAN TALABLAR',
                'issues':    'POTENSIAL MUAMMOLAR',
                'figma':     'FIGMA DIZAYN',
            }
            tz_settings_local = self._get_settings()
            visible_local = self._get_visible_sections_for_profile(output_profile)
            hidden = [v for k, v in _section_names_uz.items() if k not in visible_local]
            if hidden:
                response_format_sections += (
                    "\n\n⛔ TAQIQLANGAN BO'LIMLAR (QO'SHMA, YOZMA): "
                    + ", ".join(hidden)
                    + "\nYuqoridagi taqiqlangan bo'limlarni hech qachon javobga qo'shma!"
                )

            if not figma_section.strip():
                response_format_sections += (
                    "\n\n⛔ FIGMA MA'LUMOTI MAVJUD EMAS:"
                    "\n- Figma haqida hech qanday xulosa, taxmin, ehtimoliy moslik yoki dizayn bahosi yozma."
                    "\n- `FIGMA DIZAYN MOSLIGI` bo'limini qoldir, lekin faqat access bo'lmagani va xulosa berib bo'lmasligini yoz."
                    "\n- `Figma bo'lmasa ham kodga qarab mos deb aytish mumkin` kabi taxminiy gaplarni yozma."
                    "\n- Aniq yoz: `Figma ma'lumotlari olinmadi, shu sabab Figma dizayni bo'yicha xulosa berib bo'lmaydi.`"
                )

            # Build final prompt (tartib sozlamadan, scope qoidasi qo'shilgan)
            prompt = AI_PROMPT_TEMPLATE_UZ.format(
                task_key=task_key,
                task_summary=task_details['summary'],
                scope_instruction=SCOPE_INSTRUCTION_UZ,
                data_sections_body=data_sections_body,
                figma_analysis_section=figma_analysis,
                response_format_sections=response_format_sections
            )

            prompt_size = len(prompt)

            # Call AI — barcha bo'limlar yoqilganda javob katta bo'ladi,
            # shuning uchun max_output_tokens settings'dan olinadi
            max_tokens = tz_settings.ai_max_output_tokens
            model_name = getattr(self.gemini, "model_name", None)
            analysis = self.gemini.analyze(prompt, max_output_tokens=max_tokens)
            analysis = self._sanitize_ai_analysis_for_missing_figma(analysis, figma_data)

            return {
                'success': True,
                'analysis': analysis,
                'retry_count': retry_attempt,
                'files_analyzed': max_files or pr_info['files_changed'],
                'prompt_size': prompt_size,
                'warnings': [],
                'model_name': model_name,
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'error': f"AI xatolik (attempt {retry_attempt}): {error_msg}",
                'retry_count': retry_attempt,
                'warnings': [f"Retry {retry_attempt} failed: {error_msg}"],
                'files_analyzed': max_files or pr_info.get('files_changed', 0),
                'prompt_size': prompt_size if 'prompt_size' in locals() else 0,
                'model_name': getattr(getattr(self, "_gemini_helper", None), "model_name", None),
            }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # HELPER METHODS (UNCHANGED)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_code_changes_section(
            self,
            pr_info: Dict,
            max_files: Optional[int],
            show_full_diff: bool,
            use_smart_patch: bool
    ) -> str:
        """
        AI promti uchun kod o'zgarishlari bo'limini qurishning aqlli funksiyasi.

        Funksiya ikkita rejimda ishlaydi:
            - Smart Patch rejimi (use_smart_patch=True): Har bir fayl uchun
              ``smart_context`` maydoni mavjud bo'lsa, standart patch o'rniga
              to'liq kontekstli kod ko'rinishi qo'shiladi.
            - Standart diff rejimi (use_smart_patch=False yoki smart_context yo'q):
              GitHub PR'dagi oddiy unified diff (``patch`` maydoni) ishlatiladi.

        Qo'shilgan bo'limlar:
            - PR umumiy statistikasi (PR soni, o'zgargan fayllar, qo'shimcha/o'chirish).
            - Har bir PR uchun: sarlavha, URL, fayl soni.
            - Har bir fayl uchun (max_files chegarasigacha): fayl nomi, holati,
              o'zgarishlar soni va (show_full_diff=True bo'lsa) diff/smart_context.

        Args:
            pr_info (Dict): GitHub PR ma'lumotlari. Kerakli kalitlar:
                - 'pr_count': PR'lar soni.
                - 'files_changed': Jami o'zgargan fayllar soni.
                - 'total_additions': Jami qo'shilgan satrlar.
                - 'total_deletions': Jami o'chirilgan satrlar.
                - 'pr_details': Har bir PR uchun {title, url, files} ro'yxati.
            max_files (Optional[int]): Ko'rsatiladigan maksimal fayl soni.
                None bo'lsa — barcha o'zgargan fayllar ko'rsatiladi.
            show_full_diff (bool): True bo'lsa — patch yoki smart_context qo'shiladi.
                False bo'lsa — faqat fayl nomi va statistika ko'rsatiladi.
            use_smart_patch (bool): True bo'lsa — smart_context ustunlik qiladi.
                Agar smart_context mavjud bo'lmasa, patch bilan zaxiralash (fallback).

        Returns:
            str: AI promtiga qo'shishga tayyor formatlangan kod o'zgarishlari matn bloki.
        """
        lines = []

        files_to_show = pr_info['files_changed']
        if max_files:
            files_to_show = min(files_to_show, max_files)

        lines.append(f"📊 PR Summary:")
        lines.append(f"   PR Count: {pr_info['pr_count']}")
        lines.append(f"   Files Changed: {pr_info['files_changed']}")
        lines.append(f"   Additions: +{pr_info['total_additions']}")
        lines.append(f"   Deletions: -{pr_info['total_deletions']}")
        lines.append("")

        for pr in pr_info['pr_details']:
            lines.append(f"🔗 PR: {pr['title']}")
            lines.append(f"   URL: {pr['url']}")
            lines.append(f"   Files: {len(pr['files'])}")
            lines.append("")

            for idx, file_data in enumerate(pr['files'][:files_to_show]):
                lines.append(f"📄 File {idx + 1}: {file_data['filename']}")
                lines.append(f"   Status: {file_data['status']}")
                lines.append(f"   Changes: +{file_data['additions']} -{file_data['deletions']}")

                if show_full_diff:
                    if use_smart_patch and file_data.get('smart_context'):
                        lines.append("\n   Smart Patch (Full Context):")
                        lines.append(file_data['smart_context'])
                    elif file_data.get('patch'):
                        lines.append("\n   Patch:")
                        lines.append(file_data['patch'])

                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _clean_analysis_line(value: str) -> str:
        return (
            (value or "")
            .replace("\r", "")
            .replace("**", "")
            .replace("`", "")
            .strip()
        )

    def _classify_analysis_section_key(self, title: str) -> str:
        normalized = self._clean_analysis_line(title).lower()
        for marker, key in _ANALYSIS_TITLE_TO_KEY.items():
            if marker in normalized:
                return key
        return "other"

    def _split_analysis_sections(self, analysis: str) -> List[TZPRAnalysisSection]:
        sections: List[TZPRAnalysisSection] = []
        current_title = "Tahlil"
        current_lines: List[str] = []

        def flush_section() -> None:
            nonlocal current_title, current_lines
            cleaned_lines = [self._clean_analysis_line(line) for line in current_lines]
            cleaned_lines = [line for line in cleaned_lines if line]
            key = self._classify_analysis_section_key(current_title)
            items = self._group_analysis_items(cleaned_lines)
            sections.append(
                TZPRAnalysisSection(
                    key=key,
                    title=self._clean_analysis_line(current_title) or "Tahlil",
                    lines=cleaned_lines,
                    items=items,
                    item_count=len(items),
                    empty=len(cleaned_lines) == 0,
                )
            )
            current_title = "Tahlil"
            current_lines = []

        for raw_line in (analysis or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            heading_match = re.match(r"^#{2,3}\s*(.+)$", raw_line)
            if heading_match:
                if current_lines or current_title != "Tahlil":
                    flush_section()
                current_title = heading_match.group(1) or "Tahlil"
                continue
            current_lines.append(raw_line)

        if current_lines or current_title != "Tahlil":
            flush_section()

        return [section for section in sections if section.title or section.lines]

    def _group_analysis_items(self, cleaned_lines: List[str]) -> List[str]:
        items: List[str] = []
        current: List[str] = []

        def flush_item() -> None:
            nonlocal current
            item = "\n".join(part for part in current if part).strip()
            if item:
                items.append(item)
            current = []

        for line in cleaned_lines:
            if not line:
                flush_item()
                continue

            normalized = line.lstrip()
            starts_new = bool(
                re.match(r"^[-*•]\s+", normalized)
                or re.match(r"^\d+\.\s+", normalized)
                or normalized.startswith("✅")
                or normalized.startswith("⚠️")
                or normalized.startswith("❌")
                or normalized.startswith("🐛")
                or normalized.startswith("📌")
            )
            if starts_new and current:
                flush_item()
            current.append(normalized)

        flush_item()
        return items

    def _build_structured_analysis(
            self,
            analysis: str,
            compliance_score: Optional[int],
            output_profile: str,
            figma_data: Optional[Dict],
    ) -> tuple[List[TZPRAnalysisSection], TZPRAnalysisOverview]:
        parsed_sections = self._split_analysis_sections(analysis)
        sections_by_key: Dict[str, TZPRAnalysisSection] = {}
        for section in parsed_sections:
            if section.key == "score":
                continue
            if section.key in sections_by_key:
                merged = sections_by_key[section.key]
                merged.lines.extend(section.lines)
                merged.items.extend(section.items)
                merged.item_count = len(merged.items)
                merged.empty = merged.empty and section.empty
            else:
                sections_by_key[section.key] = section

        requested_sections = self._get_visible_sections_for_profile(output_profile)
        ordered_sections: List[TZPRAnalysisSection] = []
        for key in requested_sections:
            if key == "summary":
                continue
            existing = sections_by_key.get(key)
            if existing:
                ordered_sections.append(existing)
            else:
                title = _SECTION_PROMPT_BLOCKS.get(key, "").splitlines()[0].replace("## ", "").strip() if key in _SECTION_PROMPT_BLOCKS else "Tahlil"
                if key == "figma":
                    title = "🎨 FIGMA DIZAYN MOSLIGI"
                ordered_sections.append(
                    TZPRAnalysisSection(
                        key=key,
                        title=title,
                        lines=[],
                        items=[],
                        item_count=0,
                        empty=True,
                    )
                )

        summary_section = sections_by_key.get("summary")
        summary_lines = list(summary_section.lines) if summary_section and summary_section.lines else []
        if not summary_lines:
            summary_lines = self._build_summary_lines(ordered_sections, compliance_score, figma_data)
        elif compliance_score is not None and not any("%" in line for line in summary_lines):
            summary_lines = [f"Compliance score: {compliance_score}%", *summary_lines]

        section_counts = {
            section.key: section.item_count or len(section.lines)
            for section in ordered_sections
        }
        verdict, verdict_label, verdict_reason = self._derive_verdict(
            ordered_sections,
            compliance_score,
        )
        overview = TZPRAnalysisOverview(
            verdict=verdict,
            verdict_label=verdict_label,
            verdict_reason=verdict_reason,
            summary_lines=summary_lines,
            section_counts=section_counts,
            missing_figma_access=not self._has_usable_figma_data(figma_data),
            requested_sections=requested_sections,
        )
        return ordered_sections, overview

    def _build_summary_lines(
            self,
            ordered_sections: List[TZPRAnalysisSection],
            compliance_score: Optional[int],
            figma_data: Optional[Dict],
    ) -> List[str]:
        counts = {section.key: (section.item_count or len(section.lines)) for section in ordered_sections}
        lines = []
        if compliance_score is not None:
            lines.append(f"Compliance score: {compliance_score}%")
        if counts.get("failed"):
            lines.append(f"{counts['failed']} ta bajarilmagan talab yoki gap topildi.")
        elif counts.get("partial"):
            lines.append(f"{counts['partial']} ta qisman bajarilgan talab topildi.")
        elif counts.get("completed"):
            lines.append("Asosiy talablar bajarilgan deb baholandi.")
        else:
            lines.append("AI natijasida aniq talab ro'yxati qaytmadi, lekin umumiy verdict chiqarildi.")

        if counts.get("issues"):
            lines.append(f"{counts['issues']} ta risk yoki potensial muammo qayd etildi.")

        if not self._has_usable_figma_data(figma_data):
            lines.append("Figma access bo'lmagani uchun dizayn verdicti cheklangan.")

        return lines

    def _derive_verdict(
            self,
            ordered_sections: List[TZPRAnalysisSection],
            compliance_score: Optional[int],
    ) -> tuple[str, str, str]:
        counts = {section.key: (section.item_count or len(section.lines)) for section in ordered_sections}
        if counts.get("failed"):
            return ("fail", "Need Work", f"{counts['failed']} ta bajarilmagan talab bor")
        if counts.get("partial") or counts.get("issues"):
            total_partial = counts.get("partial", 0) + counts.get("issues", 0)
            return ("partial", "Partial", f"{total_partial} ta ochiq nuqta yoki risk bor")
        if compliance_score is not None:
            if compliance_score >= 80:
                return ("pass", "Ready", "Asosiy talablar mos deb topildi")
            if compliance_score >= 60:
                return ("partial", "Review", "Moslik o'rtacha, qo'shimcha tekshiruv kerak")
        return ("pass", "Ready", "Kritik nomoslik topilmadi")

    def _extract_compliance_score(self, analysis: str) -> Optional[int]:
        """
        AI javob matnidan moslik balini ajratib olish — 4 bosqichli regex strategiyasi.

        AI modeli har doim bir xil formatda javob bermaydi. Shuning uchun bu funksiya
        to'rtta turli regex pattern'ni ketma-ket sinab ko'radi va birinchi mos
        kelganidan balini qaytaradi.

        Regex strategiyalari (tartib bilan):
            1. Oddiy format: ``COMPLIANCE_SCORE: 85%``
            2. Bold format:  ``**COMPLIANCE_SCORE: 85%**``
            3. Bo'lim sarlavhasi: ``MOSLIK BALI`` dan keyin birinchi foiz raqam.
            4. Zaxira: ``compliance``, ``bali``, ``score`` yoki ``moslik`` so'zidan
               30 belgidan so'ng kelgan birinchi foiz raqam.

        Agar to'rtta strategiyadan birontasi ham mos kelmasa, None qaytariladi
        va log'ga ogohlantirish yoziladi.

        Args:
            analysis (str): AI tomonidan qaytarilgan to'liq tahlil matni.

        Returns:
            Optional[int]: 0-100 oralig'idagi moslik bali (masalan: 87).
                Agar hech qaysi pattern mos kelmasa — None.

        Note:
            Barcha pattern'lar case-insensitive (re.IGNORECASE) rejimida ishlatiladi.
            Xatolik bo'lsa (masalan: bo'sh string) — exception ushlanib, None qaytariladi.
        """
        try:
            # Try format: COMPLIANCE_SCORE: XX%
            match = re.search(r'COMPLIANCE_SCORE:\s*(\d+)%', analysis, re.IGNORECASE)
            if match:
                return int(match.group(1))

            # Try format: **COMPLIANCE_SCORE: XX%**
            match = re.search(r'\*\*COMPLIANCE_SCORE:\s*(\d+)%\*\*', analysis, re.IGNORECASE)
            if match:
                return int(match.group(1))

            # Try to find "MOSLIK BALI" section with score
            match = re.search(r'(?:MOSLIK BALI|MOSLIK BALI)[\s\S]*?(\d+)%', analysis, re.IGNORECASE)
            if match:
                return int(match.group(1))

            # Last resort: "MOSLIK BALI" yoki "Statistika" bo'limidan tashqari
            # COMPLIANCE yoki "bali" so'zi yonida turgan foizni qidirish
            match = re.search(r'(?:compliance|bali|score|moslik)[\s\S]{0,30}?(\d+)%', analysis, re.IGNORECASE)
            if match:
                return int(match.group(1))
        except Exception as e:
            log.log_error("UNKNOWN", "Score extraction", str(e))

        # If not found, log warning
        log.warning("COMPLIANCE_SCORE not found in AI response!")
        log.debug(f"AI Response preview: {analysis[:500]}...")

        return None

    def _log_smart_patch_status(self, use_smart_patch: bool, update_status):
        """Log Smart Patch availability"""
        if use_smart_patch:
            if SMART_PATCH_AVAILABLE:
                update_status("info", "Smart Patch: Enabled (full context mode)")
            else:
                update_status("warning", "Smart Patch: Not available (using standard diff)")

    def _create_error_result(
            self,
            task_key: str,
            error_message: str,
            tz_content: str = "",
            task_summary: str = "",
            pr_info: Optional[Dict] = None,
            warnings: Optional[List[str]] = None,
            figma_data: Optional[Dict] = None,
            status_banner: Optional[Dict] = None,
            ai_retry_count: int = 0,
            files_analyzed: int = 0,
            total_prompt_size: int = 0,
    ) -> TZPRAnalysisResult:
        """Create error result"""
        return TZPRAnalysisResult(
            task_key=task_key,
            task_summary=task_summary,
            tz_content=tz_content,
            pr_count=pr_info['pr_count'] if pr_info else 0,
            files_changed=pr_info['files_changed'] if pr_info else 0,
            pr_details=pr_info['pr_details'] if pr_info else [],
            success=False,
            error_message=error_message,
            warnings=warnings or [],
            figma_data=figma_data,
            status_banner=status_banner,
            ai_retry_count=ai_retry_count,
            files_analyzed=files_analyzed,
            total_prompt_size=total_prompt_size,
        )
