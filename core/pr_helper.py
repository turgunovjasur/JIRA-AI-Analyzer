"""
PRHelper - Pull Request olish va qidirish (UNIVERSAL Smart Patch)
Bu class JIRA task uchun PR topish logikasini o'z ichiga oladi.
"""

from typing import Dict, List, Optional, Callable
from utils.github.github_client import GitHubClient
from utils.github.smart_patch_helper import SmartPatchHelper, SmartPatchConfig


class PRHelper:
    """
    Pull Request olish va tahlil qilish (UNIVERSAL Smart Patch)

    Bu class 3 xil usul bilan PR topadi:
    1. JIRA'dan pr_urls field orqali
    2. GitHub'da JIRA key bo'yicha qidirish
    3. Multi-strategy (ikkalasini birlashtirish)

    YANGI: Universal Smart Patch support
    """

    def __init__(self, github_client: GitHubClient):
        """
        Initialize PR Helper

        Args:
            github_client: GitHub API client instance
        """
        self.github = github_client

    def get_pr_urls(
            self,
            task_key: str,
            task_details: Dict,
            status_callback: Optional[Callable[[str, str], None]] = None
    ) -> List[str]:
        """
        Task uchun PR URL'larni topish (simple version)

        Bu method faqat PR URL'larni qaytaradi, batafsil ma'lumot yo'q.
        Agar detail kerak bo'lsa, get_pr_full_info() ishlatiladi.

        Args:
            task_key: JIRA task key (DEV-1234)
            task_details: JIRA task details (get_task_details() dan)
            status_callback: Optional status update callback

        Returns:
            List[str]: PR URL'lar ro'yxati
        """

        def update_status(stype: str, msg: str):
            if status_callback:
                status_callback(stype, msg)

        # 1. JIRA dan PR URLs
        pr_urls = task_details.get('pr_urls', [])

        if pr_urls:
            update_status("success", f"✅ JIRA'dan {len(pr_urls)} ta PR topildi")
            return [item.get('url', '') for item in pr_urls if item.get('url')]

        # 2. GitHub'dan qidirish
        print(f"   📋 JIRA dev-status: {task_key} uchun PR topilmadi, GitHub search boshlanadi...")
        update_status("warning", "⚠️ JIRA da PR yo'q, GitHub'dan qidirilmoqda...")

        found_prs = self.github.search_pr_by_jira_key(task_key)

        if found_prs:
            urls = [item.get('url', '') for item in found_prs if item.get('url')]
            update_status("success", f"✅ GitHub'da {len(urls)} ta PR topildi")
            return urls

        print(f"   ❌ {task_key}: Barcha strategiyalar bo'yicha PR topilmadi")
        update_status("warning", "⚠️ PR topilmadi")
        return []

    def get_pr_full_info(
            self,
            task_key: str,
            task_details: Dict,
            status_callback: Optional[Callable[[str, str], None]] = None,
            use_smart_patch: bool = False
    ) -> Optional[Dict]:
        """
        PR'lar haqida TO'LIQ ma'lumot olish (UNIVERSAL Smart Patch)

        Bu method PR'larni topib, har birining batafsil ma'lumotini
        (files, additions, deletions) oladi.

        Args:
            task_key: JIRA task key
            task_details: JIRA task details
            status_callback: Optional status update callback
            use_smart_patch: Smart Patch ishlatish (default: False)

        Returns:
            Dict or None: {
                'pr_count': int,
                'files_changed': int,
                'total_additions': int,
                'total_deletions': int,
                'pr_details': List[Dict],
                'all_files': List[Dict]
            }
        """

        def update_status(stype: str, msg: str):
            if status_callback:
                status_callback(stype, msg)

        try:
            # 1. PR URL'larni olish
            pr_urls = self.get_pr_urls(task_key, task_details, status_callback)

            if not pr_urls:
                return None

            mode = "🧠 Smart Patch" if use_smart_patch else "📄 Standard"
            update_status("progress", f"📄 {len(pr_urls)} ta PR tahlil qilinmoqda ({mode})...")

            # 2. Har bir PR uchun batafsil ma'lumot
            pr_details = []
            total_files = 0
            total_additions = 0
            total_deletions = 0
            all_files = []

            for url in pr_urls:
                # URL parse qilish
                owner, repo, pr_number = self.github.parse_pr_url(url)

                if not all([owner, repo, pr_number]):
                    update_status("warning", f"⚠️ Noto'g'ri PR URL: {url}")
                    continue

                # PR info
                pr_info = self.github.get_pr_info(owner, repo, pr_number)
                if not pr_info:
                    update_status("warning", f"⚠️ PR ma'lumoti olinmadi: {url}")
                    continue

                # PR files
                pr_files = self.github.get_pr_files(owner, repo, pr_number)

                # Smart Patch - UNIVERSAL METHOD
                if use_smart_patch:
                    pr_files = self._apply_smart_patch_universal(
                        pr_files,
                        {'owner': owner, 'repo': repo}
                    )

                # Statistika
                total_files += len(pr_files)
                total_additions += pr_info.get('additions', 0)
                total_deletions += pr_info.get('deletions', 0)

                # Saqlash
                pr_details.append({
                    'url': url,
                    'owner': owner,
                    'repo': repo,
                    'number': pr_number,
                    'title': pr_info.get('title', ''),
                    'state': pr_info.get('state', ''),
                    'additions': pr_info.get('additions', 0),
                    'deletions': pr_info.get('deletions', 0),
                    'files_count': len(pr_files),
                    'files': pr_files
                })

                all_files.extend(pr_files)

            if not pr_details:
                update_status("error", "❌ Hech qanday PR tahlil qilinmadi")
                return None

            mode = "🧠 Smart Patch" if use_smart_patch else "📄 Patch"
            update_status("success",
                          f"✅ {len(pr_details)} ta PR tahlil qilindi ({mode}): "
                          f"{total_files} fayl, +{total_additions}/-{total_deletions}"
                          )

            return {
                'pr_count': len(pr_details),
                'files_changed': total_files,
                'total_additions': total_additions,
                'total_deletions': total_deletions,
                'pr_details': pr_details,
                'all_files': all_files
            }

        except Exception as e:
            update_status("error", f"❌ PR tahlil xatosi: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None

    def _apply_smart_patch_universal(
            self,
            pr_files: List[Dict],
            pr: Dict
    ) -> List[Dict]:
        """
        PR fayllariga Smart Patch qo'llash - UNIVERSAL METHOD

        Bu method SmartPatchHelper.get_file_content() ishlatadi
        (TZ-PR Service bilan bir xil!)

        Args:
            pr_files: PR files list
            pr: PR info (owner, repo)

        Returns:
            List[Dict]: Files with smart_context
        """
        enriched_files = []

        for file_data in pr_files:
            filename = file_data.get('filename', '')
            patch = file_data.get('patch', '')

            # Smart Patch qo'llash kerakmi?
            if SmartPatchConfig.should_use_smart_patch(filename, len(pr_files)):
                try:
                    # UNIVERSAL method - 3 xil usul
                    full_content = SmartPatchHelper.get_file_content(
                        pr,
                        file_data,
                        self.github.session
                    )

                    if full_content:
                        # Smart context yaratish
                        smart_context = SmartPatchHelper.extract_context(
                            filename,
                            patch,
                            full_content
                        )
                        file_data['smart_context'] = smart_context
                    else:
                        file_data['smart_context'] = None
                except Exception as e:
                    print(f"Smart Patch xatosi ({filename}): {e}")
                    file_data['smart_context'] = None
            else:
                file_data['smart_context'] = None

            enriched_files.append(file_data)

        return enriched_files

    def format_pr_summary(self, pr_info: Optional[Dict]) -> str:
        """
        PR ma'lumotini text formatga o'girish

        Args:
            pr_info: get_pr_full_info() dan qaytgan dict

        Returns:
            str: Formatlangan text summary
        """
        if not pr_info:
            return "📭 PR ma'lumoti yo'q"

        lines = [
            f"📊 PULL REQUEST TAHLILI",
            f"{'=' * 60}",
            f"PR'lar soni: {pr_info['pr_count']}",
            f"O'zgargan fayllar: {pr_info['files_changed']} ta",
            f"Qo'shilgan: +{pr_info['total_additions']} qator",
            f"O'chirilgan: -{pr_info['total_deletions']} qator",
            ""
        ]

        # Har bir PR
        if pr_info.get('pr_details'):
            lines.append("📋 PR'lar ro'yxati:")
            for i, pr in enumerate(pr_info['pr_details'], 1):
                lines.append(f"\n{i}. {pr['title']}")
                lines.append(f"   URL: {pr['url']}")
                lines.append(f"   Status: {pr['state']}")
                lines.append(f"   Fayllar: {pr['files_count']} ta")
                lines.append(f"   +{pr['additions']} / -{pr['deletions']} qator")

        return "\n".join(lines)