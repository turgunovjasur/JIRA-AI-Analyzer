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
import os

# Core imports
from core import BaseService, PRHelper, PRNotMergedError, TZHelper
from core.analysis_policy import build_full_analysis_blocked
from core.module_preflight import ModulePreflightPolicy, run_module_preflight
from core.logger import get_logger

# Multi-agent: Agent1 (talab ajratuvchi) checker modulidan QAYTA ISHLATILADI —
# checker fayli O'ZGARTIRILMAYDI, faqat import qilinadi.
from services.checkers.tzpr_agents import agent1 as agent1_contract
from services.checkers.tzpr_preflight import (
    build_figma_access_status,
    extract_figma_requirement_candidates,
)
from services.generators.testcase_agents import agent2_testcase
from utils.ai.gemini_json import parse_gemini_json

log = get_logger("testcase.gen")

# Agent1 (talab inventarizatsiyasi) uchun output token limiti — checker bilan bir xil.
AGENT1_MAX_OUTPUT_TOKENS = 16384

# Testcase modul setup profili (STRUKTURAVIY): testcase PR ishlatmaydi.
# Tunable qiymatlar (min_tz, figma on/off, comment limiti) settings'dan keladi.
_TESTCASE_PREFLIGHT_POLICY = ModulePreflightPolicy(
    jira_fetch=True,
    min_tz_check=True,
    pr_check=False,
    figma_check=True,
    comment_fetch=True,
    tz_build=True,
)

