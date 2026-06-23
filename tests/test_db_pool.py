"""
P1: DB connection pool — qayta ishlatish va leak himoyasi testlari.

Bu testlar real PostgreSQL talab qiladi (conftest `APP_TEST_POSTGRES_DSN` bilan
sozlaydi; bo'lmasa skip). `no_db` marker QO'YILMAGAN — pool xulqi DB bilan
tekshiriladi.
"""
import gc

import utils.database.runtime as runtime


def test_pooled_close_returns_connection_for_reuse():
    # close() ulanishni poolga QAYTARADI (yopmaydi) — qayta ishlatiladi.
    conn = runtime.connect_processing_db(row_factory=True)
    cur = conn.cursor()
    cur.execute("SELECT 1 AS x")
    assert dict(cur.fetchone())["x"] == 1
    conn.close()

    # Yangi checkout ishlashi kerak (ulanish qayta ishlatiladi).
    conn2 = runtime.connect_processing_db()
    cur2 = conn2.cursor()
    cur2.execute("SELECT 2")
    assert cur2.fetchone()[0] == 2
    conn2.close()


def test_pooled_row_factory_per_checkout():
    # Bir xil pool, lekin har checkout o'z row_factory'sini oladi.
    dict_conn = runtime.connect_processing_db(row_factory=True)
    cur = dict_conn.cursor()
    cur.execute("SELECT 5 AS val")
    assert dict(cur.fetchone())["val"] == 5
    dict_conn.close()

    tuple_conn = runtime.connect_processing_db(row_factory=False)
    cur = tuple_conn.cursor()
    cur.execute("SELECT 7")
    row = cur.fetchone()
    assert row[0] == 7  # tuple row
    tuple_conn.close()


def test_pool_does_not_leak_when_close_is_skipped(monkeypatch):
    # Pattern A repo (try/finally yo'q): xato tufayli close() chaqirilmaydi.
    # Proxy __del__ (GC) ulanishni poolga qaytarishi kerak — aks holda
    # max_size dan keyin pool tugab, getconn timeout bilan osilib qolardi.
    monkeypatch.setenv("APP_DB_POOL_MAX_SIZE", "2")
    monkeypatch.setenv("APP_DB_POOL_MIN_SIZE", "1")
    monkeypatch.setenv("APP_DB_POOL_TIMEOUT", "3")  # leak bo'lsa 3s da yiqiladi (30s emas)
    runtime.close_pool()  # kichik konfiguratsiya bilan qayta qurish

    try:
        def leaky_repo_call():
            conn = runtime.connect_processing_db()
            conn.cursor().execute("SELECT 1")
            raise RuntimeError("repo xatosi — close() chaqirilmadi")

        # max_size (2) dan ko'p marta — leak bo'lsa 3-chi getconn osilib qolardi.
        for _ in range(6):
            try:
                leaky_repo_call()
            except RuntimeError:
                pass
            gc.collect()  # CPython refcount __del__ ni darhol chaqiradi; kafolat uchun

        # Pool hali ishlashi kerak (leak yo'q):
        conn = runtime.connect_processing_db()
        cur = conn.cursor()
        cur.execute("SELECT 42")
        assert cur.fetchone()[0] == 42
        conn.close()
    finally:
        runtime.close_pool()  # keyingi testlar normal konfiguratsiya bilan qayta qursin
