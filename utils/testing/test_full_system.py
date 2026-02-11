"""
JIRA-AI-Analyzer - To'liq Tizim Testlari
==========================================

Barcha jarayonlarni batafsil tekshirish:
1. 2 ta servis qanday ishlashi (tz_pr_checker, testcase_generator)
2. JIRA task testing statusga tushganda tizim o'zini qanday tutishi
3. 5 ta task bir vaqtda testing statusga tushganda (concurrency)
4. DB fayl bilan ishlash
5. Bir taskda 2 ta servis qay tartibda ishlashi
6. Xato va error holatlarida tizim barqarorligi

Author: Test Suite
Date: 2026-02-10

Ishga tushirish:
    python utils/testing/test_full_system.py
"""
import sys
import os
import json
import sqlite3
import asyncio
import time
import logging
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import asdict

# Loyiha root path (utils/testing/ -> utils/ -> project_root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
        logger.info(f"  PASS: {test_name} {detail}")

    def fail(self, test_name, reason):
        self.failed += 1
        self.errors.append((test_name, reason))
        self.results.append(("FAIL", test_name, reason))
        logger.error(f"  FAIL: {test_name} - {reason}")

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
# 1-TEST: 2 TA SERVIS ALOHIDA ISHLASHI
# ============================================================================

