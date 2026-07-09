from __future__ import annotations

import json
from typing import Any

from .agent2 import normalize_extra, normalize_verifications

# Prompt matni o'zgarsa bump qiling (format: YYYY.MM.DD-N) va eval o'tkazing.
PROMPT_VERSION = "2026.07.03-1"


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "risks": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommendation": {"type": "string"},
        "skipped": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["id", "reason"],
            },
        },
    },
    "required": ["summary", "recommendation"],
}


def build_prompt(
    *,
    requirements: list[dict[str, Any]],
    verifications: list[dict[str, Any]],
    extra: list[dict[str, Any]],
    technical_failures: list[dict[str, Any]] | None = None,
    dev_comments: list[dict[str, Any]] | None = None,
) -> str:
    payload = {
        "requirements": compact_requirements(requirements),
        "verifications": normalize_verifications(verifications),
        "extra": normalize_extra(extra),
        "technical_failures": compact_technical_failures(technical_failures or []),
        "dev_comments": _compact_dev_comments(dev_comments or []),
    }
    return f"""Siz Agent3 — professional checker arbiter va human-readable final summarizer.

Missiya:
Agent1 requirement inventory va Agent2 verification natijalarini inson o'qiydigan yakuniy xulosaga aylantiring. Siz yangi requirement yaratmaysiz, Agent2 statuslarini qayta ixtiro qilmaysiz, score hisoblamaysiz va final matrix qaytarmaysiz. Matrix deterministic kod orqali quriladi; siz faqat aniq summary, risklar, recommendation va (kerak bo'lsa) skip qarorini yozasiz.

Asosiy kontrakt:
- Faqat valid JSON qaytaring; JSONdan tashqari izoh yozmang.
- Output `summary`, `risks`, `recommendation` va ixtiyoriy `skipped` maydonlaridan iborat bo'lsin.
- Verdict, score, completed/failed ro'yxatlari yoki matrix qaytarmang.
- Requirement ID'larini inputdagi `REQ-*` shaklida ishlating; `completed-1`, `failed-1` kabi yangi ID yasamang.
- Summary qisqa, aniq va QA/manager o'qishi uchun tushunarli bo'lsin.

Arbitraj qoidasi:
- Agent2 `completed` degan requirementlarni bajarilgan deb qabul qiling; shubha bo'lsa summaryda evidence zaifligini risk sifatida eslating, lekin statusni o'zingiz almashtirmang.
- Agent2 `failed` degan requirementlarni bajarilmagan deb tushuntiring; aynan qaysi requirement IDlari va umumiy sabablar borligini qisqa yozing.
- `technical_failures` bo'lsa, bu product failure emas, checker tekshira olmagan holat ekanini alohida risk sifatida yozing.
- `extra` itemlar bor bo'lsa, requirement failed natijasini takrorlamasdan, faqat qo'shimcha code scope/risk sifatida eslating. Failed requirement bilan aynan bir xil gapni duplicate risk qilib yozmang.
- Agar ambiguous yoki manual tekshiruv talab qiladigan dalillar bo'lsa, recommendationda manual review kerakligini aniq yozing.

SKIP qoidasi (dev commentlar asosida) — juda muhim:
- `dev_comments` — task assignee/reporter yozgan izohlar. Ular faqat TUSHUNTIRADI; ular kodni KO'RSATMAYDI va o'zicha "bajarildi" isboti EMAS.
- Faqat Agent2 `failed` degan requirement uchun skip ko'rib chiqing. completed yoki technical requirementga tegmang.
- Agar biror `failed` requirement uchun dev comment ISHONCHLI va ANIQ texnik sabab bersa (masalan: "bu logika boshqa repozitoriyada", "bu qism alohida task/PR da", "bu PR scope'idan tashqarida"), uni `skipped` ro'yxatiga qo'shing — `{{"id": "REQ-X", "reason": "<dev izohiga asoslangan qisqa sabab>"}}`.
- Shubhali, umumiy yoki "ishonib qo'yaqoling" tipidagi izohga skip BERMANG. Dalil aniq bo'lmasa requirement `failed` bo'lib qolsin.
- skip = "bajarildi" degani EMAS; skip = "bu yerda tekshirib bo'lmaydi, QA manual tekshirsin" degani. Buni summaryda aniq yozing.

Recommendation qoidasi:
- Skip qilinmagan failed requirementlar bo'lsa: return/fix kerakligini yozing.
- Skip qilingan requirementlar bo'lsa: ular manual tekshiruv talab qilishini yozing.
- Faqat medium/high extra risk bo'lsa: manual review kerakligini yozing.
- Faqat technical failure bo'lsa: checker rerun yoki manual review kerakligini yozing.
- Critical issue topilmasa: ready/approve qilish mumkinligini yozing.

INPUT:
{json.dumps(payload, ensure_ascii=False, indent=2)}

OUTPUT FORMAT:
{{
  "summary": "REQ-1 bajarilgan. REQ-3 kodi shu repoda yo'q, dev mobil repoda deydi — skip, manual tekshirilsin.",
  "risks": ["REQ-3 mobil repoda — manual tekshiruv kerak."],
  "recommendation": "Skip qilingan requirementlarni QA manual tekshirsin.",
  "skipped": [{{"id": "REQ-3", "reason": "Dev: mobil logika smartup5x_mobile repoda, bu PR scope'idan tashqarida."}}]
}}""".strip()


