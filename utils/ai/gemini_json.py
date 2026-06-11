from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GeminiJsonParseResult:
    ok: bool
    data: Any | None
    raw_length: int
    raw_excerpt: str
    used_cleanup: bool = False
    used_repair: bool = False
    repair_type: str | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


def parse_gemini_json(raw: str) -> GeminiJsonParseResult:
    original = str(raw or "")
    text = original.strip()
    raw_length = len(original)
    raw_excerpt = _summarize(original, 600)
    warnings: list[str] = []
    used_cleanup = False

    if not text:
        return GeminiJsonParseResult(
            ok=False,
            data=None,
            raw_length=raw_length,
            raw_excerpt=raw_excerpt,
            error="empty_response",
        )

    cleaned = strip_markdown_fence(text)
    if cleaned != text:
        text = cleaned
        used_cleanup = True

    parsed = _loads(text)
    if parsed.ok:
        return GeminiJsonParseResult(
            ok=True,
            data=parsed.data,
            raw_length=raw_length,
            raw_excerpt=raw_excerpt,
            used_cleanup=used_cleanup,
            repair_type="cleaned_fenced_json" if used_cleanup else "parsed_json",
        )

    objects = extract_balanced_json_objects(text)
    if len(objects) > 1:
        warnings.append("multiple_json_objects_detected")
    if objects:
        object_text = max(objects, key=len)
        parsed = _loads(object_text)
        if parsed.ok:
            return GeminiJsonParseResult(
                ok=True,
                data=parsed.data,
                raw_length=raw_length,
                raw_excerpt=raw_excerpt,
                used_cleanup=True,
                repair_type="extracted_json_object",
                warnings=warnings,
            )
        repaired = repair_json_text(object_text)
        if repaired is not None:
            return GeminiJsonParseResult(
                ok=True,
                data=repaired,
                raw_length=raw_length,
                raw_excerpt=raw_excerpt,
                used_cleanup=True,
                used_repair=True,
                repair_type="repaired_extracted_json_object",
                warnings=warnings,
            )

    candidate = json_tail_candidate(text)
    if candidate:
        repaired = repair_json_text(candidate)
        if repaired is not None:
            return GeminiJsonParseResult(
                ok=True,
                data=repaired,
                raw_length=raw_length,
                raw_excerpt=raw_excerpt,
                used_cleanup=used_cleanup or candidate != text,
                used_repair=True,
                repair_type="balanced_truncated_json",
                warnings=warnings,
            )

    repaired = repair_json_text(text)
    if repaired is not None:
        return GeminiJsonParseResult(
            ok=True,
            data=repaired,
            raw_length=raw_length,
            raw_excerpt=raw_excerpt,
            used_cleanup=used_cleanup,
            used_repair=True,
            repair_type="local_repair",
            warnings=warnings,
        )

    return GeminiJsonParseResult(
        ok=False,
        data=None,
        raw_length=raw_length,
        raw_excerpt=raw_excerpt,
        used_cleanup=used_cleanup,
        error=parsed.error or "json_parse_failed",
        warnings=warnings,
    )


def strip_markdown_fence(raw: str) -> str:
    text = str(raw or "").strip()
    if not text.startswith("```"):
        return text
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def json_tail_candidate(raw: str) -> str | None:
    text = str(raw or "").strip()
    starts = [index for index in (text.find("{"), text.find("[")) if index >= 0]
    if not starts:
        return None
    return text[min(starts):].strip()


def repair_json_text(raw: str) -> Any | None:
    text = str(raw or "").strip()
    if not text:
        return None

    candidates = [text]
    repaired = text
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    repaired = re.sub(r"([}\]])\s*(\{)", r"\1,\2", repaired)
    repaired = re.sub(r"([}\]\"])\s*(\"[A-Za-z_][A-Za-z0-9_]*\"\s*:)", r"\1,\2", repaired)
    candidates.append(repaired)

    balanced = balance_json_tail(repaired)
    if balanced != repaired:
        candidates.append(balanced)

    for candidate in candidates:
        parsed = _loads(candidate)
        if parsed.ok:
            return parsed.data
    return None


def balance_json_tail(raw: str) -> str:
    text = str(raw or "").rstrip()
    stack: list[str] = []
    in_string = False
    escaped = False

    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char in "{[":
            stack.append(char)
        elif char == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif char == "]" and stack and stack[-1] == "[":
            stack.pop()

    if in_string:
        text += '"'
    closers = {"{": "}", "[": "]"}
    return text + "".join(closers[item] for item in reversed(stack))


def extract_balanced_json_objects(raw: str) -> list[str]:
    objects: list[str] = []
    stack: list[int] = []
    in_string = False
    escaped = False

    for index, char in enumerate(str(raw or "")):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char == "{":
            stack.append(index)
            continue
        if char == "}" and stack:
            start = stack.pop()
            objects.append(str(raw or "")[start : index + 1])

    return objects


@dataclass
class _LoadResult:
    ok: bool
    data: Any | None = None
    error: str | None = None


def _loads(raw: str) -> _LoadResult:
    try:
        return _LoadResult(ok=True, data=json.loads(raw))
    except json.JSONDecodeError as exc:
        return _LoadResult(ok=False, error=str(exc))


def _summarize(value: str, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."