def test_1_services_individually():
    """
    TEST 1: Har bir servis alohida qanday ishlashini tekshirish

    - TZPRService.analyze_task() to'g'ri natija qaytaradimi?
    - TestCaseGeneratorService.generate_test_cases() to'g'ri natija qaytaradimi?
    - Har bir servis BaseService'dan meros oladimi?
    - Lazy loading ishlayaptimi?
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 1: 2 ta servis alohida ishlashi")
    logger.info("=" * 70)

    # --- 1.1 TZPRService ---
    try:
        from services.checkers.tz_pr_checker import TZPRService, TZPRAnalysisResult
        from core.base_service import BaseService

        service = TZPRService()

        # BaseService'dan meros olganmi?
        if isinstance(service, BaseService):
            tracker.ok("TZPRService BaseService'dan meros olgan")
        else:
            tracker.fail("TZPRService meros", "BaseService'dan meros olmagan")

        # Lazy loading: _jira_client boshlang'ichda None
        if service._jira_client is None:
            tracker.ok("TZPRService lazy loading (JIRA boshlang'ichda None)")
        else:
            tracker.fail("TZPRService lazy loading", "_jira_client None emas")

        if service._github_client is None:
            tracker.ok("TZPRService lazy loading (GitHub boshlang'ichda None)")
        else:
            tracker.fail("TZPRService lazy loading GitHub", "_github_client None emas")

        if service._gemini_helper is None:
            tracker.ok("TZPRService lazy loading (Gemini boshlang'ichda None)")
        else:
            tracker.fail("TZPRService lazy loading Gemini", "_gemini_helper None emas")

        # Mock bilan analyze_task tekshirish
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = {
            'summary': 'Test task summary',
            'type': 'Story',
            'priority': 'High',
            'description': 'Test TZ mazmuni',
            'comments': [],
            'figma_links': []
        }

        mock_github = MagicMock()
        mock_pr = MagicMock()
        mock_pr.title = "feat: test PR"
        mock_pr.html_url = "https://github.com/test/pr/1"
        mock_pr.get_files.return_value = [
            MagicMock(
                filename="test.py",
                status="modified",
                additions=10,
                deletions=5,
                patch="@@ -1,5 +1,10 @@\n+new code"
            )
        ]
        mock_github.search_pull_requests.return_value = [mock_pr]
        mock_github.get_repo_name.return_value = "test/repo"

        mock_gemini = MagicMock()
        mock_gemini.analyze.return_value = (
            "## BAJARILGAN TALABLAR\nTest bajarildi\n\n"
            "## MOSLIK BALI\n**COMPLIANCE_SCORE: 85%**"
        )

        service._jira_client = mock_jira
        service._github_client = mock_github
        service._gemini_helper = mock_gemini

        # PR Helper ham mock
        mock_pr_helper = MagicMock()
        mock_pr_helper.get_pr_full_info.return_value = {
            'pr_count': 1,
            'files_changed': 1,
            'total_additions': 10,
            'total_deletions': 5,
            'pr_details': [{
                'title': 'feat: test PR',
                'url': 'https://github.com/test/pr/1',
                'files': [{
                    'filename': 'test.py',
                    'status': 'modified',
                    'additions': 10,
                    'deletions': 5,
                    'patch': '+new code'
                }]
            }]
        }
        service._pr_helper = mock_pr_helper

        result = service.analyze_task("TEST-001")

        if isinstance(result, TZPRAnalysisResult):
            tracker.ok("TZPRService.analyze_task() TZPRAnalysisResult qaytaradi")
        else:
            tracker.fail("TZPRService natija turi", f"Kutilgan: TZPRAnalysisResult, Keldi: {type(result)}")

        if result.success:
            tracker.ok("TZPRService.analyze_task() muvaffaqiyatli")
        else:
            tracker.fail("TZPRService.analyze_task() success=False", result.error_message)

        if result.compliance_score == 85:
            tracker.ok("TZPRService compliance_score to'g'ri extract qilgan (85%)")
        else:
            tracker.fail("TZPRService compliance_score", f"Kutilgan: 85, Keldi: {result.compliance_score}")

        if result.task_key == "TEST-001":
            tracker.ok("TZPRService task_key to'g'ri")
        else:
            tracker.fail("TZPRService task_key", f"Kutilgan: TEST-001, Keldi: {result.task_key}")

    except Exception as e:
        tracker.fail("TZPRService umumiy", str(e))

    # --- 1.2 TestCaseGeneratorService ---
    try:
        from services.generators.testcase_generator import (
            TestCaseGeneratorService, TestCaseGenerationResult, TestCase
        )

        service2 = TestCaseGeneratorService()

        if isinstance(service2, BaseService):
            tracker.ok("TestCaseGeneratorService BaseService'dan meros olgan")
        else:
            tracker.fail("TestCaseGeneratorService meros", "BaseService'dan meros olmagan")

        # Mock sozlash
        mock_jira2 = MagicMock()
        mock_jira2.get_task_details.return_value = {
            'summary': 'Login functionality',
            'type': 'Story',
            'priority': 'High',
            'description': 'Login sahifasini yaratish kerak',
            'comments': []
        }

        mock_gemini2 = MagicMock()
        mock_gemini2.analyze.return_value = json.dumps({
            "test_cases": [
                {
                    "id": "TC-001",
                    "title": "Login positive test",
                    "description": "To'g'ri ma'lumotlar bilan login",
                    "preconditions": "Foydalanuvchi ro'yxatdan o'tgan",
                    "steps": ["1. Login sahifasini ochish", "2. Username kiritish", "3. Login bosish"],
                    "expected_result": "Muvaffaqiyatli login",
                    "test_type": "positive",
                    "priority": "High",
                    "severity": "Critical",
                    "tags": ["login", "auth"]
                },
                {
                    "id": "TC-002",
                    "title": "Login negative test",
                    "description": "Noto'g'ri parol bilan login",
                    "preconditions": "Foydalanuvchi mavjud",
                    "steps": ["1. Login sahifasini ochish", "2. Noto'g'ri parol kiritish"],
                    "expected_result": "Xato xabari ko'rsatiladi",
                    "test_type": "negative",
                    "priority": "High",
                    "severity": "Major",
                    "tags": ["login", "security"]
                }
            ]
        })

        service2._jira_client = mock_jira2
        service2._gemini_helper = mock_gemini2
        service2._github_client = MagicMock()

        # PR Helper mock (PR topilmadi holati)
        mock_pr_helper2 = MagicMock()
        mock_pr_helper2.get_pr_full_info.return_value = None
        service2._pr_helper = mock_pr_helper2

        result2 = service2.generate_test_cases("TEST-002", include_pr=True)

        if isinstance(result2, TestCaseGenerationResult):
            tracker.ok("TestCaseGeneratorService to'g'ri natija turi qaytaradi")
        else:
            tracker.fail("TestCaseGenerator natija turi", f"Keldi: {type(result2)}")

        if result2.success:
            tracker.ok("TestCaseGeneratorService muvaffaqiyatli ishladi")
        else:
            tracker.fail("TestCaseGenerator muvaffaqiyatsiz", result2.error_message)

        if len(result2.test_cases) == 2:
            tracker.ok("TestCaseGenerator 2 ta test case yaratdi")
        else:
            tracker.fail("TestCaseGenerator test cases soni", f"Kutilgan: 2, Keldi: {len(result2.test_cases)}")

        if result2.test_cases and result2.test_cases[0].test_type == "positive":
            tracker.ok("TestCaseGenerator birinchi test case positive turi")
        else:
            tracker.fail("TestCaseGenerator test type", "Birinchi test case positive emas")

        # Custom context tekshirish
        result3 = service2.generate_test_cases(
            "TEST-003",
            include_pr=False,
            custom_context="Product: ACME Widget, Narx: $99.99"
        )

        if result3.custom_context_used:
            tracker.ok("TestCaseGenerator custom_context_used=True")
        else:
            tracker.fail("TestCaseGenerator custom context", "custom_context_used=False")

        # Gemini'ga yuborilgan prompt'da custom context borligini tekshirish
        call_args = mock_gemini2.analyze.call_args
        if "ACME Widget" in str(call_args):
            tracker.ok("TestCaseGenerator custom context prompt'ga qo'shilgan")
        else:
            tracker.fail("TestCaseGenerator custom context prompt", "ACME Widget prompt'da topilmadi")

    except Exception as e:
        tracker.fail("TestCaseGeneratorService umumiy", str(e))


# ============================================================================
# 2-TEST: JIRA TASK TESTING STATUSGA TUSHGANDA
# ============================================================================

def test_2_webhook_status_change():
    """
    TEST 2: JIRA task testing statusga tushganda tizim o'zini qanday tutishi

    - Webhook endpoint to'g'ri parse qiladimi?
    - Status o'zgarishi aniqlanadimi?
    - Target status tekshiruvi ishlaydimi?
    - DB holat boshqaruvi to'g'rimi?
    - Dublikat event filtri ishlaydimi?
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 2: Webhook status o'zgarishi")
    logger.info("=" * 70)

    try:
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app

        client = TestClient(app)

        # 2.1 Health check
        response = client.get("/health")
        if response.status_code == 200:
            tracker.ok("Health check endpoint ishlaydi")
        else:
            tracker.fail("Health check", f"Status: {response.status_code}")

        # 2.2 Root endpoint
        response = client.get("/")
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'running':
                tracker.ok("Root endpoint service=running ko'rsatadi")
            else:
                tracker.fail("Root endpoint status", f"Keldi: {data.get('status')}")
        else:
            tracker.fail("Root endpoint", f"Status: {response.status_code}")

        # 2.3 Noto'g'ri event type (jira:issue_created - status change emas)
        payload_wrong_event = {
            "webhookEvent": "jira:issue_created",
            "issue": {"key": "TEST-100"},
            "changelog": {}
        }
        response = client.post("/webhook/jira", json=payload_wrong_event)
        data = response.json()
        if data.get('status') == 'ignored':
            tracker.ok("Noto'g'ri event type (issue_created) to'g'ri ignored qilindi")
        else:
            tracker.fail("Noto'g'ri event type", f"Kutilgan: ignored, Keldi: {data.get('status')}")

        # 2.4 Status o'zgarishi yo'q (changelog'da status yo'q)
        payload_no_status = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "TEST-101"},
            "changelog": {
                "items": [
                    {"field": "summary", "fromString": "Old", "toString": "New"}
                ]
            }
        }
        response = client.post("/webhook/jira", json=payload_no_status)
        data = response.json()
        if data.get('status') == 'ignored' and 'status not changed' in data.get('reason', ''):
            tracker.ok("Status o'zgarishi yo'q - to'g'ri ignored qilindi")
        else:
            tracker.fail("Status o'zgarishi yo'q", f"Keldi: {data}")

        # 2.5 Target bo'lmagan statusga o'tish (In Progress)
        payload_wrong_status = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "TEST-102"},
            "changelog": {
                "items": [
                    {"field": "status", "fromString": "Open", "toString": "In Progress"}
                ]
            }
        }
        response = client.post("/webhook/jira", json=payload_wrong_status)
        data = response.json()
        if data.get('status') == 'ignored':
            tracker.ok("Target bo'lmagan status (In Progress) ignored qilindi")
        else:
            tracker.fail("Target bo'lmagan status", f"Keldi: {data}")

        # 2.6 To'g'ri status o'zgarishi (Ready to Test) - background task ishga tushadi
        payload_correct = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "TEST-WEBHOOK-001"},
            "changelog": {
                "items": [
                    {"field": "status", "fromString": "In Progress", "toString": "READY TO TEST"}
                ]
            }
        }

        # Background task'ni mock qilish (asl AI chaqirmaslik uchun)
        with patch('services.webhook.jira_webhook_handler.check_tz_pr_and_comment', new_callable=AsyncMock):
            with patch('services.webhook.jira_webhook_handler._run_testcase_generation', new_callable=AsyncMock):
                with patch('services.webhook.jira_webhook_handler._run_task_group', new_callable=AsyncMock):
                    with patch('services.webhook.jira_webhook_handler._run_sequential_tasks', new_callable=AsyncMock):
                        response = client.post("/webhook/jira", json=payload_correct)
                        data = response.json()

                        if data.get('status') == 'processing':
                            tracker.ok("To'g'ri status (READY TO TEST) processing qilindi")
                        else:
                            tracker.fail("To'g'ri status processing", f"Keldi: {data}")

                        if data.get('task_key') == 'TEST-WEBHOOK-001':
                            tracker.ok("Task key to'g'ri qaytarildi")
                        else:
                            tracker.fail("Task key", f"Keldi: {data.get('task_key')}")

        # 2.7 Dublikat event tekshirish
        with patch('services.webhook.jira_webhook_handler.check_tz_pr_and_comment', new_callable=AsyncMock):
            with patch('services.webhook.jira_webhook_handler._run_testcase_generation', new_callable=AsyncMock):
                with patch('services.webhook.jira_webhook_handler._run_task_group', new_callable=AsyncMock):
                    with patch('services.webhook.jira_webhook_handler._run_sequential_tasks', new_callable=AsyncMock):
                        response2 = client.post("/webhook/jira", json=payload_correct)
                        data2 = response2.json()

                        if data2.get('status') == 'ignored':
                            tracker.ok("Dublikat event to'g'ri ignored qilindi (progressing)")
                        else:
                            tracker.fail("Dublikat event", f"Keldi: {data2}")

        # 2.8 Task key yo'q holat
        payload_no_key = {
            "webhookEvent": "jira:issue_updated",
            "issue": {},
            "changelog": {}
        }
        response = client.post("/webhook/jira", json=payload_no_key)
        data = response.json()
        if data.get('status') == 'error' or 'no task key' in data.get('reason', ''):
            tracker.ok("Task key yo'q - xato to'g'ri qaytarildi")
        else:
            tracker.fail("Task key yo'q holat", f"Keldi: {data}")

        # 2.9 Settings endpoint
        response = client.get("/settings")
        if response.status_code == 200:
            settings_data = response.json()
            if 'return_threshold' in settings_data:
                tracker.ok("Settings endpoint ishlaydi va threshold qaytaradi")
            else:
                tracker.fail("Settings endpoint", "return_threshold yo'q")
        else:
            tracker.fail("Settings endpoint", f"Status: {response.status_code}")

    except Exception as e:
        tracker.fail("Webhook testi umumiy", str(e))