def _compact_dev_comments(dev_comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for item in dev_comments or []:
        if not isinstance(item, dict):
            continue
        body = str(item.get("body") or "").strip()
        if not body:
            continue
        compact.append(
            {
                "author": str(item.get("author") or "Unknown").strip() or "Unknown",
                "body": body,
            }
        )
    return compact


def validate_agent3_json(parsed: Any) -> dict[str, Any]:
    warnings: list[str] = []
    if not isinstance(parsed, dict):
        return {
            "ok": False,
            "data": None,
            "error": "agent3_root_not_object",
            "warnings": warnings,
            "retryable": True,
        }

    summary = str(parsed.get("summary") or "").strip()
    if not summary:
        return {
            "ok": False,
            "data": None,
            "error": "agent3_missing_summary",
            "warnings": warnings,
            "retryable": True,
        }

    recommendation = str(parsed.get("recommendation") or "").strip()
    if not recommendation:
        return {
            "ok": False,
            "data": None,
            "error": "agent3_missing_recommendation",
            "warnings": warnings,
            "retryable": True,
        }

    risks_value = parsed.get("risks")
    if risks_value is None:
        risks: list[str] = []
    elif isinstance(risks_value, list):
        risks = [str(item).strip() for item in risks_value if str(item).strip()]
    elif str(risks_value).strip():
        risks = [str(risks_value).strip()]
        warnings.append("agent3_risks_string_wrapped")
    else:
        risks = []

    if len(summary) < 20:
        warnings.append("weak_summary")

    skipped: list[dict[str, str]] = []
    skipped_value = parsed.get("skipped")
    if isinstance(skipped_value, list):
        for item in skipped_value:
            if not isinstance(item, dict):
                continue
            skip_id = str(item.get("id") or "").strip()
            skip_reason = str(item.get("reason") or "").strip()
            if skip_id and skip_reason:
                skipped.append({"id": skip_id, "reason": skip_reason})

    return {
        "ok": True,
        "data": {
            "summary": summary,
            "risks": risks,
            "recommendation": recommendation,
            "skipped": skipped,
        },
        "error": None,
        "warnings": warnings,
        "retryable": False,
    }


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


def build_quality_artifact(
    *,
    requirements: list[dict[str, Any]],
    verifications: list[dict[str, Any]],
    extra: list[dict[str, Any]] | None = None,
    technical_failures: list[dict[str, Any]] | None = None,
    parsed: dict[str, Any] | None = None,
    agent2_success: bool = True,
    dev_comments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    # Skip uchun asos bo'lgan dev izohi(lari) — har skip qatorida ko'rsatiladi
    dev_comment_bodies = [
        c
        for c in (dev_comments or [])
        if isinstance(c, dict) and str(c.get("body") or "").strip()
    ]
    dev_comment_quote = " | ".join(
        f'{str(c.get("author") or "Dev").strip()}: "{str(c.get("body") or "").strip()}"'
        for c in dev_comment_bodies
    )

    skip_map: dict[str, str] = {}
    if isinstance(parsed, dict):
        for skip_item in (parsed.get("skipped") or []):
            if not isinstance(skip_item, dict):
                continue
            skip_id = str(skip_item.get("id") or "").strip()
            skip_reason = str(skip_item.get("reason") or "").strip()
            if skip_id and skip_reason:
                skip_map[skip_id] = skip_reason

    compact_reqs = compact_requirements(requirements)
    compact_verifications = normalize_verifications(verifications)
    compact_extra = normalize_extra(extra or [])

    req_ids = [str(item.get("id") or "").strip() for item in compact_reqs if str(item.get("id") or "").strip()]
    req_id_set = set(req_ids)
    verification_ids = [
        str(item.get("id") or "").strip()
        for item in compact_verifications
        if str(item.get("id") or "").strip()
    ]
    verification_id_set = set(verification_ids)
    missing = [req_id for req_id in req_ids if req_id not in verification_id_set]
    invalid = [
        verification_id
        for verification_id in verification_ids
        if verification_id not in req_id_set
    ]

    ver_map = {str(item.get("id") or "").strip(): item for item in compact_verifications}
    technical_failure_items = compact_technical_failures(technical_failures or [])
    technical_failure_map = {
        str(item.get("id") or "").strip(): item
        for item in technical_failure_items
        if str(item.get("id") or "").strip()
    }
    completed: list[str] = []
    failed: list[str] = []
    technical: list[str] = []
    requirement_rows: list[dict[str, Any]] = []
    for requirement in compact_reqs:
        req_id = str(requirement.get("id") or "").strip()
        verification = ver_map.get(req_id) or {}
        status = str(verification.get("status") or "failed").strip().lower()
        if status not in {"completed", "failed"}:
            status = "failed"
            invalid.append(req_id)
        if req_id in missing:
            status = "failed"
        evidence = str(verification.get("evidence") or "").strip()
        sources = list(verification.get("sources") or [])

        if req_id in technical_failure_map:
            status = "manual_review"
            technical.append(req_id)
            if not evidence:
                evidence = "Agent2 bu requirementni texnik sabab bilan tekshira olmadi."
        elif status == "completed":
            completed.append(req_id)
        else:
            failed.append(req_id)
            if not evidence:
                evidence = "Agent2 bu requirement uchun verification qaytarmadi."
        requirement_rows.append(
            {
                "id": req_id,
                "text": requirement.get("text") or "",
                "source": requirement.get("source") or "tz",
                "status": status,
                "evidence": evidence,
                "sources": sources,
                "technical_failure": req_id in technical_failure_map,
            }
        )

    invalid = list(dict.fromkeys(item for item in invalid if item))

    # Skip: Agent3 dev commentlar asosida ba'zi FAILED requirementlarni skip qiladi.
    # Skip qilinganlar failed'dan chiqariladi va balъ maxrajiga kirmaydi (checker hisoblaydi).
    skipped: list[str] = []
    if skip_map:
        skip_ids = {req_id for req_id in failed if req_id in skip_map}
        if skip_ids:
            failed = [req_id for req_id in failed if req_id not in skip_ids]
            skipped = [req_id for req_id in req_ids if req_id in skip_ids]
            has_dev_comment = bool(dev_comment_quote)
            for row in requirement_rows:
                if row["id"] in skip_ids and row["status"] == "failed":
                    reason = skip_map.get(row["id"], "")
                    row["status"] = "skipped"
                    row["skip_reason"] = reason
                    evidence = f"⏭️ Skip sababi: {reason}" if reason else "⏭️ Skip qilingan"
                    if has_dev_comment:
                        evidence = f"{evidence}  ·  💬 Dev izohi (skip asosi): {dev_comment_quote}"
                    else:
                        evidence = (
                            f"{evidence}  ·  ⚠️ Bu skip agent3 tomonidan DEV COMMENTSIZ qilindi "
                            "(arbiter'ga mos dev izohi yetmagan) — manual tekshiring."
                        )
                    row["evidence"] = evidence
                    row["dev_comments"] = list(dev_comment_bodies)
                    row["skip_without_dev_comment"] = not has_dev_comment

    extra_risk = highest_extra_risk(compact_extra)

    if not agent2_success or missing or invalid:
        verdict = "blocked"
        verdict_label = "Blocked"
        verdict_reason = "Agent2 output contract buzilgan."
        run_state = "blocked"
        quality_status = "agent2_failed" if not agent2_success else "invalid_agent2_output" if invalid else "incomplete_agent2_output"
    elif failed:
        verdict = "fail"
        verdict_label = "Need Work"
        verdict_reason = "Bajarilmagan requirementlar topildi."
        run_state = "completed"
        quality_status = "ok"
    elif technical or skipped:
        verdict = "manual_review"
        verdict_label = "Manual Review"
        if skipped and technical:
            verdict_reason = "Ba'zi requirementlar dev izohi asosida skip qilindi yoki texnik sabab bilan tekshirilmadi — manual tekshiruv kerak."
        elif skipped:
            verdict_reason = "Ba'zi requirementlar dev izohi asosida skip qilindi — manual tekshiruv kerak."
        else:
            verdict_reason = "Ba'zi requirementlar texnik sabab bilan tekshirilmadi."
        run_state = "manual_review"
        quality_status = "technical_verification_unavailable" if technical else "ok"
    elif extra_risk in {"medium", "high"}:
        verdict = "manual_review"
        verdict_label = "Manual Review"
        verdict_reason = "Extra code review talab qiladi."
        run_state = "manual_review"
        quality_status = "ok"
    else:
        verdict = "pass"
        verdict_label = "Ready"
        verdict_reason = "Kritik nomoslik topilmadi."
        run_state = "completed"
        quality_status = "ok"

    return {
        "run_state": run_state,
        "verdict": verdict,
        "verdict_label": verdict_label,
        "verdict_reason": verdict_reason,
        "quality_status": quality_status,
        "total_requirements": len(compact_reqs),
        "completed_count": len(completed),
        "failed_count": len(failed),
        "technical_count": len(technical),
        "skipped_count": len(skipped),
        "completed": completed,
        "failed": failed,
        "technical": technical,
        "skipped": skipped,
        "skip_reasons": {req_id: skip_map.get(req_id, "") for req_id in skipped},
        "missing": missing,
        "invalid": invalid,
        "extra": compact_extra,
        "extra_code_risk": extra_risk,
        "requirements": requirement_rows,
    }


def fallback_arbiter(
    *,
    requirements: list[dict[str, Any]],
    verifications: list[dict[str, Any]],
    agent2_success: bool,
    extra: list[dict[str, Any]] | None = None,
    technical_failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    quality = build_quality_artifact(
        requirements=requirements,
        verifications=verifications,
        extra=extra or [],
        technical_failures=technical_failures or [],
        agent2_success=agent2_success,
    )
    return {
        "summary": build_deterministic_summary(quality),
        **quality,
        "warnings": [],
    }


def build_deterministic_summary(quality: dict[str, Any]) -> str:
    completed = list(quality.get("completed") or [])
    failed = list(quality.get("failed") or [])
    technical = list(quality.get("technical") or [])
    skipped = list(quality.get("skipped") or [])
    missing = list(quality.get("missing") or [])
    invalid = list(quality.get("invalid") or [])
    extra = list(quality.get("extra") or [])
    parts: list[str] = []
    if completed:
        parts.append(f"{len(completed)} ta requirement bajarilgan: {', '.join(completed[:5])}.")
    if failed:
        parts.append(f"{len(failed)} ta requirement bajarilmagan: {', '.join(failed[:5])}.")
    if skipped:
        parts.append(f"{len(skipped)} ta requirement dev izohi asosida skip qilindi (manual tekshiruv kerak): {', '.join(skipped[:5])}.")
    if technical:
        parts.append(f"{len(technical)} ta requirement texnik sabab bilan tekshirilmadi: {', '.join(technical[:5])}.")
    if missing:
        parts.append(f"Agent2 {len(missing)} ta requirement verificationini qaytarmadi: {', '.join(missing[:5])}.")
    if invalid:
        parts.append(f"Agent2 {len(invalid)} ta noma'lum/invalid verification qaytardi: {', '.join(invalid[:5])}.")
    if extra:
        parts.append(f"Qo'shimcha kod o'zgarishi topildi; eng yuqori risk: {quality.get('extra_code_risk') or 'medium'}.")
    if not parts:
        parts.append("Requirementlar bo'yicha yakuniy xulosa tayyor.")
    return " ".join(parts)


def highest_extra_risk(extra_items: list[dict[str, Any]]) -> str:
    rank = {"none": 0, "low": 1, "medium": 2, "high": 3}
    highest = "none"
    for item in extra_items or []:
        risk = str(item.get("risk") or "medium").strip().lower()
        if risk not in rank:
            risk = "medium"
        if rank[risk] > rank[highest]:
            highest = risk
    return highest


def normalize_arbiter_decisions(
    items: list[dict[str, Any]],
    *,
    requirements: list[dict[str, Any]],
    verifications: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    del items
    return build_quality_artifact(
        requirements=requirements,
        verifications=verifications,
        extra=[],
    )["requirements"]


def compact_technical_failures(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            continue
        error = str(item.get("error") or "").strip()
        compact.append(
            {
                "id": item_id,
                "error": error,
            }
        )
    return compact


def status_label(status: str) -> str:
    return {
        "completed": "Bajarilgan",
        "failed": "Bajarilmagan",
        "skipped": "Skip qilingan (dev izohi)",
        "manual_review": "Manual review",
    }.get(status, "Manual review")
