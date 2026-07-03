"""Golden eval testlari — multi-agent checker pipeline'ni yozib olingan
Gemini javoblari bilan replay qiladi (DB/tarmoq kerak emas).

Prompt yoki model o'zgarishi natija sifatini buzsa, shu testlar qizaradi.
Qoida: prompt o'zgarsa PROMPT_VERSION bump + shu testlar yashil bo'lishi shart.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db

REPO_ROOT = Path(__file__).resolve().parent.parent
_RUN_EVAL_PATH = REPO_ROOT / "eval" / "run_eval.py"

_spec = importlib.util.spec_from_file_location("qa_assistant_run_eval", _RUN_EVAL_PATH)
run_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_eval)


def _case_ids() -> list[str]:
    return [path.name for path in run_eval.discover_cases()]


def test_golden_cases_exist():
    assert len(run_eval.discover_cases()) >= 3, "eval/golden ostida kamida 3 ta case bo'lishi kerak"


@pytest.mark.parametrize("case_name", _case_ids())
def test_golden_case(case_name: str):
    case_dir = run_eval.GOLDEN_DIR / case_name
    ok, report = run_eval.run_case(case_dir)
    assert ok, f"Golden case '{case_name}' mos kelmadi:\n" + "\n".join(report)


def test_prompt_version_registry():
    from core.prompt_registry import get_prompt_versions, get_prompt_versions_for

    versions = get_prompt_versions()
    expected_keys = {
        "checker.agent1",
        "checker.agent1b",
        "checker.agent2",
        "checker.agent3",
        "testcase.agent1",
        "testcase.agent2",
        "testcase.agent3",
    }
    assert set(versions) == expected_keys
    assert all(isinstance(value, str) and value.strip() for value in versions.values())

    checker_only = get_prompt_versions_for("checker")
    assert set(checker_only) == {key for key in expected_keys if key.startswith("checker.")}
