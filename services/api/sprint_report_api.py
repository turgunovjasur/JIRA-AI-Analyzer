"""
Sprint Report API - FastAPI endpoints for sprint analytics

Author: JASUR TURGUNOV
Version: 1.0
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import sqlite3
import os

router = APIRouter(prefix="/api", tags=["sprint-report"])

DB_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'utils', 'data', 'processing.db'
)


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
async def get_sprint_report(
    days: int = Query(default=7, ge=1, le=365, description="Period in days"),
    limit: int = Query(default=10, ge=1, le=100, description="Top features limit")
):
    """
    Sprint report with task statistics.

    Returns:
    - Task counts by type (product, client, bug, error, analiz)
    - Top features with breakdown
    - Bug/error distribution by feature
    - Developer workload statistics
    """
    if not os.path.exists(DB_FILE):
        raise HTTPException(status_code=404, detail="Database not found")

    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # 1. Total tasks
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM task_processing
            WHERE created_at >= ?
        """, (cutoff_date,))
        total_tasks = cursor.fetchone()['total']

        # 2. Task by type
        cursor.execute("""
            SELECT
                COALESCE(task_type, 'other') as task_type,
                COUNT(*) as count
            FROM task_processing
            WHERE created_at >= ?
            GROUP BY task_type
            ORDER BY count DESC
        """, (cutoff_date,))

        task_by_type = [
            TaskTypeStats(
                task_type=row['task_type'],
                count=row['count'],
                percentage=round(row['count'] / total_tasks * 100, 2) if total_tasks > 0 else 0
            )
            for row in cursor.fetchall()
        ]

        # 3. Top features
        cursor.execute("""
            SELECT
                COALESCE(feature_name, 'unknown') as feature_name,
                COUNT(*) as total_tasks,
                SUM(CASE WHEN task_type = 'product' THEN 1 ELSE 0 END) as product,
                SUM(CASE WHEN task_type = 'client' THEN 1 ELSE 0 END) as client,
                SUM(CASE WHEN task_type = 'bug' THEN 1 ELSE 0 END) as bug,
                SUM(CASE WHEN task_type = 'error' THEN 1 ELSE 0 END) as error,
                SUM(CASE WHEN task_type = 'analiz' THEN 1 ELSE 0 END) as analiz,
                SUM(CASE WHEN task_type NOT IN ('product','client','bug','error','analiz')
                    OR task_type IS NULL THEN 1 ELSE 0 END) as other
            FROM task_processing
            WHERE created_at >= ?
              AND feature_name IS NOT NULL
              AND feature_name != ''
            GROUP BY feature_name
            ORDER BY total_tasks DESC
            LIMIT ?
        """, (cutoff_date, limit))

        top_features = [FeatureStats(**dict(row)) for row in cursor.fetchall()]

        # 4. Bug distribution
        cursor.execute("""
            SELECT
                COALESCE(feature_name, 'unknown') as feature_name,
                SUM(CASE WHEN task_type = 'bug' THEN 1 ELSE 0 END) as bug_count,
                SUM(CASE WHEN task_type = 'error' THEN 1 ELSE 0 END) as error_count,
                SUM(CASE WHEN task_type IN ('bug', 'error') THEN 1 ELSE 0 END) as total
            FROM task_processing
            WHERE created_at >= ?
              AND feature_name IS NOT NULL
              AND task_type IN ('bug', 'error')
            GROUP BY feature_name
            ORDER BY total DESC
        """, (cutoff_date,))

        bug_distribution = [BugDistribution(**dict(row)) for row in cursor.fetchall()]

        # 5. Developer workload
        cursor.execute("""
            SELECT
                COALESCE(assignee, 'Unassigned') as assignee,
                COUNT(*) as total_tasks,
                SUM(CASE WHEN task_status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN task_status = 'progressing' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN task_status = 'returned' THEN 1 ELSE 0 END) as returned,
                AVG(compliance_score) as avg_compliance_score
            FROM task_processing
            WHERE created_at >= ?
              AND assignee IS NOT NULL
            GROUP BY assignee
            ORDER BY total_tasks DESC
        """, (cutoff_date,))

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
            for row in cursor.fetchall()
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
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
