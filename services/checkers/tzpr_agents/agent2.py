from __future__ import annotations

import json
import os
import re
from difflib import SequenceMatcher
from typing import Any

# Prompt matni o'zgarsa bump qiling (format: YYYY.MM.DD-N) va eval o'tkazing.
PROMPT_VERSION = "2026.07.03-1"

VALID_STATUSES = {"completed", "failed"}
VALID_EXTRA_RISKS = {"low", "medium", "high"}
VALID_SOURCE_TYPES = {"code", "test", "pr", "figma", "manual"}

EXTRA_OVERLAP_THRESHOLD = 0.6
_OVERLAP_TOKEN_RE = re.compile(r"[\w']+", re.UNICODE)


SOURCE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "file": {"type": "string"},
        "symbol": {"type": "string"},
        "note": {"type": "string"},
        "url": {"type": "string"},
    },
}


SINGLE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "status": {"type": "string"},
        "evidence": {"type": "string"},
        "sources": {"type": "array", "items": SOURCE_RESPONSE_SCHEMA},
    },
    "required": ["id", "status", "evidence"],
}


BATCH_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "status": {"type": "string"},
                    "evidence": {"type": "string"},
                    "sources": {"type": "array", "items": SOURCE_RESPONSE_SCHEMA},
                },
                "required": ["id", "status", "evidence"],
            },
        },
    },
    "required": ["items"],
}


EXTRA_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "extra": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "risk": {"type": "string"},
                },
                "required": ["text", "risk"],
            },
        },
    },
    "required": ["extra"],
}


VERIFIER_ROLE_PROMPT = """Siz Agent2 — professional PR/code verification auditor.

Missiya:
Agent1 bergan requirement inventory'ni PR/code context bo'yicha tekshiring. Siz yangi requirement yaratmaysiz, requirementlarni merge/split qilmaysiz, task biznes ma'nosini kengaytirmaysiz. Har bir input requirement uchun faqat shu requirement bajarilgan-bajarilmaganini aniq code evidence bilan baholaysiz.

Asosiy kontrakt:
- Faqat valid JSON qaytaring; JSONdan tashqari izoh yozmang.
- Har bir input requirement uchun aynan bitta output item qaytaring.
- Output `id` qiymati input requirement `id` bilan aynan bir xil bo'lsin.
- `status` faqat `completed` yoki `failed` bo'lsin.
- `evidence` qisqa, konkret va code/PR daliliga tayangan bo'lsin.
- `sources` ichida shu requirement uchun ishlatilgan real manbalarni qaytaring.

Til talabi:
- `evidence` matni faqat Uzbek lotin tilida yozilsin.
- File/procedure/function/package/table/constant/test nomlari original holatda qoldirilsin.
- Inglizcha umumiy izoh yozmang; faqat texnik nomlar va kod identifikatorlari original tilda qolishi mumkin.

Qaror mezoni:
- `completed`: requirementdagi barcha mustaqil majburiyatlar berilgan PR/code context ichida aniq ko'rinsa.
- `failed`: dalil topilmasa, dalil qisman bo'lsa, requirementga zid kod ko'rinsa, yoki requirementni tasdiqlash uchun manual/runtime tekshiruv kerak bo'lsa.
- Requirementni bajarilgan deb belgilash uchun faqat nom o'xshashligi yetarli emas; behavior, condition va expected result ham tasdiqlanishi kerak.
- Requirement matnini kontekstdan uzib kengaytirmang. Source'da talab qilinmagan implementation usulini majburiy deb hisoblamang.
- Nonfunctional talablar (performance, bulk, timeout, scalability) uchun aniq code mexanizm, test, limit yoki o'lchov ko'rinsa `completed`; aks holda `failed` va evidence ichida "manual/performance test kerak" deb yozing. Muayyan texnika (masalan, batching, index, FORALL) faqat requirement o'sha texnikani aniq talab qilsa majburiy hisoblanadi.
- UI, backend, DB, permission, migration, validation, logging yoki test evidence'lari requirement turiga mos bo'lsa dalil bo'lishi mumkin.

Evidence sifati:
- Evidence ichida imkon qadar file/procedure/function/component/constant/query/test nomini yozing.
- Evidence "bajarilgan", "topildi", "ok" kabi umumiy bo'lmasin; nima ko'rilgani va qaysi requirement qismini tasdiqlagani yozilsin.
- `failed` evidence aynan nima yetishmayotgani yoki nimaga zidligini yozsin.
- Agar requirement ambiguous bo'lsa, `failed` qaytaring va evidence ichida qaysi talqin noaniq ekanini yozing; o'zingiz qat'iyroq talab ixtiro qilmang.

Sources formati:
- `sources` array bo'lsin; har item: `type`, `file`, `symbol`, `note`, `url`.
- `type` qiymati: `code`, `test`, `pr`, `figma`, yoki `manual`.
- `file` faqat real PR/file path bo'lsa yozilsin; taxminiy fayl yozmang.
- `symbol` ichida procedure/function/package/table/index/constant/test nomini yozing.
- Runtime/manual tekshiruv kerak bo'lsa `type="manual"` va `note` ichida nima tekshirilishi kerakligini yozing.
""".strip()


