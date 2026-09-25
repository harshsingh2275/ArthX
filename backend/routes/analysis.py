"""
ArthX Analysis Routes — T2.1
Exposes POST /api/analysis/run and GET /api/analysis/anomalies.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.analysis import run_analysis, get_stored_anomalies

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/run")
def run_analysis_endpoint(db: Session = Depends(get_db)):
    """
    Run the anomaly detection engine against the current database state.
    Idempotent: clears previous results, resets transaction statuses, and
    recomputes everything fresh. Returns the full set of detected anomalies
    and a summary.
    """
    try:
        result = run_analysis(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/anomalies")
def list_anomalies(db: Session = Depends(get_db)):
    """
    Return the persisted anomaly records from the last analysis run,
    ordered by risk_score descending.
    """
    return get_stored_anomalies(db)
