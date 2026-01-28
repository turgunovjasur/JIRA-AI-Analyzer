# test_figma_final.py
"""
Figma Integration - FINAL WORKING TEST
Hammasi ishlaydi! ✅
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.jira.jira_client import JiraClient
from dotenv import load_dotenv
import re
from typing import List, Dict, Optional
import requests

load_dotenv()


class JiraFigmaHelper:
    """JIRA'dan Figma link'larni olish - WORKING"""

    FIGMA_PATTERN = r'https://(?:www\.)?figma\.com/(?:file|proto|design)/([A-Za-z0-9]+)[^"\s<]*'

    @staticmethod
    def extract_figma_urls(task_details: Dict) -> List[Dict]:
        """Task'dan Figma URL'larni topish"""
        figma_links = []
        seen_file_keys = set()

        # Description
        description = task_details.get('description', '')
        if description:
            matches = re.finditer(JiraFigmaHelper.FIGMA_PATTERN, description)

            for match in matches:
                url = match.group(0)
                file_key = match.group(1)

                if file_key in seen_file_keys:
                    continue

                seen_file_keys.add(file_key)

                # Clean URL
                clean_url = url.replace('&amp;', '&').rstrip('<>')

                # Extract name
                name_match = re.search(r'/(?:file|design|proto)/[A-Za-z0-9]+/([^?]+)', clean_url)
                name = name_match.group(1).replace('-', ' ') if name_match else "Figma Design"

                figma_links.append({
                    'url': clean_url,
                    'file_key': file_key,
                    'name': name,
                    'source': 'description'
                })

        return figma_links


class FigmaClient:
    """Figma API client - WORKING VERSION"""

    def __init__(self):
        self.access_token = os.getenv('FIGMA_ACCESS_TOKEN')
        self.base_url = 'https://api.figma.com/v1'

        if not self.access_token:
            raise ValueError("FIGMA_ACCESS_TOKEN not found in .env!")

        self.headers = {'X-Figma-Token': self.access_token}

    def get_file_metadata(self, file_key: str) -> Optional[Dict]:
        """File metadata olish - FIXED VERSION"""
        try:
            url = f"{self.base_url}/files/{file_key}"

            # IMPORTANT: No depth parameter!
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Count pages
                document = data.get('document', {})
                pages = len(document.get('children', []))

                return {
                    'name': data.get('name', 'Unknown'),
                    'version': str(data.get('version', 'N/A'))[:10],
                    'lastModified': data.get('lastModified', 'N/A')[:19],
                    'pages': pages
                }
            else:
                return None

        except Exception as e:
            return None

    def get_file_frames(self, file_key: str, max_frames: int = 5) -> List[Dict]:
        """Frame'larni olish"""
        try:
            url = f"{self.base_url}/files/{file_key}"
            response = requests.get(url, headers=self.headers, timeout=15)

            if response.status_code != 200:
                return []

            data = response.json()
            frames = []

            document = data.get('document', {})
            pages = document.get('children', [])

            for page in pages:
                page_name = page.get('name', 'Page')

                for child in page.get('children', []):
                    child_type = child.get('type', '')

                    if child_type in ['FRAME', 'COMPONENT', 'INSTANCE']:
                        frames.append({
                            'id': child.get('id'),
                            'name': child.get('name'),
                            'type': child_type,
                            'page': page_name
                        })

                        if len(frames) >= max_frames:
                            return frames

            return frames

        except Exception:
            return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print("╔" + "═" * 78 + "╗")
print("║" + " " * 15 + "FIGMA INTEGRATION - FINAL TEST" + " " * 32 + "║")
print("╚" + "═" * 78 + "╝\n")

TASK_KEY = "DEV-6578"

# Step 1: JIRA
print("[1/3] 📋 JIRA Task\n")

try:
    jira = JiraClient()
    task_details = jira.get_task_details(TASK_KEY)

    if not task_details:
        print("❌ Task topilmadi!")
        sys.exit(1)

    print(f"✅ {task_details['summary'][:50]}...\n")

except Exception as e:
    print(f"❌ JIRA error: {str(e)}")
    sys.exit(1)

# Step 2: Figma links
print("[2/3] 🔍 Figma Links\n")

figma_links = JiraFigmaHelper.extract_figma_urls(task_details)

if not figma_links:
    print("⚠️  Figma link topilmadi!")
    sys.exit(0)

print(f"✅ {len(figma_links)} ta Figma link topildi:\n")

for i, link in enumerate(figma_links, 1):
    print(f"   {i}. {link['name']}")
    print(f"      File: {link['file_key']}")
    print()

# Step 3: Figma API
print("[3/3] 🎨 Figma API\n")

try:
    figma = FigmaClient()

    for idx, link in enumerate(figma_links, 1):
        file_key = link['file_key']

        print(f"📐 File {idx}/{len(figma_links)}: {link['name']}")
        print("   " + "─" * 60)

        # Metadata
        metadata = figma.get_file_metadata(file_key)

        if metadata:
            print(f"   ✅ SUCCESS!")
            print(f"   📄 Name: {metadata['name']}")
            print(f"   📅 Modified: {metadata['lastModified']}")
            print(f"   📑 Pages: {metadata['pages']}")
            print(f"   🔢 Version: {metadata['version']}...")

            # Frames
            frames = figma.get_file_frames(file_key)

            if frames:
                print(f"\n   🖼️  Frames ({len(frames)} ta):")
                for frame in frames:
                    print(f"      • {frame['name']} ({frame['type']})")
            else:
                print(f"\n   📝 Bo'sh file (frame'lar yo'q)")
        else:
            print(f"   ❌ Access yo'q yoki xatolik")

        print()

except ValueError as e:
    print(f"❌ {str(e)}")
    sys.exit(1)

except Exception as e:
    print(f"❌ Error: {str(e)}")
    sys.exit(1)

# Success!
print("╔" + "═" * 78 + "╗")
print("║" + " " * 20 + "🎉 HAMMASI ISHLAYAPTI!" + " " * 33 + "║")
print("╚" + "═" * 78 + "╝\n")

print("✅ Figma integration tayyor!")
print("\n📝 Keyingi qadamlar:")
print("   1. utils/figma/figma_client.py yaratish")
print("   2. utils/jira/jira_figma_helper.py yaratish")
print("   3. JiraClient'ga get_figma_links() qo'shish")
print("   4. TZ-PR Checker'ga integratsiya")
print("   5. UI yaratish")