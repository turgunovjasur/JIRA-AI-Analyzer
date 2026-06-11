from __future__ import annotations

import traceback
from dataclasses import asdict
from typing import Any

from core.logger import get_logger
from services.checkers.tzpr_models import (
    TZPRAnalysisOverview,
    TZPRAnalysisResult,
    TZPRAnalysisSection,
)
from services.checkers.tzpr_constants import (
    FALLBACK_MODEL_NAME,
    FINAL_ANALYSIS_SECTION_TITLES,
    PRO_MODEL_NAME,
    execution_mode_display_label as _execution_mode_display_label,
)
from services.checkers.tzpr_helpers import now_iso as _now_iso, summarize as _summarize
from services.checkers.tzpr_presenters import (
    build_extra_issue_lines as _build_extra_issue_lines,
    build_final_analysis_text as _build_final_analysis_text,
    build_issue_section_items as _build_issue_section_items,
    calculate_compliance_score_from_agent3 as _calculate_compliance_score_from_agent3,
    collect_final_warnings as _collect_final_warnings,
    decision_matrix_item_text as _decision_matrix_item_text,
    figma_lines as _figma_lines,
)
from utils.database.checker_run_db import get_checker_run_snapshot, update_checker_run_record

log = get_logger("checker.multi_agent")


