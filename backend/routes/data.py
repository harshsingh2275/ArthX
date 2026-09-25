"""
ArthX Data Routes — T1.2
Exposes the ingestion and data read endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.ingestion import run_ingestion
from models.transaction import Transaction
from models.invoice import Invoice

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("/ingest")
def ingest_seed_data(db: Session = Depends(get_db)):
    """
    Idempotent ingestion endpoint. Clears all existing data and reloads
    from the seed CSV files in /data. Safe to call multiple times.
    """
    try:
        result = run_ingestion(db)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/status")
def data_status(db: Session = Depends(get_db)):
    """Returns current row counts for all data tables."""
    tx_count = db.query(Transaction).count()
    inv_count = db.query(Invoice).count()
    return {
        "transactions": tx_count,
        "invoices": inv_count,
        "data_loaded": tx_count > 0,
    }
