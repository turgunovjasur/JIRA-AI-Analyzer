"""
JIRA Statuslarini Aniqlash Skripti

Nima qiladi:
  1. Sprinting barcha tasklar changelogini o'qiydi
  2. Barcha unique statuslarni topadi
  3. Har bir statusga qancha vaqt sarflanganini ko'rsatadi
  4. Status → Status o'tish sxemasini chiqaradi

Ishlatish:
    python scripts/discover_jira_statuses.py
"""

import os
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv
from jira import JIRA
from tqdm import tqdm

load_dotenv()

# download_all_file.py dagi Config bilan bir xil
SPRINT_IDS   = [3083, 3297, 3295, 3296, 3300, 3229]
PROJECT_KEY  = 'DEV'
SPRINT_FIELD = 'customfield_10020'
STORY_POINTS_FIELD = 'customfield_10016'


# ── JIRA ulanish ─────────────────────────────────────────────────────────────
def get_jira():
    return JIRA(
        server=os.getenv('JIRA_SERVER'),
        basic_auth=(os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN'))
    )


# ── Tasklar olish ─────────────────────────────────────────────────────────────
def fetch_issues(jira):
    sprint_ids_str = ', '.join(map(str, SPRINT_IDS))
    jql = f'project = "{PROJECT_KEY}" AND sprint IN ({sprint_ids_str}) ORDER BY created DESC'
    print(f"  JQL: {jql}\n")
    issues = jira.search_issues(jql, maxResults=False, expand='changelog')
    print(f"  ✅ {len(issues)} ta task yuklandi\n")
    return issues


# ── Statuslar tahlili ─────────────────────────────────────────────────────────
def analyze_statuses(issues):
    """
    Qaytaradi:
      all_statuses   - {status_name: {count, total_hours}}
      transitions    - {(from, to): count}
      task_samples   - {status_name: [task_key, ...]}  (har biridan 3 ta)
    """
    all_statuses  = defaultdict(lambda: {'count': 0, 'total_hours': 0.0})
    transitions   = defaultdict(int)
    task_samples  = defaultdict(list)

    for issue in tqdm(issues, desc="Tahlil"):
        if not hasattr(issue, 'changelog') or not issue.changelog:
            continue

        # changelog ni vaqt bo'yicha tartibga solish
        changes = []
        for history in issue.changelog.histories:
            for item in history.items:
                if item.field == 'status':
                    changes.append({
                        'date':    history.created,
                        'from':    item.fromString or 'None',
                        'to':      item.toString   or 'None',
                    })

        if not changes:
            continue

        # Har bir status uchun vaqt hisoblash
        for i, ch in enumerate(changes):
            status = ch['to']
            all_statuses[status]['count'] += 1

            if len(task_samples[status]) < 3:
                task_samples[status].append(issue.key)

            # Qachon chiqib ketdi?
            start_dt = datetime.fromisoformat(ch['date'].replace('Z', '+00:00'))
            if i + 1 < len(changes):
                end_dt = datetime.fromisoformat(changes[i+1]['date'].replace('Z', '+00:00'))
            else:
                # Hali shu statusda
                end_dt = datetime.now(start_dt.tzinfo)

            hours = (end_dt - start_dt).total_seconds() / 3600
            all_statuses[status]['total_hours'] += hours

            # O'tish: from → to
            transitions[(ch['from'], ch['to'])] += 1

        # Birinchi status (task yaratilganda bo'lgan)
        first_from = changes[0]['from']
        all_statuses[first_from]['count'] += 1

    return all_statuses, transitions, task_samples


# ── Chiqarish ─────────────────────────────────────────────────────────────────
def print_report(all_statuses, transitions, task_samples):

    print(f"\n{'='*70}")
    print("  BARCHA STATUSLAR (vaqt bo'yicha kamayish tartibi)")
    print(f"{'='*70}")
    print(f"  {'STATUS NOMI':<38} {'TASK':<8} {'ORT. KUN':<12} {'JAMI KUN'}")
    print(f"  {'─'*67}")

    sorted_statuses = sorted(
        all_statuses.items(),
        key=lambda x: x[1]['total_hours'],
        reverse=True
    )

    for name, data in sorted_statuses:
        count       = data['count']
        total_days  = data['total_hours'] / 24
        avg_days    = total_days / count if count else 0
        samples     = ', '.join(task_samples.get(name, []))
        print(f"  {name:<38} {count:<8} {avg_days:<12.1f} {total_days:.1f}  "
              f"  (e.g: {samples})")

    print(f"\n{'='*70}")
    print("  STATUS O'TISH SXEMASI (top 20 yo'nalish)")
    print(f"{'='*70}")
    print(f"  {'FROM':<35} {'TO':<35} {'SONI'}")
    print(f"  {'─'*70}")

    top_transitions = sorted(transitions.items(), key=lambda x: x[1], reverse=True)[:20]
    for (frm, to), cnt in top_transitions:
        print(f"  {frm:<35} {to:<35} {cnt}")

    print(f"\n{'='*70}")
    print("  KEYINGI QADAM: Statuslarni 4 guruhga ajrating")
    print(f"{'='*70}")
    print("""
  Barcha status nomlarini ko'rib, quyidagilarni aniqlang:

  ⏳ KUTISH (vaqt hisoblanmaydi)    →  masalan: Open, Backlog, To Do
  🔨 ISHLASH (vaqt hisoblanadi)     →  masalan: In Progress, In Development
  🔍 TEKSHIRISH (ixtiyoriy)         →  masalan: In Review, TESTING, Ready to Test
  ✅ YAKUNLANGAN                     →  masalan: CLOSED, Done, Resolved

  Aniqlangandan keyin velocity hisoblashni implement qilamiz.
""")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*70}")
    print("  JIRA STATUS ANIQLOVCHI")
    print(f"{'='*70}\n")

    print("[1/3] JIRA ga ulanmoqda...")
    jira = get_jira()
    print(f"  ✅ Ulandi: {os.getenv('JIRA_SERVER')}\n")

    print("[2/3] Tasklar yuklanmoqda...")
    issues = fetch_issues(jira)

    print("[3/3] Statuslar tahlil qilinmoqda...")
    all_statuses, transitions, task_samples = analyze_statuses(issues)

    print_report(all_statuses, transitions, task_samples)


if __name__ == '__main__':
    main()
