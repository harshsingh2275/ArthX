"""
ArthX Forecast Routes — T2.2
Exposes POST /api/forecast/run and GET /api/forecast.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.forecast import ForecastResponse
from services.forecast import run_forecast_pipeline, get_stored_forecast

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.post("/run", response_model=ForecastResponse)
def run_forecast_endpoint(
    horizon_days: int = Query(default=30, ge=7, le=90, description="Forecast horizon in days"),
    db: Session = Depends(get_db),
):
    """
    Run the cash flow forecasting engine against the current transaction data.
    Idempotent: replaces any previously stored forecast.
    Returns forecast in the T2.2 contract shape.
    """
    try:
        result = run_forecast_pipeline(db, horizon_days=horizon_days)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast failed: {str(e)}")


@router.get("", response_model=ForecastResponse)
@router.get("/", response_model=ForecastResponse, include_in_schema=False)
def get_forecast_endpoint(db: Session = Depends(get_db)):
    """
    T3.2 — Return the latest stored forecast (from the last run), ordered by date.
    Returns forecast points with confidence bands and the analytical trend_summary.
    """
    return get_stored_forecast(db)
