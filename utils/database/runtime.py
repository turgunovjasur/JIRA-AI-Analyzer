"""
PostgreSQL runtime helpers.

Ulanishlar connection pool orqali boshqariladi (psycopg_pool). Repository'lar
hech qanday o'zgarishsiz ishlaydi: `conn = connect_*(...)` pooldan ulanish oladi,
`conn.close()` esa ulanishni poolga QAYTARADI (haqiqatan yopmaydi). Agar repo
xato tufayli `close()` chaqirmasa, proxy `__del__` (GC) orqali ulanish baribir
poolga qaytariladi — bu connection leak'ning oldini oladi.
"""
import importlib
import os
import threading
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
    # POSTGRES_DSN modul-darajada bo'lsa (test monkeypatch) — o'shani ishlatamiz.
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


# ============================================================================
# CONNECTION POOL
# ============================================================================

_pool = None
_pool_dsn = None
_pool_lock = threading.Lock()


def _pool_env_int(name: str, default: int) -> int:
    try:
        value = int((os.getenv(name) or "").strip() or default)
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


def _build_pool(dsn: str):
    from psycopg_pool import ConnectionPool

    min_size = _pool_env_int("APP_DB_POOL_MIN_SIZE", 1)
    max_size = _pool_env_int("APP_DB_POOL_MAX_SIZE", 10)
    if max_size < min_size:
        max_size = min_size
    connect_timeout = _pool_env_int("APP_DB_CONNECT_TIMEOUT", 30)

    pool = ConnectionPool(
        conninfo=dsn,
        min_size=min_size,
        max_size=max_size,
        # Bo'sh ulanish so'ralganda kutish standart timeouti (getconn override qiladi).
        timeout=float(_pool_env_int("APP_DB_POOL_TIMEOUT", 30)),
        # Uzoq turgan ulanishlarni almashtirish (stale connection oldini olish).
        max_idle=float(_pool_env_int("APP_DB_POOL_MAX_IDLE", 300)),
        max_lifetime=float(_pool_env_int("APP_DB_POOL_MAX_LIFETIME", 3600)),
        # Har checkout'da ulanish tirikligini tekshirish.
        check=ConnectionPool.check_connection,
        kwargs={"connect_timeout": connect_timeout},
        name="jira-ai-db",
        open=False,
    )
    pool.open()
    return pool


def _get_pool():
    """DSN bo'yicha keshlangan global pool. DSN o'zgarsa (test) qayta quriladi."""
    global _pool, _pool_dsn
    _require_postgres_driver()
    dsn = get_postgres_dsn()
    if not dsn:
        raise RuntimeError("APP_POSTGRES_DSN bo'sh. PostgreSQL ulanish satrini kiriting.")

    if _pool is not None and _pool_dsn == dsn:
        return _pool

    with _pool_lock:
        if _pool is not None and _pool_dsn == dsn:
            return _pool
        # DSN o'zgargan bo'lsa eskisini yopamiz (asosan testlarda).
        if _pool is not None:
            try:
                _pool.close()
            except Exception:
                pass
        _pool = _build_pool(dsn)
        _pool_dsn = dsn
        return _pool


def close_pool() -> None:
    """Pool'ni yopish (shutdown / test cleanup)."""
    global _pool, _pool_dsn
    with _pool_lock:
        if _pool is not None:
            try:
                _pool.close()
            except Exception:
                pass
        _pool = None
        _pool_dsn = None


class _PooledConnection:
    """Pooldan olingan ulanishning ingichka proxy'si.

    `close()` ulanishni poolga qaytaradi (yopmaydi). Boshqa hamma narsa
    (cursor/commit/rollback/execute/attribute) asl ulanishga delegatsiya
    qilinadi. `__del__` — leak himoya to'ri (repo close'ni unutsa).
    """

    __slots__ = ("_pool", "_conn", "_returned")

    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn
        self._returned = False

    def __getattr__(self, name):
        # __slots__ atributlari o'rnatilmagan paytda rekursiyani oldini olamiz.
        if name in ("_pool", "_conn", "_returned"):
            raise AttributeError(name)
        return getattr(self._conn, name)

    def _return(self) -> None:
        if self._returned:
            return
        self._returned = True
        conn = self._conn
        # Ochiq tranzaksiyani tozalaymiz (read tx yoki commit qilinmagan write)
        # — keyingi foydalanuvchi toza ulanish olishi uchun.
        try:
            if not conn.closed:
                conn.rollback()
        except Exception:
            pass
        try:
            self._pool.putconn(conn)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

    def close(self) -> None:
        self._return()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            try:
                self._conn.commit()
            except Exception:
                pass
        self._return()
        return False

    def __del__(self):
        try:
            self._return()
        except Exception:
            pass


def connect_postgres(*, row_factory: bool = False, timeout: float = 30.0):
    pool = _get_pool()
    conn = pool.getconn(timeout=max(1.0, float(timeout or 30)))
    try:
        if row_factory:
            from psycopg.rows import dict_row

            conn.row_factory = dict_row
        else:
            from psycopg.rows import tuple_row

            conn.row_factory = tuple_row
    except Exception:
        # row_factory o'rnatib bo'lmasa ulanishni qaytarib, xatoni ko'taramiz.
        try:
            pool.putconn(conn)
        except Exception:
            pass
        raise
    return _PooledConnection(pool, conn)


def connect_auth_db(timeout: float = 30.0):
    return connect_postgres(row_factory=True, timeout=timeout)


def connect_processing_db(timeout: float = 30.0, *, row_factory: bool = False):
    return connect_postgres(row_factory=row_factory, timeout=timeout)