# Har talab uchun test case chegarasi:
#  - kamida MIN (prompt ko'rsatmasi + qoplanmaganlik ogohlantirishi)
#  - ko'pi bilan MAX (deterministik trim) — 1 talabga juda ko'p test case yozilishini oldini oladi.
MIN_TC_PER_REQ = 1
MAX_TC_PER_REQ = 3


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
    # Qaysi talab(lar)ni qoplaydi (Agent2 belgilaydi: ["REQ-1", ...])
    requirement_ids: List[str] = field(default_factory=list)


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
    status_banner: Optional[Dict] = None
    ai_prompt_size: int = 0
    ai_model: str = ""
    files_analyzed: int = 0
    # Multi-agent: Agent1 ajratgan talablar va Agent2 qamrovi
    requirements: List[Dict] = field(default_factory=list)
    requirement_coverage: Dict = field(default_factory=dict)


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
        # Agent1/Agent2 uchun model fallback'li Gemini helper (lazy)
        self._agent_gemini = None

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

    def _resolve_min_tz_chars(self) -> int:
        """min_tz_description_chars — checker sozlamasidan (UI: user, webhook: company)."""
        if self._user_id is not None and self._company_id is not None:
            from config.app_settings import get_app_settings_for_user
            return get_app_settings_for_user(self._user_id, self._company_id).tz_pr_checker.min_tz_description_chars
        if self._company_id is not None:
            from config.app_settings import get_app_settings_for_company
            return get_app_settings_for_company(self._company_id).webhook_tz_pr.min_tz_description_chars
        from config.app_settings import get_app_settings
        return get_app_settings().tz_pr_checker.min_tz_description_chars

    @property
    def pr_helper(self):
        """Lazy PR Helper"""
        if self._pr_helper is None:
            self._pr_helper = PRHelper(self.github)
        return self._pr_helper

    def generate_test_cases(
            self,
            task_key: str,
            test_types: List[str] = None,
            custom_context: str = "",
            status_callback: Optional[Callable[[str, str], None]] = None,
            dev_objections: Optional[List[Dict]] = None
    ) -> TestCaseGenerationResult:
        """
        Testcase generation — 2-agentli pipeline (Agent1 → Agent2).

        Manbalar: JIRA TZ + comment + Figma. PR ISHLATILMAYDI. Natija
        ``TestCaseGenerationResult`` sifatida qaytadi.

        Ishlash bosqichlari:
            1. Shared module preflight (``run_module_preflight``): JIRA task olish,
               min TZ tekshiruvi, Figma (settingdan: "figma" ai_data_section_order da),
               TZ + comment formatlash.
            2. Agent1 (checker kontrakti) — TZ + Figma'dan talablar ro'yxati (comment YO'Q).
            3. Agent2 — talablar + TZ + comment + Figma asosida test case (bitta chaqiruv).
            4. Deterministik finalize: dedup, har talabga max 3 test case, TC-NNN qayta
               raqamlash, talab qamrovini hisoblash.

        Custom context (qo'shimcha kontekst):
            ``custom_context`` bo'sh bo'lmasa, Agent2 promtiga alohida bo'lim sifatida
            kiritiladi (product nomlari, narxlar, limitlar test datasida ishlatiladi).

        Args:
            task_key: JIRA task identifikatori (masalan: DEV-1234).
            test_types: Test turlari ro'yxati. Default: ``['positive', 'negative']``.
            custom_context: Qo'shimcha kontekst matni (bo'sh bo'lsa e'tiborga olinmaydi).
            status_callback: Har bosqichda chaqiriladigan callback ``(status, message)``.
            dev_objections: Developer etirozlari (ixtiyoriy).

        Returns:
            TestCaseGenerationResult: ``test_cases``, ``total_test_cases``, ``by_type``,
            ``by_priority``, ``tz_content``, ``requirements``, ``requirement_coverage``,
            ``success``, ``error_message``, ``warnings``, ``custom_context_used``.
        """
        # Status updater (BaseService'dan)
        update_status = self._create_status_updater(status_callback)

        try:
            if not test_types:
                test_types = ['positive', 'negative']

            import time as _time
            _t0 = _time.time()

            warnings = []
            tc_settings = self._get_settings()
            max_test_cases = tc_settings.max_test_cases
            min_tz_chars = self._resolve_min_tz_chars()
            # Figma checker kabi settingdan boshqariladi: "figma" ai_data_section_order da bo'lsa olinadi.
            figma_enabled = "figma" in (getattr(tc_settings, "ai_data_section_order", None) or [])

            # ── Umumiy setup check'lar (shared module preflight) ──
            ctx = run_module_preflight(
                self,
                task_key=task_key,
                policy=_TESTCASE_PREFLIGHT_POLICY,
                min_tz_chars=min_tz_chars,
                read_comments_enabled=tc_settings.read_comments_enabled,
                max_comments_to_read=tc_settings.max_comments_to_read,
                figma_enabled=figma_enabled,
                update_status=update_status,
            )

            # jira_fetch fail → task topilmadi (modul o'z xato natijasini qaytaradi)
            if ctx.failed("jira_fetch"):
                return TestCaseGenerationResult(
                    task_key=task_key,
                    task_summary="",
                    success=False,
                    error_message=f"{task_key} topilmadi"
                )

            task_details = ctx.task_details
            figma_data = ctx.figma_data

            # min_tz_check fail → TZ qisqa (modul o'z xato natijasini qaytaradi)
            if ctx.failed("min_tz_check"):
                msg = (
                    f"TZ yetarli emas. "
                    f"(mavjud: {ctx.tz_chars} belgi, min: {min_tz_chars} belgi). Servis-2 to'xtatildi."
                )
                return TestCaseGenerationResult(
                    task_key=task_key,
                    task_summary=task_details['summary'],
                    task_full_details=task_details,
                    success=False,
                    error_message=msg
                )

            tz_content = ctx.tz_content
            comment_analysis = ctx.comment_analysis
            overview = ctx.task_overview
            log.info(f"[{task_key}] Testcase ✅ TZ formatlandi ({len(tz_content)} belgi)")

            # 6. AGENT1 — talablar ro'yxati (checker Agent1 kontrakti qayta ishlatiladi)
            log.info(f"[{task_key}] Testcase ▶ Agent1 (talablar) ishga tushdi...")
            update_status("progress", "Talablar ajratilmoqda (Agent1)...")
            try:
                requirements = self._run_agent1_requirements(task_key, task_details, figma_data)
            except Exception as agent1_err:
                log.log_error(task_key, "agent1", str(agent1_err))
                return self._build_agent_error_result(
                    task_key, task_details, overview, f"Agent1 ishlamadi: {agent1_err}"
                )
            if not requirements:
                return self._build_agent_error_result(
                    task_key, task_details, overview,
                    "Agent1 talablar ro'yxatini ajrata olmadi (talab topilmadi)."
                )
            log.info(f"[{task_key}] Agent1 ✅ {len(requirements)} ta talab ajratildi")

            # 7. AGENT2 — talablar asosida test case (BITTA chaqiruv)
            update_status("progress", "AI test case'lar yozmoqda (Agent2)...")
            try:
                raw_response = self._run_agent2_testcases(
                    task_key=task_key,
                    task_details=task_details,
                    requirements=requirements,
                    tz_content=tz_content,
                    comment_analysis=comment_analysis,
                    figma_data=figma_data,
                    test_types=test_types,
                    custom_context=custom_context,
                    max_test_cases=max_test_cases,
                    dev_objections=dev_objections or [],
                )
            except Exception as agent2_err:
                log.log_error(task_key, "agent2", str(agent2_err))
                return self._build_agent_error_result(
                    task_key, task_details, overview, f"Agent2 ishlamadi: {agent2_err}"
                )

            _ai_sek = round(_time.time() - _t0, 1)
            log.info(f"[{task_key}] Testcase ✅ AI javob olindi ({_ai_sek}s), parse qilinmoqda...")

            # 8. Parse + deterministik finalize (dedup, qayta raqamlash, qamrov)
            test_cases = self._parse_test_cases(raw_response)
            test_cases, coverage = self._finalize_testcases(test_cases, requirements)
            if coverage.get("uncovered_ids"):
                warnings.append("Qoplanmagan talablar: " + ", ".join(coverage["uncovered_ids"]))
            if coverage.get("trimmed_over_limit"):
                warnings.append(
                    f"{coverage['trimmed_over_limit']} ta ortiqcha test case olib tashlandi "
                    f"(har talabga maksimum {MAX_TC_PER_REQ} ta)."
                )

            if not test_cases:
                log.warning(
                    f"[{task_key}] Agent2 javob parse'da 0 test case. Raw (2000 char): {raw_response[:2000]}"
                )
                return self._build_agent_error_result(
                    task_key, task_details, overview,
                    "Test case yaratilmadi (Agent2 javobi parse bo'lmadi)."
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
                pr_count=0,
                files_changed=0,
                pr_details=[],
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
                custom_context_used=bool(custom_context),
                ai_model=self._last_agent_model(),
                requirements=requirements,
                requirement_coverage=coverage,
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

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  MULTI-AGENT: Agent1 (reuse) + Agent2 (testcase) yordamchilari
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @property
    def agent_gemini(self):
        """Agent1/Agent2 uchun Gemini helper — model fallback bilan (lazy).

        Asosiy model: kompaniya/user sozlamasidagi model.
        Fallback model: GEMINI_FALLBACK_MODEL (boshqa modelga o'tish uchun).
        GeminiHelper o'zi transient retry (5s→10s→20s) + barcha urinishlardan
        keyin fallback modelga o'tishni bajaradi.
        """
        if self._agent_gemini is None:
            from utils.ai.gemini_helper import GeminiHelper
            creds = self._get_creds()
            primary = creds.get('gemini_model') or os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
            fallback = os.getenv('GEMINI_FALLBACK_MODEL', 'gemini-2.5-flash').strip() or 'gemini-2.5-flash'
            self._agent_gemini = GeminiHelper(
                api_keys=creds['gemini_keys'],
                model_name=primary,
                fallback_model_name=fallback,
            )
        return self._agent_gemini

    def _last_agent_model(self) -> str:
        helper = self._agent_gemini
        if helper is None:
            return ""
        return str(getattr(helper, "last_model_used", "") or getattr(helper, "model_name", "") or "")

    def _build_agent_error_result(
        self, task_key: str, task_details: Dict, overview: str, error_message: str
    ) -> "TestCaseGenerationResult":
        """Agent xatosi: eski monolit usulga QAYTILMAYDI — error + status banner qaytadi."""
        blocked = build_full_analysis_blocked(
            module_name="Test Case Generator",
            task_key=task_key,
            error_message=error_message,
            files_total=0,
            files_included=0,
            prompt_size_chars=0,
            model=self._last_agent_model(),
        )
        return TestCaseGenerationResult(
            task_key=task_key,
            task_summary=task_details.get('summary', ''),
            task_full_details=task_details,
            task_overview=overview,
            success=False,
            error_message=blocked["error_message"],
            status_banner=blocked["status_banner"],
            ai_model=self._last_agent_model(),
        )

    @staticmethod
    def _build_figma_summary_text(figma_data: Optional[Dict]) -> str:
        """Agent2 prompti uchun ishlatsa bo'ladigan Figma summary matni."""
        if not figma_data:
            return ""
        parts = []
        for item in (figma_data.get('summaries') or []):
            summary = str(item.get('summary') or "").strip()
            if not summary:
                continue
            low = summary.casefold()
            if 'error:' in low or 'token topilmadi' in low or "ruxsat yo'q" in low:
                continue
            parts.append(f"[{item.get('name') or 'Figma'}]\n{summary}")
        return "\n\n".join(parts)

    def _build_agent1_input(self, task_details: Dict, figma_data: Optional[Dict]) -> Dict:
        """Agent1 uchun {tz, comments, figma} input quradi.

        QAT'IY QOIDA: Agent1 ga comment BERILMAYDI (comments=[]). Comment'lar faqat
        keyingi agent (Agent2) ga uzatiladi — talab inventarizatsiyasini muhokama
        izohlari buzib yubormasligi uchun.
        - figma: figma_data dan toza talab-nomzodlar (preflight helperlari reuse).
        """
        tz = str(task_details.get('description') or "")

        figma_texts: List[str] = []
        if figma_data:
            access = build_figma_access_status(task_details=task_details, figma_data=figma_data)
            if access.get('has_usable_data'):
                text_candidates, comment_candidates, _ = extract_figma_requirement_candidates(figma_data)
                figma_texts = [str(t).strip() for t in (list(text_candidates) + list(comment_candidates)) if str(t).strip()]

        return {"tz": tz, "comments": [], "figma": figma_texts}

    def _run_agent1_requirements(
        self, task_key: str, task_details: Dict, figma_data: Optional[Dict]
    ) -> List[Dict]:
        """Agent1 (checker kontrakti) — talablar ro'yxati [{id, text, source}].

        Gemini hard-fail (barcha kalit/model) bo'lsa RuntimeError ko'tariladi va
        yuqori darajada xato natijaga aylanadi (eskisiga qaytmaydi).
        """
        agent1_input = self._build_agent1_input(task_details, figma_data)
        if not (str(agent1_input.get('tz') or "").strip() or agent1_input.get('comments') or agent1_input.get('figma')):
            return []

        prompt = agent1_contract.build_prompt(agent1_input=agent1_input)
        raw = self.agent_gemini.analyze(
            prompt,
            max_output_tokens=AGENT1_MAX_OUTPUT_TOKENS,
            generation_config_overrides={
                "response_mime_type": "application/json",
                "response_schema": agent1_contract.RESPONSE_SCHEMA,
            },
        )

        task_summary = str(task_details.get('summary') or "").strip()
        description = str(task_details.get('description') or "")

        parse_result = parse_gemini_json(raw)
        if parse_result.ok:
            validation = agent1_contract.validate_agent1_json(
                parse_result.data,
                task_summary=task_summary,
                description=description,
                rules=None,  # rules=None → figma-source talablar SAQLANADI
            )
            if validation.get('ok'):
                return list(validation.get('requirements') or [])

        # Fallback: local JSON recover
        recovered = agent1_contract.recover_incomplete_response(raw)
        if recovered:
            contract_out = agent1_contract.normalize_contract_output(recovered)
            requirements = agent1_contract.refine_requirements(
                requirements=contract_out['requirements'],
                task_summary=task_summary,
                description=description,
                rules=None,
            )
            return list(requirements or [])
        return []

    def _run_agent2_testcases(
        self,
        *,
        task_key: str,
        task_details: Dict,
        requirements: List[Dict],
        tz_content: str,
        comment_analysis: Dict,
        figma_data: Optional[Dict],
        test_types: List[str],
        custom_context: str,
        max_test_cases: int,
        dev_objections: List[Dict],
    ) -> str:
        """Agent2 — talablar asosida test case yozish (bitta Gemini chaqiruvi)."""
        prompt = agent2_testcase.build_prompt(
            task_key=task_key,
            task_summary=task_details.get('summary', ''),
            task_type=task_details.get('type', ''),
            task_priority=task_details.get('priority', ''),
            requirements=requirements,
            tz_content=tz_content,
            comment_summary=(comment_analysis.get('summary') if comment_analysis.get('has_changes') else ""),
            figma_summary=self._build_figma_summary_text(figma_data),
            custom_context=custom_context,
            dev_objections=dev_objections or [],
            test_types=test_types,
            max_test_cases=max_test_cases,
        )

        text_info = self._calculate_text_length(prompt)
        if not text_info['within_limit']:
            # FULL-only policy: prompt qisqartirilmaydi.
            raise RuntimeError("AI token limit: prompt too large for full analysis")

        max_tokens = self._get_settings().ai_max_output_tokens
        log.info(f"[{task_key}] Agent2 ▶ Gemini chaqirildi (max_tokens={max_tokens})...")
        return self.agent_gemini.analyze(
            prompt,
            max_output_tokens=max_tokens,
            generation_config_overrides={
                "response_mime_type": "application/json",
                "response_schema": agent2_testcase.RESPONSE_SCHEMA,
            },
        )

    def _finalize_testcases(
        self, test_cases: List[TestCase], requirements: List[Dict]
    ) -> tuple:
        """Deterministik: takror test case'larni olib tashlash, TC-NNN qayta raqamlash,
        talab qamrovini hisoblash (AI emas)."""
        seen = set()
        unique: List[TestCase] = []
        for tc in test_cases:
            key = (
                str(tc.title or "").strip().casefold(),
                tuple(str(s).strip().casefold() for s in (tc.steps or [])),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(tc)

        before_trim = len(unique)
        unique = self._enforce_max_per_requirement(unique, requirements)
        trimmed = before_trim - len(unique)

        for index, tc in enumerate(unique, start=1):
            tc.id = f"TC-{index:03d}"

        coverage = agent2_testcase.extract_requirement_coverage(unique, requirements)
        coverage["trimmed_over_limit"] = trimmed
        return unique, coverage

    def _enforce_max_per_requirement(
        self, test_cases: List[TestCase], requirements: List[Dict]
    ) -> List[TestCase]:
        """Har talab uchun KO'PI BILAN MAX_TC_PER_REQ test case qoldiradi (deterministik).

        Test case bir nechta talabni qoplashi mumkin — shuning uchun olib tashlash faqat
        o'sha test case qoplagan HAR BIR talab MIN_TC_PER_REQ dan past tushmaganda bajariladi
        (qoplangan boshqa talab qamrovini buzmaslik uchun).
        """
        from collections import defaultdict

        def covers(tc: TestCase) -> List[str]:
            return [str(x).strip() for x in (tc.requirement_ids or []) if str(x).strip()]

        count: Dict[str, int] = defaultdict(int)
        for tc in test_cases:
            for rid in covers(tc):
                count[rid] += 1

        kept = list(test_cases)
        while True:
            over = [rid for rid, n in count.items() if n > MAX_TC_PER_REQ]
            if not over:
                break
            dropped = False
            for rid in over:
                for tc in kept:
                    cov = covers(tc)
                    if rid not in cov:
                        continue
                    if all(count[r] - 1 >= MIN_TC_PER_REQ for r in cov):
                        for r in cov:
                            count[r] -= 1
                        kept.remove(tc)
                        dropped = True
                        break
                if dropped:
                    break
            if not dropped:
                break  # trim qilib bo'lmaydi (boshqa talab min ostiga tushadi)
        return kept

    def _is_tz_absent_or_minimal(self, task_details: Dict, min_description_chars: int = 50) -> bool:
        """
        Taskda batafsil TZ yo'qmi yoki faqat summary bormi aniqlash.

        Description bo'sh yoki min_description_chars dan qisqa bo'lsa True.
        """
        description = task_details.get('description') or ''
        return len(description.strip()) < min_description_chars

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
                        tags=tc_data.get('tags', []),
                        requirement_ids=tc_data.get('requirement_ids', [])
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
                                tags=tc_data.get('tags', []),
                                requirement_ids=tc_data.get('requirement_ids', [])
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
