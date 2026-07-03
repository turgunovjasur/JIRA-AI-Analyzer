"""TZPRService natija/section/matritsa qurish helperlari (multi-agent result_builder ishlatadi).

P2/M1 refactor: TZPRService'dan ajratilgan mixin. Metodlar tanasi o'zgarmagan —
TZPRService bularni meros oladi, `self.` chaqiruvlar MRO orqali hal bo'ladi.
"""
from __future__ import annotations

import re
from fnmatch import fnmatch
from typing import Any, Dict, List, Optional

from core import RECHECK_REASONS
from core.logger import get_logger
from services.checkers.tzpr_models import (
    TZPRAnalysisOverview,
    TZPRAnalysisResult,
    TZPRAnalysisSection,
    TZPRCodeReference,
    TZPRCommentIntelligence,
    TZPRCommentSignal,
    TZPREvidenceItem,
    TZPRFigmaReference,
    TZPRQARecommendation,
    TZPRRequirementMatrixItem,
    TZPRRunInfo,
    TZPRTaskInfo,
    TZPRWorkflowInfo,
)

log = get_logger("tzpr.checker")

DEFAULT_EXCLUDED_FILE_PATTERNS = (
    "package-lock.json,yarn.lock,pnpm-lock.yaml,"
    ".next/*,dist/*,build/*,coverage/*,node_modules/*,vendor/*,"
    "*.min.*,*.map,*.generated.*,*.gen.*,generated/*,__generated__/*"
)


