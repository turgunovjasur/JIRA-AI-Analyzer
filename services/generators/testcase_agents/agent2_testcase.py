"""Agent2 — Testcase yozuvchi kontrakt.

Agent1 bergan talablar ro'yxatini (REQ-1..N) olib, har bir talab uchun
bir-biriga o'xshamagan (takrorsiz) test case'lar yozadi. BITTA Gemini
chaqiruvi: butun ro'yxat bitta promptga beriladi, hamma test case bitta
javobda qaytadi — shuning uchun AI butun ro'yxatni ko'rib, takrorni kamaytiradi.

PR (kod), comment va Figma BU YERDA ISHLATILMAYDI. Agent2 manbalari:
Agent1 requirements + real TZ + user custom context.
"""
from __future__ import annotations

from typing import Any, Dict, List


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "test_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
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
    "required": ["test_cases"],
}


TEST_TYPE_DESC = {
    "positive": "To'g'ri ma'lumotlar bilan ishlash",
    "negative": "Noto'g'ri ma'lumotlar, xato holatlar",
    "boundary": "Limit qiymatlari (min/max)",
    "edge": "Maxsus/chekka holatlar",
    "integration": "Tizim integratsiyasi",
    "regression": "Regression testing",
}

_LINE = "═" * 79


def _section(title: str, body: str) -> str:
    body = (body or "").strip()
    if not body:
        return ""
    return f"{_LINE}\n{title}\n{_LINE}\n\n{body}\n"


def build_prompt(
    *,
    requirements: List[Dict[str, Any]],
    tz_content: str,
    custom_context: str = "",
    testcases_per_requirement: int = 3,
    mode: str = "initial",
) -> str:
    """Agent2 uchun talab-drayverli prompt yig'ish."""
    try:
        testcases_per_requirement = int(testcases_per_requirement)
    except (TypeError, ValueError):
        testcases_per_requirement = 3
    testcases_per_requirement = max(1, min(3, testcases_per_requirement))
    allowed_types = ", ".join(f"{t} ({desc})" for t, desc in TEST_TYPE_DESC.items())

    req_lines = "\n".join(
        f"- {str(r.get('id') or '').strip()}: {str(r.get('text') or '').strip()} "
        f"[{str(r.get('source') or 'tz').strip()}]"
        for r in (requirements or [])
        if str(r.get("text") or "").strip()
    )

    requirements_block = _section(
        "🎯 TALABLAR RO'YXATI (Agent1 ajratgan — ASOSIY MANBA)",
        f"{req_lines}\n\n"
        "Ko'rsatma:\n"
        f"- Har bir REQ uchun KAMIDA 1 ta, KO'PI BILAN {testcases_per_requirement} ta test case yozing.\n"
        "- Har test case `requirement_ids` maydonida qaysi REQ(lar)ni qoplashini ko'rsating.\n"
        "- Talablararo bir xil test case'larni TAKRORLAMANG — har biri o'ziga xos bo'lsin.\n"
        f"- Bir talab uchun kerak bo'lsa bir nechta test turini qo'llang, lekin {testcases_per_requirement} tadan oshmang.",
    )

    tz_block = _section("📝 REAL TEXNIK TOPSHIRIQ (TZ)", tz_content)

    custom_block = ""
    if custom_context:
        custom_block = _section(
            "💬 QO'SHIMCHA MA'LUMOTLAR (FOYDALANUVCHIDAN)",
            f"{custom_context}\n\n"
            "⚠️ MUHIM: Bu ma'lumotlarni (product nomlari, narxlar, chegirmalar, limitlar) "
            "test datalarida ALBATTA ishlating.",
        )

    body_parts = [
        p
        for p in (requirements_block, tz_block, custom_block)
        if p
    ]
    data_body = "\n".join(body_parts)
    mode_instruction = ""
    if str(mode or "").strip() == "repair_missing_requirements":
        mode_instruction = (
            "\n**REPAIR MODE:** Faqat yuqorida berilgan missing REQlar uchun test case yozing. "
            "Boshqa requirementlar uchun test case yozmang.\n"
        )

    return f"""**VAZIFA:** JIRA task uchun QA test case'lar yaratish (O'ZBEK TILIDA)

{data_body}
{mode_instruction}
{_LINE}
🎯 SIFAT TALABLARI
{_LINE}

**Test turlari:** {allowed_types}

1. Har bir test case TO'LIQ va ANIQ bo'lsin (title, steps, expected_result).
2. Steps batafsil — har bir qadam alohida element.
3. Expected result aniq: nima kutiladi.
4. Haqiqiy test scenario'lar yozing (TZ'dan ko'r-ko'rona copy-paste emas).
5. Har test case `requirement_ids` orqali qaysi talabni qoplashini ko'rsatsin.
6. Talablararo takrorlanmang.

{_LINE}
📊 JAVOB FORMATI (JSON)
{_LINE}

Javobni FAQAT JSON formatda bering, boshqa hech narsa yo'q:

```json
{{
  "test_cases": [
    {{
      "title": "Test case nomi (qisqa va aniq)",
      "description": "Nima test qilinadi",
      "preconditions": "Boshlang'ich shartlar",
      "steps": ["1. Birinchi qadam", "2. Ikkinchi qadam"],
      "expected_result": "Kutilayotgan natija (aniq)",
      "test_type": "positive/negative/boundary/edge",
      "priority": "High/Medium/Low",
      "severity": "Critical/Major/Minor",
      "tags": ["tag1", "tag2"],
      "requirement_ids": ["REQ-1"]
    }}
  ]
}}
```

**MUHIM:**
- Har bir talab (REQ) KAMIDA 1 ta, KO'PI BILAN {testcases_per_requirement} ta test case bilan qoplansin.
- `steps` ro'yxat (list) bo'lsin, har bir step alohida.
- `requirement_ids` har test case'da to'ldirilsin.
- `id` qaytarish shart emas — backend final TC-001 raqamlashni o'zi qiladi.

Endi talablar ro'yxati asosida test case'lar yarating!
"""


def extract_requirement_coverage(
    test_cases: List[Any],
    requirements: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Qaysi talablar test case bilan qoplangani — deterministik (AI emas)."""
    req_ids = [str(r.get("id") or "").strip() for r in (requirements or []) if str(r.get("id") or "").strip()]
    covered: set[str] = set()
    for tc in test_cases or []:
        for rid in (getattr(tc, "requirement_ids", None) or []):
            rid = str(rid).strip()
            if rid:
                covered.add(rid)
    uncovered = [rid for rid in req_ids if rid not in covered]
    return {
        "total_requirements": len(req_ids),
        "covered_count": len(req_ids) - len(uncovered),
        "uncovered_ids": uncovered,
    }
