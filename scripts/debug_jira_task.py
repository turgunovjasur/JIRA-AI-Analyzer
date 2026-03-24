"""
Debug: JIRA taskdan qanday ma'lumotlar kelishini ko'rish

Ishlatish:
    python scripts/debug_jira_task.py DEV-1234

    Agar task key bilmasangiz, avval DB dagi task keylarni ko'ring:
    python scripts/debug_jira_task.py --list

Author: JASUR TURGUNOV
"""
import sys
import os
import json
import sqlite3

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

DB_FILE = os.path.join(PROJECT_ROOT, 'data', 'processing.db')


def list_db_tasks():
    """DB dagi task keylarni ko'rsatish"""
    print(f"\n{'='*60}")
    print(f"  DB dagi task keylar: {DB_FILE}")
    print(f"{'='*60}")
    if not os.path.exists(DB_FILE):
        print("  ❌ DB fayl topilmadi")
        return
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT task_id, task_type, task_status, assignee, created_at
        FROM task_processing
        ORDER BY created_at DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("  DB bo'sh")
        return
    print(f"  {'TASK_ID':<15} {'TYPE':<20} {'STATUS':<15} {'ASSIGNEE':<20} {'CREATED'}")
    print(f"  {'-'*90}")
    for r in rows:
        print(f"  {r['task_id']:<15} {str(r['task_type']):<20} {str(r['task_status']):<15} "
              f"{str(r['assignee']):<20} {str(r['created_at'])[:16]}")
    print(f"\n  💡 Yuqoridagi task keylardan birini tanlang va ishga tushiring:")
    print(f"     python scripts/debug_jira_task.py {rows[0]['task_id']}")


