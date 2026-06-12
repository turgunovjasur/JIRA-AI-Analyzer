from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core import CommentSeparator
from services.checkers.tzpr_helpers import clean_candidate_text, normalize_text_for_dedupe


@dataclass(frozen=True)
class Agent1RulesConfig:
    figma_scope_enabled: bool = False


def agent1_rules_from_effective_settings(effective_settings: dict[str, Any] | None) -> Agent1RulesConfig:
    raw = dict((effective_settings or {}).get("agent1_rules") or {})
    defaults = Agent1RulesConfig()
    return Agent1RulesConfig(
        figma_scope_enabled=bool(raw.get("figma_scope_enabled", defaults.figma_scope_enabled)),
    )


def resolve_agent1_rules(rules: Agent1RulesConfig | None = None) -> Agent1RulesConfig:
    return rules if isinstance(rules, Agent1RulesConfig) else Agent1RulesConfig()


def parse_author_list(raw: str) -> list[str]:
    return [item.strip() for item in str(raw or "").split(",") if item.strip()]


def build_agent1_sanitized_input(
    *,
    task_details: dict[str, Any],
    trusted_authors: list[str],
    figma_data: dict[str, Any] | None,
    read_comments_enabled: bool,
    max_comments_to_read: int,
    rules: Agent1RulesConfig,
) -> dict[str, Any]:
    raw_comments = list(task_details.get("comments") or [])
    comments_to_read = raw_comments
    if read_comments_enabled and max_comments_to_read and max_comments_to_read > 0:
        comments_to_read = raw_comments[-max_comments_to_read:]

    trusted_lookup = {item.casefold() for item in trusted_authors}
    agent_comments: list[str] = []

    if read_comments_enabled:
        for comment in comments_to_read:
            body = str(comment.get("body") or "").strip()
            if not body:
                continue
            if CommentSeparator.is_ai_comment(comment):
                continue
            author = str(comment.get("author") or "Unknown").strip() or "Unknown"
            if author.casefold() in trusted_lookup:
                agent_comments.append(body)

    agent_figma: list[str] = []
    figma_access_status = build_figma_access_status(task_details=task_details, figma_data=figma_data)
    figma_enabled = bool(
        rules.figma_scope_enabled
        and figma_access_status.get("has_usable_data")
        and not (
            figma_access_status.get("explicit_unavailable")
            and not figma_access_status.get("has_usable_data")
        )
    )
    if figma_enabled:
        text_candidates, comment_candidates, _ = extract_figma_requirement_candidates(figma_data)
        for text in text_candidates:
            if str(text or "").strip():
                agent_figma.append(str(text).strip())
        for text in comment_candidates:
            if str(text or "").strip():
                agent_figma.append(str(text).strip())

    return {
        "tz": str(task_details.get("description") or ""),
        "comments": [item for item in agent_comments if item],
        "figma": [item for item in agent_figma if item],
    }


def select_agent3_dev_comments(
    *,
    comment_separated: dict[str, Any],
    task_details: dict[str, Any],
    read_comments_enabled: bool,
    dev_comment_source: str,
    max_comments_to_read: int,
) -> list[dict[str, Any]]:
    """
    Agent3 (arbiter) uchun dev commentlarni tanlaydi.

    - dev_before (oldindan) + dev_after (qaytargandan keyingi e'tiroz) birlashtiriladi.
    - AI commentlar chiqariladi.
    - dev_comment_source == "assignee_reporter" bo'lsa faqat task assignee va reporter
      commentlari olinadi; "all" bo'lsa barcha dev commentlar.
    """
    if not read_comments_enabled:
        return []

    combined: list[dict[str, Any]] = [
        comment
        for comment in [
            *(comment_separated.get("dev_before") or []),
            *(comment_separated.get("dev_after") or []),
        ]
        if isinstance(comment, dict)
        and str(comment.get("body") or "").strip()
        and not CommentSeparator.is_ai_comment(comment)
    ]

    if str(dev_comment_source or "").strip().lower() != "all":
        allowed = {
            str(task_details.get(key) or "").strip().casefold()
            for key in ("assignee", "reporter")
        }
        allowed.discard("")
        allowed.discard("unassigned")
        allowed.discard("unknown")
        combined = [
            comment
            for comment in combined
            if str(comment.get("author") or "").strip().casefold() in allowed
        ]

    if max_comments_to_read and max_comments_to_read > 0:
        combined = combined[-max_comments_to_read:]

    return [
        {
            "author": str(comment.get("author") or "Unknown").strip() or "Unknown",
            "body": str(comment.get("body") or "").strip(),
        }
        for comment in combined
    ]


