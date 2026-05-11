"""
Focused regression tests for repository-based DB refactors.

Bu testlar mavjud katta suite'ga aralashmaydi va aynan repository split
qilingan joylarning behavior'ini tekshiradi.
"""
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from utils.database.runtime import connect_processing_sqlite
from utils.database.runtime import connect_auth_sqlite


class TestTaskRepositoryRefactor:
    def test_task_db_roundtrip_still_works(self):
        from utils.database.task_db import mark_progressing, get_task, delete_task

        task_id = "TEST-REPO-ROUNDTRIP-001"
        mark_progressing(task_id, "READY TO TEST")

        task = get_task(task_id)
        assert task is not None
        assert task["task_status"] == "progressing"
        assert task["last_jira_status"] == "READY TO TEST"

        assert delete_task(task_id) is True
        assert get_task(task_id) is None

    def test_processing_schema_helpers_keep_required_columns(self):
        from utils.database.task_db import init_db

        init_db()

        conn = connect_processing_sqlite(row_factory=True)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(task_processing)")
        task_columns = {row["name"] for row in cursor.fetchall()}
        assert {"company_id", "return_reason", "blocked_retry_at"}.issubset(task_columns)

        cursor.execute("PRAGMA table_info(task_status_history)")
        history_columns = {row["name"] for row in cursor.fetchall()}
        assert {"task_id", "to_status", "changed_at", "issue_type"}.issubset(history_columns)

        conn.close()

    def test_blocked_retry_query_returns_due_tasks(self):
        from utils.database.task_db import (
            mark_progressing,
            set_service1_blocked,
            upsert_task,
            get_blocked_tasks_ready_for_retry,
            delete_task,
        )

        task_id = "TEST-REPO-BLOCKED-001"
        mark_progressing(task_id, "READY TO TEST")
        set_service1_blocked(task_id, "rate limit", retry_minutes=10)
        upsert_task(task_id, {
            "blocked_retry_at": (datetime.now() - timedelta(minutes=2)).isoformat(),
        })

        blocked = get_blocked_tasks_ready_for_retry()
        assert any(row["task_id"] == task_id for row in blocked)

        delete_task(task_id)

    def test_status_history_report_query_reads_back_logged_transition(self):
        from utils.database.task_db import log_status_change, get_status_history_for_report

        task_id = "TEST-REPO-HISTORY-001"
        changed_at = datetime.now() - timedelta(minutes=5)
        log_status_change(
            task_id=task_id,
            from_status="IN PROGRESS",
            to_status="READY TO TEST",
            changed_at=changed_at,
            assignee="Repo Tester",
            story_points=3.0,
            issue_type="Story",
        )

        rows = get_status_history_for_report(days=1)
        matched = [row for row in rows if row["task_id"] == task_id and row["to_status"] == "READY TO TEST"]
        assert matched


class TestSprintReportRepositoryRefactor:
    def test_sprint_report_repository_filters_by_company(self):
        from utils.database.task_db import upsert_task, delete_task
        from utils.database.sprint_report_repository import fetch_total_tasks, fetch_task_type_stats

        task_a = "TEST-REPO-SPRINT-A"
        task_b = "TEST-REPO-SPRINT-B"
        now = datetime.now().isoformat()

        upsert_task(task_a, {
            "company_id": 101,
            "task_status": "completed",
            "task_type": "bug",
            "created_at": now,
            "updated_at": now,
        })
        upsert_task(task_b, {
            "company_id": 202,
            "task_status": "completed",
            "task_type": "client",
            "created_at": now,
            "updated_at": now,
        })

        conn = connect_processing_sqlite(row_factory=True)
        cursor = conn.cursor()

        total = fetch_total_tasks(cursor, 101, 30)
        stats = fetch_task_type_stats(cursor, 101, 30)

        conn.close()

        assert total == 1
        assert len(stats) == 1
        assert stats[0]["task_type"] == "bug"

        delete_task(task_a)
        delete_task(task_b)

    def test_sprint_report_repository_adapter_switches_postgres_placeholders(self):
        from utils.database.sprint_report_repository import _prepare_query

        class FakePostgresCursor:
            pass

        FakePostgresCursor.__module__ = "psycopg.cursor"

        query = "SELECT * FROM task_processing WHERE company_id = ? AND created_at >= ?"
        assert _prepare_query(FakePostgresCursor(), query) == (
            "SELECT * FROM task_processing WHERE company_id = %s AND created_at >= %s"
        )


class TestMonitoringRepositoryRefactor:
    def test_monitoring_delete_check_returns_dict_shape(self):
        from utils.database.task_db import upsert_task, delete_task
        from utils.database.monitoring_repository import get_task_for_delete_check

        task_id = "TEST-REPO-MONITOR-001"
        upsert_task(task_id, {
            "company_id": 303,
            "task_status": "blocked",
            "service1_status": "pending",
            "service2_status": "done",
            "updated_at": datetime.now().isoformat(),
        })

        conn = connect_processing_sqlite(row_factory=True)
        task = get_task_for_delete_check(conn, task_id, 303)
        conn.close()

        assert task["task_id"] == task_id
        assert task["task_status"] == "blocked"
        assert task["service1_status"] == "pending"
        assert task["service2_status"] == "done"

        delete_task(task_id)

    def test_monitoring_query_adapter_switches_postgres_placeholders(self):
        from utils.database.monitoring_repository import _prepare_query

        class FakePostgresConnection:
            pass

        FakePostgresConnection.__module__ = "psycopg.connection"

        query = "SELECT * FROM task_processing WHERE task_id = ? AND company_id = ?"
        assert _prepare_query(FakePostgresConnection(), query) == (
            "SELECT * FROM task_processing WHERE task_id = %s AND company_id = %s"
        )


class TestDatabaseRuntimeHelpers:
    def test_sqlite_runtime_pragmas_helpers_are_safe(self):
        from utils.database.runtime import (
            connect_processing_sqlite,
            apply_sqlite_fresh_read_pragmas,
            checkpoint_sqlite_wal,
            is_sqlite_connection,
        )

        conn = connect_processing_sqlite()
        assert is_sqlite_connection(conn) is True

        apply_sqlite_fresh_read_pragmas(conn)
        checkpoint_sqlite_wal(conn, "TRUNCATE")
        conn.close()

    def test_runtime_sqlite_helpers_noop_for_non_sqlite_connections(self):
        from utils.database.runtime import (
            apply_sqlite_fresh_read_pragmas,
            checkpoint_sqlite_wal,
            is_sqlite_connection,
        )

        class FakePostgresConnection:
            pass

        fake_conn = FakePostgresConnection()
        assert is_sqlite_connection(fake_conn) is False

        apply_sqlite_fresh_read_pragmas(fake_conn)
        checkpoint_sqlite_wal(fake_conn, "TRUNCATE")


class TestDatabaseRepositoryCommonHelpers:
    def test_database_repository_common_prepares_postgres_placeholders(self):
        from utils.database.repository_common import prepare_query, uses_postgres_params

        class FakePostgresCursor:
            pass

        FakePostgresCursor.__module__ = "psycopg.cursor"

        query = "SELECT * FROM task_processing WHERE task_id = ? AND company_id = ?"
        assert uses_postgres_params(FakePostgresCursor()) is True
        assert prepare_query(FakePostgresCursor(), query) == (
            "SELECT * FROM task_processing WHERE task_id = %s AND company_id = %s"
        )

    def test_database_repository_common_row_to_dict_supports_sqlite_rows(self):
        from utils.database.repository_common import row_to_dict

        conn = connect_processing_sqlite(row_factory=True)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 AS sample_value")
        row = cursor.fetchone()
        conn.close()

        assert row_to_dict(row) == {"sample_value": 1}


