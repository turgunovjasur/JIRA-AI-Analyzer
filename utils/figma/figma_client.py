# utils/figma/figma_client.py
"""
Figma API Client - Production Version
Figma REST API bilan ishlash va file ma'lumotlarini olish
"""
import requests
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
        self.access_token = (access_token or "").strip()
        self.base_url = 'https://api.figma.com/v1'

        if not self.access_token:
            raise ValueError("Figma Access Token kiritilmagan.")

        self.headers = {'X-Figma-Token': self.access_token}

    @staticmethod
    def _normalize_node_id(node_id: Optional[str]) -> Optional[str]:
        """node-id formatini Figma API uchun normallashtirish."""
        if not node_id:
            return None
        return str(node_id).replace('-', ':').strip()

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

            text_snippets = self.get_text_snippets(file_key, node_id=node_id, max_items=30)
            if text_snippets:
                lines.append("")
                lines.append(f"📝 FIGMA MATNLARI ({len(text_snippets)} ta):")
                lines.append("─" * 60)
                for i, item in enumerate(text_snippets, 1):
                    frame_label = f"[Frame: {item['frame_name']}] " if item.get('frame_name') else ""
                    lines.append(f"{i}. {frame_label}{item['node_name']}: {item['text']}")
            else:
                lines.append("")
                lines.append("📝 FIGMA MATNLARI: topilmadi")

            figma_comments = self.get_file_comments(file_key, node_id=node_id, max_items=15)
            if figma_comments:
                lines.append("")
                lines.append(f"💬 FIGMA COMMENT'LAR ({len(figma_comments)} ta):")
                lines.append("─" * 60)
                for i, c in enumerate(figma_comments, 1):
                    author = c.get('author') or "Unknown"
                    lines.append(f"{i}. {author}: {c.get('message', '')}")
            else:
                lines.append("")
                lines.append("💬 FIGMA COMMENT'LAR: topilmadi")

            return "\n".join(lines)
        except Exception as e:
            return f"Figma summary error: {str(e)}"

    def _collect_text_nodes(self, node: Dict, out: List[Dict], max_items: int = 20, _frame_name: str = ""):
        """Node daraxtidan TEXT qatlamlarini yig'ish, har birida frame_name bilan."""
        if not node or len(out) >= max_items:
            return

        node_type = node.get('type', '')
        current_frame = _frame_name
        if node_type in ('FRAME', 'COMPONENT', 'INSTANCE', 'SECTION'):
            current_frame = node.get('name', '') or _frame_name

        if node_type == 'TEXT':
            raw = (node.get('characters') or '').strip()
            if raw:
                cleaned = re.sub(r'\s+', ' ', raw).strip()
                if cleaned:
                    out.append({
                        'node_id': node.get('id', ''),
                        'node_name': node.get('name', 'Text'),
                        'node_type': node_type,
                        'frame_name': current_frame,
                        'text': cleaned[:500]
                    })
                    if len(out) >= max_items:
                        return

        for child in (node.get('children') or []):
            self._collect_text_nodes(child, out, max_items=max_items, _frame_name=current_frame)
            if len(out) >= max_items:
                return

    def get_text_snippets(self, file_key: str, node_id: str = None, max_items: int = 20) -> List[Dict]:
        """
        Figma'dan o'qiladigan text layer'larni qaytaradi.
        node_id berilsa aynan shu node subtree o'qiladi.
        """
        normalized = self._normalize_node_id(node_id)
        try:
            collected: List[Dict] = []
            if normalized:
                url = f"{self.base_url}/files/{file_key}/nodes"
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=20,
                    params={'ids': normalized, 'depth': 12}
                )
                if response.status_code != 200:
                    return []
                payload = response.json()
                node_info = (payload.get('nodes') or {}).get(normalized) or {}
                document = node_info.get('document') or {}
                self._collect_text_nodes(document, collected, max_items=max_items)
            else:
                # node-id bo'lmasa, faylning o'rtacha chuqurlikdagi daraxtidan text yig'amiz
                url = f"{self.base_url}/files/{file_key}"
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=25,
                    params={'depth': 5}
                )
                if response.status_code != 200:
                    return []
                payload = response.json()
                document = payload.get('document') or {}
                self._collect_text_nodes(document, collected, max_items=max_items)

            # Dublikatsiyalarni qisqartirish
            unique = []
            seen = set()
            for item in collected:
                key = item.get('text', '')
                if not key or key in seen:
                    continue
                seen.add(key)
                unique.append(item)
                if len(unique) >= max_items:
                    break
            return unique
        except Exception:
            return []

    def _get_node_subtree_ids(self, file_key: str, node_id: str) -> set:
        """node_id subtree'sindagi barcha node ID'larini qaytarish (comment filter uchun)."""
        normalized = self._normalize_node_id(node_id)
        if not normalized:
            return set()
        ids: set = {normalized}
        try:
            url = f"{self.base_url}/files/{file_key}/nodes"
            response = requests.get(
                url, headers=self.headers, timeout=15,
                params={'ids': normalized, 'depth': 8}
            )
            if response.status_code != 200:
                return ids
            payload = response.json()
            node_info = (payload.get('nodes') or {}).get(normalized) or {}
            document = node_info.get('document') or {}
            self._collect_node_ids(document, ids)
        except Exception:
            pass
        return ids

    def _collect_node_ids(self, node: Dict, out: set) -> None:
        nid = node.get('id') or ''
        if nid:
            out.add(nid.replace('-', ':'))
        for child in (node.get('children') or []):
            self._collect_node_ids(child, out)

    def get_file_comments(self, file_key: str, node_id: str = None, max_items: int = 15) -> List[Dict]:
        """
        Figma file comment'larini qaytaradi.
        node_id berilsa, FAQAT shu node subtree'siga anchored comment'lar qaytariladi.
        Subtree'dan tashqaridagi comment'lar to'liq o'tkazib yuboriladi (fallback yo'q).
        """
        normalized = self._normalize_node_id(node_id)
        try:
            url = f"{self.base_url}/files/{file_key}/comments"
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code != 200:
                return []

            payload = response.json()
            comments = payload.get('comments') or []
            parsed = []
            for c in comments:
                message = re.sub(r'\s+', ' ', str(c.get('message') or '')).strip()
                if not message:
                    continue
                client_meta = c.get('client_meta') or {}
                cid = str(client_meta.get('node_id') or '').replace('-', ':')
                parsed.append({
                    'id': c.get('id'),
                    'author': (c.get('user') or {}).get('handle') or (c.get('user') or {}).get('name') or 'Unknown',
                    'created_at': c.get('created_at'),
                    'node_id': cid,
                    'message': message[:500],
                })

            if normalized:
                subtree_ids = self._get_node_subtree_ids(file_key, normalized)
                node_related = [c for c in parsed if c.get('node_id') in subtree_ids]
                if not node_related:
                    _log.info(f"Figma: node_id={normalized} uchun subtree'ga anchored comment topilmadi, barchasi o'tkazildi.")
                return node_related[:max_items]

            return parsed[:max_items]
        except Exception:
            return []

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
