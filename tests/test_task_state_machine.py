"""
core/task_state.py — markaziy holat mashinasi testlari.

Ikki qism:
  1. TestTransitionTable (no_db) — sof tranzitsiya-jadval testlari
  2. TestDbGuard — upsert yozuv yo'lidagi guard (APP_TEST_POSTGRES_DSN kerak)
"""
import logging

import pytest

from core.task_state import (
    ALLOWED_SERVICE1_TRANSITIONS,
    ALLOWED_SERVICE2_TRANSITIONS,
    ALLOWED_TASK_TRANSITIONS,
    GUARD_MODE_ENV,
    InvalidTransition,
    ServiceStatus,
    TaskStatus,
    validate_transition,
)


@pytest.fixture
def enforce_mode(monkeypatch):
    monkeypatch.setenv(GUARD_MODE_ENV, "enforce")


@pytest.fixture
def warn_mode(monkeypatch):
    monkeypatch.delenv(GUARD_MODE_ENV, raising=False)


class TestTransitionTable:
    pytestmark = pytest.mark.no_db

    def test_task_status_enum_matches_db_schema(self):
        assert {s.value for s in TaskStatus} == {
            "none", "progressing", "completed", "returned", "error", "blocked",
        }

    def test_service_status_enum_matches_db_schema(self):
        assert {s.value for s in ServiceStatus} == {
            "pending", "done", "error", "skip", "blocked",
        }

    def test_transition_tables_cover_all_states(self):
        assert set(ALLOWED_TASK_TRANSITIONS) == {s.value for s in TaskStatus}
        assert set(ALLOWED_SERVICE1_TRANSITIONS) == {s.value for s in ServiceStatus}
        assert set(ALLOWED_SERVICE2_TRANSITIONS) == {s.value for s in ServiceStatus} - {"skip"}

    @pytest.mark.parametrize("old,new", [
        ("none", "progressing"),          # webhook yangi sikl
        ("progressing", "completed"),     # set_service2_done / mark_completed
        ("progressing", "returned"),      # mark_returned
        ("progressing", "error"),         # mark_error / set_service*_error
        ("progressing", "blocked"),       # mark_blocked / set_service*_blocked
        ("completed", "progressing"),     # re-trigger (reset + mark_progressing)
        ("returned", "progressing"),      # re-trigger, return_count += 1
        ("error", "progressing"),         # re-trigger
        ("blocked", "progressing"),       # retry_scheduler
        ("blocked", "error"),             # retry xatosi (mark_error catch-all)
        ("returned", "error"),            # return'dan keyingi exception handler
    ])
    def test_legal_task_transitions(self, enforce_mode, old, new):
        validate_transition("task_status", old, new, task_id="TEST-1")

    @pytest.mark.parametrize("old,new", [
        ("pending", "done"),
        ("pending", "error"),
        ("pending", "blocked"),
        ("pending", "skip"),              # AI_SKIP kodi
        ("done", "pending"),              # reset / mark_returned_pr_not_merged
        ("done", "error"),                # done'dan keyingi exception
        ("done", "blocked"),
        ("error", "pending"),
        ("blocked", "pending"),           # retry_scheduler
        ("skip", "pending"),              # re-trigger reset
    ])
    def test_legal_service1_transitions(self, enforce_mode, old, new):
        validate_transition("service1_status", old, new, task_id="TEST-1")

    @pytest.mark.parametrize("old,new", [
        ("pending", "done"),
        ("pending", "error"),
        ("pending", "blocked"),
        ("done", "pending"),
        ("error", "pending"),             # keep_service2_pending / reset
        ("blocked", "pending"),
        ("blocked", "error"),             # set_service1_error(default)
    ])
    def test_legal_service2_transitions(self, enforce_mode, old, new):
        validate_transition("service2_status", old, new, task_id="TEST-1")

    @pytest.mark.parametrize("kind,value", [
        ("task_status", "progressing"),
        ("task_status", "error"),
        ("service1_status", "done"),
        ("service2_status", "blocked"),
    ])
    def test_self_loop_always_allowed(self, enforce_mode, kind, value):
        validate_transition(kind, value, value, task_id="TEST-1")

    def test_new_row_old_none_allowed(self, enforce_mode):
        validate_transition("task_status", None, "completed", task_id="TEST-1")

    def test_enum_members_accepted_as_values(self, enforce_mode):
        validate_transition("task_status", TaskStatus.NONE, TaskStatus.PROGRESSING)
        validate_transition("service1_status", ServiceStatus.PENDING, ServiceStatus.SKIP)

    @pytest.mark.parametrize("kind,old,new", [
        ("task_status", "none", "completed"),        # progressing'siz yakun yo'q
        ("task_status", "completed", "returned"),
        ("task_status", "error", "blocked"),
        ("service1_status", "error", "done"),        # reset'siz done bo'lmaydi
        ("service2_status", "done", "skip"),         # service2 da skip yo'q
        ("service2_status", "error", "done"),
        ("task_status", "progressing", "banana"),    # noma'lum qiymat
    ])
    def test_illegal_transition_enforce_raises(self, enforce_mode, kind, old, new):
        with pytest.raises(InvalidTransition):
            validate_transition(kind, old, new, task_id="TEST-1")

    def test_illegal_transition_warn_logs_and_passes(self, warn_mode, caplog):
        with caplog.at_level(logging.WARNING, logger="task_state"):
            validate_transition("task_status", "completed", "returned", task_id="TEST-9")
        assert any(
            "'completed' -> 'returned'" in rec.message and "TEST-9" in rec.message
            for rec in caplog.records
        )

    def test_webhook_full_lifecycle_sequence(self, enforce_mode):
        # webhook oqimi: yangi -> progressing -> returned -> re-trigger -> completed -> re-trigger
        chain = [None, "progressing", "returned", "progressing", "completed", "progressing"]
        for old, new in zip(chain, chain[1:]):
            validate_transition("task_status", old, new, task_id="TEST-FLOW")


