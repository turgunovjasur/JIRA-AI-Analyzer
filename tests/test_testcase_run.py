"""Testcase run driver testlari (DB talab qilmaydi — DB qatlami mock qilinadi)."""
import pytest

pytestmark = pytest.mark.no_db

from services.generators import testcase_run as tr


class _FakeResult:
    def __init__(self, success, error_message=""):
        self.success = success
        self.error_message = error_message


def _patch_db(monkeypatch):
    calls = {"run_updates": [], "agent_updates": [], "events": [], "final": []}
    monkeypatch.setattr(tr, "update_analysis_run_record", lambda run_id, **f: calls["run_updates"].append(f) or {})
    monkeypatch.setattr(tr, "update_analysis_agent_record", lambda run_id, ak, **f: calls["agent_updates"].append((ak, f)) or {})
    monkeypatch.setattr(tr, "append_analysis_run_event", lambda **f: calls["events"].append(f) or {})
    monkeypatch.setattr(
        tr, "save_analysis_run_final_result",
        lambda run_id, **f: (calls["final"].append(f) or {"run_id": run_id, **f}),
    )
    return calls


def _patch_service(monkeypatch, result, status_msgs=()):
    class FakeService:
        def __init__(self, company_id=None, user_id=None):
            pass

        def generate_test_cases(self, task_key, test_types=None, custom_context="", status_callback=None):
            for st, msg in status_msgs:
                if status_callback:
                    status_callback(st, msg)
            return result

    monkeypatch.setattr("services.generators.testcase_generator.TestCaseGeneratorService", FakeService)


def test_create_testcase_run_builds_record(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        tr, "create_analysis_run_record",
        lambda **kw: (captured.update(kw) or {"run_id": kw["run_id"]}),
    )

    snap = tr.create_testcase_run(
        task_key="DEV-1", company_id=5, user_id=55,
        test_types=["positive"], custom_context="ctx",
    )

    assert snap["run_id"].startswith("tc-")
    assert captured["module_key"] == "testcase_generator"
    assert captured["task_key"] == "DEV-1"
    assert captured["request_payload"]["test_types"] == ["positive"]
    assert captured["request_payload"]["custom_context"] == "ctx"
    assert [a["agent_key"] for a in captured["agents"]] == ["agent1_requirements", "agent2_testcase"]


def test_execute_success_marks_completed(monkeypatch):
    calls = _patch_db(monkeypatch)
    monkeypatch.setattr(tr, "get_analysis_run_snapshot", lambda run_id: {
        "run_id": run_id, "request_payload": {"test_types": ["positive"], "custom_context": ""},
        "company_id": 5, "user_id": 55, "task_key": "DEV-1",
    })
    _patch_service(monkeypatch, _FakeResult(True), status_msgs=[
        ("progress", "Talablar ajratilmoqda (Agent1)..."),
        ("progress", "AI test case'lar yozmoqda (Agent2)..."),
    ])

    tr.execute_testcase_run("tc-x")

    # running → completed
    assert any(f.get("run_state") == "running" for f in calls["run_updates"])
    assert calls["final"][-1]["run_state"] == "completed"
    # ikkala agent ham completed bo'ldi
    completed = [ak for ak, f in calls["agent_updates"] if f.get("state") == "completed"]
    assert "agent1_requirements" in completed and "agent2_testcase" in completed
    # agentlar running ga ham o'tdi (progress matnlaridan)
    running = [ak for ak, f in calls["agent_updates"] if f.get("state") == "running"]
    assert "agent1_requirements" in running and "agent2_testcase" in running


def test_execute_failure_marks_error(monkeypatch):
    calls = _patch_db(monkeypatch)
    monkeypatch.setattr(tr, "get_analysis_run_snapshot", lambda run_id: {
        "run_id": run_id, "request_payload": {}, "company_id": None, "user_id": 1, "task_key": "DEV-2",
    })
    _patch_service(monkeypatch, _FakeResult(False, "Agent1 ishlamadi"), status_msgs=[
        ("progress", "Talablar ajratilmoqda (Agent1)..."),
    ])

    tr.execute_testcase_run("tc-y")

    assert calls["final"][-1]["run_state"] == "error"
    assert "Agent1 ishlamadi" in (calls["final"][-1]["error_message"] or "")
    # aktiv agent (agent1) failed bo'ldi
    failed = [ak for ak, f in calls["agent_updates"] if f.get("state") == "failed"]
    assert "agent1_requirements" in failed


def test_execute_missing_run_raises(monkeypatch):
    monkeypatch.setattr(tr, "get_analysis_run_snapshot", lambda run_id: None)
    with pytest.raises(RuntimeError, match="topilmadi"):
        tr.execute_testcase_run("tc-missing")
