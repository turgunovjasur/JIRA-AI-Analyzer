# utils/jira/jira_status_manager.py
"""
Jira Status Manager - Task statusini o'zgartirish

Avtomatik status o'zgartirish uchun:
- Moslik bali past bo'lsa "Return" statusga o'tkazish
- Mavjud transition'larni olish
- Status o'zgartirish

Author: JASUR TURGUNOV
Version: 1.0
"""
from jira import JIRA
import os
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class JiraStatusManager:
    """Jira task statusini boshqarish"""

    def __init__(self):
        """JIRA client yaratish"""
        try:
            self.jira = JIRA(
                server=os.getenv('JIRA_SERVER', 'https://smartupx.atlassian.net'),
                basic_auth=(
                    os.getenv('JIRA_EMAIL'),
                    os.getenv('JIRA_API_TOKEN')
                )
            )
            logger.info("✅ JIRA Status Manager connected")
        except Exception as e:
            logger.error(f"❌ JIRA connection failed: {e}")
            self.jira = None

    def get_available_transitions(self, task_key: str) -> List[Dict]:
        """
        Task uchun mavjud transition'larni olish

        Args:
            task_key: JIRA task key (DEV-1234)

        Returns:
            [
                {"id": "21", "name": "In Progress"},
                {"id": "31", "name": "Done"},
                ...
            ]
        """
        if not self.jira:
            logger.error("❌ JIRA client not initialized")
            return []

        try:
            transitions = self.jira.transitions(task_key)
            result = []
            for t in transitions:
                result.append({
                    "id": t['id'],
                    "name": t['name'],
                    "to": t.get('to', {}).get('name', '')
                })
            logger.info(f"📋 {task_key} uchun {len(result)} ta transition mavjud")
            return result

        except Exception as e:
            logger.error(f"❌ Transitions olishda xato: {e}")
            return []

    def find_transition_by_name(
            self,
            task_key: str,
            target_status: str
    ) -> Optional[str]:
        """
        Status nomi bo'yicha transition ID topish

        Args:
            task_key: Task key
            target_status: Maqsad status nomi (e.g., "Return", "Ready to Test")

        Returns:
            Transition ID yoki None
        """
        transitions = self.get_available_transitions(task_key)

        # To'g'ridan-to'g'ri match
        for t in transitions:
            if t['name'].lower() == target_status.lower():
                return t['id']
            if t['to'].lower() == target_status.lower():
                return t['id']

        # Partial match (agar to'liq mos kelmasa)
        target_lower = target_status.lower()
        for t in transitions:
            if target_lower in t['name'].lower() or target_lower in t['to'].lower():
                return t['id']

        logger.warning(f"⚠️ '{target_status}' transition topilmadi")
        return None

    def change_status(
            self,
            task_key: str,
            new_status: str,
            comment: str = None
    ) -> Tuple[bool, str]:
        """
        Task statusini o'zgartirish

        Args:
            task_key: JIRA task key
            new_status: Yangi status nomi
            comment: Ixtiyoriy comment

        Returns:
            (success: bool, message: str)
        """
        if not self.jira:
            return False, "JIRA client not initialized"

        try:
            # Transition ID topish
            transition_id = self.find_transition_by_name(task_key, new_status)

            if not transition_id:
                available = self.get_available_transitions(task_key)
                available_names = [t['name'] for t in available]
                return False, f"'{new_status}' topilmadi. Mavjud: {available_names}"

            # Transition bajarish
            if comment:
                self.jira.transition_issue(
                    task_key,
                    transition_id,
                    comment=comment
                )
            else:
                self.jira.transition_issue(task_key, transition_id)

            logger.info(f"✅ {task_key} → {new_status}")
            return True, f"Status o'zgartirildi: {new_status}"

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Status o'zgartirishda xato: {error_msg}")
            return False, f"Xato: {error_msg}"

    def get_current_status(self, task_key: str) -> Optional[str]:
        """
        Task'ning hozirgi statusini olish

        Args:
            task_key: JIRA task key

        Returns:
            Status nomi yoki None
        """
        if not self.jira:
            return None

        try:
            issue = self.jira.issue(task_key)
            return issue.fields.status.name

        except Exception as e:
            logger.error(f"❌ Status olishda xato: {e}")
            return None

    def auto_return_if_needed(
            self,
            task_key: str,
            compliance_score: int,
            threshold: int,
            return_status: str,
            enabled: bool = True
    ) -> Tuple[bool, str]:
        """
        Moslik bali past bo'lsa avtomatik Return

        Args:
            task_key: Task key
            compliance_score: Moslik foizi (0-100)
            threshold: Qaytarish chegarasi (e.g., 60)
            return_status: Qaytarish status nomi
            enabled: Avtomatik qaytarish yoqilganmi

        Returns:
            (action_taken: bool, message: str)
        """
        if not enabled:
            return False, "Avtomatik Return o'chirilgan"

        if compliance_score >= threshold:
            return False, f"Moslik {compliance_score}% >= {threshold}% (qaytarish kerak emas)"

        # Return qilish kerak (notification comment alohida ADF format ile yoziladi)
        success, msg = self.change_status(task_key, return_status)

        if success:
            return True, f"Task {return_status} ga qaytarildi (moslik: {compliance_score}%)"
        else:
            return False, f"Qaytarishda xato: {msg}"


# Singleton instance
_status_manager: Optional[JiraStatusManager] = None


def get_status_manager() -> JiraStatusManager:
    """Status manager instance olish"""
    global _status_manager
    if _status_manager is None:
        _status_manager = JiraStatusManager()
    return _status_manager
