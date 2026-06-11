"""
PostgreSQL runtime helpers.
"""
import importlib
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DB_BACKEND = "postgres"
POSTGRES_DSN = (os.getenv("APP_POSTGRES_DSN") or "").strip()


def is_postgres_backend() -> bool:
    return True


def get_db_backend() -> str:
    return DB_BACKEND


def get_postgres_dsn() -> str:
    return POSTGRES_DSN


@dataclass(frozen=True)
class DatabaseBackendConfig:
    backend: str
    postgres_dsn: str
    postgres_driver_available: bool


def get_database_backend_config() -> DatabaseBackendConfig:
    return DatabaseBackendConfig(
        backend=get_db_backend(),
        postgres_dsn=get_postgres_dsn(),
        postgres_driver_available=is_postgres_driver_available(),
    )


def is_postgres_driver_available() -> bool:
    return importlib.util.find_spec("psycopg") is not None


def _require_postgres_driver() -> None:
    if not is_postgres_driver_available():
        raise RuntimeError(
            "PostgreSQL driver topilmadi. `psycopg` o'rnatilgandan keyin runtime ishlaydi."
        )


def connect_postgres(*, row_factory: bool = False, timeout: float = 30.0):
    _require_postgres_driver()
    dsn = get_postgres_dsn()
    if not dsn:
        raise RuntimeError("APP_POSTGRES_DSN bo'sh. PostgreSQL ulanish satrini kiriting.")

    import psycopg

    kwargs = {"connect_timeout": max(1, int(timeout or 30))}
    if row_factory:
        from psycopg.rows import dict_row

        kwargs["row_factory"] = dict_row
    return psycopg.connect(dsn, **kwargs)


def connect_auth_db(timeout: float = 30.0):
    return connect_postgres(row_factory=True, timeout=timeout)


def connect_processing_db(timeout: float = 30.0, *, row_factory: bool = False):
    return connect_postgres(row_factory=row_factory, timeout=timeout)
