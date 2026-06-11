import pytest
from pathlib import Path

from services.checkers.tzpr_preflight import Agent1RulesConfig, build_agent1_sanitized_input
from services.checkers.tzpr_presenters import calculate_compliance_score_from_agent3
from services.checkers.tzpr_agents import agent1, agent2, agent3


pytestmark = pytest.mark.no_db


def test_agent1_sanitized_input_contains_only_filtered_sources():
    sanitized = build_agent1_sanitized_input(
        task_details={
            "description": "Sistema buyurtmani saqlashi kerak.",
            "comments": [
                {"author": "Product Owner", "body": "Mobile empty state qo'shilsin."},
                {"author": "Developer", "body": "Ichki texnik izoh."},
            ],
        },
        trusted_authors=["Product Owner"],
        figma_data=None,
        read_comments_enabled=True,
        max_comments_to_read=0,
        rules=Agent1RulesConfig(figma_scope_enabled=False),
    )

    assert set(sanitized) == {"tz", "comments", "figma"}
    assert sanitized["tz"] == "Sistema buyurtmani saqlashi kerak."
    assert sanitized["comments"] == ["Mobile empty state qo'shilsin."]
    assert sanitized["figma"] == []


def test_agent1_sanitized_input_excludes_comments_when_disabled():
    sanitized = build_agent1_sanitized_input(
        task_details={
            "description": "Sistema order statusni ko'rsatishi kerak.",
            "comments": [{"author": "Product Owner", "body": "Trusted comment requirement."}],
        },
        trusted_authors=["Product Owner"],
        figma_data=None,
        read_comments_enabled=False,
        max_comments_to_read=0,
        rules=Agent1RulesConfig(figma_scope_enabled=False),
    )

    assert sanitized["comments"] == []


def test_agent1_runner_does_not_ask_ai_to_repair_malformed_json():
    source = Path("services/checkers/tzpr_agent_runner.py").read_text()

    assert "Fix it to be valid JSON" not in source
    assert "raw[:4000]" not in source
    assert "ai_json_fix" not in source


def test_agent1_recovery_uses_local_json_repair_before_object_salvage():
    recovered = agent1.recover_incomplete_response(
        """
        {
          "requirements": [
            {
              "id": "REQ-1"
              "text": "Birinchi talab",
              "source": "tz"
            }
            {
              "id": "REQ-2",
              "text": "Ikkinchi talab",
              "source": "tz"
            }
          ]
        }
        """
    )

    assert recovered is not None
    assert [item["id"] for item in recovered["requirements"]] == ["REQ-1", "REQ-2"]
    assert "local JSON repair" in recovered["warnings"][-1]


def test_agent1_validation_keeps_new_contract_fields_only():
    validated, warnings = agent1.validate_output(
        [
            {
                "id": "OLD-7",
                "text": "Sistema order statusni ko'rsatishi kerak.",
                "source": "bad-kind",
                "source_section": "acceptance",
                "requirement_type": "acceptance_criterion",
                "testability": "low",
            }
        ]
    )

    assert len(validated) == 1
    item = validated[0]
    assert item == {
        "id": "REQ-1",
        "text": "Sistema order statusni ko'rsatishi kerak.",
        "source": "tz",
    }
    assert "source_section" not in item
    assert "requirement_type" not in item
    assert "testability" not in item
    assert warnings


def test_agent1_json_validator_wraps_requirement_array_and_renumbers():
    result = agent1.validate_agent1_json(
        [
            {"id": "1", "text": "Birinchi talab bajarilishi kerak.", "source": "jira"},
            {"id": "2", "text": "Birinchi talab bajarilishi kerak.", "source": "tz"},
            {"id": "3", "text": "", "source": "tz"},
        ]
    )

    assert result["ok"] is True
    assert result["requirements"] == [
        {"id": "REQ-1", "text": "Birinchi talab bajarilishi kerak.", "source": "tz"}
    ]
    assert result["warnings"]


def test_agent2_json_validator_retries_on_id_mismatch_and_empty_evidence():
    mismatch = agent2.validate_agent2_json(
        {"id": "REQ-2", "status": "completed", "evidence": "Dalil bor."},
        expected_id="REQ-1",
    )
    empty_evidence = agent2.validate_agent2_json(
        {"id": "REQ-1", "status": "completed", "evidence": ""},
        expected_id="REQ-1",
    )

    assert mismatch["ok"] is False
    assert mismatch["retryable"] is True
    assert empty_evidence["ok"] is False
    assert empty_evidence["error"] == "agent2_missing_evidence"


