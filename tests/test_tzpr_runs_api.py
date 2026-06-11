import pytest
from fastapi.testclient import TestClient

import services.api.tzpr_api as tzpr_api
from services.webhook.jira_webhook_handler import app


@pytest.fixture(autouse=True)
def isolate_test_databases():
    yield


@pytest.fixture(autouse=True)
def ensure_db():
    yield


def test_create_tzpr_run_endpoint_returns_snapshot(monkeypatch):
    snapshot = {
        "run_id": "tzpr-route-1",
        "task_key": "DEV-7001",
        "company_id": 7,
        "user_id": 77,
        "source": "manual",
        "execution_mode": "multi_agent",
        "run_state": "queued",
        "active_phase": "queued",
        "status_message": "Run yaratildi",
        "requested_output_profile": "ui",
        "request_payload": {"task_key": "DEV-7001"},
        "final_result": None,
        "error_message": None,
        "agent_runs": [],
        "run_events": [],
    }

    monkeypatch.setattr(tzpr_api, "load_api_session", lambda *args, **kwargs: {})
    monkeypatch.setattr(tzpr_api, "require_customer_scope", lambda *args, **kwargs: (77, 7))
    monkeypatch.setattr(tzpr_api, "create_multi_agent_run", lambda **kwargs: snapshot)
    monkeypatch.setattr(tzpr_api, "get_checker_run_snapshot", lambda run_id: snapshot)
    monkeypatch.setattr(tzpr_api, "execute_multi_agent_run", lambda run_id: None)
    monkeypatch.setattr(tzpr_api, "_worker_queue_enabled", lambda: False)

    with TestClient(app) as client:
      response = client.post(
          "/api/tzpr/runs",
          headers={"X-Session-ID": "token-1"},
          json={
              "task_key": "dev-7001",
              "output_profile": "ui",
              "show_full_diff": True,
          },
      )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "tzpr-route-1"
    assert payload["execution_mode"] == "multi_agent"
    assert payload["run_state"] == "queued"


def test_get_tzpr_run_endpoint_recovers_stalled_run(monkeypatch):
    stalled_snapshot = {
        "run_id": "tzpr-stalled-1",
        "task_key": "DEV-7002",
        "company_id": 7,
        "user_id": 77,
        "source": "manual",
        "execution_mode": "multi_agent",
        "run_state": "running",
        "active_phase": "agent3_arbiter",
        "status_message": "Agent1 va Agent2 natijalari arbitraj qilinmoqda",
        "requested_output_profile": "ui",
        "request_payload": {"task_key": "DEV-7002"},
        "final_result": None,
        "error_message": None,
        "agent_runs": [
            {"agent_key": "agent1_scope_builder", "state": "completed", "artifact": {}},
            {"agent_key": "agent2_verifier", "state": "completed", "artifact": {}},
            {
                "agent_key": "agent3_arbiter",
                "state": "completed",
                "artifact": {
                    "summary": "Manual review kerak.",
                    "run_state": "manual_review",
                    "requirements": [{"id": "REQ-1", "status": "completed"}],
                },
            },
        ],
        "run_events": [
            {"event_type": "agent_finished", "agent_key": "agent3_arbiter"},
        ],
    }
    recovered_snapshot = {
        **stalled_snapshot,
        "run_state": "manual_review",
        "active_phase": "finished",
        "finished_at": "2026-05-13T11:20:00+05:00",
        "final_result": {"success": True, "task_key": "DEV-7002", "run_state": "manual_review"},
        "run_events": [
            *stalled_snapshot["run_events"],
            {"event_type": "run_finished", "agent_key": None},
        ],
    }

    monkeypatch.setattr(tzpr_api, "load_api_session", lambda *args, **kwargs: {"auth": {"role": "company_admin"}})
    monkeypatch.setattr(tzpr_api, "require_customer_scope", lambda *args, **kwargs: (77, 7))
    monkeypatch.setattr(tzpr_api, "get_checker_run_snapshot", lambda run_id: stalled_snapshot)
    monkeypatch.setattr(tzpr_api, "is_stalled_multi_agent_run", lambda snapshot: True)
    monkeypatch.setattr(tzpr_api, "recover_stalled_multi_agent_run", lambda run_id: recovered_snapshot)

    with TestClient(app) as client:
        response = client.get(
            "/api/tzpr/runs/tzpr-stalled-1",
            headers={"X-Session-ID": "token-2"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_state"] == "manual_review"
    assert payload["finished_at"] == "2026-05-13T11:20:00+05:00"
    assert payload["final_result"]["run_state"] == "manual_review"