class ResultBuilderMixin:
    def _build_final_result(
        self,
        *,
        context: dict[str, Any],
        agent1: dict[str, Any],
        agent2: dict[str, Any],
        agent3: dict[str, Any],
    ) -> TZPRAnalysisResult:
        compliance_score = _calculate_compliance_score_from_agent3(agent3)
        final_requirements = list(agent3.get("requirements") or [])
        extra_issues = _build_extra_issue_lines(agent1, agent2, agent3)
        analysis_text = _build_final_analysis_text(
            summary=agent3.get("summary") or "",
            decisions=final_requirements,
            compliance_score=compliance_score,
            figma_data=context["figma_data"],
            extra_issues=extra_issues,
        )
        analysis_sections = self._build_analysis_sections_from_decisions(
            decisions=final_requirements,
            figma_data=context["figma_data"],
            extra_issues=extra_issues,
        )
        analysis_overview = self._build_analysis_overview(
            analysis_sections=analysis_sections,
            compliance_score=compliance_score,
            figma_data=context["figma_data"],
            summary=str(agent3.get("summary") or "").strip(),
            verdict=str(agent3.get("verdict") or "").strip(),
            verdict_label=str(agent3.get("verdict_label") or "").strip(),
            verdict_reason=str(agent3.get("verdict_reason") or "").strip(),
        )
        requirement_matrix = self.service._build_requirement_matrix(
            analysis_sections=analysis_sections,
            task_details=context["task_details"],
            pr_details=context["pr_info"].get("pr_details", []),
            figma_data=context["figma_data"],
            comment_analysis=context["comment_analysis"],
        )
        agent3_helper = getattr(self, "_agent_helpers", {}).get("agent3_arbiter")
        agent3_primary, agent3_fallback = (
            self._model_names_for_agent("agent3_arbiter")
            if hasattr(self, "_model_names_for_agent")
            else (PRO_MODEL_NAME, FALLBACK_MODEL_NAME)
        )
        run_info = self.service._build_run_info(
            effective_settings=context["effective_settings"],
            files_analyzed=context["pr_info"].get("files_changed", 0),
            total_files_changed=context["pr_info"].get("files_changed", 0),
            prompt_size_chars=len(analysis_text),
            ai_retry_count=0,
            ai_model=str(getattr(agent3_helper, "last_model_used", agent3_primary)),
            ai_primary_model=agent3_primary,
            ai_fallback_model=agent3_fallback,
            ai_used_fallback=bool(getattr(agent3_helper, "last_used_fallback", False)),
        )
        qa_recommendation = self.service._build_qa_recommendation(
            overview=analysis_overview,
            compliance_score=compliance_score,
        )
        if str(agent3.get("run_state") or "") == "manual_review":
            qa_recommendation.action = "manual_review"
            qa_recommendation.label = "Manual review kerak"
            qa_recommendation.reason = (
                agent3.get("verdict_reason")
                or qa_recommendation.reason
                or "Run-based arbiter manual review tavsiya qildi."
            )
        workflow_info = self.service._build_workflow_info(
            task_key=self.task_key,
            compliance_score=compliance_score,
            is_recheck=context["is_recheck"],
        )
        result = TZPRAnalysisResult(
            success=True,
            task_key=self.task_key,
            task_summary=context["task_details"].get("summary") or "",
            tz_content=context["tz_content"],
            pr_count=context["pr_info"].get("pr_count", 0),
            files_changed=context["pr_info"].get("files_changed", 0),
            total_additions=context["pr_info"].get("total_additions", 0),
            total_deletions=context["pr_info"].get("total_deletions", 0),
            pr_details=context["pr_info"].get("pr_details", []),
            pr_selection=context["pr_info"].get("pr_selection", {}),
            ai_analysis=analysis_text,
            compliance_score=compliance_score,
            warnings=_collect_final_warnings(agent1, agent2, agent3),
            figma_data=context["figma_data"],
            comment_analysis=context["comment_analysis"],
            dev_objections=context["comment_separated"].get("dev_after", []) if context["is_recheck"] else [],
            analysis_sections=analysis_sections,
            analysis_overview=analysis_overview,
            task_info=self.service._build_task_info(context["task_details"]),
            run_info=run_info,
            qa_recommendation=qa_recommendation,
            comment_intelligence=self.service._build_comment_intelligence(
                comment_analysis=context["comment_analysis"],
                comment_separated=context["comment_separated"],
                is_recheck=context["is_recheck"],
            ),
            workflow_info=workflow_info,
            requirement_matrix=requirement_matrix,
            effective_settings=context["effective_settings"],
            execution_mode=self.execution_mode,
            run_id=self.run_id,
            run_state=str(agent3.get("run_state") or "completed"),
            agent_runs=(get_checker_run_snapshot(self.run_id) or {}).get("agent_runs", []),
            run_events=(get_checker_run_snapshot(self.run_id) or {}).get("run_events", []),
            requirement_inventory=agent1.get("requirements") or [],
            verifications=agent2.get("verifications") or [],
            arbiter_summary={
                "summary": agent3.get("summary") or "",
                "verdict": agent3.get("verdict") or analysis_overview.verdict,
                "verdict_label": agent3.get("verdict_label") or analysis_overview.verdict_label,
                "verdict_reason": agent3.get("verdict_reason") or analysis_overview.verdict_reason,
                "quality_status": agent3.get("quality_status") or "",
                "total_requirements": agent3.get("total_requirements") or 0,
                "completed_count": agent3.get("completed_count") or 0,
                "failed_count": agent3.get("failed_count") or 0,
                "technical_count": agent3.get("technical_count") or 0,
                "completed": agent3.get("completed") or [],
                "failed": agent3.get("failed") or [],
                "technical": agent3.get("technical") or [],
                "missing": agent3.get("missing") or [],
                "invalid": agent3.get("invalid") or [],
                "extra": agent3.get("extra") or [],
                "extra_code_risk": agent3.get("extra_code_risk") or "none",
                "requirements": agent3.get("requirements") or [],
            },
        )
        return result

    def _build_analysis_sections_from_decisions(
        self,
        *,
        decisions: list[dict[str, Any]],
        figma_data: dict[str, Any] | None,
        extra_issues: list[str],
    ) -> list[TZPRAnalysisSection]:
        by_status = {"completed": [], "failed": [], "manual_review": []}
        for item in decisions:
            status = str(item.get("status") or "failed").strip().lower()
            if bool(item.get("technical_failure")):
                status = "manual_review"
            if status not in {"completed", "failed", "manual_review"}:
                status = "failed"
            by_status.setdefault(status, []).append(item)

        issue_items = _build_issue_section_items(by_status.get("manual_review", []), extra_issues)
        figma_summaries = list((figma_data or {}).get("summaries") or [])
        figma_items = _figma_lines(figma_data) if figma_summaries else []

        section_items = {
            "completed": [_decision_matrix_item_text(item) for item in by_status.get("completed", [])],
            "failed": [_decision_matrix_item_text(item) for item in by_status.get("failed", [])],
            "issues": issue_items,
            "figma": figma_items,
        }

        return [
            TZPRAnalysisSection(
                key=key,
                title=FINAL_ANALYSIS_SECTION_TITLES[key],
                lines=list(items),
                items=list(items),
                item_count=len(items),
                empty=not bool(items),
            )
            for key, items in section_items.items()
        ]

    def _build_analysis_overview(
        self,
        *,
        analysis_sections: list[TZPRAnalysisSection],
        compliance_score: int | None,
        figma_data: dict[str, Any] | None,
        summary: str,
        verdict: str,
        verdict_label: str,
        verdict_reason: str,
    ) -> TZPRAnalysisOverview:
        derived_verdict, derived_label, derived_reason = self.service._derive_verdict(
            analysis_sections,
            compliance_score,
        )
        summary_lines: list[str] = []
        if compliance_score is not None:
            summary_lines.append(f"Compliance score: {compliance_score}%")
        if summary:
            summary_lines.append(summary)
        else:
            summary_lines = self.service._build_summary_lines(
                analysis_sections,
                compliance_score,
                figma_data,
            )

        section_counts = {
            section.key: section.item_count or len(section.lines)
            for section in analysis_sections
        }
        return TZPRAnalysisOverview(
            verdict=verdict or derived_verdict,
            verdict_label=verdict_label or derived_label,
            verdict_reason=verdict_reason or derived_reason,
            summary_lines=summary_lines,
            section_counts=section_counts,
            missing_figma_access=not self.service._has_usable_figma_data(figma_data),
            requested_sections=self.service._get_canonical_analysis_sections(),
        )

    def _build_blocked_result(self, error_message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._build_terminal_error_result(
            error_message,
            run_state="blocked",
            context=context,
        )

    def _build_terminal_error_result(
        self,
        error_message: str,
        *,
        run_state: str,
        context: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        effective_settings = (
            context.get("effective_settings")
            if context else self.service._build_effective_settings(
                requested_output_profile=self.output_profile,
                effective_use_smart_patch=self.use_smart_patch,
            )
        )
        result = self.service._create_error_result(
            self.task_key,
            error_message,
            task_summary=((context or {}).get("task_details") or {}).get("summary") or "",
            pr_info=((context or {}).get("pr_info") or None),
            warnings=warnings or [],
            figma_data=((context or {}).get("figma_data") or None),
            effective_settings=effective_settings,
        )
        result.execution_mode = self.execution_mode
        result.run_id = self.run_id
        result.run_state = run_state
        result.agent_runs = (get_checker_run_snapshot(self.run_id) or {}).get("agent_runs", [])
        result.run_events = (get_checker_run_snapshot(self.run_id) or {}).get("run_events", [])
        return asdict(result)

    def _handle_unexpected_run_failure(
        self,
        exc: Exception,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        message = str(exc).strip() or f"{_execution_mode_display_label(self.execution_mode)} run kutilmagan xato bilan to'xtadi."
        snapshot = get_checker_run_snapshot(self.run_id) or {}
        phase = str(snapshot.get("active_phase") or "unknown").strip() or "unknown"
        trace_excerpt = _summarize(traceback.format_exc(), 2400)
        log.error(f"[{self.task_key}] run-based unexpected failure ({phase}): {message}", exc_info=True)
        try:
            self._event(
                "error",
                "run_internal_error",
                f"{_execution_mode_display_label(self.execution_mode)} run kutilmagan xato bilan to'xtadi: {message}",
                meta={
                    "active_phase": phase,
                    "exception_type": exc.__class__.__name__,
                    "traceback_excerpt": trace_excerpt,
                },
            )
        except Exception:
            log.error(
                f"[{self.task_key}] run_internal_error eventini yozib bo'lmadi",
                exc_info=True,
            )

        self._block_remaining_agents(message)
        failure_result = self._build_terminal_error_result(
            message,
            run_state="failed",
            context=context,
            warnings=[
                "Run-based finalization yoki executor bosqichida kutilmagan ichki xato yuz berdi.",
                f"{exc.__class__.__name__}: {message}",
            ],
        )
        try:
            self._mark_run_finished("failed", failure_result, message)
        except Exception as finish_exc:
            log.error(
                f"[{self.task_key}] failed run holatini saqlashda qo'shimcha xato: {finish_exc}",
                exc_info=True,
            )
            update_checker_run_record(
                self.run_id,
                run_state="failed",
                active_phase="finished",
                status_message="Run ichki xato bilan tugadi",
                error_message=f"{message} | finish_error: {finish_exc}",
                finished_at=_now_iso(),
            )
