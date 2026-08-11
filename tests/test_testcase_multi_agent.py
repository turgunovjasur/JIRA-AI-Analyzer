"""Testcase (Servis-2) multi-agent oqim testlari.

Agent1 (talab ajratuvchi, checker kontrakti reuse) → Agent2 (testcase yozuvchi)
→ Agent3 (audit/grouping). PR ishlatilmaydi. Bu testlar DB talab qilmaydi.
"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.no_db


LONG_TZ = (
    "Login sahifasini yaratish kerak. Foydalanuvchi username va parol kiritib "
    "tizimga kira olishi kerak. Validatsiya: bo'sh maydon xatosi, noto'g'ri parol "
    "xatosi, muvaffaqiyatli kirish. Sessiya boshqaruvi ham talab qilinadi."
)


def test_s2_comment_uses_shared_publisher_without_section_filter(monkeypatch):
    import utils.auth.auth_db as auth_db
    import utils.jira.jira_comment_writer as writer_module
    import utils.jira.testcase_adf_formatter as formatter_module
    from services.webhook.testcase_webhook_handler import _write_testcases_comment
    from utils.jira import jira_comment_publisher
    from utils.jira.jira_comment_publisher import JiraCommentPublishResult

    calls: dict = {}

    class FakePublisher:
        def __init__(self, writer):
            calls["writer"] = writer

        def publish_adf(self, task_key, document, **kwargs):
            calls["task_key"] = task_key
            calls["document"] = document
            calls.update(kwargs)
            calls["simple"] = kwargs["simple_fallback"]()
            return JiraCommentPublishResult(success=True, part_count=3, split=True)

    monkeypatch.setattr(jira_comment_publisher, "JiraCommentPublisher", FakePublisher)
    monkeypatch.setattr(
        auth_db,
        "get_company_webhook_credentials",
        lambda company_id: {
            "jira_server": "https://jira.example.com",
            "jira_email": "qa@example.com",
            "jira_token": "secret",
        },
    )
    writer = MagicMock()
    writer.add_comment_adf.return_value = True
    monkeypatch.setattr(writer_module, "JiraCommentWriter", lambda **kwargs: writer)
    formatter = MagicMock()
    formatter.build_testcase_document.return_value = {"type": "doc", "content": []}
    formatter.build_simple_comment.return_value = "simple-s2"
    monkeypatch.setattr(formatter_module, "TestcaseADFFormatter", lambda: formatter)
    result = SimpleNamespace(test_cases=[SimpleNamespace(id="TC-1")], test_scenarios=[], agent_runs=[])

    success, message = _write_testcases_comment(
        task_key="DEV-1",
        result=result,
        use_adf=True,
        footer_text="footer",
        company_id=1,
    )

    assert success is True
    assert "1 test cases" in message
    assert calls["writer"] is writer
    assert calls["marker"] == "[AI_S2]"
    assert calls["service_name"] == "Servis-2"
    assert calls["simple"] == "simple-s2"
    assert "jira_comment_sections" not in formatter.build_testcase_document.call_args.kwargs

AGENT1_JSON = json.dumps(
    {
        "requirements": [
            {"id": "REQ-1", "text": "Foydalanuvchi username va parol bilan tizimga kira olsin", "source": "tz"},
            {"id": "REQ-2", "text": "Noto'g'ri parol uchun xato xabari ko'rsatilsin", "source": "tz"},
        ]
    },
    ensure_ascii=False,
)

AGENT2_JSON = json.dumps(
    {
        "test_cases": [
            {
                "id": "TC-001", "title": "Muvaffaqiyatli login", "description": "d",
                "preconditions": "p", "steps": ["1. ochish", "2. login"],
                "expected_result": "kirildi", "test_type": "positive", "priority": "High",
                "severity": "Critical", "tags": ["auth"], "requirement_ids": ["REQ-1"],
            },
            {
                "id": "TC-002", "title": "Noto'g'ri parol", "description": "d",
                "preconditions": "p", "steps": ["1. ochish", "2. xato parol"],
                "expected_result": "xato xabari", "test_type": "negative", "priority": "High",
                "severity": "Major", "tags": ["auth"], "requirement_ids": ["REQ-2"],
            },
        ]
    },
    ensure_ascii=False,
)

AGENT3_JSON = json.dumps(
    {
        "test_scenarios": [
            {
                "scenario_title": "Login flow",
                "screen_or_flow": "Login page",
                "requirement_ids": ["REQ-1", "REQ-2"],
                "test_cases": json.loads(AGENT2_JSON)["test_cases"],
            }
        ],
        "audit_findings": [
            {
                "type": "grouped_same_flow",
                "requirement_ids": ["REQ-1", "REQ-2"],
                "reason": "Login testlari bitta flow ichida group qilindi.",
            }
        ],
    },
    ensure_ascii=False,
)

EMPTY_AGENT2_JSON = json.dumps({"test_cases": []}, ensure_ascii=False)


def _make_service(agent_outputs, task_details=None):
    from services.generators.testcase_generator import TestCaseGeneratorService

    service = TestCaseGeneratorService()
    mock_jira = MagicMock()
    mock_jira.get_task_details.return_value = task_details or {
        "summary": "Login", "type": "Story", "priority": "High",
        "description": LONG_TZ, "comments": [],
    }
    service._jira_client = mock_jira
    service._github_client = MagicMock()

    mock_agent = MagicMock()
    mock_agent.analyze.side_effect = list(agent_outputs)
    mock_agent.last_model_used = "gemini-2.5-flash"
    mock_agent.model_name = "gemini-2.5-flash"
    service._agent_gemini = mock_agent
    return service, mock_agent


def test_multi_agent_success_and_coverage():
    service, mock_agent = _make_service([AGENT1_JSON, AGENT2_JSON, AGENT3_JSON])
    result = service.generate_test_cases("DEV-1", test_types=["positive", "negative"])

    assert result.success is True
    assert len(result.test_cases) == 2
    # Agent1 + Agent2 + Agent3 = 3 ta Gemini chaqiruvi
    assert mock_agent.analyze.call_count == 3
    assert len(result.requirements) == 2
    assert result.requirement_coverage["total_requirements"] == 2
    assert result.requirement_coverage["covered_count"] == 2
    assert result.requirement_coverage["uncovered_ids"] == []
    assert len(result.test_scenarios) == 1
    assert result.audit_findings
    assert result.test_cases[0].requirement_ids == ["REQ-1"]
    # PR endi ishlatilmaydi
    assert result.pr_count == 0
    assert result.pr_details == []


def test_uncovered_requirement_warns():
    agent2 = json.dumps(
        {
            "test_cases": [
                {
                    "id": "TC-001", "title": "t", "description": "d", "preconditions": "p",
                    "steps": ["s"], "expected_result": "r", "test_type": "positive",
                    "priority": "High", "severity": "Major", "tags": [], "requirement_ids": ["REQ-1"],
                }
            ]
        },
        ensure_ascii=False,
    )
    agent3 = json.dumps(
        {
            "test_scenarios": [
                {
                    "scenario_title": "Partial login flow",
                    "screen_or_flow": "Login page",
                    "requirement_ids": ["REQ-1"],
                    "test_cases": json.loads(agent2)["test_cases"],
                }
            ],
            "audit_findings": [],
        },
        ensure_ascii=False,
    )
    service, _ = _make_service([AGENT1_JSON, agent2, EMPTY_AGENT2_JSON, agent3])
    result = service.generate_test_cases("DEV-1")

    assert result.success is True
    assert result.requirement_coverage["uncovered_ids"] == ["REQ-2"]
    assert any("REQ-2" in w for w in result.warnings)


def test_agent1_failure_no_monolith_fallback():
    # Gemini barcha kalit/model bilan yiqildi → RuntimeError
    service, _ = _make_service([RuntimeError("barcha kalitlar muzlatildi")])

    result = service.generate_test_cases("DEV-1")

    assert result.success is False
    assert result.status_banner is not None  # xato banner ko'rsatiladi
    assert result.test_cases == []
    # Eski monolit (single-agent) kod butunlay olib tashlangan
    assert not hasattr(service, "_create_test_case_prompt")
    assert not hasattr(service, "_generate_with_ai")


def test_agent1_empty_requirements_errors():
    empty = json.dumps({"requirements": []})
    service, _ = _make_service([empty])
    result = service.generate_test_cases("DEV-1")
    assert result.success is False


def test_build_agent1_input_excludes_comments_and_adds_figma(monkeypatch):
    from services.generators import testcase_generator as tg

    service = tg.TestCaseGeneratorService()
    task_details = {
        "summary": "s", "type": "Task", "priority": "Low", "description": LONG_TZ,
        "comments": [
            {"author": "dev", "body": "Foydalanuvchi qo'shimcha talabni aytdi"},
            {"author": "bot", "body": "[AI_S1] AI yozgan izoh"},
        ],
    }
    monkeypatch.setattr(tg, "build_figma_access_status", lambda **kwargs: {"has_usable_data": True})
    monkeypatch.setattr(
        tg, "extract_figma_requirement_candidates",
        lambda figma_data: (["Figma ekrandagi talab matni"], [], []),
    )

    inp = service._build_agent1_input(task_details, {"summaries": [{"summary": "x"}]})

    assert inp["tz"] == LONG_TZ
    # QAT'IY QOIDA: Agent1 ga comment berilmaydi
    assert inp["comments"] == []
    assert inp["figma"] == ["Figma ekrandagi talab matni"]


def test_finalize_dedup_and_renumber():
    from services.generators.testcase_generator import TestCase, TestCaseGeneratorService

    service = TestCaseGeneratorService()
    tcs = [
        TestCase(id="X", title="Same", description="", preconditions="", steps=["a", "b"],
                 expected_result="", test_type="positive", priority="High", severity="Major",
                 tags=[], requirement_ids=["REQ-1"]),
        TestCase(id="Y", title="Same", description="", preconditions="", steps=["a", "b"],
                 expected_result="", test_type="positive", priority="High", severity="Major",
                 tags=[], requirement_ids=["REQ-1"]),  # takror
        TestCase(id="Z", title="Other", description="", preconditions="", steps=["c"],
                 expected_result="", test_type="negative", priority="Low", severity="Minor",
                 tags=[], requirement_ids=["REQ-2"]),
    ]
    unique, coverage = service._finalize_testcases(tcs, [{"id": "REQ-1"}, {"id": "REQ-2"}])

    assert len(unique) == 2
    assert [tc.id for tc in unique] == ["TC-001", "TC-002"]
    assert coverage["covered_count"] == 2
    assert coverage["uncovered_ids"] == []


def test_enforce_max_three_per_requirement():
    from services.generators.testcase_generator import (
        MAX_TC_PER_REQ,
        TestCase,
        TestCaseGeneratorService,
    )

    service = TestCaseGeneratorService()

    def _tc(i, reqs):
        return TestCase(id=f"X{i}", title=f"t{i}", description="", preconditions="",
                        steps=[f"s{i}"], expected_result="", test_type="positive",
                        priority="Low", severity="Minor", tags=[], requirement_ids=reqs)

    # REQ-1 ga 5 ta (ortiqcha), REQ-2 ga 1 ta (chegarada)
    tcs = [_tc(i, ["REQ-1"]) for i in range(5)] + [_tc(99, ["REQ-2"])]
    kept = service._enforce_max_per_requirement(tcs, [{"id": "REQ-1"}, {"id": "REQ-2"}])

    req1 = [t for t in kept if "REQ-1" in t.requirement_ids]
    req2 = [t for t in kept if "REQ-2" in t.requirement_ids]
    assert len(req1) == MAX_TC_PER_REQ  # 5 → 3
    assert len(req2) == 1  # min=1 buzilmaydi