def build_figma_access_status(
    *,
    task_details: dict[str, Any],
    figma_data: dict[str, Any] | None,
) -> dict[str, Any]:
    description = str(task_details.get("description") or "")
    comment_text = "\n".join(str(item.get("body") or "") for item in task_details.get("comments") or [])
    combined = f"{description}\n{comment_text}".casefold()
    explicit_unavailable = any(
        marker in combined
        for marker in (
            "figma недоступ",
            "figma недоступна",
            "figma недоступен",
            "figma unavailable",
            "figma access denied",
            "figma'ga kirish",
            "фигма недоступ",
        )
    )
    links = list((figma_data or {}).get("links") or task_details.get("figma_links") or [])
    summaries = list((figma_data or {}).get("summaries") or [])
    unusable_markers = (
        "token topilmadi",
        "ruxsat yo'q",
        "access yo'q",
        "error:",
        "olinmadi",
        "summary error",
    )
    has_usable_data = any(
        str(item.get("summary") or "").strip()
        and not any(marker in str(item.get("summary") or "").casefold() for marker in unusable_markers)
        for item in summaries
    )
    if not links and not summaries:
        status = "not_linked"
    elif explicit_unavailable and has_usable_data:
        status = "jira_says_unavailable_but_signals_present"
    elif explicit_unavailable:
        status = "explicitly_unavailable"
    elif has_usable_data:
        status = "usable"
    else:
        status = "unusable"
    return {
        "status": status,
        "explicit_unavailable": explicit_unavailable,
        "has_usable_data": has_usable_data,
        "link_count": len(links),
        "summary_count": len(summaries),
    }


def extract_figma_requirement_candidates(
    figma_data: dict[str, Any] | None,
    *,
    relevance_context: dict[str, Any] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    text_candidates: list[str] = []
    comment_candidates: list[str] = []
    discarded: list[str] = []
    current_frame: str = ""

    for item in list((figma_data or {}).get("summaries") or [])[:5]:
        section = None
        for raw_line in str(item.get("summary") or "").replace("\r", "").split("\n"):
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.startswith("🖼️"):
                current_frame = ""
                section = None
                discarded.append(f"figma-meta: {stripped}")
                continue
            if stripped.startswith("📝 FIGMA MATNLARI"):
                section = "texts"
                continue
            if stripped.startswith("💬 FIGMA COMMENT"):
                section = "comments"
                continue
            if stripped.startswith(("📐", "📅", "📑")):
                discarded.append(f"figma-meta: {stripped}")
                continue
            if stripped.startswith("─"):
                discarded.append(f"figma-separator: {stripped}")
                continue
            if section == "texts":
                candidate, item_frame = extract_figma_line_payload(stripped, expect_author=False)
                if not candidate or should_discard_figma_candidate(candidate):
                    discarded.append(f"figma-text-skip: {candidate or stripped}")
                    continue
                effective_frame = item_frame or current_frame
                labeled = f"[Frame: {effective_frame}] {candidate}" if effective_frame else candidate
                append_unique_text(text_candidates, labeled)
            elif section == "comments":
                candidate, item_frame = extract_figma_line_payload(stripped, expect_author=True)
                if not candidate or should_discard_figma_candidate(candidate):
                    discarded.append(f"figma-comment-skip: {candidate or stripped}")
                    continue
                effective_frame = item_frame or current_frame
                labeled = f"[Frame: {effective_frame}] {candidate}" if effective_frame else candidate
                append_unique_text(comment_candidates, labeled)
            else:
                discarded.append(f"figma-context: {stripped}")

    return text_candidates[:20], comment_candidates[:20], discarded


def extract_figma_line_payload(line: str, *, expect_author: bool) -> tuple[str, str]:
    text = re.sub(r"^\d+\.\s*", "", str(line or "").strip())

    frame_name = ""
    frame_match = re.match(r"^\[Frame:\s*([^\]]+)\]\s*", text)
    if frame_match:
        frame_name = frame_match.group(1).strip()
        text = text[frame_match.end():]

    if expect_author:
        parts = text.split(":", 1)
        if len(parts) == 2:
            text = parts[1].strip()
    else:
        text = re.sub(r"^\[[A-Z_]+\]\s*", "", text).strip()
        if ":" in text:
            text = text.split(":", 1)[1].strip()

    return clean_candidate_text(text), frame_name


def should_discard_figma_candidate(text: str) -> bool:
    candidate = clean_candidate_text(text)
    if not candidate:
        return True
    if len(candidate) < 18:
        return True
    if re.fullmatch(r"[\d\s.,/:;-]+", candidate):
        return True
    lowered = candidate.casefold()
    noise_markers = (
        "📐 figma",
        "📅 modified",
        "📑 pages",
        "size:",
        "elements:",
        "modified:",
    )
    if any(marker in lowered for marker in noise_markers):
        return True
    if re.fullmatch(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}", candidate.strip()):
        return True
    if re.search(r"(.)\1{9,}", candidate):
        return True
    if re.fullmatch(r"(?:спецзадача|task|задача)\s*\d+(?:[\s\d]*)?", lowered):
        return True
    return False


def append_unique_text(items: list[str], text: str) -> None:
    candidate = clean_candidate_text(text)
    if not candidate:
        return
    key = normalize_text_for_dedupe(candidate)
    existing = {normalize_text_for_dedupe(item) for item in items}
    if key in existing:
        return
    items.append(candidate)
