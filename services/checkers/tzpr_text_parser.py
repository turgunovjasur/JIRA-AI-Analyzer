"""TZPRService matn/patch/figma parse leaf-helperlari (multi-agent matritsa qurishda ishlatiladi).

P2/M1 refactor: TZPRService'dan ajratilgan mixin. Metodlar tanasi o'zgarmagan —
TZPRService bularni meros oladi, `self.` chaqiruvlar MRO orqali hal bo'ladi.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from core.logger import get_logger

log = get_logger("tzpr.checker")


class TextParserMixin:
    @staticmethod
    def _clean_analysis_line(value: str) -> str:
        return (
            (value or "")
            .replace("\r", "")
            .replace("**", "")
            .replace("`", "")
            .strip()
        )

    @staticmethod
    def _strip_analysis_item_leader(line: str) -> str:
        normalized = str(line or "").lstrip()
        normalized = re.sub(r"^[-*•]\s+", "", normalized)
        normalized = re.sub(r"^\d+\.\s+", "", normalized)
        normalized = re.sub(r"^[✅⚠️❌🐛📌]\s*", "", normalized)
        return normalized.strip()

    @staticmethod
    def _summarize_text(value: Any, limit: int = 160) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if len(text) <= limit:
            return text
        return f"{text[: max(limit - 1, 0)].rstrip()}…"

    @staticmethod
    def _extract_patch_line_range(file_item: Dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
        raw_patch = str(file_item.get("patch") or file_item.get("smart_context") or "").strip()
        if not raw_patch:
            return None, None

        starts: List[int] = []
        ends: List[int] = []
        for match in re.finditer(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", raw_patch):
            try:
                start = int(match.group(1))
                count = int(match.group(2) or "1")
            except (TypeError, ValueError):
                continue
            starts.append(start)
            ends.append(start + max(count, 1) - 1)

        if not starts:
            return None, None
        return min(starts), max(ends)

    def _build_pr_file_index(self, pr_details: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        index: Dict[str, Dict[str, Any]] = {}
        for pr in pr_details or []:
            pr_number = pr.get("number")
            pr_url = str(pr.get("url") or "")
            for file_item in pr.get("files") or []:
                filename = str(file_item.get("filename") or "").strip()
                if not filename or filename in index:
                    continue
                line_start, line_end = self._extract_patch_line_range(file_item)
                index[filename] = {
                    "filename": filename,
                    "blob_url": str(file_item.get("blob_url") or ""),
                    "pr_number": int(pr_number) if isinstance(pr_number, int) else pr_number,
                    "pr_url": pr_url,
                    "change_type": str(file_item.get("status") or ""),
                    "additions": file_item.get("additions"),
                    "deletions": file_item.get("deletions"),
                    "line_start": line_start,
                    "line_end": line_end,
                    "patch_preview": self._summarize_patch_preview(file_item),
                }
        return index

    @staticmethod
    def _extract_figma_node_id(url: str) -> str:
        try:
            parsed = urlparse(str(url or ""))
            query = parse_qs(parsed.query)
            node_ids = query.get("node-id") or query.get("node_id") or []
            return str(node_ids[0]) if node_ids else ""
        except Exception:
            return ""

    @staticmethod
    def _summarize_patch_preview(file_item: Dict[str, Any], max_lines: int = 8, max_chars: int = 900) -> str:
        raw_preview = str(
            file_item.get("smart_context")
            or file_item.get("patch")
            or ""
        ).strip()
        if not raw_preview:
            return ""
        lines = raw_preview.replace("\r", "").split("\n")[:max_lines]
        preview = "\n".join(lines).strip()
        if len(preview) > max_chars:
            return f"{preview[:max_chars].rstrip()}…"
        return preview

    @staticmethod
    def _normalize_source_lookup_text(value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

    def _infer_requirement_files_from_text(
            self,
            item_text: str,
            pr_file_index: Dict[str, Dict[str, Any]],
            *,
            limit: int = 5,
    ) -> List[str]:
        raw_text = str(item_text or "")
        if not raw_text.strip() or not pr_file_index:
            return []

        lowered_text = raw_text.lower()
        normalized_text = self._normalize_source_lookup_text(raw_text)
        scored: List[tuple[int, int, str]] = []

        for order, filename in enumerate(pr_file_index.keys()):
            lowered_filename = filename.lower()
            basename = filename.rsplit("/", 1)[-1]
            lowered_basename = basename.lower()
            stem = basename.rsplit(".", 1)[0]
            normalized_stem = self._normalize_source_lookup_text(stem)

            score = 0
            if lowered_filename in lowered_text:
                score += 50
            if lowered_basename in lowered_text:
                score += 40
            if len(normalized_stem) >= 5 and normalized_stem in normalized_text:
                score += 25

            if score:
                scored.append((score, order, filename))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [filename for _, _, filename in scored[:limit]]

    def _parse_requirement_item(self, item_text: str) -> Dict[str, Any]:
        requirement = ""
        requirement_source = ""
        evidence_notes: List[str] = []
        code_files: List[str] = []
        figma_relation = ""
        note_parts: List[str] = []
        parsed_segments: List[str] = []

        for raw_line in str(item_text or "").replace("\r", "").split("\n"):
            cleaned = self._strip_analysis_item_leader(self._clean_analysis_line(raw_line))
            if not cleaned:
                continue
            inline_segments = [segment.strip() for segment in cleaned.split(" | ") if segment.strip()]
            parsed_segments.extend(inline_segments or [cleaned])

        for segment in parsed_segments:
            normalized = segment.lower()
            if normalized.startswith(("talab:", "requirement:")):
                requirement = segment.split(":", 1)[1].strip()
            elif normalized.startswith(("source:", "manba:")):
                requirement_source = segment.split(":", 1)[1].strip()
            elif normalized.startswith(("evidence:", "isbot:", "dalil:")):
                evidence_value = segment.split(":", 1)[1].strip()
                if evidence_value:
                    evidence_notes.append(evidence_value)
            elif normalized.startswith(("file:", "files:", "fayl:", "fayllar:", "kod:", "code:")):
                file_value = segment.split(":", 1)[1].strip()
                if file_value:
                    code_files.extend(
                        [part.strip(" `") for part in re.split(r"[;,]", file_value) if part.strip()]
                    )
            elif normalized.startswith("figma:"):
                figma_relation = segment.split(":", 1)[1].strip()
            elif normalized.startswith(("note:", "notes:", "izoh:")):
                note_value = segment.split(":", 1)[1].strip()
                if note_value:
                    note_parts.append(note_value)
            elif not requirement:
                requirement = segment
            else:
                note_parts.append(segment)

        if not requirement:
            requirement = self._summarize_text(item_text, limit=220)

        deduped_code_files: List[str] = []
        seen_files = set()
        for code_file in code_files:
            if code_file in seen_files:
                continue
            seen_files.add(code_file)
            deduped_code_files.append(code_file)

        return {
            "requirement": requirement,
            "requirement_source": requirement_source,
            "evidence_notes": evidence_notes,
            "code_files": deduped_code_files,
            "figma_relation": figma_relation,
            "notes": " ".join(note_parts).strip(),
        }
