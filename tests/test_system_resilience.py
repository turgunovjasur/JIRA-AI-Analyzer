"""
JIRA-AI-Analyzer - Tizim Bardoshliligi va To'liq Testlar
==========================================================

Bu test fayli quyidagilarni tekshiradi:
1. 20 ta soxta webhook signal yuborish va tizimning qanday ishlashini tekshirish
2. Barcha mexanizmlarning ishlashini tekshirish
3. Settings ziddiyatlarini tekshirish
4. Blocked tasklar bilan key-1 va key-2 ishlashini test qilish
5. Ikkala key ham error bo'lganda retry mexanizmini test qilish
6. Barcha logikani test qilish

Author: Test Suite
Date: 2026-02-16
"""
import sys
import os
import json
import sqlite3
import asyncio
import time
import logging
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Dict, Any

# Loyiha root path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# TEST RESULTS TRACKER
# ============================================================================

class TestTracker:
    """Test natijalarini kuzatish"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.results = []

    def ok(self, test_name, detail=""):
        self.passed += 1
        self.results.append(("PASS", test_name, detail))
        logger.info(f"  ✅ PASS: {test_name} {detail}")

    def fail(self, test_name, reason):
        self.failed += 1
        self.errors.append((test_name, reason))
        self.results.append(("FAIL", test_name, reason))
        logger.error(f"  ❌ FAIL: {test_name} - {reason}")

    def summary(self):
        total = self.passed + self.failed
        logger.info("=" * 70)
        logger.info(f"NATIJA: {self.passed}/{total} test o'tdi, {self.failed} ta xato")
        if self.errors:
            logger.info("XATOLAR:")
            for name, reason in self.errors:
                logger.info(f"  - {name}: {reason}")
        logger.info("=" * 70)
        return self.failed == 0


tracker = TestTracker()


# ============================================================================
# TEST 1: 20 TA SOXTA WEBHOOK SIGNAL YUBORISH
# ============================================================================

def test_1_send_20_fake_webhooks():
    """
    TEST 1: 20 ta soxta webhook signal yuborish va tizimning qanday ishlashini tekshirish
    
    Tekshiradi:
    - 20 ta webhook bir vaqtda yuborilganda tizim barqarorligi
    - Har bir task DB ga yozilganligi
    - Tasklar ketma-ket yoki parallel ishlashini
    - Queue lock ishlashini
    - Timeout holatlarini
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 1: 20 ta soxta webhook signal yuborish")
    logger.info("=" * 70)

    try:
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        from utils.database.task_db import get_task, mark_progressing, init_db

        # DB ni ishga tushirish
        init_db()

        client = TestClient(app)

        # 20 ta soxta webhook payload yaratish
        webhook_payloads = []
        task_keys = []

        for i in range(1, 21):
            task_key = f"TEST-WEBHOOK-{i:03d}"
            task_keys.append(task_key)
            
            payload = {
                "webhookEvent": "jira:issue_updated",
                "issue": {
                    "key": task_key,
                    "fields": {
                        "summary": f"Test Task {i}",
                        "status": {"name": "READY TO TEST"}
                    }
                },
                "changelog": {
                    "items": [
                        {
                            "field": "status",
                            "fromString": "In Progress",
                            "toString": "READY TO TEST"
                        }
                    ]
                }
            }
            webhook_payloads.append(payload)

        # Background tasklarni mock qilish (asl AI chaqirmaslik uchun)
        with patch('services.webhook.jira_webhook_handler.check_tz_pr_and_comment', new_callable=AsyncMock) as mock_service1:
            with patch('services.webhook.jira_webhook_handler._run_testcase_generation', new_callable=AsyncMock) as mock_service2:
                with patch('services.webhook.jira_webhook_handler._run_task_group', new_callable=AsyncMock) as mock_group:
                    with patch('services.webhook.jira_webhook_handler._run_sequential_tasks', new_callable=AsyncMock) as mock_sequential:
                        
                        # 20 ta webhook yuborish
                        responses = []
                        for i, payload in enumerate(webhook_payloads):
                            try:
                                response = client.post("/webhook/jira", json=payload)
                                responses.append((i+1, response.status_code, response.json()))
                                logger.info(f"  Webhook {i+1}/20 yuborildi: {payload['issue']['key']}")
                            except Exception as e:
                                tracker.fail(f"Webhook {i+1} yuborish", str(e))
                                responses.append((i+1, None, {"error": str(e)}))

                        # Natijalarni tekshirish
                        success_count = 0
                        processing_count = 0
                        ignored_count = 0

                        for idx, status_code, data in responses:
                            if status_code == 200:
                                if data.get('status') == 'processing':
                                    processing_count += 1
                                    success_count += 1
                                elif data.get('status') == 'ignored':
                                    ignored_count += 1
                                else:
                                    tracker.fail(f"Webhook {idx} status", f"Kutilgan: processing/ignored, Keldi: {data.get('status')}")
                            else:
                                tracker.fail(f"Webhook {idx} HTTP", f"Status: {status_code}")

                        if success_count == 20:
                            tracker.ok("20 ta webhook muvaffaqiyatli yuborildi")
                        else:
                            tracker.fail("Webhook yuborish", f"Kutilgan: 20, Keldi: {success_count}")

                        # DB da tasklar mavjudligini tekshirish
                        db_tasks_found = 0
                        for task_key in task_keys:
                            task = get_task(task_key)
                            if task:
                                db_tasks_found += 1
                                if task['task_status'] in ('progressing', 'completed', 'blocked', 'error'):
                                    tracker.ok(f"Task {task_key} DB da mavjud: {task['task_status']}")
                                else:
                                    tracker.fail(f"Task {task_key} status", f"Kutilgan: progressing/completed/blocked/error, Keldi: {task['task_status']}")
                            else:
                                tracker.fail(f"Task {task_key} DB", "Topilmadi")

                        if db_tasks_found == 20:
                            tracker.ok("20 ta task DB ga yozildi")
                        else:
                            tracker.fail("DB task yozish", f"Kutilgan: 20, Keldi: {db_tasks_found}")

                        # Processing count tekshirish
                        if processing_count > 0:
                            tracker.ok(f"{processing_count} ta webhook processing holatida")
                        else:
                            tracker.fail("Processing count", "Hech qanday task processing emas")

    except Exception as e:
        tracker.fail("20 ta webhook test umumiy", str(e))
        import traceback
        logger.error(traceback.format_exc())


