"""Operator entry point: read Jira, import only open issues and existing task history."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.team_analytics_sync import sync_company

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--company-id", type=int, required=True)
    parser.add_argument("--initial", action="store_true")
    args = parser.parse_args()
    print(json.dumps(sync_company(args.company_id, initial=args.initial), default=str), flush=True)
