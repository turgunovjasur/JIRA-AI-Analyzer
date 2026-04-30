# utils/figma/figma_client.py
"""
Figma API Client - Production Version
Figma REST API bilan ishlash va file ma'lumotlarini olish
"""
import requests
import os
from typing import Dict, List, Optional
import re
from dataclasses import dataclass
from core.logger import get_logger

_log = get_logger("figma.client")


@dataclass
class FigmaFrame:
    """Figma frame ma'lumotlari"""
    id: str
    name: str
    type: str
    page: str
    width: float = 0
    height: float = 0
    children_count: int = 0


class FigmaClient:
    """Figma REST API Client"""

    def __init__(self, access_token: Optional[str] = None):
        """Initialize Figma client"""
        self.access_token = access_token or os.getenv('FIGMA_ACCESS_TOKEN')
        self.base_url = 'https://api.figma.com/v1'

        if not self.access_token:
            raise ValueError("FIGMA_ACCESS_TOKEN not found in .env!")

        self.headers = {'X-Figma-Token': self.access_token}

    def get_file_metadata(self, file_key: str) -> Optional[Dict]:
        """Get file metadata (depth=1 — sahifa tuzilmasi, to'liq fayl yuklanmaydi)."""
        try:
            url = f"{self.base_url}/files/{file_key}"
            response = requests.get(url, headers=self.headers, timeout=15, params={'depth': 1})

            if response.status_code == 200:
                data = response.json()
                document = data.get('document', {})
                pages = len(document.get('children', []))

                return {
                    'name': data.get('name', 'Unknown'),
                    'version': str(data.get('version', 'N/A'))[:15],
                    'lastModified': data.get('lastModified', 'N/A')[:19],
                    'pages': pages,
                    'thumbnailUrl': data.get('thumbnailUrl'),
                    'editorType': data.get('editorType', 'figma')
                }
            return None
        except Exception:
            return None

    def get_file_frames(self, file_key: str, max_frames: int = 20, node_id: str = None) -> List[FigmaFrame]:
        """Get frames from file.

        depth=2: document → pages → frames (to'liq fayl yuklanmaydi).
        node_id berilsa — faqat shu node'ning page'si o'qiladi (qolgan page'lar o'tkaziladi).
        node_id berilmasa — barcha page'lardan ketma-ket frame'lar olinadi.
        """
        try:
            url = f"{self.base_url}/files/{file_key}"
            response = requests.get(url, headers=self.headers, timeout=20, params={'depth': 2})

            if response.status_code != 200:
                return []

            data = response.json()
            frames = []

            document = data.get('document', {})
            pages = document.get('children', [])

            # node_id berilgan bo'lsa, shu node qaysi page'da ekanini aniqlash
            target_page_name = None
            if node_id:
                target_page_name = self._find_page_for_node(pages, node_id)

            for page in pages:
                page_name = page.get('name', 'Page')

                # Faqat target page ni o'qi (agar node_id bilan aniqlangan bo'lsa)
                if target_page_name and page_name != target_page_name:
                    continue

                for child in page.get('children', []):
                    child_type = child.get('type', '')

                    if child_type in ['FRAME', 'COMPONENT', 'INSTANCE', 'SECTION']:
                        bounds = child.get('absoluteBoundingBox', {})

                        frame = FigmaFrame(
                            id=child.get('id', 'N/A'),
                            name=child.get('name', 'Unnamed'),
                            type=child_type,
                            page=page_name,
                            width=bounds.get('width', 0),
                            height=bounds.get('height', 0),
                            children_count=len(child.get('children', []))
                        )

                        frames.append(frame)

                        if len(frames) >= max_frames:
                            return frames

            return frames
        except Exception:
            return []

    def _find_page_for_node(self, pages: list, node_id: str) -> str | None:
        """node_id qaysi page'ga tegishli ekanini aniqlash.

        node_id formati: "1337:16" yoki "1337-16"
        Figma fayl tuzilmasida node ID'lar page children ichida joylashgan.
        """
        normalized = node_id.replace('-', ':')
        for page in pages:
            for child in page.get('children', []):
                child_id = child.get('id', '').replace('-', ':')
                if child_id == normalized:
                    return page.get('name', '')
                # Ba'zan node nested bo'ladi — ID prefixi page'ga tegishli
                # Figma node ID formatida birinchi raqam page'ga yo'naltiradi
            # Fallback: node ID'ning birinchi qismi page'dagi biror element bilan mos kelsa
            page_id = page.get('id', '')
            if normalized.startswith(page_id.split(':')[0] + ':'):
                return page.get('name', '')
        return None

    def get_file_summary(self, file_key: str, node_id: str = None) -> str:
        """Get AI-friendly summary.

        node_id berilsa — faqat shu node'ning sahifasidagi frame'lar ko'rsatiladi.
        """
        try:
            metadata = self.get_file_metadata(file_key)
            if not metadata:
                return "Figma file'ga access yo'q"

            frames = self.get_file_frames(file_key, max_frames=15, node_id=node_id)

            lines = [
                f"📐 FIGMA: {metadata['name']}",
                f"📅 Modified: {metadata['lastModified'][:10]}",
                f"📑 Pages: {metadata['pages']}",
                ""
            ]

            if frames:
                page_note = f" [{frames[0].page} sahifasidan]" if node_id and frames else ""
                lines.append(f"🖼️  FRAME'LAR ({len(frames)} ta){page_note}:")
                lines.append("─" * 60)

                for i, frame in enumerate(frames, 1):
                    lines.append(f"{i}. {frame.name} ({frame.type})")
                    lines.append(f"   Size: {frame.width:.0f}x{frame.height:.0f}, Elements: {frame.children_count}")

                if len(frames) >= 15:
                    lines.append("   ... (va boshqa frame'lar)")
            else:
                lines.append("⚠️  Frame'lar topilmadi")

            return "\n".join(lines)
        except Exception as e:
            return f"Figma summary error: {str(e)}"

    @staticmethod
    def find_working_token(tokens: list, file_key: str) -> Optional[str]:
        """
        Berilgan tokenlar ro'yxatidan file_key ga 200 qaytaradigan birinchi tokenni topish.
        Topilmasa None qaytaradi.
        """
        _log.info(f"Figma: {len(tokens)} ta token tekshirilmoqda | file_key={file_key}")
        for i, entry in enumerate(tokens):
            token = (entry.get('token') or '').strip()
            name = entry.get('name') or f"token_{i+1}"
            if not token:
                _log.warning(f"Figma: [{name}] token bo'sh, o'tkazib yuborildi")
                continue
            token_preview = f"...{token[-6:]}" if len(token) > 6 else token
            try:
                resp = requests.get(
                    f"https://api.figma.com/v1/files/{file_key}",
                    headers={'X-Figma-Token': token},
                    timeout=8,
                    params={'depth': 1}
                )
                _log.info(f"Figma: [{name}] ({token_preview}) → HTTP {resp.status_code}")
                if resp.status_code == 200:
                    _log.info(f"Figma: [{name}] ishlaydi, ishlatilmoqda")
                    return token
                elif resp.status_code == 403:
                    _log.warning(f"Figma: [{name}] ruxsat yo'q (403) — token noto'g'ri yoki muddati o'tgan")
                elif resp.status_code == 404:
                    _log.warning(f"Figma: [{name}] fayl topilmadi (404) — file_key={file_key}")
                else:
                    _log.warning(f"Figma: [{name}] rad etildi (HTTP {resp.status_code})")
            except Exception as e:
                _log.warning(f"Figma: [{name}] so'rov xatosi: {e}")
                continue
        _log.warning(f"Figma: Hech qaysi token ishlamadi | file_key={file_key} | jami={len(tokens)} ta")
        return None

    @staticmethod
    def parse_figma_url(url: str) -> Optional[Dict]:
        """Parse Figma URL"""
        file_key_match = re.search(r'/(?:file|design|proto)/([A-Za-z0-9]+)', url)

        if not file_key_match:
            return None

        file_key = file_key_match.group(1)

        node_id = None
        node_match = re.search(r'node-id=([^&\s]+)', url)
        if node_match:
            node_id = node_match.group(1).replace('-', ':')

        return {'file_key': file_key, 'node_id': node_id}