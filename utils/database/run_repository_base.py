"""
Run repository'lar uchun umumiy parametrlangan baza.

`checker_run_repository` va `analysis_run_repository` bir xil run/agent/event
strukturasini ikki jadval to'plamida saqlaydi — farq faqat jadval nomlari,
`module_key` ustuni va yakuniy status matnida. Shu farqlar `RunTablesConfig`
orqali beriladi, SQL/serializatsiya logikasi bitta joyda turadi.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from utils.database.repository_common import (
    execute as _execute,
)
from utils.database.repository_common import (
    row_to_dict as _row_to_dict,
)


@dataclass(frozen=True)
class RunTablesConfig:
    runs_table: str
    agent_runs_table: str
    events_table: str
    index_prefix: str
    has_module_key: bool
    failed_status_message: str


def _resolve_execute(execute):
    # Wrapper modullar o'z `_execute` globalini uzatadi — testlar uni monkeypatch qiladi.
    return execute if execute is not None else _execute


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


def _loads(raw: Any, default: Any):
    if raw in (None, ""):
        return default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return default


def ensure_run_tables(conn, cfg: RunTablesConfig) -> None:
    module_key_line = "module_key TEXT NOT NULL," if cfg.has_module_key else ""
    state_index_columns = ("module_key, " if cfg.has_module_key else "") + "run_state, updated_at"
    cursor = conn.cursor()
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {cfg.runs_table} (
            run_id TEXT PRIMARY KEY,
            {module_key_line}
            task_key TEXT NOT NULL,
            company_id BIGINT NULL,
            user_id BIGINT NULL,
            source TEXT NOT NULL,
            execution_mode TEXT NOT NULL,
            run_state TEXT NOT NULL,
            active_phase TEXT NULL,
            status_message TEXT NULL,
            requested_output_profile TEXT NOT NULL,
            request_payload_json TEXT NOT NULL DEFAULT '{{}}',
            final_result_json TEXT NULL,
            error_message TEXT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            started_at TIMESTAMPTZ NULL,
            finished_at TIMESTAMPTZ NULL
        )
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {cfg.agent_runs_table} (
            id BIGSERIAL PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES {cfg.runs_table}(run_id) ON DELETE CASCADE,
            agent_key TEXT NOT NULL,
            agent_label TEXT NOT NULL,
            agent_order INTEGER NOT NULL,
            state TEXT NOT NULL,
            primary_model TEXT NULL,
            actual_model TEXT NULL,
            fallback_model TEXT NULL,
            used_fallback BOOLEAN NOT NULL DEFAULT FALSE,
            attempts INTEGER NOT NULL DEFAULT 0,
            confidence DOUBLE PRECISION NULL,
            input_summary TEXT NULL,
            output_summary TEXT NULL,
            error_text TEXT NULL,
            warnings_json TEXT NOT NULL DEFAULT '[]',
            artifact_json TEXT NOT NULL DEFAULT '{{}}',
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL,
            started_at TIMESTAMPTZ NULL,
            finished_at TIMESTAMPTZ NULL
        )
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {cfg.events_table} (
            id BIGSERIAL PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES {cfg.runs_table}(run_id) ON DELETE CASCADE,
            agent_key TEXT NULL,
            level TEXT NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL,
            meta_json TEXT NOT NULL DEFAULT '{{}}',
            created_at TIMESTAMPTZ NOT NULL
        )
        """
    )

    cursor.execute(
        f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{cfg.index_prefix}_agent_runs_unique "
        f"ON {cfg.agent_runs_table}(run_id, agent_key)"
    )
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{cfg.index_prefix}_runs_state "
        f"ON {cfg.runs_table}({state_index_columns})"
    )
    cursor.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{cfg.index_prefix}_events_run_id "
        f"ON {cfg.events_table}(run_id, id)"
    )
    conn.commit()