EXTRA_SCAN_ROLE_PROMPT = """Siz Agent2 — professional PR/code scope scanner.

Missiya:
Agent1 requirementlaridan tashqarida qolgan, lekin PR/code ichida muhim behavior yoki risk tug'diradigan qo'shimcha o'zgarishlarni aniqlang. Requirementni bajarish uchun zarur bo'lgan kodni extra deb belgilamang.

Extra deb faqat quyidagilar yozilsin:
- source requirementlarda yo'q yangi business behavior;
- data model, migration, permission, sync flow, query/index, validation yoki securityga sezilarli ta'sir;
- regression, data loss yoki access risk keltirishi mumkin bo'lgan o'zgarish.

Extra deb yozilmasin:
- formatlash, rename, comment, lokal refactor;
- requirementni bajarish uchun bevosita kerak bo'lgan kod;
- test/helperdagi mayda o'zgarish;
- Agent2 allaqachon failed deb belgilagan requirementning aynan o'zi.

Risk:
- `low`: lokal va kichik qo'shimcha o'zgarish.
- `medium`: business behavior yoki data/query flowga ta'sir qilishi mumkin.
- `high`: data loss, security, permission, migration yoki keng regressiya xavfi.

Til talabi:
- `text` matni faqat Uzbek lotin tilida yozilsin.
- File/procedure/function/package/table/constant/test nomlari original holatda qoldirilsin.
- Inglizcha umumiy izoh yozmang; faqat texnik nomlar va kod identifikatorlari original tilda qolishi mumkin.
""".strip()


def build_extra_scan_prompt(
    *,
    requirements: list[dict[str, Any]],
    pr_info: dict[str, Any],
    code_changes: str,
    verifications: list[dict[str, Any]] | None = None,
) -> str:
    requirement_json = json.dumps(compact_requirements(requirements), ensure_ascii=False, indent=2)
    verified_lines = verified_requirement_lines(requirements, verifications or [])
    verified_block = os.linesep.join(verified_lines) if verified_lines else "(hali tekshirilmagan)"
    pr_titles = [
        f"- #{pr.get('number') or '?'} {str(pr.get('title') or '').strip()}"
        for pr in list(pr_info.get("pr_details") or [])[:5]
    ]
    return f"""{EXTRA_SCAN_ROLE_PROMPT}

Output faqat valid JSON bo'lsin:
{{
  "extra": [
    {{
      "text": "TZ talablarida yo'q Room_Robots fallback logikasi qo'shilgan.",
      "risk": "medium"
    }}
  ]
}}

Agar requirementlardan tashqari muhim o'zgarish topilmasa:
{{
  "extra": []
}}

PR SUMMARY:
{os.linesep.join(pr_titles) if pr_titles else "(PR topilmadi)"}

ALLAQACHON AGENT2 TEKSHIRGAN REQUIREMENTLAR (bularning aynan o'zini extra deb YOZMA):
{verified_block}

CODE CHANGES:
{code_changes[:180000]}

REQUIREMENTS:
{requirement_json}
""".strip()


def build_cached_code_context(*, pr_info: dict[str, Any], code_changes: str) -> str:
    pr_titles = [
        f"- #{pr.get('number') or '?'} {str(pr.get('title') or '').strip()}"
        for pr in list(pr_info.get("pr_details") or [])[:5]
    ]
    return f"""PR SUMMARY:
{os.linesep.join(pr_titles) if pr_titles else "(PR topilmadi)"}

CODE CHANGES:
{code_changes[:180000]}
""".strip()


