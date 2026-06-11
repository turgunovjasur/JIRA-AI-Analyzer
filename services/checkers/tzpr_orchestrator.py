from __future__ import annotations

from dataclasses import asdict
from typing import Any

from core import CommentSeparator, PRNotMergedError, RECHECK_REASONS
from core.logger import get_logger
from services.checkers.tzpr_constants import (
    PRO_MODEL_NAME,
    execution_mode_display_label as _execution_mode_display_label,
    normalize_execution_mode as _normalize_execution_mode,
    resolve_agent_model_names,
)
from services.checkers.tzpr_multi_agent_service import TZPRMultiAgentService
from services.checkers.tzpr_preflight import (
    agent1_rules_from_effective_settings as _agent1_rules_from_effective_settings,
    build_agent1_sanitized_input as _build_agent1_sanitized_input,
    parse_author_list as _parse_author_list,
)
from services.checkers.tzpr_agent_runner import AgentRunnerMixin
from services.checkers.tzpr_result_builder import ResultBuilderMixin
from services.checkers.tzpr_run_state import RunStateMixin
from utils.ai.gemini_helper import GeminiHelper
from utils.database.checker_run_db import (
    get_checker_run_snapshot,
)

log = get_logger("checker.multi_agent")

class _TZPRMultiAgentExecutor(AgentRunnerMixin, ResultBuilderMixin, RunStateMixin):
    def __init__(self, snapshot: dict[str, Any]):
        self.snapshot = snapshot
        self.run_id = str(snapshot.get("run_id") or "")
        self.task_key = str(snapshot.get("task_key") or "").strip().upper()
        self.company_id = snapshot.get("company_id")
        self.user_id = snapshot.get("user_id")
        self.execution_mode = _normalize_execution_mode(snapshot.get("execution_mode"))
        payload = snapshot.get("request_payload") or {}
        self.output_profile = str(payload.get("output_profile") or "ui").strip().lower() or "ui"
        self.show_full_diff = bool(payload.get("show_full_diff", True))
        self.max_files = payload.get("max_files")
        self.use_smart_patch = payload.get("use_smart_patch")
        self.service = TZPRMultiAgentService(user_id=self.user_id, company_id=self.company_id)
        self._gemini_helper: GeminiHelper | None = None
        self._agent_helpers: dict[str, GeminiHelper] = {}

    def run(self) -> dict[str, Any] | None:
        self._set_run_state(
            "running",
            active_phase="input_collection",
            status_message="JIRA, PR va TZ ma'lumotlari yig'ilmoqda",
            started=True,
        )
        self._event(
            "info",
            "run_started",
            f"{_execution_mode_display_label(self.execution_mode)} checker run boshlandi",
        )

        try:
            context = self._collect_context()
        except Exception as exc:
            log.error(f"[{self.task_key}] multi-agent input collection error: {exc}", exc_info=True)
            result = self._build_blocked_result(str(exc))
            self._mark_run_finished("blocked", result, str(exc))
            self._block_remaining_agents("Input collection xatosi")
            return get_checker_run_snapshot(self.run_id)

        try:
            if context.get("error_result"):
                error_result = context["error_result"]
                self._block_remaining_agents(error_result.error_message or "Context bloklandi")
                self._mark_run_finished(
                    error_result.run_state or "blocked",
                    asdict(error_result),
                    error_result.error_message,
                )
                return get_checker_run_snapshot(self.run_id)

            agent1 = self._run_agent1(context)
            if not agent1.get("success"):
                result = self._build_blocked_result(agent1.get("error") or "Agent1 yiqildi", context=context)
                self._set_agent_state(
                    "agent2_verifier",
                    "blocked",
                    error_text="Agent1 muvaffaqiyatsiz tugadi",
                )
                self._set_agent_state(
                    "agent3_arbiter",
                    "blocked",
                    error_text="Agent1 muvaffaqiyatsiz tugadi",
                )
                self._mark_run_finished("blocked", result, agent1.get("error"))
                return get_checker_run_snapshot(self.run_id)

            agent2 = self._run_agent2(context, agent1)
            agent3 = self._run_agent3(context, agent1, agent2)
            self._event(
                "info",
                "run_finalizing",
                "Agent natijalari yakuniy resultga yig'ilmoqda",
                meta={
                    "requirements_total": len(agent1.get("requirements") or []),
                    "effective_requirements_total": len(agent1.get("effective_requirements") or []),
                    "verifications_total": len(agent2.get("verifications") or []),
                    "requirements_result_total": len(agent3.get("requirements") or []),
                },
            )

            final_result = self._build_final_result(
                context=context,
                agent1=agent1,
                agent2=agent2,
                agent3=agent3,
            )
            final_state = str(final_result.run_state or "completed")
            self._mark_run_finished(final_state, asdict(final_result), final_result.error_message)
            return get_checker_run_snapshot(self.run_id)
        except Exception as exc:
            self._handle_unexpected_run_failure(exc, context=context)
            return get_checker_run_snapshot(self.run_id)

    def _collect_context(self, *, emit_events: bool = True) -> dict[str, Any]:
        effective_use_smart_patch = (
            self.use_smart_patch
            if self.use_smart_patch is not None
            else bool(getattr(self.service._get_settings(), "default_use_smart_patch", True))
        )
        needs_code_context = True
        effective_settings = self.service._build_effective_settings(
            requested_output_profile=self.output_profile,
            effective_use_smart_patch=effective_use_smart_patch,
        )

        if self.max_files is not None or not self.show_full_diff:
            banner_result = self.service._create_error_result(
                task_key=self.task_key,
                error_message="Multi-agent checker faqat full diff bilan ishlaydi.",
                effective_settings=effective_settings,
            )
            banner_result.execution_mode = self.execution_mode
            banner_result.run_id = self.run_id
            banner_result.run_state = "blocked"
            return {"error_result": banner_result}

        status_updater = self._status_updater(emit_events=emit_events, update_run_state=emit_events)
        figma_lookup_enabled = "figma" in list(effective_settings.get("ai_data_section_order") or [])
        task_details = self.service._get_task_details(
            self.task_key,
            status_updater,
            include_pr_urls=True,
            include_figma_links=figma_lookup_enabled,
        )
        if not task_details:
            result = self.service._create_error_result(
                self.task_key,
                f"❌ {self.task_key} topilmadi. JIRA da task mavjudligini tekshiring.",
                effective_settings=effective_settings,
            )
            result.execution_mode = self.execution_mode
            result.run_id = self.run_id
            result.run_state = "blocked"
            return {"error_result": result}

        try:
            pr_info = self.service._get_pr_info(
                self.task_key,
                task_details,
                status_updater,
                effective_use_smart_patch,
            )
        except PRNotMergedError as exc:
            result = self.service._create_error_result(
                self.task_key,
                str(exc),
                task_summary=task_details.get("summary") or "",
                effective_settings=effective_settings,
            )
            result.execution_mode = self.execution_mode
            result.run_id = self.run_id
            result.run_state = "blocked"
            return {"error_result": result}

        if not pr_info:
            result = self.service._create_error_result(
                self.task_key,
                "Bu task uchun PR topilmadi (JIRA va GitHub'da)",
                task_summary=task_details.get("summary") or "",
                warnings=["JIRA da PR link yo'q", "GitHub search natija bermadi"],
                effective_settings=effective_settings,
            )
            result.execution_mode = self.execution_mode
            result.run_id = self.run_id
            result.run_state = "blocked"
            return {"error_result": result}

        min_tz = self.service._get_settings().min_tz_description_chars
        if min_tz > 0 and self.service._is_tz_too_short(task_details, min_tz):
            actual_chars = self.service._get_tz_length_chars(task_details)
            result = self.service._create_error_result(
                self.task_key,
                (
                    f"TZ yetarli emas. (summary + description: {actual_chars} belgi, "
                    f"min: {min_tz} belgi). {_execution_mode_display_label(self.execution_mode)} checker to'xtatildi."
                ),
                task_summary=task_details.get("summary") or "",
                effective_settings=effective_settings,
            )
            result.execution_mode = self.execution_mode
            result.run_id = self.run_id
            result.run_state = "blocked"
            return {"error_result": result}

        is_recheck = False
        return_reason = ""
        try:
            from utils.database.task_db import get_task

            db_task = get_task(self.task_key) or {}
            return_reason = str(db_task.get("return_reason") or "")
            is_recheck = return_reason in RECHECK_REASONS
        except Exception:
            db_task = {}

        tz_content, comment_analysis = self.service._get_tz_content(task_details, status_updater)
        comment_separated = CommentSeparator.separate(task_details.get("comments", []))
        figma_data = self.service._get_figma_data(task_details, status_updater)
        agent1_rules = _agent1_rules_from_effective_settings(effective_settings)
        trusted_authors = _parse_author_list(
            getattr(self.service._get_settings(), "trusted_scope_comment_authors", "")
        )
        agent1_input = _build_agent1_sanitized_input(
            task_details=task_details,
            trusted_authors=trusted_authors,
            figma_data=figma_data,
            read_comments_enabled=bool(effective_settings.get("read_comments_enabled", True)),
            max_comments_to_read=int(effective_settings.get("max_comments_to_read") or 0),
            rules=agent1_rules,
        )
        if emit_events:
            self._event(
                "info",
                "input_collection_done",
                "Input collection tugadi",
                meta={
                    "comments_enabled": effective_settings.get("read_comments_enabled"),
                    "files_changed": pr_info.get("files_changed"),
                    "figma_count": (figma_data or {}).get("count") or 0,
                    "agent1_comments": len(agent1_input.get("comments") or []),
                    "agent1_figma": len(agent1_input.get("figma") or []),
                    "is_recheck": is_recheck,
                },
            )

        return {
            "effective_settings": effective_settings,
            "effective_use_smart_patch": effective_use_smart_patch,
            "task_details": task_details,
            "pr_info": pr_info,
            "tz_content": tz_content,
            "comment_analysis": comment_analysis,
            "comment_separated": comment_separated,
            "figma_data": figma_data,
            "agent1_input": agent1_input,
            "is_recheck": is_recheck,
            "return_reason": return_reason,
            "db_task": db_task,
        }

    def _pro_model(self) -> GeminiHelper:
        return self._model_for_agent("agent2_verifier")

    def _model_names_for_agent(self, agent_key: str) -> tuple[str, str]:
        return resolve_agent_model_names(self.service._get_settings(), agent_key)

    def _model_for_agent(self, agent_key: str) -> GeminiHelper:
        if agent_key not in self._agent_helpers:
            creds = self.service._get_creds()
            primary_model, fallback_model = self._model_names_for_agent(agent_key)
            self._gemini_helper = GeminiHelper(
                api_keys=creds["gemini_keys"],
                model_name=primary_model,
                fallback_model_name=fallback_model,
            )
            self._agent_helpers[agent_key] = self._gemini_helper
        return self._agent_helpers[agent_key]

    def _last_model_used(self, agent_key: str | None = None) -> str:
        helper = self._agent_helpers.get(agent_key or "") if agent_key else self._gemini_helper
        if helper is None and agent_key:
            primary_model, _fallback_model = self._model_names_for_agent(agent_key)
            return primary_model
        if helper is None:
            return PRO_MODEL_NAME
        return str(helper.last_model_used or PRO_MODEL_NAME)
