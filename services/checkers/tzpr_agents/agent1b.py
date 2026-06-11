from __future__ import annotations

import json
from typing import Any


VALID_SOURCES = {"tz", "comment", "figma", "mixed"}


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "source": {"type": "string"},
                    "members": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "members"],
            },
        },
    },
    "required": ["requirements"],
}


ROLE_PROMPT = """Siz Agent1B — requirement merge specialist.

Missiya:
Agent1A ajratgan requirement ro'yxatini oling va bir xil MA'NODAGI talablarni bitta canonical talabga birlashtiring. Siz yangi talab o'ylab topmaysiz, talab matnini kengaytirmaysiz va hech qaysi talabni tashlab yubormaysiz — faqat dublikatlarni birlashtirasiz.

Bir xil ma'no mezoni:
- Ikki talab bir xil `actor + action + object + condition + expected result` ni bildirsa, ular duplicate va bitta talabga birlashadi.
- Turli so'zlar bilan yozilgan, lekin bir capability/behaviorni bildiruvchi talablar duplicate hisoblanadi.
- SHUBHA bo'lsa — BIRLASHTIRMANG. Alohida qoldiring. Noto'g'ri birlashtirish talab yo'qotadi.

Qattiq qoidalar:
- Har bir input requirement (REQ-*) natijada kamida bitta guruhning `members` ichida bo'lishi SHART. Hech birini tushirib qoldirmang.
- `members` — shu canonical talabga tegishli input REQ-* idlari ro'yxati.
- Bitta talab faqat bitta guruhga tegishli bo'lsin (members'lar kesishmasin).
- `text` — birlashtirilgan talabning aniq, testable, Uzbek tilidagi canonical matni.
- `source` faqat `tz`, `comment`, `figma`, `mixed` bo'lsin (a'zolar manbasidan kelib chiqib)."""


def build_prompt(*, requirements: list[dict[str, Any]]) -> str:
    payload = [
        {
            "id": str(item.get("id") or "").strip(),
            "text": str(item.get("text") or "").strip(),
            "source": str(item.get("source") or "tz").strip() or "tz",
        }
        for item in (requirements or [])
        if str(item.get("text") or "").strip()
    ]
    return f"""{ROLE_PROMPT}

INPUT REQUIREMENTS:
{json.dumps(payload, ensure_ascii=False, indent=2)}

OUTPUT FORMAT (faqat valid JSON):
{{
  "requirements": [
    {{
      "text": "Default holatda 'N' qiymati qaytariladi.",
      "source": "tz",
      "members": ["REQ-1", "REQ-4"]
    }}
  ]
}}""".strip()


def _resolve_source(members: list[str], raw_by_id: dict[str, dict[str, Any]]) -> str:
    sources = {
        str(raw_by_id[m].get("source") or "tz").strip().lower()
        for m in members
        if m in raw_by_id
    }
    sources.discard("")
    if not sources:
        return "tz"
    if len(sources) == 1:
        return next(iter(sources))
    return "mixed"


def reconcile_merged(
    *,
    raw_requirements: list[dict[str, Any]],
    merged_groups: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Deterministik no-loss: har bir asl REQ natijada bo'lishini kafolatlaydi."""
    raw_by_id: dict[str, dict[str, Any]] = {}
    raw_order: list[str] = []
    for item in raw_requirements or []:
        req_id = str(item.get("id") or "").strip()
        text = str(item.get("text") or "").strip()
        if not req_id or not text:
            continue
        raw_by_id[req_id] = {"id": req_id, "text": text, "source": str(item.get("source") or "tz").strip() or "tz"}
        raw_order.append(req_id)

    warnings: list[str] = []
    groups: list[dict[str, Any]] = []
    covered: set[str] = set()

    for group in merged_groups or []:
        if not isinstance(group, dict):
            continue
        text = str(group.get("text") or "").strip()
        members = [
            str(m).strip()
            for m in (group.get("members") or [])
            if str(m).strip() in raw_by_id and str(m).strip() not in covered
        ]
        if not text or not members:
            continue
        covered.update(members)
        groups.append(
            {
                "text": text,
                "source": _resolve_source(members, raw_by_id),
                "members": members,
            }
        )

    missing = [req_id for req_id in raw_order if req_id not in covered]
    if missing:
        warnings.append(
            f"Agent1B {len(missing)} ta requirementni guruhlamadi; ular asl holida saqlandi."
        )
        for req_id in missing:
            raw = raw_by_id[req_id]
            groups.append(
                {
                    "text": raw["text"],
                    "source": raw["source"],
                    "members": [req_id],
                }
            )

    result: list[dict[str, Any]] = []
    for index, group in enumerate(groups, start=1):
        member_texts = [raw_by_id[m]["text"] for m in group["members"] if m in raw_by_id]
        entry = {
            "id": f"REQ-{index}",
            "text": group["text"],
            "source": group["source"],
        }
        if len(group["members"]) > 1:
            entry["merged_from"] = member_texts
        result.append(entry)
    return result, warnings


def validate_merged_json(parsed: Any) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        return {"ok": False, "error": "Agent1B output object emas.", "groups": []}
    groups = parsed.get("requirements")
    if not isinstance(groups, list) or not groups:
        return {"ok": False, "error": "Agent1B requirements massivi bo'sh.", "groups": []}
    return {"ok": True, "error": "", "groups": groups}