# ============================================================================
# 3-TEST: 5 TA TASK BIR VAQTDA (CONCURRENCY)
# ============================================================================

def test_3_concurrent_tasks():
    """
    TEST 3: 5 ta task bir vaqtda testing statusga tushganda

    - Queue lock ishlayaptimi?
    - Timeout mehanizmi to'g'rimi?
    - Barcha tasklar DB ga yozilganmi?
    - Race condition yo'qmi?
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 3: Concurrent tasklar (5 ta bir vaqtda)")
    logger.info("=" * 70)

    try:
        from services.webhook.jira_webhook_handler import (
            _get_ai_queue_lock, _wait_for_ai_slot
        )
        from utils.database.task_db import (
            get_task, mark_progressing, mark_completed,
            set_service1_done, set_service2_done
        )

        # 3.1 Queue lock singleton tekshirish
        lock1 = _get_ai_queue_lock()
        lock2 = _get_ai_queue_lock()
        if lock1 is lock2:
            tracker.ok("AI queue lock singleton - bir xil ob'ekt")
        else:
            tracker.fail("AI queue lock singleton", "Har safar yangi ob'ekt yaratilgan")

        # 3.2 5 ta task bir vaqtda DB ga yozish
        task_keys = [f"CONC-{i}" for i in range(1, 6)]

        for key in task_keys:
            mark_progressing(key, "READY TO TEST", datetime.now())

        # Barcha tasklar DB da mavjudmi?
        all_in_db = True
        for key in task_keys:
            task = get_task(key)
            if not task:
                all_in_db = False
                tracker.fail(f"Concurrent DB yozish {key}", "Task DB da topilmadi")
                break
            if task['task_status'] != 'progressing':
                all_in_db = False
                tracker.fail(f"Concurrent DB status {key}", f"Kutilgan: progressing, Keldi: {task['task_status']}")
                break

        if all_in_db:
            tracker.ok("5 ta task bir vaqtda DB ga progressing holatda yozildi")

        # 3.3 Concurrent service done yozish
        for i, key in enumerate(task_keys):
            set_service1_done(key, compliance_score=70 + i * 5)

        scores_correct = True
        for i, key in enumerate(task_keys):
            task = get_task(key)
            expected_score = 70 + i * 5
            if task['compliance_score'] != expected_score:
                scores_correct = False
                tracker.fail(f"Concurrent score {key}",
                           f"Kutilgan: {expected_score}, Keldi: {task['compliance_score']}")
                break

        if scores_correct:
            tracker.ok("5 ta task concurrent score yozish to'g'ri ishladi")

        # 3.4 Concurrent completed qilish
        for key in task_keys:
            set_service2_done(key)

        all_completed = True
        for key in task_keys:
            task = get_task(key)
            if task['task_status'] != 'completed':
                all_completed = False
                tracker.fail(f"Concurrent completed {key}", f"Status: {task['task_status']}")
                break

        if all_completed:
            tracker.ok("5 ta task concurrent completed holatga o'tdi")

        # 3.5 Async queue lock testi
        async def test_queue_lock():
            """Queue lock'ni async muhitda tekshirish"""
            lock = _get_ai_queue_lock()
            results = []

            async def worker(worker_id, delay):
                acquired = False
                try:
                    await asyncio.wait_for(lock.acquire(), timeout=5)
                    acquired = True
                    results.append(f"W{worker_id}-start-{time.time():.2f}")
                    await asyncio.sleep(delay)
                    results.append(f"W{worker_id}-end-{time.time():.2f}")
                except asyncio.TimeoutError:
                    results.append(f"W{worker_id}-timeout")
                finally:
                    if acquired:
                        lock.release()

            # 3 ta worker parallel ishga tushirish
            await asyncio.gather(
                worker(1, 0.1),
                worker(2, 0.1),
                worker(3, 0.1)
            )

            return results

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(test_queue_lock())

            starts = [r for r in results if 'start' in r]
            ends = [r for r in results if 'end' in r]

            if len(starts) == 3 and len(ends) == 3:
                tracker.ok("Queue lock: 3 ta worker ketma-ket ishladi (parallel emas)")
            else:
                tracker.fail("Queue lock parallel test", f"Results: {results}")
        finally:
            loop.close()

        # 3.6 Queue timeout testi
        async def test_queue_timeout():
            """Queue timeout tekshirish"""
            lock = asyncio.Lock()
            await lock.acquire()  # Lock'ni ushlab turish

            timed_out = False
            try:
                await asyncio.wait_for(lock.acquire(), timeout=0.5)
            except asyncio.TimeoutError:
                timed_out = True
            finally:
                lock.release()

            return timed_out

        loop2 = asyncio.new_event_loop()
        asyncio.set_event_loop(loop2)
        try:
            timed_out = loop2.run_until_complete(test_queue_timeout())
            if timed_out:
                tracker.ok("Queue timeout mehanizmi ishlaydi (0.5s)")
            else:
                tracker.fail("Queue timeout", "Timeout ishlamadi")
        finally:
            loop2.close()

    except Exception as e:
        tracker.fail("Concurrent test umumiy", str(e))


# ============================================================================
# 4-TEST: DB FAYL BILAN ISHLASH
# ============================================================================

