from __future__ import annotations

import json
import re
from typing import Any

from utils.ai.gemini_json import extract_balanced_json_objects, repair_json_text

VALID_SOURCES = {"tz", "comment", "figma", "mixed"}

# Prompt matni o'zgarsa bump qiling (format: YYYY.MM.DD-N) va eval o'tkazing.
PROMPT_VERSION = "2026.07.03-1"


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "source": {"type": "string"},
                },
                "required": ["id", "text", "source"],
            },
        },
    },
    "required": ["requirements"],
}


def build_prompt(*, agent1_input: dict[str, Any]) -> str:
    checker_payload = compact_checker_input(agent1_input)

    return f"""Siz Agent1 — professional requirement inventory analyst.

Missiya:
Filterlangan `tz`, `comments` va `figma` source'lardan Agent2 tekshira oladigan toza requirement inventory yarating. Siz kodni baholamaysiz, PR natijasini tekshirmaysiz va yechim taklif qilmaysiz. Faqat source'larda aniq aytilgan talablarni ajratasiz.

Asosiy kontrakt:
- Faqat valid JSON qaytaring; JSONdan tashqari izoh yozmang.
- Output faqat `requirements` massivini o'z ichiga olsin.
- `id` qiymatlari ketma-ket va stable bo'lsin: `REQ-1`, `REQ-2`, ...
- `text` Uzbek tilida, qisqa, aniq va tekshiriladigan talab bo'lsin.
- `source` qiymati faqat `tz`, `comment`, `figma`, `mixed` bo'lsin.
- Source'da yo'q talab, taxmin, implementation idea yoki tavsiya qo'shmang.

Atomic requirement ta'rifi:
- Atomic requirement — bitta mustaqil implement qilinadigan va mustaqil test qilinadigan behavior, shart yoki sifat mezoni.
- Source'dagi har bir gap alohida requirement emas. Bir requirement bir nechta source gapdan yig'ilishi mumkin, agar ular bitta behavior yoki bitta output kontraktini tushuntirsa.
- Alohida requirement faqat shunda ochilsin: uni alohida implement qilish mumkin, alohida test qilish mumkin, va boshqa requirement bajarilsa ham bu requirement bajarilmay qolishi mumkin.

Dedup va merge qoidasi:
- Requirementlarni source matndagi joylashuviga qarab emas, ma'nosiga qarab ajrating.
- Bir xil `actor + action + object + condition + expected result` kombinatsiyasini bildiradigan gaplar duplicate hisoblanadi va bitta canonical requirementga birlashtiriladi.
- Summary, User Story, Use Case, Business Rules va Acceptance Criteria ichida bir talab takrorlansa, yangi `REQ-*` ochmang; AC'dagi o'lchanadigan shartlarni canonical requirement matniga qo'shing.
- Bir capability turli so'zlar bilan qayta yozilgan bo'lsa duplicate hisoblanadi. Action va natija bir xil bo'lsa, bitta requirement yozing.
- Bir flow ichidagi ketma-ket, lekin alohida tekshirib bo'lmaydigan mayda qadamlarni bitta requirementga jamlang.
- Field, column yoki parameter cheklovlarida "bitta maydon ishlatilsin" va "shu maqsad uchun alohida maydonlar bo'lmasin" bir xil cheklovni bildirsa, bitta requirementga birlashtiring. Kontekstdan uzib, talab ma'nosini kengaytirmang.
- Error handling oqimida xato aniqlash, xato qayd etish va xato sababini ko'rsatish bir output/flow bo'lsa, bitta requirementga jamlang. Turli xato turlari mustaqil tekshirilsa, alohida yozing.
- Reporting/logging talablarida hisobot yaratish, statuslar va sabablarni ko'rsatish bitta output kontrakti bo'lsa, bitta requirementga jamlang. Mustaqil outputlar bo'lsa, alohida yozing.
- Nonfunctional talablarida performance, bulk/large data, timeout va scalability bir sifat mezonini bildirsa, bitta aniq requirementga jamlang va o'lchanadigan mezonni saqlang.

Source tanlash:
- Talab faqat `tz`dan kelgan bo'lsa `source="tz"`.
- Talab faqat trusted commentdan kelgan bo'lsa `source="comment"`.
- Talab faqat Figma text/commentdan kelgan bo'lsa `source="figma"`.
- Birlashtirilgan talab bir nechta source'dan kelgan bo'lsa `source="mixed"`.

Sifat talablari:
- Requirement matnida noaniq "kerak bo'lishi mumkin", "imkon bo'lsa", "tavsiya qilinadi" kabi iboralarni ishlatmang; source majburiy qilib aytmagan bo'lsa requirementga aylantirmang.
- Requirement matnini source'dan ko'r-ko'rona ko'chirmang; ma'noni saqlagan holda professional, testable shaklda yozing.
- Bir requirement ichida bir-biriga bog'liq majburiyatlarni jamlash mumkin, lekin mustaqil tekshiriladigan turli behaviorlarni aralashtirmang.

INPUT:
{json.dumps(checker_payload, ensure_ascii=False, indent=2)}

OUTPUT FORMAT:
{{
  "requirements": [
    {{
      "id": "REQ-1",
      "text": "Default 'N' qaytishi kerak.",
      "source": "tz"
    }}
  ]
}}""".strip()


