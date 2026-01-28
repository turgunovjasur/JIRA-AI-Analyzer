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
        """Get file metadata"""
        try:
            url = f"{self.base_url}/files/{file_key}"
            response = requests.get(url, headers=self.headers, timeout=15)

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

    def get_file_frames(self, file_key: str, max_frames: int = 20) -> List[FigmaFrame]:
        """Get frames from file"""
        try:
            url = f"{self.base_url}/files/{file_key}"
            response = requests.get(url, headers=self.headers, timeout=20)

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

    def get_file_summary(self, file_key: str) -> str:
        """Get AI-friendly summary"""
        try:
            metadata = self.get_file_metadata(file_key)
            if not metadata:
                return "Figma file'ga access yo'q"

            frames = self.get_file_frames(file_key, max_frames=15)

            lines = [
                f"📐 FIGMA: {metadata['name']}",
                f"📅 Modified: {metadata['lastModified'][:10]}",
                f"📑 Pages: {metadata['pages']}",
                ""
            ]

            if frames:
                lines.append(f"🖼️  FRAME'LAR ({len(frames)} ta):")
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