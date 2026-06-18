"""Agent3 — testcase auditor va scenario organizer kontrakti.

Agent3 test case yozmaydi. Agent2 yaratgan flat testcase ro'yxatini audit qiladi,
bir xil ekran/flow/ma'nodagi testcase'larni scenario guruhlarga ajratadi va faqat
haqiqiy duplicate testcase'larni merge qiladi.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "test_scenarios": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scenario_title": {"type": "string"},
                    "screen_or_flow": {"type": "string"},
                    "requirement_ids": {"type": "array", "items": {"type": "string"}},
                    "test_cases": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "preconditions": {"type": "string"},
                                "steps": {"type": "array", "items": {"type": "string"}},
                                "expected_result": {"type": "string"},
                                "test_type": {"type": "string"},
                                "priority": {"type": "string"},
                                "severity": {"type": "string"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                                "requirement_ids": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": [
                                "title",
                                "steps",
                                "expected_result",
                                "test_type",
                                "requirement_ids",
                            ],
                        },
                    },
                },
                "required": ["scenario_title", "test_cases"],
            },
        },
        "audit_findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "requirement_ids": {"type": "array", "items": {"type": "string"}},
                    "reason": {"type": "string"},
                },
                "required": ["type", "reason"],
            },
        },
    },
    "required": ["test_scenarios", "audit_findings"],
}

_LINE = "═" * 79


def _tc_to_prompt_dict(tc: Any, index: int) -> Dict[str, Any]:
    return {
        "temp_id": getattr(tc, "id", None) or f"TMP-{index:03d}",
        "title": getattr(tc, "title", "") or "",
        "description": getattr(tc, "description", "") or "",
        "preconditions": getattr(tc, "preconditions", "") or "",
        "steps": list(getattr(tc, "steps", None) or []),
        "expected_result": getattr(tc, "expected_result", "") or "",
        "test_type": getattr(tc, "test_type", "") or "",
        "priority": getattr(tc, "priority", "") or "",
        "severity": getattr(tc, "severity", "") or "",
        "tags": list(getattr(tc, "tags", None) or []),
        "requirement_ids": list(getattr(tc, "requirement_ids", None) or []),
    }


def build_prompt(
    *,
    requirements: List[Dict[str, Any]],
    test_cases: List[Any],
) -> str:
    """Agent3 auditor prompti."""
    req_lines = "\n".join(
        f"- {str(r.get('id') or '').strip()}: {str(r.get('text') or '').strip()}"
        for r in (requirements or [])
        if str(r.get("id") or "").strip()
    )
    tc_rows = [_tc_to_prompt_dict(tc, index) for index, tc in enumerate(test_cases or [], start=1)]
    tc_json = json.dumps(tc_rows, ensure_ascii=False, indent=2)

    return f"""**VAZIFA:** Testcase'larni audit qilish va scenario guruhlarga ajratish.

{_LINE}
TALABLAR
{_LINE}

{req_lines}

{_LINE}
AGENT2 TESTCASE'LARI
{_LINE}

{tc_json}

{_LINE}
QOIDALAR
{_LINE}

1. Yangi requirement yaratmang.
2. `requirement_ids` qiymatlarini yo'qotmang va o'zgartirmang.
3. Bir xil ekran/flow/ma'nodagi testcase'larni bitta `test_scenario` ichida group qiling.
4. Positive, negative, boundary, integration kabi turli test_type'larni bitta testcasega majburan merge qilmang.
5. Expected result farqli bo'lsa, testcase'lar alohida qolsin.
6. Faqat haqiqiy duplicate yoki deyarli bir xil testcase'larni merge qiling.
7. Zaif expected_resultlarni aniqroq va tekshiriladigan ko'rinishga keltiring.
8. Har bir testcase `steps` va `expected_result` bilan qaytsin.

{_LINE}
JAVOB FORMATI
{_LINE}

Faqat JSON qaytaring:

```json
{{
  "test_scenarios": [
    {{
      "scenario_title": "Login sahifasi validatsiyasi",
      "screen_or_flow": "Login page",
      "requirement_ids": ["REQ-1", "REQ-2"],
      "test_cases": [
        {{
          "title": "Muvaffaqiyatli login",
          "description": "...",
          "preconditions": "...",
          "steps": ["..."],
          "expected_result": "...",
          "test_type": "positive",
          "priority": "High",
          "severity": "Major",
          "tags": ["auth"],
          "requirement_ids": ["REQ-1"]
        }}
      ]
    }}
  ],
  "audit_findings": [
    {{
      "type": "grouped_same_flow",
      "requirement_ids": ["REQ-1", "REQ-2"],
      "reason": "Bir xil login flowga tegishli testcase'lar bitta scenario ichida group qilindi."
    }}
  ]
}}
```
"""
