# utils/jira/jira_comment_writer.py
"""
JIRA Comment Writer - JIRA taskga comment qo'shish

AI tahlil natijalarini JIRA comment sifatida yozadi.
REST API v3 orqali ADF (Atlassian Document Format) qo'llab-quvvatlaydi.

Author: JASUR TURGUNOV
Version: 2.0 - ADF Support
"""
from jira import JIRA
import os
import requests
from typing import Dict, Optional
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


class JiraCommentWriter:
    """JIRA ga comment yozish (ADF va oddiy format)"""

    def __init__(self):
        """JIRA client yaratish"""
        self.server = os.getenv('JIRA_SERVER', 'https://smartupx.atlassian.net')
        self.email = os.getenv('JIRA_EMAIL')
        self.api_token = os.getenv('JIRA_API_TOKEN')

        # python-jira client (oddiy format uchun)
        try:
            self.jira = JIRA(
                server=self.server,
                basic_auth=(self.email, self.api_token)
            )
            logger.info("✅ JIRA connected for commenting")
        except Exception as e:
            logger.error(f"❌ JIRA connection failed: {e}")
            self.jira = None

        # REST API session (ADF format uchun)
        self._session = None

    @property
    def session(self) -> requests.Session:
        """REST API session (lazy loading)"""
        if self._session is None:
            self._session = requests.Session()
            self._session.auth = (self.email, self.api_token)
            self._session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
        return self._session

    def add_comment_adf(self, task_key: str, adf_document: Dict) -> bool:
        """
        ADF formatda comment qo'shish (REST API v3)

        Bu metod expand panel (dropdown) ishlatish imkonini beradi.

        Args:
            task_key: JIRA task key (DEV-1234)
            adf_document: ADF format document (dict)

        Returns:
            True - success, False - failed
        """
        try:
            url = f"{self.server}/rest/api/3/issue/{task_key}/comment"

            payload = {
                "body": adf_document
            }

            response = self.session.post(url, json=payload)

            if response.status_code == 201:
                logger.info(f"✅ ADF Comment added to {task_key}")
                return True
            else:
                logger.error(
                    f"❌ ADF Comment failed: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ ADF Comment error for {task_key}: {e}")
            return False

    def add_comment(self, task_key: str, comment_text: str) -> bool:
        """
        Task ga comment qo'shish

        Args:
            task_key: JIRA task key (DEV-1234)
            comment_text: Comment matni (Markdown supported)

        Returns:
            True - success, False - failed
        """
        if not self.jira:
            logger.error("❌ JIRA client not initialized")
            return False

        try:
            # Comment qo'shish
            self.jira.add_comment(task_key, comment_text)

            logger.info(f"✅ Comment added to {task_key}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to add comment to {task_key}: {e}")
            return False

    def add_comment_with_visibility(
            self,
            task_key: str,
            comment_text: str,
            visibility_type: str = "role",
            visibility_value: str = "Developers"
    ) -> bool:
        """
        Comment qo'shish + visibility restriction

        Args:
            task_key: Task key
            comment_text: Comment matni
            visibility_type: "role" yoki "group"
            visibility_value: Role/group nomi (e.g., "Developers", "QA Team")

        Returns:
            True/False
        """
        if not self.jira:
            return False

        try:
            visibility = {
                "type": visibility_type,
                "value": visibility_value
            }

            self.jira.add_comment(
                task_key,
                comment_text,
                visibility=visibility
            )

            logger.info(f"✅ Restricted comment added to {task_key}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to add restricted comment: {e}")
            return False

    def update_comment(
            self,
            comment_id: str,
            new_text: str
    ) -> bool:
        """
        Mavjud commentni yangilash

        Args:
            comment_id: Comment ID
            new_text: Yangi matn
        """
        if not self.jira:
            return False

        try:
            comment = self.jira.comment(comment_id)
            comment.update(body=new_text)

            logger.info(f"✅ Comment {comment_id} updated")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to update comment: {e}")
            return False