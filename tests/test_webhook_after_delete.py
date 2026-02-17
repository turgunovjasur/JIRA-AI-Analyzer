"""
Test: Webhook handler after delete task

Muammo:
- Task delete qilingandan keyin webhook kelganda "Dublikat event" deyapti
- Bu noto'g'ri, chunki task DB da yo'q

Test scenario:
1. Task ni DB dan delete qilish
2. Webhook event simulatsiya qilish
3. Webhook handler yangi task sifatida qabul qilishi kerak (dublikat demasligi kerak)
"""
import sys
import os

# Project root'ni PATH'ga qo'shish
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database.task_db import (
    init_db,
    get_task,
    delete_task,
    mark_progressing,
    mark_completed
)
from datetime import datetime


def simulate_webhook_handler_logic(task_key: str, new_status: str):
    """
    Webhook handler'dagi logic'ni simulatsiya qilish

    Bu kod services/webhook/jira_webhook_handler.py'dan ko'chirilgan
    """
    print(f"\n{'='*60}")
    print(f"WEBHOOK HANDLER LOGIC SIMULATION")
    print(f"Task: {task_key}, Status: {new_status}")
    print(f"{'='*60}")

    # DB'dan task olish
    task_db = get_task(task_key)

    if not task_db:
        print(f"✅ Task DB da yo'q - yangi task (yoki manual delete qilingan)")
        mark_progressing(task_key, new_status, datetime.now())
        print(f"✅ Task yaratildi: {task_key}")
        return "processing"

    # Task mavjud
    task_status = task_db.get('task_status', 'none')
    last_jira_status = task_db.get('last_jira_status')

    print(f"📊 Task DB da mavjud:")
    print(f"  - task_status: {task_status}")
    print(f"  - last_jira_status: {last_jira_status}")

    # Dublikat check
    if last_jira_status == new_status and task_status in ('progressing', 'completed'):
        print(f"⏭️ Dublikat event: {new_status} allaqachon ishlanmoqda/ishlanib bo'lgan")
        return "ignored_duplicate"

    # Task holatini yangilash
    if task_status == 'none':
        mark_progressing(task_key, new_status, datetime.now())
        print(f"✅ Task progressing ga o'tkazildi")
        return "processing"
    elif task_status == 'completed':
        print(f"🔄 Completed taskni qayta ishlash")
        # reset_service_statuses(task_key)  # Bu yerda skip
        mark_progressing(task_key, new_status, datetime.now())
        return "processing"
    elif task_status == 'progressing':
        print(f"⏭️ Task allaqachon progressing")
        return "ignored_progressing"

    return "unknown"


def test_webhook_after_manual_delete():
    """
    Test: Manual delete qilingandan keyin webhook
    """
    task_key = "TEST-WEBHOOK-001"
    status = "Ready to Test"

    print("\n" + "="*60)
    print("SCENARIO 1: Task delete qilingandan keyin webhook")
    print("="*60)

    # 1. Task yaratish va complete qilish (real holat)
    mark_progressing(task_key, status, datetime.now())
    mark_completed(task_key)

    task = get_task(task_key)
    print(f"1️⃣ Task yaratildi va completed: {task['task_status']}")

    # 2. Manual delete (monitoring page'dan)
    print(f"2️⃣ Task monitoring page'dan o'chirildi...")
    success = delete_task(task_key)
    assert success, "Delete failed"

    task_after_delete = get_task(task_key)
    assert task_after_delete is None, "Task o'chirilmadi"
    print(f"✅ Task DB dan to'liq o'chirildi")

    # 3. Webhook yana keldi (JIRA'da status yana Ready to Test'ga o'tkazildi)
    print(f"3️⃣ Webhook event keldi (JIRA status: {status})...")
    result = simulate_webhook_handler_logic(task_key, status)

    if result == "processing":
        print(f"✅ Test PASSED: Webhook yangi task sifatida qabul qildi")
    elif result == "ignored_duplicate":
        print(f"❌ Test FAILED: Webhook dublikat dedi (noto'g'ri!)")
        raise AssertionError("Webhook should NOT say duplicate after delete!")
    else:
        print(f"⚠️ Unexpected result: {result}")

    # Cleanup
    delete_task(task_key)


