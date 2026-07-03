#!/usr/bin/env python3
"""Golden eval harness — multi-agent checker pipeline'ni yozib olingan Gemini
javoblari bilan replay qiladi. Tarmoq YO'Q, DB YO'Q.

Nima REAL ishlaydi: AgentRunnerMixin (agent1 → agent1b → agent2 per-req →
extra scan → agent3), parse_gemini_json, barcha validate_*/normalize_*
kontraktlar, build_quality_artifact, compliance score va final analysis text.

Nima FAKE: Gemini chaqiruvi (yozib olingan javoblar) va run-state persistence
(no-op). Batafsil: eval/README.md.

Ishga tushirish:
    .venv/bin/python eval/run_eval.py            # hamma case
    .venv/bin/python eval/run_eval.py --case case_01_fail_verdict
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

from services.checkers.tzpr_agent_runner import AgentRunnerMixin  # noqa: E402
from services.checkers.tzpr_presenters import (  # noqa: E402
    build_extra_issue_lines,
    build_final_analysis_text,
    calculate_compliance_score_from_agent3,
)

_AGENT_KEY_TO_RESPONSE_KEY = {
    "agent1_scope_builder": "agent1",
    "agent1b_merger": "agent1b",
    "agent2_verifier": "agent2",
    "agent3_arbiter": "agent3",
}


class ResponseStore:
    """gemini_responses.json dagi yozib olingan javoblarni beradi."""

    def __init__(self, path: Path):
        self._path = path
        self._responses: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        self._used: set[str] = set()

    def take(self, key: str) -> str:
        if key not in self._responses:
            raise KeyError(
                f"{self._path.parent.name}: gemini_responses.json da '{key}' kaliti yo'q "
                f"(mavjud: {sorted(self._responses)})"
            )
        self._used.add(key)
        value = self._responses[key]
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    def unused_keys(self) -> list[str]:
        return sorted(set(self._responses) - self._used)


class FakeGemini:
    """GeminiHelper o'rnini bosuvchi — bitta agent kaliti uchun javob qaytaradi."""

    def __init__(self, store: ResponseStore, response_key: str):
        self._store = store
        self._response_key = response_key
        self.last_model_used = "eval-model"
        self.last_usage_metadata: dict[str, int] = {}
        self.last_used_fallback = False
        self.last_primary_model_name = "eval-model"
        self.last_fallback_model_name = ""
        self.last_request_time = 0.0
        self.request_count = 0

    def analyze(self, prompt: str, **_kwargs: Any) -> str:
        self.request_count += 1
        return self._store.take(self._response_key)

    def create_cache(self, *_args: Any, **_kwargs: Any) -> str:
        return ""

    def delete_cache(self, _name: str) -> None:
        return None


def _req_id_from_single_prompt(prompt: str) -> str:
    tail = prompt.rsplit("REQUIREMENT:", 1)[-1]
    match = re.search(r'"id"\s*:\s*"([^"]+)"', tail)
    if not match:
        raise ValueError("Agent2 single promptidan requirement id topilmadi")
    return match.group(1)


class _EvalService:
    """TZPRMultiAgentService o'rnini bosuvchi minimal stub."""

    def __init__(self, code_changes: str):
        self._code_changes = code_changes

    def _build_code_changes_section(self, _pr_info, *, max_files=None, show_full_diff=True, use_smart_patch=False) -> str:
        return self._code_changes

    def _get_creds(self) -> dict[str, Any]:
        return {"gemini_keys": ["eval-key"]}