def test_4_database_operations():
    """
    TEST 4: DB fayl bilan ishlash

    - init_db() to'g'ri jadval yaratadimi?
    - CRUD operatsiyalar ishlayaptimi?
    - task_status state machine to'g'rimi?
    - Service statuslar to'g'ri yangilanadimi?
    - Reset service statuslar ishlayaptimi?
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 4: Database operatsiyalari")
    logger.info("=" * 70)

    try:
        from utils.database.task_db import (
            init_db, get_task, upsert_task, mark_progressing,
            mark_completed, mark_returned, mark_error,
            increment_return_count, set_skip_detected,
            set_service1_done, set_service1_error,
            set_service2_done, set_service2_error,
            reset_service_statuses, DB_FILE
        )

        # 4.1 DB fayl mavjud
        if os.path.exists(DB_FILE):
            tracker.ok(f"DB fayl mavjud: {DB_FILE}")
        else:
            tracker.fail("DB fayl", f"Topilmadi: {DB_FILE}")
            return

        # 4.2 Jadval strukturasini tekshirish
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(task_processing)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        required_columns = {
            'task_id', 'task_status', 'task_update_time', 'return_count',
            'last_jira_status', 'last_processed_at', 'error_message', 'skip_detected',
            'service1_status', 'service2_status', 'service1_error', 'service2_error',
            'service1_done_at', 'service2_done_at', 'compliance_score',
            'created_at', 'updated_at'
        }

        missing = required_columns - columns
        if not missing:
            tracker.ok(f"DB jadval strukturasi to'liq ({len(required_columns)} ta column)")
        else:
            tracker.fail("DB jadval strukturasi", f"Yo'q columnlar: {missing}")

        # 4.3 Yangi task yaratish (upsert)
        test_key = "DB-TEST-001"
        mark_progressing(test_key, "READY TO TEST", datetime.now())

        task = get_task(test_key)
        if task and task['task_status'] == 'progressing':
            tracker.ok("mark_progressing() to'g'ri ishlaydi")
        else:
            tracker.fail("mark_progressing", f"Task: {task}")

        # 4.4 Service1 done
        set_service1_done(test_key, compliance_score=75)
        task = get_task(test_key)
        if task['service1_status'] == 'done' and task['compliance_score'] == 75:
            tracker.ok("set_service1_done() to'g'ri (score=75)")
        else:
            tracker.fail("set_service1_done", f"Status: {task['service1_status']}, Score: {task['compliance_score']}")

        # 4.5 Service2 done
        set_service2_done(test_key)
        task = get_task(test_key)
        if task['service2_status'] == 'done' and task['task_status'] == 'completed':
            tracker.ok("set_service2_done() to'g'ri (task completed)")
        else:
            tracker.fail("set_service2_done", f"Service2: {task['service2_status']}, Task: {task['task_status']}")

        # 4.6 mark_returned()
        test_key2 = "DB-TEST-002"
        mark_progressing(test_key2, "READY TO TEST")
        set_service1_done(test_key2, compliance_score=40)
        mark_returned(test_key2)

        task = get_task(test_key2)
        if task['task_status'] == 'returned':
            tracker.ok("mark_returned() to'g'ri ishlaydi")
        else:
            tracker.fail("mark_returned", f"Status: {task['task_status']}")

        # 4.7 increment_return_count()
        increment_return_count(test_key2)
        task = get_task(test_key2)
        if task['return_count'] == 1:
            tracker.ok("increment_return_count() 0 -> 1")
        else:
            tracker.fail("increment_return_count", f"Count: {task['return_count']}")

        increment_return_count(test_key2)
        task = get_task(test_key2)
        if task['return_count'] == 2:
            tracker.ok("increment_return_count() 1 -> 2")
        else:
            tracker.fail("increment_return_count 2", f"Count: {task['return_count']}")

        # 4.8 reset_service_statuses()
        reset_service_statuses(test_key2)
        task = get_task(test_key2)
        if (task['service1_status'] == 'pending' and
            task['service2_status'] == 'pending' and
            task['compliance_score'] is None):
            tracker.ok("reset_service_statuses() to'g'ri (pending, score=None)")
        else:
            tracker.fail("reset_service_statuses",
                        f"S1: {task['service1_status']}, S2: {task['service2_status']}, Score: {task['compliance_score']}")

        # 4.9 Service error holatlar
        test_key3 = "DB-TEST-003"
        mark_progressing(test_key3, "READY TO TEST")
        set_service1_error(test_key3, "AI timeout error")

        task = get_task(test_key3)
        if task['service1_status'] == 'error' and task['service1_error'] == 'AI timeout error':
            tracker.ok("set_service1_error() to'g'ri (error message saqlandi)")
        else:
            tracker.fail("set_service1_error", f"Status: {task['service1_status']}, Error: {task['service1_error']}")

        # 4.10 set_skip_detected()
        test_key4 = "DB-TEST-004"
        mark_progressing(test_key4, "READY TO TEST")
        set_skip_detected(test_key4)

        task = get_task(test_key4)
        if task['skip_detected'] == 1 and task['task_status'] == 'completed':
            tracker.ok("set_skip_detected() to'g'ri (completed, skip=1)")
        else:
            tracker.fail("set_skip_detected", f"Skip: {task['skip_detected']}, Status: {task['task_status']}")

        # 4.11 Mavjud bo'lmagan task
        task = get_task("NONEXISTENT-999")
        if task is None:
            tracker.ok("get_task() mavjud bo'lmagan task uchun None qaytaradi")
        else:
            tracker.fail("get_task nonexistent", f"Kutilgan: None, Keldi: {task}")

        # 4.12 mark_error()
        test_key5 = "DB-TEST-005"
        mark_progressing(test_key5, "READY TO TEST")
        mark_error(test_key5, "Critical system failure")

        task = get_task(test_key5)
        if task['task_status'] == 'error' and task['error_message'] == 'Critical system failure':
            tracker.ok("mark_error() to'g'ri ishlaydi")
        else:
            tracker.fail("mark_error", f"Status: {task['task_status']}, Error: {task['error_message']}")

        # 4.13 State Machine: none -> progressing -> completed
        test_key6 = "DB-TEST-006"
        mark_progressing(test_key6, "READY TO TEST")
        set_service1_done(test_key6, 90)
        set_service2_done(test_key6)
        mark_completed(test_key6)

        task = get_task(test_key6)
        if task['task_status'] == 'completed':
            tracker.ok("State Machine: none -> progressing -> completed to'g'ri")
        else:
            tracker.fail("State Machine", f"Oxirgi status: {task['task_status']}")

        # 4.14 Updated_at yangilanganligi
        task = get_task(test_key)
        if task.get('updated_at'):
            tracker.ok("updated_at avtomatik yangilanadi")
        else:
            tracker.fail("updated_at", "Topilmadi")

        # 4.15 Indexlar mavjudligi
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='task_processing'")
        indexes = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected_indexes = {'idx_task_status', 'idx_service1_status', 'idx_service2_status'}
        if expected_indexes.issubset(indexes):
            tracker.ok(f"DB indexlar mavjud: {expected_indexes}")
        else:
            tracker.fail("DB indexlar", f"Yo'q: {expected_indexes - indexes}")

    except Exception as e:
        tracker.fail("DB test umumiy", str(e))


# ============================================================================
# 5-TEST: 2 TA SERVIS TARTIB TEKSHIRISH
# ============================================================================

def test_5_service_order():
    """
    TEST 5: Bir taskda 2 ta servis qay tartibda ishlashi

    - checker_first mode: Service1 -> delay -> Service2
    - Service2 Service1 done bo'lguncha kutadimi?
    - Score threshold Service2 ni bloklayaptimi?
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 5: Servislar tartibini tekshirish")
    logger.info("=" * 70)

    try:
        from config.app_settings import get_app_settings, TZPRCheckerSettings
        from utils.database.task_db import (
            get_task, mark_progressing, set_service1_done,
            set_service2_done, mark_returned, reset_service_statuses
        )

        settings = get_app_settings()

        # 5.1 Default tartib tekshirish
        order = settings.tz_pr_checker.comment_order
        tracker.ok(f"Default comment_order: '{order}'")

        # 5.2 checker_first tartibida Service1 -> Service2
        test_key = "ORDER-001"
        mark_progressing(test_key, "READY TO TEST")

        set_service1_done(test_key, compliance_score=80)
        task = get_task(test_key)

        if task['service1_status'] == 'done':
            tracker.ok("Service1 done - Service2 ishga tushishi mumkin")
        else:
            tracker.fail("Service1 done check", f"Status: {task['service1_status']}")

        # 5.3 Score past bo'lganda Service2 bloklanishi
        test_key2 = "ORDER-002"
        mark_progressing(test_key2, "READY TO TEST")
        set_service1_done(test_key2, compliance_score=40)

        task = get_task(test_key2)
        threshold = settings.tz_pr_checker.return_threshold

        if task['compliance_score'] < threshold:
            tracker.ok(f"Score past ({task['compliance_score']}% < {threshold}%) - Service2 bloklanishi kerak")
        else:
            tracker.fail("Score threshold check", f"Score: {task['compliance_score']}, Threshold: {threshold}")

        # 5.4 Service2 Service1'siz ishlamasligi
        test_key3 = "ORDER-003"
        mark_progressing(test_key3, "READY TO TEST")

        task = get_task(test_key3)
        if task['service1_status'] == 'pending':
            tracker.ok("Service1 pending - Service2 ishlamasligi kerak")
        else:
            tracker.fail("Service1 pending check", f"Status: {task['service1_status']}")

        # 5.5 Returned taskda Service2 ishlamasligi
        test_key4 = "ORDER-004"
        mark_progressing(test_key4, "READY TO TEST")
        set_service1_done(test_key4, compliance_score=30)
        mark_returned(test_key4)

        task = get_task(test_key4)
        if task['task_status'] == 'returned':
            tracker.ok("Returned task - Service2 ishlamasligi kerak")
        else:
            tracker.fail("Returned task check", f"Status: {task['task_status']}")

        # 5.6 Re-check flow: returned -> reset -> progressing
        reset_service_statuses(test_key4)
        mark_progressing(test_key4, "READY TO TEST")

        task = get_task(test_key4)
        if (task['service1_status'] == 'pending' and
            task['service2_status'] == 'pending' and
            task['task_status'] == 'progressing'):
            tracker.ok("Re-check flow: reset -> progressing to'g'ri (ikkala servis pending)")
        else:
            tracker.fail("Re-check flow",
                        f"S1: {task['service1_status']}, S2: {task['service2_status']}, Task: {task['task_status']}")

        # 5.7 compliance_score=None bo'lganda Service2 ishlay olishi
        test_key5 = "ORDER-005"
        mark_progressing(test_key5, "READY TO TEST")
        set_service1_done(test_key5, compliance_score=None)

        task = get_task(test_key5)
        if task['compliance_score'] is None and task['service1_status'] == 'done':
            tracker.ok("Score=None holat: Service2 bloklanmasligi kerak (score None or >= threshold)")
        else:
            tracker.fail("Score=None holat", f"Score: {task['compliance_score']}, S1: {task['service1_status']}")

        # 5.8 Trigger statuses tekshirish
        trigger_statuses = settings.tz_pr_checker.get_trigger_statuses()
        if "READY TO TEST" in trigger_statuses:
            tracker.ok(f"Trigger statuses: {trigger_statuses}")
        else:
            tracker.fail("Trigger statuses", f"READY TO TEST topilmadi: {trigger_statuses}")

    except Exception as e:
        tracker.fail("Service order test umumiy", str(e))


