"""
Sprint Report API - FastAPI endpoints for sprint analytics

Author: JASUR TURGUNOV
Version: 1.0
"""
import os
import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from services.api.session_scope import get_session_company_id, get_session_role, load_api_session
from utils.database.runtime import connect_processing_db, get_db_backend
from utils.database.sprint_report_repository import (
    fetch_bug_distribution,
    fetch_developer_workload,
    fetch_task_type_stats,
    fetch_top_features,
    fetch_total_tasks,
)

router = APIRouter(prefix="/api", tags=["sprint-report"])

def _require_api_token(x_api_token: Optional[str]) -> None:
    """Sprint report API uchun oddiy token himoyasi."""
    expected_token = os.getenv("SPRINT_REPORT_API_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=503, detail="Sprint report API disabled")
    if not x_api_token or not secrets.compare_digest(x_api_token, expected_token):
        raise HTTPException(status_code=401, detail="Invalid API token")


def _resolve_company_scope(
    company_id: int,
    x_session_id: Optional[str],
    x_api_token: Optional[str],
) -> int:
    if x_session_id:
        session = load_api_session(x_session_id, allowed_roles={"super_admin", "company_admin"})
        role = get_session_role(session)
        if role == "company_admin":
            session_company_id = get_session_company_id(session)
            if not session_company_id or company_id != session_company_id:
                raise HTTPException(status_code=403, detail="Boshqa company sprint reportini ko'rib bo'lmaydi")
            return session_company_id
        return company_id

    _require_api_token(x_api_token)
    return company_id


# Response models
class TaskTypeStats(BaseModel):
    task_type: str
    count: int
    percentage: float


class FeatureStats(BaseModel):
    feature_name: str
    total_tasks: int
    product: int
    client: int
    bug: int
    error: int
    analiz: int
    other: int


class BugDistribution(BaseModel):
    feature_name: str
    bug_count: int
    error_count: int
    total: int


class DeveloperWorkload(BaseModel):
    assignee: str
    total_tasks: int
    completed: int
    in_progress: int
    returned: int
    avg_compliance_score: Optional[float]


class SprintReportResponse(BaseModel):
    period: str
    total_tasks: int
    task_by_type: List[TaskTypeStats]
    top_features: List[FeatureStats]
    bug_distribution: List[BugDistribution]
    developer_workload: List[DeveloperWorkload]
    generated_at: str


@router.get("/sprint-report", response_model=SprintReportResponse)
def get_sprint_report(
    company_id: int = Query(..., ge=1, description="Company ID"),
    days: int = Query(default=7, ge=1, le=365, description="Period in days"),
    limit: int = Query(default=10, ge=1, le=100, description="Top features limit"),
    x_api_token: Optional[str] = Header(default=None, alias="X-API-Token"),
    x_session_id: Optional[str] = Header(default=None, alias="X-Session-ID"),
):
    """
    Sprint report with task statistics.

    Returns:
    - Task counts by type (product, client, bug, error, analiz)
    - Top features with breakdown
    - Bug/error distribution by feature
    - Developer workload statistics
    """
    scoped_company_id = _resolve_company_scope(company_id, x_session_id, x_api_token)

    try:
        conn = connect_processing_db(row_factory=True)
        cursor = conn.cursor()

        total_tasks = fetch_total_tasks(cursor, scoped_company_id, days)

        task_by_type = [
            TaskTypeStats(
                task_type=row['task_type'],
                count=row['count'],
                percentage=round(row['count'] / total_tasks * 100, 2) if total_tasks > 0 else 0
            )
            for row in fetch_task_type_stats(cursor, scoped_company_id, days)
        ]

        top_features = [
            FeatureStats(**row)
            for row in fetch_top_features(cursor, scoped_company_id, days, limit)
        ]

        bug_distribution = [
            BugDistribution(**row)
            for row in fetch_bug_distribution(cursor, scoped_company_id, days)
        ]

        developer_workload = [
            DeveloperWorkload(
                assignee=row['assignee'],
                total_tasks=row['total_tasks'],
                completed=row['completed'],
                in_progress=row['in_progress'],
                returned=row['returned'],
                avg_compliance_score=round(row['avg_compliance_score'], 2)
                    if row['avg_compliance_score'] else None
            )
            for row in fetch_developer_workload(cursor, scoped_company_id, days)
        ]

        conn.close()

        return SprintReportResponse(
            period=f"Last {days} days",
            total_tasks=total_tasks,
            task_by_type=task_by_type,
            top_features=top_features,
            bug_distribution=bug_distribution,
            developer_workload=developer_workload,
            generated_at=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error ({get_db_backend()}): {str(e)}")
