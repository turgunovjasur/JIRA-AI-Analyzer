"""Markaziy prompt-versiya registri.

Har bir agent modulida `PROMPT_VERSION` bor. Run yaratilganda shu versiyalar
run yozuviga (request_payload.prompt_versions) saqlanadi — keyin har qanday
natijani qaysi prompt versiyasi bergani aniq bo'ladi.

Qoida: prompt matni o'zgarsa PROMPT_VERSION bump qilinadi va `eval/run_eval.py`
yashil bo'lishi shart (batafsil: eval/README.md).
"""
from __future__ import annotations


def get_prompt_versions() -> dict[str, str]:
    from services.checkers.tzpr_agents import agent1, agent1b, agent2, agent3
    from services.generators.testcase_agents import (
        agent2_testcase,
        agent3_testcase_auditor,
    )

    return {
        "checker.agent1": agent1.PROMPT_VERSION,
        "checker.agent1b": agent1b.PROMPT_VERSION,
        "checker.agent2": agent2.PROMPT_VERSION,
        "checker.agent3": agent3.PROMPT_VERSION,
        # Testcase agent1 checker kontraktini qayta ishlatadi (testcase_generator.py)
        "testcase.agent1": agent1.PROMPT_VERSION,
        "testcase.agent2": agent2_testcase.PROMPT_VERSION,
        "testcase.agent3": agent3_testcase_auditor.PROMPT_VERSION,
    }


def get_prompt_versions_for(module_prefix: str) -> dict[str, str]:
    prefix = f"{module_prefix.rstrip('.')}."
    return {
        key: value
        for key, value in get_prompt_versions().items()
        if key.startswith(prefix)
    }
