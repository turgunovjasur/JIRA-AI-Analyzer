import pytest

from utils.ai.gemini_json import parse_gemini_json


pytestmark = pytest.mark.no_db


def test_local_json_repair_fixes_common_model_format_errors():
    result = parse_gemini_json(
        """
        {
          "requirements": [
            {
              "id": "REQ-1"
              "text": "Birinchi talab",
              "source": "tz",
            }
            {
              "id": "REQ-2",
              "text": "Ikkinchi talab",
              "source": "tz"
            },
          ]
        }
        """
    )

    assert result.ok is True
    parsed = result.data
    assert [item["id"] for item in parsed["requirements"]] == ["REQ-1", "REQ-2"]


def test_parse_gemini_json_repairs_truncated_object():
    result = parse_gemini_json(
        '{"id": "REQ-21", "status": "completed", "evidence": "A new preference'
    )

    assert result.ok is True
    assert result.used_repair is True
    assert result.repair_type == "balanced_truncated_json"
    assert result.data["id"] == "REQ-21"
    assert result.data["status"] == "completed"