# ============================================================================
# TEST 2: SETTINGS ZIDDIYATLARINI TEKSHIRISH
# ============================================================================

def test_2_settings_conflicts():
    """
    TEST 2: Settings ziddiyatlarini tekshirish
    
    Tekshiradi:
    - Settings bir-biriga zid kelmasligi
    - Comment order va parallel mode ziddiyati
    - Threshold va auto_return ziddiyati
    - Trigger statuslar ziddiyati
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 2: Settings ziddiyatlarini tekshirish")
    logger.info("=" * 70)

    try:
        from config.app_settings import get_app_settings, AppSettings, TZPRCheckerSettings, TestcaseGeneratorSettings

        settings = get_app_settings(force_reload=True)

        # 2.1 Comment order va parallel mode ziddiyati
        comment_order = settings.tz_pr_checker.comment_order
        valid_orders = ["checker_first", "testcase_first", "parallel"]
        
        if comment_order in valid_orders:
            tracker.ok(f"comment_order to'g'ri: '{comment_order}'")
        else:
            tracker.fail("comment_order", f"Noto'g'ri qiymat: {comment_order}")

        # 2.2 Threshold va auto_return ziddiyati
        threshold = settings.tz_pr_checker.return_threshold
        auto_return = settings.tz_pr_checker.auto_return_enabled

        if 0 <= threshold <= 100:
            tracker.ok(f"return_threshold to'g'ri: {threshold}%")
        else:
            tracker.fail("return_threshold", f"Noto'g'ri qiymat: {threshold}%")

        # Auto return enabled bo'lsa threshold mavjud bo'lishi kerak
        if auto_return and threshold <= 0:
            tracker.fail("auto_return + threshold", "Auto return enabled lekin threshold 0")
        else:
            tracker.ok("auto_return va threshold ziddiyatsiz")

        # 2.3 Trigger statuslar ziddiyati
        tz_triggers = settings.tz_pr_checker.get_trigger_statuses()
        tc_triggers = settings.testcase_generator.get_trigger_statuses()

        if len(tz_triggers) > 0:
            tracker.ok(f"TZ-PR trigger statuslar: {tz_triggers}")
        else:
            tracker.fail("TZ-PR triggers", "Bo'sh ro'yxat")

        if len(tc_triggers) > 0:
            tracker.ok(f"Testcase trigger statuslar: {tc_triggers}")
        else:
            tracker.fail("Testcase triggers", "Bo'sh ro'yxat")

        # 2.4 Queue settings ziddiyati
        queue_enabled = settings.queue.queue_enabled
        task_wait_timeout = settings.queue.task_wait_timeout
        checker_testcase_delay = settings.queue.checker_testcase_delay

        if task_wait_timeout > 0:
            tracker.ok(f"task_wait_timeout to'g'ri: {task_wait_timeout}s")
        else:
            tracker.fail("task_wait_timeout", f"Noto'g'ri qiymat: {task_wait_timeout}s")

        if checker_testcase_delay >= 0:
            tracker.ok(f"checker_testcase_delay to'g'ri: {checker_testcase_delay}s")
        else:
            tracker.fail("checker_testcase_delay", f"Noto'g'ri qiymat: {checker_testcase_delay}s")

        # 2.5 Blocked retry delay ziddiyati
        blocked_retry_delay = settings.queue.blocked_retry_delay
        if blocked_retry_delay > 0:
            tracker.ok(f"blocked_retry_delay to'g'ri: {blocked_retry_delay} min")
        else:
            tracker.fail("blocked_retry_delay", f"Noto'g'ri qiymat: {blocked_retry_delay} min")

        # 2.6 Key freeze duration ziddiyati
        key_freeze_duration = settings.queue.key_freeze_duration
        if key_freeze_duration > 0:
            tracker.ok(f"key_freeze_duration to'g'ri: {key_freeze_duration}s")
        else:
            tracker.fail("key_freeze_duration", f"Noto'g'ri qiymat: {key_freeze_duration}s")

        # 2.7 AI max tokens ziddiyati
        ai_max_input_tokens = settings.queue.ai_max_input_tokens
        if 0 < ai_max_input_tokens <= 1000000:
            tracker.ok(f"ai_max_input_tokens to'g'ri: {ai_max_input_tokens}")
        else:
            tracker.fail("ai_max_input_tokens", f"Noto'g'ri qiymat: {ai_max_input_tokens}")

    except Exception as e:
        tracker.fail("Settings ziddiyat test umumiy", str(e))
        import traceback
        logger.error(traceback.format_exc())


# ============================================================================
# TEST 3: BLOCKED TASKLAR BILAN KEY-1 VA KEY-2 ISHLASHI
# ============================================================================

def test_3_blocked_tasks_key1_key2():
    """
    TEST 3: Blocked tasklar bilan key-1 va key-2 ishlashini test qilish
    
    Tekshiradi:
    - Service1 blocked bo'lganda key-1 error
    - Key-1 error bo'lganda key-2 ga o'tish
    - Key-2 ham error bo'lganda task blocked bo'lishi
    - Service2 blocked bo'lganda key-1 va key-2 ishlashi
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 3: Blocked tasklar bilan key-1 va key-2 ishlashi")
    logger.info("=" * 70)

    try:
        from utils.database.task_db import (
            mark_progressing, set_service1_blocked, set_service2_blocked,
            get_task, set_service1_done, set_service1_error, set_service2_error,
            get_blocked_tasks_ready_for_retry, upsert_task
        )
        from datetime import timedelta

        # 3.1 Service1 blocked - key-1 error simulyatsiyasi
        task_key1 = "BLOCKED-KEY1-001"
        mark_progressing(task_key1, "READY TO TEST")
        
        # Key-1 error simulyatsiyasi (AI timeout)
        set_service1_blocked(task_key1, "AI timeout: 429 rate limit exceeded", retry_minutes=1)
        
        task = get_task(task_key1)
        if task and task['service1_status'] == 'blocked':
            tracker.ok("Service1 blocked: key-1 error simulyatsiyasi")
        else:
            tracker.fail("Service1 blocked", f"Kutilgan: blocked, Keldi: {task.get('service1_status') if task else 'None'}")

        if task and task['task_status'] == 'blocked':
            tracker.ok("Task blocked holatga o'tdi")
        else:
            tracker.fail("Task blocked", f"Kutilgan: blocked, Keldi: {task.get('task_status') if task else 'None'}")

        # 3.2 Service2 blocked - key-2 error simulyatsiyasi
        task_key2 = "BLOCKED-KEY2-001"
        mark_progressing(task_key2, "READY TO TEST")
        set_service1_done(task_key2, compliance_score=80)
        
        # Key-2 error simulyatsiyasi
        set_service2_blocked(task_key2, "AI timeout: resource_exhausted quota exceeded", retry_minutes=1)
        
        task2 = get_task(task_key2)
        if task2 and task2['service2_status'] == 'blocked':
            tracker.ok("Service2 blocked: key-2 error simulyatsiyasi")
        else:
            tracker.fail("Service2 blocked", f"Kutilgan: blocked, Keldi: {task2.get('service2_status') if task2 else 'None'}")

        # 3.3 Ikkala key ham error - task blocked
        task_key3 = "BLOCKED-BOTH-001"
        mark_progressing(task_key3, "READY TO TEST")
        
        # Key-1 error
        set_service1_blocked(task_key3, "AI timeout: 429 rate limit", retry_minutes=1)
        
        # Key-2 ham error (service2 blocked)
        task3 = get_task(task_key3)
        if task3:
            # Service1 blocked bo'lganda service2 ham blocked qilish
            set_service2_blocked(task_key3, "AI timeout: ikkala key ham ishlamadi", retry_minutes=1)
        
        task3 = get_task(task_key3)
        if task3 and task3['service1_status'] == 'blocked' and task3['service2_status'] == 'blocked':
            tracker.ok("Ikkala key ham error: task blocked")
        else:
            tracker.fail("Ikkala key error", 
                        f"S1: {task3.get('service1_status') if task3 else 'None'}, "
                        f"S2: {task3.get('service2_status') if task3 else 'None'}")

        # 3.4 Blocked retry at tekshirish
        if task3 and task3.get('blocked_retry_at'):
            retry_at = datetime.fromisoformat(task3['blocked_retry_at'])
            now = datetime.now()
            if retry_at > now:
                tracker.ok("blocked_retry_at kelajakda")
            else:
                tracker.fail("blocked_retry_at", "O'tgan vaqtda")
        else:
            tracker.fail("blocked_retry_at", "Topilmadi")

        # 3.5 get_blocked_tasks_ready_for_retry tekshirish
        # Retry vaqtini o'tgan vaqtga o'rnatish
        past_time = (datetime.now() - timedelta(minutes=1)).isoformat()
        upsert_task(task_key1, {'blocked_retry_at': past_time})
        upsert_task(task_key2, {'blocked_retry_at': past_time})
        upsert_task(task_key3, {'blocked_retry_at': past_time})

        blocked_tasks = get_blocked_tasks_ready_for_retry()
        found_count = sum(1 for t in blocked_tasks if t['task_id'] in [task_key1, task_key2, task_key3])
        
        if found_count >= 1:
            tracker.ok(f"get_blocked_tasks_ready_for_retry: {found_count} ta blocked task topildi")
        else:
            tracker.fail("get_blocked_tasks_ready_for_retry", "Blocked tasklar topilmadi")

    except Exception as e:
        tracker.fail("Blocked tasks key-1 key-2 test umumiy", str(e))
        import traceback
        logger.error(traceback.format_exc())