class EvalExecutor(AgentRunnerMixin):
    """Real AgentRunnerMixin + fake Gemini + no-op run-state persistence."""

    def __init__(self, store: ResponseStore, code_changes: str, task_key: str = "EVAL-1"):
        self.store = store
        self.task_key = task_key
        self.run_id = "eval-run"
        self.company_id = None
        self.user_id = None
        self.service = _EvalService(code_changes)
        self._agent_helpers: dict[str, Any] = {}

    # --- run-state persistence seam: DB o'rniga no-op ---
    def _set_run_state(self, *args: Any, **kwargs: Any) -> None:
        pass

    def _start_agent(self, *args: Any, **kwargs: Any) -> None:
        pass

    def _finish_agent(self, *args: Any, **kwargs: Any) -> None:
        pass

    def _set_agent_state(self, *args: Any, **kwargs: Any) -> None:
        pass

    def _event(self, *args: Any, **kwargs: Any) -> None:
        pass

    # --- model seam: Gemini o'rniga yozib olingan javoblar ---
    def _model_names_for_agent(self, agent_key: str) -> tuple[str, str]:
        return "eval-model", ""

    def _require_model_names_for_agent(self, agent_key: str) -> tuple[str, str]:
        return "eval-model", ""

    def _model_for_agent(self, agent_key: str) -> FakeGemini:
        response_key = _AGENT_KEY_TO_RESPONSE_KEY[agent_key]
        helper = FakeGemini(self.store, response_key)
        self._agent_helpers[agent_key] = helper
        return helper

    def _call_agent2_single_raw_isolated(
        self,
        prompt: str,
        api_keys: list[str],
        cached_content: str = "",
        fallback_cached_content: str = "",
        shared_state: dict[str, Any] | None = None,
        force_model: str = "",
    ) -> tuple[str, str, dict[str, int]]:
        req_id = _req_id_from_single_prompt(prompt)
        return self.store.take(f"agent2.{req_id}"), "eval-model", {}

    def _call_agent2_batch_raw_isolated(self, *args: Any, **kwargs: Any):
        raise AssertionError("Eval agent2_batch_size=1 bilan ishlaydi — batch chaqiruv kutilmagan")

    def _call_agent2_extra_scan_raw(
        self,
        prompt: str,
        api_keys: list[str],
        cached_content: str = "",
        fallback_cached_content: str = "",
        shared_state: dict[str, Any] | None = None,
    ) -> tuple[str, str, dict[str, int]]:
        return self.store.take("agent2.extra_scan"), "eval-model", {}


def build_context(case_dir: Path) -> tuple[dict[str, Any], str, dict[str, Any]]:
    tz_text = (case_dir / "tz.md").read_text(encoding="utf-8")
    code_changes = (case_dir / "pr_diff.txt").read_text(encoding="utf-8")
    meta_path = case_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    effective_settings = {
        # batch_size=1 + parallelism=1: har requirement alohida, tartibli va
        # deterministik single chaqiruv bo'ladi.
        "agent2_parallelism": 1,
        "agent2_batch_size": 1,
        "agent2_extra_scan_enabled": bool(meta.get("agent2_extra_scan_enabled", True)),
        "read_comments_enabled": False,
        "agent1_rules": {"figma_scope_enabled": False},
    }
    task_key = str(meta.get("task_key") or "EVAL-1")
    task_details = {
        "key": task_key,
        "summary": str(meta.get("summary") or "Eval golden case"),
        "description": tz_text,
        "comments": [],
    }
    pr_info = {
        "pr_details": [{"number": 1, "title": str(meta.get("pr_title") or "Eval PR")}],
        "pr_count": 1,
        "files_changed": 1,
        "total_additions": 10,
        "total_deletions": 2,
        "pr_selection": {},
    }
    context = {
        "effective_settings": effective_settings,
        "effective_use_smart_patch": False,
        "task_details": task_details,
        "pr_info": pr_info,
        "tz_content": tz_text,
        "comment_analysis": {},
        "comment_separated": {"dev_before": [], "dev_after": []},
        "agent3_dev_comments": list(meta.get("dev_comments") or []),
        "figma_data": None,
        "agent1_input": {"tz": tz_text, "comments": [], "figma": []},
        "is_recheck": bool(meta.get("is_recheck")),
        "return_reason": str(meta.get("return_reason") or ""),
        "db_task": {},
    }
    return context, code_changes, meta


