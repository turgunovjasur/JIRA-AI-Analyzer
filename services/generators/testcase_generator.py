# services/generators/testcase_generator.py
"""
Test Case Generator Service — multi-agent (Agent1 → Agent2 → Agent3).

- BaseService'dan meros oladi
- Manbalar: JIRA TZ + Agent1 requirements + Figma + custom context (PR ISHLATILMAYDI)
- TZHelper ishlatadi
- Custom Context support (AI ga qo'shimcha buyruq)

Author: JASUR TURGUNOV
"""
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# Core imports
from core import BaseService
from core.analysis_policy import build_full_analysis_blocked
from core.logger import get_logger
from core.module_preflight import ModulePreflightPolicy, run_module_preflight

# Multi-agent: Agent1 (talab ajratuvchi) checker modulidan QAYTA ISHLATILADI —
# checker fayli O'ZGARTIRILMAYDI, faqat import qilinadi.
from services.checkers.tzpr_agents import agent1 as agent1_contract
from services.checkers.tzpr_preflight import (
    build_figma_access_status,
    extract_figma_requirement_candidates,
)
from services.generators.testcase_agents import agent2_testcase, agent3_testcase_auditor
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
class TestScenario:
    """Agent3 grouped scenario structure."""
    scenario_title: str
    screen_or_flow: str = ""
    requirement_ids: List[str] = field(default_factory=list)
    test_cases: List[TestCase] = field(default_factory=list)


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
    # Agent3 grouped view va audit izohlari
    test_scenarios: List[TestScenario] = field(default_factory=list)
    audit_findings: List[Dict] = field(default_factory=list)