def build_single_prompt(
    *,
    requirement: dict[str, Any],
    pr_info: dict[str, Any],
    code_changes: str,
) -> str:
    compact = compact_requirements([requirement])
    req = compact[0] if compact else {}
    requirement_json = json.dumps(req, ensure_ascii=False, indent=2)
    pr_titles = [
        f"- #{pr.get('number') or '?'} {str(pr.get('title') or '').strip()}"
        for pr in list(pr_info.get("pr_details") or [])[:5]
    ]
    return f"""{VERIFIER_ROLE_PROMPT}

Output faqat valid JSON bo'lsin:
{{
  "id": "REQ-1",
  "status": "completed",
  "evidence": "Aniq code dalil.",
  "sources": [
    {{"type": "code", "file": "main/oracle/module/example/example.pkb", "symbol": "Example_Procedure", "note": "Talab shu procedure orqali tekshirildi."}}
  ]
}}

PR SUMMARY:
{os.linesep.join(pr_titles) if pr_titles else "(PR topilmadi)"}

CODE CHANGES:
{code_changes[:180000]}

REQUIREMENT:
{requirement_json}
""".strip()


def build_batch_prompt(
    *,
    requirements: list[dict[str, Any]],
    pr_info: dict[str, Any],
    code_changes: str,
) -> str:
    requirement_json = json.dumps(compact_requirements(requirements), ensure_ascii=False, indent=2)
    pr_titles = [
        f"- #{pr.get('number') or '?'} {str(pr.get('title') or '').strip()}"
        for pr in list(pr_info.get("pr_details") or [])[:5]
    ]
    return f"""{VERIFIER_ROLE_PROMPT}

Output faqat valid JSON bo'lsin:
{{
  "items": [
    {{
      "id": "REQ-1",
      "status": "completed",
      "evidence": "Aniq code dalil.",
      "sources": [
        {{"type": "code", "file": "main/oracle/module/example/example.pkb", "symbol": "Example_Procedure", "note": "Talab shu procedure orqali tekshirildi."}}
      ]
    }}
  ]
}}

PR SUMMARY:
{os.linesep.join(pr_titles) if pr_titles else "(PR topilmadi)"}

CODE CHANGES:
{code_changes[:180000]}

REQUIREMENTS:
{requirement_json}
""".strip()


