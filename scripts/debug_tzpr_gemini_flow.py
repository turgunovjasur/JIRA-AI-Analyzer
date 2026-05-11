#!/usr/bin/env python3
"""
TZ-PR checker -> Gemini oqimini audit qilish uchun debug script.

Nima beradi:
1) Frontenddan ketadigan payload (simulyatsiya)
2) Backendga uzatiladigan payload (scope bilan)
3) Gemini'ga ketgan prompt + max_output_tokens + model
4) Gemini'dan qaytgan raw matn
5) Frontenddagi accordion logikasiga o'xshash user-facing ko'rinish

Output:
- data/debug/tzpr_gemini_flow_<TASK>_<timestamp>.json
- data/debug/tzpr_gemini_flow_<TASK>_<timestamp>.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from services.checkers.tz_pr_checker import TZPRService
from utils.database.runtime import get_db_backend
from utils.auth.auth_db import (
    get_company_webhook_credentials,
    get_user_by_id,
    get_user_credentials_for_service,
)
from utils.ai import gemini_helper


ROOT = Path(__file__).resolve().parents[1]
AUTH_DB = ROOT / "data" / "auth.db"
PROC_DB = ROOT / "data" / "processing.db"
OUT_DIR = ROOT / "data" / "debug"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clean_inline_markdown(value: str) -> str:
    return re.sub(r"`(.+?)`", r"\1", re.sub(r"\*\*(.+?)\*\*", r"\1", value)).strip()


def _classify_ai_section_key(title: str) -> str:
    normalized = _clean_inline_markdown(title).lower()
    if any(k in normalized for k in ("ijobiy", "bajarilgan", "moslik")):
        return "positive"
    if any(k in normalized for k in ("kamchilik", "bajarilmagan", "muammo")):
        return "issues"
    if any(k in normalized for k in ("tavsiya", "xulosa", "next")):
        return "recommendations"
    if any(k in normalized for k in ("developer", "izoh")):
        return "developer"
    return "developer"


def _parse_ai_analysis_sections(ai_analysis: str) -> List[Dict[str, Any]]:
    lines = ai_analysis.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    sections: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    for raw in lines:
        heading = re.match(r"^#{2,3}\s*(.+)$", raw)
        if heading:
            if current:
                sections.append(current)
            current = {"title": _clean_inline_markdown(heading.group(1) or "Tahlil"), "lines": []}
            continue
        if current is None:
            current = {"title": "Tahlil", "lines": []}
        current["lines"].append(raw)

    if current:
        sections.append(current)

    return [
        s
        for s in sections
        if (s.get("title") or "").strip()
        or any((ln or "").strip() for ln in s.get("lines", []))
    ]


def _build_ai_accordion_sections(ai_analysis: str) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[str]] = {
        "positive": [],
        "issues": [],
        "recommendations": [],
        "developer": [],
    }

    raw_sections = _parse_ai_analysis_sections(ai_analysis or "")
    if not raw_sections:
        fallback = _clean_inline_markdown(ai_analysis or "")
        if fallback:
            buckets["developer"].append(fallback)
    else:
        for section in raw_sections:
            key = _classify_ai_section_key(section.get("title", ""))
            lines = [
                _clean_inline_markdown(line)
                for line in section.get("lines", [])
                if _clean_inline_markdown(line)
            ]
            if not lines:
                continue
            if buckets[key]:
                buckets[key].append("")
            buckets[key].extend(lines)

    return [
        {"key": "positive", "title": "✅ Ijobiy jihatlari", "lines": buckets["positive"]},
        {"key": "issues", "title": "⚠️ Kamchiliklar", "lines": buckets["issues"]},
        {"key": "recommendations", "title": "💡 Tavsiyalar", "lines": buckets["recommendations"]},
        {"key": "developer", "title": "💬 Developer izohlari (AI ko'rdi)", "lines": buckets["developer"]},
    ]


def _get_task_company_id(task_key: str) -> Optional[int]:
    if not PROC_DB.exists():
        return None
    conn = sqlite3.connect(PROC_DB)
    try:
        row = conn.execute(
            "SELECT company_id FROM task_processing WHERE task_id = ? ORDER BY updated_at DESC LIMIT 1",
            [task_key],
        ).fetchone()
        if not row:
            return None
        value = row[0]
        return int(value) if value is not None else None
    finally:
        conn.close()


def _list_active_users(company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if not AUTH_DB.exists():
        return []
    conn = sqlite3.connect(AUTH_DB)
    conn.row_factory = sqlite3.Row
    try:
        if company_id is None:
            rows = conn.execute(
                "SELECT id, username, company_id, role, is_active FROM users WHERE is_active = 1 ORDER BY company_id, id"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, username, company_id, role, is_active FROM users WHERE is_active = 1 AND company_id = ? ORDER BY id",
                [company_id],
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _pick_scope(task_key: str, forced_user_id: Optional[int], forced_company_id: Optional[int]) -> Dict[str, Any]:
    if forced_user_id is not None:
        user = None
        try:
            user = get_user_by_id(forced_user_id)
        except Exception:
            user = None
        if not user:
            for row in _list_active_users():
                if int(row["id"]) == int(forced_user_id):
                    user = row
                    break
        return {
            "scope_type": "user",
            "user_id": int(forced_user_id),
            "company_id": int(user.get("company_id")) if user and user.get("company_id") else None,
            "reason": "CLI user_id berilgan (user lookup ixtiyoriy)",
        }

    if forced_company_id is not None:
        return {
            "scope_type": "company",
            "user_id": None,
            "company_id": int(forced_company_id),
            "reason": "CLI company_id berilgan",
        }

    task_company_id = _get_task_company_id(task_key)

    if task_company_id is not None:
        for user in _list_active_users(task_company_id):
            try:
                get_user_credentials_for_service(int(user["id"]))
                return {
                    "scope_type": "user",
                    "user_id": int(user["id"]),
                    "company_id": int(user["company_id"]),
                    "reason": f"Task company ({task_company_id}) ichida tayyor user topildi",
                }
            except Exception:
                continue

        try:
            get_company_webhook_credentials(task_company_id)
            return {
                "scope_type": "company",
                "user_id": None,
                "company_id": int(task_company_id),
                "reason": f"Task company ({task_company_id}) webhook credential tayyor",
            }
        except Exception:
            pass

    for user in _list_active_users():
        try:
            get_user_credentials_for_service(int(user["id"]))
            return {
                "scope_type": "user",
                "user_id": int(user["id"]),
                "company_id": int(user["company_id"]),
                "reason": "Fallback: boshqa kompaniyadan tayyor user topildi",
            }
        except Exception:
            continue

    raise RuntimeError("Hech qanday tayyor checker scope topilmadi (user/company credentiallar yo'q).")


def _build_report_markdown(payload: Dict[str, Any]) -> str:
    m = payload["meta"]
    run = payload["run"]
    gem = payload["gemini"]
    ui = payload["ui_projection"]

    md: List[str] = []
    md.append(f"# TZPR -> Gemini Flow Audit ({m['task_key']})")
    md.append("")
    md.append(f"- Run time: `{m['run_at']}`")
    md.append(f"- Scope: `{run['scope']['scope_type']}`")
    md.append(f"- user_id: `{run['scope'].get('user_id')}`")
    md.append(f"- company_id: `{run['scope'].get('company_id')}`")
    md.append(f"- Scope tanlash sababi: {run['scope'].get('reason')}")
    md.append("")
    md.append("## Frontend -> Backend payload")
    md.append("```json")
    md.append(json.dumps(payload["request_flow"], ensure_ascii=False, indent=2))
    md.append("```")
    md.append("")
    md.append("## Checker natijasi")
    md.append(f"- success: `{run['result'].get('success')}`")
    md.append(f"- compliance_score: `{run['result'].get('compliance_score')}`")
    md.append(f"- ai_retry_count: `{run['result'].get('ai_retry_count')}`")
    md.append(f"- files_analyzed: `{run['result'].get('files_analyzed')}`")
    md.append(f"- total_prompt_size: `{run['result'].get('total_prompt_size')}`")
    if run.get("status_updates"):
        md.append("- status updates:")
        for s in run["status_updates"]:
            md.append(f"  - `{s['time']}` [{s['level']}] {s['message']}")
    md.append("")
    md.append("## Gemini ga ketgan data")
    md.append(f"- model: `{gem.get('model_name')}`")
    md.append(f"- max_output_tokens: `{gem.get('max_output_tokens')}`")
    md.append(f"- prompt chars: `{gem.get('prompt_chars')}`")
    md.append(f"- response chars: `{gem.get('response_chars')}`")
    md.append(f"- call duration sec: `{gem.get('duration_sec')}`")
    md.append("")
    md.append("### Prompt preview (first 4000 chars)")
    md.append("```text")
    md.append((gem.get("prompt") or "")[:4000])
    md.append("```")
    md.append("")
    md.append("### Gemini raw response preview (first 4000 chars)")
    md.append("```text")
    md.append((gem.get("response") or "")[:4000])
    md.append("```")
    md.append("")
    md.append("## UI'ga qanday ko'rinishda ketadi (accordion projection)")
    for section in ui.get("accordion_sections", []):
        md.append(f"### {section['title']} ({len(section['lines'])} line)")
        if section["lines"]:
            md.append("```text")
            md.append("\n".join(section["lines"][:40]))
            md.append("```")
        else:
            md.append("_Bo'sh_")
    md.append("")
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="DEV task uchun TZPR->Gemini flow debug script")
    parser.add_argument("--task-key", default="DEV-8220", help="Masalan: DEV-8220")
    parser.add_argument("--user-id", type=int, default=None, help="Majburiy user scope")
    parser.add_argument("--company-id", type=int, default=None, help="Majburiy company scope")
    parser.add_argument("--max-files", type=int, default=None, help="Checker max_files")
    parser.add_argument("--show-full-diff", action="store_true", default=True, help="To'liq diff")
    parser.add_argument("--use-smart-patch", action="store_true", default=True, help="Smart patch")
    parser.add_argument(
        "--use-env-creds",
        action="store_true",
        default=False,
        help="DB credential o'rniga .env credentiallarni checkerga inject qilish",
    )
    args = parser.parse_args()

    task_key = (args.task_key or "").strip().upper()
    if not task_key:
        raise SystemExit("task key bo'sh bo'lmasin")
    print(f"[INFO] DB backend: {get_db_backend()}")

    scope = _pick_scope(task_key, args.user_id, args.company_id)
    print(f"[INFO] Scope: {scope}")

    frontend_payload = {
        "task_key": task_key,
        "max_files": args.max_files,
        "show_full_diff": bool(args.show_full_diff),
        "use_smart_patch": bool(args.use_smart_patch),
    }
    backend_payload = {
        **frontend_payload,
        "user_id": scope.get("user_id"),
        "company_id": scope.get("company_id"),
    }

    status_updates: List[Dict[str, str]] = []
    gemini_capture: Dict[str, Any] = {}
    original_analyze = gemini_helper.GeminiHelper.analyze

    def wrapped_analyze(self, prompt, max_output_tokens=32768):
        start = time.time()
        gemini_capture["model_name"] = getattr(self, "model_name", None)
        gemini_capture["api_key_count"] = len(getattr(self, "api_keys", []) or [])
        gemini_capture["max_output_tokens"] = max_output_tokens
        gemini_capture["prompt"] = prompt
        gemini_capture["prompt_chars"] = len(prompt or "")
        response = original_analyze(self, prompt, max_output_tokens=max_output_tokens)
        gemini_capture["response"] = response
        gemini_capture["response_chars"] = len(response or "")
        gemini_capture["duration_sec"] = round(time.time() - start, 3)
        return response

    gemini_helper.GeminiHelper.analyze = wrapped_analyze

    try:
        service = TZPRService(user_id=scope.get("user_id"), company_id=scope.get("company_id"))
        if args.use_env_creds:
            env_keys = [os.getenv("GOOGLE_API_KEY"), os.getenv("GOOGLE_API_KEY_2")]
            service._cached_creds = {
                "jira_server": os.getenv("JIRA_SERVER", "").strip(),
                "jira_email": os.getenv("JIRA_EMAIL", "").strip(),
                "jira_token": os.getenv("JIRA_API_TOKEN", "").strip(),
                "github_token": os.getenv("GITHUB_TOKEN", "").strip(),
                "github_org": os.getenv("GITHUB_ORG", "").strip(),
                "figma_tokens": [],
                "gemini_keys": [k.strip() for k in env_keys if k and k.strip()],
                "gemini_model": (os.getenv("GEMINI_MODEL") or "").strip() or None,
            }
        else:
            # Preload credential bir marta olinadi va service cache'ga qo'yiladi.
            if scope.get("scope_type") == "user" and scope.get("user_id") is not None:
                service._cached_creds = get_user_credentials_for_service(int(scope["user_id"]))
            elif scope.get("scope_type") == "company" and scope.get("company_id") is not None:
                service._cached_creds = get_company_webhook_credentials(int(scope["company_id"]))

        def status_cb(level: str, message: str):
            status_updates.append({"time": _now_iso(), "level": level, "message": message})

        result = service.analyze_task(
            task_key=task_key,
            max_files=args.max_files,
            show_full_diff=bool(args.show_full_diff),
            use_smart_patch=bool(args.use_smart_patch),
            status_callback=status_cb,
        )
    finally:
        gemini_helper.GeminiHelper.analyze = original_analyze

    result_dict = asdict(result)
    ui_projection = {
        "accordion_sections": _build_ai_accordion_sections(result_dict.get("ai_analysis") or "")
    }

    report = {
        "meta": {
            "task_key": task_key,
            "run_at": _now_iso(),
            "script": str(Path(__file__).resolve()),
        },
        "request_flow": {
            "frontend_payload": frontend_payload,
            "backend_payload": backend_payload,
        },
        "run": {
            "scope": scope,
            "status_updates": status_updates,
            "result": result_dict,
        },
        "gemini": gemini_capture,
        "ui_projection": ui_projection,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"tzpr_gemini_flow_{task_key}_{stamp}"
    json_path = OUT_DIR / f"{base}.json"
    md_path = OUT_DIR / f"{base}.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_build_report_markdown(report), encoding="utf-8")

    print(f"[OK] Report JSON: {json_path}")
    print(f"[OK] Report MD:   {md_path}")
    print(f"[INFO] Result success={result_dict.get('success')} compliance={result_dict.get('compliance_score')}")
    if not result_dict.get("success"):
        print(f"[WARN] error_message: {result_dict.get('error_message')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