def create_run(
    conn,
    cfg: RunTablesConfig,
    *,
    run_id: str,
    task_key: str,
    company_id: int | None,
    user_id: int | None,
    source: str,
    execution_mode: str,
    requested_output_profile: str,
    request_payload: dict[str, Any],
    module_key: str | None = None,
    commit: bool = True,
    execute=None,
) -> dict[str, Any]:
    run_execute = _resolve_execute(execute)
    now = _now_iso()
    payload_json = _dumps(request_payload)
    module_column = "module_key, " if cfg.has_module_key else ""
    module_placeholder = "?, " if cfg.has_module_key else ""
    module_params = [module_key] if cfg.has_module_key else []
    row = run_execute(
        conn,
        f"""
        INSERT INTO {cfg.runs_table} (
            run_id, {module_column}task_key, company_id, user_id, source, execution_mode,
            run_state, active_phase, status_message, requested_output_profile,
            request_payload_json, final_result_json, error_message,
            created_at, updated_at, started_at, finished_at
        )
        VALUES (?, {module_placeholder}?, ?, ?, ?, ?, 'queued', 'queued', 'Run yaratildi',
                ?, ?, NULL, NULL, ?, ?, NULL, NULL)
        RETURNING *
        """,
        [
            run_id,
            *module_params,
            task_key,
            company_id,
            user_id,
            source,
            execution_mode,
            requested_output_profile,
            payload_json,
            now,
            now,
        ],
    ).fetchone()
    if commit:
        conn.commit()
    return _deserialize_run_row(_row_to_dict(row))


def seed_agent_runs(
    conn,
    cfg: RunTablesConfig,
    *,
    run_id: str,
    agents: list[dict[str, Any]],
    commit: bool = True,
    execute=None,
) -> None:
    run_execute = _resolve_execute(execute)
    now = _now_iso()
    for item in agents:
        used_fallback = bool(item.get("used_fallback", False))
        attempts = int(item.get("attempts") or 0)
        run_execute(
            conn,
            f"""
            INSERT INTO {cfg.agent_runs_table} (
                run_id, agent_key, agent_label, agent_order, state,
                primary_model, actual_model, fallback_model, used_fallback,
                attempts, confidence, input_summary, output_summary, error_text,
                warnings_json, artifact_json, created_at, updated_at, started_at, finished_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, '[]', '{{}}', ?, ?, NULL, NULL)
            """,
            [
                run_id,
                str(item.get("agent_key") or ""),
                str(item.get("agent_label") or ""),
                int(item.get("agent_order") or 0),
                str(item.get("state") or "pending"),
                str(item.get("primary_model") or ""),
                None,
                str(item.get("fallback_model") or ""),
                used_fallback,
                attempts,
                now,
                now,
            ],
        )
    if commit:
        conn.commit()


def update_run(
    conn, cfg: RunTablesConfig, run_id: str, *, execute=None, **fields: Any
) -> dict[str, Any] | None:
    run_execute = _resolve_execute(execute)
    if not fields:
        return get_run(conn, cfg, run_id, execute=run_execute)
    now = _now_iso()
    field_map = dict(fields)
    field_map["updated_at"] = now
    columns = ", ".join(f"{key} = ?" for key in field_map)
    params = [field_map[key] for key in field_map]
    params.append(run_id)
    run_execute(
        conn,
        f"UPDATE {cfg.runs_table} SET {columns} WHERE run_id = ?",
        params,
    )
    conn.commit()
    return get_run(conn, cfg, run_id, execute=run_execute)


def update_agent_run(
    conn,
    cfg: RunTablesConfig,
    run_id: str,
    agent_key: str,
    execute=None,
    **fields: Any,
) -> dict[str, Any] | None:
    run_execute = _resolve_execute(execute)
    if not fields:
        return get_agent_run(conn, cfg, run_id, agent_key, execute=run_execute)
    now = _now_iso()
    field_map = dict(fields)
    field_map["updated_at"] = now
    if "warnings_json" in field_map and not isinstance(field_map["warnings_json"], str):
        field_map["warnings_json"] = _dumps(field_map["warnings_json"])
    if "artifact_json" in field_map and not isinstance(field_map["artifact_json"], str):
        field_map["artifact_json"] = _dumps(field_map["artifact_json"])
    columns = ", ".join(f"{key} = ?" for key in field_map)
    params = [field_map[key] for key in field_map]
    params.extend([run_id, agent_key])
    run_execute(
        conn,
        f"UPDATE {cfg.agent_runs_table} SET {columns} WHERE run_id = ? AND agent_key = ?",
        params,
    )
    conn.commit()
    return get_agent_run(conn, cfg, run_id, agent_key, execute=run_execute)


