"""
AI usage ledger repository.

Har bir model chaqiruvi bo'yicha token va taxminiy cost yoziladi. Bu Stage 10
usage/cost tracking va Stage 12 AI usage metrics uchun poydevor.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from utils.database.repository_common import (
    execute as _execute,
)
from utils.database.repository_common import (
    row_to_dict as _row_to_dict,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_default(value: Any):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (set, tuple)):
        return list(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _dumps(value: Any) -> str:
    return json.dumps(
        value if value is not None else {},
        ensure_ascii=True,
        default=_json_default,
    )


def ensure_ai_usage_tables(conn) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_usage_events (
            id BIGSERIAL PRIMARY KEY,
            company_id BIGINT NULL,
            user_id BIGINT NULL,
            run_id TEXT NULL,
            task_key TEXT NOT NULL DEFAULT '',
            module_key TEXT NOT NULL,
            agent_key TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL,
            primary_model TEXT NOT NULL DEFAULT '',
            fallback_model TEXT NOT NULL DEFAULT '',
            used_fallback BOOLEAN NOT NULL DEFAULT FALSE,
            prompt_token_count INTEGER NOT NULL DEFAULT 0,
            candidates_token_count INTEGER NOT NULL DEFAULT 0,
            thoughts_token_count INTEGER NOT NULL DEFAULT 0,
            cached_content_token_count INTEGER NOT NULL DEFAULT 0,
            total_token_count INTEGER NOT NULL DEFAULT 0,
            billable_input_tokens INTEGER NOT NULL DEFAULT 0,
            billable_output_tokens INTEGER NOT NULL DEFAULT 0,
            billable_cached_tokens INTEGER NOT NULL DEFAULT 0,
            estimated_input_cost_usd NUMERIC(18, 8) NOT NULL DEFAULT 0,
            estimated_output_cost_usd NUMERIC(18, 8) NOT NULL DEFAULT 0,
            estimated_cached_cost_usd NUMERIC(18, 8) NOT NULL DEFAULT 0,
            estimated_total_cost_usd NUMERIC(18, 8) NOT NULL DEFAULT 0,
            pricing_tier TEXT NOT NULL DEFAULT '',
            pricing_source TEXT NOT NULL DEFAULT '',
            cost_warning BOOLEAN NOT NULL DEFAULT FALSE,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_usage_company_created ON ai_usage_events(company_id, created_at DESC)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_usage_run_id ON ai_usage_events(run_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_usage_module_created ON ai_usage_events(module_key, created_at DESC)"
    )
    conn.commit()


def record_ai_usage_event(
    conn,
    *,
    company_id: int | None,
    user_id: int | None,
    run_id: str | None,
    task_key: str,
    module_key: str,
    agent_key: str,
    source: str,
    model: str,
    primary_model: str,
    fallback_model: str,
    used_fallback: bool,
    usage: dict[str, Any],
    cost: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    now = _now_iso()
    row = _execute(
        conn,
        """
        INSERT INTO ai_usage_events (
            company_id, user_id, run_id, task_key, module_key, agent_key, source,
            model, primary_model, fallback_model, used_fallback,
            prompt_token_count, candidates_token_count, thoughts_token_count,
            cached_content_token_count, total_token_count,
            billable_input_tokens, billable_output_tokens, billable_cached_tokens,
            estimated_input_cost_usd, estimated_output_cost_usd, estimated_cached_cost_usd,
            estimated_total_cost_usd, pricing_tier, pricing_source, cost_warning,
            metadata_json, created_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?
        )
        RETURNING *
        """,
        [
            company_id,
            user_id,
            run_id or None,
            str(task_key or ""),
            str(module_key or "unknown"),
            str(agent_key or ""),
            str(source or ""),
            str(model or ""),
            str(primary_model or ""),
            str(fallback_model or ""),
            bool(used_fallback),
            int(usage.get("prompt_token_count") or 0),
            int(usage.get("candidates_token_count") or 0),
            int(usage.get("thoughts_token_count") or 0),
            int(usage.get("cached_content_token_count") or 0),
            int(usage.get("total_token_count") or 0),
            int(cost.get("billable_input_tokens") or 0),
            int(cost.get("billable_output_tokens") or 0),
            int(cost.get("billable_cached_tokens") or 0),
            float(cost.get("estimated_input_cost_usd") or 0),
            float(cost.get("estimated_output_cost_usd") or 0),
            float(cost.get("estimated_cached_cost_usd") or 0),
            float(cost.get("estimated_total_cost_usd") or 0),
            str(cost.get("pricing_tier") or ""),
            str(cost.get("pricing_source") or ""),
            bool(cost.get("cost_warning", False)),
            _dumps(metadata or {}),
            now,
        ],
    ).fetchone()
    if commit:
        conn.commit()
    return _row_to_dict(row)


def _month_bounds_utc(year_month: str | None) -> tuple[datetime, datetime]:
    if year_month:
        year_str, month_str = str(year_month).split("-", 1)
        year, month = int(year_str), int(month_str)
    else:
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end


def get_company_monthly_cost_usd(
    conn,
    company_id: int,
    year_month: str | None = None,
) -> float:
    """Kompaniyaning bitta kalendar oyidagi jami taxminiy AI xarajati (USD).

    Oy chegarasi — UTC kalendar oyi: created_at TIMESTAMPTZ va yozuvlar
    `_now_iso()` (UTC) bilan yoziladi, shuning uchun [oy boshi, keyingi oy boshi)
    intervali UTC'da olinadi — server timezone'idan qat'i nazar barqaror.
    year_month: "YYYY-MM" yoki None (joriy oy).
    """
    start, end = _month_bounds_utc(year_month)
    row = _execute(
        conn,
        """
        SELECT COALESCE(SUM(estimated_total_cost_usd), 0) AS total_cost_usd
        FROM ai_usage_events
        WHERE company_id = ? AND created_at >= ? AND created_at < ?
        """,
        [int(company_id), start, end],
    ).fetchone()
    data = _row_to_dict(row)
    return float(data.get("total_cost_usd") or 0)


def fetch_ai_usage_summary(
    conn,
    *,
    company_id: int | None = None,
    module_key: str | None = None,
) -> dict[str, Any]:
    clauses: list[str] = []
    params: list[Any] = []
    if company_id is not None:
        clauses.append("company_id = ?")
        params.append(company_id)
    if module_key:
        clauses.append("module_key = ?")
        params.append(module_key)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    row = _execute(
        conn,
        f"""
        SELECT
            COUNT(*) AS event_count,
            COALESCE(SUM(prompt_token_count), 0) AS prompt_token_count,
            COALESCE(SUM(candidates_token_count), 0) AS candidates_token_count,
            COALESCE(SUM(thoughts_token_count), 0) AS thoughts_token_count,
            COALESCE(SUM(total_token_count), 0) AS total_token_count,
            COALESCE(SUM(estimated_total_cost_usd), 0) AS estimated_total_cost_usd,
            COALESCE(SUM(CASE WHEN cost_warning THEN 1 ELSE 0 END), 0) AS cost_warning_count
        FROM ai_usage_events
        {where}
        """,
        params,
    ).fetchone()
    return _row_to_dict(row)


def fetch_ai_usage_dashboard(conn, *, limit: int = 20) -> dict[str, Any]:
    """Super Admin UI uchun AI usage dashboard payload."""
    safe_limit = max(1, min(100, int(limit or 20)))
    summary = _row_to_dict(
        _execute(
            conn,
            """
            SELECT
                COUNT(*) AS event_count,
                COALESCE(SUM(prompt_token_count), 0) AS prompt_token_count,
                COALESCE(SUM(candidates_token_count), 0) AS candidates_token_count,
                COALESCE(SUM(thoughts_token_count), 0) AS thoughts_token_count,
                COALESCE(SUM(total_token_count), 0) AS total_token_count,
                COALESCE(SUM(estimated_total_cost_usd), 0) AS estimated_total_cost_usd,
                COALESCE(SUM(CASE WHEN cost_warning THEN 1 ELSE 0 END), 0) AS cost_warning_count
            FROM ai_usage_events
            """,
        ).fetchone()
    )
    by_company = [
        _row_to_dict(row)
        for row in _execute(
            conn,
            """
            SELECT
                e.company_id,
                COALESCE(c.company_code, '') AS company_code,
                COALESCE(c.company_name, '') AS company_name,
                COUNT(*) AS event_count,
                COALESCE(SUM(e.prompt_token_count), 0) AS prompt_token_count,
                COALESCE(SUM(e.thoughts_token_count), 0) AS thoughts_token_count,
                COALESCE(SUM(e.total_token_count), 0) AS total_token_count,
                COALESCE(SUM(e.estimated_total_cost_usd), 0) AS estimated_total_cost_usd,
                COALESCE(SUM(CASE WHEN e.cost_warning THEN 1 ELSE 0 END), 0) AS cost_warning_count
            FROM ai_usage_events e
            LEFT JOIN companies c ON c.id = e.company_id
            GROUP BY e.company_id, c.company_code, c.company_name
            ORDER BY estimated_total_cost_usd DESC, event_count DESC
            LIMIT ?
            """,
            [safe_limit],
        ).fetchall()
    ]
    by_module = [
        _row_to_dict(row)
        for row in _execute(
            conn,
            """
            SELECT
                module_key,
                COUNT(*) AS event_count,
                COALESCE(SUM(prompt_token_count), 0) AS prompt_token_count,
                COALESCE(SUM(thoughts_token_count), 0) AS thoughts_token_count,
                COALESCE(SUM(total_token_count), 0) AS total_token_count,
                COALESCE(SUM(estimated_total_cost_usd), 0) AS estimated_total_cost_usd,
                COALESCE(SUM(CASE WHEN cost_warning THEN 1 ELSE 0 END), 0) AS cost_warning_count
            FROM ai_usage_events
            GROUP BY module_key
            ORDER BY estimated_total_cost_usd DESC, event_count DESC
            LIMIT ?
            """,
            [safe_limit],
        ).fetchall()
    ]
    recent_events = [
        _row_to_dict(row)
        for row in _execute(
            conn,
            """
            SELECT
                e.id,
                e.created_at,
                e.company_id,
                COALESCE(c.company_code, '') AS company_code,
                e.user_id,
                e.run_id,
                e.task_key,
                e.module_key,
                e.agent_key,
                e.source,
                e.model,
                e.prompt_token_count,
                e.candidates_token_count,
                e.thoughts_token_count,
                e.cached_content_token_count,
                e.total_token_count,
                e.estimated_total_cost_usd,
                e.pricing_tier,
                e.cost_warning
            FROM ai_usage_events e
            LEFT JOIN companies c ON c.id = e.company_id
            ORDER BY e.created_at DESC, e.id DESC
            LIMIT ?
            """,
            [safe_limit],
        ).fetchall()
    ]

    return {
        "summary": summary,
        "by_company": by_company,
        "by_module": by_module,
        "recent_events": recent_events,
    }
