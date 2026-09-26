"""
ArthX Invoice Validation Service — T2.4

Orchestrates invoice audit validation rules:
  1. Runs pure validation engine (ml/invoice_validator.py)
  2. Persists detected issues to the invoice_issues table
  3. Provides querying capabilities for API endpoints and dashboard consumption
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.invoice import Invoice
from models.invoice_issue import InvoiceIssue
from ml.invoice_validator import (
    run_invoice_validation,
    InvoiceValidationIssue,
    InvoiceIssueType,
    DUPLICATE_WINDOW_DAYS,
)


def clear_invoice_issues(db: Session) -> int:
    """Clear all existing invoice issue records. Returns count of deleted records."""
    count = db.query(InvoiceIssue).delete()
    db.commit()
    return count


def persist_invoice_issues(
    db: Session,
    issues: List[InvoiceValidationIssue],
) -> List[InvoiceIssue]:
    """Persist a list of validation issues into the invoice_issues table."""
    records = []
    for issue in issues:
        record = InvoiceIssue(
            invoice_id=issue.invoice_id,
            vendor=issue.vendor,
            amount=issue.amount,
            issue_type=issue.issue_type,
            detail=issue.detail,
        )
        db.add(record)
        records.append(record)

    db.commit()
    return records


def run_invoice_validation_pipeline(
    db: Session,
    window_days: int = DUPLICATE_WINDOW_DAYS,
) -> Dict[str, Any]:
    """
    Full invoice validation pipeline (idempotent — safe to re-run):
      1. Load all invoices from database
      2. Run duplicate and missing PO detection
      3. Clear stale invoice issue records
      4. Persist newly detected issues
      5. Return summary contract
    """
    invoices = db.query(Invoice).order_by(Invoice.invoice_date.asc(), Invoice.id.asc()).all()
    issues: List[InvoiceValidationIssue] = run_invoice_validation(
        invoices=invoices,
        window_days=window_days,
    )

    # Clear previous issues and persist fresh results
    clear_invoice_issues(db)
    persist_invoice_issues(db, issues)

    # Compute metrics
    duplicate_count = sum(
        1 for i in issues if i.issue_type == InvoiceIssueType.DUPLICATE_INVOICE.value
    )
    missing_po_count = sum(
        1 for i in issues
        if i.issue_type in (InvoiceIssueType.MISSING_PO_REFERENCE.value, "MISSING_PO")
    )

    return {
        "status": "success",
        "total_invoices_scanned": len(invoices),
        "total_issues_found": len(issues),
        "duplicate_count": duplicate_count,
        "missing_po_count": missing_po_count,
        "issues": [i.to_contract() for i in issues],
    }


def get_stored_invoice_issues(
    db: Session,
    issue_type: Optional[str] = None,
    invoice_id: Optional[int] = None,
    vendor: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Retrieve persisted invoice issues from the DB with optional filtering.
    """
    query = db.query(InvoiceIssue)

    if issue_type:
        clean_type = issue_type.strip().upper()
        if clean_type in ("MISSING_PO", "MISSING_PO_REFERENCE"):
            query = query.filter(InvoiceIssue.issue_type.in_(["MISSING_PO", "MISSING_PO_REFERENCE"]))
        else:
            query = query.filter(InvoiceIssue.issue_type == clean_type)

    if invoice_id is not None:
        query = query.filter(InvoiceIssue.invoice_id == invoice_id)

    if vendor:
        query = query.filter(InvoiceIssue.vendor.ilike(f"%{vendor.strip()}%"))

    query = query.order_by(InvoiceIssue.invoice_id.asc(), InvoiceIssue.issue_type.asc())

    if offset > 0:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    rows = query.all()
    return [row.to_dict() for row in rows]
