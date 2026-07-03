"""
Test Data Generator

Monitoring dashboard'ni test qilish uchun fake task ma'lumotlari yaratish.

Author: JASUR TURGUNOV
Version: 1.0
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
from datetime import datetime, timedelta

from utils.database.task_db import (
    increment_return_count,
    mark_completed,
    mark_error,
    mark_progressing,
    mark_returned,
    set_service1_done,
    set_service1_error,
    set_service2_done,
    set_service2_error,
    set_skip_detected,
)


def generate_test_tasks(count: int = 20):
    """
    Test uchun fake tasklar yaratish

    Args:
        count: Yaratilgan tasklar soni (default: 20)
    """
    print(f"🔧 {count} ta test task yaratilmoqda...")

    statuses = ['completed', 'progressing', 'returned', 'error']
    task_types = ['DEV', 'BUG', 'STORY']

    for i in range(1, count + 1):
        task_key = f"{random.choice(task_types)}-{1000 + i}"
        jira_status = "Ready to Test"
        now = datetime.now() - timedelta(hours=random.randint(0, 48))

        # Random status
        status = random.choice(statuses)

        # Mark progressing (har doim)
        mark_progressing(task_key, jira_status, now)

        # Service1 (TZ-PR)
        if random.random() > 0.2:  # 80% success
            compliance_score = random.randint(50, 100)
            set_service1_done(task_key, compliance_score)
        else:
            set_service1_error(task_key, "TZ topilmadi yoki GitHub PR yo'q")
            continue  # Service2 ishlamaydi

        # Service2 (Testcase)
        if random.random() > 0.1:  # 90% success
            set_service2_done(task_key)
        else:
            set_service2_error(task_key, "Test case generation failed")

        # Final status
        if status == 'completed':
            mark_completed(task_key)
        elif status == 'returned':
            mark_returned(task_key)
            # Return count
            return_times = random.randint(1, 3)
            for _ in range(return_times):
                increment_return_count(task_key)
        elif status == 'error':
            mark_error(task_key, "Kutilmagan xatolik")
        # progressing → hech narsa qilmaymiz

        # Skip detected (5% ehtimol)
        if random.random() < 0.05:
            set_skip_detected(task_key)

        print(f"  ✅ {task_key} → {status}")

    print(f"\n🎉 {count} ta test task yaratildi!")


def clear_all_tasks():
    """Barcha tasklarni o'chirish"""
    from utils.database.runtime import connect_processing_db

    conn = connect_processing_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM task_processing")
    conn.commit()
    count = cursor.rowcount
    conn.close()

    print(f"🗑️  {count} ta task o'chirildi")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        clear_all_tasks()
    else:
        count = int(sys.argv[1]) if len(sys.argv) > 1 else 20
        generate_test_tasks(count)
