# jira_client.py - FIGMA INTEGRATION ADDED
"""
JIRA API Client - Task va PR ma'lumotlarini olish

YANGI:
- Development Status API dan PR URL olish
- ✅ Figma link'larni olish (NEW!)
"""
from jira import JIRA
from typing import Dict, List, Optional, Any
import json
import requests


class JiraClient:
    """JIRA API bilan ishlash"""

    def __init__(self):
        from config.settings import settings

        self.server = settings.JIRA_SERVER
        self.email = settings.JIRA_EMAIL
        self.token = settings.JIRA_API_TOKEN

        # Custom fields
        self.story_points_field = settings.STORY_POINTS_FIELD
        self.sprint_field = settings.SPRINT_FIELD
        self.pr_field = settings.PR_FIELD

        self._client = None

    @property
    def client(self) -> JIRA:
        """Lazy connection"""
        if self._client is None:
            self._client = JIRA(
                server=self.server,
                basic_auth=(self.email, self.token)
            )
        return self._client

    def test_connection(self) -> bool:
        """JIRA ulanishini tekshirish"""
        try:
            myself = self.client.myself()
            print(f"✅ JIRA ulandi: {myself['displayName']}")
            return True
        except Exception as e:
            print(f"❌ JIRA ulanish xatosi: {e}")
            return False

    def get_issue(self, issue_key: str, expand: str = 'changelog,renderedFields') -> Optional[Any]:
        """Bitta issue ni olish"""
        try:
            issue = self.client.issue(issue_key, expand=expand)
            return issue
        except Exception as e:
            print(f"❌ Issue olishda xatolik: {e}")
            return None

    def get_task_details(self, issue_key: str) -> Optional[Dict]:
        """
        Task ning asosiy ma'lumotlarini olish (TZ uchun)

        ✅ YANGI: figma_links field qo'shildi!
        """
        issue = self.get_issue(issue_key)
        if not issue:
            return None

        fields = issue.fields

        # Comments olish
        comments = []
        if hasattr(fields, 'comment') and hasattr(fields.comment, 'comments'):
            for c in fields.comment.comments:
                comments.append({
                    'author': getattr(c.author, 'displayName', 'Unknown'),
                    'body': c.body,
                    'created': c.created[:16].replace('T', ' ')
                })

        # PR URLs olish
        pr_urls = self.extract_pr_urls_dev_status(issue_key)
        if not pr_urls:
            pr_urls = self.extract_pr_urls_legacy(issue)

        # ✅ FIGMA INTEGRATION
        figma_links = self.get_figma_links(issue_key)

        return {
            'key': issue.key,
            'summary': fields.summary or '',
            'description': fields.description or '',
            'type': getattr(fields.issuetype, 'name', '') if fields.issuetype else '',
            'status': getattr(fields.status, 'name', '') if fields.status else '',
            'assignee': getattr(fields.assignee, 'displayName', 'Unassigned') if fields.assignee else 'Unassigned',
            'reporter': getattr(fields.reporter, 'displayName', 'Unknown') if fields.reporter else 'Unknown',
            'priority': getattr(fields.priority, 'name', 'None') if fields.priority else 'None',
            'story_points': getattr(fields, self.story_points_field, 0) or 0,
            'comments': comments,
            'pr_urls': pr_urls,
            'figma_links': figma_links,  # ✅ YANGI!
            'created': fields.created[:10] if fields.created else '',
            'resolved': fields.resolutiondate[:10] if fields.resolutiondate else '',
            'labels': list(fields.labels) if fields.labels else [],
            'components': [c.name for c in fields.components] if fields.components else []
        }

    def get_figma_links(self, issue_key: str) -> List[Dict]:
        """
        ✅ YANGI METHOD: Task'dan Figma link'larni olish

        Returns:
            List[Dict]: Figma link'lar ro'yxati
        """
        try:
            from utils.jira.jira_figma_helper import JiraFigmaHelper

            # Get minimal task data
            issue = self.get_issue(issue_key)
            if not issue:
                return []

            task_details = {
                'description': issue.fields.description or '',
                'comments': []
            }

            if hasattr(issue.fields, 'comment') and hasattr(issue.fields.comment, 'comments'):
                for c in issue.fields.comment.comments:
                    task_details['comments'].append({
                        'author': getattr(c.author, 'displayName', 'Unknown'),
                        'body': c.body
                    })

            # Extract Figma links
            figma_links_objs = JiraFigmaHelper.extract_figma_urls(task_details)

            # Convert to dict
            return [
                {
                    'url': link.url,
                    'file_key': link.file_key,
                    'name': link.name,
                    'source': link.source,
                    'author': link.author
                }
                for link in figma_links_objs
            ]

        except Exception as e:
            print(f"⚠️  Figma links error: {str(e)}")
            return []

    def extract_pr_urls_dev_status(self, issue_key: str) -> List[Dict]:
        """Development Status API dan PR URL olish"""
        pr_urls = []

        try:
            url = f"{self.server}/rest/dev-status/1.0/issue/detail"
            params = {
                'issueId': issue_key,
                'applicationType': 'GitHub',
                'dataType': 'pullrequest'
            }

            response = requests.get(
                url,
                auth=(self.email, self.token),
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                details = data.get('detail', [])

                if details and len(details) > 0:
                    detail = details[0]
                    pull_requests = detail.get('pullRequests', [])

                    print(f"   ✅ Dev Status API: {len(pull_requests)} ta PR topildi!")

                    for pr in pull_requests:
                        pr_url = pr.get('url', '')
                        if pr_url and 'github.com' in pr_url:
                            pr_urls.append({
                                'url': pr_url,
                                'title': pr.get('name', 'PR'),
                                'status': pr.get('status', 'UNKNOWN'),
                                'source': 'dev_status_api'
                            })

        except Exception as e:
            print(f"   ⚠️  Dev Status API error: {str(e)}")

        return pr_urls

    def extract_pr_urls_legacy(self, issue: Any) -> List[Dict]:
        """Legacy method: Custom PR field'dan qidirish"""
        pr_urls = []

        try:
            if hasattr(issue.fields, self.pr_field):
                pr_field_value = getattr(issue.fields, self.pr_field, None)

                if pr_field_value:
                    import re
                    github_pattern = r'https://github\.com/[^\s<>"\']+'

                    pr_field_str = str(pr_field_value)
                    matches = re.findall(github_pattern, pr_field_str)

                    for url in matches:
                        if '/pull/' in url:
                            pr_urls.append({
                                'url': url,
                                'title': 'PR',
                                'status': 'UNKNOWN',
                                'source': 'custom_field'
                            })

        except Exception as e:
            print(f"   ⚠️  Legacy PR extraction error: {str(e)}")

        return pr_urls

    def get_sprint_tasks(self, sprint_name: str) -> List[Dict]:
        """Sprint'dagi task'larni olish"""
        try:
            jql = f'Sprint = "{sprint_name}" ORDER BY created DESC'
            issues = self.client.search_issues(jql, maxResults=500)

            results = []
            for issue in issues:
                results.append({
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'type': getattr(issue.fields.issuetype, 'name', ''),
                    'status': getattr(issue.fields.status, 'name', ''),
                    'assignee': getattr(issue.fields.assignee, 'displayName',
                                        'Unassigned') if issue.fields.assignee else 'Unassigned'
                })

            return results

        except Exception as e:
            print(f"❌ Sprint tasks xatolik: {e}")
            return []

    def get_bug_tasks(self, sprint_name: Optional[str] = None) -> List[Dict]:
        """Bug'larni olish"""
        try:
            if sprint_name:
                jql = f'Sprint = "{sprint_name}" AND type = Bug ORDER BY created DESC'
            else:
                jql = 'type = Bug AND status != Done ORDER BY created DESC'

            issues = self.client.search_issues(jql, maxResults=500)

            results = []
            for issue in issues:
                results.append({
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'status': getattr(issue.fields.status, 'name', ''),
                    'priority': getattr(issue.fields.priority, 'name', 'None'),
                    'assignee': getattr(issue.fields.assignee, 'displayName',
                                        'Unassigned') if issue.fields.assignee else 'Unassigned'
                })

            return results

        except Exception as e:
            print(f"❌ Bug tasks xatolik: {e}")
            return []

    def search_tasks(self, jql: str, max_results: int = 100) -> List[Dict]:
        """JQL orqali qidirish"""
        try:
            issues = self.client.search_issues(jql, maxResults=max_results)

            results = []
            for issue in issues:
                results.append({
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'type': getattr(issue.fields.issuetype, 'name', ''),
                    'status': getattr(issue.fields.status, 'name', ''),
                    'assignee': getattr(issue.fields.assignee, 'displayName',
                                        'Unassigned') if issue.fields.assignee else 'Unassigned'
                })

            return results

        except Exception as e:
            print(f"❌ Search xatolik: {e}")
            return []