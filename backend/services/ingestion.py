"""
ArthX Ingestion Service — T1.2
Loads seed CSV data (transactions.csv, invoices.csv) into the SQLite database.

Strategy: CLEAR + RELOAD (idempotent)
  - Delete all rows from derived tables first (FK order: anomalies, forecasts,
    invoice_issues, then transactions, invoices)
  - Reload fresh from the CSV files in /data
  - Re-running produces the exact same row count every time.

One service = one responsibility.
Does NOT format API responses — that belongs to the route layer.
"""

import csv
from datetime import date, datetime
from pathlib import Path
from sqlalchemy.orm import Session

from config import ROOT_DIR
from models.transaction import Transaction, TransactionType, TransactionStatus
from models.invoice import Invoice, InvoiceStatus
from models.anomaly import Anomaly
from models.forecast import Forecast
from models.invoice_issue import InvoiceIssue

DATA_DIR = ROOT_DIR / "data"


def _parse_date(val: str) -> date:
    return date.fromisoformat(val.strip())


def _parse_float(val: str) -> float:
    return round(float(val.strip()), 2)


def clear_all_tables(db: Session) -> dict:
    """
    Delete all rows from all ArthX tables in the correct FK dependency order.
    Returns a dict of {table_name: rows_deleted}.
    """
    counts = {}
    counts["anomalies"] = db.query(Anomaly).delete()
    counts["forecasts"] = db.query(Forecast).delete()
    counts["invoice_issues"] = db.query(InvoiceIssue).delete()
    counts["transactions"] = db.query(Transaction).delete()
    counts["invoices"] = db.query(Invoice).delete()
    db.commit()
    return counts


def load_transactions(db: Session) -> int:
    """Load transactions.csv into the transactions table. Returns number of rows inserted."""
    csv_path = DATA_DIR / "transactions.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"transactions.csv not found at {csv_path}")

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(Transaction(
                id=int(row["id"]),
                date=_parse_date(row["date"]),
                vendor=row["vendor"].strip(),
                category=row["category"].strip(),
                amount=_parse_float(row["amount"]),
                type=TransactionType(row["type"].strip()),
                status=TransactionStatus(row["status"].strip()),
                description=row.get("description", "").strip() or None,
            ))

    db.bulk_save_objects(rows)
    db.commit()
    return len(rows)


def load_invoices(db: Session) -> int:
    """Load invoices.csv into the invoices table. Returns number of rows inserted."""
    csv_path = DATA_DIR / "invoices.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"invoices.csv not found at {csv_path}")

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            po_ref = row.get("po_reference", "").strip()
            rows.append(Invoice(
                id=int(row["id"]),
                vendor=row["vendor"].strip(),
                amount=_parse_float(row["amount"]),
                invoice_date=_parse_date(row["invoice_date"]),
                due_date=_parse_date(row["due_date"]),
                status=InvoiceStatus(row["status"].strip()),
                po_reference=po_ref if po_ref else None,
            ))

    db.bulk_save_objects(rows)
    db.commit()
    return len(rows)


def run_ingestion(db: Session) -> dict:
    """
    Full idempotent ingestion pipeline:
    1. Clear all existing data
    2. Load transactions from CSV
    3. Load invoices from CSV
    Returns a summary dict suitable for API or CLI output.
    """
    cleared = clear_all_tables(db)
    tx_count = load_transactions(db)
    inv_count = load_invoices(db)

    return {
        "status": "success",
        "cleared": cleared,
        "loaded": {
            "transactions": tx_count,
            "invoices": inv_count,
        },
        "message": (
            f"Ingested {tx_count} transactions and {inv_count} invoices from "
            f"{DATA_DIR}. Idempotent: re-running will produce the same counts."
        ),
    }
