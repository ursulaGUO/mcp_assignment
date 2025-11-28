import asyncio
import logging
import os
from typing import List, Dict, Any
import sqlite3
from fastmcp import FastMCP
from datetime import datetime

from database_setup import DatabaseSetup  

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

# Cloud Run writable path
DATABASE = DatabaseSetup("/tmp/support.db")
DATABASE.connect()
cursor = DATABASE.cursor

mcp = FastMCP("Customer Database MCP")


@mcp.tool()
def get_customer(customer_id: int):
    """
    Retrieve a customer by ID.
    """

    cursor.execute("""
        SELECT id, name, email, phone, status, created_at, updated_at
        FROM customers 
        WHERE id = ?
    """, (customer_id,))

    row = cursor.fetchone()
    if row is None:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "phone": row[3],
        "status": row[4],
        "created_at": row[5],
        "updated_at": row[6],
    }


@mcp.tool()
def list_customers(status: str, limit: int = 10):
    """
    List customers filtered by status.
    """

    cursor.execute("""
        SELECT id, name, email, phone, status, created_at, updated_at
        FROM customers
        WHERE status = ?
        LIMIT ?
    """, (status, limit))

    rows = cursor.fetchall()
    result = []

    for row in rows:
        result.append({
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "phone": row[3],
            "status": row[4],
            "created_at": row[5],
            "updated_at": row[6],
        })

    return result



@mcp.tool()
def update_customer(customer_id: int, field_name: str, field_value: Any):
    """
    Update a customer field.
    """

    if field_name == "id":
        return {"error": "Cannot update ID field."}

    if field_name not in ["name", "email", "phone", "status"]:
        return {"error": "Invalid field name."}

    if field_name == "status" and field_value not in ["active", "disabled"]:
        return {"error": "Invalid status value."}

    # Build dynamic query safely
    query = f"UPDATE customers SET {field_name} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
    cursor.execute(query, (field_value, customer_id))
    DATABASE.conn.commit()

    return {"success": True, "message": f"Customer {customer_id} updated."}


@mcp.tool()
def create_ticket(customer_id: int, issue: str, priority: str):
    """
    Create a new ticket for a customer.
    """

    if priority not in ["low", "medium", "high"]:
        return {"error": "Invalid priority."}

    cursor.execute("""
        INSERT INTO tickets (customer_id, issue, priority)
        VALUES (?, ?, ?)
    """, (customer_id, issue, priority))

    DATABASE.conn.commit()

    ticket_id = cursor.lastrowid

    # Return new ticket object
    cursor.execute("""
        SELECT id, customer_id, issue, status, priority, created_at
        FROM tickets
        WHERE id = ?
    """, (ticket_id,))

    row = cursor.fetchone()

    return {
        "id": row[0],
        "customer_id": row[1],
        "issue": row[2],
        "status": row[3],
        "priority": row[4],
        "created_at": row[5],
    }



@mcp.tool()
def get_customer_history(customer_id: int):
    """
    Return all tickets belonging to a specific customer.
    """

    cursor.execute("""
        SELECT id, customer_id, issue, status, priority, created_at
        FROM tickets
        WHERE customer_id = ?
        ORDER BY created_at DESC
    """, (customer_id,))

    rows = cursor.fetchall()

    history = []
    for row in rows:
        history.append({
            "id": row[0],
            "customer_id": row[1],
            "issue": row[2],
            "status": row[3],
            "priority": row[4],
            "created_at": row[5],
        })

    return history


if __name__ == "__main__":

    # 1. Initialize SQLite BEFORE starting MCP
    setup = DatabaseSetup("/tmp/support.db")
    setup.connect()
    setup.create_tables()
    setup.create_triggers()
    setup.insert_sample_data()      # (optional for demo)
    print("[Sqlite DB] Initialized inside Cloud Run container.")

    # 2. Start MCP server
    port = int(os.getenv("PORT", 8080))
    asyncio.run(
        mcp.run_async(
            transport="http",
            host="0.0.0.0",
            port=port,
            path="/mcp"
        )
    )