class TestAuthSchemaRefactor:
    def test_auth_init_still_provides_required_tables_and_columns(self):
        from utils.auth.auth_db import init_auth_db

        init_auth_db()

        conn = connect_auth_sqlite()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row["name"] for row in cursor.fetchall()}
        expected_tables = {
            "companies",
            "users",
            "company_settings",
            "user_module_settings",
            "user_credentials",
            "global_settings",
            "login_attempts",
            "login_audit_logs",
            "platform_admins",
            "user_password_reset_tokens",
            "company_subscriptions",
        }
        assert expected_tables.issubset(tables)

        cursor.execute("PRAGMA table_info(user_credentials)")
        user_credential_columns = {row[1] for row in cursor.fetchall()}
        assert "jira_project_keys" in user_credential_columns
        assert "figma_tokens" in user_credential_columns
        assert "gemini_model" in user_credential_columns

        cursor.execute("PRAGMA table_info(company_settings)")
        company_settings_columns = {row[1] for row in cursor.fetchall()}
        assert "figma_tokens" in company_settings_columns
        assert "gemini_model" in company_settings_columns
        assert "webhook_jira_token" in company_settings_columns
        assert "webhook_figma_tokens" in company_settings_columns
        assert "webhook_gemini_model" in company_settings_columns

        conn.close()


class TestAuthConfigHelperRefactor:
    def test_user_credentials_fall_back_to_global_gemini_defaults(self):
        from utils.auth.auth_config_helpers import build_user_credentials_for_service

        result = build_user_credentials_for_service(
            user_id=7,
            user_credentials={
                "jira_email": "qa@example.com",
                "jira_token": "jira-token",
                "github_token": "github-token",
                "github_org": "acme",
            },
            parse_figma_tokens=lambda raw: [],
            get_global_gemini_defaults=lambda: {
                "api_key_1": "global-key-1",
                "api_key_2": "global-key-2",
                "model": "gemini-global",
            },
            get_user_by_id=lambda user_id: {"company_id": 99},
            get_company_settings=lambda company_id: {},
            getenv=lambda key, default="": "",
        )

        assert result["gemini_keys"] == ["global-key-1", "global-key-2"]

    def test_user_credentials_use_company_shared_integrations_and_personal_gemini_override(self):
        from utils.auth.auth_config_helpers import build_user_credentials_for_service

        result = build_user_credentials_for_service(
            user_id=9,
            user_credentials={
                "jira_server": "https://ignored.example.atlassian.net",
                "jira_email": "ignored@example.com",
                "jira_token": "ignored-user-jira",
                "github_token": "ignored-user-github",
                "github_org": "ignored-org",
                "figma_tokens": '[{"name":"ignored","token":"ignored-figma"}]',
                "gemini_api_key_1": "user-gemini-key",
                "gemini_model": "gemini-2.5-pro",
            },
            parse_figma_tokens=lambda raw: __import__("json").loads(raw) if raw else [],
            get_global_gemini_defaults=lambda: {"api_key_1": "", "api_key_2": "", "model": ""},
            get_user_by_id=lambda user_id: {"id": user_id, "company_id": 55},
            get_company_settings=lambda company_id: {
                "jira_server": "https://shared.example.atlassian.net",
                "jira_email": "shared@example.com",
                "jira_token": "shared-jira-token",
                "github_token": "shared-github-token",
                "github_org": "shared-org",
                "figma_tokens": '[{"name":"shared","token":"shared-figma"}]',
                "gemini_api_key_1": "company-gemini-key",
                "gemini_model": "gemini-2.5-flash",
            },
            getenv=lambda key, default="": "",
        )

        assert result["jira_server"] == "https://shared.example.atlassian.net"
        assert result["jira_email"] == "shared@example.com"
        assert result["jira_token"] == "shared-jira-token"
        assert result["github_token"] == "shared-github-token"
        assert result["github_org"] == "shared-org"
        assert result["figma_tokens"][0]["token"] == "shared-figma"
        assert result["gemini_keys"] == ["user-gemini-key"]
        assert result["gemini_model"] == "gemini-2.5-pro"

    def test_company_webhook_credentials_prefer_dedicated_webhook_fields(self):
        from utils.auth.auth_config_helpers import build_company_webhook_credentials

        result = build_company_webhook_credentials(
            company_id=77,
            company_settings={
                "jira_server": "https://shared.example.atlassian.net",
                "jira_email": "shared@example.com",
                "jira_token": "shared-jira-token",
                "github_token": "shared-github-token",
                "github_org": "shared-org",
                "figma_tokens": '[{"name":"shared","token":"shared-figma"}]',
                "gemini_api_key_1": "shared-gemini-key",
                "gemini_model": "gemini-2.5-flash",
                "webhook_jira_server": "https://webhook.example.atlassian.net",
                "webhook_jira_email": "webhook@example.com",
                "webhook_jira_token": "webhook-jira-token",
                "webhook_github_token": "webhook-github-token",
                "webhook_github_org": "webhook-org",
                "webhook_figma_tokens": '[{"name":"bot","token":"webhook-figma"}]',
                "webhook_gemini_api_key_1": "webhook-gemini-key",
                "webhook_gemini_model": "gemini-2.5-pro",
            },
            parse_figma_tokens=lambda raw: __import__("json").loads(raw) if raw else [],
        )

        assert result["jira_server"] == "https://webhook.example.atlassian.net"
        assert result["jira_email"] == "webhook@example.com"
        assert result["jira_token"] == "webhook-jira-token"
        assert result["github_token"] == "webhook-github-token"
        assert result["github_org"] == "webhook-org"
        assert result["figma_tokens"][0]["token"] == "webhook-figma"
        assert result["gemini_keys"] == ["webhook-gemini-key"]
        assert result["gemini_model"] == "gemini-2.5-pro"


class TestSharedCredentialModel:
    def test_has_user_credentials_configured_uses_company_shared_credentials(self, monkeypatch):
        from utils.auth.auth_db import (
            create_company,
            create_user,
            save_company_settings,
            has_user_credentials_configured,
        )

        monkeypatch.setenv("APP_CREDENTIALS_MASTER_KEY", "shared-cred-test-key")
        company = create_company(f"shd{uuid4().hex[:8]}", "Shared Cred Company")
        assert company is not None
        user, err = create_user(company["id"], f"user{uuid4().hex[:6]}", "secret123", role="user")
        assert err is None
        assert user is not None

        assert has_user_credentials_configured(user["id"]) is False
        assert save_company_settings(company["id"], {
            "jira_email": "shared@example.com",
            "jira_token": "shared-jira-token",
            "github_token": "shared-github-token",
            "jira_project_keys": f"SHD{uuid4().hex[:6]}",
        }) is True
        assert has_user_credentials_configured(user["id"]) is True

    def test_company_admin_does_not_consume_extra_user_seat(self):
        from utils.auth.auth_db import create_company, create_user, count_users_in_company

        company = create_company(f"seat{uuid4().hex[:8]}", "Seat Policy Company", seat_limit=0)
        assert company is not None

        admin_user, admin_err = create_user(company["id"], f"admin{uuid4().hex[:6]}", "secret123", role="company_admin")
        assert admin_err is None
        assert admin_user is not None
        assert count_users_in_company(company["id"]) == 0

        extra_user, extra_err = create_user(company["id"], f"user{uuid4().hex[:6]}", "secret123", role="user")
        assert extra_user is None
        assert "Seat limit" in extra_err

    def test_standalone_module_settings_remain_per_user_inside_same_company(self):
        from utils.auth.auth_db import create_company, create_user, save_user_module_settings, get_user_module_settings

        company = create_company(f"per{uuid4().hex[:8]}", "Per User Settings Company", seat_limit=1)
        assert company is not None

        admin_user, admin_err = create_user(company["id"], f"admin{uuid4().hex[:6]}", "secret123", role="company_admin")
        member_user, member_err = create_user(company["id"], f"user{uuid4().hex[:6]}", "secret123", role="user")
        assert admin_err is None and admin_user is not None
        assert member_err is None and member_user is not None

        assert save_user_module_settings(admin_user["id"], "tz_pr_checker", {"max_comments_to_read": 15}) is True
        assert save_user_module_settings(member_user["id"], "tz_pr_checker", {"max_comments_to_read": 10}) is True

        assert get_user_module_settings(admin_user["id"], "tz_pr_checker")["max_comments_to_read"] == 15
        assert get_user_module_settings(member_user["id"], "tz_pr_checker")["max_comments_to_read"] == 10


