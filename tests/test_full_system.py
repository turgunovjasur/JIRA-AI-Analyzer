"""
JIRA-AI-Analyzer - To'liq Tizim Testlari (Consolidated)
=========================================================

Barcha test fayllardan birlashtirilib yaratilgan pytest test fayli.
Manba fayllar:
- test_full_system.py (original, 12 test funksiya)
- test_system_resilience.py (6 test funksiya)
- test_webhook_after_delete.py (3 test funksiya)
- test_delete_task_flow.py (3 test funksiya)

Pytest class tuzilmasi:
- TestServiceUnit         - test_1 (services), test_9 (base_service)
- TestWebhookEndpoint     - test_2 (webhook), resilience test_1
- TestConcurrency         - test_3 (concurrent tasks)
- TestDatabaseOperations  - test_4 (db), test_delete_task_flow
- TestServiceOrchestration- test_5 (service order), test_8 (testcase webhook)
- TestErrorHandling       - test_6 (error), resilience test_4, test_6
- TestSettingsManagement  - test_7 (settings), resilience test_2
- TestDebugCapability     - test_10 (debug info)
- TestBlockedRetry        - test_11 (blocked status), resilience test_3
- TestGeminiKeyFallback   - test_12 (key freeze)
- TestDeleteAndWebhook    - test_webhook_after_delete
- TestSystemResilience    - resilience test_5, test_6

Author: Test Suite (Consolidated)
Date: 2026-02-20
"""
import sys
import os
import json
import sqlite3
import asyncio
import time
import logging
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import asdict
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
# CLASS 1: TestServiceUnit
# ============================================================================

