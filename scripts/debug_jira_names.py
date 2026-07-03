"""
JIRA Issue Type va Assignee nomlarini tekshirish uchun debug script.

Ishlatish:
    python scripts/debug_jira_names.py

Nima qiladi:
    1. Barcha mavjud JIRA issue type nomlarini ko'rsatadi
    2. So'nggi N taskdan assignee displayName larini ko'rsatadi
    3. Bitta task uchun webhook payload simulatsiyasi
    4. Sozlamalardagi filter qiymatlarini real JIRA ma'lumotlari bilan solishtiradi
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import requests

JIRA_SERVER = os.getenv('JIRA_SERVER', 'https://smartupx.atlassian.net')
JIRA_EMAIL  = os.getenv('JIRA_EMAIL')
JIRA_TOKEN  = os.getenv('JIRA_API_TOKEN')
AUTH        = (JIRA_EMAIL, JIRA_TOKEN)
HEADERS     = {"Accept": "application/json"}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SOZLAMALAR: Mana shu yerga o'z qiymatlaringizni yozing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ALLOWED_ISSUE_TYPES = [
    "DEV- PROD TASK",
    "DEV-BUG",
    "DEV-TECHTASK",
    "DEV-CLIENT TASK",
]

EXCLUDED_ASSIGNEES = [
    "Dilmurod Muminbekov",
    "Sadikova Farangiz",
    "Alisher Umarov",
    "Valeriy Khan",
    "Asadbek Akmalov",
    "Komiljon Zokirov",
    "Shahzod Mirjalolov",
    "Ergashev Zarifjon",
    "Shakhzodbek Abdujabborov"
]

# So'nggi nechta task tekshirilsin
MAX_RECENT_TASKS = 200

# Bitta aniq task tekshirish (ixtiyoriy, None qoldirsa o'tkazib yuboriladi)
SINGLE_TASK_KEY = None  # masalan: "DEV-1234"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def jira_get(path: str, params: dict = None) -> dict:
    url = f"{JIRA_SERVER}/rest/api/2/{path}"
    r = requests.get(url, auth=AUTH, headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def jira_search(jql: str, fields: list, max_results: int = 60) -> dict:
    """POST /rest/api/2/search/jql — Atlassian Cloud yangi endpoint"""
    # Yangi endpoint sinab ko'ramiz, eski endpoint 410 bersa fallback
    for endpoint in [
        f"{JIRA_SERVER}/rest/api/2/search/jql",
        f"{JIRA_SERVER}/rest/api/3/issue/search/jql",
    ]:
        try:
            r = requests.post(
                endpoint, auth=AUTH,
                headers={**HEADERS, "Content-Type": "application/json"},
                json={"jql": jql, "maxResults": max_results, "fields": fields},
                timeout=15,
            )
            if r.status_code == 410:
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError:
            continue

    # Oxirgi fallback: GET with query params
    r = requests.get(
        f"{JIRA_SERVER}/rest/api/2/search",
        auth=AUTH, headers=HEADERS,
        params={"jql": jql, "maxResults": max_results, "fields": ",".join(fields)},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def sep(title: str = ""):
    print("\n" + "═" * 62)
    if title:
        print(f"  {title}")
        print("═" * 62)


# ──────────────────────────────────────────────────────
# 1. Barcha issue type'lar
# ──────────────────────────────────────────────────────
def show_issue_types():
    sep("📋 JIRA BARCHA ISSUE TYPE'LAR  (webhook 'issuetype.name')")
    data = jira_get("issuetype")
    types = sorted(data, key=lambda x: x['name'])
    for t in types:
        match = "✅" if t['name'] in ALLOWED_ISSUE_TYPES else "  "
        print(f"  {match}  {t['name']!r:42s}  id={t['id']}")

    print()
    not_found = [t for t in ALLOWED_ISSUE_TYPES if t not in [x['name'] for x in types]]
    if not_found:
        print("  ⚠️  SOZLAMADA BOR LEKIN JIRA'DA YO'Q:")
        for name in not_found:
            print(f"       ❌  {name!r}  ← nomi noto'g'ri!")
    else:
        print("  ✅  Barcha allowed_issue_types JIRA'da topildi")


# ──────────────────────────────────────────────────────
# 2. So'nggi N taskdan assignee + type nomlar
# ──────────────────────────────────────────────────────
def show_recent_tasks(max_results: int = 60):
    sep(f"👤 SO'NGI {max_results} TASK — ASSIGNEE va ISSUE TYPE NOMLARI")
    data = jira_search(
        jql="project = DEV ORDER BY updated DESC",
        fields=["assignee", "issuetype", "status", "summary"],
        max_results=max_results,
    )

    seen_assignees: dict[str, str] = {}
    seen_types: dict[str, str] = {}

    for issue in data.get("issues", []):
        fields = issue["fields"]
        assignee = fields.get("assignee")
        if assignee:
            name  = assignee.get("displayName", "")
            email = assignee.get("emailAddress", "")
            if name and name not in seen_assignees:
                seen_assignees[name] = email

        itype = fields.get("issuetype", {})
        iname = itype.get("name", "")
        if iname and iname not in seen_types:
            seen_types[iname] = itype.get("id", "")

    print("\n  👤 TOPILGAN ASSIGNEE displayName'lar:")
    for name, email in sorted(seen_assignees.items()):
        match = "🚫" if name in EXCLUDED_ASSIGNEES else "  "
        print(f"    {match}  {name!r:42s}  ({email})")

    print("\n  📋 TOPILGAN ISSUE TYPE nomlari:")
    for name, tid in sorted(seen_types.items()):
        match = "✅" if name in ALLOWED_ISSUE_TYPES else "  "
        print(f"    {match}  {name!r:42s}  id={tid}")

    # Mos kelmaydiganlarni aniqlaymiz
    print()
    not_found_assignees = [a for a in EXCLUDED_ASSIGNEES if a not in seen_assignees]
    if not_found_assignees:
        print("  ⚠️  EXCLUDED_ASSIGNEES da bor lekin so'nggi tasklarda yo'q:")
        for a in not_found_assignees:
            print(f"       ❓  {a!r}  ← nomi noto'g'ri yoki bu tasklar boshqa proyektda")
    else:
        print("  ✅  Barcha excluded_assignees so'nggi tasklarda topildi")


# ──────────────────────────────────────────────────────
# 3. Bitta task — webhook payload simulatsiyasi
# ──────────────────────────────────────────────────────
def show_single_task(task_key: str):
    sep(f"🔍 TASK {task_key} — WEBHOOK FIELDLARI (aynan shunday keladi)")
    data = jira_get(f"issue/{task_key}", params={"fields": "assignee,issuetype,status,summary"})
    fields   = data["fields"]
    assignee = fields.get("assignee") or {}
    itype    = fields.get("issuetype") or {}
    status   = fields.get("status") or {}

    itype_name    = itype.get("name", "")
    assignee_name = assignee.get("displayName", "Unassigned")

    print(f"\n  summary      : {fields.get('summary', '')[:70]}")
    print(f"  issuetype    : {itype_name!r}")
    print(f"  assignee     : {assignee_name!r}")
    print(f"  status       : {status.get('name', '')!r}")

    print()
    type_allowed  = itype_name in ALLOWED_ISSUE_TYPES
    assignee_excl = assignee_name in EXCLUDED_ASSIGNEES

    print(f"  Issue Type filtri  : {'✅ RUXSAT'  if type_allowed  else '❌ SKIP — allowed listda yoq'}")
    print(f"  Assignee filtri    : {'🚫 SKIP — excluded listda bor' if assignee_excl else '✅ RUXSAT'}")

    if type_allowed and not assignee_excl:
        print("\n  ✅  NATIJA: Servislar ISHGA TUSHADI")
    else:
        print("\n  ⛔  NATIJA: Servislar SKIP bo'ladi")


# ──────────────────────────────────────────────────────
# 4. Joriy app_settings.json dagi qiymatlarni ko'rsatish
# ──────────────────────────────────────────────────────
def show_saved_settings():
    sep("💾 SAQLANGAN app_settings.json FILTER QIYMATLARI")
    try:
        from config.app_settings import get_app_settings
        s = get_app_settings(force_reload=True).tz_pr_checker
        print(f"\n  allowed_issue_types  : {s.allowed_issue_types!r}")
        print(f"  excluded_assignees   : {s.excluded_assignees!r}")
    except Exception as e:
        print(f"  ⚠️  settings yuklanmadi: {e}")


# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    if not JIRA_EMAIL or not JIRA_TOKEN:
        print("❌ JIRA_EMAIL yoki JIRA_API_TOKEN .env da yo'q!")
        sys.exit(1)

    print(f"\n  JIRA server : {JIRA_SERVER}")
    print(f"  Email       : {JIRA_EMAIL}")

    show_saved_settings()
    show_issue_types()
    show_recent_tasks(MAX_RECENT_TASKS)

    if SINGLE_TASK_KEY:
        show_single_task(SINGLE_TASK_KEY)

    print("\n" + "═" * 62)
    print("  Tayyor. Yuqoridagi ✅ / ❌ / ⚠️ belgilarni tekshiring.")
    print("  Noto'g'ri nomlarni aynan JIRA ko'rsatgan nom bilan almashtiring.")
    print("═" * 62 + "\n")
