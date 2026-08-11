from __future__ import annotations

import importlib

import pytest

from utils.jira.jira_comment_writer import JiraCommentWriter, JiraCommentWriteResult

pytestmark = pytest.mark.no_db


class FakeResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text


class FakeSession:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.requests: list[tuple[str, dict]] = []

    def post(self, url: str, json: dict):
        self.requests.append((url, json))
        return self.response


class FakeWriter:
    def __init__(self, results: list[JiraCommentWriteResult] | None = None):
        self.results = list(results or [])
        self.adf_documents: list[dict] = []
        self.text_comments: list[str] = []

    def add_comment_adf_result(self, task_key: str, document: dict):
        self.adf_documents.append(document)
        if self.results:
            return self.results.pop(0)
        return JiraCommentWriteResult(success=True, status_code=201)

    def add_comment(self, task_key: str, text: str) -> bool:
        self.text_comments.append(text)
        return True


def _paragraph(text: str) -> dict:
    return {
        "type": "paragraph",
        "content": [{"type": "text", "text": text}],
    }


def _doc(*nodes: dict) -> dict:
    return {"version": 1, "type": "doc", "content": list(nodes)}


def _heading(text: str) -> dict:
    return {
        "type": "heading",
        "attrs": {"level": 1},
        "content": [{"type": "text", "text": text}],
    }


def _expand(title: str, text: str) -> dict:
    return {
        "type": "expand",
        "attrs": {"title": title},
        "content": [_paragraph(text)],
    }


def _publisher_module():
    try:
        return importlib.import_module("utils.jira.jira_comment_publisher")
    except ModuleNotFoundError:
        pytest.fail("utils.jira.jira_comment_publisher hali yaratilmagan")


def _text_nodes(value) -> list[str]:
    if isinstance(value, dict):
        values = [str(value["text"])] if "text" in value else []
        for key, child in value.items():
            if key != "text":
                values.extend(_text_nodes(child))
        return values
    if isinstance(value, list):
        values: list[str] = []
        for child in value:
            values.extend(_text_nodes(child))
        return values
    return []


def test_adf_result_preserves_content_limit_response():
    writer = JiraCommentWriter.__new__(JiraCommentWriter)
    writer.server = "https://jira.example.com"
    writer._session = FakeSession(
        FakeResponse(400, '{"errorMessages":["CONTENT_LIMIT_EXCEEDED"]}')
    )

    result = writer.add_comment_adf_result("DEV-1", _doc(_paragraph("x")))

    assert result.success is False
    assert result.status_code == 400
    assert result.content_limit_exceeded is True


def test_split_text_lossless_preserves_unicode_and_delimiters():
    publisher = _publisher_module()
    source = "Birinchi gap.\nIkkinchi Ўзбекча gap va yakun. " * 5

    chunks = publisher.split_text_lossless(source, max_chars=35)

    assert len(chunks) > 1
    assert "".join(chunks) == source
    assert all(0 < len(chunk) <= 35 for chunk in chunks)


def test_split_adf_preserves_large_expand_content_with_valid_parts():
    publisher = _publisher_module()
    first = "FIRST|" + ("a" * 1600) + "|FIRST-END"
    second = "SECOND|" + ("b" * 1600) + "|SECOND-END"
    source = _doc(
        _paragraph("[AI_S1]"),
        _heading("Checker — 33%"),
        _expand("REQ-1", first),
        _expand("REQ-2", second),
    )

    parts = publisher.split_adf_document(
        source,
        max_chars=900,
        marker="[AI_S1]",
        task_key="DEV-8843",
    )

    assert len(parts) > 1
    assert all(part["version"] == 1 and part["type"] == "doc" for part in parts)
    assert all(publisher.adf_size(part) <= 900 for part in parts)

    texts = _text_nodes(parts)
    business_text = "".join(
        text
        for text in texts
        if text not in {"[AI_S1]", "Checker — 33%"}
        and not text.startswith("Task: DEV-8843 · Qism:")
    )
    assert business_text == first + second


