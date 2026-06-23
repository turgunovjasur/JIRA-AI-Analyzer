from __future__ import annotations

from typing import Any

from services.checkers.tzpr_constants import FINAL_ANALYSIS_SECTION_TITLES


def calculate_compliance_score_from_agent3(agent3: dict[str, Any]) -> int | None:
    try:
        total = int(agent3.get("total_requirements") or 0)
        completed = int(agent3.get("completed_count") or 0)
        technical = int(agent3.get("technical_count") or 0)
        skipped = int(agent3.get("skipped_count") or 0)
    except (TypeError, ValueError):
        total = 0
        completed = 0
        technical = 0
        skipped = 0
    if total <= 0:
        decisions = list(agent3.get("requirements") or [])
        if not decisions:
            return 0
        total = len(decisions)
        technical = sum(
            1
            for item in decisions
            if str(item.get("status") or "").strip().lower() == "manual_review"
            or bool(item.get("technical_failure"))
        )
        skipped = sum(
            1
            for item in decisions
            if str(item.get("status") or "").strip().lower() == "skipped"
        )
        completed = sum(
            1
            for item in decisions
            if str(item.get("status") or "").strip().lower() == "completed"
        )
    # Skip qilingan (dev izohi) va technical requirementlar balъ maxrajiga kirmaydi.
    verifiable_total = max(total - technical - skipped, 0)
    if verifiable_total <= 0:
        # Talablar bor, lekin hammasi skip/technical — ballash mumkin emas.
        # 0 qaytarish xato auto-return'ga olib keladi; manual review uchun None.
        return None
    return max(0, min(100, round((completed / verifiable_total) * 100)))


def build_final_analysis_text(
    *,
    summary: str,
    decisions: list[dict[str, Any]],
    compliance_score: int | None,
    figma_data: dict[str, Any] | None,
    extra_issues: list[str],
) -> str:
    by_status = {"completed": [], "failed": [], "skipped": [], "manual_review": []}
    for item in decisions:
        status = str(item.get("status") or "failed").strip().lower()
        if bool(item.get("technical_failure")):
            status = "manual_review"
        if status not in {"completed", "failed", "skipped", "manual_review"}:
            status = "failed"
        by_status.setdefault(status, []).append(item)
    issue_items = build_issue_section_items(by_status.get("manual_review", []), extra_issues)
    figma_summaries = list((figma_data or {}).get("summaries") or [])
    figma_output_lines = figma_lines(figma_data) if figma_summaries else ["Figma ma'lumotlari olinmadi yoki signal qaytmadi."]

    sections = [
        "## 🧭 XULOSA",
        summary or "Multi-agent checker yakuniy xulosa qaytardi.",
        "",
        f"## {FINAL_ANALYSIS_SECTION_TITLES['completed']}",
        *decision_lines(by_status.get("completed", [])),
        "",
        f"## {FINAL_ANALYSIS_SECTION_TITLES['failed']}",
        *decision_lines(by_status.get("failed", [])),
        "",
        f"## {FINAL_ANALYSIS_SECTION_TITLES['skipped']}",
        *decision_lines(by_status.get("skipped", [])),
        "",
        f"## {FINAL_ANALYSIS_SECTION_TITLES['issues']}",
        *issue_items,
        "",
        f"## {FINAL_ANALYSIS_SECTION_TITLES['figma']}",
        *figma_output_lines,
        "",
        "## 📊 MOSLIK BALI",
        (
            f"**COMPLIANCE_SCORE: {compliance_score}%**"
            if compliance_score is not None
            else "**COMPLIANCE_SCORE: N/A — barcha talablar skip/technical, manual review kerak**"
        ),
    ]
    return "\n".join(sections).strip()