def test_agent3_json_validator_normalizes_risks_string():
    result = agent3.validate_agent3_json(
        {
            "summary": "REQ-1 bajarilgan, REQ-2 manual review talab qiladi.",
            "risks": "REQ-2 texnik sabab bilan tekshirilmadi.",
            "recommendation": "Manual review kerak.",
        }
    )

    assert result["ok"] is True
    assert result["data"]["risks"] == ["REQ-2 texnik sabab bilan tekshirilmadi."]
    assert result["warnings"] == ["agent3_risks_string_wrapped"]


def test_agent2_normalizes_any_non_completed_status_to_failed():
    verifications = agent2.normalize_verifications(
        [
            {
                "id": "REQ-1",
                "status": "partial",
                "evidence": "",
            }
        ]
    )

    assert verifications[0]["status"] == "failed"
    assert verifications[0]["evidence"]


def test_agent2_checker_detects_missing_verifications():
    requirements = [
        {"id": "REQ-1", "text": "Birinchi talab", "source": "tz"},
        {"id": "REQ-2", "text": "Ikkinchi talab", "source": "tz"},
        {"id": "REQ-3", "text": "Uchinchi talab", "source": "tz"},
    ]
    first = [
        {"id": "REQ-1", "status": "completed", "evidence": "Dalil bor."},
    ]

    coverage = agent2.verification_coverage(
        requirements=requirements,
        verifications=first,
    )

    assert coverage["missing"] == ["REQ-2", "REQ-3"]


def test_agent2_single_verification_normalizes_to_expected_requirement_id():
    verification, warnings = agent2.normalize_single_verification(
        {
            "id": "WRONG",
            "status": "completed",
            "evidence": "Dalil bor.",
        },
        requirement={"id": "REQ-1", "text": "Birinchi talab", "source": "tz"},
    )

    assert verification == {
        "id": "REQ-1",
        "status": "completed",
        "evidence": "Dalil bor.",
    }
    assert warnings


def test_agent2_extra_scan_prompt_returns_extra_only_contract():
    prompt = agent2.build_extra_scan_prompt(
        requirements=[
            {"id": "REQ-1", "text": "Birinchi talab", "source": "tz"},
        ],
        pr_info={"pr_details": [{"number": 7, "title": "Test PR"}]},
        code_changes="FILE: app.sql\n+ extra behavior",
    )

    assert '"extra": []' in prompt
    assert "verifications" not in agent2.EXTRA_RESPONSE_SCHEMA["required"]
    assert agent2.EXTRA_RESPONSE_SCHEMA["required"] == ["extra"]


def test_agent3_marks_missing_ids_as_contract_gap():
    artifact = agent3.build_quality_artifact(
        requirements=[
            {"id": "REQ-1", "text": "Birinchi talab", "source": "tz"},
            {"id": "REQ-2", "text": "Ikkinchi talab", "source": "tz"},
        ],
        verifications=[
            {
                "id": "REQ-1",
                "status": "completed",
                "evidence": "Dalil bor.",
            }
        ],
        extra=[],
    )

    assert artifact["quality_status"] == "incomplete_agent2_output"
    assert artifact["missing"] == ["REQ-2"]


def test_agent3_separates_technical_failure_from_real_failed_requirement():
    artifact = agent3.build_quality_artifact(
        requirements=[
            {"id": "REQ-1", "text": "Birinchi talab", "source": "tz"},
            {"id": "REQ-2", "text": "Ikkinchi talab", "source": "tz"},
        ],
        verifications=[
            {
                "id": "REQ-1",
                "status": "completed",
                "evidence": "Dalil bor.",
            },
            {
                "id": "REQ-2",
                "status": "failed",
                "evidence": "Agent2 texnik xato sabab bu requirementni tekshira olmadi.",
            },
        ],
        technical_failures=[
            {
                "id": "REQ-2",
                "error": "empty response",
            }
        ],
        extra=[],
    )

    assert artifact["verdict"] == "manual_review"
    assert artifact["quality_status"] == "technical_verification_unavailable"
    assert artifact["failed"] == []
    assert artifact["technical"] == ["REQ-2"]
    assert artifact["requirements"][1]["status"] == "manual_review"


def test_checker_calculates_compliance_score_from_agent3_counts():
    score = calculate_compliance_score_from_agent3(
        {
            "total_requirements": 10,
            "completed_count": 8,
        }
    )

    assert score == 80


def test_checker_excludes_technical_failures_from_compliance_denominator():
    score = calculate_compliance_score_from_agent3(
        {
            "total_requirements": 15,
            "completed_count": 13,
            "failed_count": 0,
            "technical_count": 2,
        }
    )

    assert score == 100
