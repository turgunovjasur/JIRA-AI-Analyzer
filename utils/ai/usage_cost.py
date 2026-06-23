"""
AI usage cost estimation helpers.

Bu modul billing provider emas; u operatsion cost tracking uchun deterministic
estimate beradi. Pricing qiymatlari model oilasi bo'yicha markazlashgan.
"""
from __future__ import annotations

from typing import Any

from config.token_limits import (
    AI_COST_WARNING_INPUT_TOKENS,
    AI_LONG_CONTEXT_PRICE_THRESHOLD_TOKENS,
)


_MILLION = 1_000_000


def _int_value(source: dict[str, Any], key: str) -> int:
    try:
        return max(0, int(source.get(key) or 0))
    except (TypeError, ValueError):
        return 0


def _model_family(model_name: str) -> str:
    model = str(model_name or "").strip().lower()
    if "gemini-2.5-pro" in model:
        return "gemini-2.5-pro"
    if "gemini-2.5-flash-lite" in model:
        return "gemini-2.5-flash-lite"
    if "gemini-2.5-flash" in model:
        return "gemini-2.5-flash"
    return "unknown"


def _pricing_for(model_name: str, prompt_tokens: int) -> dict[str, Any]:
    family = _model_family(model_name)
    long_context = prompt_tokens > AI_LONG_CONTEXT_PRICE_THRESHOLD_TOKENS

    if family == "gemini-2.5-pro":
        return {
            "family": family,
            "tier": "long_context" if long_context else "standard",
            "input_per_million": 2.50 if long_context else 1.25,
            "output_per_million": 15.00 if long_context else 10.00,
            "cached_per_million": 0.625 if long_context else 0.3125,
            "source": "gemini_api_pricing_estimate",
        }
    if family == "gemini-2.5-flash":
        return {
            "family": family,
            "tier": "standard",
            "input_per_million": 0.30,
            "output_per_million": 2.50,
            "cached_per_million": 0.075,
            "source": "gemini_api_pricing_estimate",
        }
    if family == "gemini-2.5-flash-lite":
        return {
            "family": family,
            "tier": "standard",
            "input_per_million": 0.10,
            "output_per_million": 0.40,
            "cached_per_million": 0.025,
            "source": "gemini_api_pricing_estimate",
        }

    return {
        "family": family,
        "tier": "unknown",
        "input_per_million": 0.0,
        "output_per_million": 0.0,
        "cached_per_million": 0.0,
        "source": "unknown_model",
    }


def estimate_gemini_usage_cost(model_name: str, usage: dict[str, Any] | None) -> dict[str, Any]:
    """Return token buckets and estimated USD cost for one Gemini response."""
    source = usage or {}
    prompt_tokens = _int_value(source, "prompt_token_count")
    candidates_tokens = _int_value(source, "candidates_token_count")
    thoughts_tokens = _int_value(source, "thoughts_token_count")
    cached_tokens = _int_value(source, "cached_content_token_count")
    total_tokens = _int_value(source, "total_token_count")

    billable_cached_tokens = min(cached_tokens, prompt_tokens)
    billable_input_tokens = max(0, prompt_tokens - billable_cached_tokens)
    billable_output_tokens = candidates_tokens + thoughts_tokens
    pricing = _pricing_for(model_name, prompt_tokens)

    input_cost = (billable_input_tokens / _MILLION) * float(pricing["input_per_million"])
    output_cost = (billable_output_tokens / _MILLION) * float(pricing["output_per_million"])
    cached_cost = (billable_cached_tokens / _MILLION) * float(pricing["cached_per_million"])
    total_cost = input_cost + output_cost + cached_cost

    return {
        "model_family": pricing["family"],
        "pricing_tier": pricing["tier"],
        "pricing_source": pricing["source"],
        "prompt_token_count": prompt_tokens,
        "candidates_token_count": candidates_tokens,
        "thoughts_token_count": thoughts_tokens,
        "cached_content_token_count": cached_tokens,
        "total_token_count": total_tokens,
        "billable_input_tokens": billable_input_tokens,
        "billable_output_tokens": billable_output_tokens,
        "billable_cached_tokens": billable_cached_tokens,
        "estimated_input_cost_usd": round(input_cost, 8),
        "estimated_output_cost_usd": round(output_cost, 8),
        "estimated_cached_cost_usd": round(cached_cost, 8),
        "estimated_total_cost_usd": round(total_cost, 8),
        "cost_warning": prompt_tokens >= AI_COST_WARNING_INPUT_TOKENS,
        "long_context_pricing": prompt_tokens > AI_LONG_CONTEXT_PRICE_THRESHOLD_TOKENS,
    }
