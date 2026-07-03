"""Agent1 test natijalarini JIRA bilan taqqoslash skripti."""
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()
from utils.jira.jira_client import JiraClient

MD_PATH = "/Users/mac/Documents/projects/QA-Assistant/AGENT1_TEST_RESULTS.md"

def extract_jsons(content):
    """Markdown'dan 3 ta JSON ni ajratish."""
    pattern = r"<!-- BEGIN AGENT1 JSON -->(.*?)<!-- END AGENT1 JSON -->"
    blocks = re.findall(pattern, content, re.DOTALL)
    results = []
    for block in blocks:
        s = block.strip()
        if s.startswith("```json"):
            s = s[7:]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
        try:
            results.append(json.loads(s))
        except json.JSONDecodeError as e:
            results.append({"error": str(e), "raw_head": s[:200]})
    return results

def count_ac_dod(desc):
    """JIRA description'dan AC va DoD punktlarini sanash."""
    ac_items = []
    dod_items = []
    if not desc:
        return ac_items, dod_items
    ac_match = re.search(r"Acceptance Criteria(.+?)(?=----|$)", desc, re.DOTALL)
    if ac_match:
        ac_items = [l.strip()[1:].strip() for l in ac_match.group(1).split("\n") if l.strip().startswith("*")]
    dod_match = re.search(r"DoD(.+?)(?=----)", desc, re.DOTALL)
    if dod_match:
        dod_items = [l.strip()[1:].strip() for l in dod_match.group(1).split("\n") if l.strip().startswith("*")]
    return ac_items, dod_items

def get_jira_summary(client, task_key):
    """JIRA dan task tafsilotini olish va sanash."""
    task = client.get_task_details(task_key)
    desc = task.get("description", "") or ""
    ac_items, dod_items = count_ac_dod(desc)
    expected_match = re.search(r"(Ожидаемый результат|Expected result)(.+?)(?=Фактический|Actual|----|$)", desc, re.DOTALL | re.IGNORECASE)
    actual_match = re.search(r"(Фактический результат|Actual result)(.+?)(?=----|$)", desc, re.DOTALL | re.IGNORECASE)
    return {
        "key": task_key,
        "summary": task.get("summary"),
        "status": task.get("status"),
        "issue_type": task.get("issue_type"),
        "ac_count": len(ac_items),
        "ac_items": ac_items,
        "dod_count": len(dod_items),
        "dod_items": dod_items,
        "has_expected": bool(expected_match),
        "has_actual": bool(actual_match),
        "desc_len": len(desc),
        "comments_count": len(task.get("comments", [])),
    }

def summarize_agent1(payload):
    """Agent1 natijasidan asosiy raqamlarni olish."""
    final = payload.get("final_result") or payload.get("run_snapshot", {}).get("final_result") or {}
    artifact = None
    for run in payload.get("agent_runs") or final.get("agent_runs") or []:
        if run.get("agent_key") == "agent1_scope_builder":
            artifact = run.get("artifact") or {}
            break
    if not artifact:
        artifact = final.get("requirement_inventory") or []

    reqs = artifact.get("requirements") if isinstance(artifact, dict) else artifact
    if not isinstance(reqs, list):
        reqs = final.get("requirement_inventory") or []

    source_stats = artifact.get("source_stats") if isinstance(artifact, dict) else {}
    warnings = (final.get("warnings") or []) if isinstance(final, dict) else []

    source_counts = {}
    for r in reqs:
        source = r.get("source", "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1

    return {
        "task_key": final.get("task_key") if isinstance(final, dict) else payload.get("task_key"),
        "total_reqs": len(reqs),
        "source_breakdown": source_counts,
        "source_stats": source_stats or {},
        "warnings": warnings,
        "requirements": reqs,
        "execution_mode": final.get("execution_mode") if isinstance(final, dict) else "",
        "pr_count": final.get("pr_count") if isinstance(final, dict) else None,
        "figma_data": final.get("figma_data") if isinstance(final, dict) else None,
        "verdict_label": (final.get("analysis_overview") or {}).get("verdict_label") if isinstance(final, dict) else "",
        "coverage_warning": next((w for w in warnings if "Coverage" in w), None),
    }

def main():
    with open(MD_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    jsons = extract_jsons(content)
    print(f"Topildi: {len(jsons)} ta JSON\n")

    client = JiraClient(os.getenv("JIRA_SERVER"), os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN"))

    report = []
    for i, payload in enumerate(jsons, 1):
        if "error" in payload:
            print(f"=== Task {i}: JSON parse error: {payload['error']}")
            continue
        a = summarize_agent1(payload)
        task_key = a["task_key"]
        print(f"=== Task {i}: {task_key} ===")
        j = get_jira_summary(client, task_key)

        print(f"  Summary: {j['summary']}")
        print(f"  Status: {j['status']} | Type: {j['issue_type']}")
        print(f"  Desc length: {j['desc_len']} chars | Comments: {j['comments_count']}")
        print(f"  JIRA AC count: {j['ac_count']}")
        print(f"  JIRA DoD count: {j['dod_count']}")
        print(f"  Has Expected/Actual: {j['has_expected']} / {j['has_actual']}")
        print(f"  Agent1 total REQ: {a['total_reqs']}")
        print(f"  Agent1 source_stats: {a['source_stats']}")
        print(f"  Agent1 source breakdown: {a['source_breakdown']}")
        print(f"  Execution mode: {a['execution_mode']}")
        print(f"  PR count: {a['pr_count']} | Figma: {bool(a['figma_data'])}")
        print(f"  Verdict: {a['verdict_label']}")
        print(f"  Coverage warning: {a['coverage_warning']}")
        print(f"  All warnings: {a['warnings']}")
        print()

        report.append({"jira": j, "agent1": a})

    # Output JSON file for further analysis
    out_path = "/tmp/agent1_analysis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nFull report saved: {out_path}")

if __name__ == "__main__":
    main()
