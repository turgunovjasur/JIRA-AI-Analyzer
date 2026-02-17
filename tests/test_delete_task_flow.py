"""
Test: Task delete qilinganda webhook qayta ishlashi

Muammo:
- Monitoring page'dan task delete qilinyapti
- Lekin webhook yana kelganda "Dublikat event" yozilyapti
- Task qayta ishlanmayapti

Expected behavior:
- Task delete qilingandan keyin webhook kelganda task yangi task sifatida qayta ishlanishi kerak
"""
import sqlite3
import os
from datetime import datetime

from utils.database.task_db import (
    init_db,
    get_task,
    delete_task,
    mark_progressing,
    DB_FILE
)


def test_delete_task_then_webhook():
    """
    1. Task yaratish
    2. Task ni delete qilish
    3. get_task None qaytarishi kerak
    4. Webhook yana kelganda yangi task sifatida yaratilishi kerak
    """
    # Setup
    task_key = "TEST-DELETE-001"

    # 1. Task yaratish
    mark_progressing(task_key, "Ready to Test", datetime.now())

    task = get_task(task_key)
    assert task is not None, "Task yaratilmadi"
    assert task['task_id'] == task_key
    assert task['task_status'] == 'progressing'
    print(f"✅ Task yaratildi: {task_key}")

    # 2. Task ni delete qilish
    success = delete_task(task_key)
    assert success is True, "Delete failed"
    print(f"✅ Task o'chirildi: {task_key}")

    # 3. get_task None qaytarishi kerak
    task_after_delete = get_task(task_key)
    assert task_after_delete is None, f"Task hali ham mavjud: {task_after_delete}"
    print(f"✅ Task DB dan to'liq o'chirildi")

    # 4. DB'dan to'g'ridan-to'g'ri tekshirish
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT task_id FROM task_processing WHERE task_id = ?", (task_key,))
    row = cursor.fetchone()
    conn.close()

    assert row is None, f"Task DB da hali ham mavjud: {row}"
    print(f"✅ DB verification: Task yo'q")

    # 5. Webhook yana kelganda yangi task sifatida yaratilishi kerak
    mark_progressing(task_key, "Ready to Test", datetime.now())

    task_after_recreate = get_task(task_key)
    assert task_after_recreate is not None, "Task qayta yaratilmadi"
    assert task_after_recreate['task_status'] == 'progressing'
    assert task_after_recreate['return_count'] == 0, "Return count 0 bo'lishi kerak (yangi task)"
    print(f"✅ Task qayta yaratildi (yangi task sifatida)")

    # Cleanup
    delete_task(task_key)
    print(f"✅ Cleanup: {task_key}")


def test_multiple_delete_calls():
    """
    Bir necha marta delete qilish xavfsiz bo'lishi kerak
    """
    task_key = "TEST-DELETE-002"

    # Task yaratish
    mark_progressing(task_key, "Ready to Test", datetime.now())
    task = get_task(task_key)
    assert task is not None

    # 1-chi delete
    success1 = delete_task(task_key)
    assert success1 is True

    # 2-chi delete (task yo'q)
    success2 = delete_task(task_key)
    assert success2 is False, "Mavjud bo'lmagan taskni o'chirish False qaytarishi kerak"

    # 3-chi delete (hali ham safe)
    success3 = delete_task(task_key)
    assert success3 is False

    print(f"✅ Multiple delete calls safe")


def test_delete_with_concurrent_access():
    """
    Concurrent access (UI + webhook) holatida delete
    """
    task_key = "TEST-DELETE-003"

    # Task yaratish
    mark_progressing(task_key, "Ready to Test", datetime.now())

    # UI'dan delete
    success = delete_task(task_key)
    assert success is True

    # Webhook kelayotgan vaqtda get_task None qaytarishi kerak
    task = get_task(task_key)
    assert task is None

    # Webhook handler yangi task sifatida yaratadi
    mark_progressing(task_key, "Ready to Test", datetime.now())
    task_new = get_task(task_key)
    assert task_new is not None
    assert task_new['task_status'] == 'progressing'

    # Cleanup
    delete_task(task_key)
    print(f"✅ Concurrent access test passed")


if __name__ == "__main__":
    # DB init
    init_db()

    print("\n" + "="*60)
    print("TEST 1: Delete task then webhook")
    print("="*60)
    test_delete_task_then_webhook()

    print("\n" + "="*60)
    print("TEST 2: Multiple delete calls")
    print("="*60)
    test_multiple_delete_calls()

    print("\n" + "="*60)
    print("TEST 3: Delete with concurrent access")
    print("="*60)
    test_delete_with_concurrent_access()

    print("\n" + "="*60)
    print("✅ BARCHA TESTLAR O'TDI!")
    print("="*60)