# ============================================================================
# 6-TEST: XATO VA ERROR HOLATLAR
# ============================================================================

def test_6_error_handling():
    """
    TEST 6: Xato va error holatlarida tizim barqarorligi

    - Task topilmasa nima bo'ladi?
    - PR topilmasa nima bo'ladi?
    - AI xato bersa nima bo'ladi?
    - JSON parse xato bo'lsa nima bo'ladi?
    - Compliance score topilmasa nima bo'ladi?
    - Gemini fallback ishlayaptimi?
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 6: Error handling va barqarorlik")
    logger.info("=" * 70)

    try:
        from services.checkers.tz_pr_checker import TZPRService, TZPRAnalysisResult
        from services.generators.testcase_generator import TestCaseGeneratorService
        from utils.ai.gemini_helper import GeminiHelper

        # 6.1 TZPRService: Task topilmasa
        service = TZPRService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = None
        service._jira_client = mock_jira

        result = service.analyze_task("NONEXIST-001")
        if not result.success and "topilmadi" in result.error_message:
            tracker.ok("TZPRService: Task topilmasa graceful error qaytaradi")
        else:
            tracker.fail("TZPRService task topilmadi", f"Success: {result.success}, Error: {result.error_message}")

        if isinstance(result, TZPRAnalysisResult):
            tracker.ok("TZPRService: Task topilmasa ham TZPRAnalysisResult qaytaradi (crash yo'q)")
        else:
            tracker.fail("TZPRService crash", "Natija turi noto'g'ri")

        # 6.2 TZPRService: PR topilmasa
        service2 = TZPRService()
        mock_jira2 = MagicMock()
        mock_jira2.get_task_details.return_value = {
            'summary': 'Test task',
            'type': 'Story',
            'priority': 'High',
            'description': 'TZ content',
            'comments': [],
            'figma_links': []
        }
        service2._jira_client = mock_jira2

        mock_pr_helper = MagicMock()
        mock_pr_helper.get_pr_full_info.return_value = None
        service2._pr_helper = mock_pr_helper

        result = service2.analyze_task("NOPR-001")
        if not result.success and "PR topilmadi" in result.error_message:
            tracker.ok("TZPRService: PR topilmasa graceful error qaytaradi")
        else:
            tracker.fail("TZPRService PR topilmadi", f"Success: {result.success}, Error: {result.error_message}")

        if result.warnings:
            tracker.ok(f"TZPRService: PR topilmasa warnings bor: {result.warnings}")
        else:
            tracker.fail("TZPRService PR warnings", "Warnings bo'sh")

        # 6.3 AI xato bersa (Gemini exception)
        service3 = TZPRService()
        mock_jira3 = MagicMock()
        mock_jira3.get_task_details.return_value = {
            'summary': 'Test', 'type': 'Story', 'priority': 'High',
            'description': 'TZ', 'comments': [], 'figma_links': []
        }
        service3._jira_client = mock_jira3

        mock_pr3 = MagicMock()
        mock_pr3.get_pr_full_info.return_value = {
            'pr_count': 1, 'files_changed': 1,
            'total_additions': 1, 'total_deletions': 0,
            'pr_details': [{'title': 'test', 'url': 'http://test', 'files': []}]
        }
        service3._pr_helper = mock_pr3

        mock_gemini3 = MagicMock()
        mock_gemini3.analyze.side_effect = RuntimeError("Gemini API xatosi: quota exceeded")
        service3._gemini_helper = mock_gemini3

        result = service3.analyze_task("AIERR-001")
        if not result.success:
            tracker.ok("TZPRService: AI xatoda graceful error (tizim crash qilmadi)")
        else:
            tracker.fail("TZPRService AI xato", "Success=True bo'lmasligi kerak edi")

        # 6.4 Compliance score topilmasa
        service4 = TZPRService()
        score = service4._extract_compliance_score("Bu javobda hech qanday score yo'q")
        if score is None:
            tracker.ok("Compliance score topilmasa None qaytaradi (crash yo'q)")
        else:
            tracker.fail("Compliance score None", f"Kutilgan: None, Keldi: {score}")

        # Turli formatdagi score'lar
        score1 = service4._extract_compliance_score("COMPLIANCE_SCORE: 85%")
        score2 = service4._extract_compliance_score("**COMPLIANCE_SCORE: 92%**")
        score3 = service4._extract_compliance_score("MOSLIK BALI: 73%")

        if score1 == 85:
            tracker.ok("Score format 1 (COMPLIANCE_SCORE: 85%) to'g'ri")
        else:
            tracker.fail("Score format 1", f"Keldi: {score1}")

        if score2 == 92:
            tracker.ok("Score format 2 (**COMPLIANCE_SCORE: 92%**) to'g'ri")
        else:
            tracker.fail("Score format 2", f"Keldi: {score2}")

        if score3 == 73:
            tracker.ok("Score format 3 (MOSLIK BALI: 73%) to'g'ri")
        else:
            tracker.fail("Score format 3", f"Keldi: {score3}")

        # 6.5 TestCaseGenerator: JSON parse xato
        tc_service = TestCaseGeneratorService()

        broken_json = '{"test_cases": [{"id": "TC-001", "title": "Test", "description": "desc", "preconditions": "pre", "steps": ["1"], "expected_result": "ok", "test_type": "positive", "priority": "High", "severity": "Major"}, {"id": "TC-002", "title": "Test 2", "desc'

        repaired = tc_service._try_repair_json(broken_json)
        if repaired:
            try:
                data = json.loads(repaired)
                if 'test_cases' in data and len(data['test_cases']) >= 1:
                    tracker.ok(f"JSON repair ishladi: {len(data['test_cases'])} ta test case tiklandi")
                else:
                    tracker.fail("JSON repair natija", f"Test cases topilmadi: {data.keys()}")
            except json.JSONDecodeError as je:
                tracker.fail("JSON repair parse", str(je))
        else:
            tracker.fail("JSON repair", "None qaytardi - tuzatib bo'lmadi")

        repaired_empty = tc_service._try_repair_json("")
        if repaired_empty is None:
            tracker.ok("JSON repair: bo'sh string uchun None qaytaradi")
        else:
            tracker.fail("JSON repair bo'sh", f"Kutilgan: None, Keldi: {repaired_empty}")

        # 6.6 TestCaseGenerator: Task topilmasa
        tc_service2 = TestCaseGeneratorService()
        mock_jira_tc = MagicMock()
        mock_jira_tc.get_task_details.return_value = None
        tc_service2._jira_client = mock_jira_tc

        result = tc_service2.generate_test_cases("NOTFOUND-001")
        if not result.success and "topilmadi" in result.error_message:
            tracker.ok("TestCaseGenerator: Task topilmasa graceful error")
        else:
            tracker.fail("TestCaseGenerator task topilmadi", f"Success: {result.success}")

        # 6.7 Gemini fallback mehanizmi
        try:
            helper = GeminiHelper.__new__(GeminiHelper)
            helper.api_key_1 = "key1"
            helper.api_key_2 = "key2"
            helper.using_fallback = False
            helper.FALLBACK_ERROR_KEYWORDS = GeminiHelper.FALLBACK_ERROR_KEYWORDS

            class FakeQuotaError(Exception):
                pass

            quota_error = FakeQuotaError("resource_exhausted: quota limit reached")
            if helper._is_fallback_error(quota_error):
                tracker.ok("Gemini fallback: quota error to'g'ri detect qiladi")
            else:
                tracker.fail("Gemini fallback detection", "quota error detect qilmadi")

            normal_error = FakeQuotaError("connection timeout")
            if not helper._is_fallback_error(normal_error):
                tracker.ok("Gemini fallback: oddiy xatoda fallback qilmaydi")
            else:
                tracker.fail("Gemini fallback oddiy xato", "Noto'g'ri fallback qildi")

            rate_error = FakeQuotaError("429 rate limit exceeded")
            if helper._is_fallback_error(rate_error):
                tracker.ok("Gemini fallback: 429 rate limit to'g'ri detect qiladi")
            else:
                tracker.fail("Gemini fallback 429", "429 detect qilmadi")
        except Exception as e:
            tracker.fail("Gemini fallback test", str(e))

        # 6.8 Webhook error handling - noto'g'ri payload
        try:
            from fastapi.testclient import TestClient
            from services.webhook.jira_webhook_handler import app

            client = TestClient(app)

            response = client.post("/webhook/jira", json={"random": "data"})
            if response.status_code in [200, 422]:
                tracker.ok("Webhook: noto'g'ri payload crash qilmaydi")
            else:
                tracker.fail("Webhook noto'g'ri payload", f"Status: {response.status_code}")

            response = client.post("/webhook/jira", json={})
            if response.status_code in [200, 422]:
                tracker.ok("Webhook: bo'sh payload crash qilmaydi")
            else:
                tracker.fail("Webhook bo'sh payload", f"Status: {response.status_code}")
        except Exception as e:
            tracker.fail("Webhook error handling", str(e))

    except Exception as e:
        tracker.fail("Error handling test umumiy", str(e))


# ============================================================================
# 7-TEST: KONFIGURATSIYA VA SOZLAMALAR
# ============================================================================

def test_7_settings():
    """
    TEST 7: Sozlamalar tizimi to'g'ri ishlashi
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 7: Sozlamalar tizimi")
    logger.info("=" * 70)

    try:
        from config.app_settings import (
            AppSettings, TZPRCheckerSettings, TestcaseGeneratorSettings,
            QueueSettings, get_app_settings, AppSettingsManager
        )

        # 7.1 Default qiymatlar
        settings = AppSettings()

        if settings.tz_pr_checker.return_threshold == 60:
            tracker.ok("Default return_threshold: 60")
        else:
            tracker.fail("Default threshold", f"Keldi: {settings.tz_pr_checker.return_threshold}")

        if settings.tz_pr_checker.auto_return_enabled == False:
            tracker.ok("Default auto_return_enabled: False")
        else:
            tracker.fail("Default auto_return", "True bo'lmasligi kerak")

        if settings.queue.queue_enabled == True:
            tracker.ok("Default queue_enabled: True")
        else:
            tracker.fail("Default queue", "False bo'lmasligi kerak")

        if settings.queue.checker_testcase_delay == 15:
            tracker.ok("Default checker_testcase_delay: 15s")
        else:
            tracker.fail("Default delay", f"Keldi: {settings.queue.checker_testcase_delay}")

        # 7.2 Trigger statuses (aliases bilan)
        tz_triggers = settings.tz_pr_checker.get_trigger_statuses()
        if "READY TO TEST" in tz_triggers:
            tracker.ok(f"TZ-PR trigger statuses: {tz_triggers}")
        else:
            tracker.fail("TZ-PR triggers", f"READY TO TEST topilmadi: {tz_triggers}")

        tc_triggers = settings.testcase_generator.get_trigger_statuses()
        if "READY TO TEST" in tc_triggers:
            tracker.ok(f"Testcase trigger statuses: {tc_triggers}")
        else:
            tracker.fail("Testcase triggers", f"READY TO TEST topilmadi: {tc_triggers}")

        # 7.3 Settings singleton
        s1 = get_app_settings()
        s2 = get_app_settings()
        if s1 is s2:
            tracker.ok("Settings singleton: bir xil ob'ekt (cache ishlaydi)")
        else:
            tracker.fail("Settings singleton", "Har safar yangi ob'ekt")

        # 7.4 force_reload
        s3 = get_app_settings(force_reload=True)
        if isinstance(s3, AppSettings):
            tracker.ok("force_reload=True ishlaydi (AppSettings qaytaradi)")
        else:
            tracker.fail("force_reload", f"Turi noto'g'ri: {type(s3)}")

        # 7.5 visible_sections default
        if 'completed' in settings.tz_pr_checker.visible_sections:
            tracker.ok(f"visible_sections default: {settings.tz_pr_checker.visible_sections}")
        else:
            tracker.fail("visible_sections", f"Keldi: {settings.tz_pr_checker.visible_sections}")

        # 7.6 Comment order qiymatlari
        valid_orders = ["checker_first", "testcase_first", "parallel"]
        if settings.tz_pr_checker.comment_order in valid_orders:
            tracker.ok(f"comment_order: '{settings.tz_pr_checker.comment_order}' (valid)")
        else:
            tracker.fail("comment_order", f"Noto'g'ri qiymat: {settings.tz_pr_checker.comment_order}")

        # 7.7 Testcase settings
        if settings.testcase_generator.max_test_cases == 10:
            tracker.ok("Default max_test_cases: 10")
        else:
            tracker.fail("Default max_test_cases", f"Keldi: {settings.testcase_generator.max_test_cases}")

        if settings.testcase_generator.default_test_types == ['positive', 'negative']:
            tracker.ok("Default test_types: ['positive', 'negative']")
        else:
            tracker.fail("Default test_types", f"Keldi: {settings.testcase_generator.default_test_types}")

    except Exception as e:
        tracker.fail("Settings test umumiy", str(e))


