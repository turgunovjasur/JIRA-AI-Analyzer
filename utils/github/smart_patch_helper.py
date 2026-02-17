# utils/smart_patch_helper.py
"""
Smart Patch Analyzer - UNIVERSAL VERSION
Faqat ishlaydigan, oddiy yechim + File Content Fetcher

Author: JASUR TURGUNOV
Version: 4.0 - UNIVERSAL
"""

import re
import base64
import requests
from typing import Dict, List, Optional


class SmartPatchHelper:
    """Smart Patch - Oddiy va ishonchli (with File Fetcher)"""

    @staticmethod
    def extract_context(filename: str, patch: str, full_file_content: str) -> str:
        """
        Smart context extract

        ODDIY YONDASHUV:
        - Patch'dan funksiya nomlarini to'g'ridan-to'g'ri topamiz
        - Full file'dan signature'ni topamiz
        """
        if not patch or not full_file_content:
            return f"```diff\n{patch}\n```"

        # Language detection
        lang = SmartPatchHelper._detect_language(filename)

        if lang == 'unsupported':
            return f"```diff\n{patch}\n```"

        # Patch'dan funksiya nomlarini topish (ODDIY!)
        function_names = SmartPatchHelper._extract_function_names_from_patch(patch, lang)

        if not function_names:
            return f"```diff\n{patch}\n```"

        # Full file'dan signature topish
        functions = SmartPatchHelper._find_function_signatures(
            full_file_content,
            function_names,
            lang
        )

        # Format
        output = []

        if functions:
            output.append("**📦 Affected Functions:**")
            for func in functions[:3]:
                output.append(f"- `{func['name']}` (line {func['line']})")
                if func.get('signature'):
                    lang_label = SmartPatchHelper._get_language_label(lang)
                    output.append(f"  ```{lang_label}\n  {func['signature']}\n  ```")
            output.append("")

        # Count additions
        additions = len([l for l in patch.split('\n') if l.startswith('+') and not l.startswith('+++')])
        output.append(f"**Changes:** +{additions} lines")
        output.append(f"```diff\n{patch}\n```")

        return '\n'.join(output)

    @staticmethod
    def _detect_language(filename: str) -> str:
        """Fayl tilini aniqlash"""
        ext = filename.split('.')[-1].lower() if '.' in filename else ''

        lang_map = {
            'py': 'python',
            'js': 'javascript',
            'jsx': 'javascript',
            'ts': 'typescript',
            'tsx': 'typescript',
            'html': 'html',
            'htm': 'html',
            'sql': 'sql',
            'pck': 'plsql',
        }

        return lang_map.get(ext, 'unsupported')

    @staticmethod
    def _get_language_label(lang: str) -> str:
        """Language label"""
        labels = {
            'python': 'python',
            'javascript': 'javascript',
            'typescript': 'typescript',
            'html': 'javascript',
            'sql': 'sql',
            'plsql': 'sql',
        }
        return labels.get(lang, 'text')

    @staticmethod
    def _extract_function_names_from_patch(patch: str, lang: str) -> List[str]:
        """
        ODDIY: Patch'dan funksiya nomlarini to'g'ridan-to'g'ri topish

        Bu eng oddiy va ishonchli usul!
        """
        function_names = []

        # Language-specific patterns
        if lang in ['python']:
            # def function_name(
            pattern = r'def\s+(\w+)\s*\('
        elif lang in ['javascript', 'typescript', 'html']:
            # function functionName(
            pattern = r'function\s+(\w+)\s*\('
        elif lang in ['sql', 'plsql']:
            # PROCEDURE procedure_name(
            # FUNCTION function_name(
            pattern = r'(?:PROCEDURE|FUNCTION)\s+(\w+)\s*\('
        else:
            return []

        # Patch'dan qidirish
        for line in patch.split('\n'):
            # Faqat context va added lines'dan qidirish
            if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
                continue

            matches = re.findall(pattern, line, re.IGNORECASE)
            function_names.extend(matches)

        # Unique names
        return list(set(function_names))

    @staticmethod
    def _find_function_signatures(file_content: str, function_names: List[str], lang: str) -> List[Dict]:
        """
        Full file'dan funksiya signature'larini topish
        """
        functions = []

        # Build pattern based on language
        if lang == 'python':
            pattern_template = r'^(\s*)(async\s+)?def\s+{}\s*\((.*?)\)(\s*->\s*[\w\[\], ]+)?:'
        elif lang in ['javascript', 'typescript', 'html']:
            pattern_template = r'^\s*(async\s+)?function\s+{}\s*\((.*?)\)'
        elif lang in ['sql', 'plsql']:
            pattern_template = r'^\s*(?:CREATE\s+OR\s+REPLACE\s+)?(?:PROCEDURE|FUNCTION)\s+{}\s*\((.*?)\)'
        else:
            return []

        lines = file_content.split('\n')

        for func_name in function_names:
            pattern = pattern_template.format(re.escape(func_name))

            for i, line in enumerate(lines, start=1):
                if re.search(pattern, line, re.IGNORECASE):
                    functions.append({
                        'name': func_name,
                        'signature': line.strip(),
                        'line': i
                    })
                    break  # Found, next function

        return functions

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FILE CONTENT FETCHER - UNIVERSAL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @staticmethod
    def get_file_content(
            pr: Dict,
            file_data: Dict,
            github_session: requests.Session
    ) -> Optional[str]:
        """
        GitHub dan fayl kontentini olish - UNIVERSAL

        3 xil usul (priority order):
        1. contents_url (most reliable)
        2. blob API (fallback)
        3. raw_url (public repos)

        Args:
            pr: PR ma'lumotlari (owner, repo)
            file_data: File ma'lumotlari (sha, contents_url, raw_url)
            github_session: GitHub API session (headers bilan)

        Returns:
            str: File content yoki None
        """
        methods = [
            lambda: SmartPatchHelper._try_contents_url(file_data, github_session),
            lambda: SmartPatchHelper._try_blob_api(pr, file_data, github_session),
            lambda: SmartPatchHelper._try_raw_url(file_data, github_session)
        ]

        for method in methods:
            try:
                content = method()
                if content:
                    return content
            except Exception as e:
                # Silent fail, try next method
                continue

        return None

    @staticmethod
    def _try_contents_url(file_data: Dict, session: requests.Session) -> Optional[str]:
        """Method 1: Contents URL (most reliable)"""
        contents_url = file_data.get('contents_url')

        if not contents_url:
            return None

        # Get timeout from settings
        try:
            from config.app_settings import get_app_settings
            timeout = get_app_settings(force_reload=False).queue.http_timeout
        except Exception:
            timeout = 30  # Default fallback

        response = session.get(contents_url, timeout=timeout)

        if response.status_code == 200:
            content_data = response.json()

            if 'content' in content_data:
                content_b64 = content_data['content']
                content_bytes = base64.b64decode(content_b64)
                return content_bytes.decode('utf-8', errors='ignore')

        return None

    @staticmethod
    def _try_blob_api(pr: Dict, file_data: Dict, session: requests.Session) -> Optional[str]:
        """Method 2: Blob API (fallback)"""
        file_sha = file_data.get('sha')
        owner = pr.get('owner')
        repo = pr.get('repo')

        if not (file_sha and owner and repo):
            return None

        # Get timeout from settings
        try:
            from config.app_settings import get_app_settings
            timeout = get_app_settings(force_reload=False).queue.http_timeout
        except Exception:
            timeout = 30  # Default fallback

        blob_url = f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{file_sha}"
        response = session.get(blob_url, timeout=timeout)

        if response.status_code == 200:
            blob_data = response.json()

            if blob_data.get('encoding') == 'base64':
                content_b64 = blob_data.get('content', '')
                content_bytes = base64.b64decode(content_b64)
                return content_bytes.decode('utf-8', errors='ignore')

        return None

    @staticmethod
    def _try_raw_url(file_data: Dict, session: requests.Session) -> Optional[str]:
        """Method 3: Raw URL (public repos)"""
        raw_url = file_data.get('raw_url')

        if not raw_url:
            return None

        # Get timeout from settings
        try:
            from config.app_settings import get_app_settings
            timeout = get_app_settings(force_reload=False).queue.http_timeout
        except Exception:
            timeout = 30  # Default fallback

        response = session.get(raw_url, timeout=timeout)

        if response.status_code == 200:
            return response.text

        return None


class SmartPatchConfig:
    """Smart Patch konfiguratsiya"""

    SUPPORTED_EXTENSIONS = {
        '.py', '.js', '.jsx', '.ts', '.tsx',
        '.html', '.htm',
        '.sql', '.pck'
    }

    MAX_FUNCTIONS_PER_FILE = 10
    MAX_SMART_FILES = 100

    @staticmethod
    def should_use_smart_patch(filename: str, file_count: int) -> bool:
        """Smart patch ishlatish kerakmi?"""
        ext = '.' + filename.split('.')[-1] if '.' in filename else ''
        if ext not in SmartPatchConfig.SUPPORTED_EXTENSIONS:
            return False

        if file_count > SmartPatchConfig.MAX_SMART_FILES:
            return False

        return True