class TestDbGuard:
    """upsert yozuv yo'lidagi guard — real PostgreSQL test DB bilan."""

    def _task_db(self, isolate_test_databases):
        return isolate_test_databases["task_db"]

    def test_legal_flow_writes_through(self, isolate_test_databases, warn_mode):
        task_db = self._task_db(isolate_test_databases)
        task_id = "TEST-SM-LEGAL"

        task_db.mark_progressing(task_id, "READY TO TEST")
        task_db.set_service1_done(task_id, compliance_score=85)
        task_db.set_service2_done(task_id)

        row = task_db.get_task(task_id)
        assert row["task_status"] == "completed"
        assert row["service1_status"] == "done"
        assert row["service2_status"] == "done"
        assert row["compliance_score"] == 85

    def test_illegal_write_warn_mode_logs_but_proceeds(self, isolate_test_databases, warn_mode, caplog):
        task_db = self._task_db(isolate_test_databases)
        task_id = "TEST-SM-WARN"

        task_db.mark_progressing(task_id, "READY TO TEST")
        task_db.mark_completed(task_id)

        with caplog.at_level(logging.WARNING, logger="task_state"):
            task_db.upsert_task(task_id, {"task_status": "returned"})

        assert any(
            "task_status" in rec.message and "'completed' -> 'returned'" in rec.message
            for rec in caplog.records
        )
        # warn rejimda yozuv baribir o'tadi
        assert task_db.get_task(task_id)["task_status"] == "returned"

    def test_illegal_write_enforce_mode_raises_and_blocks(self, isolate_test_databases, enforce_mode):
        task_db = self._task_db(isolate_test_databases)
        task_id = "TEST-SM-ENFORCE"

        task_db.mark_progressing(task_id, "READY TO TEST")
        task_db.mark_completed(task_id)

        with pytest.raises(InvalidTransition):
            task_db.upsert_task(task_id, {"task_status": "returned"})

        # enforce rejimda DB o'zgarmaydi
        assert task_db.get_task(task_id)["task_status"] == "completed"

    def test_insert_new_row_not_validated(self, isolate_test_databases, enforce_mode):
        task_db = self._task_db(isolate_test_databases)
        task_id = "TEST-SM-INSERT"

        # Yangi qator (oldingi holat yo'q) — istalgan boshlang'ich qiymat ruxsat
        task_db.upsert_task(task_id, {"task_status": "blocked"})
        assert task_db.get_task(task_id)["task_status"] == "blocked"