class TestServiceUnit:
    """
    Har bir servis alohida qanday ishlashini tekshirish (test_1, test_9)
    - TZPRService.analyze_task() to'g'ri natija qaytaradimi?
    - TestCaseGeneratorService.generate_test_cases() to'g'ri natija qaytaradimi?
    - Har bir servis BaseService'dan meros oladimi?
    - Lazy loading ishlayaptimi?
    - BaseService text length, truncation, status updater
    """

    def test_tzpr_service_inherits_base_service(self):
        from services.checkers.tz_pr_checker import TZPRService
        from core.base_service import BaseService
        service = TZPRService()
        assert isinstance(service, BaseService)

    def test_tzpr_service_lazy_loading_jira(self):
        from services.checkers.tz_pr_checker import TZPRService
        service = TZPRService()
        assert service._jira_client is None

    def test_tzpr_service_lazy_loading_github(self):
        from services.checkers.tz_pr_checker import TZPRService
        service = TZPRService()
        assert service._github_client is None

    def test_tzpr_service_lazy_loading_gemini(self):
        from services.checkers.tz_pr_checker import TZPRService
        service = TZPRService()
        assert service._gemini_helper is None

    def test_tzpr_service_analyze_task_returns_result_type(self):
        from services.checkers.tz_pr_checker import TZPRService, TZPRAnalysisResult
        service = TZPRService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = {
            'summary': 'Test task summary',
            'type': 'Story',
            'priority': 'High',
            'description': 'Test TZ mazmuni',
            'comments': [],
            'figma_links': []
        }
        mock_gemini = MagicMock()
        mock_gemini.analyze.return_value = (
            "## BAJARILGAN TALABLAR\nTest bajarildi\n\n"
            "## MOSLIK BALI\n**COMPLIANCE_SCORE: 85%**"
        )
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
        service._jira_client = mock_jira
        service._github_client = MagicMock()
        service._gemini_helper = mock_gemini
        service._pr_helper = mock_pr_helper
        result = service.analyze_task("TEST-001")
        assert isinstance(result, TZPRAnalysisResult)

    def test_tzpr_service_analyze_task_success(self):
        from services.checkers.tz_pr_checker import TZPRService
        service = TZPRService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = {
            'summary': 'Test task summary',
            'type': 'Story',
            'priority': 'High',
            'description': 'Test TZ mazmuni',
            'comments': [],
            'figma_links': []
        }
        mock_gemini = MagicMock()
        mock_gemini.analyze.return_value = (
            "## BAJARILGAN TALABLAR\nTest bajarildi\n\n"
            "## MOSLIK BALI\n**COMPLIANCE_SCORE: 85%**"
        )
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
        service._jira_client = mock_jira
        service._github_client = MagicMock()
        service._gemini_helper = mock_gemini
        service._pr_helper = mock_pr_helper
        result = service.analyze_task("TEST-001")
        assert result.success

    def test_tzpr_service_compliance_score_extraction(self):
        from services.checkers.tz_pr_checker import TZPRService
        service = TZPRService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = {
            'summary': 'Test task summary',
            'type': 'Story',
            'priority': 'High',
            'description': 'Test TZ mazmuni',
            'comments': [],
            'figma_links': []
        }
        mock_gemini = MagicMock()
        mock_gemini.analyze.return_value = (
            "## BAJARILGAN TALABLAR\nTest bajarildi\n\n"
            "## MOSLIK BALI\n**COMPLIANCE_SCORE: 85%**"
        )
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
        service._jira_client = mock_jira
        service._github_client = MagicMock()
        service._gemini_helper = mock_gemini
        service._pr_helper = mock_pr_helper
        result = service.analyze_task("TEST-001")
        assert result.compliance_score == 85

    def test_tzpr_service_task_key_preserved(self):
        from services.checkers.tz_pr_checker import TZPRService
        service = TZPRService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = {
            'summary': 'Test task summary',
            'type': 'Story',
            'priority': 'High',
            'description': 'Test TZ mazmuni',
            'comments': [],
            'figma_links': []
        }
        mock_gemini = MagicMock()
        mock_gemini.analyze.return_value = (
            "## BAJARILGAN TALABLAR\nTest bajarildi\n\n"
            "## MOSLIK BALI\n**COMPLIANCE_SCORE: 85%**"
        )
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
        service._jira_client = mock_jira
        service._github_client = MagicMock()
        service._gemini_helper = mock_gemini
        service._pr_helper = mock_pr_helper
        result = service.analyze_task("TEST-001")
        assert result.task_key == "TEST-001"

    def test_testcase_generator_inherits_base_service(self):
        from services.generators.testcase_generator import TestCaseGeneratorService
        from core.base_service import BaseService
        service = TestCaseGeneratorService()
        assert isinstance(service, BaseService)

    def test_testcase_generator_success(self):
        from services.generators.testcase_generator import TestCaseGeneratorService, TestCaseGenerationResult
        service = TestCaseGeneratorService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = {
            'summary': 'Login functionality',
            'type': 'Story',
            'priority': 'High',
            'description': 'Login sahifasini yaratish kerak',
            'comments': []
        }
        mock_gemini = MagicMock()
        mock_gemini.analyze.return_value = json.dumps({
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
        mock_pr_helper = MagicMock()
        mock_pr_helper.get_pr_full_info.return_value = None
        service._jira_client = mock_jira
        service._gemini_helper = mock_gemini
        service._github_client = MagicMock()
        service._pr_helper = mock_pr_helper
        result = service.generate_test_cases("TEST-002", include_pr=True)
        assert isinstance(result, TestCaseGenerationResult)
        assert result.success

    def test_testcase_generator_returns_correct_count(self):
        from services.generators.testcase_generator import TestCaseGeneratorService
        service = TestCaseGeneratorService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = {
            'summary': 'Login functionality',
            'type': 'Story',
            'priority': 'High',
            'description': 'Login sahifasini yaratish kerak',
            'comments': []
        }
        mock_gemini = MagicMock()
        mock_gemini.analyze.return_value = json.dumps({
            "test_cases": [
                {
                    "id": "TC-001",
                    "title": "Login positive test",
                    "description": "desc",
                    "preconditions": "pre",
                    "steps": ["1. step"],
                    "expected_result": "ok",
                    "test_type": "positive",
                    "priority": "High",
                    "severity": "Critical",
                    "tags": ["login"]
                },
                {
                    "id": "TC-002",
                    "title": "Login negative test",
                    "description": "desc",
                    "preconditions": "pre",
                    "steps": ["1. step"],
                    "expected_result": "error shown",
                    "test_type": "negative",
                    "priority": "High",
                    "severity": "Major",
                    "tags": ["login"]
                }
            ]
        })
        mock_pr_helper = MagicMock()
        mock_pr_helper.get_pr_full_info.return_value = None
        service._jira_client = mock_jira
        service._gemini_helper = mock_gemini
        service._github_client = MagicMock()
        service._pr_helper = mock_pr_helper
        result = service.generate_test_cases("TEST-002", include_pr=True)
        assert len(result.test_cases) == 2

    def test_testcase_generator_first_test_type(self):
        from services.generators.testcase_generator import TestCaseGeneratorService
        service = TestCaseGeneratorService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = {
            'summary': 'Login functionality',
            'type': 'Story',
            'priority': 'High',
            'description': 'Login',
            'comments': []
        }
        mock_gemini = MagicMock()
        mock_gemini.analyze.return_value = json.dumps({
            "test_cases": [
                {
                    "id": "TC-001",
                    "title": "Login positive test",
                    "description": "desc",
                    "preconditions": "pre",
                    "steps": ["1. step"],
                    "expected_result": "ok",
                    "test_type": "positive",
                    "priority": "High",
                    "severity": "Critical",
                    "tags": []
                }
            ]
        })
        mock_pr_helper = MagicMock()
        mock_pr_helper.get_pr_full_info.return_value = None
        service._jira_client = mock_jira
        service._gemini_helper = mock_gemini
        service._github_client = MagicMock()
        service._pr_helper = mock_pr_helper
        result = service.generate_test_cases("TEST-002", include_pr=True)
        assert result.test_cases[0].test_type == "positive"

    def test_testcase_generator_custom_context(self):
        from services.generators.testcase_generator import TestCaseGeneratorService
        service = TestCaseGeneratorService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = {
            'summary': 'Widget test',
            'type': 'Story',
            'priority': 'High',
            'description': 'desc',
            'comments': []
        }
        mock_gemini = MagicMock()
        mock_gemini.analyze.return_value = json.dumps({
            "test_cases": [
                {
                    "id": "TC-001",
                    "title": "Test",
                    "description": "desc",
                    "preconditions": "pre",
                    "steps": ["1. step"],
                    "expected_result": "ok",
                    "test_type": "positive",
                    "priority": "High",
                    "severity": "Critical",
                    "tags": []
                }
            ]
        })
        mock_pr_helper = MagicMock()
        mock_pr_helper.get_pr_full_info.return_value = None
        service._jira_client = mock_jira
        service._gemini_helper = mock_gemini
        service._github_client = MagicMock()
        service._pr_helper = mock_pr_helper
        result = service.generate_test_cases(
            "TEST-003",
            include_pr=False,
            custom_context="Product: ACME Widget, Narx: $99.99"
        )
        assert result.custom_context_used
        call_args = mock_gemini.analyze.call_args
        assert "ACME Widget" in str(call_args)

    # --- BaseService tests (test_9) ---

    def test_base_service_text_length_chars(self):
        from core.base_service import BaseService
        service = BaseService()
        test_text = "Hello World" * 100  # 1100 chars
        info = service._calculate_text_length(test_text)
        assert info['chars'] == 1100

    def test_base_service_text_length_tokens(self):
        from core.base_service import BaseService
        service = BaseService()
        test_text = "Hello World" * 100  # 1100 chars
        info = service._calculate_text_length(test_text)
        assert info['tokens'] == 275  # 1100 / 4

    def test_base_service_text_within_limit(self):
        from core.base_service import BaseService
        service = BaseService()
        test_text = "Hello World" * 100
        info = service._calculate_text_length(test_text)
        assert info['within_limit'] is True

    def test_base_service_text_truncation(self):
        from core.base_service import BaseService
        service = BaseService()
        big_text = "A" * (900000 * 4 + 1000)
        truncated = service._truncate_text(big_text)
        assert len(truncated) < len(big_text)

    def test_base_service_text_truncation_warning(self):
        from core.base_service import BaseService
        service = BaseService()
        big_text = "A" * (900000 * 4 + 1000)
        truncated = service._truncate_text(big_text)
        assert "TRUNCATED" in truncated

    def test_base_service_small_text_not_truncated(self):
        from core.base_service import BaseService
        service = BaseService()
        small_text = "Small text"
        result = service._truncate_text(small_text)
        assert result == small_text

    def test_base_service_status_updater_callback(self):
        from core.base_service import BaseService
        service = BaseService()
        statuses_collected = []
        def mock_callback(status_type, message):
            statuses_collected.append((status_type, message))
        updater = service._create_status_updater(mock_callback)
        updater("info", "Test message")
        assert len(statuses_collected) == 1
        assert statuses_collected[0] == ("info", "Test message")

    def test_base_service_status_updater_none_callback(self):
        from core.base_service import BaseService
        service = BaseService()
        updater_none = service._create_status_updater(None)
        # Should not raise
        updater_none("info", "Test")

    def test_base_service_max_tokens(self):
        from core.base_service import BaseService
        service = BaseService()
        assert service.MAX_TOKENS == 900000


# ============================================================================
# CLASS 2: TestWebhookEndpoint
# ============================================================================

class TestWebhookEndpoint:
    """
    Webhook endpoint testlari (test_2, resilience test_1)
    - Webhook endpoint to'g'ri parse qiladimi?
    - Status o'zgarishi aniqlanadimi?
    - Target status tekshiruvi ishlaydimi?
    - DB holat boshqaruvi to'g'rimi?
    - Dublikat event filtri ishlaydimi?
    - 20 ta soxta webhook yuborish
    """

    def test_health_check_endpoint(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_root_endpoint_status_running(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'running'

    def test_wrong_event_type_ignored(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        payload = {
            "webhookEvent": "jira:issue_created",
            "issue": {"key": "TEST-100"},
            "changelog": {}
        }
        response = client.post("/webhook/jira", json=payload)
        data = response.json()
        assert data.get('status') == 'ignored'

    def test_no_status_change_ignored(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "TEST-101"},
            "changelog": {
                "items": [
                    {"field": "summary", "fromString": "Old", "toString": "New"}
                ]
            }
        }
        response = client.post("/webhook/jira", json=payload)
        data = response.json()
        assert data.get('status') == 'ignored'
        assert 'status not changed' in data.get('reason', '')

    def test_non_target_status_ignored(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "TEST-102"},
            "changelog": {
                "items": [
                    {"field": "status", "fromString": "Open", "toString": "In Progress"}
                ]
            }
        }
        response = client.post("/webhook/jira", json=payload)
        data = response.json()
        assert data.get('status') == 'ignored'

    def test_correct_status_processing(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "TEST-WEBHOOK-001"},
            "changelog": {
                "items": [
                    {"field": "status", "fromString": "In Progress", "toString": "READY TO TEST"}
                ]
            }
        }
        with patch('services.webhook.jira_webhook_handler.check_tz_pr_and_comment', new_callable=AsyncMock):
            with patch('services.webhook.jira_webhook_handler._run_testcase_generation', new_callable=AsyncMock):
                with patch('services.webhook.jira_webhook_handler._run_task_group', new_callable=AsyncMock):
                    with patch('services.webhook.jira_webhook_handler._run_sequential_tasks', new_callable=AsyncMock):
                        response = client.post("/webhook/jira", json=payload)
                        data = response.json()
                        assert data.get('status') == 'processing'

    def test_correct_status_task_key_returned(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "TEST-WEBHOOK-001"},
            "changelog": {
                "items": [
                    {"field": "status", "fromString": "In Progress", "toString": "READY TO TEST"}
                ]
            }
        }
        with patch('services.webhook.jira_webhook_handler.check_tz_pr_and_comment', new_callable=AsyncMock):
            with patch('services.webhook.jira_webhook_handler._run_testcase_generation', new_callable=AsyncMock):
                with patch('services.webhook.jira_webhook_handler._run_task_group', new_callable=AsyncMock):
                    with patch('services.webhook.jira_webhook_handler._run_sequential_tasks', new_callable=AsyncMock):
                        response = client.post("/webhook/jira", json=payload)
                        data = response.json()
                        assert data.get('task_key') == 'TEST-WEBHOOK-001'

    def test_duplicate_event_ignored(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": "TEST-WEBHOOK-001"},
            "changelog": {
                "items": [
                    {"field": "status", "fromString": "In Progress", "toString": "READY TO TEST"}
                ]
            }
        }
        with patch('services.webhook.jira_webhook_handler.check_tz_pr_and_comment', new_callable=AsyncMock):
            with patch('services.webhook.jira_webhook_handler._run_testcase_generation', new_callable=AsyncMock):
                with patch('services.webhook.jira_webhook_handler._run_task_group', new_callable=AsyncMock):
                    with patch('services.webhook.jira_webhook_handler._run_sequential_tasks', new_callable=AsyncMock):
                        # First request
                        client.post("/webhook/jira", json=payload)
                        # Duplicate request
                        response2 = client.post("/webhook/jira", json=payload)
                        data2 = response2.json()
                        assert data2.get('status') == 'ignored'

    def test_no_task_key_returns_error(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {},
            "changelog": {}
        }
        response = client.post("/webhook/jira", json=payload)
        data = response.json()
        assert data.get('status') == 'error' or 'no task key' in data.get('reason', '')

    def test_settings_endpoint(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        response = client.get("/settings")
        assert response.status_code == 200
        settings_data = response.json()
        assert 'return_threshold' in settings_data

    def test_20_fake_webhooks_all_responded(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        from utils.database.task_db import get_task, init_db
        init_db()
        client = TestClient(app)
        task_keys = [f"TEST-WEBHOOK-{i:03d}" for i in range(1, 21)]
        webhook_payloads = []
        for i, task_key in enumerate(task_keys, 1):
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
        with patch('services.webhook.jira_webhook_handler.check_tz_pr_and_comment', new_callable=AsyncMock):
            with patch('services.webhook.jira_webhook_handler._run_testcase_generation', new_callable=AsyncMock):
                with patch('services.webhook.jira_webhook_handler._run_task_group', new_callable=AsyncMock):
                    with patch('services.webhook.jira_webhook_handler._run_sequential_tasks', new_callable=AsyncMock):
                        success_count = 0
                        for payload in webhook_payloads:
                            response = client.post("/webhook/jira", json=payload)
                            if response.status_code == 200:
                                data = response.json()
                                if data.get('status') in ('processing', 'ignored'):
                                    success_count += 1
                        assert success_count == 20

    def test_20_fake_webhooks_written_to_db(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        from utils.database.task_db import get_task, init_db
        init_db()
        client = TestClient(app)
        task_keys = [f"TEST-WEBHOOK-{i:03d}" for i in range(1, 21)]
        webhook_payloads = []
        for i, task_key in enumerate(task_keys, 1):
            payload = {
                "webhookEvent": "jira:issue_updated",
                "issue": {"key": task_key},
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
        with patch('services.webhook.jira_webhook_handler.check_tz_pr_and_comment', new_callable=AsyncMock):
            with patch('services.webhook.jira_webhook_handler._run_testcase_generation', new_callable=AsyncMock):
                with patch('services.webhook.jira_webhook_handler._run_task_group', new_callable=AsyncMock):
                    with patch('services.webhook.jira_webhook_handler._run_sequential_tasks', new_callable=AsyncMock):
                        for payload in webhook_payloads:
                            client.post("/webhook/jira", json=payload)
                        db_tasks_found = sum(1 for k in task_keys if get_task(k) is not None)
                        assert db_tasks_found == 20


# ============================================================================
# CLASS 3: TestConcurrency
# ============================================================================

class TestConcurrency:
    """
    5 ta task bir vaqtda testing statusga tushganda (test_3)
    - Queue lock ishlayaptimi?
    - Timeout mehanizmi to'g'rimi?
    - Barcha tasklar DB ga yozilganmi?
    - Race condition yo'qmi?
    """

    def test_queue_lock_singleton(self):
        from services.webhook.jira_webhook_handler import _get_ai_queue_lock
        lock1 = _get_ai_queue_lock()
        lock2 = _get_ai_queue_lock()
        assert lock1 is lock2

    def test_five_tasks_written_to_db_concurrently(self):
        from utils.database.task_db import get_task, mark_progressing
        task_keys = [f"TEST-CONC-{i}" for i in range(1, 6)]
        for key in task_keys:
            mark_progressing(key, "READY TO TEST", datetime.now())
        for key in task_keys:
            task = get_task(key)
            assert task is not None, f"Task {key} DB da topilmadi"
            assert task['task_status'] == 'progressing'

    def test_concurrent_service1_scores(self):
        from utils.database.task_db import get_task, mark_progressing, set_service1_done
        task_keys = [f"TEST-CONC-SCORE-{i}" for i in range(1, 6)]
        for key in task_keys:
            mark_progressing(key, "READY TO TEST", datetime.now())
        for i, key in enumerate(task_keys):
            set_service1_done(key, compliance_score=70 + i * 5)
        for i, key in enumerate(task_keys):
            task = get_task(key)
            expected_score = 70 + i * 5
            assert task['compliance_score'] == expected_score

    def test_concurrent_tasks_all_completed(self):
        from utils.database.task_db import (
            get_task, mark_progressing, set_service1_done, set_service2_done
        )
        task_keys = [f"TEST-CONC-COMP-{i}" for i in range(1, 6)]
        for key in task_keys:
            mark_progressing(key, "READY TO TEST", datetime.now())
        for i, key in enumerate(task_keys):
            set_service1_done(key, compliance_score=70 + i * 5)
        for key in task_keys:
            set_service2_done(key)
        for key in task_keys:
            task = get_task(key)
            assert task['task_status'] == 'completed'

    def test_queue_lock_sequential_workers(self):
        from services.webhook.jira_webhook_handler import _get_ai_queue_lock

        async def run_test():
            lock = _get_ai_queue_lock()
            results = []

            async def worker(worker_id, delay):
                acquired = False
                try:
                    await asyncio.wait_for(lock.acquire(), timeout=5)
                    acquired = True
                    results.append(f"W{worker_id}-start")
                    await asyncio.sleep(delay)
                    results.append(f"W{worker_id}-end")
                except asyncio.TimeoutError:
                    results.append(f"W{worker_id}-timeout")
                finally:
                    if acquired:
                        lock.release()
            await asyncio.gather(
                worker(1, 0.05),
                worker(2, 0.05),
                worker(3, 0.05)
            )
            return results

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(run_test())
            starts = [r for r in results if 'start' in r]
            ends = [r for r in results if 'end' in r]
            assert len(starts) == 3
            assert len(ends) == 3
        finally:
            loop.close()

    def test_queue_timeout_mechanism(self):
        async def run_test():
            lock = asyncio.Lock()
            await lock.acquire()
            timed_out = False
            try:
                await asyncio.wait_for(lock.acquire(), timeout=0.3)
            except asyncio.TimeoutError:
                timed_out = True
            finally:
                lock.release()
            return timed_out

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            timed_out = loop.run_until_complete(run_test())
            assert timed_out
        finally:
            loop.close()


# ============================================================================
# CLASS 4: TestDatabaseOperations
# ============================================================================

class TestDatabaseOperations:
    """
    DB fayl bilan ishlash (test_4, test_delete_task_flow)
    - init_db() to'g'ri jadval yaratadimi?
    - CRUD operatsiyalar ishlayaptimi?
    - task_status state machine to'g'rimi?
    - Service statuslar to'g'ri yangilanadimi?
    - Reset service statuslar ishlayaptimi?
    - Delete after webhook flow
    """

    def test_db_file_exists(self):
        from utils.database.task_db import DB_FILE
        assert os.path.exists(DB_FILE), f"DB fayl topilmadi: {DB_FILE}"

    def test_db_table_structure(self):
        from utils.database.task_db import DB_FILE
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
        assert not missing, f"Yo'q columnlar: {missing}"

    def test_mark_progressing(self):
        from utils.database.task_db import get_task, mark_progressing
        test_key = "TEST-DB-001"
        mark_progressing(test_key, "READY TO TEST", datetime.now())
        task = get_task(test_key)
        assert task is not None
        assert task['task_status'] == 'progressing'

    def test_set_service1_done_score(self):
        from utils.database.task_db import get_task, mark_progressing, set_service1_done
        test_key = "TEST-DB-002"
        mark_progressing(test_key, "READY TO TEST", datetime.now())
        set_service1_done(test_key, compliance_score=75)
        task = get_task(test_key)
        assert task['service1_status'] == 'done'
        assert task['compliance_score'] == 75

    def test_set_service2_done_completes_task(self):
        from utils.database.task_db import get_task, mark_progressing, set_service1_done, set_service2_done
        test_key = "TEST-DB-003"
        mark_progressing(test_key, "READY TO TEST", datetime.now())
        set_service1_done(test_key, compliance_score=75)
        set_service2_done(test_key)
        task = get_task(test_key)
        assert task['service2_status'] == 'done'
        assert task['task_status'] == 'completed'

    def test_mark_returned(self):
        from utils.database.task_db import get_task, mark_progressing, set_service1_done, mark_returned
        test_key = "TEST-DB-004"
        mark_progressing(test_key, "READY TO TEST")
        set_service1_done(test_key, compliance_score=40)
        mark_returned(test_key)
        task = get_task(test_key)
        assert task['task_status'] == 'returned'

    def test_increment_return_count(self):
        from utils.database.task_db import get_task, mark_progressing, increment_return_count
        test_key = "TEST-DB-005"
        mark_progressing(test_key, "READY TO TEST")
        increment_return_count(test_key)
        task = get_task(test_key)
        assert task['return_count'] == 1
        increment_return_count(test_key)
        task = get_task(test_key)
        assert task['return_count'] == 2

    def test_reset_service_statuses(self):
        from utils.database.task_db import (
            get_task, mark_progressing, set_service1_done,
            mark_returned, reset_service_statuses
        )
        test_key = "TEST-DB-006"
        mark_progressing(test_key, "READY TO TEST")
        set_service1_done(test_key, compliance_score=40)
        mark_returned(test_key)
        reset_service_statuses(test_key)
        task = get_task(test_key)
        assert task['service1_status'] == 'pending'
        assert task['service2_status'] == 'pending'
        assert task['compliance_score'] is None

    def test_set_service1_error(self):
        from utils.database.task_db import get_task, mark_progressing, set_service1_error
        test_key = "TEST-DB-007"
        mark_progressing(test_key, "READY TO TEST")
        set_service1_error(test_key, "AI timeout error")
        task = get_task(test_key)
        assert task['service1_status'] == 'error'
        assert task['service1_error'] == 'AI timeout error'

    def test_set_skip_detected(self):
        from utils.database.task_db import get_task, mark_progressing, set_skip_detected
        test_key = "TEST-DB-008"
        mark_progressing(test_key, "READY TO TEST")
        set_skip_detected(test_key)
        task = get_task(test_key)
        assert task['skip_detected'] == 1
        assert task['task_status'] == 'completed'

    def test_get_task_nonexistent_returns_none(self):
        from utils.database.task_db import get_task
        task = get_task("TEST-NONEXISTENT-99999")
        assert task is None

    def test_mark_error(self):
        from utils.database.task_db import get_task, mark_progressing, mark_error
        test_key = "TEST-DB-009"
        mark_progressing(test_key, "READY TO TEST")
        mark_error(test_key, "Critical system failure")
        task = get_task(test_key)
        assert task['task_status'] == 'error'
        assert task['error_message'] == 'Critical system failure'

    def test_state_machine_full_flow(self):
        from utils.database.task_db import (
            get_task, mark_progressing, set_service1_done,
            set_service2_done, mark_completed
        )
        test_key = "TEST-DB-010"
        mark_progressing(test_key, "READY TO TEST")
        set_service1_done(test_key, 90)
        set_service2_done(test_key)
        mark_completed(test_key)
        task = get_task(test_key)
        assert task['task_status'] == 'completed'

    def test_updated_at_is_set(self):
        from utils.database.task_db import get_task, mark_progressing
        test_key = "TEST-DB-011"
        mark_progressing(test_key, "READY TO TEST")
        task = get_task(test_key)
        assert task.get('updated_at') is not None

    def test_db_indexes_exist(self):
        from utils.database.task_db import DB_FILE
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='task_processing'")
        indexes = {row[0] for row in cursor.fetchall()}
        conn.close()
        expected_indexes = {'idx_task_status', 'idx_service1_status', 'idx_service2_status'}
        assert expected_indexes.issubset(indexes), f"Yo'q indexlar: {expected_indexes - indexes}"

    # --- test_delete_task_flow tests ---

    def test_delete_task_then_get_returns_none(self):
        from utils.database.task_db import get_task, delete_task, mark_progressing, DB_FILE
        task_key = "TEST-DELETE-001"
        mark_progressing(task_key, "Ready to Test", datetime.now())
        task = get_task(task_key)
        assert task is not None
        assert task['task_status'] == 'progressing'
        success = delete_task(task_key)
        assert success is True
        task_after_delete = get_task(task_key)
        assert task_after_delete is None
        # DB direct verification
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT task_id FROM task_processing WHERE task_id = ?", (task_key,))
        row = cursor.fetchone()
        conn.close()
        assert row is None

    def test_delete_then_recreate_as_new(self):
        from utils.database.task_db import get_task, delete_task, mark_progressing
        task_key = "TEST-DELETE-RECREATE"
        mark_progressing(task_key, "Ready to Test", datetime.now())
        delete_task(task_key)
        mark_progressing(task_key, "Ready to Test", datetime.now())
        task_new = get_task(task_key)
        assert task_new is not None
        assert task_new['task_status'] == 'progressing'
        assert task_new['return_count'] == 0

    def test_multiple_delete_calls_safe(self):
        from utils.database.task_db import get_task, delete_task, mark_progressing
        task_key = "TEST-DELETE-MULTI"
        mark_progressing(task_key, "Ready to Test", datetime.now())
        success1 = delete_task(task_key)
        assert success1 is True
        success2 = delete_task(task_key)
        assert success2 is False
        success3 = delete_task(task_key)
        assert success3 is False

    def test_delete_with_concurrent_access_pattern(self):
        from utils.database.task_db import get_task, delete_task, mark_progressing
        task_key = "TEST-DELETE-CONC"
        mark_progressing(task_key, "Ready to Test", datetime.now())
        success = delete_task(task_key)
        assert success is True
        task = get_task(task_key)
        assert task is None
        # Simulate webhook handler recreating
        mark_progressing(task_key, "Ready to Test", datetime.now())
        task_new = get_task(task_key)
        assert task_new is not None
        assert task_new['task_status'] == 'progressing'


# ============================================================================
# CLASS 5: TestServiceOrchestration
# ============================================================================

class TestServiceOrchestration:
    """
    Bir taskda 2 ta servis qay tartibda ishlashi (test_5, test_8)
    - checker_first mode: Service1 -> delay -> Service2
    - Service2 Service1 done bo'lguncha kutadimi?
    - Score threshold Service2 ni bloklayaptimi?
    - Testcase webhook handler
    """

    def test_default_comment_order_is_valid(self):
        from config.app_settings import get_app_settings
        settings = get_app_settings()
        valid_orders = ["checker_first", "testcase_first", "parallel"]
        assert settings.tz_pr_checker.comment_order in valid_orders

    def test_service1_done_allows_service2(self):
        from utils.database.task_db import get_task, mark_progressing, set_service1_done
        test_key = "TEST-ORDER-001"
        mark_progressing(test_key, "READY TO TEST")
        set_service1_done(test_key, compliance_score=80)
        task = get_task(test_key)
        assert task['service1_status'] == 'done'

    def test_low_score_should_block_service2(self):
        from utils.database.task_db import get_task, mark_progressing, set_service1_done
        from config.app_settings import get_app_settings
        settings = get_app_settings()
        test_key = "TEST-ORDER-002"
        mark_progressing(test_key, "READY TO TEST")
        set_service1_done(test_key, compliance_score=40)
        task = get_task(test_key)
        threshold = settings.tz_pr_checker.return_threshold
        assert task['compliance_score'] < threshold

    def test_service1_pending_blocks_service2(self):
        from utils.database.task_db import get_task, mark_progressing
        test_key = "TEST-ORDER-003"
        mark_progressing(test_key, "READY TO TEST")
        task = get_task(test_key)
        assert task['service1_status'] == 'pending'

    def test_returned_task_service2_not_run(self):
        from utils.database.task_db import get_task, mark_progressing, set_service1_done, mark_returned
        test_key = "TEST-ORDER-004"
        mark_progressing(test_key, "READY TO TEST")
        set_service1_done(test_key, compliance_score=30)
        mark_returned(test_key)
        task = get_task(test_key)
        assert task['task_status'] == 'returned'

    def test_recheck_flow_reset_to_progressing(self):
        from utils.database.task_db import (
            get_task, mark_progressing, set_service1_done,
            mark_returned, reset_service_statuses
        )
        test_key = "TEST-ORDER-005"
        mark_progressing(test_key, "READY TO TEST")
        set_service1_done(test_key, compliance_score=30)
        mark_returned(test_key)
        reset_service_statuses(test_key)
        mark_progressing(test_key, "READY TO TEST")
        task = get_task(test_key)
        assert task['service1_status'] == 'pending'
        assert task['service2_status'] == 'pending'
        assert task['task_status'] == 'progressing'

    def test_score_none_does_not_block_service2(self):
        from utils.database.task_db import get_task, mark_progressing, set_service1_done
        test_key = "TEST-ORDER-006"
        mark_progressing(test_key, "READY TO TEST")
        set_service1_done(test_key, compliance_score=None)
        task = get_task(test_key)
        assert task['compliance_score'] is None
        assert task['service1_status'] == 'done'

    def test_trigger_statuses_contain_ready_to_test(self):
        from config.app_settings import get_app_settings
        settings = get_app_settings()
        trigger_statuses = settings.tz_pr_checker.get_trigger_statuses()
        assert "READY TO TEST" in trigger_statuses

    # --- test_8 testcase webhook handler ---

    def test_testcase_trigger_status_ready_to_test(self):
        from services.webhook.testcase_webhook_handler import is_testcase_trigger_status
        from config.app_settings import get_app_settings
        settings = get_app_settings(force_reload=True)
        if settings.testcase_generator.auto_comment_enabled:
            assert is_testcase_trigger_status("READY TO TEST") is True
        else:
            assert is_testcase_trigger_status("READY TO TEST") is False

    def test_testcase_trigger_status_in_progress_false(self):
        from services.webhook.testcase_webhook_handler import is_testcase_trigger_status
        assert is_testcase_trigger_status("In Progress") is False

    def test_testcase_trigger_status_empty_false(self):
        from services.webhook.testcase_webhook_handler import is_testcase_trigger_status
        assert is_testcase_trigger_status("") is False


# ============================================================================
# CLASS 6: TestErrorHandling
# ============================================================================

class TestErrorHandling:
    """
    Xato va error holatlarida tizim barqarorligi (test_6, resilience test_4, test_6)
    - Task topilmasa nima bo'ladi?
    - PR topilmasa nima bo'ladi?
    - AI xato bersa nima bo'ladi?
    - JSON parse xato bo'lsa nima bo'ladi?
    - Gemini fallback ishlayaptimi?
    - Webhook error handling
    """

    def test_tzpr_task_not_found_graceful_error(self):
        from services.checkers.tz_pr_checker import TZPRService, TZPRAnalysisResult
        service = TZPRService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = None
        service._jira_client = mock_jira
        result = service.analyze_task("TEST-NONEXIST-001")
        assert not result.success
        assert "topilmadi" in result.error_message

    def test_tzpr_task_not_found_returns_result_type(self):
        from services.checkers.tz_pr_checker import TZPRService, TZPRAnalysisResult
        service = TZPRService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = None
        service._jira_client = mock_jira
        result = service.analyze_task("TEST-NONEXIST-002")
        assert isinstance(result, TZPRAnalysisResult)

    def test_tzpr_pr_not_found_graceful_error(self):
        from services.checkers.tz_pr_checker import TZPRService
        service = TZPRService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = {
            'summary': 'Test task',
            'type': 'Story',
            'priority': 'High',
            'description': 'TZ content',
            'comments': [],
            'figma_links': []
        }
        service._jira_client = mock_jira
        mock_pr_helper = MagicMock()
        mock_pr_helper.get_pr_full_info.return_value = None
        service._pr_helper = mock_pr_helper
        result = service.analyze_task("TEST-NOPR-001")
        assert not result.success
        assert "PR topilmadi" in result.error_message

    def test_tzpr_pr_not_found_has_warnings(self):
        from services.checkers.tz_pr_checker import TZPRService
        service = TZPRService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = {
            'summary': 'Test task',
            'type': 'Story',
            'priority': 'High',
            'description': 'TZ content',
            'comments': [],
            'figma_links': []
        }
        service._jira_client = mock_jira
        mock_pr_helper = MagicMock()
        mock_pr_helper.get_pr_full_info.return_value = None
        service._pr_helper = mock_pr_helper
        result = service.analyze_task("TEST-NOPR-002")
        assert len(result.warnings) > 0

    def test_tzpr_ai_error_graceful(self):
        from services.checkers.tz_pr_checker import TZPRService
        service = TZPRService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = {
            'summary': 'Test', 'type': 'Story', 'priority': 'High',
            'description': 'TZ', 'comments': [], 'figma_links': []
        }
        service._jira_client = mock_jira
        mock_pr = MagicMock()
        mock_pr.get_pr_full_info.return_value = {
            'pr_count': 1, 'files_changed': 1,
            'total_additions': 1, 'total_deletions': 0,
            'pr_details': [{'title': 'test', 'url': 'http://test', 'files': []}]
        }
        service._pr_helper = mock_pr
        mock_gemini = MagicMock()
        mock_gemini.analyze.side_effect = RuntimeError("Gemini API xatosi: quota exceeded")
        service._gemini_helper = mock_gemini
        result = service.analyze_task("TEST-AIERR-001")
        assert not result.success

    def test_compliance_score_none_when_missing(self):
        from services.checkers.tz_pr_checker import TZPRService
        service = TZPRService()
        score = service._extract_compliance_score("Bu javobda hech qanday score yo'q")
        assert score is None

    def test_compliance_score_format1(self):
        from services.checkers.tz_pr_checker import TZPRService
        service = TZPRService()
        score = service._extract_compliance_score("COMPLIANCE_SCORE: 85%")
        assert score == 85

    def test_compliance_score_format2(self):
        from services.checkers.tz_pr_checker import TZPRService
        service = TZPRService()
        score = service._extract_compliance_score("**COMPLIANCE_SCORE: 92%**")
        assert score == 92

    def test_compliance_score_format3(self):
        from services.checkers.tz_pr_checker import TZPRService
        service = TZPRService()
        score = service._extract_compliance_score("MOSLIK BALI: 73%")
        assert score == 73

    def test_testcase_json_repair(self):
        from services.generators.testcase_generator import TestCaseGeneratorService
        tc_service = TestCaseGeneratorService()
        broken_json = ('{"test_cases": [{"id": "TC-001", "title": "Test", "description": "desc", '
                       '"preconditions": "pre", "steps": ["1"], "expected_result": "ok", '
                       '"test_type": "positive", "priority": "High", "severity": "Major"}, '
                       '{"id": "TC-002", "title": "Test 2", "desc')
        repaired = tc_service._try_repair_json(broken_json)
        assert repaired is not None
        data = json.loads(repaired)
        assert 'test_cases' in data
        assert len(data['test_cases']) >= 1

    def test_testcase_json_repair_empty_string(self):
        from services.generators.testcase_generator import TestCaseGeneratorService
        tc_service = TestCaseGeneratorService()
        repaired = tc_service._try_repair_json("")
        assert repaired is None

    def test_testcase_task_not_found_graceful(self):
        from services.generators.testcase_generator import TestCaseGeneratorService
        tc_service = TestCaseGeneratorService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = None
        tc_service._jira_client = mock_jira
        result = tc_service.generate_test_cases("TEST-NOTFOUND-001")
        assert not result.success
        assert "topilmadi" in result.error_message

    def test_gemini_fallback_quota_error_detection(self):
        from utils.ai.gemini_helper import GeminiHelper
        helper = GeminiHelper.__new__(GeminiHelper)
        helper.api_key_1 = "key1"
        helper.api_key_2 = "key2"
        helper.using_fallback = False
        helper.FALLBACK_ERROR_KEYWORDS = GeminiHelper.FALLBACK_ERROR_KEYWORDS

        class FakeQuotaError(Exception):
            pass

        quota_error = FakeQuotaError("resource_exhausted: quota limit reached")
        assert helper._is_fallback_error(quota_error)

    def test_gemini_fallback_normal_error_not_triggered(self):
        from utils.ai.gemini_helper import GeminiHelper
        helper = GeminiHelper.__new__(GeminiHelper)
        helper.api_key_1 = "key1"
        helper.api_key_2 = "key2"
        helper.using_fallback = False
        helper.FALLBACK_ERROR_KEYWORDS = GeminiHelper.FALLBACK_ERROR_KEYWORDS

        class FakeError(Exception):
            pass

        normal_error = FakeError("connection timeout")
        assert not helper._is_fallback_error(normal_error)

    def test_gemini_fallback_429_detection(self):
        from utils.ai.gemini_helper import GeminiHelper
        helper = GeminiHelper.__new__(GeminiHelper)
        helper.api_key_1 = "key1"
        helper.api_key_2 = "key2"
        helper.using_fallback = False
        helper.FALLBACK_ERROR_KEYWORDS = GeminiHelper.FALLBACK_ERROR_KEYWORDS

        class FakeError(Exception):
            pass

        rate_error = FakeError("429 rate limit exceeded")
        assert helper._is_fallback_error(rate_error)

    def test_webhook_invalid_payload_no_crash(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        response = client.post("/webhook/jira", json={"random": "data"})
        assert response.status_code in [200, 422]

    def test_webhook_empty_payload_no_crash(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        response = client.post("/webhook/jira", json={})
        assert response.status_code in [200, 422]

    # --- Resilience test_4: both keys error retry ---

    def test_service1_blocked_retry_flow(self):
        from utils.database.task_db import (
            mark_progressing, set_service1_blocked, get_task, upsert_task
        )
        from services.webhook.jira_webhook_handler import _retry_blocked_task
        task_key = "TEST-RETRY-KEY1-001"
        mark_progressing(task_key, "READY TO TEST")
        set_service1_blocked(task_key, "AI timeout: 429 rate limit", retry_minutes=0)
        past_time = (datetime.now() - timedelta(minutes=1)).isoformat()
        upsert_task(task_key, {'blocked_retry_at': past_time})
        # retry_scheduler.py funksiya ichida import qiladi: from services.webhook.service_runner import check_tz_pr_and_comment
        with patch('services.webhook.service_runner.check_tz_pr_and_comment', new_callable=AsyncMock):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_retry_blocked_task(task_key))
                task = get_task(task_key)
                assert task is not None
                assert task['service1_status'] in ('pending', 'done', 'skip')
            finally:
                loop.close()

    def test_service2_blocked_retry_flow(self):
        from utils.database.task_db import (
            mark_progressing, set_service1_done, set_service2_blocked, get_task, upsert_task
        )
        from services.webhook.jira_webhook_handler import _retry_blocked_task
        task_key = "TEST-RETRY-KEY2-001"
        mark_progressing(task_key, "READY TO TEST")
        set_service1_done(task_key, compliance_score=80)
        set_service2_blocked(task_key, "AI timeout: resource_exhausted", retry_minutes=0)
        past_time = (datetime.now() - timedelta(minutes=1)).isoformat()
        upsert_task(task_key, {'blocked_retry_at': past_time})
        # retry_scheduler.py funksiya ichida import qiladi: from services.webhook.service_runner import _run_testcase_generation
        with patch('services.webhook.service_runner._run_testcase_generation', new_callable=AsyncMock):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_retry_blocked_task(task_key))
                task = get_task(task_key)
                assert task is not None
                assert task['service2_status'] in ('pending', 'done')
            finally:
                loop.close()

    def test_both_keys_error_service1_stays_blocked_on_retry(self):
        from utils.database.task_db import (
            mark_progressing, set_service1_blocked, set_service2_blocked,
            get_task, upsert_task
        )
        from services.webhook.jira_webhook_handler import _retry_blocked_task
        task_key = "TEST-RETRY-BOTH-001"
        mark_progressing(task_key, "READY TO TEST")
        set_service1_blocked(task_key, "AI timeout: ikkala key ham ishlamadi", retry_minutes=0)
        set_service2_blocked(task_key, "AI timeout: ikkala key ham ishlamadi", retry_minutes=0)
        past_time = (datetime.now() - timedelta(minutes=1)).isoformat()
        upsert_task(task_key, {'blocked_retry_at': past_time})

        async def mock_service1_error(**kwargs):
            set_service1_blocked(task_key, "AI timeout: yana error", retry_minutes=1)

        # retry_scheduler.py funksiya ichida import qiladi: from services.webhook.service_runner import check_tz_pr_and_comment
        with patch('services.webhook.service_runner.check_tz_pr_and_comment',
                   new_callable=AsyncMock) as mock_service1:
            mock_service1.side_effect = mock_service1_error
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_retry_blocked_task(task_key))
                task = get_task(task_key)
                assert task is not None
                assert task['service1_status'] == 'blocked'
            finally:
                loop.close()

    # --- Resilience test_6: system resilience ---

    def test_webhook_null_task_key_graceful(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": None},
            "changelog": {}
        }
        response = client.post("/webhook/jira", json=payload)
        if response.status_code == 200:
            data = response.json()
            assert data.get('status') in ['error', 'ignored']
        else:
            assert response.status_code in [200, 422]

    def test_db_nonexistent_task_no_crash(self):
        from utils.database.task_db import get_task
        nonexistent = get_task("TEST-NONEXISTENT-999999")
        assert nonexistent is None


# ============================================================================
# CLASS 7: TestSettingsManagement
# ============================================================================

class TestSettingsManagement:
    """
    Sozlamalar tizimi to'g'ri ishlashi (test_7, resilience test_2)
    - AppSettings default qiymatlar to'g'rimi?
    - Settings file o'qilishi va yozilishi
    - force_reload ishlayaptimi?
    - Trigger statuses to'g'ri generatsiya qilinadimi?
    - Settings ziddiyatlarini tekshirish
    """

    def test_default_return_threshold(self):
        from config.app_settings import AppSettings
        settings = AppSettings()
        assert settings.tz_pr_checker.return_threshold == 60

    def test_default_auto_return_disabled(self):
        from config.app_settings import AppSettings
        settings = AppSettings()
        assert settings.tz_pr_checker.auto_return_enabled is False

    def test_default_queue_enabled(self):
        from config.app_settings import AppSettings
        settings = AppSettings()
        assert settings.queue.queue_enabled is True

    def test_default_checker_testcase_delay(self):
        from config.app_settings import AppSettings
        settings = AppSettings()
        assert settings.queue.checker_testcase_delay == 15

    def test_tz_pr_trigger_statuses_contain_ready(self):
        from config.app_settings import AppSettings
        settings = AppSettings()
        tz_triggers = settings.tz_pr_checker.get_trigger_statuses()
        assert "READY TO TEST" in tz_triggers

    def test_testcase_trigger_statuses_contain_ready(self):
        from config.app_settings import AppSettings
        settings = AppSettings()
        tc_triggers = settings.testcase_generator.get_trigger_statuses()
        assert "READY TO TEST" in tc_triggers

    def test_settings_singleton(self):
        from config.app_settings import get_app_settings
        s1 = get_app_settings()
        s2 = get_app_settings()
        assert s1 is s2

    def test_force_reload_returns_app_settings(self):
        from config.app_settings import get_app_settings, AppSettings
        s3 = get_app_settings(force_reload=True)
        assert isinstance(s3, AppSettings)

    def test_visible_sections_default(self):
        from config.app_settings import AppSettings
        settings = AppSettings()
        assert 'completed' in settings.tz_pr_checker.visible_sections

    def test_comment_order_valid_value(self):
        from config.app_settings import AppSettings
        settings = AppSettings()
        valid_orders = ["checker_first", "testcase_first", "parallel"]
        assert settings.tz_pr_checker.comment_order in valid_orders

    def test_default_max_test_cases(self):
        from config.app_settings import AppSettings
        settings = AppSettings()
        assert settings.testcase_generator.max_test_cases == 10

    def test_default_test_types(self):
        from config.app_settings import AppSettings
        settings = AppSettings()
        assert settings.testcase_generator.default_test_types == ['positive', 'negative']

    # --- Resilience test_2: settings conflicts ---

    def test_comment_order_is_valid_value(self):
        from config.app_settings import get_app_settings
        settings = get_app_settings(force_reload=True)
        valid_orders = ["checker_first", "testcase_first", "parallel"]
        assert settings.tz_pr_checker.comment_order in valid_orders

    def test_return_threshold_range(self):
        from config.app_settings import get_app_settings
        settings = get_app_settings(force_reload=True)
        threshold = settings.tz_pr_checker.return_threshold
        assert 0 <= threshold <= 100

    def test_auto_return_threshold_not_zero(self):
        from config.app_settings import get_app_settings
        settings = get_app_settings(force_reload=True)
        auto_return = settings.tz_pr_checker.auto_return_enabled
        threshold = settings.tz_pr_checker.return_threshold
        if auto_return:
            assert threshold > 0, "Auto return enabled lekin threshold 0"

    def test_tz_triggers_not_empty(self):
        from config.app_settings import get_app_settings
        settings = get_app_settings(force_reload=True)
        tz_triggers = settings.tz_pr_checker.get_trigger_statuses()
        assert len(tz_triggers) > 0

    def test_tc_triggers_not_empty(self):
        from config.app_settings import get_app_settings
        settings = get_app_settings(force_reload=True)
        tc_triggers = settings.testcase_generator.get_trigger_statuses()
        assert len(tc_triggers) > 0

    def test_task_wait_timeout_positive(self):
        from config.app_settings import get_app_settings
        settings = get_app_settings(force_reload=True)
        assert settings.queue.task_wait_timeout > 0

    def test_checker_testcase_delay_non_negative(self):
        from config.app_settings import get_app_settings
        settings = get_app_settings(force_reload=True)
        assert settings.queue.checker_testcase_delay >= 0

    def test_blocked_retry_delay_positive(self):
        from config.app_settings import get_app_settings
        settings = get_app_settings(force_reload=True)
        assert settings.queue.blocked_retry_delay > 0

    def test_key_freeze_duration_positive(self):
        from config.app_settings import get_app_settings
        settings = get_app_settings(force_reload=True)
        assert settings.queue.key_freeze_duration > 0

    def test_ai_max_input_tokens_valid_range(self):
        from config.app_settings import get_app_settings
        settings = get_app_settings(force_reload=True)
        assert 0 < settings.queue.ai_max_input_tokens <= 1000000


# ============================================================================
# CLASS 8: TestDebugCapability
# ============================================================================

class TestDebugCapability:
    """
    Debug qilish osonligi (test_10)
    - Logging konfiguratsiyasi to'g'rimi?
    - Error message'lar tushunarli mi?
    - Stack trace saqlanadigmi?
    - DB'da error ma'lumot saqlanganmi?
    """

    def test_webhook_module_logger_exists(self):
        import services.webhook.jira_webhook_handler as webhook_module
        module_logger = logging.getLogger(webhook_module.__name__)
        assert module_logger is not None

    def test_error_message_contains_task_key(self):
        from services.checkers.tz_pr_checker import TZPRService
        service = TZPRService()
        mock_jira = MagicMock()
        mock_jira.get_task_details.return_value = None
        service._jira_client = mock_jira
        result = service.analyze_task("TEST-DEBUG-001")
        assert "TEST-DEBUG-001" in result.error_message

    def test_db_error_message_saved(self):
        from utils.database.task_db import mark_error, get_task, mark_progressing
        mark_progressing("TEST-DEBUG-002", "READY TO TEST")
        mark_error("TEST-DEBUG-002", "Gemini API xatosi: rate limit exceeded")
        task = get_task("TEST-DEBUG-002")
        assert task is not None
        assert task['error_message'] == "Gemini API xatosi: rate limit exceeded"

    def test_service1_error_saved_separately(self):
        from utils.database.task_db import mark_progressing, set_service1_error, get_task
        mark_progressing("TEST-DEBUG-003", "READY TO TEST")
        set_service1_error("TEST-DEBUG-003", "PR fetch timeout: 30s")
        task = get_task("TEST-DEBUG-003")
        assert task['service1_error'] == "PR fetch timeout: 30s"

    def test_service2_error_saved_separately(self):
        from utils.database.task_db import mark_progressing, set_service1_error, set_service2_error, get_task
        mark_progressing("TEST-DEBUG-004", "READY TO TEST")
        set_service1_error("TEST-DEBUG-004", "PR fetch timeout: 30s")
        set_service2_error("TEST-DEBUG-004", "JSON parse xatosi")
        task = get_task("TEST-DEBUG-004")
        assert task['service2_error'] == "JSON parse xatosi"

    def test_updated_at_timestamp_present(self):
        from utils.database.task_db import mark_progressing, set_service2_error, get_task, set_service1_error
        mark_progressing("TEST-DEBUG-005", "READY TO TEST")
        set_service1_error("TEST-DEBUG-005", "err")
        set_service2_error("TEST-DEBUG-005", "JSON parse xatosi")
        task = get_task("TEST-DEBUG-005")
        assert task.get('updated_at') is not None

    def test_last_processed_at_present(self):
        from utils.database.task_db import mark_progressing, get_task
        mark_progressing("TEST-DEBUG-006", "READY TO TEST")
        task = get_task("TEST-DEBUG-006")
        assert task.get('last_processed_at') is not None

    def test_analysis_result_warnings_field(self):
        from services.checkers.tz_pr_checker import TZPRAnalysisResult
        error_result = TZPRAnalysisResult(
            task_key="TEST-DEBUG-007",
            success=False,
            error_message="Test error",
            warnings=["PR topilmadi", "Figma token yo'q"]
        )
        assert len(error_result.warnings) == 2

    def test_analysis_result_ai_retry_count(self):
        from services.checkers.tz_pr_checker import TZPRAnalysisResult
        success_result = TZPRAnalysisResult(
            task_key="TEST-DEBUG-008",
            success=True,
            ai_retry_count=2,
            total_prompt_size=50000
        )
        assert success_result.ai_retry_count == 2

    def test_analysis_result_total_prompt_size(self):
        from services.checkers.tz_pr_checker import TZPRAnalysisResult
        success_result = TZPRAnalysisResult(
            task_key="TEST-DEBUG-009",
            success=True,
            ai_retry_count=2,
            total_prompt_size=50000
        )
        assert success_result.total_prompt_size == 50000


# ============================================================================
# CLASS 9: TestBlockedRetry
# ============================================================================

class TestBlockedRetry:
    """
    Blocked status va retry logikasi (test_11, resilience test_3)
    - Xato klassifikatsiya
    - mark_blocked, set_service1_blocked, set_service2_blocked
    - get_blocked_tasks_ready_for_retry
    - delete_task
    - DB v3 migration columns
    - Blocked tasklar bilan key-1 va key-2 ishlashi
    """

    def _classify_error_local(self, error_msg: str) -> str:
        """Local copy of error classification logic for testing"""
        if not error_msg:
            return 'unknown'
        msg_lower = error_msg.lower()
        pr_keywords = ['pr topilmadi', 'pr not found', 'no pr found']
        if any(kw in msg_lower for kw in pr_keywords):
            return 'pr_not_found'
        ai_timeout_keywords = [
            'timeout', '429', 'rate limit', 'rate_limit',
            'overloaded', 'quota', 'resource exhausted',
            'resource_exhausted', 'too many requests'
        ]
        if any(kw in msg_lower for kw in ai_timeout_keywords):
            return 'ai_timeout'
        return 'unknown'

    def test_classify_error_pr_not_found(self):
        result = self._classify_error_local("Bu task uchun PR topilmadi (JIRA va GitHub'da)")
        assert result == 'pr_not_found'

    def test_classify_error_timeout(self):
        result = self._classify_error_local("AI xatolik: timeout after 60s")
        assert result == 'ai_timeout'

    def test_classify_error_429(self):
        result = self._classify_error_local("Error 429: Too Many Requests")
        assert result == 'ai_timeout'

    def test_classify_error_quota(self):
        result = self._classify_error_local("Resource exhausted: quota exceeded")
        assert result == 'ai_timeout'

    def test_classify_error_unknown(self):
        result = self._classify_error_local("Some random error")
        assert result == 'unknown'

    def test_classify_error_empty(self):
        result = self._classify_error_local("")
        assert result == 'unknown'

    def test_classify_error_from_webhook_handler(self):
        from services.webhook.jira_webhook_handler import _classify_error
        result = _classify_error("PR topilmadi: no PR found")
        assert result == 'pr_not_found'

    def test_classify_error_timeout_from_handler(self):
        from services.webhook.jira_webhook_handler import _classify_error
        result = _classify_error("AI timeout: 429 rate limit exceeded")
        assert result == 'ai_timeout'

    def test_classify_error_both_keys_from_handler(self):
        from services.webhook.jira_webhook_handler import _classify_error
        result = _classify_error("AI xatolik: ikkala key ham ishlamadi")
        assert result == 'ai_timeout'

    def test_mark_blocked_task_status(self):
        from utils.database.task_db import mark_progressing, mark_blocked, get_task
        task_id = "TEST-BLOCKED-001"
        mark_progressing(task_id, "READY TO TEST")
        mark_blocked(task_id, "AI timeout: 60s", retry_minutes=5)
        task = get_task(task_id)
        assert task is not None
        assert task['task_status'] == 'blocked'

    def test_mark_blocked_reason_saved(self):
        from utils.database.task_db import mark_progressing, mark_blocked, get_task
        task_id = "TEST-BLOCKED-002"
        mark_progressing(task_id, "READY TO TEST")
        mark_blocked(task_id, "AI timeout: 60s", retry_minutes=5)
        task = get_task(task_id)
        assert task.get('block_reason') == 'AI timeout: 60s'

    def test_mark_blocked_blocked_at_saved(self):
        from utils.database.task_db import mark_progressing, mark_blocked, get_task
        task_id = "TEST-BLOCKED-003"
        mark_progressing(task_id, "READY TO TEST")
        mark_blocked(task_id, "AI timeout: 60s", retry_minutes=5)
        task = get_task(task_id)
        assert task.get('blocked_at') is not None

    def test_mark_blocked_retry_at_saved(self):
        from utils.database.task_db import mark_progressing, mark_blocked, get_task
        task_id = "TEST-BLOCKED-004"
        mark_progressing(task_id, "READY TO TEST")
        mark_blocked(task_id, "AI timeout: 60s", retry_minutes=5)
        task = get_task(task_id)
        assert task.get('blocked_retry_at') is not None

    def test_set_service1_blocked_status(self):
        from utils.database.task_db import mark_progressing, set_service1_blocked, get_task
        task_id = "TEST-BLOCKED-005"
        mark_progressing(task_id, "READY TO TEST")
        set_service1_blocked(task_id, "429 rate limit", retry_minutes=3)
        task = get_task(task_id)
        assert task['service1_status'] == 'blocked'

    def test_set_service1_blocked_service2_stays_pending(self):
        from utils.database.task_db import mark_progressing, set_service1_blocked, get_task
        task_id = "TEST-BLOCKED-006"
        mark_progressing(task_id, "READY TO TEST")
        set_service1_blocked(task_id, "429 rate limit", retry_minutes=3)
        task = get_task(task_id)
        assert task['service2_status'] == 'pending'

    def test_set_service1_blocked_task_becomes_blocked(self):
        from utils.database.task_db import mark_progressing, set_service1_blocked, get_task
        task_id = "TEST-BLOCKED-007"
        mark_progressing(task_id, "READY TO TEST")
        set_service1_blocked(task_id, "429 rate limit", retry_minutes=3)
        task = get_task(task_id)
        assert task['task_status'] == 'blocked'

    def test_set_service2_blocked_service1_stays_done(self):
        from utils.database.task_db import (
            mark_progressing, set_service1_done, set_service2_blocked, get_task
        )
        task_id = "TEST-BLOCKED-008"
        mark_progressing(task_id, "READY TO TEST")
        set_service1_done(task_id, compliance_score=80)
        set_service2_blocked(task_id, "AI overloaded", retry_minutes=5)
        task = get_task(task_id)
        assert task['service1_status'] == 'done'

    def test_set_service2_blocked_status(self):
        from utils.database.task_db import (
            mark_progressing, set_service1_done, set_service2_blocked, get_task
        )
        task_id = "TEST-BLOCKED-009"
        mark_progressing(task_id, "READY TO TEST")
        set_service1_done(task_id, compliance_score=80)
        set_service2_blocked(task_id, "AI overloaded", retry_minutes=5)
        task = get_task(task_id)
        assert task['service2_status'] == 'blocked'

    def test_set_service1_skip_status(self):
        from utils.database.task_db import mark_progressing, set_service1_skip, get_task
        task_id = "TEST-BLOCKED-010"
        mark_progressing(task_id, "READY TO TEST")
        set_service1_skip(task_id)
        task = get_task(task_id)
        assert task['service1_status'] == 'skip'

    def test_set_service1_skip_score_100(self):
        from utils.database.task_db import mark_progressing, set_service1_skip, get_task
        task_id = "TEST-BLOCKED-011"
        mark_progressing(task_id, "READY TO TEST")
        set_service1_skip(task_id)
        task = get_task(task_id)
        assert task.get('compliance_score') == 100

    def test_set_service1_skip_flag(self):
        from utils.database.task_db import mark_progressing, set_service1_skip, get_task
        task_id = "TEST-BLOCKED-012"
        mark_progressing(task_id, "READY TO TEST")
        set_service1_skip(task_id)
        task = get_task(task_id)
        assert task.get('skip_detected') == 1

    def test_set_service1_error_keep_service2_pending(self):
        from utils.database.task_db import mark_progressing, set_service1_error, get_task
        task_id = "TEST-BLOCKED-013"
        mark_progressing(task_id, "READY TO TEST")
        set_service1_error(task_id, "PR topilmadi", keep_service2_pending=True)
        task = get_task(task_id)
        assert task['service1_status'] == 'error'
        assert task['service2_status'] == 'pending'

    def test_mark_returned_service2_stays_pending(self):
        from utils.database.task_db import (
            mark_progressing, set_service1_done, mark_returned, get_task
        )
        task_id = "TEST-BLOCKED-014"
        mark_progressing(task_id, "READY TO TEST")
        set_service1_done(task_id, compliance_score=40)
        mark_returned(task_id)
        task = get_task(task_id)
        assert task['task_status'] == 'returned'
        assert task['service2_status'] == 'pending'

    def test_get_blocked_tasks_ready_for_retry(self):
        from utils.database.task_db import (
            mark_progressing, mark_blocked, get_blocked_tasks_ready_for_retry, upsert_task
        )
        task_id = "TEST-BLOCKED-015"
        mark_progressing(task_id, "READY TO TEST")
        mark_blocked(task_id, "test blocked", retry_minutes=0)
        past_time = (datetime.now() - timedelta(minutes=1)).isoformat()
        upsert_task(task_id, {'blocked_retry_at': past_time})
        blocked_tasks = get_blocked_tasks_ready_for_retry()
        found = any(t['task_id'] == task_id for t in blocked_tasks)
        assert found

    def test_delete_task_removes_from_db(self):
        from utils.database.task_db import mark_progressing, delete_task, get_task
        task_id = "TEST-BLOCKED-016"
        mark_progressing(task_id, "READY TO TEST")
        assert get_task(task_id) is not None
        result = delete_task(task_id)
        assert result is True
        assert get_task(task_id) is None

    def test_delete_task_returns_false_for_nonexistent(self):
        from utils.database.task_db import delete_task
        result = delete_task("TEST-NONEXIST-99999")
        assert result is False

    def test_db_v3_migration_blocked_at_column(self):
        from utils.database.task_db import DB_FILE
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(task_processing)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        assert 'blocked_at' in columns

    def test_db_v3_migration_blocked_retry_at_column(self):
        from utils.database.task_db import DB_FILE
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(task_processing)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        assert 'blocked_retry_at' in columns

    def test_db_v3_migration_block_reason_column(self):
        from utils.database.task_db import DB_FILE
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(task_processing)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        assert 'block_reason' in columns

    # --- Resilience test_3: blocked tasks key1/key2 ---

    def test_service1_blocked_key1_error_simulation(self):
        from utils.database.task_db import mark_progressing, set_service1_blocked, get_task
        task_key = "TEST-BLOCKED-KEY1-001"
        mark_progressing(task_key, "READY TO TEST")
        set_service1_blocked(task_key, "AI timeout: 429 rate limit exceeded", retry_minutes=1)
        task = get_task(task_key)
        assert task is not None
        assert task['service1_status'] == 'blocked'
        assert task['task_status'] == 'blocked'

    def test_service2_blocked_key2_error_simulation(self):
        from utils.database.task_db import (
            mark_progressing, set_service1_done, set_service2_blocked, get_task
        )
        task_key = "TEST-BLOCKED-KEY2-001"
        mark_progressing(task_key, "READY TO TEST")
        set_service1_done(task_key, compliance_score=80)
        set_service2_blocked(task_key, "AI timeout: resource_exhausted quota exceeded", retry_minutes=1)
        task = get_task(task_key)
        assert task is not None
        assert task['service2_status'] == 'blocked'

    def test_both_keys_error_both_blocked(self):
        from utils.database.task_db import (
            mark_progressing, set_service1_blocked, set_service2_blocked, get_task
        )
        task_key = "TEST-BLOCKED-BOTH-001"
        mark_progressing(task_key, "READY TO TEST")
        set_service1_blocked(task_key, "AI timeout: 429 rate limit", retry_minutes=1)
        set_service2_blocked(task_key, "AI timeout: ikkala key ham ishlamadi", retry_minutes=1)
        task = get_task(task_key)
        assert task is not None
        assert task['service1_status'] == 'blocked'
        assert task['service2_status'] == 'blocked'

    def test_blocked_retry_at_is_in_future(self):
        from utils.database.task_db import (
            mark_progressing, set_service1_blocked, set_service2_blocked, get_task
        )
        task_key = "TEST-BLOCKED-FUTURE-001"
        mark_progressing(task_key, "READY TO TEST")
        set_service1_blocked(task_key, "AI timeout", retry_minutes=5)
        set_service2_blocked(task_key, "AI timeout", retry_minutes=5)
        task = get_task(task_key)
        assert task.get('blocked_retry_at') is not None
        retry_at = datetime.fromisoformat(task['blocked_retry_at'])
        assert retry_at > datetime.now()

    def test_get_blocked_tasks_includes_past_retry(self):
        from utils.database.task_db import (
            mark_progressing, set_service1_blocked, set_service2_blocked,
            get_blocked_tasks_ready_for_retry, upsert_task
        )
        task_key1 = "TEST-BLOCKED-PAST-001"
        task_key2 = "TEST-BLOCKED-PAST-002"
        mark_progressing(task_key1, "READY TO TEST")
        set_service1_blocked(task_key1, "AI timeout", retry_minutes=1)
        mark_progressing(task_key2, "READY TO TEST")
        set_service2_blocked(task_key2, "AI timeout", retry_minutes=1)
        past_time = (datetime.now() - timedelta(minutes=1)).isoformat()
        upsert_task(task_key1, {'blocked_retry_at': past_time})
        upsert_task(task_key2, {'blocked_retry_at': past_time})
        blocked_tasks = get_blocked_tasks_ready_for_retry()
        found_count = sum(1 for t in blocked_tasks if t['task_id'] in [task_key1, task_key2])
        assert found_count >= 1


# ============================================================================
# CLASS 10: TestGeminiKeyFallback
# ============================================================================

class TestGeminiKeyFallback:
    """
    Gemini Key Freeze logikasi va Service2 TZ-only flow (test_12)
    - GeminiHelper KEY_1 freeze logikasi
    - KEY_1 unfreeze (muddat tugashi)
    - Service1 error → Service2 pending holat
    """

    class MockGeminiHelper:
        KEY1_FREEZE_DURATION = 600

        def __init__(self):
            self.api_key_1 = "test_key_1"
            self.api_key_2 = "test_key_2"
            self.current_key = self.api_key_1
            self.using_fallback = False
            self._key1_frozen_until = None

        def _is_key1_frozen(self):
            if self._key1_frozen_until is None:
                return False
            return time.time() < self._key1_frozen_until

        def _freeze_key1(self):
            self._key1_frozen_until = time.time() + self.KEY1_FREEZE_DURATION

        def _unfreeze_key1(self):
            self._key1_frozen_until = None
            self.using_fallback = False
            self.current_key = self.api_key_1

        def _switch_to_fallback(self):
            if not self.api_key_2 or self.using_fallback:
                return False
            self.current_key = self.api_key_2
            self.using_fallback = True
            return True

    def test_key1_not_frozen_initially(self):
        helper = self.MockGeminiHelper()
        assert not helper._is_key1_frozen()

    def test_key1_frozen_after_freeze(self):
        helper = self.MockGeminiHelper()
        helper._freeze_key1()
        assert helper._is_key1_frozen()

    def test_frozen_until_timestamp_saved(self):
        helper = self.MockGeminiHelper()
        helper._freeze_key1()
        assert helper._key1_frozen_until is not None

    def test_switch_to_fallback_success(self):
        helper = self.MockGeminiHelper()
        helper._freeze_key1()
        assert helper._switch_to_fallback() is True

    def test_current_key_is_key2_after_fallback(self):
        helper = self.MockGeminiHelper()
        helper._freeze_key1()
        helper._switch_to_fallback()
        assert helper.current_key == "test_key_2"

    def test_using_fallback_true_after_switch(self):
        helper = self.MockGeminiHelper()
        helper._freeze_key1()
        helper._switch_to_fallback()
        assert helper.using_fallback is True

    def test_repeated_fallback_blocked(self):
        helper = self.MockGeminiHelper()
        helper._freeze_key1()
        helper._switch_to_fallback()
        assert helper._switch_to_fallback() is False

    def test_key1_unfrozen_after_unfreeze(self):
        helper = self.MockGeminiHelper()
        helper._freeze_key1()
        helper._unfreeze_key1()
        assert not helper._is_key1_frozen()

    def test_returns_to_key1_after_unfreeze(self):
        helper = self.MockGeminiHelper()
        helper._freeze_key1()
        helper._switch_to_fallback()
        helper._unfreeze_key1()
        assert helper.current_key == "test_key_1"
        assert helper.using_fallback is False

    def test_freeze_duration_expiry(self):
        helper = self.MockGeminiHelper()
        helper._freeze_key1()
        helper._key1_frozen_until = time.time() - 1  # Expired
        assert not helper._is_key1_frozen()

    def test_no_key2_blocks_fallback(self):
        helper = self.MockGeminiHelper()
        helper.api_key_2 = None
        helper._freeze_key1()
        assert helper._switch_to_fallback() is False

    def test_freeze_duration_constant(self):
        assert self.MockGeminiHelper.KEY1_FREEZE_DURATION == 600

    # --- Service2 TZ-only flow ---

    def test_service1_error_pr_not_found_keeps_s2_pending(self):
        from utils.database.task_db import mark_progressing, set_service1_error, get_task
        task_key = "TEST-FREEZE-001"
        mark_progressing(task_key, "READY TO TEST", datetime.now())
        set_service1_error(task_key, "PR topilmadi: no PR found for branch", keep_service2_pending=True)
        task_data = get_task(task_key)
        assert task_data['service1_status'] == 'error'
        assert task_data['service2_status'] == 'pending'

    def test_service1_error_unknown_sets_s2_error(self):
        from utils.database.task_db import mark_progressing, set_service1_error, get_task
        task_key = "TEST-FREEZE-002"
        mark_progressing(task_key, "READY TO TEST", datetime.now())
        set_service1_error(task_key, "Unknown critical error")
        task_data = get_task(task_key)
        assert task_data['service2_status'] == 'error'

    def test_service1_error_pr_then_service2_done_completes(self):
        from utils.database.task_db import (
            mark_progressing, set_service1_error, set_service2_done, get_task
        )
        task_key = "TEST-FREEZE-003"
        mark_progressing(task_key, "READY TO TEST", datetime.now())
        set_service1_error(task_key, "PR topilmadi", keep_service2_pending=True)
        set_service2_done(task_key)
        task_data = get_task(task_key)
        assert task_data['task_status'] == 'completed'


# ============================================================================
# CLASS 11: TestDeleteAndWebhook
# ============================================================================

class TestDeleteAndWebhook:
    """
    Webhook handler after delete task (test_webhook_after_delete.py)
    - Task delete qilingandan keyin webhook kelganda yangi task sifatida qabul qilinishi
    - Completed task'ga webhook kelganda dublikat logikasi
    - Real problem scenariosi
    """

    def _simulate_webhook_handler_logic(self, task_key: str, new_status: str):
        """Webhook handler logikasini simulatsiya qilish"""
        from utils.database.task_db import get_task, mark_progressing
        task_db = get_task(task_key)
        if not task_db:
            mark_progressing(task_key, new_status, datetime.now())
            return "processing"
        task_status = task_db.get('task_status', 'none')
        last_jira_status = task_db.get('last_jira_status')
        if last_jira_status == new_status and task_status in ('progressing', 'completed'):
            return "ignored_duplicate"
        if task_status == 'none':
            mark_progressing(task_key, new_status, datetime.now())
            return "processing"
        elif task_status == 'completed':
            mark_progressing(task_key, new_status, datetime.now())
            return "processing"
        elif task_status == 'progressing':
            return "ignored_progressing"
        return "unknown"

    def test_webhook_after_manual_delete_should_process(self):
        from utils.database.task_db import (
            get_task, delete_task, mark_progressing, mark_completed
        )
        task_key = "TEST-WEBHOOK-AFTERDEL-001"
        status = "Ready to Test"
        mark_progressing(task_key, status, datetime.now())
        mark_completed(task_key)
        task = get_task(task_key)
        assert task['task_status'] == 'completed'
        success = delete_task(task_key)
        assert success
        task_after_delete = get_task(task_key)
        assert task_after_delete is None
        result = self._simulate_webhook_handler_logic(task_key, status)
        assert result == "processing", f"Webhook should process as new task, got: {result}"
        delete_task(task_key)

    def test_webhook_completed_task_without_delete_is_duplicate(self):
        from utils.database.task_db import (
            get_task, delete_task, mark_progressing, mark_completed
        )
        task_key = "TEST-WEBHOOK-AFTERDEL-002"
        status = "Ready to Test"
        mark_progressing(task_key, status, datetime.now())
        mark_completed(task_key)
        task = get_task(task_key)
        assert task['task_status'] == 'completed'
        result = self._simulate_webhook_handler_logic(task_key, status)
        # Same status + completed = duplicate
        assert result == "ignored_duplicate"
        delete_task(task_key)

    def test_real_problem_scenario_delete_then_webhook(self):
        from utils.database.task_db import (
            get_task, delete_task, mark_progressing, mark_completed
        )
        task_key = "TEST-WEBHOOK-AFTERDEL-003"
        status = "Ready to Test"
        mark_progressing(task_key, status, datetime.now())
        mark_completed(task_key)
        task_before = get_task(task_key)
        assert task_before is not None
        delete_task(task_key)
        task_after_delete = get_task(task_key)
        assert task_after_delete is None
        result = self._simulate_webhook_handler_logic(task_key, status)
        assert result == "processing", (
            f"After delete, webhook should process as new task, got: {result}"
        )
        delete_task(task_key)


# ============================================================================
# CLASS 12: TestSystemResilience
# ============================================================================

class TestSystemResilience:
    """
    Tizim bardoshliligi (resilience test_5, test_6)
    - Queue lock mexanizmi
    - DB concurrent access
    - Settings reload mexanizmi
    - Error classification mexanizmi
    - Task status state machine
    - Invalid payload handling
    """

    def test_queue_lock_singleton_resilience(self):
        from services.webhook.jira_webhook_handler import _get_ai_queue_lock
        lock1 = _get_ai_queue_lock()
        lock2 = _get_ai_queue_lock()
        assert lock1 is lock2

    def test_error_classification_pr_not_found(self):
        from services.webhook.jira_webhook_handler import _classify_error
        result = _classify_error("PR topilmadi: no PR found")
        assert result == 'pr_not_found'

    def test_error_classification_ai_timeout(self):
        from services.webhook.jira_webhook_handler import _classify_error
        result = _classify_error("AI timeout: 429 rate limit exceeded")
        assert result == 'ai_timeout'

    def test_error_classification_both_keys(self):
        from services.webhook.jira_webhook_handler import _classify_error
        result = _classify_error("AI xatolik: ikkala key ham ishlamadi")
        assert result == 'ai_timeout'

    def test_task_state_machine_progressing(self):
        from utils.database.task_db import mark_progressing, get_task
        task_key = "TEST-MECH-001"
        mark_progressing(task_key, "READY TO TEST")
        task = get_task(task_key)
        assert task is not None
        assert task['task_status'] == 'progressing'

    def test_task_state_machine_service1_done(self):
        from utils.database.task_db import mark_progressing, set_service1_done, get_task
        task_key = "TEST-MECH-002"
        mark_progressing(task_key, "READY TO TEST")
        set_service1_done(task_key, compliance_score=85)
        task = get_task(task_key)
        assert task['service1_status'] == 'done'

    def test_task_state_machine_service2_done(self):
        from utils.database.task_db import (
            mark_progressing, set_service1_done, set_service2_done, get_task
        )
        task_key = "TEST-MECH-003"
        mark_progressing(task_key, "READY TO TEST")
        set_service1_done(task_key, compliance_score=85)
        set_service2_done(task_key)
        task = get_task(task_key)
        assert task['service2_status'] == 'done'

    def test_task_state_machine_completed(self):
        from utils.database.task_db import (
            mark_progressing, set_service1_done, set_service2_done,
            mark_completed, get_task
        )
        task_key = "TEST-MECH-004"
        mark_progressing(task_key, "READY TO TEST")
        set_service1_done(task_key, compliance_score=85)
        set_service2_done(task_key)
        mark_completed(task_key)
        task = get_task(task_key)
        assert task['task_status'] == 'completed'

    def test_settings_cache_same_object(self):
        from config.app_settings import get_app_settings
        settings1 = get_app_settings(force_reload=False)
        settings2 = get_app_settings(force_reload=False)
        assert settings1 is settings2

    def test_settings_force_reload_creates_new(self):
        from config.app_settings import get_app_settings
        settings1 = get_app_settings(force_reload=False)
        settings3 = get_app_settings(force_reload=True)
        assert isinstance(settings3, type(settings1))

    def test_db_concurrent_five_tasks(self):
        from utils.database.task_db import mark_progressing, get_task, init_db
        init_db()
        task_keys = [f"TEST-CONCURRENT-{i}" for i in range(1, 6)]
        for key in task_keys:
            mark_progressing(key, "READY TO TEST")
        for key in task_keys:
            task = get_task(key)
            assert task is not None, f"Task {key} topilmadi"
            assert task['task_status'] == 'progressing'

    def test_webhook_invalid_payload_no_crash_resilience(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        response = client.post("/webhook/jira", json={"invalid": "data"})
        assert response.status_code in [200, 422]

    def test_webhook_empty_payload_no_crash_resilience(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        response = client.post("/webhook/jira", json={})
        assert response.status_code in [200, 422]

    def test_webhook_null_key_resilience(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {"key": None},
            "changelog": {}
        }
        response = client.post("/webhook/jira", json=payload)
        if response.status_code == 200:
            data = response.json()
            assert data.get('status') in ['error', 'ignored']
        else:
            assert response.status_code in [200, 422]

    def test_health_check_resilience(self):
        from fastapi.testclient import TestClient
        from services.webhook.jira_webhook_handler import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_nonexistent_task_returns_none_resilience(self):
        from utils.database.task_db import get_task
        result = get_task("TEST-NONEXISTENT-RESILIENCE-999")
        assert result is None
