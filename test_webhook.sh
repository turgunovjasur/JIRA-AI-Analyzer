#!/usr/bin/env bash
# Multi-agent webhook TEST — local Mac backendiga JIRA webhook'ini simulyatsiya qiladi.
# Windows'dagi jonli monolitga TEGMAYDI (so'rov to'g'ridan-to'g'ri localhost:8000 ga boradi).
#
# Foydalanish:
#   ./test_webhook.sh                 # default DEV-8245
#   ./test_webhook.sh DEV-1234        # boshqa task
#   BACKEND=http://127.0.0.1:8000 ./test_webhook.sh DEV-1234

set -euo pipefail

TASK_KEY="${1:-DEV-8245}"
BACKEND="${BACKEND:-http://127.0.0.1:8000}"
ISSUE_TYPE="${ISSUE_TYPE:-DEV-BUG}"          # uzum allowed_issue_types ichidan
ASSIGNEE="${ASSIGNEE:-Test QA}"               # excluded ro'yxatida BO'LMAGAN ism
TRIGGER_STATUS="${TRIGGER_STATUS:-READY TO TEST}"
FROM_STATUS="${FROM_STATUS:-In Progress}"

echo "▶ Webhook simulyatsiya → $BACKEND/webhook/jira"
echo "  task=$TASK_KEY type=$ISSUE_TYPE assignee='$ASSIGNEE' status='$FROM_STATUS' → '$TRIGGER_STATUS'"
echo ""

PAYLOAD=$(cat <<JSON
{
  "webhookEvent": "jira:issue_updated",
  "issue": {
    "key": "$TASK_KEY",
    "fields": {
      "issuetype": { "name": "$ISSUE_TYPE" },
      "assignee": { "displayName": "$ASSIGNEE" }
    }
  },
  "changelog": {
    "items": [
      { "field": "status", "fromString": "$FROM_STATUS", "toString": "$TRIGGER_STATUS" }
    ]
  }
}
JSON
)

echo "=== Javob ==="
curl -s -X POST "$BACKEND/webhook/jira" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | python3 -m json.tool 2>/dev/null || echo "(JSON emas — yuqoriga qarang)"

echo ""
echo "=== Keyingi qadam ==="
echo "  1. Backend terminalida agent1 → agent1b → agent2 → agent3 oqimini kuzating"
echo "  2. JIRA'da $TASK_KEY task'ida [AI_S1] multi-agent comment'ini kuting (~1-2 daqiqa)"
