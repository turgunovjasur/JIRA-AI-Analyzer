from datetime import datetime

import pytest

from utils.database.checker_run_db import create_checker_run_record, save_checker_run_final_result
from utils.database.checker_run_repository import (
    build_checker_run_snapshot,
    ensure_checker_run_tables,
    get_checker_run,
    seed_checker_agent_runs,
)
from utils.database.runtime import connect_processing_db


def _sample_agents():
    return [
        {
            "agent_key": "agent1_scope_builder",
            "agent_label": "Agent1 Scope Builder",
            "agent_order": 1,
            "state": "pending",
            "primary_model": "gemini-2.5-pro",
            "fallback_model": "gemini-2.5-flash",
        },
        {
            "agent_key": "agent2_verifier",
            "agent_label": "Agent2 Verifier",
            "agent_order": 2,
            "state": "pending",
            "primary_model": "gemini-2.5-pro",
            "fallback_model": "gemini-2.5-flash",
        },
        {
            "agent_key": "agent3_arbiter",
            "agent_label": "Agent3 Arbiter",
            "agent_order": 3,
            "state": "pending",
            "primary_model": "gemini-2.5-pro",
            "fallback_model": "gemini-2.5-flash",
        },
    ]


@pytest.mark.no_db
def test_seed_checker_agent_runs_maps_used_fallback_and_attempts(monkeypatch):
    captured = {}

    class FakeConn:
        def __init__(self):
            self.commit_calls = 0

        def commit(self):
            self.commit_calls += 1

    def fake_execute(conn, query, params=None):
        captured["query"] = query
        captured["params"] = list(params or [])

        class DummyCursor:
            pass

        return DummyCursor()

    conn = FakeConn()
    monkeypatch.setattr(
        "utils.database.checker_run_repository._execute",
        fake_execute,
    )

    seed_checker_agent_runs(
        conn,
        run_id="tzpr-seed-test",
        agents=[_sample_agents()[0]],
        commit=False,
    )

    assert "used_fallback" in captured["query"]
    assert "attempts" in captured["query"]
    assert "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL" in captured["query"]
    assert captured["params"][8] is False
    assert captured["params"][9] == 0
    assert conn.commit_calls == 0


def _connect_for_test():
    conn = connect_processing_db(row_factory=True)
    ensure_checker_run_tables(conn)
    return conn


def _cleanup_run(run_id: str):
    conn = _connect_for_test()
    try:
        conn.execute("DELETE FROM checker_runs WHERE run_id = %s", [run_id])
        conn.commit()
    finally:
        conn.close()


def test_create_checker_run_record_persists_run_and_agents(monkeypatch):
    run_id = "tzpr-success-1"
    _cleanup_run(run_id)
    monkeypatch.setattr("utils.database.checker_run_db._connect", _connect_for_test)

    snapshot = create_checker_run_record(
        run_id=run_id,
        task_key="DEV-9001",
        company_id=7,
        user_id=77,
        source="manual",
        execution_mode="multi_agent",
        requested_output_profile="ui",
        request_payload={"task_key": "DEV-9001"},
        agents=_sample_agents(),
    )

    assert snapshot["run_id"] == run_id
    assert snapshot["task_key"] == "DEV-9001"
    assert snapshot["run_state"] == "queued"
    assert len(snapshot["agent_runs"]) == 3
    assert all(item["state"] == "pending" for item in snapshot["agent_runs"])
    assert len(snapshot["run_events"]) == 1

    verify_conn = _connect_for_test()
    try:
        persisted = build_checker_run_snapshot(verify_conn, run_id)
        assert persisted is not None
        assert len(persisted["agent_runs"]) == 3
    finally:
        verify_conn.close()
        _cleanup_run(run_id)


def test_create_checker_run_record_rolls_back_when_agent_seed_fails(monkeypatch):
    run_id = "tzpr-rollback-1"
    _cleanup_run(run_id)

    def explode_seed(*args, **kwargs):
        raise RuntimeError("seed failed")

    monkeypatch.setattr("utils.database.checker_run_db._connect", _connect_for_test)
    monkeypatch.setattr("utils.database.checker_run_db.repo_seed_checker_agent_runs", explode_seed)

    with pytest.raises(RuntimeError, match="seed failed"):
        create_checker_run_record(
            run_id=run_id,
            task_key="DEV-9002",
            company_id=8,
            user_id=88,
            source="manual",
            execution_mode="multi_agent",
            requested_output_profile="ui",
            request_payload={"task_key": "DEV-9002"},
            agents=_sample_agents(),
        )

    verify_conn = _connect_for_test()
    try:
        assert get_checker_run(verify_conn, run_id) is None
    finally:
        verify_conn.close()


def test_save_checker_run_final_result_serializes_datetime_values(monkeypatch):
    run_id = "tzpr-datetime-1"
    _cleanup_run(run_id)
    monkeypatch.setattr("utils.database.checker_run_db._connect", _connect_for_test)

    create_checker_run_record(
        run_id=run_id,
        task_key="DEV-9003",
        company_id=9,
        user_id=99,
        source="manual",
        execution_mode="multi_agent",
        requested_output_profile="ui",
        request_payload={"task_key": "DEV-9003"},
        agents=_sample_agents(),
    )

    snapshot = save_checker_run_final_result(
        run_id,
        run_state="completed",
        final_result={
            "success": True,
            "task_key": "DEV-9003",
            "captured_at": datetime(2026, 5, 13, 11, 40, 0),
            "nested": {
                "when": datetime(2026, 5, 13, 11, 41, 0),
            },
        },
        error_message=None,
    )

    assert snapshot is not None
    assert snapshot["run_state"] == "completed"
    assert snapshot["final_result"]["captured_at"] == "2026-05-13T11:40:00"
    assert snapshot["final_result"]["nested"]["when"] == "2026-05-13T11:41:00"
    _cleanup_run(run_id)