def run_pipeline(case_dir: Path) -> dict[str, Any]:
    """Real pipeline kodini replay qilib actual natijani qaytaradi."""
    context, code_changes, meta = build_context(case_dir)
    store = ResponseStore(case_dir / "gemini_responses.json")
    executor = EvalExecutor(store, code_changes, task_key=str(context["task_details"]["key"]))

    agent1 = executor._run_agent1(context)
    if not agent1.get("success"):
        raise RuntimeError(f"Agent1 yiqildi: {agent1.get('error')}")
    agent2 = executor._run_agent2(context, agent1)
    agent3 = executor._run_agent3(context, agent1, agent2)

    compliance_score = calculate_compliance_score_from_agent3(agent3)
    extra_issues = build_extra_issue_lines(agent1, agent2, agent3)
    analysis_text = build_final_analysis_text(
        summary=str(agent3.get("summary") or ""),
        decisions=list(agent3.get("requirements") or []),
        compliance_score=compliance_score,
        figma_data=context["figma_data"],
        extra_issues=extra_issues,
    )

    return {
        "actual": {
            "verdict": agent3.get("verdict"),
            "run_state": agent3.get("run_state"),
            "compliance_score": compliance_score,
            "completed": list(agent3.get("completed") or []),
            "failed": list(agent3.get("failed") or []),
            "skipped": list(agent3.get("skipped") or []),
            "technical": list(agent3.get("technical") or []),
            "extra_code_risk": agent3.get("extra_code_risk"),
            "requirement_statuses": {
                str(row.get("id")): str(row.get("status"))
                for row in list(agent3.get("requirements") or [])
            },
        },
        "analysis_text": analysis_text,
        "unused_response_keys": store.unused_keys(),
        "agent3": agent3,
    }


def run_case(case_dir: Path) -> tuple[bool, list[str]]:
    """Bitta golden case: (ok, hisobot qatorlari)."""
    report: list[str] = []
    expected = json.loads((case_dir / "expected.json").read_text(encoding="utf-8"))
    expected_contains = list(expected.pop("analysis_text_contains", []))

    try:
        outcome = run_pipeline(case_dir)
    except Exception as exc:
        return False, [f"{case_dir.name}: pipeline yiqildi — {exc.__class__.__name__}: {exc}"]

    actual = outcome["actual"]
    ok = True

    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if actual_value != expected_value:
            ok = False
            report.append(f"  MISMATCH {key}:")
            report.append(f"    expected: {json.dumps(expected_value, ensure_ascii=False)}")
            report.append(f"    actual:   {json.dumps(actual_value, ensure_ascii=False)}")

    unexpected_keys = sorted(set(actual) - set(expected))
    if unexpected_keys:
        report.append(
            f"  INFO expected.json qamrab olmagan maydonlar: {', '.join(unexpected_keys)}"
        )

    for needle in expected_contains:
        if needle not in outcome["analysis_text"]:
            ok = False
            report.append(f"  MISMATCH analysis_text_contains: '{needle}' topilmadi")

    if outcome["unused_response_keys"]:
        ok = False
        report.append(
            f"  MISMATCH ishlatilmagan gemini javob kalitlari: {outcome['unused_response_keys']} "
            "(golden fayl eskirgan yoki xato kalit)"
        )

    if not ok:
        report.append("  --- actual (to'liq) ---")
        report.append(
            "  " + json.dumps(actual, ensure_ascii=False, indent=2).replace("\n", "\n  ")
        )
    return ok, report


def discover_cases() -> list[Path]:
    if not GOLDEN_DIR.is_dir():
        return []
    return sorted(
        path for path in GOLDEN_DIR.iterdir()
        if path.is_dir() and (path / "expected.json").exists()
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Multi-agent checker golden eval")
    parser.add_argument("--case", help="Faqat bitta case (papka nomi)")
    parser.add_argument(
        "--record",
        action="store_true",
        help="(Hali implement qilinmagan) real Gemini javoblarini yozib olish rejimi",
    )
    args = parser.parse_args(argv)

    if args.record:
        print("--record hali implement qilinmagan. Qo'lda yozib olish: eval/README.md ga qarang.")
        return 2

    cases = discover_cases()
    if args.case:
        cases = [path for path in cases if path.name == args.case]
        if not cases:
            print(f"Case topilmadi: {args.case}")
            return 2
    if not cases:
        print(f"Golden case topilmadi: {GOLDEN_DIR}")
        return 2

    failures = 0
    for case_dir in cases:
        ok, report = run_case(case_dir)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case_dir.name}")
        for line in report:
            print(line)
        if not ok:
            failures += 1

    print(f"\n{len(cases) - failures}/{len(cases)} case yashil.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
