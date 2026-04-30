# services/testcase_generator_service.py
"""
Test Case Generator Service with Smart Patch & Custom Context Support

OPTIMIZED VERSION:
- BaseService'dan meros oladi
- PRHelper ishlatadi (Smart Patch bilan)
- TZHelper ishlatadi
- Custom Context support (AI ga qo'shimcha buyruq)
- Kod dublikatsiyasi yo'q

Author: JASUR TURGUNOV
Version: 6.0 CUSTOM CONTEXT
"""
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
import json

# Core imports
from core import BaseService, PRHelper, PRNotMergedError, TZHelper
from core.logger import get_logger

log = get_logger("testcase.gen")


@dataclass
class TestCase:
    """Test case structure"""
    id: str
    title: str
    description: str
    preconditions: str
    steps: List[str]
    expected_result: str
    test_type: str
    priority: str
    severity: str
    tags: List[str] = field(default_factory=list)


@dataclass
class TestCaseGenerationResult:
    """Test case generation natijasi"""
    task_key: str
    task_summary: str
    test_cases: List[TestCase] = field(default_factory=list)
    tz_content: str = ""
    pr_count: int = 0
    files_changed: int = 0
    pr_details: List[Dict] = field(default_factory=list)  # PR details for Code Changes tab
    task_full_details: Dict = field(default_factory=dict)
    task_overview: str = ""
    comment_changes_detected: bool = False
    comment_summary: str = ""
    comment_details: List[str] = field(default_factory=list)
    total_test_cases: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_priority: Dict[str, int] = field(default_factory=dict)
    success: bool = True
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)
    custom_context_used: bool = False