def debug_jira_task(task_key: str):
    print(f"\n{'#'*60}")
    print(f"  JIRA DEBUG: {task_key}")
    print(f"{'#'*60}")

    # ── 1. Settings ──────────────────────────────────────────
    print("\n[1/4] Settings yuklanmoqda...")
    try:
        from config.settings import settings
        print(f"  ✅ JIRA Server : {settings.JIRA_SERVER}")
        print(f"  ✅ JIRA Email  : {settings.JIRA_EMAIL}")
        token_tail = settings.JIRA_API_TOKEN[-6:] if settings.JIRA_API_TOKEN else ''
        print(f"  ✅ JIRA Token  : {'***' + token_tail if token_tail else 'YOQ!'}")
    except Exception as e:
        print(f"  ❌ Settings xato: {e}")
        return

    # ── 2. JIRA ulanish ──────────────────────────────────────
    print("\n[2/4] JIRA ga ulanmoqda...")
    try:
        from utils.jira.jira_client import JiraClient
        jira = JiraClient()
        _ = jira.client
        print("  ✅ JIRA ulanish muvaffaqiyatli")
    except Exception as e:
        print(f"  ❌ JIRA ulanish xatosi: {e}")
        return

    # ── 3. Task ma'lumotlari ─────────────────────────────────
    print(f"\n[3/4] {task_key} ma'lumotlari olinmoqda...")
    try:
        task_details = jira.get_task_details(task_key)
        if not task_details:
            print(f"  ❌ Task topilmadi: {task_key}")
            print(f"\n  💡 DB dagi mavjud task keylar:")
            list_db_tasks()
            return
        print(f"  ✅ Task ma'lumotlari olindi")
    except Exception as e:
        print(f"  ❌ get_task_details xatosi: {e}")
        print(f"\n  💡 DB dagi mavjud task keylar:")
        list_db_tasks()
        return

    # ── 4. Natijalar ─────────────────────────────────────────
    print(f"\n[4/4] Natijalar:\n")

    # Asosiy maydonlar
    print(f"\n{'='*60}")
    print(f"  ASOSIY MA'LUMOTLAR")
    print(f"{'='*60}")
    main_fields = {
        'key'         : task_details.get('key'),
        'summary'     : task_details.get('summary', '')[:80],
        '>>> type'    : task_details.get('type'),       # ← Bu task_type uchun ishlatiladi!
        'status'      : task_details.get('status'),
        'assignee'    : task_details.get('assignee'),
        'reporter'    : task_details.get('reporter'),
        'priority'    : task_details.get('priority'),
        'story_points': task_details.get('story_points'),
        'created'     : task_details.get('created'),
        'resolved'    : task_details.get('resolved'),
        'labels'      : task_details.get('labels'),
        'components'  : task_details.get('components'),
    }
    for k, v in main_fields.items():
        print(f"  {k:20s} = {v}")

    # Description
    desc = task_details.get('description', '') or ''
    print(f"\n{'='*60}")
    print(f"  DESCRIPTION (birinchi 400 belgi)")
    print(f"{'='*60}")
    print(f"  {repr(desc[:400])}")

    # PR URLs
    pr_urls = task_details.get('pr_urls', [])
    print(f"\n{'='*60}")
    print(f"  PR URLs ({len(pr_urls)} ta)")
    print(f"{'='*60}")
    if pr_urls:
        for i, pr in enumerate(pr_urls):
            print(f"  [{i}] url    = {pr.get('url', '')}")
            print(f"      title  = {pr.get('title', '')}")
            print(f"      status = {pr.get('status', '')}")
            print(f"      source = {pr.get('source', '')}")
    else:
        print("  ⚠️  PR URL topilmadi (JIRA da PR bog'liq emas)")

    # Comments
    comments = task_details.get('comments', [])
    print(f"\n{'='*60}")
    print(f"  COMMENTS ({len(comments)} ta, birinchi 3 ko'rsatilmoqda)")
    print(f"{'='*60}")
    for i, c in enumerate(comments[:3]):
        print(f"  [{i}] author = {c.get('author', '')}")
        print(f"      body   = {c.get('body', '')[:120]}...")
    if len(comments) > 3:
        print(f"  ... va yana {len(comments)-3} ta comment")

    # Figma
    figma = task_details.get('figma_links', [])
    print(f"\n{'='*60}")
    print(f"  FIGMA LINKS ({len(figma)} ta)")
    print(f"{'='*60}")
    for i, f in enumerate(figma):
        print(f"  [{i}] {f}")

    # Barcha kalitlar
    print(f"\n{'='*60}")
    print(f"  BARCHA MAYDONLAR (kalitlar ro'yxati)")
    print(f"{'='*60}")
    print(f"  {list(task_details.keys())}")

    # ── Xulosa ───────────────────────────────────────────────
    raw_type = task_details.get('type', '') or ''
    saved_type = raw_type.strip() if raw_type.strip() else 'other'

    print(f"\n{'='*60}")
    print(f"  ⚙️  task_type XULOSA")
    print(f"{'='*60}")
    print(f"  task_details['type']    = '{raw_type}'")
    print(f"  DB ga saqlanadigan qiymat = '{saved_type}'")
    print(f"\n  allowed_issue_types sozlamasi bilan solishtirish:")
    try:
        from config.app_settings import get_app_settings
        allowed = get_app_settings().tz_pr_checker.allowed_issue_types
        allowed_list = [t.strip() for t in allowed.split(',') if t.strip()]
        print(f"  allowed_issue_types = {allowed_list}")
        if saved_type in allowed_list:
            print(f"  ✅ '{saved_type}' sozlamada bor — statistika to'g'ri ishlaydi")
        else:
            print(f"  ⚠️  '{saved_type}' sozlamada YO'Q!")
            print(f"  💡 allowed_issue_types ga '{saved_type}' qo'shing")
            print(f"     yoki sozlamadagi nomlarni JIRA dagi nom bilan moslashtiring")
    except Exception as e:
        print(f"  ⚠️  app_settings o'qib bo'lmadi: {e}")

    print(f"\n{'#'*60}")
    print(f"  Debug yakunlandi: {task_key}")
    print(f"{'#'*60}\n")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--list':
        list_db_tasks()
    else:
        task_key = sys.argv[1] if len(sys.argv) > 1 else None
        if not task_key:
            print("Ishlatish: python scripts/debug_jira_task.py DEV-XXXX")
            print("           python scripts/debug_jira_task.py --list   (DB dagi task keylarni ko'rish)")
            list_db_tasks()
        else:
            debug_jira_task(task_key)
