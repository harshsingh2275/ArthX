"""
ArthX Transactions Service — T1.3
Handles data access and filtering queries for transactions.
Single-purpose functions following repository conventions.
"""

from datetime import date
from typing import List, Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session

from models.transaction import Transaction


def get_transactions(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    vendor: Optional[str] = None,
    status: Optional[str] = None,
    transaction_type: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Transaction]:
    """
    Retrieve transactions with optional filtering:
    - start_date / end_date: inclusive date range on transaction date
    - vendor: case-insensitive partial match
    - status: match transaction status (normal, flagged, reviewed)
    - transaction_type: match type (inflow, outflow)
    - category: case-insensitive partial match
    - limit / offset: pagination controls
    """
    query = db.query(Transaction)

    if start_date is not None:
        query = query.filter(Transaction.date >= start_date)
    if end_date is not None:
        query = query.filter(Transaction.date <= end_date)
    if vendor:
        query = query.filter(Transaction.vendor.ilike(f"%{vendor.strip()}%"))
    if status:
        query = query.filter(Transaction.status == status.strip().lower())
    if transaction_type:
        query = query.filter(Transaction.type == transaction_type.strip().lower())
    if category:
        query = query.filter(Transaction.category.ilike(f"%{category.strip()}%"))

    # Order by date descending, then id descending
    query = query.order_by(desc(Transaction.date), desc(Transaction.id))

    if offset > 0:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    return query.all()
