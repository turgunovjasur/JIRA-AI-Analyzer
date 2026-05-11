"""
Database runtime helpers.

Primary runtime backend endi `postgres`, `sqlite` esa legacy backup/import
qatlami sifatida saqlanadi.
"""
import os
import sqlite3
import importlib
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_BACKEND = (os.getenv("APP_DB_BACKEND") or "postgres").strip().lower()
POSTGRES_DSN = (os.getenv("APP_POSTGRES_DSN") or "").strip()
if DB_BACKEND != "postgres":
    raise RuntimeError(
        "SQLite backend o'chirilgan. Faqat APP_DB_BACKEND=postgres rejimi qo'llab-quvvatlanadi."
    )

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
AUTH_DB_PATH = os.path.join(DATA_DIR, "auth.db")
PROCESSING_DB_PATH = os.path.join(DATA_DIR, "processing.db")


def is_sqlite_backend() -> bool:
    return DB_BACKEND == "sqlite"


def is_postgres_backend() -> bool:
    return DB_BACKEND == "postgres"


def get_db_backend() -> str:
    return DB_BACKEND


def get_postgres_dsn() -> str:
    return POSTGRES_DSN


@dataclass(frozen=True)
class DatabaseBackendConfig:
    backend: str
    auth_sqlite_path: str
    processing_sqlite_path: str
    postgres_dsn: str
    postgres_driver_available: bool


def get_database_backend_config() -> DatabaseBackendConfig:
    return DatabaseBackendConfig(
        backend=get_db_backend(),
        auth_sqlite_path=get_auth_db_path(),
        processing_sqlite_path=get_processing_db_path(),
        postgres_dsn=get_postgres_dsn(),
        postgres_driver_available=is_postgres_driver_available(),
    )


def ensure_data_dir() -> None:
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def get_auth_db_path() -> str:
    return AUTH_DB_PATH


def get_processing_db_path() -> str:
    return PROCESSING_DB_PATH


def is_postgres_driver_available() -> bool:
    return importlib.util.find_spec("psycopg") is not None


def _require_postgres_driver() -> None:
    if not is_postgres_driver_available():
        raise RuntimeError(
            "PostgreSQL driver topilmadi. `psycopg` o'rnatilgandan keyin "
            "`APP_DB_BACKEND=postgres` rejimi ishlaydi."
        )


def connect_postgres(*, row_factory: bool = False):
    _require_postgres_driver()
    dsn = get_postgres_dsn()
    if not dsn:
        raise RuntimeError("APP_POSTGRES_DSN bo'sh. PostgreSQL ulanish satrini kiriting.")
    import psycopg
    if row_factory:
        from psycopg.rows import dict_row
        return psycopg.connect(dsn, row_factory=dict_row)
    return psycopg.connect(dsn)


def connect_auth_db(timeout: float = 30.0):
    return connect_postgres(row_factory=True)


def connect_processing_db(timeout: float = 30.0, *, row_factory: bool = False):
    return connect_postgres(row_factory=row_factory)


def connect_sqlite(db_path: str, timeout: float = 30.0, *, row_factory: bool = False) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=timeout)
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


def connect_auth_sqlite(timeout: float = 30.0) -> sqlite3.Connection:
    return connect_sqlite(get_auth_db_path(), timeout=timeout, row_factory=True)


def connect_processing_sqlite(timeout: float = 30.0, *, row_factory: bool = False) -> sqlite3.Connection:
    return connect_sqlite(get_processing_db_path(), timeout=timeout, row_factory=row_factory)


def is_sqlite_connection(conn) -> bool:
    return isinstance(conn, sqlite3.Connection)


def apply_sqlite_fresh_read_pragmas(conn) -> None:
    if not is_sqlite_connection(conn):
        return
    conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
    conn.execute("PRAGMA synchronous=FULL")


def checkpoint_sqlite_wal(conn, mode: str = "PASSIVE") -> None:
    if not is_sqlite_connection(conn):
        return
    clean_mode = (mode or "PASSIVE").strip().upper()
    conn.execute(f"PRAGMA wal_checkpoint({clean_mode})")
