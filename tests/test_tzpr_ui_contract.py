import pytest

from core.tz_helper import TZHelper
from services.checkers.tz_pr_checker import TZPRService


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


def test_structured_analysis_builds_requirement_sections_and_fail_verdict():
    service = TZPRService()
    analysis_text = """
## 🧭 XULOSA
Asosiy requirementlar qisman bajarilgan.

## ✅ BAJARILGAN TALABLAR
- API endpoint yangilangan.
- Input validatsiya qo'shilgan.

## ❌ BAJARILMAGAN TALABLAR
- Mobil ekran holati yo'q.

## 🐛 POTENSIAL MUAMMOLAR
- Edge case uchun test topilmadi.

## 📊 MOSLIK BALI
**COMPLIANCE_SCORE: 74%**
""".strip()

    sections, overview = service._build_structured_analysis(
        analysis_text,
        compliance_score=74,
        output_profile="ui",
        figma_data=None,
    )

    section_map = {section.key: section for section in sections}

    assert overview.verdict == "fail"
    assert overview.verdict_label == "Need Work"
    assert "74%" in " ".join(overview.summary_lines)
    assert section_map["completed"].item_count == 2
    assert section_map["failed"].item_count == 1
    assert section_map["issues"].item_count == 1


def test_sanitize_ai_analysis_replaces_plain_figma_heading_without_duplicate():
    service = TZPRService()
    raw_analysis = """
## ❌ BAJARILMAGAN TALABLAR
- Bir talab yo'q.

## FIGMA DIZAYN MOSLIGI
Figma ma'lumotlari olinmadi, shu sabab xulosa yo'q.

## 📊 MOSLIK BALI
**COMPLIANCE_SCORE: 61%**
""".strip()

    sanitized = service._sanitize_ai_analysis_for_missing_figma(raw_analysis, figma_data=None)

    assert sanitized.count("FIGMA DIZAYN MOSLIGI") == 1
    assert "Figma token yoki ruxsat mavjud emas" in sanitized
    assert "COMPLIANCE_SCORE: 61%" in sanitized


def test_ui_profile_requests_full_section_set():
    service = TZPRService()

    assert service._get_visible_sections_for_profile("ui") == [
        "summary",
        "completed",
        "partial",
        "failed",
        "issues",
        "figma",
    ]
