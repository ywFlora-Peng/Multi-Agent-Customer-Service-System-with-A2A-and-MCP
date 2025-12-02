"""
MCP server exposing customer & ticket tools for the A2A assignment.

- Uses FastMCP (official Python MCP SDK).
- Serves via Streamable HTTP so it supports tools/list and tools/call.
- Backs all tools with a SQLite database created by `database_setup.py`.

Test with MCP Inspector by connecting to:
    http://localhost:8000/mcp
"""

# mcp_server.py

import sqlite3
from datetime import datetime
from typing import Any, Dict, List

# NOTE: DB_PATH must match the path used in database_setup.py
DB_PATH = "support.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Tool 1: Get Customer
def get_customer(customer_id: int) -> Dict[str, Any]:
    """Fetch a single customer by ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, email, phone, status FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if row is None:
            return {"found": False, "customer": None}
        return {"found": True, "customer": dict(row)}

# Tool 2: List Customers
def list_customers(status: str = "active", limit: int = 20) -> List[Dict[str, Any]]:
    """List customers filtered by status ('active', 'disabled')."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, email, phone, status FROM customers WHERE status = ? ORDER BY id LIMIT ?",
            (status, limit),
        ).fetchall()
        return [dict(r) for r in rows]

# Tool 3: Update Customer
def update_customer(customer_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a customer record (name, email, phone, status)."""
    if not data:
        return {"updated": False, "reason": "No fields provided"}
    allowed_fields = {"name", "email", "phone", "status"}
    fields = [k for k in data.keys() if k in allowed_fields]
    if not fields:
        return {"updated": False, "reason": "No valid fields in data"}
    set_clause = ", ".join(f"{f} = ?" for f in fields)
    values = [data[f] for f in fields]
    with get_connection() as conn:
        cur = conn.execute(
            f"UPDATE customers SET {set_clause}, updated_at = ? WHERE id = ?",
            (*values, datetime.utcnow().isoformat(), customer_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return {"updated": False, "reason": "Customer not found"}
        return {"updated": True, "customer_id": customer_id, "updated_fields": fields}

# Tool 4: Create Ticket
def create_ticket(
    customer_id: int,
    issue: str,
    priority: str = "medium",
) -> Dict[str, Any]:
    """Create a support ticket."""
    if priority not in {"low", "medium", "high"}:
        return {"created": False, "reason": "Invalid priority"}
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if row is None:
            return {"created": False, "reason": "Customer not found"}
        cur = conn.execute(
            """
            INSERT INTO tickets (customer_id, issue, status, priority, created_at)
            VALUES (?, ?, 'open', ?, ?)
            """,
            (customer_id, issue, priority, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return {"created": True, "ticket_id": cur.lastrowid, "priority": priority}

# Tool 5: Get Customer History
def get_customer_history(customer_id: int) -> Dict[str, Any]:
    """Return all tickets for a given customer as their support history."""
    with get_connection() as conn:
        cust = conn.execute(
            "SELECT id, name, status FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if cust is None:
            return {"found": False, "customer": None, "tickets": []}
        rows = conn.execute(
            "SELECT id, issue, status, priority, created_at FROM tickets WHERE customer_id = ? ORDER BY created_at DESC",
            (customer_id,),
        ).fetchall()
        return {
            "found": True,
            "customer": dict(cust),
            "tickets": [dict(r) for r in rows],
        }

if __name__ == "__main__":
    # Optional: Run a FastMCP server here if needed for testing, but typically 
    # the functions are just imported by the Data Agent.
    print("MCP tools defined. Run the agents directly.")