def decision_matrix_item_text(item: dict[str, Any]) -> str:
    requirement = str(item.get("text") or "").strip()
    if not requirement:
        requirement = str(item.get("id") or "Talab matni qaytmadi.").strip()
    requirement = requirement.replace("|", "/")

    segments = [f"Talab: {requirement}"]
    requirement_source = str(item.get("source") or item.get("requirement_source") or "").strip()
    if requirement_source:
        segments.append(f"Source: {requirement_source}")

    observed = str(item.get("evidence") or "").strip().replace("|", "/")
    if observed:
        segments.append(f"Evidence: {observed}")

    source_files: list[str] = []
    raw_files = item.get("files") or []
    raw_code_files = item.get("code_files") or []
    if isinstance(raw_files, str):
        raw_files = [raw_files]
    if isinstance(raw_code_files, str):
        raw_code_files = [raw_code_files]
    for file_name in list(raw_files) + list(raw_code_files):
        text = str(file_name).strip()
        if text:
            source_files.append(text)
    for source in item.get("sources") or []:
        if not isinstance(source, dict):
            continue
        file_name = str(source.get("file") or source.get("filename") or "").strip()
        if file_name:
            source_files.append(file_name)
    files = ", ".join(dict.fromkeys(source_files))
    if files:
        segments.append(f"File: {files}")

    figma_relation = str(item.get("figma_relation") or "").strip().replace("|", "/")
    if not figma_relation:
        figma_sources = [
            str(source.get("url") or source.get("note") or source.get("symbol") or "").strip()
            for source in item.get("sources") or []
            if isinstance(source, dict) and str(source.get("type") or "").strip().lower() == "figma"
        ]
        figma_relation = ", ".join(item for item in figma_sources if item)
    if figma_relation:
        segments.append(f"Figma: {figma_relation}")

    note = str(item.get("note") or "").strip().replace("|", "/")
    if note:
        segments.append(f"Note: {note}")

    return " | ".join(segments)


def decision_lines(items: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. Talab: {item.get('text')}")
        observed = str(item.get("evidence") or "").strip()
        if observed:
            lines.append(f"* Evidence: {observed}")
        files = ", ".join(item.get("files") or [])
        if files:
            lines.append(f"* File: {files}")
        figma_relation = str(item.get("figma_relation") or "").strip()
        if figma_relation:
            lines.append(f"* Figma: {figma_relation}")
        note = str(item.get("note") or "").strip()
        if note:
            lines.append(f"* Note: {note}")
        lines.append("")
    return [line for line in lines if line != "" or lines]


def decision_issue_lines(items: list[dict[str, Any]]) -> list[str]:
    lines = []
    for item in items:
        lines.append(
            f"- Talab `{item.get('id')}` bo'yicha verifier aniq xulosa qaytarmadi; manual review kerak."
        )
    return lines


def build_issue_section_items(contract_gap_items: list[dict[str, Any]], extra_issues: list[str]) -> list[str]:
    lines: list[str] = []
    contract_gap_count = len(contract_gap_items or [])
    if contract_gap_count:
        requirement_ids = [
            str(item.get("id") or "").strip()
            for item in contract_gap_items[:3]
            if str(item.get("id") or "").strip()
        ]
        suffix = ""
        if requirement_ids:
            suffix = f" ({', '.join(requirement_ids)})"
            remaining = contract_gap_count - len(requirement_ids)
            if remaining > 0:
                suffix = f"{suffix} va yana {remaining} ta"
        lines.append(
            f"{contract_gap_count} ta talab bo'yicha Agent2 verification qaytarmadi; Agent3 contract gap aniqladi{suffix}."
        )
    lines.extend(str(item).strip() for item in (extra_issues or []) if str(item).strip())
    return list(dict.fromkeys(lines))


def figma_lines(figma_data: dict[str, Any] | None) -> list[str]:
    summaries = list((figma_data or {}).get("summaries") or [])
    if not summaries:
        return ["Figma ma'lumotlari olinmadi yoki signal qaytmadi."]
    lines = []
    for item in summaries[:3]:
        label = str(item.get("name") or item.get("file_key") or "Figma")
        summary = str(item.get("summary") or "").strip() or "Summary qaytmadi."
        lines.append(f"- {label}: {summary}")
    return lines


def build_extra_issue_lines(agent1: dict[str, Any], agent2: dict[str, Any], agent3: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for warning in collect_final_warnings(agent1, agent2, agent3):
        lines.append(f"- {warning}")
    for item in agent3.get("extra") or agent2.get("extra") or []:
        if not isinstance(item, dict):
            continue
        description = str(item.get("text") or item.get("description") or "").strip()
        risk = str(item.get("risk") or "").strip()
        files = ", ".join(str(file_name).strip() for file_name in (item.get("files") or []) if str(file_name).strip())
        if description:
            suffix = f" ({files})" if files else ""
            risk_suffix = f" [risk: {risk}]" if risk else ""
            lines.append(f"- Extra code change: {description}{risk_suffix}{suffix}")
    return list(dict.fromkeys([line for line in lines if line.strip()]))


def collect_final_warnings(*agents: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for agent in agents:
        for item in agent.get("warnings") or []:
            text = str(item or "").strip()
            if text and text not in warnings:
                warnings.append(text)
    return warnings
