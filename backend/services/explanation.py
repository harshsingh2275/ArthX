"""
ArthX Explanation Service — T2.3
===================================
DB persistence layer for the explainability engine.

Responsibilities:
  - Fetch stored anomaly rows and attach LLM-generated explanations
    to the `anomalies.explanation` column.
  - Fetch stored forecast rows and update `forecasts.trend_summary`
    with an LLM-generated narrative (if the stored summary is plain/empty).
  - Expose `run_explanation_pipeline()` — idempotent, safe to re-run.

Architectural boundary:
  ml/explainer.py  → pure LLM logic, no DB access
  services/explanation.py (this) → DB reads/writes, calls ML layer
  routes/analysis.py            → HTTP endpoint
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ml.explainer import generate_explanation
from models.anomaly import Anomaly
from models.forecast import Forecast

logger = logging.getLogger(__name__)


# ── Anomaly explanations ─────────────────────────────────────────────────────

def _anomaly_to_input_dict(anomaly: Anomaly) -> Dict[str, Any]:
    """
    Build the structured-JSON dict that is passed to generate_explanation().
    Matches the T2.1 anomaly output contract — only real field values, no invented data.
    """
    return {
        "transaction_id": anomaly.transaction_id,
        "vendor": anomaly.vendor,
        "amount": anomaly.amount,
        "risk_score": anomaly.risk_score,
        "reason_code": anomaly.reason_code,
        "trigger_metric": anomaly.trigger_metric,
    }


def explain_anomalies(db: Session, overwrite: bool = True) -> Dict[str, Any]:
    """
    Generate and persist explanations for all stored anomaly rows.

    Args:
        db: Active SQLAlchemy session.
        overwrite: If True, regenerate even if explanation already exists.
                   Set False to skip already-explained rows (cheap re-run).

    Returns:
        Summary dict: {total, explained, skipped, failed}
    """
    anomalies: List[Anomaly] = (
        db.query(Anomaly).order_by(Anomaly.risk_score.desc()).all()
    )

    explained = 0
    skipped = 0
    failed = 0

    for anomaly in anomalies:
        if not overwrite and anomaly.explanation:
            skipped += 1
            continue

        input_dict = _anomaly_to_input_dict(anomaly)
        try:
            explanation = generate_explanation(input_dict)
            if not explanation:
                raise ValueError("generate_explanation returned empty string")
            anomaly.explanation = explanation
            explained += 1
            logger.info(
                "Anomaly %d (tx %d, %s): explanation generated.",
                anomaly.id,
                anomaly.transaction_id,
                anomaly.vendor,
            )
        except Exception as exc:
            logger.error(
                "Failed to explain anomaly %d: %s", anomaly.id, exc
            )
            # Store a minimal fallback so the column is never NULL/blank
            anomaly.explanation = (
                f"Transaction flagged for {anomaly.reason_code}: "
                f"{anomaly.trigger_metric} (vendor: {anomaly.vendor})."
            )
            failed += 1

    db.commit()
    return {
        "total": len(anomalies),
        "explained": explained,
        "skipped": skipped,
        "failed": failed,
    }


# ── Forecast trend_summary ───────────────────────────────────────────────────

def _build_forecast_input_dict(rows: List[Forecast]) -> Dict[str, Any]:
    """
    Build a compact forecast summary dict for the LLM prompt.
    We send the aggregate picture (horizon, first/last predicted flow, trend_summary)
    rather than all 30 daily rows — keeps the prompt concise.
    """
    first = rows[0]
    last = rows[-1]
    return {
        "horizon_days": first.horizon_days,
        "trend_summary": first.trend_summary or "",
        "forecast_start": {
            "date": first.date.isoformat() if first.date else None,
            "predicted_net_flow": first.predicted_net_flow,
            "lower": first.lower,
            "upper": first.upper,
        },
        "forecast_end": {
            "date": last.date.isoformat() if last.date else None,
            "predicted_net_flow": last.predicted_net_flow,
            "lower": last.lower,
            "upper": last.upper,
        },
        "total_forecast_days": len(rows),
    }


def explain_forecast(db: Session, overwrite: bool = True) -> Dict[str, Any]:
    """
    Generate an LLM narrative for the stored forecast and write it back to
    `forecasts.trend_summary` on all rows (denormalised storage pattern from T2.2).

    Args:
        db: Active SQLAlchemy session.
        overwrite: If True, regenerate even if trend_summary is already populated.

    Returns:
        Summary dict: {rows_updated, explanation_source}
    """
    rows: List[Forecast] = db.query(Forecast).order_by(Forecast.date.asc()).all()

    if not rows:
        return {"rows_updated": 0, "explanation_source": "no_data"}

    existing_summary = rows[0].trend_summary or ""

    if not overwrite and existing_summary:
        return {"rows_updated": 0, "explanation_source": "skipped_existing"}

    input_dict = _build_forecast_input_dict(rows)
    try:
        narrative = generate_explanation(input_dict)
        if not narrative:
            raise ValueError("generate_explanation returned empty string")
        source = "llm"
    except Exception as exc:
        logger.error("Failed to generate forecast explanation: %s", exc)
        narrative = existing_summary or (
            f"The {rows[0].horizon_days}-day forecast projects net cash flows "
            f"from {rows[0].predicted_net_flow:,.0f} to {rows[-1].predicted_net_flow:,.0f}."
        )
        source = "fallback"

    # Write the narrative back to every forecast row (denormalised)
    db.query(Forecast).update({"trend_summary": narrative}, synchronize_session=False)
    db.commit()

    logger.info(
        "Forecast trend_summary updated on %d rows (source=%s).", len(rows), source
    )
    return {"rows_updated": len(rows), "explanation_source": source}


# ── Orchestrator ─────────────────────────────────────────────────────────────

def run_explanation_pipeline(
    db: Session,
    overwrite: bool = True,
) -> Dict[str, Any]:
    """
    Run the full T2.3 explanation pipeline:
      1. Explain all stored anomalies (updates anomalies.explanation)
      2. Explain the stored forecast (updates forecasts.trend_summary)

    Idempotent when overwrite=False — only fills NULL / blank explanations.

    Returns:
        Combined summary dict for the API response.
    """
    anomaly_summary = explain_anomalies(db, overwrite=overwrite)
    forecast_summary = explain_forecast(db, overwrite=overwrite)

    return {
        "status": "success",
        "anomalies": anomaly_summary,
        "forecast": forecast_summary,
    }
