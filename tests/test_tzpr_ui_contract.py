import pytest
from types import SimpleNamespace

from core.tz_helper import TZHelper
from services.checkers.tzpr_models import (
    TZPRAnalysisOverview,
    TZPRAnalysisResult,
    TZPRAnalysisSection,
)
from services.checkers.tz_pr_checker import TZPRService
from utils.jira.jira_adf_formatter import JiraADFFormatter


@pytest.fixture(autouse=True)
def isolate_test_databases():
    """Bu fayldagi testlar DB ga muhtoj emas."""
    yield


@pytest.fixture(autouse=True)
def ensure_db():
    """Global DB fixture'ni no-op bilan override qilamiz."""
    yield


def test_format_tz_with_comments_filters_previous_ai_comments():
    task_details = {
        "summary": "Task summary",
        "description": "Task description",
        "type": "Story",
        "priority": "High",
        "status": "Ready to Test",
        "assignee": "Dev",
        "reporter": "QA",
        "created": "2026-05-11",
        "story_points": 3,
        "comments": [
            {"author": "Dev", "body": "Oddiy developer comment", "created": "2026-05-10"},
            {"author": "AI", "body": "[AI_S1]\nEski checker xulosasi", "created": "2026-05-10"},
            {"author": "AI", "body": "[AI_S2]\nEski testcase xulosasi", "created": "2026-05-10"},
            {"author": "Dev", "body": "Yangi izoh", "created": "2026-05-11"},
        ],
    }

    tz_content, comment_analysis = TZHelper.format_tz_with_comments(
        task_details,
        exclude_ai_comments=True,
    )

    assert "[AI_S1]" not in tz_content
    assert "[AI_S2]" not in tz_content
    assert "Oddiy developer comment" in tz_content
    assert "Yangi izoh" in tz_content
    assert comment_analysis["total_comments"] == 2
    assert comment_analysis["filtered_out_ai_comments"] == 2


def test_analyze_comments_ignores_ai_comments_by_default():
    analysis = TZHelper.analyze_comments(
        "desc",
        [
            {"author": "AI", "body": "[AI_S1]\nchanged", "created": "2026-05-10"},
            {"author": "Dev", "body": "Yangi talab qoshildi", "created": "2026-05-11"},
        ],
    )

    assert analysis["total_comments"] == 1
    assert analysis["filtered_out_ai_comments"] == 1
    assert analysis["has_changes"] is True


def test_analyze_comments_ignores_auto_generated_reports_without_marker():
    analysis = TZHelper.analyze_comments(
        "desc",
        [
            {
                "author": "QA Bot",
                "body": (
                    "h2. 🎯 Avtomatik TZ-PR Moslik Tekshiruvi\n"
                    "_🤖 Bu komment AI tomonidan avtomatik yaratilgan. "
                    "Savollar bo'lsa QA Team ga murojaat qiling._"
                ),
                "created": "2026-05-10",
            },
            {
                "author": "QA Bot",
                "body": (
                    "h2. 🧪 Avtomatik Test Case'lar\n"
                    "_🤖 Test case'lar AI (Gemini) tomonidan avtomatik yaratilgan._"
                ),
                "created": "2026-05-10",
            },
            {"author": "Dev", "body": "Yangi talab qoshildi", "created": "2026-05-11"},
        ],
    )

    assert analysis["total_comments"] == 1
    assert analysis["filtered_out_ai_comments"] == 2
    assert analysis["change_count"] == 1
    assert analysis["important_comments"][0]["author"] == "Dev"






def test_run_info_exposes_ai_model_and_fallback_metadata():
    service = TZPRService()

    run_info = service._build_run_info(
        effective_settings={
            "requested_output_profile": "ui",
            "read_comments_enabled": True,
            "max_comments_to_read": 0,
            "effective_use_smart_patch": True,
            "ai_data_section_order": ["tz", "comments", "code"],
        },
        files_analyzed=4,
        total_files_changed=4,
        prompt_size_chars=12345,
        ai_retry_count=1,
        ai_model="gemini-2.5-flash",
        ai_primary_model="gemini-2.5-pro",
        ai_fallback_model="gemini-2.5-flash",
        ai_used_fallback=True,
    )

    assert run_info.ai_model == "gemini-2.5-flash"
    assert run_info.ai_primary_model == "gemini-2.5-pro"
    assert run_info.ai_fallback_model == "gemini-2.5-flash"
    assert run_info.ai_used_fallback is True




