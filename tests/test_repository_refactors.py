import pytest


@pytest.mark.no_db
class TestPostgresRuntimeRefactors:
    def test_runtime_config_is_postgres_only(self):
        from utils.database.runtime import get_database_backend_config, get_db_backend

        config = get_database_backend_config()

        assert get_db_backend() == "postgres"
        assert config.backend == "postgres"
        assert hasattr(config, "postgres_dsn")
        assert not hasattr(config, "auth_file_path")
        assert not hasattr(config, "processing_file_path")

    def test_database_repository_common_prepares_postgres_placeholders(self):
        from utils.database.repository_common import prepare_query, uses_postgres_params

        assert uses_postgres_params(object()) is True
        assert prepare_query(object(), "SELECT * FROM task_processing WHERE task_id = ?") == (
            "SELECT * FROM task_processing WHERE task_id = %s"
        )

    def test_auth_repository_common_prepares_postgres_placeholders(self):
        from utils.auth.repository_common import prepare_query, uses_postgres_params

        assert uses_postgres_params(object()) is True
        assert prepare_query(object(), "SELECT * FROM users WHERE id = ?") == (
            "SELECT * FROM users WHERE id = %s"
        )

    def test_postgres_schema_validator_reports_required_tables(self):
        from utils.tools.validate_postgres_schema import validate_postgres_schema

        result = validate_postgres_schema("database/postgresql/001_initial_schema.sql")

        assert result["ok"] is True
        assert "companies" in result["schema_tables"]
        assert "task_processing" in result["schema_tables"]
