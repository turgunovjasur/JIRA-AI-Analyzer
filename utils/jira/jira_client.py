# jira_client.py - FIGMA INTEGRATION ADDED
"""
JIRA API Client - Task va PR ma'lumotlarini olish

YANGI:
- Development Status API dan PR URL olish
- ✅ Figma link'larni olish (NEW!)
"""
from typing import Any, Dict, List, Optional

import requests
from jira import JIRA

from core.logger import get_logger
from utils.jira.task_details_cache import (
    get_cached_task_details,
    get_cached_task_details_state,
    make_task_details_cache_key,
    set_cached_task_details,
)

_log = get_logger("jira.client")


def _http_timeout(default: int = 30) -> int:
    """Tashqi HTTP so'rovlar timeouti — `queue.http_timeout` sozlamasidan (lazy)."""
    try:
        from config.app_settings import get_app_settings
        return int(get_app_settings(force_reload=False).queue.http_timeout) or default
    except Exception:
        return default


class JiraClient:
    """JIRA API bilan ishlash"""

    def __init__(self, server: str = None, email: str = None, token: str = None):
        from config.settings import settings

        self.server = (server or "").strip()
        self.email  = (email or "").strip()
        self.token  = (token or "").strip()

        missing = []
        if not self.server:
            missing.append("JIRA Server")
        if not self.email:
            missing.append("JIRA Email")
        if not self.token:
            missing.append("JIRA API Token")
        if missing:
            raise ValueError(f"JIRA credentials to'liq emas: {', '.join(missing)}")

        # Custom fields
        self.story_points_field = settings.STORY_POINTS_FIELD
        self.sprint_field = settings.SPRINT_FIELD
        self.pr_field = settings.PR_FIELD

        self._client = None

    @staticmethod
    def _normalize_user_name_candidate(value: Any) -> str:
        """User nomi uchun yaroqli bo'lgan text qiymatni tozalash."""
        if value is None:
            return ""

        text = str(value).strip()
        if not text:
            return ""

        lowered = text.lower()
        if lowered in {"none", "null", "n/a"}:
            return ""
        if " object at 0x" in text:
            return ""
        if text.startswith(("namespace(", "SimpleNamespace(")):
            return ""
        if text.startswith("<") and text.endswith(">"):
            return ""
        return text

    @classmethod
    def _resolve_user_name(cls, user: Any, fallback: str) -> str:
        """JIRA user object'dan ko'rinadigan ismni xavfsiz olish."""
        if not user:
            return fallback

        candidate_keys = ("displayName", "name", "emailAddress", "accountId")
        nested_keys = ("raw", "user", "assignee", "author")
        queue = [user]
        seen: set[int] = set()

        while queue:
            current = queue.pop(0)
            if current is None:
                continue

            marker = id(current)
            if marker in seen:
                continue
            seen.add(marker)

            if isinstance(current, dict):
                for key in candidate_keys:
                    value = cls._normalize_user_name_candidate(current.get(key))
                    if value:
                        return value

                for key in nested_keys:
                    nested = current.get(key)
                    if nested is not None:
                        queue.append(nested)
                continue

            for key in candidate_keys:
                try:
                    raw_value = getattr(current, key, None)
                except Exception:
                    raw_value = None
                value = cls._normalize_user_name_candidate(raw_value)
                if value:
                    return value

            for key in nested_keys:
                try:
                    nested = getattr(current, key, None)
                except Exception:
                    nested = None
                if nested is not None:
                    queue.append(nested)

            value = cls._normalize_user_name_candidate(current)
            if value:
                return value

        return fallback

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

    def get_issue(
            self,
            issue_key: str,
            expand: str = 'changelog,renderedFields',
            fields: Optional[str] = None,
    ) -> Optional[Any]:
        """Bitta issue ni olish"""
        try:
            kwargs = {}
            if expand is not None:
                kwargs["expand"] = expand
            if fields is not None:
                kwargs["fields"] = fields
            issue = self.client.issue(issue_key, **kwargs)
            return issue
        except Exception as e:
            print(f"❌ Issue olishda xatolik: {e}")
            # Auth xatosini aniqlab, tushunarli xabar qaytarish
            resp = getattr(e, 'response', None)
            status = getattr(e, 'status_code', None)
            is_auth_fail = (
                status in (401, 403)
                or (
                    resp is not None
                    and getattr(resp, 'headers', {}).get('X-Seraph-Loginreason') == 'AUTHENTICATED_FAILED'
                )
            )
            if is_auth_fail:
                raise RuntimeError(
                    "JIRA autentifikatsiya xatosi. "
                    "JIRA Email va API Token ni tekshiring (Sozlamalar → API Kalitlar)."
                ) from e
            return None

    def _task_detail_fields(self) -> str:
        fields = [
            "summary",
            "description",
            "issuetype",
            "status",
            "assignee",
            "reporter",
            "priority",
            self.story_points_field,
            self.pr_field,
            "created",
            "resolutiondate",
            "labels",
            "components",
        ]
        return ",".join(dict.fromkeys(field for field in fields if field))

    def _normalize_comment(self, comment: Any) -> Dict[str, Any]:
        def _value(key: str, default: Any = None) -> Any:
            if isinstance(comment, dict):
                return comment.get(key, default)
            return getattr(comment, key, default)

        created = str(_value("created", "") or "")
        return {
            "author": self._resolve_user_name(_value("author"), "Unknown"),
            "body": _value("body", "") or "",
            "created": created[:16].replace("T", " ") if created else "",
        }

    def _comments_from_issue_fields(self, fields: Any) -> List[Dict]:
        comments = []
        if hasattr(fields, 'comment') and hasattr(fields.comment, 'comments'):
            for comment in fields.comment.comments:
                comments.append(self._normalize_comment(comment))
        return comments

    def _fetch_recent_comments(self, issue_key: str, max_comments: int) -> Optional[List[Dict]]:
        """JIRA comment endpointidan faqat oxirgi N ta commentni olish."""
        try:
            limit = int(max_comments)
        except (TypeError, ValueError):
            return None
        if limit <= 0:
            return None

        url = f"{self.server}/rest/api/2/issue/{issue_key}/comment"
        try:
            first = requests.get(
                url,
                auth=(self.email, self.token),
                params={"startAt": 0, "maxResults": 1, "orderBy": "created"},
                timeout=_http_timeout(),
            )
            if first.status_code != 200:
                _log.warning(f"JIRA comments API status={first.status_code}: {first.text[:200]}")
                return None

            first_payload = first.json() or {}
            total = int(first_payload.get("total") or 0)
            start_at = max(total - limit, 0)

            response = requests.get(
                url,
                auth=(self.email, self.token),
                params={"startAt": start_at, "maxResults": limit, "orderBy": "created"},
                timeout=_http_timeout(),
            )
            if response.status_code != 200:
                _log.warning(f"JIRA comments API status={response.status_code}: {response.text[:200]}")
                return None

            payload = response.json() or {}
            return [self._normalize_comment(item) for item in payload.get("comments", []) or []]
        except Exception as exc:
            _log.warning(f"JIRA comments API error: {exc}")
            return None

    def get_task_details(
            self,
            issue_key: str,
            *,
            include_pr_urls: bool = True,
            include_figma_links: bool = True,
            use_cache: bool = True,
            max_comments_to_read: int | None = None,
    ) -> Optional[Dict]:
        """
        Task ning asosiy ma'lumotlarini olish (TZ uchun)

        ✅ YANGI: figma_links field qo'shildi!
        """
        try:
            comment_limit = int(max_comments_to_read or 0)
        except (TypeError, ValueError):
            comment_limit = 0
        limited_comments = comment_limit > 0

        cache_key = make_task_details_cache_key(self.server, self.email, issue_key)
        use_cache = bool(use_cache and not limited_comments)
        if use_cache:
            cached = get_cached_task_details(
                cache_key,
                need_pr_urls=include_pr_urls,
                need_figma_links=include_figma_links,
            )
            if cached is not None:
                return cached
            cached_state = get_cached_task_details_state(cache_key)
            if cached_state is not None:
                cached_task, has_pr_urls, has_figma_links = cached_state
                changed = False
                if include_pr_urls and not has_pr_urls:
                    pr_urls = self.extract_pr_urls_dev_status(issue_key, issue_id=cached_task.get('issue_id'))
                    if not pr_urls:
                        issue = self.get_issue(issue_key)
                        if issue:
                            pr_urls = self.extract_pr_urls_legacy(issue)
                    cached_task['pr_urls'] = pr_urls
                    has_pr_urls = True
                    changed = True
                if include_figma_links and not has_figma_links:
                    cached_task['figma_links'] = self.extract_figma_links_from_task_details(cached_task)
                    has_figma_links = True
                    changed = True
                if changed:
                    set_cached_task_details(
                        cache_key,
                        cached_task,
                        include_pr_urls=has_pr_urls,
                        include_figma_links=has_figma_links,
                    )
                return cached_task

        issue = self.get_issue(
            issue_key,
            fields=self._task_detail_fields() if limited_comments else None,
        )
        if not issue:
            return None

        fields = issue.fields

        # Comments olish
        comments = self._fetch_recent_comments(issue_key, comment_limit) if limited_comments else None
        if comments is None and limited_comments:
            fallback_issue = self.get_issue(issue_key)
            if fallback_issue:
                issue = fallback_issue
                fields = fallback_issue.fields
        if comments is None:
            comments = self._comments_from_issue_fields(fields)
            if limited_comments and comments:
                comments = comments[-comment_limit:]

        task_details = {
            'issue_id': str(getattr(issue, 'id', '') or ''),
            'key': issue.key,
            'summary': fields.summary or '',
            'description': fields.description or '',
            'type': getattr(fields.issuetype, 'name', '') if fields.issuetype else '',
            'status': getattr(fields.status, 'name', '') if fields.status else '',
            'assignee': self._resolve_user_name(fields.assignee, 'Unassigned'),
            'reporter': self._resolve_user_name(fields.reporter, 'Unknown'),
            'priority': getattr(fields.priority, 'name', 'None') if fields.priority else 'None',
            'story_points': getattr(fields, self.story_points_field, 0) or 0,
            'comments': comments,
            'pr_urls': [],
            'figma_links': [],
            'created': fields.created[:10] if fields.created else '',
            'resolved': fields.resolutiondate[:10] if fields.resolutiondate else '',
            'labels': list(fields.labels) if fields.labels else [],
            'components': [c.name for c in fields.components] if fields.components else []
        }

        # PR URLs olish. issue.id allaqachon bor, shuning uchun Jira issue qayta olinmaydi.
        if include_pr_urls:
            pr_urls = self.extract_pr_urls_dev_status(issue_key, issue_id=task_details.get('issue_id'))
            if not pr_urls:
                pr_urls = self.extract_pr_urls_legacy(issue)
            task_details['pr_urls'] = pr_urls

        # Figma link'lar description/comments ichidan olinadi, Jira qayta chaqirilmaydi.
        if include_figma_links:
            task_details['figma_links'] = self.extract_figma_links_from_task_details(task_details)

        if use_cache:
            set_cached_task_details(
                cache_key,
                task_details,
                include_pr_urls=include_pr_urls,
                include_figma_links=include_figma_links,
            )

        return task_details

    def extract_figma_links_from_task_details(self, task_details: Dict) -> List[Dict]:
        """Task details ichidagi description/comments dan Figma link'larni olish."""
        try:
            from utils.jira.jira_figma_helper import JiraFigmaHelper

            figma_links_objs = JiraFigmaHelper.extract_figma_urls(task_details)
            return [
                {
                    'url': link.url,
                    'file_key': link.file_key,
                    'name': link.name,
                    'source': link.source,
                    'author': link.author,
                    'node_id': link.node_id
                }
                for link in figma_links_objs
            ]
        except Exception as e:
            print(f"⚠️  Figma links error: {str(e)}")
            return []

    def get_figma_links(self, issue_key: str) -> List[Dict]:
        """
        ✅ YANGI METHOD: Task'dan Figma link'larni olish

        Returns:
            List[Dict]: Figma link'lar ro'yxati
        """
        try:

            cached = get_cached_task_details(
                make_task_details_cache_key(self.server, self.email, issue_key),
                need_pr_urls=False,
                need_figma_links=False,
            )
            if cached is not None:
                return self.extract_figma_links_from_task_details(cached)

            # Backward-compatible fallback for direct callers.
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
                        'author': self._resolve_user_name(c.author, 'Unknown'),
                        'body': c.body
                    })

            return self.extract_figma_links_from_task_details(task_details)

        except Exception as e:
            print(f"⚠️  Figma links error: {str(e)}")
            return []

    def extract_pr_urls_dev_status(self, issue_key: str, issue_id: str | None = None) -> List[Dict]:
        """Development Status API dan PR URL olish"""
        pr_urls = []

        try:
            numeric_id = str(issue_id or "").strip()
            if not numeric_id:
                # Dev Status API raqamli issueId talab qiladi, matn key emas.
                # Fallback faqat eski direct callerlar uchun qoldirilgan.
                issue = self.client.issue(issue_key)
                numeric_id = issue.id

            url = f"{self.server}/rest/dev-status/1.0/issue/detail"
            params = {
                'issueId': numeric_id,
                'applicationType': 'GitHub',
                'dataType': 'pullrequest'
            }

            response = requests.get(
                url,
                auth=(self.email, self.token),
                params=params,
                timeout=_http_timeout()
            )

            if response.status_code == 200:
                data = response.json()
                details = data.get('detail', [])

                if details and len(details) > 0:
                    detail = details[0]
                    pull_requests = detail.get('pullRequests', [])

                    _log.info(f"Dev Status API: {len(pull_requests)} ta PR topildi")

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
            _log.warning(f"Dev Status API error: {str(e)}")

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
                    'assignee': self._resolve_user_name(issue.fields.assignee, 'Unassigned')
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
                    'assignee': self._resolve_user_name(issue.fields.assignee, 'Unassigned')
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
                    'assignee': self._resolve_user_name(issue.fields.assignee, 'Unassigned')
                })

            return results

        except Exception as e:
            print(f"❌ Search xatolik: {e}")
            return []

    # ================================================================
    # SPRINT API METODLARI (Agile REST API)
    # ================================================================

    def get_boards(self, project_key: str = 'DEV') -> List[Dict]:
        """
        JIRA boardlarni olish.
        Returns: [{'id': 123, 'name': 'DEV board', 'type': 'scrum'}, ...]
        """
        try:
            boards = self.client.boards()
            results = []
            for b in boards:
                if not project_key or (
                    hasattr(b, 'location') and
                    getattr(b.location, 'projectKey', '') == project_key
                ):
                    results.append({
                        'id': b.id,
                        'name': b.name,
                        'type': getattr(b, 'type', 'unknown'),
                    })
            return results
        except Exception as e:
            _log.warning(f"get_boards error: {e}")
            return []

    def get_sprints(self, board_id: int, state: str = 'active,closed') -> List[Dict]:
        """
        Board dagi sprintlar ro'yxati.
        Args:
            board_id: JIRA board ID
            state: 'active', 'closed', 'future' yoki kombinatsiya
        Returns: [{'id', 'name', 'state', 'start_date', 'end_date'}, ...]
        """
        try:
            sprints = self.client.sprints(board_id, state=state)
            results = []
            for s in sprints:
                results.append({
                    'id': s.id,
                    'name': s.name,
                    'state': s.state,
                    'start_date': getattr(s, 'startDate', None),
                    'end_date': getattr(s, 'endDate', None),
                    'complete_date': getattr(s, 'completeDate', None),
                })
            return results
        except Exception as e:
            _log.warning(f"get_sprints error: {e}")
            return []

    def get_sprint_issues_full(self, sprint_id: int) -> List[Dict]:
        """
        Sprint dagi barcha tasklar — story points, assignee, status, changelog bilan.
        Bu dashboard uchun asosiy data source.

        Returns: [{
            'key', 'summary', 'type', 'status', 'assignee',
            'story_points', 'created', 'updated',
            'transitions': [{'from', 'to', 'timestamp', 'author'}, ...]
        }, ...]
        """
        try:
            jql = f'sprint = {sprint_id} ORDER BY created ASC'
            issues = self.client.search_issues(
                jql, maxResults=500, expand='changelog',
                fields='summary,issuetype,status,assignee,'
                       f'{self.story_points_field},created,updated,resolutiondate'
            )

            results = []
            for issue in issues:
                fields = issue.fields

                # Transitions (changelog dan)
                transitions = []
                if hasattr(issue, 'changelog') and issue.changelog:
                    for history in issue.changelog.histories:
                        for item in history.items:
                            if item.field == 'status':
                                transitions.append({
                                    'from_status': item.fromString or '',
                                    'to_status': item.toString or '',
                                    'timestamp': history.created,
                                    'author': self._resolve_user_name(history.author, 'Unknown'),
                                })

                results.append({
                    'key': issue.key,
                    'summary': fields.summary or '',
                    'type': getattr(fields.issuetype, 'name', '') if fields.issuetype else '',
                    'status': getattr(fields.status, 'name', '') if fields.status else '',
                    'assignee': self._resolve_user_name(fields.assignee, 'Unassigned'),
                    'story_points': getattr(fields, self.story_points_field, None) or 0,
                    'created': fields.created[:19] if fields.created else '',
                    'updated': fields.updated[:19] if fields.updated else '',
                    'resolved': fields.resolutiondate[:19] if fields.resolutiondate else None,
                    'transitions': transitions,
                })

            _log.info(f"Sprint {sprint_id}: {len(results)} task yuklandi")
            return results

        except Exception as e:
            _log.warning(f"get_sprint_issues_full error: {e}")
            return []
