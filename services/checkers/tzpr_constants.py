from __future__ import annotations

from typing import Any

EXECUTION_MODE_MULTI = "multi_agent"
PRO_MODEL_NAME = ""
FALLBACK_MODEL_NAME = ""

AGENT_MODEL_FIELDS = {
    "agent1_scope_builder": ("agent1_primary_model", "agent1_fallback_model"),
    "agent1b_merger": ("agent1_primary_model", "agent1_fallback_model"),
    "agent2_verifier": ("agent2_primary_model", "agent2_fallback_model"),
    "agent3_arbiter": ("agent3_primary_model", "agent3_fallback_model"),
}

DEFAULT_AGENT_MODEL_NAMES = {
    "agent1_scope_builder": ("", ""),
    "agent1b_merger": ("", ""),
    "agent2_verifier": ("", ""),
    "agent3_arbiter": ("", ""),
}


def resolve_agent_model_names(checker_settings: Any, agent_key: str) -> tuple[str, str]:
    primary_field, fallback_field = AGENT_MODEL_FIELDS.get(agent_key, ("", ""))
    primary = str(getattr(checker_settings, primary_field, "") or "").strip()
    fallback = str(getattr(checker_settings, fallback_field, "") or "").strip()
    return primary, fallback


def resolve_agent_models(checker_settings: Any) -> dict[str, tuple[str, str]]:
    return {
        agent_key: resolve_agent_model_names(checker_settings, agent_key)
        for agent_key in AGENT_MODEL_FIELDS
    }


def build_agent_sequence(checker_settings: Any = None) -> list[dict[str, Any]]:
    models = resolve_agent_models(checker_settings) if checker_settings is not None else DEFAULT_AGENT_MODEL_NAMES
    return [
        {
            "agent_key": "agent1_scope_builder",
            "agent_label": "Agent1 Scope Builder",
            "agent_order": 1,
            "primary_model": models["agent1_scope_builder"][0],
            "fallback_model": models["agent1_scope_builder"][1],
            "state": "pending",
        },
        {
            "agent_key": "agent2_verifier",
            "agent_label": "Agent2 Verifier",
            "agent_order": 2,
            "primary_model": models["agent2_verifier"][0],
            "fallback_model": models["agent2_verifier"][1],
            "state": "pending",
        },
        {
            "agent_key": "agent3_arbiter",
            "agent_label": "Agent3 Arbiter",
            "agent_order": 3,
            "primary_model": models["agent3_arbiter"][0],
            "fallback_model": models["agent3_arbiter"][1],
            "state": "pending",
        },
    ]


AGENT_SEQUENCE = build_agent_sequence()

FINAL_ANALYSIS_SECTION_TITLES = {
    "completed": "✅ BAJARILGAN TALABLAR",
    "failed": "❌ BAJARILMAGAN TALABLAR",
    "skipped": "⏭️ SKIP QILINGAN (dev izohi — manual tekshiring)",
    "issues": "🐛 POTENSIAL MUAMMOLAR",
    "figma": "🎨 FIGMA DIZAYN MOSLIGI",
}

RUN_BASED_EXECUTION_MODES = {
    EXECUTION_MODE_MULTI,
}


def normalize_execution_mode(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == EXECUTION_MODE_MULTI:
        return normalized
    return EXECUTION_MODE_MULTI


def execution_mode_display_label(value: str) -> str:
    return "Multi-agent"
