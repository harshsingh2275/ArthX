"""
ArthX Invoices Routes — T1.3
Provides GET /api/invoices with date range, vendor, and status filtering.
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.invoice import (
    InvoiceResponse,
    InvoiceIssueResponse,
    InvoiceValidationSummary,
)
from services.invoices import get_invoices
from services.invoice_validation import (
    run_invoice_validation_pipeline,
    get_stored_invoice_issues,
)

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("", response_model=List[InvoiceResponse])
@router.get("/", response_model=List[InvoiceResponse], include_in_schema=False)
def list_invoices(
    start_date: Optional[date] = Query(None, description="Filter invoices on or after this date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter invoices on or before this date (YYYY-MM-DD)"),
    vendor: Optional[str] = Query(None, description="Filter by vendor name (case-insensitive substring)"),
    status: Optional[str] = Query(None, description="Filter by status (paid, pending, disputed)"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    db: Session = Depends(get_db),
):
    """
    Retrieve invoices with optional filtering by:
    - Date range (`start_date`, `end_date`)
    - `vendor`
    - `status`
    """
    return get_invoices(
        db=db,
        start_date=start_date,
        end_date=end_date,
        vendor=vendor,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post("/validate", response_model=InvoiceValidationSummary)
def validate_invoices_endpoint(
    window_days: int = Query(7, ge=1, le=30, description="Window in days for duplicate invoice detection"),
    db: Session = Depends(get_db),
):
    """
    T2.4 — Execute automated invoice validation rules:
      1. Duplicate detection: same vendor + amount within window_days (default 7 days)
      2. Missing PO reference flag

    Clears and persists flagged issues into the invoice_issues table.
    Returns structured output contract with all flagged issues.
    """
    try:
        result = run_invoice_validation_pipeline(db=db, window_days=window_days)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invoice validation failed: {str(e)}")


@router.get("/issues", response_model=List[InvoiceIssueResponse])
def list_invoice_issues(
    issue_type: Optional[str] = Query(None, description="Filter by issue type: DUPLICATE_INVOICE or MISSING_PO_REFERENCE"),
    invoice_id: Optional[int] = Query(None, description="Filter by invoice ID"),
    vendor: Optional[str] = Query(None, description="Filter by vendor name (case-insensitive substring)"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    db: Session = Depends(get_db),
):
    """
    T3.2 / T2.4 — Retrieve stored invoice issues from the DB.
    """
    return get_stored_invoice_issues(
        db=db,
        issue_type=issue_type,
        invoice_id=invoice_id,
        vendor=vendor,
        limit=limit,
        offset=offset,
    )
