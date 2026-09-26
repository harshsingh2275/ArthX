"""
ArthX Analysis Routes — T2.1 / T2.3 / T3.1
Exposes:
  POST /api/analysis/run       — Unified pipeline: detection, invoices, forecast, impact linking, explainability
  GET  /api/analysis/anomalies — List persisted anomalies
  GET  /api/anomalies          — List persisted anomalies (T3.2 specification alias)
  POST /api/analysis/explain   — Regenerate LLM explanations
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.anomaly import AnomalyResponse
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


@router.get("/api/analysis/anomalies", response_model=List[AnomalyResponse])
@router.get("/api/anomalies", response_model=List[AnomalyResponse])
@router.get("/api/anomalies/", response_model=List[AnomalyResponse], include_in_schema=False)
def list_anomalies(
    min_risk: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum risk score (0.0 - 1.0)"),
    vendor: Optional[str] = Query(None, description="Filter by vendor name (case-insensitive substring)"),
    reason_code: Optional[str] = Query(None, description="Filter by reason code"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    db: Session = Depends(get_db),
):
    """
    T3.2 — Return persisted anomaly records from the DB, ordered by risk_score descending.
    Includes risk_score, reason_code, trigger_metric, explanation, and impact_on_30d_forecast.
    """
    return get_stored_anomalies(
        db=db,
        min_risk=min_risk,
        vendor=vendor,
        reason_code=reason_code,
        limit=limit,
        offset=offset,
    )


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
