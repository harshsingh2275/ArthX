"""
ArthX Analysis Routes — T2.1 / T2.3 / T3.1
Exposes:
  POST /api/analysis/run       — Unified pipeline: detection, invoices, forecast, impact linking, explainability
  GET  /api/analysis/anomalies — List persisted anomalies
  GET  /api/anomalies          — List persisted anomalies (T3.2 specification alias)
  POST /api/analysis/explain   — Regenerate LLM explanations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from services.analysis import get_stored_anomalies
from services.explanation import run_explanation_pipeline
from services.orchestrator import run_orchestrated_pipeline

router = APIRouter(tags=["analysis"])


@router.post("/api/analysis/run")
def run_analysis_endpoint(
    run_explainer: bool = Query(
        default=True,
        description="Whether to run LLM explainability generation for results",
    ),
    horizon_days: int = Query(
        default=30,
        ge=7,
        le=90,
        description="Cash flow forecast horizon in days",
    ),
    db: Session = Depends(get_db),
):
    """
    T3.1 — Master pipeline orchestration endpoint:
      1. Anomaly & fraud detection (T2.1)
      2. Invoice validation (T2.4)
      3. Cash flow forecasting (T2.2)
      4. Forecast impact linking (T2.5)
      5. Grounded explainability generation (T2.3)

    Persists all computed outputs to the database.
    Subsequent GET queries to dashboard endpoints return instantaneously (<1s).
    """
    try:
        result = run_orchestrated_pipeline(
            db=db,
            run_explainer=run_explainer,
            horizon_days=horizon_days,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orchestration pipeline failed: {str(e)}")


@router.get("/api/analysis/anomalies")
@router.get("/api/anomalies")
def list_anomalies(db: Session = Depends(get_db)):
    """
    T3.2 — Return persisted anomaly records from the DB, ordered by risk_score descending.
    Includes explanation and impact_on_30d_forecast.
    """
    return get_stored_anomalies(db)


@router.post("/api/analysis/explain")
def run_explain_endpoint(
    overwrite: bool = Query(
        default=True,
        description="If false, skip anomalies/forecasts that already have explanations.",
    ),
    db: Session = Depends(get_db),
):
    """
    T2.3 — Standalone trigger for generating LLM explanations.
    """
    try:
        result = run_explanation_pipeline(db, overwrite=overwrite)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explanation pipeline failed: {str(e)}")
