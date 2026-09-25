"""
ArthX Invoices Routes — T1.3
Provides GET /api/invoices with date range, vendor, and status filtering.
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.invoice import InvoiceResponse
from services.invoices import get_invoices

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
