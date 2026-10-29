import json
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "voizgger.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    summary TEXT,
    items TEXT,
    quantity TEXT,
    amount_paid REAL DEFAULT 0,
    amount_owed REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS usage (
    day TEXT PRIMARY KEY,
    count INTEGER NOT NULL DEFAULT 0
)
"""


def _connect() -> sqlite3.Connection:
    path = Path(os.environ.get("VOIZGGER_DB", DB_PATH))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _row_to_invoice(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "date": row["created_at"],
        "summary": row["summary"] or "",
        "items": json.loads(row["items"] or "[]"),
        "quantity": json.loads(row["quantity"] or "[]"),
        "amount_paid": row["amount_paid"] or 0,
        "amount_owed": row["amount_owed"] or 0,
    }


def list_invoices(limit: int = 25) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM invoices ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_invoice(row) for row in rows]


def add_invoice(invoice: dict) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO invoices
                (id, created_at, summary, items, quantity, amount_paid, amount_owed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice["id"],
                invoice["date"],
                invoice.get("summary", ""),
                json.dumps(invoice.get("items", [])),
                json.dumps(invoice.get("quantity", [])),
                float(invoice.get("amount_paid") or 0),
                float(invoice.get("amount_owed") or 0),
            ),
        )


def delete_all_invoices() -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM invoices")
