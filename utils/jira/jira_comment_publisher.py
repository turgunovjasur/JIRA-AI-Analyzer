from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any, Callable

from core.logger import get_logger
from utils.jira.jira_comment_writer import JiraCommentWriter

log = get_logger("jira.comment.publisher")


JIRA_COMMENT_TARGET_CHARS = 30_000
JIRA_COMMENT_RETRY_TARGET_CHARS = 15_000


def _document(content: list[dict]) -> dict:
    return {"version": 1, "type": "doc", "content": content}


def adf_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def split_text_lossless(text: str, max_chars: int) -> list[str]:
    if max_chars < 1:
        raise ValueError("max_chars 1 yoki undan katta bo'lishi kerak")
    if not text:
        return []

    chunks: list[str] = []
    offset = 0
    while len(text) - offset > max_chars:
        window = text[offset:offset + max_chars]
        boundaries = (
            window.rfind("\n") + 1,
            window.rfind(". ") + 2,
            window.rfind(" ") + 1,
        )
        split_at = max((value for value in boundaries if value > 0), default=max_chars)
        chunks.append(text[offset:offset + split_at])
        offset += split_at
    if offset < len(text):
        chunks.append(text[offset:])
    return chunks


def _node_text(node: dict) -> str:
    if node.get("type") == "text":
        return str(node.get("text") or "")
    return "".join(
        _node_text(child)
        for child in node.get("content", [])
        if isinstance(child, dict)
    )


def _clone_with_content(node: dict, content: list[dict]) -> dict:
    cloned = copy.deepcopy(node)
    cloned["content"] = content
    return cloned


def _max_text_chars(node: dict, max_size: int) -> int:
    text = str(node.get("text") or "")
    low = 1
    high = max(1, len(text))
    best = 0
    while low <= high:
        middle = (low + high) // 2
        candidate = copy.deepcopy(node)
        candidate["text"] = text[:middle]
        if adf_size(_document([candidate])) <= max_size:
            best = middle
            low = middle + 1
        else:
            high = middle - 1
    return best


def _split_node(node: dict, max_size: int) -> list[dict]:
    if adf_size(_document([node])) <= max_size:
        return [copy.deepcopy(node)]

    if node.get("type") == "text":
        chunk_size = _max_text_chars(node, max_size)
        if chunk_size < 1:
            raise ValueError("ADF text node berilgan limitga sig'maydi")
        chunks = split_text_lossless(str(node.get("text") or ""), chunk_size)
        result = []
        for chunk in chunks:
            cloned = copy.deepcopy(node)
            cloned["text"] = chunk
            result.append(cloned)
        return result

    children = node.get("content")
    if not isinstance(children, list) or not children:
        raise ValueError(f"ADF {node.get('type')} node berilgan limitga sig'maydi")

    empty_size = adf_size(_document([_clone_with_content(node, [])]))
    base_size = adf_size(_document([]))
    child_limit = max_size - (empty_size - base_size)
    if child_limit < 1:
        raise ValueError(f"ADF {node.get('type')} container overhead limitdan katta")

    split_children: list[dict] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        split_children.extend(_split_node(child, child_limit))

    result: list[dict] = []
    current: list[dict] = []
    for child in split_children:
        candidate = _clone_with_content(node, current + [child])
        if current and adf_size(_document([candidate])) > max_size:
            result.append(_clone_with_content(node, current))
            current = [child]
        else:
            current.append(child)
        if adf_size(_document([_clone_with_content(node, current)])) > max_size:
            raise ValueError(f"ADF {node.get('type')} child berilgan limitga sig'maydi")
    if current:
        result.append(_clone_with_content(node, current))
    return result


def _paragraph(text: str) -> dict:
    return {
        "type": "paragraph",
        "content": [{"type": "text", "text": text}],
    }


def _part_header(
    marker: str,
    task_key: str,
    part_index: int,
    part_count: int,
    repeated_heading: dict | None,
) -> list[dict]:
    content = [_paragraph(marker)]
    if repeated_heading is not None:
        content.append(copy.deepcopy(repeated_heading))
    content.append(_paragraph(f"Task: {task_key} · Qism: {part_index}/{part_count}"))
    return content


def split_adf_document(
    document: dict,
    *,
    max_chars: int,
    marker: str,
    task_key: str,
) -> list[dict]:
    if max_chars < 200:
        raise ValueError("ADF part limiti kamida 200 bo'lishi kerak")

    source_content = [
        copy.deepcopy(node)
        for node in document.get("content", [])
        if isinstance(node, dict)
    ]
    if source_content and _node_text(source_content[0]).strip() == marker:
        source_content.pop(0)

    repeated_heading = None
    if source_content and source_content[0].get("type") == "heading":
        repeated_heading = source_content.pop(0)

    placeholder_header = _part_header(
        marker,
        task_key,
        part_index=9999,
        part_count=9999,
        repeated_heading=repeated_heading,
    )
    header_overhead = adf_size(_document(placeholder_header)) - adf_size(_document([]))
    node_limit = max_chars - header_overhead - 16
    if node_limit < 1:
        raise ValueError("ADF marker va part sarlavhasi limitga sig'maydi")

    body_nodes: list[dict] = []
    for node in source_content:
        body_nodes.extend(_split_node(node, node_limit))

    body_parts: list[list[dict]] = []
    current: list[dict] = []
    for node in body_nodes:
        candidate = _document(placeholder_header + current + [node])
        if current and adf_size(candidate) > max_chars:
            body_parts.append(current)
            current = [node]
        else:
            current.append(node)
        if adf_size(_document(placeholder_header + current)) > max_chars:
            raise ValueError("ADF node part sarlavhasi bilan limitga sig'maydi")
    if current or not body_parts:
        body_parts.append(current)

    part_count = len(body_parts)
    parts = [
        _document(
            _part_header(
                marker,
                task_key,
                part_index=index,
                part_count=part_count,
                repeated_heading=repeated_heading,
            ) + body
        )
        for index, body in enumerate(body_parts, 1)
    ]
    if any(adf_size(part) > max_chars for part in parts):
        raise ValueError("ADF part yakuniy metadata bilan limitdan oshdi")
    return parts