def compact_checker_input(agent1_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "tz": str(agent1_input.get("tz") or ""),
        "comments": [
            str(item.get("text") if isinstance(item, dict) else item).strip()
            for item in list(agent1_input.get("comments") or [])
            if str(item.get("text") if isinstance(item, dict) else item).strip()
        ],
        "figma": [
            str(item.get("text") if isinstance(item, dict) else item).strip()
            for item in list(agent1_input.get("figma") or [])
            if str(item.get("text") if isinstance(item, dict) else item).strip()
        ],
    }


def recover_incomplete_response(raw: str) -> dict[str, Any] | None:
    text = str(raw or "").strip()
    if not text:
        return None

    repaired = repair_json_text(text)
    if repaired and requirements_from_parsed(repaired):
        return {
            "requirements": requirements_from_parsed(repaired),
            "warnings": [
                *[
                    str(item).strip()
                    for item in (repaired.get("warnings") or [])
                    if str(item).strip()
                ],
                "Agent1 raw outputi local JSON repair orqali tiklandi.",
            ],
        }

    recovered_requirements: list[dict[str, Any]] = []
    for snippet in extract_balanced_json_objects(text):
        if '"text"' not in snippet:
            continue
        try:
            parsed = json.loads(snippet)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            recovered_requirements.append(parsed)

    if not recovered_requirements:
        return None

    return {
        "requirements": recovered_requirements,
        "warnings": ["Agent1 raw outputidan qisman JSON recover qilindi."],
    }


