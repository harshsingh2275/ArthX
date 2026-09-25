"""
ArthX Analysis Routes — T2.1 / T2.3
Exposes:
  POST /api/analysis/run      — anomaly detection
  GET  /api/analysis/anomalies — list stored anomalies
  POST /api/analysis/explain  — generate/update LLM explanations (T2.3)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from services.analysis import run_analysis, get_stored_anomalies
from services.explanation import run_explanation_pipeline

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


@router.post("/explain")
def run_explain_endpoint(
    overwrite: bool = Query(
        default=True,
        description="If false, skip anomalies/forecasts that already have explanations.",
    ),
    db: Session = Depends(get_db),
):
    """
    T2.3 — Generate LLM-powered explanations for all stored anomalies and the
    current forecast, then persist them to the DB.

    - Updates anomalies.explanation for every row in the anomalies table.
    - Updates forecasts.trend_summary for every row in the forecasts table.
    - Idempotent when overwrite=false (skips already-explained rows).
    - Falls back to a deterministic template if the Gemini API is unavailable.
    """
    try:
        result = run_explanation_pipeline(db, overwrite=overwrite)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explanation pipeline failed: {str(e)}")
