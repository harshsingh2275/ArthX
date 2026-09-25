"""
ArthX Invoices Service — T1.3
Handles data access and filtering queries for invoices.
Single-purpose functions following repository conventions.
"""

from datetime import date
from typing import List, Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session

from models.invoice import Invoice


def get_invoices(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    vendor: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Invoice]:
    """
    Retrieve invoices with optional filtering:
    - start_date / end_date: inclusive date range on invoice_date
    - vendor: case-insensitive partial match
    - status: match invoice status (paid, pending, disputed)
    - limit / offset: pagination controls
    """
    query = db.query(Invoice)

    if start_date is not None:
        query = query.filter(Invoice.invoice_date >= start_date)
    if end_date is not None:
        query = query.filter(Invoice.invoice_date <= end_date)
    if vendor:
        query = query.filter(Invoice.vendor.ilike(f"%{vendor.strip()}%"))
    if status:
        query = query.filter(Invoice.status == status.strip().lower())

    # Order by invoice_date descending, then id descending
    query = query.order_by(desc(Invoice.invoice_date), desc(Invoice.id))

    if offset > 0:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    return query.all()
