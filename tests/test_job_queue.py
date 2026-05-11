from datetime import datetime, timedelta


class TestJobQueueRuntime:
    def test_enqueue_claim_and_complete_job(self):
        from utils.database.task_db import (
            claim_next_background_job,
            complete_background_job,
            enqueue_background_job,
            get_background_queue_snapshot,
        )

        job = enqueue_background_job(
            "run_checker_only",
            "TEST-JOB-1",
            company_id=321,
            payload={"task_key": "TEST-JOB-1", "company_id": 321, "new_status": "READY TO TEST"},
            dedupe_key="job:test-1",
        )
        assert job
        assert job["status"] == "queued"

        claimed = claim_next_background_job("pytest-worker")
        assert claimed
        assert claimed["id"] == job["id"]
        assert claimed["status"] == "running"

        assert complete_background_job(claimed) is True

        snapshot = get_background_queue_snapshot()
        assert snapshot["done"] >= 1

    def test_enqueue_job_dedupe_blocks_duplicate_queued_job(self):
        from utils.database.task_db import enqueue_background_job

        first = enqueue_background_job(
            "run_task_group",
            "TEST-JOB-2",
            company_id=321,
            payload={"task_key": "TEST-JOB-2", "company_id": 321, "new_status": "READY TO TEST"},
            dedupe_key="job:test-2",
        )
        second = enqueue_background_job(
            "run_task_group",
            "TEST-JOB-2",
            company_id=321,
            payload={"task_key": "TEST-JOB-2", "company_id": 321, "new_status": "READY TO TEST"},
            dedupe_key="job:test-2",
        )

        assert first["id"] == second["id"]

    def test_due_blocked_task_is_enqueued_for_retry(self):
        from services.worker.main import _enqueue_due_retry_jobs
        from utils.database.task_db import (
            claim_next_background_job,
            mark_progressing,
            set_service1_blocked,
            upsert_task,
        )

        task_key = "TEST-RETRY-1"
        mark_progressing(task_key, "READY TO TEST", datetime.now(), company_id=321)
        set_service1_blocked(task_key, "AI timeout", retry_minutes=0)
        upsert_task(task_key, {"company_id": 321, "blocked_retry_at": (datetime.now() - timedelta(minutes=1)).isoformat()})

        enqueued = _enqueue_due_retry_jobs()
        assert enqueued >= 1

        claimed = claim_next_background_job("pytest-worker")
        assert claimed
        assert claimed["job_type"] == "retry_blocked_task"
        assert claimed["task_key"] == task_key
