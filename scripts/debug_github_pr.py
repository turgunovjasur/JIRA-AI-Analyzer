"""
Debug: GitHub PRdan qanday ma'lumotlar kelishini ko'rish
(GitHubClient import qilinmaydi — to'g'ridan-to'g'ri requests ishlatiladi)

Ishlatish:
    python scripts/debug_github_pr.py DEV-1234

Author: JASUR TURGUNOV
"""
import sys
import os
import json
import re
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def _make_request(session, url, params=None):
    """GitHub API ga so'rov yuborish"""
    try:
        resp = session.get(url, params=params, timeout=15)
        remaining = resp.headers.get('X-RateLimit-Remaining', '?')
        print(f"    → GET {url[:80]}  [{resp.status_code}] rate_limit_remaining={remaining}")
        return resp
    except Exception as e:
        print(f"    ❌ Request xatosi: {e}")
        return None


def debug_github_pr(task_key: str):
    print(f"\n{'#'*60}")
    print(f"  GITHUB DEBUG: {task_key}")
    print(f"{'#'*60}")

    # ── 1. Settings ──────────────────────────────────────────
    print("\n[1/5] Settings yuklanmoqda...")
    try:
        from config.settings import settings
        token = settings.GITHUB_TOKEN
        org   = settings.GITHUB_ORG
        base  = settings.GITHUB_API_URL
        token_tail = token[-6:] if token else ''
        print(f"  ✅ Token : {'***' + token_tail if token_tail else 'YOQ!'}")
        print(f"  ✅ Org   : {org}")
        print(f"  ✅ Base  : {base}")
    except Exception as e:
        print(f"  ❌ Settings xato: {e}")
        return

    # ── 2. Session ───────────────────────────────────────────
    print("\n[2/5] HTTP session yaratilmoqda...")
    session = requests.Session()
    session.headers.update({
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'QA-Assistant-Debug',
        'Authorization': f'token {token}' if token else ''
    })
    print("  ✅ Session tayyor")

    # ── 3. PR qidirish strategiyalari ───────────────────────
    print(f"\n[3/5] '{task_key}' uchun PR lar qidirilmoqda...")

    found_prs = []

    # Strategiya 1: GitHub Search API — title/body da task_key
    print(f"\n  [Strategiya 1] GitHub Search: title/body da '{task_key}'")
    search_url = f"{base}/search/issues"
    resp = _make_request(session, search_url, params={
        'q': f'{task_key} is:pr org:{org}',
        'per_page': 10
    })
    if resp and resp.status_code == 200:
        items = resp.json().get('items', [])
        print(f"    Topildi: {len(items)} ta PR")
        for item in items:
            found_prs.append({
                'number': item.get('number'),
                'title': item.get('title'),
                'html_url': item.get('html_url'),
                'state': item.get('state'),
                'repo_url': item.get('repository_url', ''),
                'strategy': 'search_title_body'
            })
    elif resp:
        print(f"    ⚠️  Status: {resp.status_code}, body: {resp.text[:200]}")

    # Strategiya 2: Branch nomi qidirish (repo listing)
    print(f"\n  [Strategiya 2] Repos listing va branch qidirish")
    repos_url = f"{base}/orgs/{org}/repos"
    resp = _make_request(session, repos_url, params={'per_page': 50, 'type': 'all'})
    if resp and resp.status_code == 200:
        repos = resp.json()
        print(f"    Org da {len(repos)} ta repo topildi")
        for repo in repos[:10]:  # Max 10 ta repo tekshiriladi
            repo_name = repo.get('name', '')
            # Bu repo da task_key bilan PR bormi?
            prs_url = f"{base}/repos/{org}/{repo_name}/pulls"
            pr_resp = _make_request(session, prs_url, params={
                'state': 'all',
                'per_page': 20
            })
            if pr_resp and pr_resp.status_code == 200:
                prs = pr_resp.json()
                for pr in prs:
                    title = pr.get('title', '')
                    body = pr.get('body', '') or ''
                    head = pr.get('head', {}).get('ref', '')
                    if (task_key.lower() in title.lower() or
                        task_key.lower() in body.lower() or
                        task_key.lower() in head.lower()):
                        found_prs.append({
                            'number': pr.get('number'),
                            'title': title,
                            'html_url': pr.get('html_url'),
                            'state': pr.get('state'),
                            'repo': repo_name,
                            'head_ref': head,
                            'strategy': 'repo_listing'
                        })
                        print(f"    ✅ Topildi! Repo: {repo_name}, PR #{pr.get('number')}: {title}")
    elif resp:
        print(f"    ⚠️  Repos olishda xato: {resp.status_code}")

    # Topilganlar
    print(f"\n  Jami topilgan PR: {len(found_prs)} ta")
    if not found_prs:
        print(f"\n  ⚠️  '{task_key}' uchun GitHub da PR topilmadi")
        print(f"  💡 Sabablari:")
        print(f"     - PR title/body da task key yo'q")
        print(f"     - Branch nomida task key yo'q")
        print(f"     - Boshqa task key bilan tekshiring")
        return

    # ── 4. PR detallari ──────────────────────────────────────
    print(f"\n[4/5] PR detallari olinmoqda...")

    for idx, pr_meta in enumerate(found_prs[:3]):  # Max 3 ta
        print(f"\n  {'─'*60}")
        print(f"  PR #{idx+1} ({pr_meta.get('strategy')})")
        print(f"  {'─'*60}")
        print(f"  number   : {pr_meta.get('number')}")
        print(f"  title    : {pr_meta.get('title')}")
        print(f"  url      : {pr_meta.get('html_url')}")
        print(f"  state    : {pr_meta.get('state')}")
        print(f"  repo     : {pr_meta.get('repo', '?')}")
        print(f"  head_ref : {pr_meta.get('head_ref', '?')}")

        # Repo va PR number aniqlash
        repo_name = pr_meta.get('repo')
        if not repo_name:
            # html_url dan ajratib olish: .../greenwhite/REPO/pull/123
            url = pr_meta.get('html_url', '')
            match = re.search(r'github\.com/[^/]+/([^/]+)/pull/(\d+)', url)
            if match:
                repo_name = match.group(1)
                pr_meta['number'] = int(match.group(2))

        pr_number = pr_meta.get('number')
        if not repo_name or not pr_number:
            print(f"  ⚠️  Repo yoki PR number aniqlanmadi, o'tkazib yuborilmoqda")
            continue

        # PR to'liq ma'lumotlari
        pr_url = f"{base}/repos/{org}/{repo_name}/pulls/{pr_number}"
        resp = _make_request(session, pr_url)
        if resp and resp.status_code == 200:
            pr_data = resp.json()
            print(f"\n  PR TO'LIQ MA'LUMOTLARI:")
            print(f"    Barcha kalitlar: {list(pr_data.keys())}")
            show_fields = ['number', 'title', 'state', 'merged', 'merge_commit_sha',
                           'additions', 'deletions', 'changed_files', 'commits']
            for f in show_fields:
                print(f"    {f:25s} = {pr_data.get(f, 'N/A')}")

            # Head/Base
            head = pr_data.get('head', {})
            base_branch = pr_data.get('base', {})
            print(f"    {'head.ref':<25} = {head.get('ref', 'N/A')}")
            print(f"    {'base.ref':<25} = {base_branch.get('ref', 'N/A')}")

            # Author
            user = pr_data.get('user', {})
            print(f"    {'author':<25} = {user.get('login', 'N/A')}")

            # Body (qisqa)
            body = pr_data.get('body', '') or ''
            print(f"    {'body (birinchi 200)':<25} = {repr(body[:200])}")

        # PR fayllar
        files_url = f"{base}/repos/{org}/{repo_name}/pulls/{pr_number}/files"
        resp = _make_request(session, files_url, params={'per_page': 30})
        if resp and resp.status_code == 200:
            files = resp.json()
            print(f"\n  PR FILES ({len(files)} ta fayl):")
            print(f"  Birinchi fayl kalitlari: {list(files[0].keys()) if files else '[]'}")
            print(f"\n  {'#':<4} {'STATUS':<10} {'+ADD':>6} {'-DEL':>6}  FILENAME")
            print(f"  {'-'*70}")
            for i, f in enumerate(files):
                fname    = f.get('filename', '')
                status   = f.get('status', '')
                adds     = f.get('additions', 0)
                dels     = f.get('deletions', 0)
                print(f"  {i:<4} {status:<10} {adds:>6} {dels:>6}  {fname}")
            # Feature/Tech extraction preview
            print(f"\n  FEATURE/TECH EXTRACTION PREVIEW:")
            features = set()
            techs    = set()
            tech_patterns = {
                'Oracle': [r'\.sql$', r'\.pks$', r'\.pkb$', r'\.pck$', r'/oracle/'],
                'HTML':   [r'\.html?$'],
                'Java':   [r'\.java$'],
                'JS':     [r'\.jsx?$'],
                'TS':     [r'\.tsx?$'],
                'Python': [r'\.py$'],
            }
            feat_patterns = [
                r'main/page/form/[^/]+/([^/]+)/',
                r'main/oracle/[^/]+/([^/]+)/',
                r'main/app/([^/]+)/',
                r'src/([^/]+)/',
            ]
            for f in files:
                fname = f.get('filename', '')
                for pat in feat_patterns:
                    m = re.search(pat, fname)
                    if m:
                        feat = re.sub(r'[^a-z0-9_]', '', m.group(1).lower())
                        if len(feat) > 2:
                            features.add(feat)
                for tech, pats in tech_patterns.items():
                    for p in pats:
                        if re.search(p, fname, re.IGNORECASE):
                            techs.add(tech)
            print(f"    feature_name      = {sorted(features) if features else 'topilmadi'}")
            print(f"    technology_stack  = {sorted(techs) if techs else 'topilmadi'}")

    # ── 5. Xulosa ────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  ⚙️  XULOSA: DB GA NIMA SAQLANADI (task_type EMAS)")
    print(f"{'='*60}")
    print(f"  GitHub dan faqat quyidagilar saqlanadi:")
    print(f"    feature_name     → PR fayl yo'llari asosida")
    print(f"    technology_stack → PR fayl kengaytmalari asosida")
    print(f"  task_type esa JIRA dan keladi (debug_jira_task.py ga qarang)")

    print(f"\n{'#'*60}")
    print(f"  Debug yakunlandi: {task_key}")
    print(f"{'#'*60}\n")


if __name__ == '__main__':
    task_key = sys.argv[1] if len(sys.argv) > 1 else None
    if not task_key:
        print("Ishlatish: python scripts/debug_github_pr.py DEV-XXXX")
        sys.exit(1)
    debug_github_pr(task_key)
