"""Agent2 — Testcase yozuvchi kontrakt.

Agent1 bergan talablar ro'yxatini (REQ-1..N) olib, har bir talab uchun
bir-biriga o'xshamagan (takrorsiz) test case'lar yozadi. BITTA Gemini
chaqiruvi: butun ro'yxat bitta promptga beriladi, hamma test case bitta
javobda qaytadi — shuning uchun AI butun ro'yxatni ko'rib, takrorni kamaytiradi.

PR (kod) BU YERDA ISHLATILMAYDI. Manbalar: talablar + TZ + Figma + comment.
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
                    "id",
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
    task_key: str,
    task_summary: str,
    task_type: str,
    task_priority: str,
    requirements: List[Dict[str, Any]],
    tz_content: str,
    comment_summary: str = "",
    figma_summary: str = "",
    custom_context: str = "",
    dev_objections: List[Dict[str, Any]] | None = None,
    test_types: List[str] | None = None,
    max_test_cases: int = 10,
) -> str:
    """Agent2 uchun talab-drayverli prompt yig'ish."""
    test_types = test_types or ["positive", "negative"]
    types_text = ", ".join(f"{t} ({TEST_TYPE_DESC.get(t, t)})" for t in test_types)

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
        "- Har bir REQ uchun KAMIDA 1 ta, KO'PI BILAN 3 ta test case yozing (majburiy chegara).\n"
        "- Har test case `requirement_ids` maydonida qaysi REQ(lar)ni qoplashini ko'rsating.\n"
        "- Talablararo bir xil test case'larni TAKRORLAMANG — har biri o'ziga xos bo'lsin.\n"
        "- Bir talab uchun kerak bo'lsa bir nechta test turini (positive/negative/edge) qo'llang, lekin 3 tadan oshmang.",
    )

    tz_block = _section("📝 TEXNIK TOPSHIRIQ (TZ) — qo'shimcha kontekst", tz_content)
    figma_block = _section("🎨 FIGMA DIZAYN MA'LUMOTLARI", figma_summary)

    comments_block = ""
    if comment_summary:
        comments_block = _section(
            "⚠️ MUHIM: COMMENT'LARDA O'ZGARISHLAR ANIQLANDI",
            f"{comment_summary}\n\nBu o'zgarishlar test case'larda ALBATTA hisobga olinishi kerak!",
        )

    custom_block = ""
    if custom_context:
        custom_block = _section(
            "💬 QO'SHIMCHA MA'LUMOTLAR (FOYDALANUVCHIDAN)",
            f"{custom_context}\n\n"
            "⚠️ MUHIM: Bu ma'lumotlarni (product nomlari, narxlar, chegirmalar, limitlar) "
            "test datalarida ALBATTA ishlating.",
        )

    objections_block = ""
    if dev_objections:
        lines = []
        for c in dev_objections:
            author = c.get("author", "Dev")
            created = str(c.get("created", ""))[:10]
            body = str(c.get("body", "")).strip()
            lines.append(f"  • {author} ({created}): {body}")
        objections_block = _section(
            "⚡ DEVELOPER ETIROZLARI (tahlildan KEYIN yozilgan)",
            "\n".join(lines) + "\n\nTest case'larni yozishda bu izohlarni hisobga oling.",
        )

    body_parts = [
        p
        for p in (requirements_block, tz_block, figma_block, comments_block, custom_block, objections_block)
        if p
    ]
    data_body = "\n".join(body_parts)

    return f"""**VAZIFA:** JIRA task uchun QA test case'lar yaratish (O'ZBEK TILIDA)

{_LINE}
📋 TASK MA'LUMOTLARI
{_LINE}

**Task Key:** {task_key}
**Summary:** {task_summary}
**Type:** {task_type}
**Priority:** {task_priority}

{data_body}
{_LINE}
🎯 SIFAT TALABLARI
{_LINE}

**Test turlari:** {types_text}

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
      "id": "TC-001",
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
- Har bir talab (REQ) KAMIDA 1 ta, KO'PI BILAN 3 ta test case bilan qoplansin (majburiy).
- Eng ko'pi {max_test_cases} ta test case yarating.
- `steps` ro'yxat (list) bo'lsin, har bir step alohida.
- `requirement_ids` har test case'da to'ldirilsin.

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