def test_effective_settings_expose_render_and_analysis_controls():
    service = TZPRService()
    service._get_settings = lambda: SimpleNamespace(
        visible_sections=["failed", "figma"],
        read_comments_enabled=False,
        max_comments_to_read=7,
        default_use_smart_patch=False,
        ai_data_section_order=["tz", "figma", "code"],
        show_contradictory_comments=True,
        agent2_parallelism=7,
    )
    effective = service._build_effective_settings(
        requested_output_profile="ui",
        effective_use_smart_patch=True,
    )

    assert effective["visible_sections"] == ["failed", "figma"]
    assert effective["read_comments_enabled"] is False
    assert effective["max_comments_to_read"] == 7
    assert effective["default_use_smart_patch"] is False
    assert effective["effective_use_smart_patch"] is True
    assert effective["ai_data_section_order"] == ["tz", "figma", "code"]
    assert effective["show_contradictory_comments"] is True
    assert effective["agent2_parallelism"] == 7
    assert effective["agent1_rules"]["figma_scope_enabled"] is True
    assert effective["agent1_rules"]["coverage_threshold"] == 1.0
    assert effective["requested_output_profile"] == "ui"


def test_agent1_figma_scope_follows_ai_data_section_order():
    service = TZPRService()
    service._get_settings = lambda: SimpleNamespace(
        visible_sections=["failed"],
        read_comments_enabled=True,
        max_comments_to_read=0,
        default_use_smart_patch=True,
        ai_data_section_order=["tz", "comments", "code"],
        show_contradictory_comments=False,
    )

    effective = service._build_effective_settings()

    assert effective["agent1_rules"]["figma_scope_enabled"] is False


def test_canonical_sections_are_profile_agnostic():
    service = TZPRService()

    assert service._get_canonical_analysis_sections() == [
        "summary",
        "completed",
        "partial",
        "failed",
        "issues",
        "figma",
    ]


def test_task_info_builder_exposes_qa_identity_fields():
    service = TZPRService()
    task_info = service._build_task_info(
        {
            "key": "DEV-77",
            "summary": "Checker QA paneli",
            "type": "DEV-TECHTASK",
            "status": "READY TO TEST",
            "assignee": "Ali",
            "reporter": "QA",
            "priority": "High",
            "story_points": 5,
            "created": "2026-05-12",
            "resolved": "",
            "labels": ["checker"],
            "components": ["UI"],
        }
    )

    assert task_info.key == "DEV-77"
    assert task_info.assignee == "Ali"
    assert task_info.issue_type == "DEV-TECHTASK"
    assert task_info.priority == "High"
    assert task_info.story_points == 5.0


def test_qa_recommendation_prefers_return_for_failed_requirements():
    service = TZPRService()
    recommendation = service._build_qa_recommendation(
        TZPRAnalysisOverview(
            verdict="fail",
            verdict_label="Need Work",
            verdict_reason="2 ta bajarilmagan talab bor",
            section_counts={"failed": 2, "partial": 0, "issues": 0},
            missing_figma_access=False,
        ),
        compliance_score=58,
    )

    assert recommendation.action == "return"
    assert "bajarilmagan talab" in recommendation.reason.lower()


def test_requirement_matrix_builds_requirement_evidence_rows():
    service = TZPRService()
    matrix = service._build_requirement_matrix(
        analysis_sections=[
            TZPRAnalysisSection(
                key="failed",
                title="❌ BAJARILMAGAN TALABLAR",
                items=[
                    "Talab: Mobile empty state bo'lishi kerak. | Evidence: UI'da bu state ko'rinmadi. | File: frontend/src/components/tzpr-checker.tsx | Figma: Mobile flowda placeholder card bor.",
                ],
                item_count=1,
            )
        ],
        task_details={
            "summary": "Checker mobile state audit",
            "description": "Mobile ekranlarda checker empty state ko'rinishi kerak.",
        },
        pr_details=[
            {
                "number": 42,
                "title": "checker: mobile qa polish",
                "url": "https://github.com/example/repo/pull/42",
                "files": [
                    {
                        "filename": "frontend/src/components/tzpr-checker.tsx",
                        "blob_url": "https://github.com/example/repo/blob/main/frontend/src/components/tzpr-checker.tsx",
                        "status": "modified",
                        "additions": 12,
                        "deletions": 3,
                        "patch": "@@\n+const mobile = true;\n+renderEmptyState();",
                    },
                    {"filename": "frontend/src/app/globals.css"},
                ],
            }
        ],
        figma_data={
            "summaries": [
                {
                    "name": "Checker Mobile Flow",
                    "summary": "Mobile empty state card dizaynda ko'rsatilgan.",
                    "url": "https://www.figma.com/file/example?node-id=812-4",
                }
            ]
        },
        comment_analysis={
            "important_comments": [
                {
                    "author": "QA",
                    "preview": "Mobile empty state product requirement sifatida qolgan.",
                }
            ]
        },
    )

    assert len(matrix) == 1
    row = matrix[0]
    assert row.status == "failed"
    assert row.status_label == "Bajarilmagan"
    assert "Mobile empty state" in row.requirement
    assert row.code_files == ["frontend/src/components/tzpr-checker.tsx"]
    assert row.code_refs[0].blob_url == "https://github.com/example/repo/blob/main/frontend/src/components/tzpr-checker.tsx"
    assert row.code_refs[0].pr_number == 42
    assert row.code_refs[0].change_type == "modified"
    assert "renderEmptyState" in row.code_refs[0].patch_preview
    assert "Mobile flow" in row.figma_relation
    assert row.figma_sources[0].name == "Checker Mobile Flow"
    assert row.figma_sources[0].node_id == "812-4"
    assert "empty state card" in row.figma_sources[0].summary
    assert any(item.source == "comment" for item in row.evidence)
    assert any(item.source == "pr" for item in row.evidence)




