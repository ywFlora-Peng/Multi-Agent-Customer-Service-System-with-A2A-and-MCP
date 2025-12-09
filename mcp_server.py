# mcp_server.py  —— FastMCP HTTP ver customer/ticket MCP server

import sqlite3
from datetime import datetime
from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP

DB_PATH = "support.db"

mcp = FastMCP(
    "customer_support_mcp",
    stateless_http=True,
    json_response=True, 
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {k: row[k] for k in row.keys()}


@mcp.tool()
def get_customer(customer_id: int) -> Dict[str, Any]:
    """Return a single customer record by ID."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()

    if row is None:
        return {"found": False, "customer": None}

    return {"found": True, "customer": _row_to_dict(row)}


@mcp.tool()
def list_customers(status: str = "active", limit: int = 20) -> Dict[str, Any]:
    """List customers filtered by status (active/disabled)."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM customers
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (status, limit),
        ).fetchall()

    return {
        "status": status,
        "count": len(rows),
        "customers": [_row_to_dict(r) for r in rows],
    }


@mcp.tool()
def update_customer(customer_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update basic customer fields like name/email/phone/status."""
    if not data:
        return {"ok": False, "message": "No fields to update."}

    allowed = {"name", "email", "phone", "status"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return {"ok": False, "message": "No valid fields to update."}

    set_clause = ", ".join(f"{col} = ?" for col in updates.keys())
    values: List[Any] = list(updates.values())
    values.append(datetime.utcnow().isoformat())
    values.append(customer_id)

    with _connect() as conn:
        cur = conn.execute(
            f"""
            UPDATE customers
            SET {set_clause}, updated_at = ?
            WHERE id = ?
            """,
            values,
        )
        conn.commit()

        if cur.rowcount == 0:
            return {"ok": False, "message": f"Customer {customer_id} not found."}

        row = conn.execute(
            "SELECT * FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()

    return {"ok": True, "customer": _row_to_dict(row)}


@mcp.tool()
def create_ticket(customer_id: int, issue: str, priority: str = "medium") -> Dict[str, Any]:
    """Create a new ticket for the customer."""
    if priority not in {"low", "medium", "high"}:
        return {"ok": False, "message": f"Invalid priority: {priority}"}

    now = datetime.utcnow().isoformat()

    with _connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()
        if exists is None:
            return {"ok": False, "message": f"Customer {customer_id} not found."}

        cur = conn.execute(
            """
            INSERT INTO tickets (customer_id, issue, status, priority, created_at)
            VALUES (?, ?, 'open', ?, ?)
            """,
            (customer_id, issue, priority, now),
        )
        ticket_id = cur.lastrowid
        conn.commit()

        row = conn.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

    return {"ok": True, "ticket": _row_to_dict(row)}


@mcp.tool()
def get_customer_history(customer_id: int) -> Dict[str, Any]:
    """Return customer profile + ticket history."""
    with _connect() as conn:
        cust = conn.execute(
            "SELECT * FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()
        if cust is None:
            return {"found": False, "customer": None, "tickets": []}

        rows = conn.execute(
            """
            SELECT * FROM tickets
            WHERE customer_id = ?
            ORDER BY created_at DESC
            """,
            (customer_id,),
        ).fetchall()

    return {
        "found": True,
        "customer": _row_to_dict(cust),
        "tickets": [_row_to_dict(r) for r in rows],
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