class TestCaseGeneratorService(BaseService):
    """
    Test Case Generator Service — multi-agent (Agent1 → Agent2 → Agent3).

    - BaseService'dan meros oladi
    - TZHelper ishlatadi
    - Custom Context support
    - PR ISHLATILMAYDI (manbalar: TZ + Agent1 requirements + Figma)
    """

    _require_github = False  # testcase GitHub ishlatmaydi

    def __init__(self, company_id: int = None, user_id: int = None):
        """Initialize service.
        UI modullar: user_id bilan yarating (user_credentials ishlatadi).
        Webhook:     company_id bilan yarating (company_settings ishlatadi).
        """
        super().__init__(company_id=company_id, user_id=user_id)
        # Agent1/Agent2/Agent3 uchun model fallback'li Gemini helper (lazy)
        self._agent_gemini = None
        self._agent_helpers = {}

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

    def generate_test_cases(
            self,
            task_key: str,
            test_types: List[str] = None,
            custom_context: str = "",
            status_callback: Optional[Callable[[str, str], None]] = None,
    ) -> TestCaseGenerationResult:
        """
        Testcase generation — multi-agent pipeline (Agent1 → Agent2 → Agent3).

        Manbalar: JIRA TZ + Agent1 requirements + user custom context. PR ISHLATILMAYDI. Natija
        ``TestCaseGenerationResult`` sifatida qaytadi.

        Ishlash bosqichlari:
            1. Shared module preflight (``run_module_preflight``): JIRA task olish,
               min TZ tekshiruvi, Figma (settingdan: "figma" ai_data_section_order da),
               TZ + comment formatlash.
            2. Agent1 (checker kontrakti) — TZ + Figma'dan talablar ro'yxati (comment YO'Q).
            3. Agent2 — talablar + real TZ + custom context asosida test case (bitta chaqiruv).
            4. Backend validation — qamrov/count/schema tekshiruvi.
            5. Agent2 repair — faqat missing requirementlar uchun.
            6. Agent3 — audit va scenario grouping.
            7. Deterministik finalize: dedup, har talabga setting bo'yicha max test case,
               TC-NNN qayta raqamlash, talab qamrovini hisoblash.

        Custom context (qo'shimcha kontekst):
            ``custom_context`` bo'sh bo'lmasa, Agent2 promtiga alohida bo'lim sifatida
            kiritiladi (product nomlari, narxlar, limitlar test datasida ishlatiladi).

        Args:
            task_key: JIRA task identifikatori (masalan: DEV-1234).
            test_types: Test turlari ro'yxati. Default: ``['positive', 'negative']``.
            custom_context: Qo'shimcha kontekst matni (bo'sh bo'lsa e'tiborga olinmaydi).
            status_callback: Har bosqichda chaqiriladigan callback ``(status, message)``.

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
            testcases_per_requirement = self._resolve_testcases_per_requirement(tc_settings)
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
            update_status("progress", f"{len(requirements)} ta talab ajratildi (Agent1).")

            # 7. AGENT2 — talablar asosida test case (BITTA chaqiruv)
            update_status("progress", "AI test case'lar yozmoqda (Agent2)...")
            try:
                raw_response = self._run_agent2_testcases(
                    task_key=task_key,
                    requirements=requirements,
                    tz_content=tz_content,
                    custom_context=custom_context,
                    testcases_per_requirement=testcases_per_requirement,
                    test_types=test_types,
                )
            except Exception as agent2_err:
                log.log_error(task_key, "agent2", str(agent2_err))
                return self._build_agent_error_result(
                    task_key, task_details, overview, f"Agent2 ishlamadi: {agent2_err}"
                )

            _ai_sek = round(_time.time() - _t0, 1)
            log.info(f"[{task_key}] Testcase ✅ AI javob olindi ({_ai_sek}s), parse qilinmoqda...")
            update_status("progress", f"Agent2 javobi olindi ({_ai_sek}s), JSON parse va backend validation qilinmoqda (Agent2).")

            # 8. Parse + backend validation #1
            test_cases = self._parse_test_cases(raw_response)
            test_cases, coverage, validation = self._validate_and_finalize_agent2_output(
                test_cases,
                requirements,
                testcases_per_requirement,
            )
            warnings.extend(validation.get("warnings") or [])
            validation_level = "warning" if validation.get("missing_requirement_ids") or validation.get("warnings") else "progress"
            update_status(
                validation_level,
                (
                    f"Agent2 validation: {len(test_cases)} ta testcase, "
                    f"coverage {coverage.get('covered_count', 0)}/{coverage.get('total_requirements', len(requirements))} talab."
                ),
            )

            # 9. Agent2 repair — faqat umuman qoplanmagan requirementlar uchun
            missing_ids = list(validation.get("missing_requirement_ids") or [])
            if missing_ids:
                warnings.append(
                    "Agent2 ayrim talablar uchun testcase yozmadi. Repair mode ishga tushdi: "
                    + ", ".join(missing_ids)
                )
                update_status("progress", "Qoplanmagan talablar uchun test case yozilmoqda (Agent2 repair)...")
                try:
                    repair_raw = self._run_agent2_testcases(
                        task_key=task_key,
                        requirements=[r for r in requirements if str(r.get("id") or "").strip() in set(missing_ids)],
                        tz_content=tz_content,
                        custom_context=custom_context,
                        testcases_per_requirement=testcases_per_requirement,
                        test_types=test_types,
                        mode="repair_missing_requirements",
                    )
                    repair_cases = self._parse_test_cases(repair_raw)
                    test_cases = self._merge_testcase_batches(test_cases, repair_cases)
                    test_cases, coverage, validation = self._validate_and_finalize_agent2_output(
                        test_cases,
                        requirements,
                        testcases_per_requirement,
                    )
                    warnings.extend(validation.get("warnings") or [])
                    update_status(
                        "progress",
                        (
                            f"Agent2 repair yakunlandi: {len(test_cases)} ta testcase, "
                            f"coverage {coverage.get('covered_count', 0)}/{coverage.get('total_requirements', len(requirements))} talab."
                        ),
                    )
                except Exception as repair_err:
                    log.log_error(task_key, "agent2_repair", str(repair_err))
                    warnings.append(f"Agent2 repair ishlamadi: {repair_err}")
            remaining_missing = list(validation.get("missing_requirement_ids") or [])
            if remaining_missing:
                warnings.append("Qoplanmagan talablar: " + ", ".join(remaining_missing))

            if not test_cases:
                log.warning(
                    f"[{task_key}] Agent2 javob parse'da 0 test case. Raw (2000 char): {raw_response[:2000]}"
                )
                return self._build_agent_error_result(
                    task_key, task_details, overview,
                    "Test case yaratilmadi (Agent2 javobi parse bo'lmadi)."
                )

            # 10. Agent3 — audit/grouping; xato bo'lsa flat Agent2 natijasi fallback
            test_scenarios = self._build_default_scenarios(test_cases, requirements)
            audit_findings: List[Dict] = []
            update_status("progress", "Test case'lar audit va grouping qilinmoqda (Agent3)...")
            try:
                agent3_raw = self._run_agent3_audit(
                    task_key=task_key,
                    requirements=requirements,
                    test_cases=test_cases,
                )
                parsed_scenarios, parsed_findings = self._parse_agent3_result(agent3_raw)
                accepted_cases, accepted_scenarios, accepted_findings, agent3_warnings = self._validate_agent3_output(
                    parsed_scenarios,
                    parsed_findings,
                    requirements,
                    testcases_per_requirement,
                    fallback_test_cases=test_cases,
                )
                test_cases = accepted_cases
                test_scenarios = accepted_scenarios
                audit_findings = accepted_findings
                warnings.extend(agent3_warnings)
                update_status(
                    "progress",
                    f"Agent3 audit yakunlandi: {len(test_scenarios)} ta scenario, {len(audit_findings)} ta finding.",
                )
                test_cases, coverage = self._finalize_testcases(
                    test_cases,
                    requirements,
                    testcases_per_requirement,
                )
                test_scenarios = self._sync_scenarios_with_final_cases(test_scenarios, test_cases)
            except Exception as agent3_err:
                log.log_error(task_key, "agent3", str(agent3_err))
                warnings.append(f"Agent3 audit ishlamadi, Agent2 flat output ishlatildi: {agent3_err}")
                test_cases, coverage = self._finalize_testcases(
                    test_cases,
                    requirements,
                    testcases_per_requirement,
                )
                test_scenarios = self._build_default_scenarios(test_cases, requirements)
                audit_findings = []

            # Statistika
            by_type = {}
            by_priority = {}
            for tc in test_cases:
                by_type[tc.test_type] = by_type.get(tc.test_type, 0) + 1
                by_priority[tc.priority] = by_priority.get(tc.priority, 0) + 1

            _total_sek = round(_time.time() - _t0, 1)
            log.info(f"[{task_key}] Testcase ✅ {len(test_cases)} ta test case yaratildi | jami: {_total_sek}s | {by_type}")
            update_status(
                "progress",
                f"Yakuniy testcase natijasi yig'ildi: {len(test_cases)} ta testcase, jami {_total_sek}s.",
            )

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
                warnings=list(dict.fromkeys(warnings)),
                custom_context_used=bool(custom_context),
                ai_model=self._last_agent_model(),
                requirements=requirements,
                requirement_coverage=coverage,
                test_scenarios=test_scenarios,
                audit_findings=audit_findings,
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
        """Backward-compat helper: Agent2 generator modeli qaytariladi."""
        return self._model_for_agent("agent2_testcase")

    def _model_names_for_agent(self, agent_key: str) -> tuple[str, str]:
        settings = self._get_settings()
        mapping = {
            "agent1_requirements": ("agent1_primary_model", "agent1_fallback_model"),
            "agent2_testcase": ("agent2_primary_model", "agent2_fallback_model"),
            "agent3_testcase_auditor": ("agent3_primary_model", "agent3_fallback_model"),
            "agent3_audit": ("agent3_primary_model", "agent3_fallback_model"),
        }
        primary_field, fallback_field = mapping.get(
            agent_key,
            ("agent2_primary_model", "agent2_fallback_model"),
        )
        primary = str(getattr(settings, primary_field, "") or "").strip()
        fallback = str(getattr(settings, fallback_field, "") or "").strip()
        return primary, fallback

    def _model_for_agent(self, agent_key: str):
        if self._agent_gemini is not None:
            return self._agent_gemini
        if agent_key not in self._agent_helpers:
            from utils.ai.gemini_helper import GeminiHelper
            creds = self._get_creds()
            primary, fallback = self._model_names_for_agent(agent_key)
            if not primary:
                raise RuntimeError(
                    f"{agent_key} primary modeli sozlanmagan. "
                    "Modul settingida yoki Super Admin global AI defaultlarida model tanlang."
                )
            self._agent_helpers[agent_key] = GeminiHelper(
                api_keys=creds['gemini_keys'],
                model_name=primary,
                fallback_model_name=fallback,
            )
        return self._agent_helpers[agent_key]

    def _last_agent_model(self) -> str:
        helper = self._agent_gemini
        if helper is None and self._agent_helpers:
            helper = next(reversed(self._agent_helpers.values()))
        if helper is None:
            return ""
        return str(getattr(helper, "last_model_used", "") or getattr(helper, "model_name", "") or "")

    def _set_agent_usage_context(
        self,
        *,
        task_key: str,
        agent_key: str,
        prompt_size_chars: int = 0,
        estimated_prompt_tokens: int = 0,
        max_output_tokens: int = 0,
        request_kind: str = "",
    ):
        helper = self._model_for_agent(agent_key)
        if hasattr(helper, "set_usage_context"):
            helper.set_usage_context(
                company_id=self._company_id,
                user_id=self._user_id,
                task_key=task_key,
                module_key="testcase_generator",
                agent_key=agent_key,
                source="testcase_multi_agent",
                prompt_size_chars=prompt_size_chars,
                estimated_prompt_tokens=estimated_prompt_tokens,
                max_output_tokens=max_output_tokens,
                request_kind=request_kind or agent_key,
            )
        return helper

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
    def _normalize_testcases_per_requirement(value: Any = None) -> int:
        try:
            n = int(value if value is not None else 3)
        except (TypeError, ValueError):
            n = 3
        return max(1, min(3, n))

    def _resolve_testcases_per_requirement(self, settings: Any = None) -> int:
        settings = settings or self._get_settings()
        return self._normalize_testcases_per_requirement(
            getattr(settings, "testcases_per_requirement", 3)
        )


    def _build_agent1_input(self, task_details: Dict, figma_data: Optional[Dict]) -> Dict:
        """Agent1 uchun {tz, comments, figma} input quradi.

        QAT'IY QOIDA: Agent1 ga comment BERILMAYDI (comments=[]). Testcase Agent2
        ham comment/Figma raw context olmaydi; Agent2 uchun source of truth — Agent1
        requirements + real TZ + user custom context.
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
        helper = self._set_agent_usage_context(
            task_key=task_key,
            agent_key="agent1_requirements",
            prompt_size_chars=len(prompt or ""),
            max_output_tokens=AGENT1_MAX_OUTPUT_TOKENS,
        )
        raw = helper.analyze(
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
        requirements: List[Dict],
        tz_content: str,
        custom_context: str,
        testcases_per_requirement: int,
        test_types: Optional[List[str]] = None,
        mode: str = "initial",
    ) -> str:
        """Agent2 — talablar asosida test case yozish (bitta Gemini chaqiruvi)."""
        prompt = agent2_testcase.build_prompt(
            requirements=requirements,
            tz_content=tz_content,
            custom_context=custom_context,
            testcases_per_requirement=testcases_per_requirement,
            test_types=test_types,
            mode=mode,
        )

        text_info = self._calculate_text_length(prompt)
        if not text_info['within_limit']:
            # FULL-only policy: prompt qisqartirilmaydi.
            raise RuntimeError("AI token limit: prompt too large for full analysis")

        max_tokens = self._get_settings().ai_max_output_tokens
        log.info(f"[{task_key}] Agent2 ▶ Gemini chaqirildi (mode={mode}, max_tokens={max_tokens})...")
        helper = self._set_agent_usage_context(
            task_key=task_key,
            agent_key="agent2_testcase",
            prompt_size_chars=int(text_info.get("chars") or 0),
            estimated_prompt_tokens=int(text_info.get("tokens") or 0),
            max_output_tokens=max_tokens,
            request_kind=mode,
        )
        return helper.analyze(
            prompt,
            max_output_tokens=max_tokens,
            generation_config_overrides={
                "response_mime_type": "application/json",
                "response_schema": agent2_testcase.RESPONSE_SCHEMA,
            },
        )

    def _run_agent3_audit(
        self,
        *,
        task_key: str,
        requirements: List[Dict],
        test_cases: List[TestCase],
    ) -> str:
        """Agent3 — Agent2 outputini audit/grouping qiladi."""
        prompt = agent3_testcase_auditor.build_prompt(
            requirements=requirements,
            test_cases=test_cases,
        )

        text_info = self._calculate_text_length(prompt)
        if not text_info['within_limit']:
            raise RuntimeError("AI token limit: agent3 prompt too large for full analysis")

        max_tokens = self._get_settings().ai_max_output_tokens
        log.info(f"[{task_key}] Agent3 ▶ Gemini chaqirildi (max_tokens={max_tokens})...")
        helper = self._set_agent_usage_context(
            task_key=task_key,
            agent_key="agent3_testcase_auditor",
            prompt_size_chars=int(text_info.get("chars") or 0),
            estimated_prompt_tokens=int(text_info.get("tokens") or 0),
            max_output_tokens=max_tokens,
        )
        return helper.analyze(
            prompt,
            max_output_tokens=max_tokens,
            generation_config_overrides={
                "response_mime_type": "application/json",
                "response_schema": agent3_testcase_auditor.RESPONSE_SCHEMA,
            },
        )

    @staticmethod
    def _requirement_ids(requirements: List[Dict]) -> List[str]:
        return [
            str(r.get("id") or "").strip()
            for r in (requirements or [])
            if str(r.get("id") or "").strip()
        ]

    @staticmethod
    def _as_string_list(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, tuple):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value or "").strip()
        return [text] if text else []

    @staticmethod
    def _strip_leading_enum(text: str) -> str:
        """Qator boshidagi '1.', '2)', '10. ' kabi raqamlashni olib tashlash."""
        return re.sub(r"^\s*\d+[.)]\s+", "", str(text or "")).strip()

    @classmethod
    def _normalize_steps(cls, steps: Any) -> List[str]:
        """Qadamlardagi qo'lbola raqamlashni tozalash (ADF ordered-list o'zi raqamlaydi)."""
        out: List[str] = []
        for raw in cls._as_string_list(steps):
            for part in str(raw).split("\n"):
                cleaned = cls._strip_leading_enum(part)
                if cleaned:
                    out.append(cleaned)
        return out

    @classmethod
    def _split_enum_items(cls, text: str) -> List[str]:
        """Bir/ko'p qatorli matnni alohida bandlarga bo'lish (raqamlashsiz)."""
        text = str(text or "").strip()
        if not text:
            return []
        if "\n" in text:
            parts = text.split("\n")
        else:
            parts = re.split(r"\s*[,;]?\s*(?=\d+[.)]\s)", text)
        items = [cls._strip_leading_enum(p) for p in parts]
        return [it for it in items if it]

    def _normalize_test_case(self, tc: TestCase, valid_requirement_ids: set[str]) -> TestCase:
        tc.title = str(tc.title or "").strip() or "Nomsiz test case"
        tc.description = str(tc.description or "").strip()
        tc.preconditions = "\n".join(self._split_enum_items(tc.preconditions))
        tc.steps = self._normalize_steps(tc.steps)
        tc.expected_result = str(tc.expected_result or "").strip()
        tc.test_type = str(tc.test_type or "positive").strip() or "positive"
        tc.priority = str(tc.priority or "Medium").strip() or "Medium"
        tc.severity = str(tc.severity or "Major").strip() or "Major"
        tc.tags = self._as_string_list(tc.tags)
        req_ids = self._as_string_list(tc.requirement_ids)
        tc.requirement_ids = [rid for rid in req_ids if rid in valid_requirement_ids]
        return tc

    def _filter_invalid_testcases(
        self,
        test_cases: List[TestCase],
        requirements: List[Dict],
    ) -> tuple[List[TestCase], List[str]]:
        valid_requirement_ids = set(self._requirement_ids(requirements))
        valid: List[TestCase] = []
        invalid_reasons: List[str] = []
        for index, tc in enumerate(test_cases or [], start=1):
            tc = self._normalize_test_case(tc, valid_requirement_ids)
            if not tc.requirement_ids:
                invalid_reasons.append(f"TC#{index}: requirement_ids yo'q yoki noma'lum")
                continue
            if not tc.steps:
                invalid_reasons.append(f"TC#{index}: steps bo'sh")
                continue
            if not tc.expected_result:
                invalid_reasons.append(f"TC#{index}: expected_result bo'sh")
                continue
            valid.append(tc)
        return valid, invalid_reasons

    def _validate_and_finalize_agent2_output(
        self,
        test_cases: List[TestCase],
        requirements: List[Dict],
        testcases_per_requirement: int,
    ) -> tuple[List[TestCase], Dict, Dict]:
        testcases_per_requirement = self._normalize_testcases_per_requirement(testcases_per_requirement)
        valid_cases, invalid_reasons = self._filter_invalid_testcases(test_cases, requirements)
        finalized, coverage = self._finalize_testcases(
            valid_cases,
            requirements,
            testcases_per_requirement,
        )

        req_ids = self._requirement_ids(requirements)
        counts = {rid: 0 for rid in req_ids}
        for tc in finalized:
            for rid in tc.requirement_ids or []:
                if rid in counts:
                    counts[rid] += 1

        missing = [rid for rid, count in counts.items() if count == 0]
        underfilled = [
            rid for rid, count in counts.items()
            if 0 < count < testcases_per_requirement
        ]

        warnings: List[str] = []
        if invalid_reasons:
            warnings.append(
                f"{len(invalid_reasons)} ta yaroqsiz test case olib tashlandi: "
                + "; ".join(invalid_reasons[:5])
            )
        if underfilled:
            warnings.append(
                f"{testcases_per_requirement} ta targetdan kam testcase yozilgan talablar: "
                + ", ".join(underfilled)
            )
        if coverage.get("trimmed_over_limit"):
            warnings.append(
                f"{coverage['trimmed_over_limit']} ta ortiqcha test case olib tashlandi "
                f"(har talabga maksimum {testcases_per_requirement} ta)."
            )

        validation = {
            "missing_requirement_ids": missing,
            "underfilled_requirement_ids": underfilled,
            "invalid_test_cases": invalid_reasons,
            "warnings": warnings,
        }
        return finalized, coverage, validation

    def _merge_testcase_batches(
        self,
        initial_cases: List[TestCase],
        repair_cases: List[TestCase],
    ) -> List[TestCase]:
        return list(initial_cases or []) + list(repair_cases or [])

    @staticmethod
    def _testcase_identity_key(tc: TestCase) -> tuple:
        return (
            tuple(sorted(str(rid).strip() for rid in (tc.requirement_ids or []) if str(rid).strip())),
            str(tc.test_type or "").strip().casefold(),
            str(tc.title or "").strip().casefold(),
            tuple(str(step).strip().casefold() for step in (tc.steps or [])),
            str(tc.expected_result or "").strip().casefold(),
        )

    def _testcase_from_dict(self, data: Dict[str, Any]) -> TestCase:
        return TestCase(
            id=str(data.get("id") or "TC-XXX"),
            title=str(data.get("title") or ""),
            description=str(data.get("description") or ""),
            preconditions=str(data.get("preconditions") or ""),
            steps=self._as_string_list(data.get("steps") or []),
            expected_result=str(data.get("expected_result") or ""),
            test_type=str(data.get("test_type") or "positive"),
            priority=str(data.get("priority") or "Medium"),
            severity=str(data.get("severity") or "Major"),
            tags=self._as_string_list(data.get("tags") or []),
            requirement_ids=self._as_string_list(data.get("requirement_ids") or []),
        )

    def _parse_agent3_result(self, raw_response: str) -> tuple[List[TestScenario], List[Dict]]:
        parse_result = parse_gemini_json(raw_response)
        data = parse_result.data if parse_result.ok and isinstance(parse_result.data, dict) else None
        if data is None:
            json_start = raw_response.find('{')
            json_end = raw_response.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                return [], []
            data = json.loads(self._sanitize_json_escapes(raw_response[json_start:json_end]))

        raw_scenarios = data.get("test_scenarios") or data.get("scenarios") or []
        scenarios: List[TestScenario] = []
        for idx, scenario_data in enumerate(raw_scenarios, start=1):
            if not isinstance(scenario_data, dict):
                continue
            cases = []
            for tc_data in scenario_data.get("test_cases") or []:
                if isinstance(tc_data, dict):
                    cases.append(self._testcase_from_dict(tc_data))
            if not cases:
                continue
            req_ids = self._as_string_list(scenario_data.get("requirement_ids") or [])
            if not req_ids:
                req_ids = sorted({
                    rid for tc in cases for rid in (tc.requirement_ids or [])
                    if str(rid).strip()
                })
            scenarios.append(TestScenario(
                scenario_title=str(scenario_data.get("scenario_title") or f"Scenario {idx}").strip(),
                screen_or_flow=str(scenario_data.get("screen_or_flow") or "").strip(),
                requirement_ids=req_ids,
                test_cases=cases,
            ))

        findings: List[Dict] = []
        for item in data.get("audit_findings") or []:
            if not isinstance(item, dict):
                continue
            reason = str(item.get("reason") or "").strip()
            if not reason:
                continue
            findings.append({
                "type": str(item.get("type") or "note").strip() or "note",
                "requirement_ids": self._as_string_list(item.get("requirement_ids") or item.get("requirement_id") or []),
                "reason": reason,
            })
        return scenarios, findings

    @staticmethod
    def _flatten_scenarios(scenarios: List[TestScenario]) -> List[TestCase]:
        return [tc for scenario in (scenarios or []) for tc in (scenario.test_cases or [])]

    def _build_default_scenarios(
        self,
        test_cases: List[TestCase],
        requirements: List[Dict],
    ) -> List[TestScenario]:
        if not test_cases:
            return []
        req_ids = sorted({
            rid for tc in test_cases for rid in (tc.requirement_ids or [])
            if str(rid).strip()
        }) or self._requirement_ids(requirements)
        return [TestScenario(
            scenario_title="Yaratilgan test case'lar",
            screen_or_flow="General",
            requirement_ids=req_ids,
            test_cases=list(test_cases),
        )]

    def _validate_agent3_output(
        self,
        scenarios: List[TestScenario],
        audit_findings: List[Dict],
        requirements: List[Dict],
        testcases_per_requirement: int,
        *,
        fallback_test_cases: List[TestCase],
    ) -> tuple[List[TestCase], List[TestScenario], List[Dict], List[str]]:
        warnings: List[str] = []
        fallback_cases, fallback_coverage = self._finalize_testcases(
            list(fallback_test_cases or []),
            requirements,
            testcases_per_requirement,
        )
        if not scenarios:
            warnings.append("Agent3 grouped scenario qaytarmadi, Agent2 flat output ishlatildi.")
            return fallback_cases, self._build_default_scenarios(fallback_cases, requirements), [], warnings

        flattened = self._flatten_scenarios(scenarios)
        accepted_cases, accepted_coverage, validation = self._validate_and_finalize_agent2_output(
            flattened,
            requirements,
            testcases_per_requirement,
        )
        accepted_missing = set(accepted_coverage.get("uncovered_ids") or [])
        fallback_missing = set(fallback_coverage.get("uncovered_ids") or [])
        if not accepted_cases or not accepted_missing.issubset(fallback_missing):
            warnings.append("Agent3 grouping coverage'ni buzdi, Agent2 flat output ishlatildi.")
            return fallback_cases, self._build_default_scenarios(fallback_cases, requirements), [], warnings

        warnings.extend(validation.get("warnings") or [])
        synced = self._sync_scenarios_with_final_cases(scenarios, accepted_cases)
        if not synced:
            synced = self._build_default_scenarios(accepted_cases, requirements)
        return accepted_cases, synced, list(audit_findings or []), warnings

    def _sync_scenarios_with_final_cases(
        self,
        scenarios: List[TestScenario],
        final_cases: List[TestCase],
    ) -> List[TestScenario]:
        from collections import Counter

        remaining = Counter(self._testcase_identity_key(tc) for tc in (final_cases or []))
        synced: List[TestScenario] = []
        for scenario in scenarios or []:
            kept: List[TestCase] = []
            for tc in scenario.test_cases or []:
                key = self._testcase_identity_key(tc)
                if remaining.get(key, 0) <= 0:
                    continue
                remaining[key] -= 1
                kept.append(tc)
            if not kept:
                continue
            req_ids = sorted({
                rid for tc in kept for rid in (tc.requirement_ids or [])
                if str(rid).strip()
            })
            synced.append(TestScenario(
                scenario_title=scenario.scenario_title,
                screen_or_flow=scenario.screen_or_flow,
                requirement_ids=req_ids,
                test_cases=kept,
            ))
        return synced

    def _finalize_testcases(
        self, test_cases: List[TestCase], requirements: List[Dict], max_per_requirement: int | None = None
    ) -> tuple:
        """Deterministik: takror test case'larni olib tashlash, TC-NNN qayta raqamlash,
        talab qamrovini hisoblash (AI emas)."""
        max_per_requirement = self._normalize_testcases_per_requirement(max_per_requirement)
        seen = set()
        unique: List[TestCase] = []
        for tc in test_cases:
            key = self._testcase_identity_key(tc)
            if key in seen:
                continue
            seen.add(key)
            unique.append(tc)

        before_trim = len(unique)
        unique = self._enforce_max_per_requirement(unique, requirements, max_per_requirement)
        trimmed = before_trim - len(unique)

        for index, tc in enumerate(unique, start=1):
            tc.id = f"TC-{index:03d}"

        coverage = agent2_testcase.extract_requirement_coverage(unique, requirements)
        coverage["trimmed_over_limit"] = trimmed
        return unique, coverage

    def _enforce_max_per_requirement(
        self, test_cases: List[TestCase], requirements: List[Dict], max_per_requirement: int | None = None
    ) -> List[TestCase]:
        """Har talab uchun KO'PI BILAN MAX_TC_PER_REQ test case qoldiradi (deterministik).

        Test case bir nechta talabni qoplashi mumkin — shuning uchun olib tashlash faqat
        o'sha test case qoplagan HAR BIR talab MIN_TC_PER_REQ dan past tushmaganda bajariladi
        (qoplangan boshqa talab qamrovini buzmaslik uchun).
        """
        from collections import defaultdict
        max_per_requirement = self._normalize_testcases_per_requirement(max_per_requirement)

        def covers(tc: TestCase) -> List[str]:
            return [str(x).strip() for x in (tc.requirement_ids or []) if str(x).strip()]

        count: Dict[str, int] = defaultdict(int)
        for tc in test_cases:
            for rid in covers(tc):
                count[rid] += 1

        kept = list(test_cases)
        while True:
            over = [rid for rid, n in count.items() if n > max_per_requirement]
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


    def _parse_test_cases(self, raw_response: str) -> List[TestCase]:
        """
        AI xom javobidan JSON ajratib olish va ``TestCase`` ob'ektlarini yaratish.

        Parse yo'li (Agent1/Agent3 bilan bir xil):
            1. Avval mustahkam ``parse_gemini_json`` (markdown fence olib tashlash,
               balanced-object ajratish va repair — hammasi bir joyda).
            2. Faqat u muvaffaqiyatsiz bo'lsa — eski fallback (naive ``{``/``}``
               kesish + ``_sanitize_json_escapes`` + truncated ``_try_repair_json``).
            3. Test case ro'yxati alias orqali topiladi: ``test_cases`` →
               ``testCases`` → ``tests`` → ``test_case_list``.
            4. Har bir lug'at ``_testcase_from_dict`` orqali ``TestCase`` ga aylanadi.

        Returns:
            List[TestCase]: parse qilingan test case'lar; xato bo'lsa bo'sh ro'yxat
                (exception ko'tarilmaydi).
        """
        data = self._extract_testcase_payload(raw_response)
        if data is None:
            log.info("Parse natija: 0 ta test case")
            return []

        tc_list = (
            data.get('test_cases')
            or data.get('testCases')
            or data.get('tests')
            or data.get('test_case_list')
            or []
        )
        if not tc_list:
            log.warning(
                f"JSON parse OK, lekin test case kaliti topilmadi. "
                f"Mavjud kalitlar: {list(data.keys())} | Raw response (2000 char): {raw_response[:2000]}"
            )

        test_cases: List[TestCase] = []
        for tc_data in tc_list:
            if not isinstance(tc_data, dict):
                continue
            try:
                test_cases.append(self._testcase_from_dict(tc_data))
            except Exception as e:
                log.warning(f"Test case parse xatosi: {e}")
                continue

        log.info(f"Parse natija: {len(test_cases)} ta test case")
        return test_cases

    def _extract_testcase_payload(self, raw_response: str) -> Optional[Dict[str, Any]]:
        """Xom javobdan test case JSON payload'ini (dict) olish.

        Avval mustahkam ``parse_gemini_json``; u ishlamasa eski naive kesish +
        truncated ``_try_repair_json`` fallback. Topilmasa ``None``.
        """
        parse_result = parse_gemini_json(raw_response)
        if parse_result.ok:
            if isinstance(parse_result.data, dict):
                return parse_result.data
            if isinstance(parse_result.data, list):
                return {"test_cases": parse_result.data}

        json_start = raw_response.find('{')
        json_end = raw_response.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            log.warning("JSON topilmadi!")
            return None

        json_str = self._sanitize_json_escapes(raw_response[json_start:json_end])
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            log.json_parse_error("UNKNOWN", f"JSON parse xatosi: {e}")
            log.json_repair_attempt("UNKNOWN")

        repaired = self._try_repair_json(json_str)
        if not repaired:
            log.json_parse_error("UNKNOWN", "JSON repair imkonsiz")
            log.warning(f"Response: {raw_response[:500]}")
            return None
        try:
            data = json.loads(repaired)
            log.json_repair_success("UNKNOWN", "Truncated JSON tiklandi")
            return data
        except json.JSONDecodeError:
            log.json_parse_error("UNKNOWN", "Truncated JSON tuzatib bo'lmadi")
            log.warning(f"Response: {raw_response[:500]}")
            return None

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
