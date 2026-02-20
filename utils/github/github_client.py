# utils/github/github_client.py
"""
GitHub API Client - PR va kod olish

FIX: contents_url qo'shildi (Smart Patch uchun)

YANGI: Branch name bilan ham PR qidirish!
"""
import requests
import base64
import re
from typing import List, Dict, Optional, Tuple
import time

from core.logger import get_logger

log = get_logger("github.client")


class GitHubClient:
    """GitHub API bilan ishlash"""

    def __init__(self, token: str = None):
        """
        Args:
            token: GitHub Personal Access Token
        """
        from config.settings import settings

        self.token = token or settings.GITHUB_TOKEN
        self.base_url = settings.GITHUB_API_URL
        self.org = settings.GITHUB_ORG

        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'JIRA-Bug-Analyzer'
        }

        if self.token:
            self.headers['Authorization'] = f'token {self.token}'

        # Rate limit tracking
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = 0

        # Session for backward compatibility with tz_pr_service
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _make_request(self, url: str, accept_header: str = None, params: Dict = None) -> requests.Response:
        """API so'rov yuborish (rate limit bilan)"""
        headers = self.headers.copy()
        if accept_header:
            headers['Accept'] = accept_header

        # Rate limit tekshirish
        if self.rate_limit_remaining < 10:
            wait_time = self.rate_limit_reset - time.time()
            if wait_time > 0:
                log.warning(f"Rate limit kutish: {wait_time:.0f} sekund")
                time.sleep(wait_time + 1)

        # Get timeout from settings
        try:
            from config.app_settings import get_app_settings
            timeout = get_app_settings(force_reload=False).queue.http_timeout
        except Exception:
            timeout = 30  # Default fallback
        
        response = requests.get(url, headers=headers, params=params, timeout=timeout)

        # Rate limit yangilash
        self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 5000))
        self.rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))

        return response

    def parse_pr_url(self, pr_url: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        """
        PR URL dan owner, repo, pr_number ajratish

        Supports:
        - https://github.com/owner/repo/pull/123
        - https://github.com/owner/repo/pull/123/files
        - github.com/owner/repo/pull/123

        Returns:
            (owner, repo, pr_number) yoki (None, None, None)
        """
        patterns = [
            r'github\.com/([^/]+)/([^/]+)/pull/(\d+)',
            r'github\.com/([^/]+)/([^/]+)/pulls/(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, pr_url)
            if match:
                return match.group(1), match.group(2), int(match.group(3))

        return None, None, None

    def get_pr_info(self, owner: str, repo: str, pr_number: int) -> Optional[Dict]:
        """PR asosiy ma'lumotlarini olish"""
        url = f'{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}'
        response = self._make_request(url)

        if response.status_code != 200:
            log.error(f"PR info olishda xatolik: {response.status_code}")
            return None

        data = response.json()

        return {
            'title': data.get('title', ''),
            'state': data.get('state', ''),
            'merged': data.get('merged', False),
            'user': data.get('user', {}).get('login', ''),
            'created_at': data.get('created_at', ''),
            'merged_at': data.get('merged_at', ''),
            'base': data.get('base', {}).get('ref', ''),
            'head': data.get('head', {}).get('ref', ''),
            'head_sha': data.get('head', {}).get('sha', ''),  # 🔥 HEAD SHA qo'shildi
            'commits': data.get('commits', 0),
            'additions': data.get('additions', 0),
            'deletions': data.get('deletions', 0),
            'changed_files': data.get('changed_files', 0),
            'body': data.get('body', '')
        }

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        """
        PR da o'zgargan fayllar ro'yxatini olish

        FIX: contents_url qo'shildi - Smart Patch uchun kerak!
        """
        url = f'{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files'

        all_files = []
        page = 1
        per_page = 100

        while True:
            paginated_url = f'{url}?page={page}&per_page={per_page}'
            response = self._make_request(paginated_url)

            if response.status_code != 200:
                log.error(f"PR files olishda xatolik: {response.status_code}")
                break

            files = response.json()
            if not files:
                break

            for f in files:
                all_files.append({
                    'filename': f.get('filename', ''),
                    'status': f.get('status', ''),
                    'additions': f.get('additions', 0),
                    'deletions': f.get('deletions', 0),
                    'changes': f.get('changes', 0),
                    'patch': f.get('patch', ''),
                    'blob_url': f.get('blob_url', ''),
                    'raw_url': f.get('raw_url', ''),
                    'contents_url': f.get('contents_url', ''),  # QO'SHILDI! Smart Patch uchun
                    'sha': f.get('sha', ''),
                    'previous_filename': f.get('previous_filename', '')
                })

            if len(files) < per_page:
                break
            page += 1

        return all_files

    def get_file_content(self, owner: str, repo: str, path: str, ref: str = 'main') -> Optional[str]:
        """Faylning to'liq mazmunini olish"""
        url = f'{self.base_url}/repos/{owner}/{repo}/contents/{path}?ref={ref}'
        response = self._make_request(url)

        if response.status_code != 200:
            log.error(f"File content olishda xatolik: {response.status_code} - {path}")
            return None

        data = response.json()

        # Base64 decode
        content = data.get('content', '')
        if content:
            try:
                return base64.b64decode(content).decode('utf-8')
            except Exception as e:
                log.warning(f"Decode xatolik: {e}")
                return None

        return None

    def get_file_content_by_sha(self, owner: str, repo: str, sha: str) -> Optional[str]:
        """
        YANGI: Blob API orqali fayl content olish

        Bu usul private repositorylar uchun ishlaydi!
        """
        url = f'{self.base_url}/repos/{owner}/{repo}/git/blobs/{sha}'
        response = self._make_request(url)

        if response.status_code != 200:
            log.error(f"Blob olishda xatolik: {response.status_code}")
            return None

        data = response.json()

        if data.get('encoding') == 'base64':
            content_b64 = data.get('content', '')
            if content_b64:
                try:
                    return base64.b64decode(content_b64).decode('utf-8', errors='ignore')
                except Exception as e:
                    log.warning(f"Blob decode xatolik: {e}")
                    return None

        return None

    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> Optional[str]:
        """PR ning to'liq diff'ini olish"""
        url = f'{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}'
        response = self._make_request(url, accept_header='application/vnd.github.v3.diff')

        if response.status_code == 200:
            return response.text

        return None

    def get_pr_commits(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        """PR dagi commitlar ro'yxati"""
        url = f'{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/commits'
        response = self._make_request(url)

        if response.status_code != 200:
            return []

        commits = []
        for c in response.json():
            commits.append({
                'sha': c.get('sha', '')[:7],
                'message': c.get('commit', {}).get('message', ''),
                'author': c.get('commit', {}).get('author', {}).get('name', ''),
                'date': c.get('commit', {}).get('author', {}).get('date', '')
            })

        return commits

    def check_rate_limit(self) -> Dict:
        """Rate limit holatini tekshirish"""
        url = f'{self.base_url}/rate_limit'
        response = self._make_request(url)

        if response.status_code == 200:
            data = response.json()
            core = data.get('resources', {}).get('core', {})
            return {
                'limit': core.get('limit', 0),
                'remaining': core.get('remaining', 0),
                'reset': core.get('reset', 0),
                'used': core.get('used', 0)
            }

        return {}

    def test_connection(self) -> bool:
        """GitHub ulanishini tekshirish"""
        try:
            rate_info = self.check_rate_limit()
            if rate_info:
                log.info(f"GitHub ulandi!")
                log.info(f"Rate limit: {rate_info['remaining']}/{rate_info['limit']}")
                return True
        except Exception as e:
            log.error(f"GitHub ulanish xatosi: {e}")

        return False

    def search_pr_by_jira_key(self, jira_key: str) -> List[Dict]:
        """
        Jira Key (masalan DEV-6959) bo'yicha GitHub dan PR qidirish.
        Bu metod Jira link bermagan holatlar uchun zaxira yo'li.

        YANGI: Multi-strategy search!
        1. Title/body'da JIRA key bor PR'lar
        2. Branch name'da JIRA key bor PR'lar (head:branch-name)
        """
        url = f"{self.base_url}/search/issues"
        found_prs = []

        # Strategy 1: Search in title and body
        query1 = f'org:{self.org} "{jira_key}" is:pr'
        log.debug(f"GitHub Search (title/body): {query1}")

        try:
            response1 = self._make_request(url, params={'q': query1, 'sort': 'updated'})

            if response1.status_code == 200:
                items = response1.json().get('items', [])
                for item in items:
                    found_prs.append({
                        'url': item.get('html_url'),
                        'title': item.get('title'),
                        'status': item.get('state'),
                        'source': 'GitHub (title/body)'
                    })

                if items:
                    log.debug(f"Title/body search: {len(items)} ta topildi!")
            else:
                log.warning(f"Title/body search error: {response1.status_code}")
        except Exception as e:
            log.warning(f"Title/body search exception: {e}")

        # Strategy 2: Search in branch names (if not found in title/body)
        if not found_prs:
            log.debug(f"Branch name search...")

            # Common branch patterns
            branch_patterns = [
                jira_key,  # DEV-6959
                jira_key.lower(),  # dev-6959
                jira_key.replace('-', '_'),  # DEV_6959
                f"feature/{jira_key}",  # feature/DEV-6959
                f"bugfix/{jira_key}",  # bugfix/DEV-6959
                f"fix/{jira_key}",  # fix/DEV-6959
            ]

            for pattern in branch_patterns:
                query2 = f'org:{self.org} head:{pattern} is:pr'

                try:
                    response2 = self._make_request(url, params={'q': query2, 'sort': 'updated'})

                    if response2.status_code == 200:
                        items = response2.json().get('items', [])
                        for item in items:
                            pr_url = item.get('html_url')
                            # Avoid duplicates
                            if not any(pr['url'] == pr_url for pr in found_prs):
                                found_prs.append({
                                    'url': pr_url,
                                    'title': item.get('title'),
                                    'status': item.get('state'),
                                    'source': f'GitHub (branch:{pattern})'
                                })

                        # If found, break
                        if items:
                            log.debug(f"Branch search: {len(items)} ta topildi (pattern: {pattern})!")
                            break
                except Exception as e:
                    log.warning(f"Branch search exception ({pattern}): {e}")
                    continue

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Strategy 3: Numeric part broad search + verification
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        numeric_part, prefix_part = self._extract_numeric_part(jira_key)

        if not found_prs and numeric_part:
            found_prs = self._search_by_numeric_part(jira_key, numeric_part, url)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Strategy 4: Extended head: patterns (numeric-only)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if not found_prs and numeric_part:
            found_prs = self._search_extended_branch_patterns(jira_key, numeric_part, prefix_part, url)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Strategy 5: Repo PR listing (last resort)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if not found_prs and numeric_part:
            found_prs = self._search_by_repo_listing(jira_key, numeric_part)

        # Final result
        if not found_prs:
            log.warning("Hech qanday PR topilmadi")

        return found_prs

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # HELPER METHODS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _extract_numeric_part(self, jira_key: str) -> Tuple[Optional[str], Optional[str]]:
        """
        JIRA key dan numeric va prefix qismini ajratish.

        DEV-7068 → ('7068', 'DEV-')
        PROJ-123 → ('123', 'PROJ-')
        DEV-0042 → ('0042', 'DEV-')  leading zeros saqlandi

        Returns:
            (numeric_part, prefix_part) yoki (None, None)
        """
        match = re.match(r'^([A-Z]+-?)(\d+)$', jira_key.strip().upper())
        if match:
            return match.group(2), match.group(1)
        return None, None

    def _verify_pr_for_ticket(self, pr_url: str, numeric_part: str, jira_key: str) -> Tuple[bool, str]:
        """
        PR URL'ni JIRA ticketga aloqadorligini tekshirish.

        Verification checks (priority order):
        1. head branch'da numeric_part substring
        2. title/body'da full jira_key (case-insensitive)
        3. title/body'da numeric_part with word-boundary isolation

        Returns:
            (is_match, reason) — reason debug log uchun
        """
        owner, repo, pr_number = self.parse_pr_url(pr_url)
        if not all([owner, repo, pr_number]):
            return False, "URL parse failed"

        log.debug(f"Verifying PR #{pr_number} ({owner}/{repo})...")

        pr_info = self.get_pr_info(owner, repo, pr_number)
        if not pr_info:
            return False, "get_pr_info returned None"

        head_branch = pr_info.get('head', '')
        title = pr_info.get('title', '')
        body = pr_info.get('body', '') or ''

        # Check 1: numeric_part in head branch name
        if numeric_part in head_branch:
            return True, f"branch '{head_branch}' contains '{numeric_part}'"

        # Check 2: full jira_key in title+body (case-insensitive)
        combined = f"{title} {body}".lower()
        if jira_key.lower() in combined:
            return True, f"title/body contains '{jira_key}'"

        # Check 3: numeric_part with word-boundary ((?<!\d)7068(?!\d))
        boundary_pattern = r'(?<!\d)' + re.escape(numeric_part) + r'(?!\d)'
        if re.search(boundary_pattern, combined):
            return True, f"title/body contains '{numeric_part}' (word-boundary)"

        return False, f"no match in branch '{head_branch}' or title/body"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STRATEGY 3: Numeric broad search + verification
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _search_by_numeric_part(self, jira_key: str, numeric_part: str, search_url: str) -> List[Dict]:
        """
        Strategy 3: Unquoted numeric search + post-filter verification.

        Query: org:{org} {numeric_part} is:pr  (unquoted — matches anywhere in PR index)
        Then verify each candidate via get_pr_info() to avoid false positives.
        """
        found = []
        query = f'org:{self.org} {numeric_part} is:pr'
        log.debug(f"Numeric search: {query} (from {jira_key})")

        try:
            response = self._make_request(search_url, params={
                'q': query,
                'sort': 'updated',
                'per_page': 10
            })

            if response.status_code != 200:
                log.warning(f"Numeric search error: {response.status_code}")
                return found

            items = response.json().get('items', [])
            log.debug(f"Numeric search: {len(items)} candidate(s) found, verifying...")

            for item in items:
                pr_url = item.get('html_url')
                if not pr_url:
                    continue

                is_match, reason = self._verify_pr_for_ticket(pr_url, numeric_part, jira_key)

                if is_match:
                    log.debug(f"PR matched: {reason}")
                    found.append({
                        'url': pr_url,
                        'title': item.get('title'),
                        'status': item.get('state'),
                        'source': 'GitHub (numeric-search)'
                    })
                    break  # First valid match is enough
                else:
                    log.debug(f"PR rejected: {reason}")

            if not found:
                log.debug(f"Numeric search: all candidates rejected")

        except Exception as e:
            log.warning(f"Numeric search exception: {e}")

        return found

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STRATEGY 4: Extended head: patterns (numeric-only variants)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _search_extended_branch_patterns(
            self, jira_key: str, numeric_part: str, prefix_part: str, search_url: str
    ) -> List[Dict]:
        """
        Strategy 4: head: patterns using numeric-only branch names.

        Covers cases like:
        - 7068 (bare number)
        - 7068b (number + letter suffix)
        - fix/7068, feature/7068, etc.
        - DEV7068 (prefix without hyphen)
        """
        found = []
        prefix_clean = prefix_part.rstrip('-') if prefix_part else ''

        patterns = [
            numeric_part,                                    # 7068
            f"{numeric_part}b",                              # 7068b
            f"fix-{numeric_part}",                           # fix-7068
            f"fix/{numeric_part}",                           # fix/7068
            f"hotfix-{numeric_part}",                        # hotfix-7068
            f"hotfix/{numeric_part}",                        # hotfix/7068
            f"feature-{numeric_part}",                       # feature-7068
            f"feature/{numeric_part}",                       # feature/7068
            f"bugfix-{numeric_part}",                        # bugfix-7068
            f"bugfix/{numeric_part}",                        # bugfix/7068
            f"{prefix_clean}{numeric_part}",                 # DEV7068
            f"{prefix_clean.lower()}{numeric_part}",         # dev7068
        ]

        # Deduplicate while preserving order
        seen = set()
        unique_patterns = []
        for p in patterns:
            if p not in seen:
                seen.add(p)
                unique_patterns.append(p)

        log.debug(f"Extended branch patterns (numeric): {len(unique_patterns)} patterns...")

        for pattern in unique_patterns:
            query = f'org:{self.org} head:{pattern} is:pr'

            try:
                response = self._make_request(search_url, params={'q': query, 'sort': 'updated'})

                if response.status_code == 200:
                    items = response.json().get('items', [])
                    for item in items:
                        pr_url = item.get('html_url')
                        if not any(pr['url'] == pr_url for pr in found):
                            found.append({
                                'url': pr_url,
                                'title': item.get('title'),
                                'status': item.get('state'),
                                'source': f'GitHub (extended-branch:{pattern})'
                            })

                    if items:
                        log.debug(f"Extended branch: {len(items)} ta topildi (pattern: {pattern})!")
                        break  # Found — stop trying patterns

            except Exception as e:
                log.warning(f"Extended branch exception ({pattern}): {e}")
                continue

        if not found:
            log.debug(f"Extended branch patterns: nothing found")

        return found

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STRATEGY 5: Org repo listing + local branch filter (last resort)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _get_org_repos(self, max_repos: int = 5) -> List[Dict]:
        """Org'dagi eng so'nggi update qilgan repo'larni olish"""
        url = f"{self.base_url}/orgs/{self.org}/repos"
        response = self._make_request(url, params={
            'sort': 'updated',
            'per_page': max_repos
        })

        if response.status_code == 200:
            return response.json()

        log.warning(f"Org repos olishda xatolik: {response.status_code}")
        return []

    def _search_by_repo_listing(self, jira_key: str, numeric_part: str) -> List[Dict]:
        """
        Strategy 5: Org'dagi repo'larning PR list'larini scan qilib
        branch name'da numeric_part qidirish.

        GitHub search index hali yangilanmagan holat uchun zaxira.
        Faqat 5 eng so'nggi repo tekshiriladi.
        """
        found = []
        print(f"   🔎 Repo listing search (last resort): numeric '{numeric_part}' qidirilmoqda...")

        try:
            repos = self._get_org_repos(max_repos=5)
            if not repos:
                print(f"   ⚠️ Repo listing: no repos returned")
                return found

            for repo_data in repos:
                repo_name = repo_data.get('name', '')
                owner = repo_data.get('owner', {}).get('login', self.org)
                print(f"   🔍 Checking repo: {owner}/{repo_name}...")

                try:
                    pr_list_url = f"{self.base_url}/repos/{owner}/{repo_name}/pulls"
                    response = self._make_request(pr_list_url, params={
                        'state': 'all',
                        'per_page': 100,
                        'sort': 'updated'
                    })

                    if response.status_code != 200:
                        print(f"   ⚠️ PR list error for {repo_name}: {response.status_code}")
                        continue

                    prs = response.json()
                    for pr in prs:
                        head_ref = pr.get('head', {}).get('ref', '')
                        if numeric_part in head_ref:
                            pr_html_url = pr.get('html_url', '')
                            print(f"   ✅ Found in {repo_name}: PR #{pr.get('number')} branch '{head_ref}' contains '{numeric_part}'")
                            found.append({
                                'url': pr_html_url,
                                'title': pr.get('title', ''),
                                'status': pr.get('state', ''),
                                'source': f'GitHub (repo-listing:{repo_name})'
                            })
                            break  # Found in this repo

                except Exception as e:
                    print(f"   ⚠️ Repo listing exception ({repo_name}): {e}")
                    continue

                if found:
                    break  # Found — stop scanning repos

        except Exception as e:
            print(f"   ⚠️ Repo listing search exception: {e}")

        if not found:
            print(f"   ⏭️  Repo listing: checked repos, no match")

        return found