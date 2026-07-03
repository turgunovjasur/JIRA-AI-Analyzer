import pytest

from utils.ai.usage_cost import estimate_gemini_usage_cost

pytestmark = pytest.mark.no_db


def test_usage_cost_estimator_marks_pro_long_context_and_thinking_tokens():
    cost = estimate_gemini_usage_cost(
        "gemini-2.5-pro",
        {
            "prompt_token_count": 210_000,
            "candidates_token_count": 1_000,
            "thoughts_token_count": 2_000,
            "cached_content_token_count": 10_000,
            "total_token_count": 213_000,
        },
    )

    assert cost["pricing_tier"] == "long_context"
    assert cost["cost_warning"] is True
    assert cost["long_context_pricing"] is True
    assert cost["billable_input_tokens"] == 200_000
    assert cost["billable_cached_tokens"] == 10_000
    assert cost["billable_output_tokens"] == 3_000
    assert cost["estimated_total_cost_usd"] > 0


def test_gemini_helper_captures_thoughts_token_count():
    from utils.ai.gemini_helper import GeminiHelper

    class Usage:
        cached_content_token_count = 3
        prompt_token_count = 100
        candidates_token_count = 20
        thoughts_token_count = 7
        total_token_count = 127

    helper = GeminiHelper.__new__(GeminiHelper)
    helper._set_last_usage_metadata(Usage())

    assert helper.last_thoughts_token_count == 7
    assert helper.last_usage_metadata == {
        "cached_content_token_count": 3,
        "prompt_token_count": 100,
        "candidates_token_count": 20,
        "thoughts_token_count": 7,
        "total_token_count": 127,
    }


def test_ai_usage_repository_insert_contract(monkeypatch):
    from utils.database import ai_usage_repository as repo

    captured = {}

    class FakeConn:
        def __init__(self):
            self.commit_calls = 0

        def commit(self):
            self.commit_calls += 1

    class DummyCursor:
        def fetchone(self):
            return {
                "id": 1,
                "company_id": 9,
                "module_key": "tz_pr_checker",
                "thoughts_token_count": 7,
                "estimated_total_cost_usd": 0.001,
            }

    def fake_execute(conn, query, params=None):
        captured["query"] = query
        captured["params"] = list(params or [])
        return DummyCursor()

    monkeypatch.setattr(repo, "_execute", fake_execute)
    conn = FakeConn()

    row = repo.record_ai_usage_event(
        conn,
        company_id=9,
        user_id=3,
        run_id="run-1",
        task_key="DEV-1",
        module_key="tz_pr_checker",
        agent_key="agent2_verifier",
        source="multi_agent",
        model="gemini-2.5-pro",
        primary_model="gemini-2.5-pro",
        fallback_model="gemini-2.5-flash",
        used_fallback=False,
        usage={
            "prompt_token_count": 100,
            "candidates_token_count": 20,
            "thoughts_token_count": 7,
            "cached_content_token_count": 3,
            "total_token_count": 127,
        },
        cost={
            "billable_input_tokens": 97,
            "billable_output_tokens": 27,
            "billable_cached_tokens": 3,
            "estimated_input_cost_usd": 0.0001,
            "estimated_output_cost_usd": 0.0002,
            "estimated_cached_cost_usd": 0.00001,
            "estimated_total_cost_usd": 0.00031,
            "pricing_tier": "standard",
            "pricing_source": "gemini_api_pricing_estimate",
            "cost_warning": False,
        },
        metadata={"request_kind": "batch"},
        commit=False,
    )

    assert "thoughts_token_count" in captured["query"]
    assert captured["params"][0] == 9
    assert captured["params"][5] == "agent2_verifier"
    assert captured["params"][13] == 7
    assert captured["params"][22] == 0.00031
    assert conn.commit_calls == 0
    assert row["thoughts_token_count"] == 7
