"""
ArthX Forecast Service — T2.2
==============================
Orchestrates cash flow forecasting:
  - forecast.py (ml):      pure forecasting logic (no DB writes)
  - forecast.py (this):    DB persistence + response formatting
  - routes/forecast.py:    HTTP routing

Single-responsibility boundary:
  ml/forecaster.py  → no DB access, pure pandas/statsmodels
  services/forecast.py → DB read/write, calls ml layer
"""

from datetime import date
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ml.forecaster import run_forecast, ForecastResult
from models.forecast import Forecast
from models.transaction import Transaction


def _clear_forecasts(db: Session) -> int:
    """Delete all existing forecast rows. Returns count deleted."""
    count = db.query(Forecast).delete()
    db.commit()
    return count


def _persist_forecast(db: Session, result: ForecastResult) -> None:
    """
    Persist each daily ForecastPoint as a Forecast row.
    Also stores trend_summary on every row (denormalised for simple retrieval).
    """
    for point in result.forecast:
        row = Forecast(
            date=point.date,
            predicted_net_flow=round(point.predicted_net_flow, 2),
            lower=round(point.lower, 2),
            upper=round(point.upper, 2),
            horizon_days=result.horizon_days,
            trend_summary=result.trend_summary,
        )
        db.add(row)
    db.commit()


def run_forecast_pipeline(db: Session, horizon_days: int = 30) -> Dict[str, Any]:
    """
    Full forecast pipeline (idempotent — safe to re-run):
      1. Load all transactions from DB
      2. Run forecasting engine (ETS or WMA fallback)
      3. Clear old forecast rows
      4. Persist new forecast points
      5. Return output matching the T2.2 contract

    Returns:
        {
            "horizon_days": 30,
            "forecast": [...daily points...],
            "trend_summary": "...",
            "method": "ETS" | "WMA_TREND",
        }
    """
    transactions = db.query(Transaction).all()

    result: ForecastResult = run_forecast(transactions, horizon_days=horizon_days)

    # Idempotent: replace old rows
    _clear_forecasts(db)
    _persist_forecast(db, result)

    return {
        "horizon_days": result.horizon_days,
        "forecast": [
            {
                "date": p.date.isoformat(),
                "predicted_net_flow": p.predicted_net_flow,
                "lower": p.lower,
                "upper": p.upper,
            }
            for p in result.forecast
        ],
        "trend_summary": result.trend_summary,
        "method": result.method,
    }


def get_stored_forecast(db: Session) -> Dict[str, Any]:
    """
    Return the latest persisted forecast, ordered by date.
    Returns the T2.2 contract shape, or an empty forecast if none exists.
    """
    rows = db.query(Forecast).order_by(Forecast.date.asc()).all()

    if not rows:
        return {
            "horizon_days": 0,
            "forecast": [],
            "trend_summary": "No forecast has been run yet. Call POST /api/forecast/run first.",
            "method": None,
        }

    trend_summary = rows[0].trend_summary or ""
    horizon_days = rows[0].horizon_days

    return {
        "horizon_days": horizon_days,
        "forecast": [
            {
                "date": r.date.isoformat(),
                "predicted_net_flow": r.predicted_net_flow,
                "lower": r.lower,
                "upper": r.upper,
            }
            for r in rows
        ],
        "trend_summary": trend_summary,
        "method": None,   # method not stored separately; available on fresh run
    }
