"""Admin job console (DLQ) testlari: repository + API auth."""
from fastapi.testclient import TestClient

from utils.database.job_queue_repository import (
    claim_next_job,
    delete_job,
    enqueue_job,
    fetch_queue_snapshot,
    get_job,
    list_jobs,
    mark_job_failed,
    requeue_failed_job,
)
from utils.database.runtime import connect_processing_db


def _conn():
    return connect_processing_db(timeout=30.0, row_factory=True)


def _seed_failed_job(conn, task_key: str, *, error: str = "AI timeout", company_id: int = 321):
    job = enqueue_job(
        conn,
        job_type="run_task_group",
        task_key=task_key,
        company_id=company_id,
        payload={"task_key": task_key},
        dedupe_key=f"job:test-admin:{task_key}",
    )
    claimed = claim_next_job(conn, worker_name="pytest-admin-worker")
    assert claimed and claimed["id"] == job["id"]
    mark_job_failed(conn, claimed, error)
    return claimed


class TestAdminJobsRepository:
    def test_failed_job_listed_requeued_and_claimable_again(self):
        conn = _conn()
        try:
            failed = _seed_failed_job(conn, "TEST-DLQ-1", error="Gemini quota exceeded")

            listed = list_jobs(conn, statuses=["failed"])
            match = [j for j in listed["jobs"] if j["id"] == failed["id"]]
            assert match, "failed job ro'yxatda ko'rinishi kerak"
            row = match[0]
            assert row["status"] == "failed"
            assert row["last_error"] == "Gemini quota exceeded"
            assert row["attempts"] == 1
            assert row["task_key"] == "TEST-DLQ-1"
            assert row["finished_at"]
            assert listed["total"] >= 1

            requeued = requeue_failed_job(conn, failed["id"])
            assert requeued
            assert requeued["status"] == "queued"
            assert requeued["attempts"] == 0
            assert requeued["worker_name"] is None
            assert requeued["started_at"] is None
            assert requeued["last_error"] == "Gemini quota exceeded"

            reclaimed = claim_next_job(conn, worker_name="pytest-admin-worker-2")
            assert reclaimed and reclaimed["id"] == failed["id"]
            assert reclaimed["status"] == "running"
            assert reclaimed["attempts"] == 1
        finally:
            conn.close()

    def test_requeue_rejects_non_failed_job(self):
        conn = _conn()
        try:
            job = enqueue_job(
                conn,
                job_type="run_task_group",
                task_key="TEST-DLQ-2",
                company_id=321,
                dedupe_key="job:test-admin:TEST-DLQ-2",
            )
            assert requeue_failed_job(conn, job["id"]) is None
            assert get_job(conn, job["id"])["status"] == "queued"
        finally:
            conn.close()

    def test_delete_job_guards_non_terminal_statuses(self):
        conn = _conn()
        try:
            job = enqueue_job(
                conn,
                job_type="run_task_group",
                task_key="TEST-DLQ-3",
                company_id=321,
                dedupe_key="job:test-admin:TEST-DLQ-3",
            )
            assert delete_job(conn, job["id"]) is False

            claimed = claim_next_job(conn, worker_name="pytest-admin-worker")
            assert claimed and claimed["id"] == job["id"]
            assert delete_job(conn, job["id"]) is False

            mark_job_failed(conn, claimed, "boom")
            assert delete_job(conn, job["id"]) is True
            assert get_job(conn, job["id"]) is None
        finally:
            conn.close()

    def test_list_jobs_company_filter_and_pagination(self):
        conn = _conn()
        try:
            for suffix in ("A", "B", "C"):
                enqueue_job(
                    conn,
                    job_type="run_task_group",
                    task_key=f"TEST-DLQ-4{suffix}",
                    company_id=321,
                    dedupe_key=f"job:test-admin:TEST-DLQ-4{suffix}",
                )
            enqueue_job(
                conn,
                job_type="run_task_group",
                task_key="TEST-DLQ-4Z",
                company_id=999321,
                dedupe_key="job:test-admin:TEST-DLQ-4Z",
            )

            scoped = list_jobs(conn, statuses=["queued"], company_id=999321)
            assert scoped["total"] == 1
            assert scoped["jobs"][0]["task_key"] == "TEST-DLQ-4Z"

            page = list_jobs(conn, statuses=["queued"], company_id=321, limit=2, offset=0)
            assert page["total"] == 3
            assert len(page["jobs"]) == 2
            rest = list_jobs(conn, statuses=["queued"], company_id=321, limit=2, offset=2)
            assert len(rest["jobs"]) == 1
        finally:
            conn.close()

    def test_list_jobs_rejects_unknown_status(self):
        conn = _conn()
        try:
            try:
                list_jobs(conn, statuses=["bogus"])
                assert False, "ValueError kutilgan edi"
            except ValueError:
                pass
        finally:
            conn.close()

    def test_snapshot_includes_recent_failed(self):
        conn = _conn()
        try:
            failed = _seed_failed_job(conn, "TEST-DLQ-5", error="worker crash")

            snapshot = fetch_queue_snapshot(conn)
            assert snapshot["failed"] >= 1
            entries = [item for item in snapshot["recent_failed"] if item["id"] == failed["id"]]
            assert entries
            assert entries[0]["task_key"] == "TEST-DLQ-5"
            assert entries[0]["error"] == "worker crash"
            assert entries[0]["failed_at"]
            assert len(snapshot["recent_failed"]) <= 10
        finally:
            conn.close()


class TestAdminJobsApiAuth:
    def test_requires_session(self):
        from services.webhook.jira_webhook_handler import app

        client = TestClient(app)
        response = client.get("/api/admin/jobs")
        assert response.status_code == 401

    def test_rejects_non_super_admin(self, monkeypatch):
        import services.api.session_scope as session_scope
        from services.webhook.jira_webhook_handler import app

        monkeypatch.setattr(
            session_scope,
            "get_web_session",
            lambda token, touch=True: {
                "auth": {"logged_in": True, "role": "company_admin", "company_id": 321}
            },
        )

        client = TestClient(app)
        response = client.get("/api/admin/jobs", headers={"X-Session-ID": "token-1"})
        assert response.status_code == 403

        response = client.post("/api/admin/jobs/1/requeue", headers={"X-Session-ID": "token-1"})
        assert response.status_code == 403

        response = client.delete("/api/admin/jobs/1", headers={"X-Session-ID": "token-1"})
        assert response.status_code == 403
