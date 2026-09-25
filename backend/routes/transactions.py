"""
ArthX Transactions Routes — T1.3
Provides GET /api/transactions with date range, vendor, and status filtering.
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.transaction import TransactionResponse
from services.transactions import get_transactions

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=List[TransactionResponse])
@router.get("/", response_model=List[TransactionResponse], include_in_schema=False)
def list_transactions(
    start_date: Optional[date] = Query(None, description="Filter transactions on or after this date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter transactions on or before this date (YYYY-MM-DD)"),
    vendor: Optional[str] = Query(None, description="Filter by vendor name (case-insensitive substring)"),
    status: Optional[str] = Query(None, description="Filter by status (normal, flagged, reviewed)"),
    type: Optional[str] = Query(None, description="Filter by type (inflow, outflow)"),
    category: Optional[str] = Query(None, description="Filter by category (case-insensitive substring)"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    db: Session = Depends(get_db),
):
    """
    Retrieve financial transactions with optional filtering by:
    - Date range (`start_date`, `end_date`)
    - `vendor`
    - `status`
    - `type` (inflow/outflow)
    - `category`
    """
    return get_transactions(
        db=db,
        start_date=start_date,
        end_date=end_date,
        vendor=vendor,
        status=status,
        transaction_type=type,
        category=category,
        limit=limit,
        offset=offset,
    )