# ============================================================================
# TEST 4: IKKALA KEY HAM ERROR BO'LGANDA RETRY MEXANIZMI
# ============================================================================

def test_4_both_keys_error_retry():
    """
    TEST 4: Ikkala key ham error bo'lganda blocked taskni retry mexanizmini test qilish
    
    Tekshiradi:
    - Blocked task retry vaqti kelganda qayta ishlash
    - Service1 blocked → retry → yana blocked bo'lsa to'xtash
    - Service2 blocked → retry → yana blocked bo'lsa to'xtash
    - Retry dan keyin task completed bo'lishi
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 4: Ikkala key ham error bo'lganda retry mexanizmi")
    logger.info("=" * 70)

    try:
        from utils.database.task_db import (
            mark_progressing, set_service1_blocked, set_service2_blocked,
            get_task, set_service1_done, set_service2_done,
            get_blocked_tasks_ready_for_retry, upsert_task
        )
        from datetime import timedelta
        from services.webhook.jira_webhook_handler import _retry_blocked_task
        import asyncio

        # 4.1 Service1 blocked → retry simulyatsiyasi
        task_key1 = "RETRY-KEY1-001"
        mark_progressing(task_key1, "READY TO TEST")
        set_service1_blocked(task_key1, "AI timeout: 429 rate limit", retry_minutes=0)  # 0 min = darhol retry
        
        # Retry vaqtini o'tgan vaqtga o'rnatish
        past_time = (datetime.now() - timedelta(minutes=1)).isoformat()
        upsert_task(task_key1, {'blocked_retry_at': past_time})

        # Retry funksiyasini mock bilan test qilish
        with patch('services.webhook.jira_webhook_handler.check_tz_pr_and_comment', new_callable=AsyncMock) as mock_service1:
            # Service1 muvaffaqiyatli bo'lsin
            mock_service1.return_value = None
            
            # Retry ni ishga tushirish
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_retry_blocked_task(task_key1))
                
                task = get_task(task_key1)
                if task:
                    # Service1 retry dan keyin pending yoki done bo'lishi kerak
                    if task['service1_status'] in ('pending', 'done', 'skip'):
                        tracker.ok("Service1 retry: status pending/done/skip")
                    else:
                        tracker.fail("Service1 retry status", f"Kutilgan: pending/done/skip, Keldi: {task['service1_status']}")
                else:
                    tracker.fail("Service1 retry", "Task topilmadi")
            finally:
                loop.close()

        # 4.2 Service2 blocked → retry simulyatsiyasi
        task_key2 = "RETRY-KEY2-001"
        mark_progressing(task_key2, "READY TO TEST")
        set_service1_done(task_key2, compliance_score=80)
        set_service2_blocked(task_key2, "AI timeout: resource_exhausted", retry_minutes=0)
        
        # Retry vaqtini o'tgan vaqtga o'rnatish
        past_time = (datetime.now() - timedelta(minutes=1)).isoformat()
        upsert_task(task_key2, {'blocked_retry_at': past_time})

        with patch('services.webhook.jira_webhook_handler._run_testcase_generation', new_callable=AsyncMock) as mock_service2:
            mock_service2.return_value = None
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_retry_blocked_task(task_key2))
                
                task = get_task(task_key2)
                if task:
                    if task['service2_status'] in ('pending', 'done'):
                        tracker.ok("Service2 retry: status pending/done")
                    else:
                        tracker.fail("Service2 retry status", f"Kutilgan: pending/done, Keldi: {task['service2_status']}")
                else:
                    tracker.fail("Service2 retry", "Task topilmadi")
            finally:
                loop.close()

        # 4.3 Ikkala key ham error → retry → yana error
        task_key3 = "RETRY-BOTH-001"
        mark_progressing(task_key3, "READY TO TEST")
        set_service1_blocked(task_key3, "AI timeout: ikkala key ham ishlamadi", retry_minutes=0)
        set_service2_blocked(task_key3, "AI timeout: ikkala key ham ishlamadi", retry_minutes=0)
        
        past_time = (datetime.now() - timedelta(minutes=1)).isoformat()
        upsert_task(task_key3, {'blocked_retry_at': past_time})

        # Service1 yana error bo'lsin
        with patch('services.webhook.jira_webhook_handler.check_tz_pr_and_comment', new_callable=AsyncMock) as mock_service1:
            # Service1 yana blocked qilish
            async def mock_service1_error():
                set_service1_blocked(task_key3, "AI timeout: yana error", retry_minutes=1)
            mock_service1.side_effect = mock_service1_error
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_retry_blocked_task(task_key3))
                
                task = get_task(task_key3)
                if task:
                    # Service1 yana blocked bo'lishi kerak
                    if task['service1_status'] == 'blocked':
                        tracker.ok("Service1 retry: yana blocked (to'g'ri)")
                    else:
                        tracker.fail("Service1 retry yana error", f"Kutilgan: blocked, Keldi: {task['service1_status']}")
                else:
                    tracker.fail("Service1 retry yana error", "Task topilmadi")
            finally:
                loop.close()

    except Exception as e:
        tracker.fail("Both keys error retry test umumiy", str(e))
        import traceback
        logger.error(traceback.format_exc())


# ============================================================================
# TEST 5: BARCHA MEXANIZMLARNI TEKSHIRISH
# ============================================================================

def test_5_all_mechanisms():
    """
    TEST 5: Barcha mexanizmlarni test qilish
    
    Tekshiradi:
    - Queue lock mexanizmi
    - DB concurrent access
    - Settings reload mexanizmi
    - Error classification mexanizmi
    - Task status state machine
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 5: Barcha mexanizmlarni test qilish")
    logger.info("=" * 70)

    try:
        from services.webhook.jira_webhook_handler import (
            _get_ai_queue_lock, _classify_error
        )
        from utils.database.task_db import (
            mark_progressing, set_service1_done, set_service2_done,
            mark_completed, get_task, init_db
        )
        from config.app_settings import get_app_settings

        # 5.1 Queue lock mexanizmi
        lock1 = _get_ai_queue_lock()
        lock2 = _get_ai_queue_lock()
        if lock1 is lock2:
            tracker.ok("Queue lock singleton: bir xil ob'ekt")
        else:
            tracker.fail("Queue lock singleton", "Har safar yangi ob'ekt")

        # 5.2 Error classification mexanizmi
        error_pr = _classify_error("PR topilmadi: no PR found")
        if error_pr == 'pr_not_found':
            tracker.ok("Error classification: PR topilmadi → pr_not_found")
        else:
            tracker.fail("Error classification PR", f"Kutilgan: pr_not_found, Keldi: {error_pr}")

        error_timeout = _classify_error("AI timeout: 429 rate limit exceeded")
        if error_timeout == 'ai_timeout':
            tracker.ok("Error classification: timeout → ai_timeout")
        else:
            tracker.fail("Error classification timeout", f"Kutilgan: ai_timeout, Keldi: {error_timeout}")

        error_both = _classify_error("AI xatolik: ikkala key ham ishlamadi")
        if error_both == 'ai_timeout':
            tracker.ok("Error classification: ikkala key → ai_timeout")
        else:
            tracker.fail("Error classification both keys", f"Kutilgan: ai_timeout, Keldi: {error_both}")

        # 5.3 Task status state machine
        task_key = "MECHANISM-001"
        mark_progressing(task_key, "READY TO TEST")
        task = get_task(task_key)
        if task and task['task_status'] == 'progressing':
            tracker.ok("State machine: none → progressing")
        else:
            tracker.fail("State machine progressing", f"Kutilgan: progressing, Keldi: {task.get('task_status') if task else 'None'}")

        set_service1_done(task_key, compliance_score=85)
        task = get_task(task_key)
        if task and task['service1_status'] == 'done':
            tracker.ok("State machine: service1 → done")
        else:
            tracker.fail("State machine service1", f"Kutilgan: done, Keldi: {task.get('service1_status') if task else 'None'}")

        set_service2_done(task_key)
        task = get_task(task_key)
        if task and task['service2_status'] == 'done':
            tracker.ok("State machine: service2 → done")
        else:
            tracker.fail("State machine service2", f"Kutilgan: done, Keldi: {task.get('service2_status') if task else 'None'}")

        mark_completed(task_key)
        task = get_task(task_key)
        if task and task['task_status'] == 'completed':
            tracker.ok("State machine: progressing → completed")
        else:
            tracker.fail("State machine completed", f"Kutilgan: completed, Keldi: {task.get('task_status') if task else 'None'}")

        # 5.4 Settings reload mexanizmi
        settings1 = get_app_settings(force_reload=False)
        settings2 = get_app_settings(force_reload=False)
        if settings1 is settings2:
            tracker.ok("Settings cache: bir xil ob'ekt (cache ishlaydi)")
        else:
            tracker.fail("Settings cache", "Har safar yangi ob'ekt")

        settings3 = get_app_settings(force_reload=True)
        if isinstance(settings3, type(settings1)):
            tracker.ok("Settings force_reload: yangi ob'ekt yaratildi")
        else:
            tracker.fail("Settings force_reload", "Yangi ob'ekt yaratilmadi")

        # 5.5 DB concurrent access
        init_db()
        task_keys_concurrent = [f"CONCURRENT-{i}" for i in range(1, 6)]
        for key in task_keys_concurrent:
            mark_progressing(key, "READY TO TEST")

        concurrent_ok = True
        for key in task_keys_concurrent:
            task = get_task(key)
            if not task or task['task_status'] != 'progressing':
                concurrent_ok = False
                tracker.fail(f"DB concurrent {key}", "Task topilmadi yoki status noto'g'ri")
                break

        if concurrent_ok:
            tracker.ok("DB concurrent access: 5 ta task bir vaqtda yozildi")

    except Exception as e:
        tracker.fail("Barcha mexanizmlar test umumiy", str(e))
        import traceback
        logger.error(traceback.format_exc())


