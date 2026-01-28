# figma_inspector.py
"""
Figma Full Inspector - AI nimalarni ko'radi?

Bu script Figma file'dan BARCHA ma'lumotlarni chiqaradi:
- File metadata
- Har bir page
- Har bir frame/component
- Frame ichidagi elementlar (text, rectangle, etc.)
- AI'ga yuborilgan prompt ko'rinishi
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from dotenv import load_dotenv
import json

load_dotenv()

FIGMA_TOKEN = os.getenv('FIGMA_ACCESS_TOKEN')
FILE_KEY = 'QCD8ZfGx0zOMvEV9nvk3zC'  # Sizning "Untitled" file

print("╔" + "═" * 80 + "╗")
print("║" + " " * 25 + "FIGMA FULL INSPECTOR" + " " * 35 + "║")
print("╚" + "═" * 80 + "╝\n")

print(f"📐 File Key: {FILE_KEY}")
print(f"🔍 Token: {FIGMA_TOKEN[:15]}...\n")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GET FULL FILE DATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

url = f"https://api.figma.com/v1/files/{FILE_KEY}"
headers = {'X-Figma-Token': FIGMA_TOKEN}

print("📡 Figma API dan to'liq ma'lumot olinmoqda...\n")

try:
    response = requests.get(url, headers=headers, timeout=15)

    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        sys.exit(1)

    data = response.json()

except Exception as e:
    print(f"❌ Error: {str(e)}")
    sys.exit(1)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 1: FILE METADATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print("=" * 80)
print("📄 FILE METADATA")
print("=" * 80)

print(f"\n✅ Name: {data.get('name', 'N/A')}")
print(f"✅ Version: {data.get('version', 'N/A')}")
print(f"✅ Last Modified: {data.get('lastModified', 'N/A')[:19]}")
print(f"✅ Editor Type: {data.get('editorType', 'N/A')}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 2: DOCUMENT STRUCTURE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print("\n" + "=" * 80)
print("📋 DOCUMENT STRUCTURE")
print("=" * 80)

document = data.get('document', {})
pages = document.get('children', [])

print(f"\n✅ Pages: {len(pages)}\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 3: DETAILED PAGE/FRAME ANALYSIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def analyze_node(node, indent=0):
    """Node'ni recursive tahlil qilish"""
    prefix = "  " * indent

    node_type = node.get('type', 'UNKNOWN')
    node_name = node.get('name', 'Unnamed')
    node_id = node.get('id', 'N/A')

    # Icon based on type
    icons = {
        'CANVAS': '📄',
        'FRAME': '🖼️',
        'COMPONENT': '🧩',
        'INSTANCE': '📦',
        'TEXT': '📝',
        'RECTANGLE': '▭',
        'ELLIPSE': '⭕',
        'VECTOR': '✏️',
        'GROUP': '📁',
        'BOOLEAN_OPERATION': '🔀',
        'LINE': '━',
        'IMAGE': '🖼️'
    }

    icon = icons.get(node_type, '•')

    print(f"{prefix}{icon} {node_type}: {node_name}")
    print(f"{prefix}   ID: {node_id}")

    # Additional info based on type
    if node_type == 'TEXT':
        characters = node.get('characters', '')
        if characters:
            # Truncate long text
            text_preview = characters[:50] + "..." if len(characters) > 50 else characters
            print(f"{prefix}   Text: '{text_preview}'")

    if node_type == 'FRAME':
        bounds = node.get('absoluteBoundingBox', {})
        if bounds:
            width = bounds.get('width', 0)
            height = bounds.get('height', 0)
            print(f"{prefix}   Size: {width:.0f} x {height:.0f}")

    # Background color
    if 'fills' in node and node['fills']:
        for fill in node['fills']:
            if fill.get('type') == 'SOLID':
                color = fill.get('color', {})
                r = int(color.get('r', 0) * 255)
                g = int(color.get('g', 0) * 255)
                b = int(color.get('b', 0) * 255)
                print(f"{prefix}   Color: RGB({r}, {g}, {b})")

    # Recursive children
    children = node.get('children', [])
    if children and indent < 3:  # Limit depth to 3
        print(f"{prefix}   Children: {len(children)}")
        for child in children[:10]:  # Max 10 children
            analyze_node(child, indent + 1)

        if len(children) > 10:
            print(f"{prefix}   ... and {len(children) - 10} more children")


print("=" * 80)
print("🔍 DETAILED STRUCTURE (AI'ga yuboriladi)")
print("=" * 80)

for page_idx, page in enumerate(pages, 1):
    print(f"\n{'━' * 80}")
    print(f"📄 PAGE {page_idx}: {page.get('name', 'Unnamed')}")
    print(f"{'━' * 80}\n")

    analyze_node(page, indent=0)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 4: AI PROMPT SIMULATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print("\n" + "=" * 80)