class TestCaseGeneratorService(BaseService):
    """
    Test Case Generator Service

    REFACTORED VERSION with Smart Patch & Custom Context:
    - BaseService'dan meros oladi
    - PRHelper ishlatadi (Smart Patch bilan)
    - TZHelper ishlatadi
    - Custom Context support
    - Kod dublikatsiyasi yo'q
    """

    def __init__(self, company_id: int = None, user_id: int = None):
        """Initialize service.
        UI modullar: user_id bilan yarating (user_credentials ishlatadi).
        Webhook:     company_id bilan yarating (company_settings ishlatadi).
        """
        super().__init__(company_id=company_id, user_id=user_id)
        self._pr_helper = None

    def _get_settings(self):
        """User yoki kompaniya Testcase sozlamalarini qaytarish.
        UI (user_id bor): testcase_generator — user-specific settings
        Webhook (faqat company_id): webhook_testcase — kompaniya webhook settings
        """
        if self._user_id is not None and self._company_id is not None:
            from config.app_settings import get_app_settings_for_user
            return get_app_settings_for_user(self._user_id, self._company_id).testcase_generator
        if self._company_id is not None:
            from config.app_settings import get_app_settings_for_company
            return get_app_settings_for_company(self._company_id).webhook_testcase
        from config.app_settings import get_app_settings
        return get_app_settings().testcase_generator

    @property
    def pr_helper(self):
        """Lazy PR Helper"""
        if self._pr_helper is None:
            self._pr_helper = PRHelper(self.github)
        return self._pr_helper

    def generate_test_cases(
            self,
            task_key: str,
            include_pr: bool = True,
            use_smart_patch: bool = True,
            test_types: List[str] = None,
            custom_context: str = "",
            status_callback: Optional[Callable[[str, str], None]] = None,
            dev_objections: Optional[List[Dict]] = None
    ) -> TestCaseGenerationResult:
        """
        Testcase generation — asosiy funksiya (6 bosqichli pipeline).

        Bu funksiya JIRA task TZ va GitHub PR ma'lumotlari asosida
        Google Gemini AI yordamida test case'lar yaratadi va
        ``TestCaseGenerationResult`` sifatida qaytaradi.

        Ishlash bosqichlari:
            1. JIRA'dan task tafsilotlarini olish (summary, TZ, description, comments).
            2. TZHelper orqali TZ matnini formatlash va comment tahlilini bajarish.
            3. GitHub'dan PR ma'lumotlarini olish — ``include_pr=True`` bo'lsa
               ``PRHelper.get_pr_full_info()`` chaqiriladi (Smart Patch bilan).
               PR topilmasa — TZ-only rejimga o'tish (fallback), warning saqlanadi.
            4. ``TZHelper.create_task_overview()`` orqali task umumiy tavsifi yaratiladi.
            5. ``_generate_with_ai()`` orqali Gemini AI ga prompt yuboriladi va
               xom JSON javob olinadi.
            6. ``_parse_test_cases()`` orqali xom JSON dan ``TestCase`` ro'yxati
               ajratib olinadi va statistika hisoblanadi.

        Custom context (qo'shimcha kontekst):
            ``custom_context`` bo'sh bo'lmasa, u prompt ichiga alohida bo'lim
            sifatida kiritiladi va AI ga ``MUHIM: ishlat`` ko'rsatmasi beriladi.
            Bu QA muhandisga product nomlari, narxlar, chegirmalar kabi
            domainга xos ma'lumotlarni AI ga berish imkonini yaratadi.

        PR topilmasa nima bo'ladi (fallback):
            - ``pr_info = None`` qoladi
            - ``warnings`` ro'yxatiga xabar qo'shiladi
            - AI faqat TZ asosida ishlaydi (``include_pr=False`` bilan ekvivalent)
            - ``TestCaseGenerationResult.pr_count = 0``

        Args:
            task_key: JIRA task identifikatori (masalan: DEV-1234).
            include_pr: True bo'lsa GitHub PR ma'lumotlari olinadi.
                False bo'lsa — faqat TZ asosida ishlaydi (tezroq, PR-siz).
            use_smart_patch: True bo'lsa PRHelper Smart Patch algoritmini
                ishlatadi — katta PR'larda faqat muhim o'zgarishlar olinadi.
            test_types: Yaratilishi kerak bo'lgan test turlari ro'yxati.
                Masalan: ``['positive', 'negative', 'boundary']``.
                Default: ``['positive', 'negative']``.
            custom_context: Foydalanuvchidan qo'shimcha kontekst matni.
                Masalan: ``'Mahsulot: Anor Premium. Narx: 50000 so'm. Chegirma: 20%'``.
                Bo'sh string bo'lsa e'tiborga olinmaydi.
            status_callback: Har bir bosqich tugaganda chaqiriladigan callback.
                Imzosi: ``(status: str, message: str) -> None``.

        Returns:
            TestCaseGenerationResult: Natija ob'ekti quyidagilarni o'z ichiga oladi:
                - ``test_cases``: ``TestCase`` ob'ektlari ro'yxati
                - ``total_test_cases``: yaratilgan test case'lar soni
                - ``by_type``: test turi bo'yicha statistika (masalan: ``{'positive': 3}``)
                - ``by_priority``: prioritet bo'yicha statistika
                - ``pr_count``, ``files_changed``: PR statistikasi
                - ``tz_content``: ishlatilgan TZ matni
                - ``success``: True agar muvaffaqiyatli
                - ``error_message``: xato bo'lsa tavsif
                - ``warnings``: ogohlantirish xabarlari ro'yxati
                - ``custom_context_used``: custom_context ishlatilganmi
        """
        # Status updater (BaseService'dan)
        update_status = self._create_status_updater(status_callback)

        try:
            if not test_types:
                test_types = ['positive', 'negative']

            import time as _time
            _t0 = _time.time()

            # 1. JIRA dan task olish
            log.info(f"[{task_key}] Testcase ▶ JIRA task olinmoqda...")
            update_status("progress", "JIRA task ma'lumotlari olinmoqda...")
            task_details = self.jira.get_task_details(task_key)
            if not task_details:
                return TestCaseGenerationResult(
                    task_key=task_key,
                    task_summary="",
                    success=False,
                    error_message=f"{task_key} topilmadi"
                )

            from config.app_settings import get_app_settings
            from utils.pr_cache import (
                get_skip_cache, get_pr_exists_cache, get_pr_merged_cache, get_pr_cache
            )

            # 2. Skip cache o'qish — AI_SKIP topilganmi?
            skip_detected = get_skip_cache(task_key)

            # 3. PR check (skip bo'lmasa)
            warnings = []
            pr_info = None
            pr_details_list = []

            if skip_detected:
                # AI_SKIP topilgan — PR check o'tkazib yuboriladi
                log.info(f"[{task_key}] skip_cache=True → PR check o'tkazib yuborildi")
            elif include_pr:
                # skip yo'q — PR bor/merged natijasini cache dan olamiz
                pr_exists = get_pr_exists_cache(task_key)
                pr_merged = get_pr_merged_cache(task_key)

                if pr_exists is False:
                    return TestCaseGenerationResult(
                        task_key=task_key,
                        task_summary=task_details.get('summary', ''),
                        success=False,
                        error_message="Bu task uchun PR topilmadi (JIRA va GitHub'da)",
                    )
                if pr_merged is False:
                    return TestCaseGenerationResult(
                        task_key=task_key,
                        task_summary=task_details.get('summary', ''),
                        success=False,
                        error_message="❌ PR merged emas. Faqat 'merged' statusdagi PR'lar qabul qilinadi.",
                    )

                # Cache dan PR info olish (Servis-1 saqlagan)
                pr_info = get_pr_cache(task_key)
                if pr_info:
                    log.info(f"[{task_key}] PR cache dan foydalanildi (Servis-1 topgan, qayta qidirilmadi)")
                else:
                    # Cache yo'q (faqat Servis-2 standalone ishlayotgan holat)
                    try:
                        pr_info = self.pr_helper.get_pr_full_info(
                            task_key,
                            task_details,
                            status_callback,
                            use_smart_patch=use_smart_patch
                        )
                    except PRNotMergedError as e:
                        log.warning(f"[{task_key}] PR merged emas: {e}")
                        return TestCaseGenerationResult(
                            task_key=task_key,
                            task_summary=task_details.get('summary', ''),
                            success=False,
                            error_message=str(e),
                        )
                    except Exception as pr_e:
                        log.warning(f"[{task_key}] PR fetch xatosi: {pr_e}")
                        pr_info = None

                if pr_info:
                    pr_details_list = pr_info.get('pr_details', [])
                    log.info(f"[{task_key}] Testcase ✅ PR ma'lumot olindi ({pr_info.get('files_changed', 0)} fayl)")
                else:
                    warnings.append(
                        "PR ma'lumoti topilmadi yoki olishda xato yuz berdi. "
                        "Test case'lar faqat TZ asosida yaratilgan."
                    )
                    log.warning(f"[{task_key}] Testcase ⚠ PR topilmadi — TZ asosida davom etilmoqda")
                    update_status("warning", "PR topilmadi, TZ asosida davom etilmoqda...")

            # 4. TZ uzunlik tekshiruvi
            tc_settings = self._get_settings()
            max_test_cases = tc_settings.max_test_cases
            if self._company_id is not None:
                from config.app_settings import get_app_settings_for_company
                min_tz_chars = get_app_settings_for_company(self._company_id).webhook_tz_pr.min_tz_description_chars
            else:
                from config.app_settings import get_app_settings
                min_tz_chars = get_app_settings().tz_pr_checker.min_tz_description_chars
            if min_tz_chars > 0 and self._is_tz_absent_or_minimal(task_details, min_tz_chars):
                actual_chars = len((task_details.get('description') or '').strip())
                msg = (
                    f"TZ yetarli emas. "
                    f"(mavjud: {actual_chars} belgi, min: {min_tz_chars} belgi). Servis-2 to'xtatildi."
                )
                return TestCaseGenerationResult(
                    task_key=task_key,
                    task_summary=task_details['summary'],
                    task_full_details=task_details,
                    success=False,
                    error_message=msg
                )

            # 5. TZ va Comment tahlili
            log.info(f"[{task_key}] Testcase ▶ TZ formatlanyapti...")
            update_status("progress", "TZ va comment'lar tahlil qilinmoqda...")
            if not tc_settings.read_comments_enabled:
                task_no_comments = dict(task_details)
                task_no_comments['comments'] = []
                tz_content, comment_analysis = TZHelper.format_tz_with_comments(task_no_comments)
            else:
                max_c = tc_settings.max_comments_to_read if tc_settings.max_comments_to_read > 0 else None
                tz_content, comment_analysis = TZHelper.format_tz_with_comments(
                    task_details, max_comments=max_c
                )
            log.info(f"[{task_key}] Testcase ✅ TZ formatlandi ({len(tz_content)} belgi)")

            # 6. Overview yaratish
            log.info(f"[{task_key}] Testcase ▶ Overview yaratilmoqda...")
            overview = TZHelper.create_task_overview(
                task_details,
                comment_analysis,
                pr_info
            )

            log.info(f"[{task_key}] Testcase ▶ AI ga so'rov yuborilmoqda (test turlari: {test_types})...")
            update_status("progress", "AI test case'lar yaratmoqda...")
            ai_result = self._generate_with_ai(
                task_key=task_key,
                task_details=task_details,
                tz_content=tz_content,
                comment_analysis=comment_analysis,
                pr_info=pr_info,
                test_types=test_types,
                custom_context=custom_context,
                max_test_cases=max_test_cases,
                dev_objections=dev_objections or []
            )

            if not ai_result['success']:
                return TestCaseGenerationResult(
                    task_key=task_key,
                    task_summary=task_details['summary'],
                    task_full_details=task_details,
                    task_overview=overview,
                    success=False,
                    error_message=ai_result['error']
                )

            _ai_sek = round(_time.time() - _t0, 1)
            log.info(f"[{task_key}] Testcase ✅ AI javob olindi ({_ai_sek}s), parse qilinmoqda...")

            # 6. Test case'larni parse qilish
            test_cases = self._parse_test_cases(ai_result['raw_response'])

            if not test_cases:
                log.warning(
                    f"[{task_key}] AI javob parse'da 0 test case. Raw response (2000 char): {ai_result['raw_response'][:2000]}"
                )

            # Statistika
            by_type = {}
            by_priority = {}
            for tc in test_cases:
                by_type[tc.test_type] = by_type.get(tc.test_type, 0) + 1
                by_priority[tc.priority] = by_priority.get(tc.priority, 0) + 1

            _total_sek = round(_time.time() - _t0, 1)
            log.info(f"[{task_key}] Testcase ✅ {len(test_cases)} ta test case yaratildi | jami: {_total_sek}s | {by_type}")

            return TestCaseGenerationResult(
                task_key=task_key,
                task_summary=task_details['summary'],
                test_cases=test_cases,
                tz_content=tz_content,
                pr_count=pr_info['pr_count'] if pr_info else 0,
                files_changed=pr_info['files_changed'] if pr_info else 0,
                pr_details=pr_details_list,  # PR details for Code Changes tab
                task_full_details=task_details,
                task_overview=overview,
                comment_changes_detected=comment_analysis['has_changes'],
                comment_summary=comment_analysis['summary'],
                comment_details=comment_analysis.get('important_comments', []),
                total_test_cases=len(test_cases),
                by_type=by_type,
                by_priority=by_priority,
                success=True,
                warnings=warnings,
                custom_context_used=bool(custom_context)
            )

        except Exception as e:
            import traceback
            log.log_error(task_key, "generate_test_cases", traceback.format_exc())
            return TestCaseGenerationResult(
                task_key=task_key,
                task_summary="",
                success=False,
                error_message=str(e)
            )

    def _is_tz_absent_or_minimal(self, task_details: Dict, min_description_chars: int = 50) -> bool:
        """
        Taskda batafsil TZ yo'qmi yoki faqat summary bormi aniqlash.

        Description bo'sh yoki min_description_chars dan qisqa bo'lsa True.
        """
        description = task_details.get('description') or ''
        return len(description.strip()) < min_description_chars

    def _generate_with_ai(
            self,
            task_key: str,
            task_details: Dict,
            tz_content: str,
            comment_analysis: Dict,
            pr_info: Optional[Dict],
            test_types: List[str],
            custom_context: str = "",
            max_test_cases: int = 10,
            dev_objections: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Gemini AI ga prompt yuborish va xom javobni qaytarish.

        Bu metod ``generate_test_cases()`` pipeline'ining 5-bosqichi:
        prompt yaratiladi → matn hajmi tekshiriladi → AI chaqiriladi.

        Prompt yaratish:
            ``_create_test_case_prompt()`` chaqiriladi — barcha parametrlar
            u yerga uzatiladi. Prompt TZ, comment tahlili, PR ma'lumoti va
            custom context bo'limlarini o'z ichiga oladi.

        Matn hajmi tekshiruvi:
            ``BaseService._calculate_text_length()`` orqali prompt token hajmi
            aniqlanadi. Agar limit oshilgan bo'lsa ``BaseService._truncate_text()``
            orqali prompt qisqartiriladi — bu Gemini kontekst limitiga sig'ish
            uchun zarur.

        AI chaqiruvi:
            ``self.gemini.analyze(prompt, max_output_tokens=...)`` chaqiriladi.
            ``max_output_tokens`` ``app_settings.testcase_generator.ai_max_output_tokens``
            dan olinadi — bu JSON truncation (kesilish) xatosini oldini oladi.

        Args:
            task_key: JIRA task identifikatori (log uchun).
            task_details: JIRA task to'liq ma'lumotlari (summary, type, priority).
            tz_content: Formatlangan TZ matni.
            comment_analysis: ``TZHelper.format_tz_with_comments()`` natijasi
                (``has_changes``, ``summary``, ``important_comments``).
            pr_info: ``PRHelper.get_pr_full_info()`` natijasi yoki None.
            test_types: Yaratilishi kerak bo'lgan test turlari.
            custom_context: Foydalanuvchi qo'shimcha matni (bo'sh bo'lishi mumkin).
            max_test_cases: AI yaratishi mumkin bo'lgan maksimal test case soni.

        Returns:
            Dict: Ikki kalitli lug'at:
                - Muvaffaqiyatli holda:
                    ``{'success': True, 'raw_response': '<AI xom JSON javobi>'}``
                - Xato holda:
                    ``{'success': False, 'error': 'AI xatosi: <sabab>'}``
        """
        try:
            import time as _time

            prompt = self._create_test_case_prompt(
                task_key=task_key,
                task_details=task_details,
                tz_content=tz_content,
                comment_analysis=comment_analysis,
                pr_info=pr_info,
                test_types=test_types,
                custom_context=custom_context,
                max_test_cases=max_test_cases,
                dev_objections=dev_objections or []
            )

            # Text hajmini tekshirish (BaseService'dan)
            text_info = self._calculate_text_length(prompt)
            prompt_chars = len(prompt)
            prompt_k_tokens = round(prompt_chars / 4000, 1)
            log.info(f"[{task_key}] AI prompt: {prompt_chars:,} belgi (~{prompt_k_tokens}K token) | limit: {'✅' if text_info['within_limit'] else '⚠ oshdi, qisqartiriladi'}")

            if not text_info['within_limit']:
                prompt = self._truncate_text(prompt)
                log.info(f"[{task_key}] AI prompt qisqartirildi → {len(prompt):,} belgi")

            # AI chaqirish (max_output_tokens — truncation oldini olish uchun)
            max_tokens = self._get_settings().ai_max_output_tokens
            log.info(f"[{task_key}] AI ▶ Gemini.generate_content() chaqirildi (max_tokens={max_tokens})...")
            _t_ai = _time.time()
            response = self.gemini.analyze(prompt, max_output_tokens=max_tokens)
            _ai_dur = round(_time.time() - _t_ai, 1)
            log.info(f"[{task_key}] AI ✅ Gemini javob olindi: {_ai_dur}s | javob: {len(response):,} belgi")

            return {
                'success': True,
                'raw_response': response
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"AI xatosi: {str(e)}"
            }

    def _create_test_case_prompt(
            self,
            task_key: str,
            task_details: Dict,
            tz_content: str,
            comment_analysis: Dict,
            pr_info: Optional[Dict],
            test_types: List[str],
            custom_context: str = "",
            max_test_cases: int = 10,
            dev_objections: Optional[List[Dict]] = None
    ) -> str:
        """
        Gemini AI uchun testcase generation promptini yig'ish.

        Prompt dinamik ravishda bo'limlardan tuziladi — ba'zi bo'limlar
        faqat ma'lumot mavjud bo'lganda kiritiladi:

        Har doim kiritilgan bo'limlar:
            1. TASK MA'LUMOTLARI — task_key, summary, type, priority.
            2. TEXNIK TOPSHIRIQ (TZ) — ``tz_content`` to'liq matni.
            3. TEST CASE TALABLARI — test turlari va sifat ko'rsatmalari.
            4. JAVOB FORMATI (JSON) — AI javob strukturasi namunasi.

        Shartli bo'limlar (mavjud bo'lganda qo'shiladi):
            - QO'SHIMCHA MA'LUMOTLAR: ``custom_context`` bo'sh bo'lmasa,
              alohida bo'lim sifatida kiritiladi. AI ga ``ALBATTA ishlat``
              ko'rsatmasi beriladi — product nomlari, narxlar, domenga xos
              ma'lumotlar test datalarida aks ettiriladi.
            - MUHIM: COMMENT'LARDA O'ZGARISHLAR: ``comment_analysis['has_changes']``
              True bo'lsa, comment tahlili kiritiladi.
            - KOD O'ZGARISHLARI: ``pr_info`` mavjud bo'lsa, PR statistikasi
              (PR soni, fayl soni, qo'shilgan/o'chirilgan qatorlar) kiritiladi.

        Prompt formati:
            - O'zbek tilida yoziladi (AI javobi ham O'zbek tilida bo'ladi)
            - Unicode vizual ajratgichlar (═══) bo'limlar chegarasini belgilaydi
            - JSON namunasi ``{{}}`` escape bilan f-string ichida beriladi
            - ``max_test_cases`` va ``len(test_types)`` dinamik kiritiladi

        Args:
            task_key: JIRA task identifikatori (prompt sarlavhasida ko'rsatiladi).
            task_details: JIRA task ma'lumotlari (summary, type, priority kerak).
            tz_content: Formatlangan TZ matni (prompt markaziy bo'limi).
            comment_analysis: Comment tahlili natijasi.
            pr_info: PR ma'lumotlari lug'ati yoki None.
            test_types: Yaratilishi kerak bo'lgan test turlari ro'yxati.
            custom_context: Foydalanuvchi qo'shimcha matni (bo'sh bo'lsa bo'lim qo'shilmaydi).
            max_test_cases: Maksimal test case soni (prompt ichiga kiritiladi).

        Returns:
            str: Gemini AI ga yuborish uchun tayyor prompt matni.
        """
        # Test types description
        test_types_desc = {
            'positive': 'To\'g\'ri ma\'lumotlar bilan ishlash',
            'negative': 'Noto\'g\'ri ma\'lumotlar, xato holatlar',
            'boundary': 'Limit qiymatlari (min/max)',
            'edge': 'Maxsus/chekka holatlar',
            'integration': 'Tizim integratsiyasi',
            'regression': 'Regression testing'
        }

        types_text = ', '.join([f"{t} ({test_types_desc.get(t, t)})" for t in test_types])

        # Bo'limlar matni (sozlamadagi tartib bo'yicha — servis qat'iy amal qiladi)
        tz_block = f"""
═══════════════════════════════════════════════════════════════════════════════
📝 TEXNIK TOPSHIRIQ (TZ)
═══════════════════════════════════════════════════════════════════════════════

{tz_content}
"""
        comments_block = ""
        if comment_analysis['has_changes']:
            comments_block = f"""
═══════════════════════════════════════════════════════════════════════════════
⚠️ MUHIM: COMMENT'LARDA O'ZGARISHLAR ANIQLANDI
═══════════════════════════════════════════════════════════════════════════════

{comment_analysis['summary']}

Comment'lardagi o'zgarishlar test case'larda ALBATTA hisobga olinishi kerak!
"""
        custom_context_block = ""
        if custom_context:
            custom_context_block = f"""
═══════════════════════════════════════════════════════════════════════════════
💬 QO'SHIMCHA MA'LUMOTLAR (FOYDALANUVCHIDAN)
═══════════════════════════════════════════════════════════════════════════════

{custom_context}

⚠️ **MUHIM:** Yuqoridagi qo'shimcha ma'lumotlarni test case'larda ALBATTA ishlatish kerak!
- Product nomlari, narxlar va boshqa ma'lumotlarni test datalarida ishlating
- Chegirmalar, limitlar va maxsus shartlarni test scenario'larda qamrab oling
- Foydalanuvchi aytgan barcha narsalarni hisobga oling
"""
        dev_objections_block = ""
        if dev_objections:
            objection_lines = []
            for c in dev_objections:
                author = c.get('author', 'Dev')
                created = c.get('created', '')[:10]
                body = c.get('body', '').strip()
                objection_lines.append(f"  • {author} ({created}): {body}")
            objections_text = "\n".join(objection_lines)
            dev_objections_block = f"""
═══════════════════════════════════════════════════════════════════════════════
⚡ DEVELOPER ETIROZLARI (tahlildan KEYIN yozilgan)
═══════════════════════════════════════════════════════════════════════════════

{objections_text}

Ko'rsatma: Testcase'larni yozishda bu izohlarni hisobga ol.
Developer to'g'ri qayta bajargan funksiyalar uchun test yoz.
"""
        code_block = ""
        if pr_info:
            # Kod o'zgarishlari bo'limi: servis-1 dagi kabi, ammo testcase uchun qisqaroq format
            tc_settings = self._get_settings()
            max_files = getattr(tc_settings, "pr_max_files", None)

            lines = []
            lines.append("📊 PR Summary:")
            lines.append(f"   PR Count: {pr_info['pr_count']}")
            lines.append(f"   Files Changed: {pr_info['files_changed']}")
            lines.append(f"   Additions: +{pr_info['total_additions']}")
            lines.append(f"   Deletions: -{pr_info['total_deletions']}")
            lines.append("")

            files_to_show = pr_info["files_changed"]
            if max_files:
                files_to_show = min(files_to_show, max_files)

            shown_files = 0
            for pr in pr_info["pr_details"]:
                lines.append(f"🔗 PR: {pr['title']}")
                lines.append(f"   URL: {pr['url']}")
                lines.append(f"   Files: {len(pr['files'])}")
                lines.append("")

                for file_data in pr["files"]:
                    if shown_files >= files_to_show:
                        break

                    lines.append(f"📄 File: {file_data.get('filename', '')}")
                    lines.append(f"   Status: {file_data.get('status', '')}")
                    lines.append(f"   Changes: +{file_data.get('additions', 0)} -{file_data.get('deletions', 0)}")

                    smart_ctx = file_data.get("smart_context")
                    patch = file_data.get("patch")
                    if smart_ctx:
                        lines.append("")
                        lines.append("   Smart Patch (kod konteksti):")
                        lines.append(smart_ctx)
                    elif patch:
                        lines.append("")
                        lines.append("   Patch:")
                        lines.append(patch)

                    lines.append("")
                    shown_files += 1
                    if shown_files >= files_to_show:
                        break

            lines_text = "\n".join(lines)
            code_block = (
                "═══════════════════════════════════════════════════════════════════════════════\n"
                "💻 KOD O'ZGARISHLARI (PR dan olingan)\n"
                "═══════════════════════════════════════════════════════════════════════════════\n\n"
                f"{lines_text}\n\n"
                "Test case'larni yozayotganda yuqoridagi kod o'zgarishlaridagi har bir funksionalni qamrab ol.\n"
            )

        order = self._get_settings().ai_data_section_order or [
            "tz", "comments", "custom_context", "dev_objections", "code"
        ]
        sections_map = {
            "tz": tz_block,
            "comments": comments_block,
            "custom_context": custom_context_block,
            "dev_objections": dev_objections_block,
            "code": code_block,
        }
        data_sections_body_parts = []
        for key in order:
            if key not in sections_map:
                continue
            part = (sections_map[key] or "").strip()
            if part:
                data_sections_body_parts.append(part)
        data_sections_body = "\n".join(data_sections_body_parts)

        prompt = f"""
**VAZIFA:** JIRA task uchun QA test case'lar yaratish (O'ZBEK TILIDA)

═══════════════════════════════════════════════════════════════════════════════
📋 TASK MA'LUMOTLARI
═══════════════════════════════════════════════════════════════════════════════

**Task Key:** {task_key}
**Summary:** {task_details['summary']}
**Type:** {task_details['type']}
**Priority:** {task_details['priority']}

{data_sections_body}

═══════════════════════════════════════════════════════════════════════════════
🎯 TEST CASE TALABLARI
═══════════════════════════════════════════════════════════════════════════════

"""
        prompt += f"""
**Test turlari:** {types_text}

**Har bir test case uchun:**
1. TZ'dagi barcha talablarni qamrab olish
2. Comment'lardagi o'zgarishlarni hisobga olish
3. Kod o'zgarishlarini test qilish
4. Edge case'larni tekshirish
{"5. QO'SHIMCHA MA'LUMOTLARDAGI barcha shartlarni test qilish" if custom_context else ""}

**Sifat talablari:**
1. Har bir test case TO'LIQ va ANIQ bo'lishi kerak
2. Steps BATAFSIL (har bir qadam alohida)
3. Expected result ANIQ (nima kutiladi)
4. O'zbek tilida, tushunarli
5. Haqiqiy test scenario'lar (copy-paste emas!)
{"6. QO'SHIMCHA MA'LUMOTLARDAGI product nomlari va narxlarni ishlatish" if custom_context else ""}

═══════════════════════════════════════════════════════════════════════════════
📊 JAVOB FORMATI (JSON)
═══════════════════════════════════════════════════════════════════════════════

Javobni FAQAT JSON formatda bering, boshqa hech narsa yo'q:

```json
{{
  "test_cases": [
    {{
      "id": "TC-001",
      "title": "Test case nomi (qisqa va aniq)",
      "description": "Test case tavsifi (nima test qilinadi)",
      "preconditions": "Boshlang'ich shartlar (system holati, ma'lumotlar)",
      "steps": [
        "1. Birinchi qadam (batafsil)",
        "2. Ikkinchi qadam (batafsil)",
        "3. Uchinchi qadam (batafsil)"
      ],
      "expected_result": "Kutilayotgan natija (aniq)",
      "test_type": "positive/negative/boundary/edge",
      "priority": "High/Medium/Low",
      "severity": "Critical/Major/Minor",
      "tags": ["tag1", "tag2"]
    }}
  ]
}}
```

**MUHIM:**
- Kamida {len(test_types)} ta test case yarating (har bir type uchun kamida 1 ta)
- Har bir test type uchun kamida 1 ta test case
- Eng ko'pi {max_test_cases} ta test case yarating
- JSON to'g'ri formatda bo'lishi kerak
- Steps ro'yxat (list) bo'lishi kerak
- Har bir step alohida element
{"- QO'SHIMCHA MA'LUMOTLARDAGI ma'lumotlarni test data sifatida ishlating" if custom_context else ""}

Endi {len(test_types)} xil test ({types_text}) uchun test case'lar yarating!
"""

        return prompt

    def _parse_test_cases(self, raw_response: str) -> List[TestCase]:
        """
        AI xom javobidan JSON ajratib olish va ``TestCase`` ob'ektlarini yaratish.

        Parse bosqichlari:
            1. Xom javobdan birinchi ``{`` va oxirgi ``}`` orasidagi JSON
               qismi kesib olinadi (markdown blok, ortiqcha matn filtirlanadi).
            2. ``json.loads()`` bilan parse qilinadi.
            3. Test case ro'yxati quyidagi kalitlardan biri orqali topiladi
               (alias qidirish): ``test_cases`` → ``testCases`` → ``tests``
               → ``test_case_list``.
            4. Har bir test case lug'atidan ``TestCase`` dataclass ob'ekti
               yaratiladi.

        JSON parse xatosi bo'lsa (repair rejimi):
            Agar ``json.loads()`` ``JSONDecodeError`` ko'tarsa —
            ``_try_repair_json()`` chaqiriladi. Muvaffaqiyatli bo'lsa
            repaired JSON qayta parse qilinadi va test case'lar tiklangan
            miqdorda qaytariladi.

        Maydonlar uchun default qiymatlar:
            Har bir maydon uchun ``.get(key, default)`` ishlatiladi —
            agar AI javobida maydon bo'lmasa xato ko'tarilmaydi:
            - ``id`` → ``'TC-XXX'``
            - ``test_type`` → ``'positive'``
            - ``priority`` → ``'Medium'``
            - ``severity`` → ``'Major'``
            - ``steps``, ``tags`` → bo'sh ro'yxat

        Args:
            raw_response: AI dan kelgan xom matn (JSON yoki JSON + boshqa matn).

        Returns:
            List[TestCase]: Muvaffaqiyatli parse qilingan test case'lar ro'yxati.
                Xato bo'lsa — bo'sh ro'yxat qaytadi (exception ko'tarilmaydi).
        """
        test_cases = []

        try:
            # JSON'ni extract qilish
            json_start = raw_response.find('{')
            json_end = raw_response.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                log.warning("JSON topilmadi!")
                return []

            json_str = raw_response[json_start:json_end]
            json_str = self._sanitize_json_escapes(json_str)

            # Parse
            data = json.loads(json_str)

            # Test case'larni yaratish (aliaslar ile qidirish)
            tc_list = (
                data.get('test_cases')
                or data.get('testCases')
                or data.get('tests')
                or data.get('test_case_list')
                or []
            )

            if not tc_list:
                log.warning(
                    f"JSON parse OK, lekin test case kaidi topilmadi. "
                    f"Mavjud kaidlar: {list(data.keys())} | Raw response (2000 char): {raw_response[:2000]}"
                )

            for tc_data in tc_list:
                try:
                    test_case = TestCase(
                        id=tc_data.get('id', 'TC-XXX'),
                        title=tc_data.get('title', ''),
                        description=tc_data.get('description', ''),
                        preconditions=tc_data.get('preconditions', ''),
                        steps=tc_data.get('steps', []),
                        expected_result=tc_data.get('expected_result', ''),
                        test_type=tc_data.get('test_type', 'positive'),
                        priority=tc_data.get('priority', 'Medium'),
                        severity=tc_data.get('severity', 'Major'),
                        tags=tc_data.get('tags', [])
                    )
                    test_cases.append(test_case)
                except Exception as e:
                    log.warning(f"Test case parse xatosi: {e}")
                    continue

        except json.JSONDecodeError as e:
            log.json_parse_error("UNKNOWN", f"JSON parse xatosi: {e}")
            log.json_repair_attempt("UNKNOWN")

            # Truncated JSON ni tuzatishga urinish
            repaired = self._try_repair_json(json_str)
            if repaired:
                try:
                    data = json.loads(repaired)
                    tc_list = (
                        data.get('test_cases')
                        or data.get('testCases')
                        or data.get('tests')
                        or data.get('test_case_list')
                        or []
                    )
                    for tc_data in tc_list:
                        try:
                            test_case = TestCase(
                                id=tc_data.get('id', 'TC-XXX'),
                                title=tc_data.get('title', ''),
                                description=tc_data.get('description', ''),
                                preconditions=tc_data.get('preconditions', ''),
                                steps=tc_data.get('steps', []),
                                expected_result=tc_data.get('expected_result', ''),
                                test_type=tc_data.get('test_type', 'positive'),
                                priority=tc_data.get('priority', 'Medium'),
                                severity=tc_data.get('severity', 'Major'),
                                tags=tc_data.get('tags', [])
                            )
                            test_cases.append(test_case)
                        except Exception as parse_err:
                            log.warning(f"Repaired test case parse xatosi: {parse_err}")
                            continue
                    log.json_repair_success("UNKNOWN", f"{len(test_cases)} ta test case tiklandi")
                except json.JSONDecodeError:
                    log.json_parse_error("UNKNOWN", "Truncated JSON tuzatib bo'lmadi")
                    log.warning(f"Response: {raw_response[:500]}")
            else:
                log.json_parse_error("UNKNOWN", "JSON repair imkonsiz")
                log.warning(f"Response: {raw_response[:500]}")

        except Exception as e:
            log.warning(f"Parse xatosi: {e}")

        log.info(f"Parse natija: {len(test_cases)} ta test case")
        return test_cases

    @staticmethod
    def _sanitize_json_escapes(s: str) -> str:
        """JSON da noto'g'ri \\escape larni tuzatish.

        AI Kirill yoki boshqa maxsus harflar oldiga backslash qo'yganda
        (masalan \\е, \\и) JSON.loads xato beradi. Bunday backslash'lar
        doubled (\\\\) qilinadi — JSON da literal backslash sifatida o'qiladi.

        Saqlanadi: \\" \\\\ \\/ \\b \\f \\n \\r \\t \\uXXXX
        """
        import re
        return re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', s)

    def _try_repair_json(self, broken_json: str) -> Optional[str]:
        """
        Yarim kesilgan (truncated) JSON ni tiklab, to'liq va yaroqli holga keltirish.

        Kesilish sababi:
            Gemini AI ``max_output_tokens`` limitiga yetganda javobni o'rtada
            to'xtatadi. Bu holda JSON strukturasi yarim holda qoladi:
            oxirgi test case tugallanmagan, yopilmagan ``[`` yoki ``{`` qoladi.

        Tuzatish strategiyalari (ketma-ket uriniladi):

            1-urinish (rfind ``},`` metodi):
                Oxirgi to'liq test case obyektini topish uchun ``},`` izlanadi —
                bu array ichida bir test case tugab, keyingisi boshlanayotgan joy.
                O'sha nuqtagacha kesib, ochilmagan ``[`` va ``{`` bracket'larni
                sanab yopiladi. Natija JSON ga parse qilinib tekshiriladi.

            2-urinish (oxirgi ``}`` metodi):
                Agar 1-urinish muvaffaqiyatsiz bo'lsa, eng oxirgi ``}``
                topiladi va undan keyin kesish amalga oshiriladi.
                Xuddi shunday bracket'lar yopiladi va parse tekshiriladi.

        Bracket balanslashtirish:
            ``open_brackets = str.count('[') - str.count(']')``
            ``open_braces   = str.count('{') - str.count('}'')``
            Kamchilikcha yopilmagan har bir bracket uchun yopuvchi belgi qo'shiladi.

        Args:
            broken_json: Yarim kesilgan JSON matni (bo'sh bo'lishi mumkin).

        Returns:
            Optional[str]: Tuzatilgan va ``json.loads()`` dan o'tgan JSON matni.
                Agar barcha urinishlar muvaffaqiyatsiz bo'lsa — None qaytadi.
        """
        if not broken_json:
            return None

        broken_json = self._sanitize_json_escapes(broken_json)

        try:
            # 0-urinish: Sanitize shunday tuzatib qo'yganmi?
            try:
                json.loads(broken_json)
                log.info("JSON repair: 0-urinish muvaffaqiyatli (escape sanitize)")
                return broken_json
            except json.JSONDecodeError:
                pass

            # 1-urinish: Oxirgi to'liq test case obyektini topish
            #    Har bir test case "}, " bilan tugaydi (array ichida)
            last_complete = broken_json.rfind('},')
            if last_complete > 0:
                fixed = broken_json[:last_complete + 1]  # oxirgi to'liq '}' gacha

                # Yopilmagan bracket'larni hisoblash va yopish
                open_brackets = fixed.count('[') - fixed.count(']')
                open_braces = fixed.count('{') - fixed.count('}')

                fixed += ']' * open_brackets
                fixed += '}' * open_braces

                try:
                    json.loads(fixed)
                    log.info("JSON repair: 1-urinish muvaffaqiyatli (rfind method)")
                    return fixed
                except json.JSONDecodeError:
                    pass

            # 2-urinish: Oxirgi to'liq '}' ni topib, undan keyin kesish
            last_brace = broken_json.rfind('}')
            if last_brace > 0:
                fixed = broken_json[:last_brace + 1]

                open_brackets = fixed.count('[') - fixed.count(']')
                open_braces = fixed.count('{') - fixed.count('}')

                fixed += ']' * open_brackets
                fixed += '}' * open_braces

                try:
                    json.loads(fixed)
                    log.info("JSON repair: 2-urinish muvaffaqiyatli (last brace method)")
                    return fixed
                except json.JSONDecodeError:
                    pass

            log.warning("JSON repair: barcha urinishlar muvaffaqiyatsiz")
            return None

        except Exception as e:
            log.log_error("UNKNOWN", "json_repair", str(e))
            return None