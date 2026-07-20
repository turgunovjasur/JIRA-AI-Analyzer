"""Landing/demo contact formasidan kelgan lidlar (contact_leads) repository.

Jadval `database/postgresql/004_contact_leads.sql` migratsiyasida yaratiladi.
"""
from __future__ import annotations

from utils.database.repository_common import execute, row_to_dict


def create_lead(
    conn,
    *,
    name: str,
    phone: str,
    role: str,
    source: str = "landing",
    note: str | None = None,
) -> dict:
    cursor = execute(
        conn,
        """
        INSERT INTO contact_leads (name, phone, role, source, note)
        VALUES (?, ?, ?, ?, ?)
        RETURNING id, name, phone, role, source, status, note, created_at
        """,
        [name, phone, role, source, note],
    )
    row = cursor.fetchone()
    conn.commit()
    return row_to_dict(row)


def list_leads(conn, *, limit: int = 50, offset: int = 0) -> dict:
    total_cur = execute(conn, "SELECT COUNT(*) AS total FROM contact_leads")
    total_row = total_cur.fetchone()
    if isinstance(total_row, dict):
        total = int(total_row.get("total") or 0)
    else:
        total = int((total_row[0] if total_row else 0) or 0)

    cursor = execute(
        conn,
        """
        SELECT id, name, phone, role, source, status, note, created_at
        FROM contact_leads
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        [int(limit), int(offset)],
    )
    leads = [row_to_dict(r) for r in cursor.fetchall()]
    return {"leads": leads, "total": total}