def test_comment_intelligence_detects_deferred_scope_and_dev_objection():
    service = TZPRService()
    comment_intelligence = service._build_comment_intelligence(
        comment_analysis={
            "has_changes": True,
            "summary": "⚠️ 1 ta comment'da o'zgarish topildi!",
            "change_count": 1,
            "total_comments": 3,
            "filtered_out_ai_comments": 1,
            "important_comments": [
                {
                    "author": "QA",
                    "created": "2026-05-12",
                    "preview": "Button text o'zgardi",
                    "full_text": "Button text o'zgardi",
                }
            ],
        },
        comment_separated={
            "dev_before": [
                {
                    "author": "Dev",
                    "created": "2026-05-12",
                    "body": "Bu linklarni keyingi sprintda qilamiz.",
                }
            ],
            "dev_after": [
                {
                    "author": "Dev",
                    "created": "2026-05-13",
                    "body": "Oldingi return bo'yicha menimcha bu joy aslida scope ichida emas.",
                }
            ],
        },
        is_recheck=True,
    )

    assert comment_intelligence.has_scope_changes is True
    assert comment_intelligence.deferred_scope_detected is True
    assert comment_intelligence.has_dev_objections is True
    assert comment_intelligence.objection_count == 1
    assert len(comment_intelligence.deferred_scope_comments) == 1


def test_workflow_info_reads_task_processing_context(monkeypatch):
    service = TZPRService()
    service._get_settings = lambda: SimpleNamespace(
        return_threshold=75,
        auto_return_enabled=True,
    )

    import utils.database.task_db as task_db

    monkeypatch.setattr(
        task_db,
        "get_task",
        lambda task_key: {
            "task_status": "returned",
            "service1_status": "done",
            "service2_status": "pending",
            "compliance_score": 68,
            "return_reason": "WARN_LOW_SCORE",
            "blocked_at": "",
            "blocked_retry_at": "",
            "updated_at": "2026-05-12T11:05:00",
        },
    )

    workflow = service._build_workflow_info(
        task_key="DEV-88",
        compliance_score=68,
        is_recheck=True,
    )

    assert workflow.available is True
    assert workflow.task_status == "returned"
    assert workflow.service1_status == "done"
    assert workflow.return_reason == "WARN_LOW_SCORE"
    assert workflow.auto_return_enabled is True
    assert workflow.return_threshold == 75
    assert workflow.is_recheck is True