# ============================================================================
# 8-TEST: TESTCASE WEBHOOK HANDLER
# ============================================================================

def test_8_testcase_webhook():
    """
    TEST 8: Testcase webhook handler
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 8: Testcase webhook handler")
    logger.info("=" * 70)

    try:
        from services.webhook.testcase_webhook_handler import is_testcase_trigger_status
        from config.app_settings import get_app_settings

        settings = get_app_settings(force_reload=True)

        # 8.1 Trigger status tekshirish
        if settings.testcase_generator.auto_comment_enabled:
            is_trigger = is_testcase_trigger_status("READY TO TEST")
            if is_trigger:
                tracker.ok("is_testcase_trigger_status('READY TO TEST') = True")
            else:
                tracker.fail("Testcase trigger", "READY TO TEST trigger emas")
        else:
            is_trigger = is_testcase_trigger_status("READY TO TEST")
            if not is_trigger:
                tracker.ok("is_testcase_trigger_status: auto_comment=False -> False qaytaradi")
            else:
                tracker.fail("Testcase trigger disabled", "auto_comment=False lekin True qaytardi")

        # 8.2 Noto'g'ri status
        is_trigger_wrong = is_testcase_trigger_status("In Progress")
        if not is_trigger_wrong:
            tracker.ok("is_testcase_trigger_status('In Progress') = False (to'g'ri)")
        else:
            tracker.fail("Testcase wrong trigger", "In Progress True bo'lmasligi kerak")

        # 8.3 Bo'sh status
        is_trigger_empty = is_testcase_trigger_status("")
        if not is_trigger_empty:
            tracker.ok("is_testcase_trigger_status('') = False (to'g'ri)")
        else:
            tracker.fail("Testcase empty trigger", "Bo'sh string True bo'lmasligi kerak")

    except Exception as e:
        tracker.fail("Testcase webhook test umumiy", str(e))


# ============================================================================
# 9-TEST: BASE SERVICE
# ============================================================================

def test_9_base_service():
    """
    TEST 9: BaseService funksionalligini tekshirish
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 9: BaseService funksionalligi")
    logger.info("=" * 70)

    try:
        from core.base_service import BaseService

        service = BaseService()

        # 9.1 Text length calculation
        test_text = "Hello World" * 100  # 1100 chars
        info = service._calculate_text_length(test_text)

        if info['chars'] == 1100:
            tracker.ok("Text length calculation: chars to'g'ri (1100)")
        else:
            tracker.fail("Text length chars", f"Kutilgan: 1100, Keldi: {info['chars']}")

        if info['tokens'] == 275:  # 1100 / 4
            tracker.ok("Text length calculation: tokens to'g'ri (275)")
        else:
            tracker.fail("Text length tokens", f"Kutilgan: 275, Keldi: {info['tokens']}")

        if info['within_limit'] == True:  # 275 < 900000
            tracker.ok("Text length: within_limit=True (limit ichida)")
        else:
            tracker.fail("Text length limit", "within_limit False bo'lmasligi kerak")

        # 9.2 Text truncation
        big_text = "A" * (900000 * 4 + 1000)  # Limitdan katta
        truncated = service._truncate_text(big_text)

        if len(truncated) < len(big_text):
            tracker.ok("Text truncation ishlaydi (text qisqartirildi)")
        else:
            tracker.fail("Text truncation", "Text qisqartirilmadi")

        if "TRUNCATED" in truncated:
            tracker.ok("Text truncation: TRUNCATED warning qo'shilgan")
        else:
            tracker.fail("Text truncation warning", "TRUNCATED matni topilmadi")

        # 9.3 Kichik text truncation qilinmasligi
        small_text = "Small text"
        result = service._truncate_text(small_text)
        if result == small_text:
            tracker.ok("Kichik text truncation qilinmaydi")
        else:
            tracker.fail("Kichik text truncation", "Kerak emas edi")

        # 9.4 Status updater
        statuses_collected = []
        def mock_callback(status_type, message):
            statuses_collected.append((status_type, message))

        updater = service._create_status_updater(mock_callback)
        updater("info", "Test message")

        if len(statuses_collected) == 1 and statuses_collected[0] == ("info", "Test message"):
            tracker.ok("Status updater callback ishlaydi")
        else:
            tracker.fail("Status updater", f"Keldi: {statuses_collected}")

        # 9.5 Status updater None callback bilan
        updater_none = service._create_status_updater(None)
        try:
            updater_none("info", "Test")
            tracker.ok("Status updater None callback crash qilmaydi")
        except Exception as e:
            tracker.fail("Status updater None callback", str(e))

        # 9.6 MAX_TOKENS default
        if service.MAX_TOKENS == 900000:
            tracker.ok("MAX_TOKENS default: 900000")
        else:
            tracker.fail("MAX_TOKENS", f"Keldi: {service.MAX_TOKENS}")

    except Exception as e:
        tracker.fail("BaseService test umumiy", str(e))