def append_run_event(
    conn,
    cfg: RunTablesConfig,
    *,
    run_id: str,
    level: str,
    event_type: str,
    message: str,
    agent_key: str | None = None,
    meta: dict[str, Any] | None = None,
    commit: bool = True,
    execute=None,
) -> dict[str, Any]:
    run_execute = _resolve_execute(execute)
    now = _now_iso()
    meta_json = _dumps(meta or {})
    row = run_execute(
        conn,
        f"""
        INSERT INTO {cfg.events_table} (
            run_id, agent_key, level, event_type, message, meta_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        RETURNING *
        """,
        [run_id, agent_key, level, event_type, message, meta_json, now],
    ).fetchone()
    if commit:
        conn.commit()
    return _deserialize_event_row(_row_to_dict(row))


def save_run_final_result(
    conn,
    cfg: RunTablesConfig,
    run_id: str,
    *,
    run_state: str,
    final_result: dict[str, Any] | None,
    error_message: str | None = None,
    execute=None,
) -> dict[str, Any] | None:
    return update_run(
        conn,
        cfg,
        run_id,
        execute=execute,
        run_state=run_state,
        active_phase="finished",
        status_message="Run yakunlandi" if run_state == "completed" else cfg.failed_status_message,
        final_result_json=_dumps(final_result or {}),
        error_message=error_message,
        finished_at=_now_iso(),
    )


def get_run(conn, cfg: RunTablesConfig, run_id: str, *, execute=None) -> dict[str, Any] | None:
    row = _resolve_execute(execute)(
        conn,
        f"SELECT * FROM {cfg.runs_table} WHERE run_id = ? LIMIT 1",
        [run_id],
    ).fetchone()
    if not row:
        return None
    return _deserialize_run_row(_row_to_dict(row))


def get_agent_run(
    conn, cfg: RunTablesConfig, run_id: str, agent_key: str, *, execute=None
) -> dict[str, Any] | None:
    row = _resolve_execute(execute)(
        conn,
        f"""
        SELECT * FROM {cfg.agent_runs_table}
        WHERE run_id = ? AND agent_key = ?
        LIMIT 1
        """,
        [run_id, agent_key],
    ).fetchone()
    if not row:
        return None
    return _deserialize_agent_row(_row_to_dict(row))


def list_agent_runs(conn, cfg: RunTablesConfig, run_id: str, *, execute=None) -> list[dict[str, Any]]:
    rows = _resolve_execute(execute)(
        conn,
        f"""
        SELECT * FROM {cfg.agent_runs_table}
        WHERE run_id = ?
        ORDER BY agent_order ASC, id ASC
        """,
        [run_id],
    ).fetchall()
    return [_deserialize_agent_row(_row_to_dict(row)) for row in rows]


def list_run_events(conn, cfg: RunTablesConfig, run_id: str, *, execute=None) -> list[dict[str, Any]]:
    rows = _resolve_execute(execute)(
        conn,
        f"""
        SELECT * FROM {cfg.events_table}
        WHERE run_id = ?
        ORDER BY id ASC
        """,
        [run_id],
    ).fetchall()
    return [_deserialize_event_row(_row_to_dict(row)) for row in rows]


def build_run_snapshot(
    conn, cfg: RunTablesConfig, run_id: str, *, execute=None
) -> dict[str, Any] | None:
    run = get_run(conn, cfg, run_id, execute=execute)
    if not run:
        return None
    return {
        **run,
        "agent_runs": list_agent_runs(conn, cfg, run_id, execute=execute),
        "run_events": list_run_events(conn, cfg, run_id, execute=execute),
        "final_result": run.get("final_result"),
    }


def _deserialize_run_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    payload["request_payload"] = _loads(payload.pop("request_payload_json", None), {})
    payload["final_result"] = _loads(payload.pop("final_result_json", None), None)
    return payload


def _deserialize_agent_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    payload["used_fallback"] = bool(payload.get("used_fallback"))
    payload["warnings"] = _loads(payload.pop("warnings_json", None), [])
    payload["artifact"] = _loads(payload.pop("artifact_json", None), {})
    return payload


def _deserialize_event_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    payload["meta"] = _loads(payload.pop("meta_json", None), {})
    return payload