def compact_requirements(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for index, item in enumerate(requirements or [], start=1):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        compact.append(
            {
                "id": str(item.get("id") or f"REQ-{index}").strip() or f"REQ-{index}",
                "text": text,
                "source": str(item.get("source") or "tz").strip() or "tz",
            }
        )
    return compact


def normalize_sources(items: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not isinstance(items, list):
        return normalized

    for item in items:
        if not isinstance(item, dict):
            continue
        source_type = str(item.get("type") or "").strip().lower()
        file_name = str(
            item.get("file")
            or item.get("filename")
            or item.get("path")
            or ""
        ).strip()
        if source_type not in VALID_SOURCE_TYPES:
            source_type = "code" if file_name else "manual"
        symbol = str(item.get("symbol") or item.get("name") or "").strip()
        note = str(item.get("note") or item.get("description") or "").strip()
        url = str(item.get("url") or "").strip()
        if not any([file_name, symbol, note, url]):
            continue
        normalized.append(
            {
                "type": source_type,
                "file": file_name,
                "symbol": symbol,
                "note": note,
                "url": url,
            }
        )
    return normalized


def normalize_verifications(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            continue
        status = str(item.get("status") or "failed").strip().lower()
        if status not in VALID_STATUSES:
            status = "failed"
        evidence = str(
            item.get("evidence")
            or ""
        ).strip()
        if not evidence:
            evidence = (
                "PR'da bu talab bajarilgani tasdiqlanmadi."
                if status == "failed"
                else "PR/code evidence topildi."
            )
        normalized.append(
            {
                "id": item_id,
                "status": status,
                "evidence": evidence,
                "sources": normalize_sources(item.get("sources")),
            }
        )
    return normalized


def normalize_single_verification(
    item: dict[str, Any],
    *,
    requirement: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    expected_id = str(requirement.get("id") or "").strip()
    normalized_items = normalize_verifications([item])
    if normalized_items:
        normalized = normalized_items[0]
    else:
        normalized = {
            "id": expected_id,
            "status": "failed",
            "evidence": "Agent2 bu requirement uchun valid verification qaytarmadi.",
        }
        warnings.append("Agent2 single verification valid item qaytarmadi.")

    if expected_id and normalized.get("id") != expected_id:
        warnings.append(
            f"Agent2 verification id mos kelmadi: expected={expected_id}, actual={normalized.get('id') or ''}."
        )
        normalized["id"] = expected_id

    return normalized, warnings


def validate_agent2_json(
    parsed: Any,
    *,
    expected_id: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    expected = str(expected_id or "").strip()

    if not isinstance(parsed, dict):
        return {
            "ok": False,
            "data": None,
            "verification": None,
            "error": "agent2_root_not_object",
            "warnings": warnings,
            "retryable": True,
        }

    # AI ba'zan single rejimda ham batch shaklini ({"items":[...]}) qaytaradi —
    # ichidagi bitta verification elementini ochib olamiz.
    if not str(parsed.get("status") or "").strip() and isinstance(parsed.get("items"), list):
        first_item = next((it for it in parsed["items"] if isinstance(it, dict)), None)
        if first_item is not None:
            parsed = first_item

    # Single rejimda qaysi requirement so'ralganini bilamiz (expected). Shuning uchun
    # id yo'q yoki noto'g'ri bo'lsa rad etmaymiz — expected'ni o'zimiz qo'yamiz.
    # Faqat status va evidence haqiqiy signal bo'lgani uchun ular tekshiriladi.
    actual_id = str(parsed.get("id") or "").strip()
    if expected:
        if not actual_id:
            warnings.append("agent2_id_backfilled_missing")
        elif actual_id != expected:
            warnings.append(f"agent2_id_backfilled expected={expected} actual={actual_id}")
        actual_id = expected
    elif not actual_id:
        return {
            "ok": False,
            "data": None,
            "verification": None,
            "error": "agent2_missing_id",
            "warnings": warnings,
            "retryable": True,
        }

    raw_status = str(parsed.get("status") or "").strip()
    if not raw_status:
        return {
            "ok": False,
            "data": None,
            "verification": None,
            "error": "agent2_missing_status",
            "warnings": warnings,
            "retryable": True,
        }
    status = raw_status.lower()
    if status not in VALID_STATUSES:
        return {
            "ok": False,
            "data": None,
            "verification": None,
            "error": f"agent2_invalid_status {raw_status}",
            "warnings": warnings,
            "retryable": True,
        }

    evidence = str(parsed.get("evidence") or "").strip()
    if not evidence:
        return {
            "ok": False,
            "data": None,
            "verification": None,
            "error": "agent2_missing_evidence",
            "warnings": warnings,
            "retryable": True,
        }
    if len(evidence) < 20 or evidence.lower() in {"ok", "done", "bajarilgan", "topilmadi", "yo'q", "yoq"}:
        warnings.append("weak_evidence")

    verification = {
        "id": actual_id,
        "status": status,
        "evidence": evidence,
        "sources": normalize_sources(parsed.get("sources")),
    }
    return {
        "ok": True,
        "data": verification,
        "verification": verification,
        "error": None,
        "warnings": warnings,
        "retryable": False,
    }


def validate_agent2_batch_json(
    parsed: Any,
    *,
    expected_ids: list[str],
) -> dict[str, Any]:
    warnings: list[str] = []
    expected = [str(item or "").strip() for item in expected_ids if str(item or "").strip()]

    if not isinstance(parsed, dict):
        return {
            "ok": False,
            "data": None,
            "verifications": [],
            "error": "agent2_batch_root_not_object",
            "warnings": warnings,
            "missing_ids": expected,
            "retryable": True,
        }

    items = parsed.get("items")
    if not isinstance(items, list):
        return {
            "ok": False,
            "data": None,
            "verifications": [],
            "error": "agent2_batch_items_not_array",
            "warnings": warnings,
            "missing_ids": expected,
            "retryable": True,
        }

    raw_items = [item for item in items if isinstance(item, dict)]
    expected_set = set(expected)

    # 1-bosqich: id'si TO'G'RI bo'lgan javoblarni ishonchli ulaymiz; id'siz yoki
    # noto'g'ri id'li javoblarni keyingi bosqich uchun chetga saqlaymiz.
    # (normalize_verifications id'siz itemlarni tashlab yuboradi — shuning uchun
    #  id'ni AVVAL, raw item ustida to'ldiramiz.)
    matched_raw: dict[str, dict[str, Any]] = {}
    leftover_raw: list[dict[str, Any]] = []
    for item in raw_items:
        item_id = str(item.get("id") or "").strip()
        if item_id and item_id in expected_set and item_id not in matched_raw:
            matched_raw[item_id] = item
        else:
            leftover_raw.append(item)

    # 2-bosqich: qolgan (id'siz/noto'g'ri) javoblarni qolgan talablar bilan
    # TARTIB (navbat) bo'yicha moslaymiz — AI odatda javoblarni so'ralgan tartibда qaytaradi.
    unmatched_expected = [eid for eid in expected if eid not in matched_raw]
    backfilled_ids: list[str] = []
    for eid, item in zip(unmatched_expected, leftover_raw):
        patched = dict(item)
        patched["id"] = eid
        matched_raw[eid] = patched
        backfilled_ids.append(eid)

    normalized = normalize_verifications(
        [matched_raw[eid] for eid in expected if eid in matched_raw]
    )
    by_id = {str(item.get("id") or "").strip(): item for item in normalized}
    missing_ids = [item_id for item_id in expected if item_id not in by_id]
    unused_count = max(0, len(leftover_raw) - len(unmatched_expected))

    if backfilled_ids:
        if len(backfilled_ids) == 1:
            warnings.append(
                f"Agent2 batch: {backfilled_ids[0]} id'siz/noto'g'ri qaytdi — "
                "tartib bo'yicha tiklandi."
            )
        else:
            warnings.append(
                f"Agent2 batch: {len(backfilled_ids)} ta verification id tartib bo'yicha "
                f"taxmin qilindi ({', '.join(backfilled_ids[:10])}) — tekshirib ko'ring."
            )
    if unused_count:
        warnings.append(f"Agent2 batch ortiqcha {unused_count} ta javob qaytardi.")
    if missing_ids:
        warnings.append(f"Agent2 batch ayrim idlarni qaytarmadi: {', '.join(missing_ids[:10])}.")

    ordered = [by_id[item_id] for item_id in expected if item_id in by_id]
    return {
        "ok": bool(ordered),
        "data": parsed,
        "verifications": ordered,
        "error": "" if ordered else "agent2_batch_no_expected_items",
        "warnings": warnings,
        "missing_ids": missing_ids,
        "retryable": bool(missing_ids),
    }


def verification_coverage(
    *,
    requirements: list[dict[str, Any]],
    verifications: list[dict[str, Any]],
) -> dict[str, list[str]]:
    expected_ids = [
        str(item.get("id") or "").strip()
        for item in compact_requirements(requirements)
        if str(item.get("id") or "").strip()
    ]
    actual_ids = [
        str(item.get("id") or "").strip()
        for item in normalize_verifications(verifications)
        if str(item.get("id") or "").strip()
    ]
    expected_set = set(expected_ids)
    actual_set = set(actual_ids)
    return {
        "expected": expected_ids,
        "actual": actual_ids,
        "missing": [item_id for item_id in expected_ids if item_id not in actual_set],
        "invalid": [item_id for item_id in actual_ids if item_id not in expected_set],
    }


def normalize_extra(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        risk = str(item.get("risk") or "").strip().lower()
        if risk not in VALID_EXTRA_RISKS:
            risk = "medium"
        normalized.append(
            {
                "text": text,
                "risk": risk,
            }
        )
    return normalized


def _normalize_for_overlap(text: str) -> str:
    return " ".join(_OVERLAP_TOKEN_RE.findall(str(text or "").lower()))


def _text_overlap_ratio(left: str, right: str) -> float:
    left_norm = _normalize_for_overlap(left)
    right_norm = _normalize_for_overlap(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def verified_requirement_texts(
    requirements: list[dict[str, Any]],
    verifications: list[dict[str, Any]],
) -> list[dict[str, str]]:
    text_by_id = {
        str(item.get("id") or "").strip(): str(item.get("text") or "").strip()
        for item in compact_requirements(requirements)
    }
    verified: list[dict[str, str]] = []
    for item in normalize_verifications(verifications):
        req_id = str(item.get("id") or "").strip()
        text = text_by_id.get(req_id)
        if not text:
            continue
        verified.append({"id": req_id, "text": text, "status": str(item.get("status") or "").strip().lower()})
    return verified


def verified_requirement_lines(
    requirements: list[dict[str, Any]],
    verifications: list[dict[str, Any]],
) -> list[str]:
    return [
        f"- [{item['status'] or 'tekshirilgan'}] {item['id']}: {item['text']}"
        for item in verified_requirement_texts(requirements, verifications)
    ]


def filter_extra_against_requirements(
    *,
    extra_items: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    verifications: list[dict[str, Any]],
    threshold: float = EXTRA_OVERLAP_THRESHOLD,
) -> tuple[list[dict[str, Any]], list[str]]:
    verified_texts = [item["text"] for item in verified_requirement_texts(requirements, verifications)]
    kept: list[dict[str, Any]] = []
    dropped: list[str] = []
    for item in normalize_extra(extra_items):
        extra_text = item.get("text") or ""
        if any(_text_overlap_ratio(extra_text, req_text) >= threshold for req_text in verified_texts):
            dropped.append(extra_text)
            continue
        kept.append(item)
    return kept, dropped