@dataclass(frozen=True)
class JiraCommentPublishResult:
    success: bool
    part_count: int = 0
    split: bool = False
    error: str = ""


def _hint_document(
    marker: str,
    service_name: str,
    task_key: str,
    part_count: int,
) -> dict:
    return _document([
        _paragraph(marker),
        _paragraph(
            f"ℹ️ {service_name} hisoboti JIRA comment hajmi limitidan oshdi. "
            f"To'liq natija qisqartirilmasdan {part_count} ta commentga bo'lib yuboriladi."
        ),
        _paragraph(f"Task: {task_key}"),
    ])


class JiraCommentPublisher:
    def __init__(
        self,
        writer: JiraCommentWriter,
        target_chars: int = JIRA_COMMENT_TARGET_CHARS,
    ):
        self.writer = writer
        self.target_chars = target_chars

    def publish_adf(
        self,
        task_key: str,
        document: dict,
        *,
        marker: str,
        service_name: str,
        simple_fallback: Callable[[], str] | None = None,
    ) -> JiraCommentPublishResult:
        if adf_size(document) <= self.target_chars:
            write_result = self.writer.add_comment_adf_result(task_key, document)
            if write_result.success:
                return JiraCommentPublishResult(success=True, part_count=1)
            if not write_result.content_limit_exceeded:
                if simple_fallback is not None:
                    return self.publish_text(
                        task_key,
                        simple_fallback(),
                        marker=marker,
                        service_name=service_name,
                    )
                return JiraCommentPublishResult(
                    success=False,
                    error=write_result.error or write_result.response_text,
                )

        split_target = self.target_chars
        if adf_size(document) <= self.target_chars:
            split_target = min(
                JIRA_COMMENT_RETRY_TARGET_CHARS,
                max(400, self.target_chars // 2),
            )
        try:
            parts = split_adf_document(
                document,
                max_chars=split_target,
                marker=marker,
                task_key=task_key,
            )
        except Exception as exc:
            log.log_error(task_key, service_name, f"ADF split failed: {exc}")
            if simple_fallback is not None:
                return self.publish_text(
                    task_key,
                    simple_fallback(),
                    marker=marker,
                    service_name=service_name,
                )
            return JiraCommentPublishResult(success=False, error=str(exc))

        hint_result = self.writer.add_comment_adf_result(
            task_key,
            _hint_document(marker, service_name, task_key, len(parts)),
        )
        if not hint_result.success:
            return JiraCommentPublishResult(
                success=False,
                part_count=len(parts),
                split=True,
                error=hint_result.error or hint_result.response_text,
            )

        for index, part in enumerate(parts, 1):
            part_result = self.writer.add_comment_adf_result(task_key, part)
            if not part_result.success:
                log.log_error(
                    task_key,
                    service_name,
                    f"Comment part {index}/{len(parts)} failed: "
                    f"{part_result.error or part_result.response_text}",
                )
                return JiraCommentPublishResult(
                    success=False,
                    part_count=len(parts),
                    split=True,
                    error=part_result.error or part_result.response_text,
                )
        return JiraCommentPublishResult(
            success=True,
            part_count=len(parts),
            split=True,
        )

    def publish_text(
        self,
        task_key: str,
        text: str,
        *,
        marker: str,
        service_name: str,
    ) -> JiraCommentPublishResult:
        if len(text) <= self.target_chars:
            success = self.writer.add_comment(task_key, text)
            return JiraCommentPublishResult(
                success=success,
                part_count=1 if success else 0,
                error="" if success else f"{service_name} simple comment yozilmadi",
            )

        placeholder_header = f"{marker}\nTask: {task_key} · Qism: 9999/9999\n\n"
        body_limit = self.target_chars - len(placeholder_header)
        if body_limit < 1:
            return JiraCommentPublishResult(
                success=False,
                error=f"{service_name} simple comment header limitga sig'maydi",
            )
        chunks = split_text_lossless(text, body_limit)
        hint = (
            f"{marker}\n\n"
            f"ℹ️ {service_name} hisoboti JIRA comment hajmi limitidan oshdi. "
            f"To'liq natija qisqartirilmasdan {len(chunks)} ta commentga bo'lib yuboriladi.\n"
            f"Task: {task_key}"
        )
        if not self.writer.add_comment(task_key, hint):
            return JiraCommentPublishResult(
                success=False,
                part_count=len(chunks),
                split=True,
                error=f"{service_name} simple split hint yozilmadi",
            )

        for index, chunk in enumerate(chunks, 1):
            header = f"{marker}\nTask: {task_key} · Qism: {index}/{len(chunks)}\n\n"
            if not self.writer.add_comment(task_key, header + chunk):
                return JiraCommentPublishResult(
                    success=False,
                    part_count=len(chunks),
                    split=True,
                    error=f"{service_name} simple part {index}/{len(chunks)} yozilmadi",
                )
        return JiraCommentPublishResult(
            success=True,
            part_count=len(chunks),
            split=True,
        )