class TestCredentialCryptoHardening:
    def test_encrypt_and_decrypt_sensitive_fields_roundtrip(self, monkeypatch):
        from utils.auth.credential_crypto import (
            encrypt_sensitive_fields,
            decrypt_sensitive_fields,
            is_encrypted_value,
        )

        monkeypatch.setenv("APP_CREDENTIALS_MASTER_KEY", "repo-test-master-key")

        payload = {
            "jira_token": "jira-secret",
            "github_token": "github-secret",
            "figma_tokens": '[{"name":"main","token":"figma-secret"}]',
            "jira_email": "qa@example.com",
        }

        encrypted = encrypt_sensitive_fields(payload)
        assert encrypted["jira_token"] != "jira-secret"
        assert encrypted["github_token"] != "github-secret"
        assert is_encrypted_value(encrypted["jira_token"]) is True
        assert encrypted["jira_email"] == "qa@example.com"

        decrypted = decrypt_sensitive_fields(encrypted)
        assert decrypted["jira_token"] == "jira-secret"
        assert decrypted["github_token"] == "github-secret"
        assert decrypted["figma_tokens"] == '[{"name":"main","token":"figma-secret"}]'

    def test_user_credentials_are_stored_encrypted_and_loaded_decrypted(self, monkeypatch):
        from utils.auth.auth_db import create_company, create_user, save_user_credentials, get_user_credentials

        monkeypatch.setenv("APP_CREDENTIALS_MASTER_KEY", "repo-test-master-key")

        company = create_company(f"ucr{uuid4().hex[:8]}", "User Credential Repo")
        assert company is not None
        user, err = create_user(company["id"], f"user{uuid4().hex[:6]}", "secret123", role="user")
        assert err is None
        assert user is not None

        payload = {
            "jira_email": "qa@example.com",
            "jira_token": "jira-secret",
            "github_token": "github-secret",
            "jira_project_keys": "DEV",
        }
        assert save_user_credentials(user["id"], payload) is True

        conn = connect_auth_sqlite()
        cursor = conn.cursor()
        cursor.execute("SELECT jira_token, github_token FROM user_credentials WHERE user_id = ?", (user["id"],))
        row = cursor.fetchone()
        conn.close()

        assert row["jira_token"].startswith("enc::")
        assert row["github_token"].startswith("enc::")

        loaded = get_user_credentials(user["id"])
        assert loaded["jira_token"] == "jira-secret"
        assert loaded["github_token"] == "github-secret"

    def test_company_settings_credentials_are_stored_encrypted_and_loaded_decrypted(self, monkeypatch):
        from utils.auth.auth_db import create_company, save_company_settings, get_company_settings

        monkeypatch.setenv("APP_CREDENTIALS_MASTER_KEY", "repo-test-master-key")

        company = create_company(f"ccr{uuid4().hex[:8]}", "Company Credential Repo")
        assert company is not None

        payload = {
            "jira_email": "admin@example.com",
            "jira_token": "jira-company-secret",
            "github_token": "github-company-secret",
            "gemini_api_key_1": "gemini-company-secret",
            "webhook_project_keys": f"CP{uuid4().hex[:6].upper()}",
        }
        assert save_company_settings(company["id"], payload) is True

        conn = connect_auth_sqlite()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT jira_token, github_token, gemini_api_key_1 FROM company_settings WHERE company_id = ?",
            (company["id"],),
        )
        row = cursor.fetchone()
        conn.close()

        assert row["jira_token"].startswith("enc::")
        assert row["github_token"].startswith("enc::")
        assert row["gemini_api_key_1"].startswith("enc::")

        loaded = get_company_settings(company["id"])
        assert loaded["jira_token"] == "jira-company-secret"
        assert loaded["github_token"] == "github-company-secret"
        assert loaded["gemini_api_key_1"] == "gemini-company-secret"

    def test_company_webhook_credentials_are_stored_separately_from_shared_settings(self, monkeypatch):
        from utils.auth.auth_db import (
            create_company,
            save_company_settings,
            get_company_settings,
            get_company_webhook_credentials,
        )

        monkeypatch.setenv("APP_CREDENTIALS_MASTER_KEY", "repo-test-master-key")

        company = create_company(f"whc{uuid4().hex[:8]}", "Webhook Credential Repo")
        assert company is not None

        assert save_company_settings(company["id"], {
            "jira_server": "https://shared.example.atlassian.net",
            "jira_email": "shared@example.com",
            "jira_token": "shared-jira-secret",
            "github_token": "shared-github-secret",
            "github_org": "shared-org",
            "gemini_api_key_1": "shared-gemini-secret",
            "webhook_jira_server": "https://webhook.example.atlassian.net",
            "webhook_jira_email": "webhook@example.com",
            "webhook_jira_token": "webhook-jira-secret",
            "webhook_github_token": "webhook-github-secret",
            "webhook_github_org": "webhook-org",
            "webhook_gemini_api_key_1": "webhook-gemini-secret",
            "webhook_figma_tokens": '[{"name":"bot","token":"webhook-figma-secret"}]',
            "webhook_project_keys": f"WHP{uuid4().hex[:6].upper()}",
        }) is True

        conn = connect_auth_sqlite()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT jira_token, webhook_jira_token, github_token, webhook_github_token,
                   gemini_api_key_1, webhook_gemini_api_key_1
            FROM company_settings
            WHERE company_id = ?
            """,
            (company["id"],),
        )
        row = cursor.fetchone()
        conn.close()

        assert row["jira_token"].startswith("enc::")
        assert row["webhook_jira_token"].startswith("enc::")
        assert row["github_token"].startswith("enc::")
        assert row["webhook_github_token"].startswith("enc::")
        assert row["gemini_api_key_1"].startswith("enc::")
        assert row["webhook_gemini_api_key_1"].startswith("enc::")

        loaded = get_company_settings(company["id"])
        webhook_creds = get_company_webhook_credentials(company["id"])

        assert loaded["jira_token"] == "shared-jira-secret"
        assert loaded["github_token"] == "shared-github-secret"
        assert loaded["gemini_api_key_1"] == "shared-gemini-secret"
        assert webhook_creds["jira_token"] == "webhook-jira-secret"
        assert webhook_creds["github_token"] == "webhook-github-secret"
        assert webhook_creds["github_org"] == "webhook-org"
        assert webhook_creds["gemini_keys"] == ["webhook-gemini-secret"]
        assert webhook_creds["figma_tokens"][0]["token"] == "webhook-figma-secret"

    def test_credential_security_status_reports_master_key_modes(self, monkeypatch):
        from utils.auth.credential_crypto import get_credential_security_status

        monkeypatch.setenv("APP_CREDENTIALS_MASTER_KEY", "repo-master-key")
        monkeypatch.setenv("SUPER_ADMIN_PASSWORD", "fallback-pass")
        status = get_credential_security_status()
        assert status["status"] == "ok"

        monkeypatch.delenv("APP_CREDENTIALS_MASTER_KEY", raising=False)
        status = get_credential_security_status()
        assert status["status"] == "warning"

        monkeypatch.delenv("SUPER_ADMIN_PASSWORD", raising=False)
        status = get_credential_security_status()
        assert status["status"] == "danger"

    def test_credential_masking_helpers_preserve_existing_secret_on_blank_input(self):
        from utils.auth.credential_crypto import (
            mask_secret_value,
            resolve_secret_input,
            merge_masked_token_rows,
        )

        assert mask_secret_value("secret-token-123456").endswith("3456")
        assert resolve_secret_input("", "stored-secret") == "stored-secret"
        assert resolve_secret_input("new-secret", "stored-secret") == "new-secret"

        merged_rows = merge_masked_token_rows(
            [
                {"name": "A", "token": ""},
                {"name": "B", "token": "fresh-token"},
            ],
            [
                {"name": "A", "token": "old-token-a"},
                {"name": "B", "token": "old-token-b"},
            ],
        )
        assert merged_rows == [
            {"name": "A", "token": "old-token-a"},
            {"name": "B", "token": "fresh-token"},
        ]

    def test_credential_crypto_supports_old_master_key_rotation_chain(self, monkeypatch):
        import utils.auth.credential_crypto as crypto

        monkeypatch.setenv("APP_CREDENTIALS_MASTER_KEY", "old-master-key")
        encrypted = crypto.encrypt_value("jira-secret-rotation")

        monkeypatch.setenv("APP_CREDENTIALS_MASTER_KEY", "new-master-key")
        monkeypatch.setenv("APP_CREDENTIALS_OLD_MASTER_KEYS", "old-master-key")

        assert crypto.decrypt_value(encrypted) == "jira-secret-rotation"
        assert crypto.needs_reencryption(encrypted) is True

        status = crypto.get_credential_security_status()
        assert status["status"] == "ok"
        assert status["rotation_ready"] is True

    def test_reencrypt_sensitive_fields_rewrites_old_key_ciphertext(self, monkeypatch):
        import utils.auth.credential_crypto as crypto

        monkeypatch.setenv("APP_CREDENTIALS_MASTER_KEY", "old-master-key")
        old_encrypted = crypto.encrypt_value("rotate-me")

        monkeypatch.setenv("APP_CREDENTIALS_MASTER_KEY", "new-master-key")
        monkeypatch.setenv("APP_CREDENTIALS_OLD_MASTER_KEYS", "old-master-key")

        rotated = crypto.reencrypt_sensitive_fields({"jira_token": old_encrypted})
        assert rotated["jira_token"] != old_encrypted
        assert crypto.decrypt_value(rotated["jira_token"]) == "rotate-me"
        assert crypto.payload_needs_reencryption(rotated) is False

    def test_user_credentials_save_is_blocked_without_any_encryption_secret(self, monkeypatch):
        from utils.auth.auth_db import create_company, create_user, save_user_credentials

        monkeypatch.delenv("APP_CREDENTIALS_MASTER_KEY", raising=False)
        monkeypatch.delenv("SUPER_ADMIN_PASSWORD", raising=False)

        company = create_company(f"ubk{uuid4().hex[:8]}", "Blocked User Creds")
        assert company is not None
        user, err = create_user(company["id"], f"user{uuid4().hex[:6]}", "secret123", role="user")
        assert err is None
        assert user is not None

        ok = save_user_credentials(
            user["id"],
            {
                "jira_email": "qa@example.com",
                "jira_token": "jira-secret",
                "github_token": "github-secret",
            },
        )
        assert ok is False

    def test_company_settings_save_is_blocked_without_any_encryption_secret(self, monkeypatch):
        from utils.auth.auth_db import create_company, save_company_settings

        monkeypatch.delenv("APP_CREDENTIALS_MASTER_KEY", raising=False)
        monkeypatch.delenv("SUPER_ADMIN_PASSWORD", raising=False)

        company = create_company(f"cbk{uuid4().hex[:8]}", "Blocked Company Creds")
        assert company is not None

        ok = save_company_settings(
            company["id"],
            {
                "jira_email": "admin@example.com",
                "jira_token": "jira-company-secret",
                "github_token": "github-company-secret",
            },
        )
        assert ok is False


class TestAuthCompanyRepositoryRefactor:
    def test_create_company_still_creates_default_subscription(self):
        from utils.auth.auth_db import create_company, get_company_subscription

        company_code = f"repo{uuid4().hex[:8]}"
        company = create_company(company_code, "Repo Company", enabled_modules={"webhook": True})
        assert company is not None

        subscription = get_company_subscription(company["id"])
        assert subscription["plan_name"] == "base"
        assert subscription["subscription_status"] == "trial"
        assert subscription["billing_mode"] == "manual"
        assert subscription["billing_end_date"]

    def test_project_key_conflicts_are_still_detected(self):
        from utils.auth.auth_db import create_company, save_company_settings

        existing = create_company(f"base{uuid4().hex[:8]}", "Existing Project Key Company")
        company_code = f"repc{uuid4().hex[:8]}"
        company = create_company(company_code, "Repo Conflict Company")
        assert existing is not None
        assert company is not None
        assert save_company_settings(existing["id"], {"webhook_project_keys": "TEST"}) is True

        result = save_company_settings(company["id"], {"webhook_project_keys": "TEST, NEWKEY"})
        assert result is False

    def test_failed_login_lockout_state_still_works(self):
        from utils.auth.auth_db import get_login_attempt_state, record_failed_login, reset_login_attempts

        identifier = f"repo-lock-{uuid4().hex[:8]}"

        for _ in range(4):
            result = record_failed_login(identifier)
            assert result["is_locked"] is False

        result = record_failed_login(identifier)
        assert result["failed_count"] == 5
        assert result["is_locked"] is True
        assert result["seconds_remaining"] > 0

        state = get_login_attempt_state(identifier)
        assert state["is_locked"] is True
        assert state["failed_count"] == 5

        reset_login_attempts(identifier)
        reset_state = get_login_attempt_state(identifier)
        assert reset_state == {"failed_count": 0, "is_locked": False, "seconds_remaining": 0}

    def test_company_scoped_user_mutations_reject_foreign_company_targets(self):
        from utils.auth.auth_db import (
            create_company,
            create_user,
            get_user_by_id,
            update_user_status_for_company,
            update_user_password_for_company,
            delete_user_for_company,
            verify_password,
        )

        company_a = create_company(f"caa{uuid4().hex[:8]}", "Company A")
        company_b = create_company(f"cbb{uuid4().hex[:8]}", "Company B")
        assert company_a is not None and company_b is not None

        user, err = create_user(company_a["id"], f"user{uuid4().hex[:6]}", "secret123", role="user")
        assert err is None
        assert user is not None

        original_user = get_user_by_id(user["id"])
        assert original_user is not None

        assert update_user_status_for_company(user["id"], company_b["id"], False) is False
        assert update_user_password_for_company(user["id"], company_b["id"], "changed456") is False
        assert delete_user_for_company(user["id"], company_b["id"]) is False

        after_user = get_user_by_id(user["id"])
        assert after_user is not None
        assert int(after_user["is_active"]) == 1
        assert verify_password("secret123", after_user["password_hash"]) is True

    def test_company_scoped_user_mutations_protect_company_admin_accounts(self):
        from utils.auth.auth_db import (
            create_company,
            create_user,
            get_user_by_id,
            update_user_status_for_company,
            delete_user_for_company,
        )

        company = create_company(f"cad{uuid4().hex[:8]}", "Company Admin Guard")
        assert company is not None

        admin_user, err = create_user(company["id"], f"admin{uuid4().hex[:6]}", "secret123", role="company_admin")
        assert err is None
        assert admin_user is not None

        assert update_user_status_for_company(admin_user["id"], company["id"], False) is False
        assert delete_user_for_company(admin_user["id"], company["id"]) is False

        saved_admin = get_user_by_id(admin_user["id"])
        assert saved_admin is not None
        assert saved_admin["role"] == "company_admin"
        assert int(saved_admin["is_active"]) == 1

    def test_company_webhook_settings_roundtrip_shape(self):
        from utils.auth.auth_config_helpers import (
            build_company_webhook_config,
            validate_company_webhook_config_shape,
            parse_webhook_module_settings,
        )

        config = build_company_webhook_config({
            "webhook_project_keys": "DEV, QA",
            "webhook_trigger_status": "READY TO TEST",
            "webhook_trigger_aliases": "READY TO TEST,Ready To Test",
            "webhook_auto_return_enabled": 1,
            "webhook_return_threshold": "75",
        })
        errors = validate_company_webhook_config_shape(config)
        module_settings = parse_webhook_module_settings('{"queue":{"queue_enabled":true}}')

        assert errors == []
        assert config["webhook_auto_return_enabled"] is True
        assert config["webhook_return_threshold"] == 75
        assert module_settings["queue"]["queue_enabled"] is True


class TestPlatformAdminFoundation:
    def test_seed_default_platform_admin_writes_env_admin_into_db(self, monkeypatch):
        from utils.auth.auth_db import seed_default_platform_admin, get_platform_admin_by_username, verify_password

        username = f"admin{uuid4().hex[:6]}"
        monkeypatch.setenv("SUPER_ADMIN_USERNAME", username)
        monkeypatch.setenv("SUPER_ADMIN_PASSWORD", "seed-pass-123")

        assert seed_default_platform_admin() is True

        admin = get_platform_admin_by_username(username)
        assert admin is not None
        assert admin["username"] == username
        assert int(admin["is_active"]) == 1
        assert verify_password("seed-pass-123", admin["password_hash"]) is True

    def test_save_platform_admin_creates_db_based_super_admin(self):
        from utils.auth.auth_db import save_platform_admin, get_platform_admin_by_username, verify_password

        username = f"dbadmin{uuid4().hex[:6]}"
        assert save_platform_admin(username, "db-secret-123", is_active=True) is True

        admin = get_platform_admin_by_username(username)
        assert admin is not None
        assert admin["username"] == username
        assert verify_password("db-secret-123", admin["password_hash"]) is True

    def test_save_platform_admin_rotates_existing_password_hash(self):
        from utils.auth.auth_db import save_platform_admin, get_platform_admin_by_username, verify_password

        username = f"rotate{uuid4().hex[:6]}"
        assert save_platform_admin(username, "old-secret-123", is_active=True) is True
        first = get_platform_admin_by_username(username)
        assert first is not None

        assert save_platform_admin(username, "new-secret-456", is_active=True) is True
        updated = get_platform_admin_by_username(username)
        assert updated is not None
        assert updated["password_hash"] != first["password_hash"]
        assert verify_password("new-secret-456", updated["password_hash"]) is True

    def test_auth_manager_empty_session_includes_auth_source(self):
        from utils.auth.auth_manager import _EMPTY_SESSION

        assert "auth_source" in _EMPTY_SESSION
        assert _EMPTY_SESSION["auth_source"] is None

    def test_db_platform_admin_disables_legacy_env_fallback_for_same_username(self, monkeypatch):
        import utils.auth.auth_manager as auth_manager

        monkeypatch.setattr(auth_manager.st, "session_state", {})
        monkeypatch.setattr(auth_manager, "_SUPER_USERNAME", "admin")
        monkeypatch.setattr(auth_manager, "_SUPER_ADMIN_CONFIGURED", True)
        monkeypatch.setattr(auth_manager, "get_platform_admin_by_username", lambda username: {
            "username": "admin",
            "password_hash": "db-hash",
            "is_active": 1,
        })
        monkeypatch.setattr(auth_manager, "get_login_attempt_state", lambda identifier: {"is_locked": False, "seconds_remaining": 0})
        monkeypatch.setattr(auth_manager, "verify_password", lambda password, password_hash: False)
        monkeypatch.setattr(auth_manager, "_check_super_admin", lambda username, password: True)
        monkeypatch.setattr(auth_manager, "record_failed_login", lambda identifier: {"failed_count": 1, "is_locked": False, "seconds_remaining": 0})
        monkeypatch.setattr(auth_manager, "log_login_attempt", lambda *args, **kwargs: True)

        success, message = auth_manager.login("admin", "env-password")

        assert success is False
        assert "noto'g'ri" in message.lower()

    def test_legacy_env_fallback_still_works_when_db_platform_admin_missing(self, monkeypatch):
        import utils.auth.auth_manager as auth_manager

        monkeypatch.setattr(auth_manager.st, "session_state", {})
        monkeypatch.setattr(auth_manager, "_SUPER_USERNAME", "admin")
        monkeypatch.setattr(auth_manager, "_SUPER_ADMIN_CONFIGURED", True)
        monkeypatch.setattr(auth_manager, "get_platform_admin_by_username", lambda username: None)
        monkeypatch.setattr(auth_manager, "get_login_attempt_state", lambda identifier: {"is_locked": False, "seconds_remaining": 0})
        monkeypatch.setattr(auth_manager, "_check_super_admin", lambda username, password: True)
        monkeypatch.setattr(auth_manager, "reset_login_attempts", lambda identifier: True)
        monkeypatch.setattr(auth_manager, "log_login_attempt", lambda *args, **kwargs: True)

        success, message = auth_manager.login("admin", "env-password")

        assert success is True
        assert message == ""
        assert auth_manager.st.session_state["auth"]["auth_source"] == "legacy_env_super_admin"

    def test_company_user_session_contains_expiry_metadata(self, monkeypatch):
        import utils.auth.auth_manager as auth_manager

        monkeypatch.setattr(auth_manager.st, "session_state", {})
        monkeypatch.setattr(auth_manager, "get_platform_admin_by_username", lambda username: None)
        monkeypatch.setattr(auth_manager, "validate_username_format", lambda username: True)
        monkeypatch.setattr(auth_manager, "get_user_by_full_username", lambda username: {
            "id": 10,
            "company_id": 77,
            "role": "user",
            "is_active": 1,
            "password_hash": "hash",
        })
        monkeypatch.setattr(auth_manager, "get_login_attempt_state", lambda identifier: {"is_locked": False, "seconds_remaining": 0})
        monkeypatch.setattr(auth_manager, "verify_password", lambda password, password_hash: True)
        monkeypatch.setattr(auth_manager, "get_company_by_id", lambda company_id: {
            "id": 77,
            "company_code": "acme",
            "company_name": "Acme",
            "is_active": 1,
        })
        monkeypatch.setattr(auth_manager, "is_company_subscription_active", lambda company_id: (True, ""))
        monkeypatch.setattr(auth_manager, "reset_login_attempts", lambda identifier: True)
        monkeypatch.setattr(auth_manager, "log_login_attempt", lambda *args, **kwargs: True)
        monkeypatch.setattr(auth_manager, "parse_username", lambda username: ("qa", "acme"))

        success, _ = auth_manager.login("qa@acme", "secret123")

        assert success is True
        auth_state = auth_manager.st.session_state["auth"]
        assert auth_state["session_started_at"] is not None
        assert auth_state["last_activity_at"] is not None
        assert auth_state["expires_at"] is not None
        assert auth_state["session_nonce"] is not None

    def test_is_authenticated_expires_stale_session(self, monkeypatch):
        import utils.auth.auth_manager as auth_manager

        expired_at = (datetime.now() - timedelta(minutes=1)).isoformat()
        monkeypatch.setattr(auth_manager.st, "session_state", {
            "auth": {
                **auth_manager._EMPTY_SESSION,
                "logged_in": True,
                "role": "user",
                "expires_at": expired_at,
            }
        })

        assert auth_manager.is_authenticated() is False
        assert auth_manager.st.session_state["auth"]["logged_in"] is False
        assert "login_error" in auth_manager.st.session_state


class TestPasswordResetFoundation:
    def test_password_reset_token_can_rotate_password_once(self):
        from utils.auth.auth_db import (
            create_company,
            create_user,
            create_password_reset_token,
            consume_password_reset_token,
            get_user_by_id,
            verify_password,
        )

        company = create_company(f"rst{uuid4().hex[:8]}", "Reset Token Company")
        assert company is not None
        user, err = create_user(company["id"], f"user{uuid4().hex[:6]}", "old-secret-123", role="user")
        assert err is None
        assert user is not None

        reset_payload = create_password_reset_token(user["id"], ttl_minutes=30)
        assert reset_payload is not None
        assert consume_password_reset_token(reset_payload["token"], "new-secret-456") is True
        assert consume_password_reset_token(reset_payload["token"], "another-secret-789") is False

        updated_user = get_user_by_id(user["id"])
        assert updated_user is not None
        assert verify_password("new-secret-456", updated_user["password_hash"]) is True

    def test_password_reset_token_rejects_expired_token(self):
        from utils.auth.auth_db import (
            create_company,
            create_user,
            create_password_reset_token,
            consume_password_reset_token,
            _hash_password_reset_token,
        )

        company = create_company(f"exp{uuid4().hex[:8]}", "Expired Reset Company")
        assert company is not None
        user, err = create_user(company["id"], f"user{uuid4().hex[:6]}", "old-secret-123", role="user")
        assert err is None
        assert user is not None

        reset_payload = create_password_reset_token(user["id"], ttl_minutes=30)
        assert reset_payload is not None

        conn = connect_auth_sqlite()
        conn.execute(
            "UPDATE user_password_reset_tokens SET expires_at = ? WHERE token_hash = ?",
            [
                (datetime.now() - timedelta(minutes=5)).isoformat(),
                _hash_password_reset_token(reset_payload["token"]),
            ],
        )
        conn.commit()
        conn.close()

        assert consume_password_reset_token(reset_payload["token"], "new-secret-456") is False


class TestLoginAuditFoundation:
    def test_login_audit_log_can_be_written_and_read_back(self):
        from utils.auth.auth_db import log_login_attempt, get_recent_login_audit_logs

        identifier = f"audit-{uuid4().hex[:8]}"
        assert log_login_attempt(
            identifier,
            success=False,
            reason="invalid_user_password",
            user_id=123,
            company_id=456,
            role="user",
        ) is True

        rows = get_recent_login_audit_logs(limit=20)
        matched = [row for row in rows if row["identifier"] == identifier]
        assert matched
        assert matched[0]["reason"] == "invalid_user_password"
        assert int(matched[0]["success"]) == 0
        assert matched[0]["role"] == "user"

    def test_login_audit_log_filters_by_success_and_identifier(self):
        from utils.auth.auth_db import log_login_attempt, get_recent_login_audit_logs

        success_identifier = f"audit-success-{uuid4().hex[:6]}"
        failure_identifier = f"audit-failure-{uuid4().hex[:6]}"

        assert log_login_attempt(success_identifier, success=True, reason="user_login", role="user") is True
        assert log_login_attempt(failure_identifier, success=False, reason="invalid_user_password", role="user") is True

        success_rows = get_recent_login_audit_logs(limit=20, success=True, identifier_contains=success_identifier)
        failure_rows = get_recent_login_audit_logs(limit=20, success=False, identifier_contains=failure_identifier)

        assert any(row["identifier"] == success_identifier for row in success_rows)
        assert all(int(row["success"]) == 1 for row in success_rows)
        assert any(row["identifier"] == failure_identifier for row in failure_rows)
        assert all(int(row["success"]) == 0 for row in failure_rows)


class TestAuthSubscriptionHelperRefactor:
    def test_subscription_validation_rejects_missing_end_date_for_active(self):
        import re
        from utils.auth.auth_subscription_helpers import validate_company_subscription_data

        ok, error, normalized = validate_company_subscription_data(
            {
                "plan_name": "base",
                "subscription_status": "active",
                "billing_mode": "manual",
                "billing_start_date": "2026-05-01",
                "billing_end_date": "",
            },
            re.compile(r"^[a-z0-9][a-z0-9_-]{1,31}$"),
            {"trial", "active", "past_due", "suspended", "cancelled"},
            {"manual"},
            "manual",
        )

        assert ok is False
        assert "billing end date" in error.lower()
        assert normalized == {}

    def test_effective_modules_include_plan_entitlements_only_for_active_access(self):
        from utils.auth.auth_subscription_helpers import get_effective_company_modules

        base_modules = {
            "tz_pr_checker": False,
            "testcase_generator": False,
            "monitoring": True,
        }
        effective = get_effective_company_modules(
            base_modules,
            {"subscription_status": "trial", "plan_name": "base"},
            {"trial", "active", "past_due"},
            "base",
            {"base": {"tz_pr_checker", "testcase_generator"}},
        )
        suspended = get_effective_company_modules(
            base_modules,
            {"subscription_status": "suspended", "plan_name": "base"},
            {"trial", "active", "past_due"},
            "base",
            {"base": {"tz_pr_checker", "testcase_generator"}},
        )

        assert effective["tz_pr_checker"] is True
        assert effective["testcase_generator"] is True
        assert effective["monitoring"] is True
        assert suspended["tz_pr_checker"] is False


class TestAuthRepositoryBackendRefactor:
    def test_auth_repository_adapter_switches_postgres_placeholders(self):
        from utils.auth.repository_common import prepare_query

        class FakePostgresConnection:
            pass

        FakePostgresConnection.__module__ = "psycopg.connection"

        query = "SELECT * FROM users WHERE id = ? AND company_id = ?"
        assert prepare_query(FakePostgresConnection(), query) == (
            "SELECT * FROM users WHERE id = %s AND company_id = %s"
        )

    def test_auth_init_still_runs_with_backend_aware_connection(self):
        from utils.auth.auth_db import init_auth_db, get_global_setting

        init_auth_db()
        assert isinstance(get_global_setting("missing_key", ""), str)

    def test_auth_bootstrap_legacy_detector_recognizes_current_schema(self):
        from utils.auth.auth_bootstrap import is_old_auth_schema
        from utils.auth.auth_db import init_auth_db

        init_auth_db()
        conn = connect_auth_sqlite()
        assert is_old_auth_schema(conn) is False
        conn.close()

    def test_sales_ready_module_scope_is_limited_to_three_modules(self):
        from utils.auth.auth_db import SALES_READY_MODULES, DEFERRED_MODULES

        assert SALES_READY_MODULES == {"tz_pr_checker", "testcase_generator", "monitoring"}
        assert {"bug_analyzer", "statistics", "sprint_report"}.issubset(DEFERRED_MODULES)


class TestUiPreferencesFoundation:
    def test_i18n_supports_three_locales(self):
        from config.ui_foundation import SUPPORTED_LOCALES, TRANSLATIONS

        assert set(SUPPORTED_LOCALES) == {"uz", "en", "ru"}
        assert TRANSLATIONS["en"]["language"] == "Language"
        assert TRANSLATIONS["ru"]["appearance"] == "Тема"

    def test_theme_options_are_limited_to_dark_and_light(self):
        from config.ui_foundation import THEME_OPTIONS

        assert THEME_OPTIONS == ("dark", "light")


class TestPostgresPreparationRefactor:
    def test_database_runtime_exposes_backend_config(self):
        from utils.database.runtime import get_database_backend_config

        config = get_database_backend_config()

        assert config.backend in {"sqlite", "postgres"}
        assert config.auth_sqlite_path.endswith("auth.db")
        assert config.processing_sqlite_path.endswith("processing.db")
        assert isinstance(config.postgres_driver_available, bool)

    def test_postgres_schema_artifact_exists_with_core_tables(self):
        schema_path = Path("database/postgresql/001_initial_schema.sql")
        content = schema_path.read_text()

        assert schema_path.exists()
        assert "CREATE TABLE IF NOT EXISTS companies" in content
        assert "CREATE TABLE IF NOT EXISTS users" in content
        assert "CREATE TABLE IF NOT EXISTS company_subscriptions" in content
        assert "CREATE TABLE IF NOT EXISTS company_settings" in content
        assert "CREATE TABLE IF NOT EXISTS platform_admins" in content
        assert "CREATE TABLE IF NOT EXISTS user_password_reset_tokens" in content
        assert "CREATE TABLE IF NOT EXISTS task_processing" in content

    def test_sqlite_export_script_writes_manifest(self, tmp_path):
        from utils.tools.export_sqlite_for_postgres import export_sqlite_for_postgres

        manifest = export_sqlite_for_postgres(tmp_path)

        manifest_path = tmp_path / "manifest.json"
        assert manifest_path.exists()
        assert "files" in manifest
        assert any(item["table"] == "companies" for item in manifest["files"])
        assert any(item["table"] == "platform_admins" for item in manifest["files"])
        assert any(item["table"] == "login_audit_logs" for item in manifest["files"])
        assert any(item["table"] == "user_password_reset_tokens" for item in manifest["files"])
        assert any(item["table"] == "task_processing" for item in manifest["files"])

    def test_postgres_import_sql_generator_creates_sql_file(self, tmp_path):
        from utils.auth.auth_db import create_company, create_user, create_password_reset_token, save_company_settings
        from utils.tools.export_sqlite_for_postgres import export_sqlite_for_postgres
        from utils.tools.generate_postgres_import_sql import generate_postgres_import_sql

        company = create_company(f"exp{uuid4().hex[:8]}", "Export Company")
        assert company is not None
        assert save_company_settings(company["id"], {"webhook_project_keys": "EXPKEY"}) is True
        user, err = create_user(company["id"], f"user{uuid4().hex[:6]}", "secret123", role="user")
        assert err is None
        assert user is not None
        assert create_password_reset_token(user["id"]) is not None

        export_dir = tmp_path / "export"
        output_file = tmp_path / "import" / "import.sql"
        export_sqlite_for_postgres(export_dir)
        path = generate_postgres_import_sql(export_dir, output_file)
        content = path.read_text()

        assert path.exists()
        assert "BEGIN;" in content
        assert "TRUNCATE TABLE" in content
        assert "INSERT INTO companies" in content
        assert "INSERT INTO company_settings" in content
        assert "INSERT INTO platform_admins" in content
        assert "INSERT INTO user_password_reset_tokens" in content
        assert "INSERT INTO task_processing" in content
        assert "SELECT setval(" in content
        assert "COMMIT;" in content
        assert "TRUE" in content or "FALSE" in content

    def test_postgres_import_sql_generator_converts_blank_dates_to_null(self):
        from utils.tools.generate_postgres_import_sql import _build_insert_statement

        sql = _build_insert_statement(
            "company_subscriptions",
            {
                "company_id": 1,
                "plan_name": "base",
                "subscription_status": "active",
                "billing_mode": "manual",
                "billing_start_date": "",
                "billing_end_date": "",
                "next_payment_date": "",
                "last_payment_date": "",
                "last_payment_note": "",
                "created_at": "2026-05-03 21:00:00",
                "updated_at": "2026-05-03 21:00:00",
            },
        )

        assert "VALUES (1, 'base', 'active', 'manual', NULL, NULL, NULL, NULL" in sql

    def test_postgres_import_sql_generator_backfills_orphan_task_company_ids(self):
        from utils.tools.generate_postgres_import_sql import (
            _build_insert_statement,
            _build_migration_context,
        )

        payloads = {
            "auth__companies.json": {
                "rows": [
                    {
                        "id": 10,
                        "company_code": "pytestco",
                        "company_name": "Pytest Company",
                        "seat_limit": 1,
                        "is_active": 1,
                        "created_at": "2026-05-03T12:30:58",
                    }
                ]
            },
            "auth__company_subscriptions.json": {"rows": []},
            "processing__task_processing.json": {
                "rows": [
                    {
                        "task_id": "DEV-7172",
                        "company_id": None,
                        "task_status": "none",
                        "created_at": "2026-04-30T18:17:20.756794",
                        "updated_at": "2026-04-30T18:17:20.756781",
                    }
                ]
            },
        }

        context = _build_migration_context(payloads)
        sql = _build_insert_statement("task_processing", payloads["processing__task_processing.json"]["rows"][0], context)

        assert context["legacy_company_id"] == 11
        assert "'legacy-import'" in _build_insert_statement("companies", payloads["auth__companies.json"]["rows"][-1], context)
        assert "VALUES ('DEV-7172', 11," in sql

    def test_postgres_import_sql_generator_nulls_orphan_login_audit_references(self):
        from utils.tools.generate_postgres_import_sql import (
            _build_insert_statement,
            _build_migration_context,
        )

        payloads = {
            "auth__companies.json": {"rows": [{"id": 1, "company_code": "acme", "company_name": "Acme"}]},
            "auth__users.json": {"rows": [{"id": 10, "company_id": 1, "username": "user@acme"}]},
            "auth__company_subscriptions.json": {"rows": []},
            "processing__task_processing.json": {"rows": []},
        }

        context = _build_migration_context(payloads)
        sql = _build_insert_statement(
            "login_audit_logs",
            {
                "id": 5,
                "identifier": "bad-ref@example.com",
                "user_id": 123,
                "company_id": 456,
                "role": "user",
                "success": 0,
                "reason": "invalid_user_password",
                "created_at": "2026-05-04T12:00:00",
            },
            context,
        )

        assert "VALUES (5, 'bad-ref@example.com', NULL, NULL, 'user', FALSE" in sql

    def test_postgres_migration_bundle_validator_passes_for_generated_artifacts(self, tmp_path):
        from utils.tools.export_sqlite_for_postgres import export_sqlite_for_postgres
        from utils.tools.generate_postgres_import_sql import generate_postgres_import_sql
        from utils.tools.validate_postgres_migration_bundle import validate_postgres_migration_bundle

        export_dir = tmp_path / "export"
        import_file = tmp_path / "import" / "import.sql"
        schema_file = Path("database/postgresql/001_initial_schema.sql")

        export_sqlite_for_postgres(export_dir)
        generate_postgres_import_sql(export_dir, import_file)
        result = validate_postgres_migration_bundle(schema_file, export_dir, import_file)

        assert result["ok"] is True
        assert result["errors"] == []

    def test_reencrypt_credentials_utility_rotates_old_key_rows(self, monkeypatch):
        from utils.auth.auth_db import (
            create_company,
            create_user,
            save_user_credentials,
            save_company_settings,
        )
        from utils.tools.reencrypt_credentials import reencrypt_stored_credentials
        from utils.auth.credential_crypto import needs_reencryption

        monkeypatch.setenv("APP_CREDENTIALS_MASTER_KEY", "utility-old-key")
        monkeypatch.delenv("APP_CREDENTIALS_OLD_MASTER_KEYS", raising=False)

        company = create_company(f"rot{uuid4().hex[:8]}", "Rotation Utility Co")
        assert company is not None
        user, err = create_user(company["id"], f"user{uuid4().hex[:6]}", "secret123", role="user")
        assert err is None
        assert user is not None

        assert save_user_credentials(user["id"], {
            "jira_token": "user-old-token",
            "github_token": "user-old-github",
        }) is True
        assert save_company_settings(company["id"], {
            "jira_token": "company-old-token",
            "github_token": "company-old-github",
        }) is True

        monkeypatch.setenv("APP_CREDENTIALS_MASTER_KEY", "utility-new-key")
        monkeypatch.setenv("APP_CREDENTIALS_OLD_MASTER_KEYS", "utility-old-key")

        dry_run = reencrypt_stored_credentials(apply=False)
        assert dry_run["user_credentials"]["updated"] >= 1
        assert dry_run["company_settings"]["updated"] >= 1

        applied = reencrypt_stored_credentials(apply=True)
        assert applied["user_credentials"]["updated"] >= 1
        assert applied["company_settings"]["updated"] >= 1

        conn = connect_auth_sqlite()
        row = conn.execute(
            "SELECT jira_token FROM user_credentials WHERE user_id = ?",
            (user["id"],),
        ).fetchone()
        company_row = conn.execute(
            "SELECT jira_token FROM company_settings WHERE company_id = ?",
            (company["id"],),
        ).fetchone()
        conn.close()

        assert row is not None
        assert company_row is not None
        assert needs_reencryption(row["jira_token"]) is False
        assert needs_reencryption(company_row["jira_token"]) is False

    def test_postgres_runtime_reports_missing_driver_cleanly(self):
        from utils.database import runtime

        original_dsn = runtime.POSTGRES_DSN
        runtime.POSTGRES_DSN = ""
        try:
            if runtime.is_postgres_driver_available():
                try:
                    runtime.connect_postgres()
                    assert False, "DSN yo'q holatda xato bo'lishi kerak edi"
                except RuntimeError as exc:
                    assert "dsn" in str(exc).lower()
            else:
                try:
                    runtime.connect_postgres()
                    assert False, "Driver yo'q holatda xato bo'lishi kerak edi"
                except RuntimeError as exc:
                    assert "driver" in str(exc).lower()
        finally:
            runtime.POSTGRES_DSN = original_dsn

    def test_backend_aware_connectors_delegate_to_postgres_when_enabled(self, monkeypatch):
        from utils.database import runtime

        calls = []

        def fake_connect_postgres(*, row_factory=False):
            calls.append({"row_factory": row_factory})
            return {"row_factory": row_factory}

        original_backend = runtime.DB_BACKEND
        monkeypatch.setattr(runtime, "connect_postgres", fake_connect_postgres)
        runtime.DB_BACKEND = "postgres"
        try:
            auth_conn = runtime.connect_auth_db(timeout=9.5)
            processing_conn = runtime.connect_processing_db(timeout=4.0, row_factory=True)
        finally:
            runtime.DB_BACKEND = original_backend

        assert auth_conn == {"row_factory": True}
        assert processing_conn == {"row_factory": True}
        assert calls == [{"row_factory": True}, {"row_factory": True}]

    def test_backend_aware_connectors_keep_sqlite_path_when_backend_is_sqlite(self, monkeypatch):
        from utils.database import runtime

        calls = []

        def fake_connect_auth_sqlite(timeout=30.0):
            calls.append(("auth", timeout))
            return {"kind": "auth-sqlite", "timeout": timeout}

        def fake_connect_processing_sqlite(timeout=30.0, *, row_factory=False):
            calls.append(("processing", timeout, row_factory))
            return {"kind": "processing-sqlite", "timeout": timeout, "row_factory": row_factory}

        original_backend = runtime.DB_BACKEND
        monkeypatch.setattr(runtime, "connect_auth_sqlite", fake_connect_auth_sqlite)
        monkeypatch.setattr(runtime, "connect_processing_sqlite", fake_connect_processing_sqlite)
        runtime.DB_BACKEND = "sqlite"
        try:
            auth_conn = runtime.connect_auth_db(timeout=12.0)
            processing_conn = runtime.connect_processing_db(timeout=7.0, row_factory=True)
        finally:
            runtime.DB_BACKEND = original_backend

        assert auth_conn == {"kind": "auth-sqlite", "timeout": 12.0}
        assert processing_conn == {"kind": "processing-sqlite", "timeout": 7.0, "row_factory": True}
        assert calls == [("auth", 12.0), ("processing", 7.0, True)]

    def test_postgres_readiness_checker_reports_missing_dsn(self, tmp_path):
        from utils.tools.export_sqlite_for_postgres import export_sqlite_for_postgres
        from utils.tools.generate_postgres_import_sql import generate_postgres_import_sql
        from utils.tools.check_postgres_ready import check_postgres_ready
        import utils.database.runtime as runtime

        export_dir = tmp_path / "export"
        import_file = tmp_path / "import" / "import.sql"
        schema_file = Path("database/postgresql/001_initial_schema.sql")

        export_sqlite_for_postgres(export_dir)
        generate_postgres_import_sql(export_dir, import_file)

        original_dsn = runtime.POSTGRES_DSN
        runtime.POSTGRES_DSN = ""
        try:
            result = check_postgres_ready(schema_file, export_dir, import_file)
        finally:
            runtime.POSTGRES_DSN = original_dsn

        assert result["checks"]["driver_available"] is True
        assert result["checks"]["schema_file_exists"] is True
        assert result["checks"]["export_manifest_exists"] is True
        assert result["checks"]["import_sql_exists"] is True
        assert result["checks"]["dsn_configured"] is False
        assert "dsn_configured" in result["missing"]

    def test_postgres_migration_runner_applies_schema_before_import(self, monkeypatch, tmp_path):
        from utils.tools.run_postgres_migration_bundle import run_postgres_migration_bundle
        import utils.tools.run_postgres_migration_bundle as runner

        calls = []
        schema_file = tmp_path / "schema.sql"
        import_file = tmp_path / "import.sql"
        schema_file.write_text("SELECT 1;")
        import_file.write_text("SELECT 2;")

        class FakeConfig:
            postgres_dsn = "postgresql://demo"

        monkeypatch.setattr(runner, "get_database_backend_config", lambda: FakeConfig())
        monkeypatch.setattr(runner, "run_postgres_sql_file", lambda path: calls.append(str(path)))

        result = run_postgres_migration_bundle(schema_file, import_file)

        assert calls == [str(schema_file), str(import_file)]
        assert result["import_applied"] is True


class TestTenantIsolationRegressions:
    def test_project_key_routing_ignores_inactive_company(self):
        from utils.auth.auth_db import (
            create_company,
            save_company_settings,
            update_company_status,
            get_company_by_project_key,
        )

        company = create_company(f"prj{uuid4().hex[:8]}", "Project Key Company")
        assert company is not None
        assert save_company_settings(company["id"], {"webhook_project_keys": "TENANTX"}) is True

        routed = get_company_by_project_key("tenantx")
        assert routed is not None
        assert routed["id"] == company["id"]

        assert update_company_status(company["id"], False) is True
        assert get_company_by_project_key("TENANTX") is None