print("🤖 AI'GA YUBORILGAN PROMPT (Simulation)")
print("=" * 80)

# Collect all frames and their info
all_frames = []

for page in pages:
    page_name = page.get('name', 'Page')

    for child in page.get('children', []):
        if child.get('type') in ['FRAME', 'COMPONENT', 'INSTANCE']:
            frame_info = {
                'name': child.get('name', 'Unnamed'),
                'type': child.get('type'),
                'page': page_name,
                'id': child.get('id'),
                'children_count': len(child.get('children', []))
            }

            # Count element types
            element_types = {}
            for element in child.get('children', []):
                elem_type = element.get('type', 'UNKNOWN')
                element_types[elem_type] = element_types.get(elem_type, 0) + 1

            frame_info['elements'] = element_types
            all_frames.append(frame_info)

# Create AI prompt
prompt = f"""
╔══════════════════════════════════════════════════════════════════╗
║ 🎯 FIGMA DIZAYN TAHLILI                                          ║
╚══════════════════════════════════════════════════════════════════╝

📐 FILE: {data.get('name', 'Unknown')}
📅 Last Modified: {data.get('lastModified', 'N/A')[:19]}
📑 Pages: {len(pages)}

─────────────────────────────────────────────────────────────────────
🖼️  FRAME'LAR VA UI ELEMENTLAR
─────────────────────────────────────────────────────────────────────

"""

for i, frame in enumerate(all_frames, 1):
    prompt += f"\n{i}. {frame['name']} ({frame['type']})\n"
    prompt += f"   Page: {frame['page']}\n"
    prompt += f"   ID: {frame['id']}\n"
    prompt += f"   Children: {frame['children_count']} ta element\n"

    if frame['elements']:
        prompt += f"   Elements:\n"
        for elem_type, count in frame['elements'].items():
            prompt += f"      • {elem_type}: {count} ta\n"

prompt += """

─────────────────────────────────────────────────────────────────────
📝 AI TASK
─────────────────────────────────────────────────────────────────────

Bu Figma dizaynga asoslanib:
1. Qaysi UI componentlar mavjud?
2. Layout struktura qanday?
3. Kod bilan moslik bormi?
4. Qaysi elementlar implement qilingan?

"""

print(prompt)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 5: STATISTICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print("\n" + "=" * 80)
print("📊 STATISTIKA")
print("=" * 80)

# Count all element types
all_element_types = {}


def count_elements(node):
    """Recursive element counting"""
    node_type = node.get('type', 'UNKNOWN')
    all_element_types[node_type] = all_element_types.get(node_type, 0) + 1

    for child in node.get('children', []):
        count_elements(child)


for page in pages:
    count_elements(page)

print(f"\n✅ Jami element turlari:\n")
for elem_type, count in sorted(all_element_types.items(), key=lambda x: x[1], reverse=True):
    print(f"   {elem_type:20s}: {count:3d} ta")

# Total prompt size
prompt_size = len(prompt)
print(f"\n✅ AI prompt size: {prompt_size:,} characters")
print(f"✅ Tokens (approx): {prompt_size // 4:,}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 6: SAVE TO FILE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

print("\n" + "=" * 80)
print("💾 SAVE TO FILE")
print("=" * 80)

# Save full JSON
json_file = f"figma_full_data_{FILE_KEY}.json"
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\n✅ Full JSON saved: {json_file}")

# Save prompt
prompt_file = f"figma_ai_prompt_{FILE_KEY}.txt"
with open(prompt_file, 'w', encoding='utf-8') as f:
    f.write(prompt)

print(f"✅ AI Prompt saved: {prompt_file}")

# Save structure
structure_file = f"figma_structure_{FILE_KEY}.txt"
with open(structure_file, 'w', encoding='utf-8') as f:
    import sys
    from io import StringIO

    # Capture printed output
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    for page_idx, page in enumerate(pages, 1):
        print(f"\n{'━' * 80}")
        print(f"PAGE {page_idx}: {page.get('name', 'Unnamed')}")
        print(f"{'━' * 80}\n")
        analyze_node(page, indent=0)

    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    f.write(output)

print(f"✅ Structure saved: {structure_file}")

print("\n" + "=" * 80)
print("✅ TAYYOR!")
print("=" * 80)

print(f"""
📂 3 ta fayl yaratildi:

1. {json_file}
   → To'liq Figma JSON data (debug uchun)

2. {prompt_file}
   → AI'ga yuborilgan prompt (tahlil uchun)

3. {structure_file}
   → Figma structure (o'qish uchun)

💡 Bu fayllarni ochib ko'ring - AI aynan shu ma'lumotlarni ko'radi!
""")