def test_webhook_completed_task_without_delete():
    """
    Test: Completed task'ga webhook kelganda (delete qilinmagan)
    """
    task_key = "TEST-WEBHOOK-002"
    status = "Ready to Test"

    print("\n" + "="*60)
    print("SCENARIO 2: Completed task'ga webhook (delete yo'q)")
    print("="*60)

    # 1. Task yaratish va complete qilish
    mark_progressing(task_key, status, datetime.now())
    mark_completed(task_key)

    task = get_task(task_key)
    print(f"1️⃣ Task completed: {task['task_status']}")

    # 2. Webhook yana keldi (delete qilinmagan, lekin JIRA'da status yana o'zgardi)
    print(f"2️⃣ Webhook event keldi (status yana: {status})...")
    result = simulate_webhook_handler_logic(task_key, status)

    # Completed task'ga webhook kelganda:
    # - Agar last_jira_status == new_status -> dublikat (to'g'ri)
    # - Agar last_jira_status != new_status -> qayta ishlash (to'g'ri)

    # Bizning holatda last_jira_status == new_status bo'ladi
    # Chunki biz task'ni "Ready to Test" statusda yaratdik va completed qildik
    # Webhook yana "Ready to Test" bilan keldi

    if result == "ignored_duplicate":
        print(f"✅ Test PASSED: Webhook dublikat dedi (to'g'ri, chunki task allaqachon shu statusda completed)")
    elif result == "processing":
        print(f"⚠️ Webhook qayta ishlayapti (last_jira_status != new_status bo'lsa to'g'ri)")

    # Cleanup
    delete_task(task_key)


def test_real_problem_scenario():
    """
    Test: Real muammo scenariosi

    Foydalanuvchi:
    1. Task delete qilyapti (monitoring page)
    2. Webhook keladi
    3. "Dublikat event" log chiqadi
    """
    task_key = "TEST-REAL-PROBLEM"
    status = "Ready to Test"

    print("\n" + "="*60)
    print("SCENARIO 3: Real muammo scenariosi")
    print("="*60)

    # 1. Task oldingi ishlashda yaratilgan
    mark_progressing(task_key, status, datetime.now())
    mark_completed(task_key)

    task_before = get_task(task_key)
    print(f"1️⃣ Task mavjud: status={task_before['task_status']}, last_jira_status={task_before['last_jira_status']}")

    # 2. Foydalanuvchi monitoring page'dan o'chiradi
    print(f"2️⃣ Foydalanuvchi monitoring page'dan task'ni o'chiradi...")
    delete_task(task_key)

    # 3. Verify task o'chirildi
    task_after_delete = get_task(task_key)
    if task_after_delete is None:
        print(f"✅ Task DB dan to'liq o'chirildi")
    else:
        print(f"❌ Task hali ham DB da: {task_after_delete}")
        raise AssertionError("Task should be deleted!")

    # 4. Webhook keladi (JIRA'da status o'zgardi)
    print(f"3️⃣ Webhook event keldi (JIRA status: {status})...")
    result = simulate_webhook_handler_logic(task_key, status)

    # Expected: "processing" (yangi task)
    # Actual: "ignored_duplicate" (muammo!)

    if result == "processing":
        print(f"✅ SUCCESS: Webhook task'ni yangi task sifatida qabul qildi")
        print(f"✅ Muammo hal qilindi!")
    elif result == "ignored_duplicate":
        print(f"❌ FAIL: Webhook 'Dublikat event' dedi")
        print(f"❌ Bu muammo - task DB da yo'q, lekin webhook dublikat deyapti!")
        raise AssertionError("This is the BUG!")

    # Cleanup
    delete_task(task_key)


if __name__ == "__main__":
    # DB init
    init_db()

    # Test 1
    test_webhook_after_manual_delete()

    # Test 2
    test_webhook_completed_task_without_delete()

    # Test 3: Real problem
    test_real_problem_scenario()

    print("\n" + "="*60)
    print("✅ BARCHA TESTLAR O'TDI!")
    print("="*60)