def validate_agent1_json(
    parsed: Any,
    *,
    task_summary: str = "",
    description: str = "",
    rules: Any = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    if isinstance(parsed, list):
        parsed = {"requirements": parsed}
        warnings.append("agent1_root_array_wrapped")

    if not isinstance(parsed, dict):
        return {
            "ok": False,
            "data": None,
            "requirements": [],
            "error": "agent1_root_not_object",
            "warnings": warnings,
            "retryable": True,
        }

    if "requirements" not in parsed:
        return {
            "ok": False,
            "data": None,
            "requirements": [],
            "error": "agent1_missing_requirements",
            "warnings": warnings,
            "retryable": True,
        }

    raw_requirements = parsed.get("requirements")
    if not isinstance(raw_requirements, list):
        return {
            "ok": False,
            "data": None,
            "requirements": [],
            "error": "agent1_requirements_not_array",
            "warnings": warnings,
            "retryable": True,
        }

    skipped = sum(1 for item in raw_requirements if not isinstance(item, dict) or not str(item.get("text") or "").strip())
    requirements = refine_requirements(
        requirements=raw_requirements,
        task_summary=task_summary,
        description=description,
        rules=rules,
    )
    validated, validation_warnings = validate_output(requirements)
    warnings.extend(user_facing_validation_warnings(validation_warnings))
    if skipped:
        warnings.append(f"Agent1 {skipped} ta invalid requirement itemni o'tkazib yubordi.")
    if not validated:
        return {
            "ok": False,
            "data": None,
            "requirements": [],
            "error": "agent1_empty_requirements",
            "warnings": warnings,
            "retryable": True,
        }

    data = {
        "requirements": public_requirement_items(validated),
        "warnings": [
            str(item).strip()
            for item in [*(parsed.get("warnings") or []), *warnings]
            if str(item).strip()
        ],
    }
    return {
        "ok": True,
        "data": data,
        "requirements": validated,
        "error": None,
        "warnings": warnings,
        "retryable": False,
    }


def requirements_from_parsed(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if not isinstance(parsed, dict):
        return []
    return list(parsed.get("requirements") or [])


def normalize_contract_output(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirements": requirements_from_parsed(parsed),
        "warnings": [
            str(item).strip()
            for item in (parsed.get("warnings") or [])
            if str(item).strip()
        ],
    }


def refine_requirements(
    *,
    requirements: list[dict[str, Any]],
    task_summary: str,
    description: str,
    rules: Any = None,
) -> list[dict[str, Any]]:
    normalized = normalize_requirement_inventory(requirements)
    if rules is not None and not getattr(rules, "figma_scope_enabled", False):
        normalized = [
            req for req in normalized
            if str(req.get("source") or "").strip().lower() != "figma"
        ]
    return renumber_requirement_inventory(normalized)


def normalize_requirement_inventory(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(items or [], start=1):
        if not isinstance(item, dict):
            continue
        req_id = str(item.get("id") or f"REQ-{index}").strip() or f"REQ-{index}"
        req_text = str(item.get("text") or "").strip()
        if not req_text:
            continue
        key = normalize_text_for_dedupe(req_text)
        if key in seen:
            continue
        seen.add(key)
        source = str(item.get("source") or "tz").strip().lower() or "tz"
        if source not in VALID_SOURCES:
            source = "mixed" if "," in source else "tz"
        normalized.append(
            {
                "id": req_id,
                "text": req_text,
                "source": source,
            }
        )
    return normalized


def public_requirement_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return normalize_requirement_inventory(items)


def validate_output(
    requirements: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    validated: list[dict[str, Any]] = []
    warnings: list[str] = []

    for index, req in enumerate(requirements or [], start=1):
        if not isinstance(req, dict):
            warnings.append(f"REQ-{index}: object emas, o'tkazib yuborildi")
            continue
        original_id = str(req.get("id") or f"REQ-{index}").strip()
        text = str(req.get("text") or "").strip()

        if not text or len(text) < 6:
            warnings.append(f"{original_id}: bo'sh matn, o'tkazib yuborildi")
            continue

        source = str(req.get("source") or "tz").strip().lower() or "tz"
        if source not in VALID_SOURCES:
            warnings.append(f"{original_id}: source='{source}' noto'g'ri -> 'tz' ga to'g'irlandi")
            source = "tz"

        validated.append(
            {
                "id": original_id or f"REQ-{len(validated) + 1}",
                "text": text,
                "source": source,
            }
        )

    for index, req in enumerate(validated, start=1):
        req["id"] = f"REQ-{index}"

    return validated, warnings


def user_facing_validation_warnings(warnings: list[str]) -> list[str]:
    return [
        warning
        for warning in warnings or []
        if "source='" not in str(warning)
    ]


def merge_requirements(
    existing: list[dict[str, Any]],
    extras: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged = normalize_requirement_inventory(existing)
    existing_keys = {normalize_requirement_for_dedupe(item) for item in merged}
    for req in normalize_requirement_inventory(extras):
        key = normalize_requirement_for_dedupe(req)
        if not key or key in existing_keys:
            continue
        if any(requirements_are_duplicateish(req, item) for item in merged):
            continue
        existing_keys.add(key)
        merged.append(req)
    return renumber_requirement_inventory(merged)


def renumber_requirement_inventory(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    renumbered: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        updated = dict(item)
        updated["id"] = f"REQ-{index}"
        renumbered.append(updated)
    return renumbered


def normalize_requirement_for_dedupe(req: dict[str, Any]) -> str:
    return normalize_text_for_dedupe(clean_requirement_text(str(req.get("text") or "")))


def requirements_are_duplicateish(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_text = str(left.get("text") or "").strip()
    right_text = str(right.get("text") or "").strip()
    if not left_text or not right_text:
        return False
    return source_text_similarity(left_text, right_text) >= 0.72


def source_text_similarity(left: str, right: str) -> float:
    left_spaced = normalize_text_for_similarity(left)
    right_spaced = normalize_text_for_similarity(right)
    left_norm = re.sub(r"\s+", "", left_spaced)
    right_norm = re.sub(r"\s+", "", right_spaced)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    if left_norm in right_norm or right_norm in left_norm:
        shorter = min(len(left_norm), len(right_norm))
        longer = max(len(left_norm), len(right_norm))
        return max(0.75, shorter / max(1, longer))

    left_tokens = set(re.findall(r"[\wА-Яа-яЁёЎўҚқҒғҲҳІіЇїЄє]+", left_spaced, flags=re.UNICODE))
    right_tokens = set(re.findall(r"[\wА-Яа-яЁёЎўҚқҒғҲҳІіЇїЄє]+", right_spaced, flags=re.UNICODE))
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    return overlap / max(1, min(len(left_tokens), len(right_tokens)))


def normalize_text_for_similarity(text: str) -> str:
    tokenized = re.sub(r"[^\wА-Яа-яЁёЎўҚқҒғҲҳІіЇїЄє]+", " ", str(text or "").casefold())
    return re.sub(r"\s+", " ", tokenized).strip()


def clean_candidate_text(text: str) -> str:
    cleaned = str(text or "").strip()
    cleaned = cleaned.replace("->", "->")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"^[*\-#]+\s*", "", cleaned)
    cleaned = re.sub(r"^\d+\.\s*", "", cleaned)
    cleaned = cleaned.strip(" -:")
    return cleaned


def clean_requirement_text(text: str) -> str:
    return clean_candidate_text(text)


def normalize_text_for_dedupe(text: str) -> str:
    return re.sub(r"\W+", "", str(text or "").casefold())