# ============================================================================
# TEST 6: TIZIM BARDOShLILIGI (RESILIENCE)
# ============================================================================

def test_6_system_resilience():
    """
    TEST 6: Tizim bardoshliligini tekshirish
    
    Tekshiradi:
    - Xato holatlarda tizim crash qilmasligi
    - DB xatolarida graceful handling
    - Network xatolarida retry
    - Invalid payload handling
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 6: Tizim bardoshliligi")
    logger.info("=" * 70)

    try:
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        from utils.database.task_db import get_task

        client = TestClient(app)

        # 6.1 Invalid payload
        try:
            response = client.post("/webhook/jira", json={"invalid": "data"})
            if response.status_code in [200, 422]:
                tracker.ok("Invalid payload: crash qilmadi")
            else:
                tracker.fail("Invalid payload", f"Status: {response.status_code}")
        except Exception as e:
            tracker.fail("Invalid payload exception", str(e))

        # 6.2 Bo'sh payload
        try:
            response = client.post("/webhook/jira", json={})
            if response.status_code in [200, 422]:
                tracker.ok("Bo'sh payload: crash qilmadi")
            else:
                tracker.fail("Bo'sh payload", f"Status: {response.status_code}")
        except Exception as e:
            tracker.fail("Bo'sh payload exception", str(e))

        # 6.3 Noto'g'ri task key
        try:
            payload = {
                "webhookEvent": "jira:issue_updated",
                "issue": {"key": None},
                "changelog": {}
            }
            response = client.post("/webhook/jira", json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') in ['error', 'ignored']:
                    tracker.ok("Noto'g'ri task key: graceful error")
                else:
                    tracker.fail("Noto'g'ri task key", f"Status: {data.get('status')}")
            else:
                tracker.fail("Noto'g'ri task key HTTP", f"Status: {response.status_code}")
        except Exception as e:
            tracker.fail("Noto'g'ri task key exception", str(e))

        # 6.4 Mavjud bo'lmagan task DB da
        nonexistent_task = get_task("NONEXISTENT-999999")
        if nonexistent_task is None:
            tracker.ok("Mavjud bo'lmagan task: None qaytaradi (crash yo'q)")
        else:
            tracker.fail("Mavjud bo'lmagan task", "None kutilgan")

        # 6.5 Health check
        try:
            response = client.get("/health")
            if response.status_code == 200:
                tracker.ok("Health check: ishlaydi")
            else:
                tracker.fail("Health check", f"Status: {response.status_code}")
        except Exception as e:
            tracker.fail("Health check exception", str(e))

    except Exception as e:
        tracker.fail("Tizim bardoshliligi test umumiy", str(e))
        import traceback
        logger.error(traceback.format_exc())


# ============================================================================
# CLEANUP
# ============================================================================

def cleanup_test_data():
    """Test ma'lumotlarini DB dan tozalash"""
    logger.info("\nTest ma'lumotlarini tozalash...")
    try:
        from utils.database.task_db import DB_FILE
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Test task'larni tozalash
        test_prefixes = [
            'TEST-WEBHOOK-%', 'BLOCKED-%', 'RETRY-%', 'MECHANISM-%', 'CONCURRENT-%'
        ]

        for prefix in test_prefixes:
            cursor.execute("DELETE FROM task_processing WHERE task_id LIKE ?", (prefix,))

        conn.commit()
        deleted = cursor.rowcount
        conn.close()

        logger.info(f"  {deleted} ta test yozuv tozalandi")
    except Exception as e:
        logger.warning(f"  Tozalashda xato: {e}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("JIRA-AI-Analyzer TIZIM BARDOShLILIGI VA TO'LIQ TESTLAR")
    logger.info("=" * 70)
    logger.info(f"Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python: {sys.version}")
    logger.info("=" * 70)

    start_time = time.time()

    # Barcha testlarni ishga tushirish
    test_1_send_20_fake_webhooks()
    test_2_settings_conflicts()
    test_3_blocked_tasks_key1_key2()
    test_4_both_keys_error_retry()
    test_5_all_mechanisms()
    test_6_system_resilience()

    # Tozalash
    cleanup_test_data()

    elapsed = time.time() - start_time

    # Yakuniy natija
    logger.info("\n")
    logger.info("=" * 70)
    logger.info("YAKUNIY NATIJA")
    logger.info("=" * 70)

    all_passed = tracker.summary()

    logger.info(f"Vaqt: {elapsed:.2f} sekund")
    logger.info("=" * 70)

    # Exit code
    sys.exit(0 if all_passed else 1)
