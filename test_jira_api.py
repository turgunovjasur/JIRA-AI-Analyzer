# test_jira_api.py - TO'G'RILANGAN VERSIYA
"""
JIRA API Test - Figma link'larni qidirish
"""
from utils.jira.jira_client import JiraClient  # ← TO'G'RI IMPORT!
import re

# JIRA client yaratish
jira = JiraClient()

# Test task key
TASK_KEY = 'DEV-6578'  # O'zgartiring - o'z task keyingizni yozing

print("=" * 60)
print(f"🔍 JIRA TASK TEKSHIRILMOQDA: {TASK_KEY}")
print("=" * 60)

try:
    # Task ma'lumotlarini olish
    print(f"\n📋 Task ma'lumoti olinmoqda...")
    task_details = jira.get_task_details(TASK_KEY)

    if not task_details:
        print(f"❌ Task {TASK_KEY} topilmadi!")
        print("\n📝 Yechim:")
        print("1. Task key to'g'ri ekanligini tekshiring")
        print("2. Task'ga access borligini tekshiring")
        exit(1)

    print(f"✅ Task topildi: {task_details.get('summary', 'N/A')}")

    # Figma link'larni qidirish
    print("\n🎨 Figma link'lar qidirilmoqda...\n")

    figma_links = []
    figma_pattern = r'https://(?:www\.)?figma\.com/(?:file|proto)/[A-Za-z0-9/\-]+'

    # 1. Description'dan qidirish
    description = task_details.get('description', '')
    if description:
        urls_in_desc = re.findall(figma_pattern, description)
        if urls_in_desc:
            print(f"📝 Description'da topildi:")
            for url in urls_in_desc:
                print(f"   - {url}")
                figma_links.append({
                    'url': url,
                    'source': 'description'
                })

    # 2. Comments'dan qidirish
    comments = task_details.get('comments', [])
    if comments:
        for comment in comments:
            comment_body = comment.get('body', '')
            urls_in_comment = re.findall(figma_pattern, comment_body)
            if urls_in_comment:
                print(f"\n💬 Comment'da topildi:")
                for url in urls_in_comment:
                    print(f"   - {url}")
                    print(f"     Author: {comment.get('author', 'Unknown')}")
                    figma_links.append({
                        'url': url,
                        'source': 'comment',
                        'author': comment.get('author')
                    })

    # 3. Attachment'larni tekshirish
    # JIRA'da Figma for JIRA app o'rnatilgan bo'lsa,
    # Figma file'lar alohida field'da bo'ladi

    # Natija
    print("\n" + "=" * 60)
    if figma_links:
        print(f"✅ JAMI {len(figma_links)} ta Figma link topildi!")
        print("=" * 60)

        print("\n📊 To'liq ro'yxat:")
        for i, link in enumerate(figma_links, 1):
            print(f"\n{i}. URL: {link['url']}")
            print(f"   Source: {link['source']}")
            if link.get('author'):
                print(f"   Author: {link['author']}")
    else:
        print("⚠️  Figma link topilmadi")
        print("=" * 60)
        print("\n💡 Ehtimoliy sabablar:")
        print("1. Task'da Figma link yo'q")
        print("2. Figma for JIRA app o'rnatilmagan")
        print("3. Link description/comment'larda emas")

        print("\n📝 Figma link qo'shish:")
        print("1. JIRA'da task'ni oching")
        print("2. 'Add design' tugmasini bosing (agar ko'rinsa)")
        print("3. Figma URL'ni kiriting")

except Exception as e:
    print(f"\n❌ XATOLIK: {str(e)}")
    import traceback

    print("\n🔧 Debug ma'lumotlari:")
    traceback.print_exc()

    print("\n📝 Keng tarqalgan xatoliklar:")
    print("1. JIRA credentials noto'g'ri (.env tekshiring)")
    print("2. Task topilmadi yoki access yo'q")
    print("3. Network muammosi")