class ResultBuildersMixin:
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
        excluded_patterns = self._get_excluded_file_patterns()
        skipped_files: list[str] = []

        files_to_show = pr_info['files_changed']
        if max_files:
            files_to_show = min(files_to_show, max_files)

        lines.append("📊 PR Summary:")
        lines.append(f"   PR Count: {pr_info['pr_count']}")
        lines.append(f"   Files Changed: {pr_info['files_changed']}")
        lines.append(f"   Additions: +{pr_info['total_additions']}")
        lines.append(f"   Deletions: -{pr_info['total_deletions']}")
        if excluded_patterns:
            lines.append(f"   AI Excluded Patterns: {', '.join(excluded_patterns)}")
        lines.append("")

        for pr in pr_info['pr_details']:
            pr_files = list(pr.get('files') or [])
            filtered_files = []
            for file_data in pr_files:
                filename = str(file_data.get('filename') or '').strip()
                if filename and self._is_excluded_code_file(filename, excluded_patterns):
                    skipped_files.append(filename)
                    continue
                filtered_files.append(file_data)

            lines.append(f"🔗 PR: {pr['title']}")
            lines.append(f"   URL: {pr['url']}")
            lines.append(f"   Files: {len(pr_files)}")
            if skipped_files:
                lines.append(f"   Files skipped for AI context: {len(skipped_files)}")
            lines.append("")

            for idx, file_data in enumerate(filtered_files[:files_to_show]):
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

        if skipped_files:
            lines.append("AI contextdan chiqarilgan fayllar:")
            for filename in skipped_files[:30]:
                lines.append(f"- {filename}")
            if len(skipped_files) > 30:
                lines.append(f"- ... yana {len(skipped_files) - 30} ta fayl")
            lines.append("")

        return "\n".join(lines)

    def _get_excluded_file_patterns(self) -> list[str]:
        raw = str(
            getattr(self._get_settings(), "excluded_file_patterns", DEFAULT_EXCLUDED_FILE_PATTERNS)
            or ""
        )
        parts = re.split(r"[,\n]+", raw)
        return [part.strip() for part in parts if part.strip()]

    @staticmethod
    def _is_excluded_code_file(filename: str, patterns: list[str]) -> bool:
        normalized = filename.replace("\\", "/").strip().lower()
        basename = normalized.rsplit("/", 1)[-1]
        for pattern in patterns:
            candidate = pattern.replace("\\", "/").strip().lower()
            if not candidate:
                continue
            if fnmatch(normalized, candidate) or fnmatch(basename, candidate):
                return True
        return False

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

    def _build_task_info(self, task_details: Dict) -> TZPRTaskInfo:
        story_points_raw = task_details.get("story_points")
        try:
            story_points = float(story_points_raw) if story_points_raw not in (None, "") else None
        except (TypeError, ValueError):
            story_points = None

        return TZPRTaskInfo(
            key=str(task_details.get("key") or ""),
            summary=str(task_details.get("summary") or ""),
            issue_type=str(task_details.get("type") or ""),
            status=str(task_details.get("status") or ""),
            assignee=str(task_details.get("assignee") or ""),
            reporter=str(task_details.get("reporter") or ""),
            priority=str(task_details.get("priority") or ""),
            story_points=story_points,
            created_at=str(task_details.get("created") or ""),
            resolved_at=str(task_details.get("resolved") or ""),
            labels=list(task_details.get("labels") or []),
            components=list(task_details.get("components") or []),
        )

    def _build_run_info(
            self,
            effective_settings: Dict[str, Any],
            files_analyzed: int,
            total_files_changed: int,
            prompt_size_chars: int,
            ai_retry_count: int,
            ai_model: Optional[str] = None,
            ai_primary_model: Optional[str] = None,
            ai_fallback_model: Optional[str] = None,
            ai_used_fallback: bool = False,
    ) -> TZPRRunInfo:
        return TZPRRunInfo(
            source="manual" if self._user_id is not None else "webhook",
            requested_output_profile=str(effective_settings.get("requested_output_profile") or "ui"),
            comments_enabled=bool(effective_settings.get("read_comments_enabled", True)),
            max_comments_to_read=int(effective_settings.get("max_comments_to_read") or 0),
            smart_patch_enabled=bool(effective_settings.get("effective_use_smart_patch", False)),
            ai_data_section_order=list(effective_settings.get("ai_data_section_order") or []),
            files_analyzed=int(files_analyzed or 0),
            total_files_changed=int(total_files_changed or 0),
            prompt_size_chars=int(prompt_size_chars or 0),
            ai_retry_count=int(ai_retry_count or 0),
            ai_model=str(ai_model or ""),
            ai_primary_model=str(ai_primary_model or ""),
            ai_fallback_model=str(ai_fallback_model or ""),
            ai_used_fallback=bool(ai_used_fallback),
        )

    def _build_qa_recommendation(
            self,
            overview: Optional[TZPRAnalysisOverview],
            compliance_score: Optional[int],
    ) -> TZPRQARecommendation:
        if overview is None:
            return TZPRQARecommendation(
                action="manual_review",
                label="Manual review kerak",
                reason="Checker structured overview qaytarmadi.",
            )

        counts = overview.section_counts or {}
        if counts.get("failed", 0) > 0:
            return TZPRQARecommendation(
                action="return",
                label="Return qilish kerak",
                reason=f"{counts.get('failed', 0)} ta bajarilmagan talab topildi.",
            )

        if overview.missing_figma_access:
            return TZPRQARecommendation(
                action="manual_review",
                label="Manual review kerak",
                reason="Figma evidence cheklangan, dizayn bo'yicha yakuniy qaror uchun qo'shimcha tekshiruv kerak.",
            )

        if counts.get("partial", 0) > 0 or counts.get("issues", 0) > 0:
            total_open = counts.get("partial", 0) + counts.get("issues", 0)
            return TZPRQARecommendation(
                action="manual_review",
                label="Manual review kerak",
                reason=f"{total_open} ta qisman talab yoki potensial muammo bor.",
            )

        if compliance_score is None:
            return TZPRQARecommendation(
                action="manual_review",
                label="Manual review kerak",
                reason="Compliance score topilmadi.",
            )

        return TZPRQARecommendation(
            action="pass",
            label="Passed qilish mumkin",
            reason="Kritik nomoslik topilmadi, asosiy talablar mos deb baholandi.",
        )

    @staticmethod
    def _build_comment_signal(comment: Dict[str, Any], category: str) -> TZPRCommentSignal:
        body = str(comment.get("body") or comment.get("full_text") or "").strip()
        preview = str(comment.get("preview") or "").strip() or body[:200]
        if len(body) > 200 and not preview.endswith("...") and preview == body[:200]:
            preview = f"{preview}..."
        return TZPRCommentSignal(
            author=str(comment.get("author") or "Unknown"),
            created=str(comment.get("created") or ""),
            preview=preview,
            full_text=body,
            category=category,
        )

    @staticmethod
    def _is_deferred_scope_comment(text: str) -> bool:
        normalized = str(text or "").lower()
        deferred_markers = [
            "keyin qilinadi",
            "keyin qilamiz",
            "keyingi sprint",
            "keyingi sprintda",
            "later",
            "next sprint",
            "out of scope",
            "not in this pr",
            "bu pr doirasida emas",
            "alohida task",
            "separate task",
        ]
        return any(marker in normalized for marker in deferred_markers)

    def _build_comment_intelligence(
            self,
            comment_analysis: Optional[Dict[str, Any]],
            comment_separated: Optional[Dict[str, Any]],
            is_recheck: bool,
    ) -> TZPRCommentIntelligence:
        analysis = comment_analysis or {}
        separated = comment_separated or {}
        important_comments = [
            self._build_comment_signal(comment, "scope_change")
            for comment in analysis.get("important_comments", [])[:5]
        ]
        before_comments = list(separated.get("dev_before", []) or [])
        after_comments = list(separated.get("dev_after", []) or [])
        deferred_comments = [
            self._build_comment_signal(comment, "deferred_scope")
            for comment in [*before_comments, *after_comments]
            if self._is_deferred_scope_comment(comment.get("body") or comment.get("full_text") or "")
        ]
        dev_objections = [
            self._build_comment_signal(comment, "dev_objection")
            for comment in (after_comments if is_recheck else [])
        ]

        if deferred_comments:
            scope_note = "Developer comment'larda keyinga qoldirilgan yoki scope'dan tashqariga chiqarilgan talab signali bor."
        elif dev_objections:
            scope_note = "Oldingi checker commentidan keyin developer e'tiroz yoki izoh yozgan."
        elif analysis.get("has_changes"):
            scope_note = "Commentlarda talabni o'zgartiradigan signal bor, QA scope'ni shu izohlar bilan birga ko'rishi kerak."
        else:
            scope_note = "Muhim scope o'zgarishi topilmadi."

        return TZPRCommentIntelligence(
            summary=str(analysis.get("summary") or "Comment intelligence qaytmadi."),
            has_scope_changes=bool(analysis.get("has_changes", False)),
            change_count=int(analysis.get("change_count") or 0),
            total_comments=int(analysis.get("total_comments") or 0),
            filtered_out_ai_comments=int(analysis.get("filtered_out_ai_comments") or 0),
            has_dev_objections=bool(dev_objections),
            objection_count=len(dev_objections),
            deferred_scope_detected=bool(deferred_comments),
            scope_note=scope_note,
            important_comments=important_comments,
            deferred_scope_comments=deferred_comments,
            dev_objections=dev_objections,
        )

    def _build_workflow_info(
            self,
            task_key: str,
            compliance_score: Optional[int],
            is_recheck: bool,
    ) -> TZPRWorkflowInfo:
        settings = self._get_settings()
        source = "manual" if self._user_id is not None else "webhook"
        db_task: Dict[str, Any] = {}
        try:
            from utils.database.task_db import get_task
            try:
                db_task = get_task(task_key, company_id=self._company_id) or {}
            except TypeError:
                db_task = get_task(task_key) or {}
        except Exception as exc:
            log.warning(f"[{task_key}] Workflow info load failed: {exc}")

        threshold = int(getattr(settings, "return_threshold", 0) or 0)
        auto_return_enabled = bool(getattr(settings, "auto_return_enabled", False))
        db_score = db_task.get("compliance_score")
        effective_score = (
            int(db_score)
            if db_score not in (None, "")
            else (int(compliance_score) if compliance_score is not None else None)
        )

        if db_task.get("service1_status") == "blocked" or db_task.get("service2_status") == "blocked":
            note = "Task blocked holatda. Retry schedule yoki tashqi servis muammosi bor."
        elif is_recheck or db_task.get("return_reason") in RECHECK_REASONS:
            note = "Task oldin qaytarilgan va hozir re-check kontekstida ko'rilmoqda."
        elif auto_return_enabled and effective_score is not None and effective_score < threshold:
            note = "Compliance score thresholddan past bo'lsa webhook oqimida auto-return ishlashi mumkin."
        elif db_task:
            note = "Workflow yozuvi topildi, checker process signallarini DB'dan ko'rsatmoqda."
        else:
            note = "Bu run uchun webhook workflow yozuvi topilmadi. Manual checker konteksti bo'lishi mumkin."

        return TZPRWorkflowInfo(
            available=bool(db_task),
            source=source,
            task_status=str(db_task.get("task_status") or ""),
            service1_status=str(db_task.get("service1_status") or ""),
            service2_status=str(db_task.get("service2_status") or ""),
            compliance_score=effective_score,
            return_reason=str(db_task.get("return_reason") or ""),
            blocked_at=str(db_task.get("blocked_at") or ""),
            blocked_retry_at=str(db_task.get("blocked_retry_at") or ""),
            updated_at=str(db_task.get("updated_at") or ""),
            return_threshold=threshold,
            auto_return_enabled=auto_return_enabled,
            is_recheck=is_recheck,
            note=note,
        )

    def _build_requirement_matrix(
            self,
            analysis_sections: List[TZPRAnalysisSection],
            task_details: Dict[str, Any],
            pr_details: List[Dict[str, Any]],
            figma_data: Optional[Dict[str, Any]],
            comment_analysis: Optional[Dict[str, Any]],
    ) -> List[TZPRRequirementMatrixItem]:
        status_meta = {
            "completed": ("completed", "Bajarilgan"),
            "partial": ("partial", "Qisman bajarilgan"),
            "failed": ("failed", "Bajarilmagan"),
            "skipped": ("skipped", "Skip qilingan (dev izohi)"),
        }
        pr_file_index = self._build_pr_file_index(pr_details)
        figma_summaries = list((figma_data or {}).get("summaries") or [])
        important_comments = list((comment_analysis or {}).get("important_comments") or [])
        matrix: List[TZPRRequirementMatrixItem] = []

        for section in analysis_sections or []:
            if section.key not in status_meta:
                continue

            items = [item for item in (section.items or section.lines or []) if str(item or "").strip()]
            for index, item_text in enumerate(items, start=1):
                parsed = self._parse_requirement_item(item_text)
                evidence: List[TZPREvidenceItem] = []

                for note in parsed["evidence_notes"][:1]:
                    evidence.append(
                        TZPREvidenceItem(
                            source="analysis",
                            label="Gemini evidence",
                            detail=str(note or "").strip(),
                        )
                    )

                if task_details.get("summary") or task_details.get("description"):
                    evidence.append(
                        TZPREvidenceItem(
                            source="tz",
                            label="Task context",
                            detail=self._summarize_text(
                                task_details.get("summary") or task_details.get("description"),
                                limit=180,
                            ),
                        )
                    )

                if important_comments:
                    top_comment = important_comments[0]
                    evidence.append(
                        TZPREvidenceItem(
                            source="comment",
                            label=f"Comment: {top_comment.get('author') or 'Unknown'}",
                            detail=self._summarize_text(top_comment.get("preview") or "", limit=180),
                        )
                    )

                if pr_details:
                    top_pr = pr_details[0]
                    evidence.append(
                        TZPREvidenceItem(
                            source="pr",
                            label=f"PR #{top_pr.get('number') or '?'}",
                            detail=self._summarize_text(top_pr.get("title") or "", limit=180),
                            url=str(top_pr.get("url") or ""),
                        )
                    )

                if figma_summaries:
                    top_figma = figma_summaries[0]
                    evidence.append(
                        TZPREvidenceItem(
                            source="figma",
                            label=str(top_figma.get("name") or top_figma.get("file_key") or "Figma summary"),
                            detail=self._summarize_text(top_figma.get("summary") or "", limit=180),
                            url=str(top_figma.get("url") or ""),
                        )
                    )

                status_value, status_label = status_meta[section.key]
                resolved_files = parsed["code_files"] or self._infer_requirement_files_from_text(
                    str(item_text or ""),
                    pr_file_index,
                )
                code_refs = [
                    TZPRCodeReference(
                        filename=file_name,
                        blob_url=str((pr_file_index.get(file_name) or {}).get("blob_url") or ""),
                        pr_number=(pr_file_index.get(file_name) or {}).get("pr_number"),
                        pr_url=str((pr_file_index.get(file_name) or {}).get("pr_url") or ""),
                        change_type=str((pr_file_index.get(file_name) or {}).get("change_type") or ""),
                        additions=(pr_file_index.get(file_name) or {}).get("additions"),
                        deletions=(pr_file_index.get(file_name) or {}).get("deletions"),
                        line_start=(pr_file_index.get(file_name) or {}).get("line_start"),
                        line_end=(pr_file_index.get(file_name) or {}).get("line_end"),
                        patch_preview=str((pr_file_index.get(file_name) or {}).get("patch_preview") or ""),
                    )
                    for file_name in resolved_files
                ]
                notes = parsed["notes"] or {
                    "completed": "Gemini bu talabni bajarilgan deb baholagan.",
                    "partial": "Gemini bu talabni qisman bajarilgan deb baholagan.",
                    "failed": "Gemini bu talabni bajarilmagan deb baholagan.",
                    "skipped": "Dev izohi asosida skip qilingan — manual tekshiruv kerak.",
                }[section.key]
                figma_relation = parsed["figma_relation"] or (
                    "Figma bo'yicha ishonchli xulosa yo'q."
                    if not figma_summaries
                    else "Figma summary mavjud, lekin requirement-level node mapping hali chiqarilmagan."
                )
                figma_sources = [
                    TZPRFigmaReference(
                        name=str(item.get("name") or ""),
                        file_key=str(item.get("file_key") or ""),
                        url=str(item.get("url") or ""),
                        node_id=self._extract_figma_node_id(str(item.get("url") or "")),
                        summary=self._summarize_text(item.get("summary") or "", limit=220),
                    )
                    for item in figma_summaries[:2]
                ]

                matrix.append(
                    TZPRRequirementMatrixItem(
                        id=f"{section.key}-{index}",
                        status=status_value,
                        status_label=status_label,
                        requirement=parsed["requirement"],
                        requirement_source=parsed["requirement_source"],
                        evidence=evidence[:4],
                        code_files=resolved_files,
                        code_refs=code_refs,
                        figma_relation=figma_relation,
                        figma_sources=figma_sources,
                        notes=notes,
                    )
                )

        return matrix

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
            effective_settings: Optional[Dict[str, Any]] = None,
            error: Optional[BaseException] = None,
    ) -> TZPRAnalysisResult:
        """Create error result.

        `error` — typed exception (core/errors.py). Dataclass field emas
        (asdict/DB payload o'zgarmasin) — jonli obyektga atribut sifatida
        biriktiriladi; webhook `_classify_error` avval shuni tekshiradi.
        """
        result = TZPRAnalysisResult(
            task_key=task_key,
            task_summary=task_summary,
            tz_content=tz_content,
            pr_count=pr_info['pr_count'] if pr_info else 0,
            files_changed=pr_info['files_changed'] if pr_info else 0,
            pr_details=pr_info['pr_details'] if pr_info else [],
            pr_selection=pr_info.get('pr_selection', {}) if pr_info else {},
            success=False,
            error_message=error_message,
            warnings=warnings or [],
            figma_data=figma_data,
            status_banner=status_banner,
            ai_retry_count=ai_retry_count,
            files_analyzed=files_analyzed,
            total_prompt_size=total_prompt_size,
            effective_settings=effective_settings or {},
            execution_mode="multi_agent",
            run_state="blocked" if status_banner else "failed",
        )
        if error is not None:
            result.typed_error = error
        return result
