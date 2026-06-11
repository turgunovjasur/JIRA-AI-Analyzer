from __future__ import annotations

import re
from typing import Any


def now_iso() -> str:
    from datetime import datetime

    return datetime.now().isoformat()


def summarize(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 1, 0)].rstrip()}…"


def clean_candidate_text(text: str) -> str:
    cleaned = str(text or "").strip()
    cleaned = cleaned.replace("->", "→")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"^[*\-#]+\s*", "", cleaned)
    cleaned = re.sub(r"^\d+\.\s*", "", cleaned)
    cleaned = cleaned.strip(" -:")
    return cleaned


def normalize_text_for_dedupe(text: str) -> str:
    return re.sub(r"\W+", "", str(text or "").casefold())


def build_artifact_preview(artifact: dict[str, Any]) -> dict[str, Any]:
    if not artifact:
        return {}
    preview: dict[str, Any] = {"keys": sorted(str(key) for key in artifact.keys())[:12]}
    if isinstance(artifact.get("summary"), str) and artifact.get("summary"):
        preview["summary"] = summarize(artifact.get("summary"), 220)
    if isinstance(artifact.get("parse_mode"), str) and artifact.get("parse_mode"):
        preview["parse_mode"] = str(artifact.get("parse_mode"))
    if isinstance(artifact.get("requirements"), list):
        preview["requirements_total"] = len(artifact.get("requirements") or [])
    if isinstance(artifact.get("verifications"), list):
        preview["verifications_total"] = len(artifact.get("verifications") or [])
    if isinstance(artifact.get("requirements"), list):
        preview["requirements_total"] = len(artifact.get("requirements") or [])
    if isinstance(artifact.get("raw_excerpt"), str) and artifact.get("raw_excerpt"):
        preview["raw_excerpt"] = summarize(artifact.get("raw_excerpt"), 220)
    if isinstance(artifact.get("raw_model_excerpt"), str) and artifact.get("raw_model_excerpt"):
        preview["raw_model_excerpt"] = summarize(artifact.get("raw_model_excerpt"), 220)
    return preview