def test_publish_long_adf_writes_hint_then_numbered_parts():
    publisher_module = _publisher_module()
    writer = FakeWriter()
    publisher = publisher_module.JiraCommentPublisher(writer, target_chars=500)
    source = _doc(
        _paragraph("[AI_S1]"),
        _heading("Checker — 33%"),
        _expand("REQ-1", "Talab tafsiloti. " * 180),
    )

    result = publisher.publish_adf(
        "DEV-8843",
        source,
        marker="[AI_S1]",
        service_name="Servis-1",
    )

    assert result.success is True
    assert result.split is True
    assert result.part_count >= 2
    assert len(writer.adf_documents) == result.part_count + 1
    assert "bo'lib yuboriladi" in "".join(_text_nodes(writer.adf_documents[0]))
    assert "Qism: 1/" in "".join(_text_nodes(writer.adf_documents[1]))


def test_publish_short_adf_writes_once_without_hint():
    publisher_module = _publisher_module()
    writer = FakeWriter()
    publisher = publisher_module.JiraCommentPublisher(writer, target_chars=1000)
    source = _doc(_paragraph("[AI_S1]"), _paragraph("Qisqa natija"))

    result = publisher.publish_adf(
        "DEV-1",
        source,
        marker="[AI_S1]",
        service_name="Servis-1",
    )

    assert result.success is True
    assert result.split is False
    assert result.part_count == 1
    assert writer.adf_documents == [source]


def test_publish_adf_retries_content_limit_as_smaller_parts():
    publisher_module = _publisher_module()
    writer = FakeWriter([
        JiraCommentWriteResult(
            success=False,
            status_code=400,
            response_text='{"errorMessages":["CONTENT_LIMIT_EXCEEDED"]}',
        ),
    ])
    publisher = publisher_module.JiraCommentPublisher(writer, target_chars=1200)
    source = _doc(
        _paragraph("[AI_S1]"),
        _heading("Checker — 33%"),
        _expand("REQ-1", "JIRA ichki hisobi. " * 35),
    )
    assert publisher_module.adf_size(source) <= 1200

    result = publisher.publish_adf(
        "DEV-1",
        source,
        marker="[AI_S1]",
        service_name="Servis-1",
    )

    assert result.success is True
    assert result.split is True
    assert len(writer.adf_documents) == result.part_count + 2


def test_publish_adf_returns_failure_when_a_part_is_rejected():
    publisher_module = _publisher_module()
    writer = FakeWriter([
        JiraCommentWriteResult(success=True, status_code=201),
        JiraCommentWriteResult(success=False, status_code=503, response_text="unavailable"),
    ])
    publisher = publisher_module.JiraCommentPublisher(writer, target_chars=500)
    source = _doc(
        _paragraph("[AI_S2]"),
        _heading("Test cases"),
        _expand("TC-1", "Qadam. " * 200),
    )

    result = publisher.publish_adf(
        "DEV-1",
        source,
        marker="[AI_S2]",
        service_name="Servis-2",
    )

    assert result.success is False
    assert result.split is True
    assert result.part_count >= 2
    assert result.error == "unavailable"


def test_publish_long_text_writes_hint_and_lossless_numbered_parts():
    publisher_module = _publisher_module()
    writer = FakeWriter()
    publisher = publisher_module.JiraCommentPublisher(writer, target_chars=180)
    source = "Birinchi qator.\nIkkinchi Ўзбекча qator. " * 20

    result = publisher.publish_text(
        "DEV-1",
        source,
        marker="[AI_S2]",
        service_name="Servis-2",
    )

    assert result.success is True
    assert result.split is True
    assert result.part_count >= 2
    assert "bo'lib yuboriladi" in writer.text_comments[0]
    bodies = [comment.split("\n\n", 1)[1] for comment in writer.text_comments[1:]]
    assert "".join(bodies) == source