def test_jira_formatter_prefers_structured_sections_and_visible_filter():
    formatter = JiraADFFormatter()
    result = TZPRAnalysisResult(
        success=True,
        task_key="DEV-1",
        task_summary="Summary",
        pr_count=1,
        files_changed=2,
        total_additions=10,
        total_deletions=3,
        compliance_score=66,
        ai_analysis="RAW TEXT WITHOUT PARSEABLE HEADINGS",
        analysis_sections=[
            TZPRAnalysisSection(
                key="failed",
                title="❌ BAJARILMAGAN TALABLAR",
                items=["Mobil ekran ishlanmagan."],
                item_count=1,
            ),
            TZPRAnalysisSection(
                key="completed",
                title="✅ BAJARILGAN TALABLAR",
                items=["API endpoint tayyor."],
                item_count=1,
            ),
            TZPRAnalysisSection(
                key="skipped",
                title="⏭️ SKIP QILINGAN",
                items=["Dev izohi asosida boshqa repoda tekshiriladi."],
                item_count=1,
            ),
            TZPRAnalysisSection(
                key="partial",
                title="⚠️ QISMAN BAJARILGAN",
                items=["Legacy partial chiqmasligi kerak."],
                item_count=1,
            ),
        ],
    )

    default_adf_text = str(formatter.build_comment_document(result))
    default_simple_comment = formatter.build_simple_comment(result)
    adf_doc = formatter.build_comment_document(
        result,
        visible_sections=["failed"],
    )
    adf_text = str(adf_doc)
    simple_comment = formatter.build_simple_comment(
        result,
        visible_sections=["failed"],
    )

    assert "Dev izohi asosida boshqa repoda tekshiriladi." in default_adf_text
    assert "Dev izohi asosida boshqa repoda tekshiriladi." in default_simple_comment
    assert "Legacy partial chiqmasligi kerak." not in default_adf_text
    assert "Legacy partial chiqmasligi kerak." not in default_simple_comment
    assert "Mobil ekran ishlanmagan." in adf_text
    assert "API endpoint tayyor." not in adf_text
    assert "Dev izohi asosida boshqa repoda tekshiriladi." not in adf_text
    assert "Mobil ekran ishlanmagan." in simple_comment
    assert "API endpoint tayyor." not in simple_comment
    assert "Dev izohi asosida boshqa repoda tekshiriladi." not in simple_comment
    assert "RAW TEXT WITHOUT PARSEABLE HEADINGS" not in simple_comment


def test_jira_formatter_renders_each_requirement_as_nested_expand():
    formatter = JiraADFFormatter()
    result = TZPRAnalysisResult(
        success=True,
        task_key="DEV-1",
        task_summary="Summary",
        analysis_sections=[
            TZPRAnalysisSection(
                key="completed",
                title="✅ Bajarilgan talablar",
                items=[
                    "[REQ-1] Login validatsiyasi bajarilgan. | Evidence: LoginForm.tsx",
                    "[REQ-2] Submit loading holati qo'shilgan. | Evidence: Button disabled state",
                ],
                item_count=2,
            ),
            TZPRAnalysisSection(
                key="failed",
                title="❌ Bajarilmagan talablar",
                items=["[REQ-3] Export flow topilmadi. | Evidence: route yo'q"],
                item_count=1,
            ),
            TZPRAnalysisSection(
                key="skipped",
                title="⏭️ Skip qilingan talablar",
                items=["[REQ-4] Scope tashqarisida. | Evidence: dev izohi"],
                item_count=1,
            ),
            TZPRAnalysisSection(
                key="issues",
                title="🔍 Extra Scan",
                items=["[REQ-5] Potensial regression bor. | Evidence: shared helper o'zgargan"],
                item_count=1,
            ),
        ],
    )

    adf_doc = formatter.build_comment_document(result)

    def _heading_text(node):
        return "".join(c.get("text", "") for c in node.get("content", []))

    def _requirement_panels_under(section_title):
        content = adf_doc["content"]
        idx = next(
            i for i, node in enumerate(content)
            if node.get("type") == "heading" and _heading_text(node) == section_title
        )
        panels = []
        for node in content[idx + 1:]:
            # ADF qoidasi: bo'lim = heading, talablar = flat top-level expand
            # (expand ichida expand JIRA'da 400 beradi). Keyingi heading/rule'da to'xtaymiz.
            if node.get("type") in ("heading", "rule"):
                break
            if node.get("type") == "expand":
                panels.append(node)
        return panels

    completed_panels = _requirement_panels_under("✅ Bajarilgan talablar (2 ta)")
    assert [node["attrs"]["title"] for node in completed_panels] == [
        "✅ [REQ-1] Login validatsiyasi bajarilgan.",
        "✅ [REQ-2] Submit loading holati qo'shilgan.",
    ]
    assert "Login validatsiyasi bajarilgan" in str(completed_panels[0])
    assert "Submit loading holati qo'shilgan" in str(completed_panels[1])
    assert len(completed_panels[0]["content"]) == 2
    assert "Evidence: " in str(completed_panels[0]["content"][1])

    for section_title, requirement_title in [
        ("❌ Bajarilmagan talablar (1 ta)", "❌ [REQ-3] Export flow topilmadi."),
        ("⏭️ Skip qilingan talablar (1 ta)", "⏭️ [REQ-4] Scope tashqarisida."),
        ("🔍 Extra Scan (1 ta)", "🔍 [REQ-5] Potensial regression bor."),
    ]:
        panels = _requirement_panels_under(section_title)
        assert [node["attrs"]["title"] for node in panels] == [requirement_title]

    # Scoreboard: ball ostida talab verdiktlari bir qatorda ko'rinadi
    doc_text = str(adf_doc["content"])
    assert "2 bajarildi" in doc_text
    assert "1 bajarilmadi" in doc_text
