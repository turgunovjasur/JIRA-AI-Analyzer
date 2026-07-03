#!/usr/bin/env python3
"""
Debug multi-agent TZPR input collection for one Jira task.

This script does not call Agent1/Agent2/Agent3 or Gemini. It uses the same
multi-agent checker context collection path and exports:
- Jira task_details as returned to checker
- checker tz_content/comment/figma/pr context
- sanitized Agent1 input

Usage:
    PYTHONPATH=. ./.venv/bin/python scripts/debug_tzpr_input_context.py \
      --task-key DEV-8358 --user-id 160 --company-id 329
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.checkers.tzpr_multi_agent import (
    _TZPRMultiAgentExecutor,
    create_multi_agent_run,
)

OUT_DIR = ROOT / "data" / "debug"


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _truncate_text(value: Any, limit: int = 2000) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...<truncated {len(text) - limit} chars>"


def _comment_preview(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "author": item.get("author"),
            "created": item.get("created"),
            "body": item.get("body"),
            "body_len": len(str(item.get("body") or "")),
        }
        for index, item in enumerate(comments, start=1)
    ]


def _pr_preview(pr_info: dict[str, Any]) -> dict[str, Any]:
    return {
        "pr_count": pr_info.get("pr_count"),
        "files_changed": pr_info.get("files_changed"),
        "total_additions": pr_info.get("total_additions"),
        "total_deletions": pr_info.get("total_deletions"),
        "pr_details": [
            {
                "number": pr.get("number"),
                "title": pr.get("title"),
                "url": pr.get("url"),
                "state": pr.get("state"),
                "merged": pr.get("merged"),
                "files_count": pr.get("files_count"),
                "files": [
                    {
                        "filename": file_item.get("filename"),
                        "status": file_item.get("status"),
                        "additions": file_item.get("additions"),
                        "deletions": file_item.get("deletions"),
                        "patch_len": len(str(file_item.get("patch") or "")),
                        "smart_context_len": len(str(file_item.get("smart_context") or "")),
                    }
                    for file_item in (pr.get("files") or [])
                ],
            }
            for pr in (pr_info.get("pr_details") or [])
        ],
    }


def _build_markdown(report: dict[str, Any]) -> str:
    task = report["checker_context"]["task_details"]
    agent1_input = report["checker_context"]["agent1_input"]
    lines: list[str] = []
    lines.append(f"# TZPR Input Context Debug: {report['meta']['task_key']}")
    lines.append("")
    lines.append("## 1. Jira task_details shape")
    lines.append("```json")
    lines.append(json.dumps(report["jira_task_details_shape"], ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## 2. Jira task_details exact values")
    lines.append("```json")
    lines.append(json.dumps(task, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## 3. Checker tz_content")
    lines.append("```text")
    lines.append(report["checker_context"]["tz_content"])
    lines.append("```")
    lines.append("")
    lines.append("## 4. Agent1 sanitized input")
    lines.append("```json")
    lines.append(json.dumps(agent1_input, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## 5. Agent1 input summary")
    lines.append("```json")
    lines.append(json.dumps(report["agent1_input_summary"], ensure_ascii=False, indent=2))
    lines.append("```")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug checker Jira input and Agent1 sanitized input")
    parser.add_argument("--task-key", required=True)
    parser.add_argument("--user-id", type=int, default=None)
    parser.add_argument("--company-id", type=int, default=None)
    parser.add_argument("--output-profile", default="ui")
    parser.add_argument("--show-full-diff", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--use-smart-patch", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--max-files", type=int, default=None)
    args = parser.parse_args()

    task_key = args.task_key.strip().upper()
    run = create_multi_agent_run(
        task_key=task_key,
        company_id=args.company_id,
        user_id=args.user_id,
        source="manual_debug",
        output_profile=args.output_profile,
        show_full_diff=bool(args.show_full_diff),
        use_smart_patch=args.use_smart_patch,
        max_files=args.max_files,
    )
    executor = _TZPRMultiAgentExecutor(run)
    context = executor._collect_context(emit_events=False)
    if context.get("error_result"):
        error = context["error_result"]
        raise SystemExit(f"Context blocked: {getattr(error, 'error_message', error)}")

    task_details = context["task_details"]
    agent1_input = context.get("agent1_input") or {}
    allowed_agent1_keys = {"tz", "comments", "figma"}
    report = {
        "meta": {
            "task_key": task_key,
            "run_id": run.get("run_id"),
            "company_id": args.company_id,
            "user_id": args.user_id,
            "execution_mode": "multi_agent",
            "exported_at": datetime.now().isoformat(timespec="seconds"),
        },
        "jira_task_details_shape": {
            "keys": list(task_details.keys()),
            "summary_len": len(str(task_details.get("summary") or "")),
            "description_len": len(str(task_details.get("description") or "")),
            "comments_count": len(task_details.get("comments") or []),
            "pr_urls_count": len(task_details.get("pr_urls") or []),
            "figma_links_count": len(task_details.get("figma_links") or []),
            "comment_preview": _comment_preview(task_details.get("comments") or []),
        },
        "checker_context": {
            "effective_settings": context.get("effective_settings"),
            "task_details": task_details,
            "tz_content": context.get("tz_content"),
            "comment_analysis": context.get("comment_analysis"),
            "comment_separated": context.get("comment_separated"),
            "figma_data": context.get("figma_data"),
            "pr_info_preview": _pr_preview(context.get("pr_info") or {}),
            "agent1_input": context.get("agent1_input"),
        },
        "agent1_input_summary": {
            "keys": list(agent1_input.keys()),
            "allowed_keys": sorted(allowed_agent1_keys),
            "extra_keys": sorted(set(agent1_input.keys()) - allowed_agent1_keys),
            "tz_len": len(str(agent1_input.get("tz") or "")),
            "comments_count": len(agent1_input.get("comments") or []),
            "figma_count": len(agent1_input.get("figma") or []),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = f"tzpr_input_context_{task_key}_{_now_stamp()}"
    json_path = OUT_DIR / f"{base}.json"
    md_path = OUT_DIR / f"{base}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_build_markdown(report), encoding="utf-8")

    print(f"[OK] JSON: {json_path}")
    print(f"[OK] MD:   {md_path}")
    print("[SUMMARY]")
    print(json.dumps({
        "run_id": run.get("run_id"),
        "task_key": task_key,
        "description_len": report["jira_task_details_shape"]["description_len"],
        "comments_count": report["jira_task_details_shape"]["comments_count"],
        "pr_urls_count": report["jira_task_details_shape"]["pr_urls_count"],
        "figma_links_count": report["jira_task_details_shape"]["figma_links_count"],
        "agent1_input_keys": report["agent1_input_summary"]["keys"],
        "agent1_extra_keys": report["agent1_input_summary"]["extra_keys"],
        "tz_len": report["agent1_input_summary"]["tz_len"],
        "comments_count": report["agent1_input_summary"]["comments_count"],
        "figma_count": report["agent1_input_summary"]["figma_count"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