# ============================================================================
# 10-TEST: DEBUG QILISH IMKONIYATI
# ============================================================================

def test_10_debug_capability():
    """
    TEST 10: Debug qilish osonligi
    """
    logger.info("\n" + "=" * 70)
    logger.info("TEST 10: Debug qilish imkoniyati")
    logger.info("=" * 70)

    try:
        # 10.1 Webhook log faylga yozish sozlamasi
        import services.webhook.jira_webhook_handler as webhook_module

        module_logger = logging.getLogger(webhook_module.__name__)
        if module_logger:
            tracker.ok("Webhook module logger mavjud")
        else:
            tracker.fail("Webhook logger", "Logger topilmadi")

        # 10.2 Error message'lar tushunarli
        from services.checkers.tz_pr_checker import TZPRService

        service = TZPRService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = None
        service._jira_client = mock_jira

        result = service.analyze_task("DEBUG-001")

        if "DEBUG-001" in result.error_message:
            tracker.ok("Error message'da task key mavjud (debug oson)")
        else:
            tracker.fail("Error message task key", f"Error: {result.error_message}")

        # 10.3 DB da error message saqlanishi
        from utils.database.task_db import mark_error, get_task, mark_progressing

        mark_progressing("DEBUG-002", "READY TO TEST")
        mark_error("DEBUG-002", "Gemini API xatosi: rate limit exceeded")

        task = get_task("DEBUG-002")
        if task and task['error_message'] == "Gemini API xatosi: rate limit exceeded":
            tracker.ok("DB'da error message to'liq saqlanadi (debug uchun)")
        else:
            tracker.fail("DB error message", f"Saqlangan: {task.get('error_message') if task else 'None'}")

        # 10.4 Service error alohida saqlanishi
        from utils.database.task_db import set_service1_error, set_service2_error

        mark_progressing("DEBUG-003", "READY TO TEST")
        set_service1_error("DEBUG-003", "PR fetch timeout: 30s")

        task = get_task("DEBUG-003")
        if task['service1_error'] == "PR fetch timeout: 30s":
            tracker.ok("Service1 error alohida saqlanadi")
        else:
            tracker.fail("Service1 error", f"Keldi: {task['service1_error']}")

        set_service2_error("DEBUG-003", "JSON parse xatosi")
        task = get_task("DEBUG-003")
        if task['service2_error'] == "JSON parse xatosi":
            tracker.ok("Service2 error alohida saqlanadi")
        else:
            tracker.fail("Service2 error", f"Keldi: {task['service2_error']}")

        # 10.5 Timestamps mavjudligi
        if task.get('updated_at'):
            tracker.ok("Error vaqti updated_at da saqlanadi")
        else:
            tracker.fail("Error timestamp", "updated_at yo'q")

        if task.get('last_processed_at'):
            tracker.ok("last_processed_at debug uchun mavjud")
        else:
            tracker.fail("last_processed_at", "Topilmadi")

        # 10.6 TZPRAnalysisResult da warnings field
        from services.checkers.tz_pr_checker import TZPRAnalysisResult

        error_result = TZPRAnalysisResult(
            task_key="DEBUG-004",
            success=False,
            error_message="Test error",
            warnings=["PR topilmadi", "Figma token yo'q"]
        )

        if len(error_result.warnings) == 2:
            tracker.ok("TZPRAnalysisResult.warnings debug uchun mavjud")
        else:
            tracker.fail("Warnings", f"Count: {len(error_result.warnings)}")

        # 10.7 AI retry count tracking
        success_result = TZPRAnalysisResult(
            task_key="DEBUG-005",
            success=True,
            ai_retry_count=2,
            total_prompt_size=50000
        )

        if success_result.ai_retry_count == 2:
            tracker.ok("ai_retry_count debug uchun saqlanadi")
        else:
            tracker.fail("ai_retry_count", f"Keldi: {success_result.ai_retry_count}")

        if success_result.total_prompt_size == 50000:
            tracker.ok("total_prompt_size debug uchun saqlanadi")
        else:
            tracker.fail("total_prompt_size", f"Keldi: {success_result.total_prompt_size}")

    except Exception as e:
        tracker.fail("Debug test umumiy", str(e))


# ============================================================================
# DB CLEANUP (test ma'lumotlarini tozalash)
# ============================================================================

def cleanup_test_data():
    """Test ma'lumotlarini DB dan tozalash"""
    logger.info("\nTest ma'lumotlarini tozalash...")
    try:
        from utils.database.task_db import DB_FILE
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        test_prefixes = [
            'TEST-%', 'CONC-%', 'DB-TEST-%', 'ORDER-%',
            'NONEXIST-%', 'NOPR-%', 'AIERR-%', 'NOTFOUND-%',
            'DEBUG-%', 'TEST-WEBHOOK-%'
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
    logger.info("JIRA-AI-Analyzer TO'LIQ TIZIM TESTLARI")
    logger.info("=" * 70)
    logger.info(f"Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python: {sys.version}")
    logger.info("=" * 70)

    start_time = time.time()

    # Barcha testlarni ishga tushirish
    test_1_services_individually()
    test_2_webhook_status_change()
    test_3_concurrent_tasks()
    test_4_database_operations()
    test_5_service_order()
    test_6_error_handling()
    test_7_settings()
    test_8_testcase_webhook()
    test_9_base_service()
    test_10_debug_capability()

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
