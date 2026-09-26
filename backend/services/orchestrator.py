"""
ArthX Pipeline Orchestration Service — T3.1
=============================================
Unified orchestration engine that acts as the primary trigger for the ArthX platform.
Sequentially executes:
  1. Anomaly & Fraud Detection (T2.1)
  2. Invoice Validation Logic (T2.4)
  3. Cash Flow Forecasting Engine (T2.2)
  4. Forecast Impact Linking (T2.5)
  5. Explainability Generation (T2.3)

All results are persisted to the database so that subsequent dashboard reads
(GET /api/anomalies, GET /api/forecast, GET /api/invoices/issues)
fetch instantaneously (<1s) without re-running ML models.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from models.anomaly import Anomaly
from models.transaction import Transaction
from services.analysis import run_analysis, get_stored_anomalies, FLAG_THRESHOLD
from services.invoice_validation import run_invoice_validation_pipeline, get_stored_invoice_issues
from services.forecast import run_forecast_pipeline, get_stored_forecast
from services.explanation import run_explanation_pipeline
from ml.impact_linker import compute_forecast_impacts

logger = logging.getLogger(__name__)


def run_orchestrated_pipeline(
    db: Session,
    run_explainer: bool = True,
    horizon_days: int = 30,
) -> Dict[str, Any]:
    """
    Executes the full ArthX analytics pipeline in sequence:
      1. Anomaly Detection (T2.1) -> persists to 'anomalies', flags transactions
      2. Invoice Validation (T2.4) -> persists to 'invoice_issues'
      3. Forecasting Engine (T2.2) -> persists 30-day forecast to 'forecasts'
      4. Impact Linking (T2.5) -> computes forecast delta excluding each flagged outflow
      5. Explainability (T2.3) -> generates data-grounded explanations for anomalies and forecast

    Idempotent and safe to re-run at any time.
    """
    t_start = time.perf_counter()
    timings: Dict[str, float] = {}

    # ── Step 1: Anomaly Detection (T2.1) ─────────────────────────────────────
    logger.info("[T3.1 Pipeline] Step 1: Running Anomaly Detection...")
    t0 = time.perf_counter()
    anomaly_result = run_analysis(db)
    timings["anomaly_detection_s"] = round(time.perf_counter() - t0, 3)

    # ── Step 2: Invoice Validation (T2.4) ────────────────────────────────────
    logger.info("[T3.1 Pipeline] Step 2: Running Invoice Validation...")
    t0 = time.perf_counter()
    invoice_result = run_invoice_validation_pipeline(db)
    timings["invoice_validation_s"] = round(time.perf_counter() - t0, 3)

    # ── Step 3: Cash Flow Forecasting (T2.2) ─────────────────────────────────
    logger.info("[T3.1 Pipeline] Step 3: Running Cash Flow Forecasting...")
    t0 = time.perf_counter()
    forecast_result = run_forecast_pipeline(db, horizon_days=horizon_days)
    timings["forecasting_s"] = round(time.perf_counter() - t0, 3)

    # ── Step 4: Impact Linking (T2.5) ────────────────────────────────────────
    logger.info("[T3.1 Pipeline] Step 4: Computing Forecast Impact Linking...")
    t0 = time.perf_counter()
    all_transactions = db.query(Transaction).all()
    flagged_anomalies = (
        db.query(Anomaly)
        .filter(Anomaly.risk_score >= FLAG_THRESHOLD)
        .all()
    )
    flagged_tx_ids = [a.transaction_id for a in flagged_anomalies]

    impacts = compute_forecast_impacts(
        transactions=all_transactions,
        flagged_transaction_ids=flagged_tx_ids,
        horizon_days=horizon_days,
    )

    # Update impact_on_30d_forecast column on anomaly rows
    for anomaly in flagged_anomalies:
        if anomaly.transaction_id in impacts:
            anomaly.impact_on_30d_forecast = impacts[anomaly.transaction_id]

    db.commit()
    timings["impact_linking_s"] = round(time.perf_counter() - t0, 3)

    # ── Step 5: Explainability Engine (T2.3) ─────────────────────────────────
    explanation_result = {"status": "skipped"}
    if run_explainer:
        logger.info("[T3.1 Pipeline] Step 5: Generating Grounded Explanations...")
        t0 = time.perf_counter()
        explanation_result = run_explanation_pipeline(db, overwrite=True)
        timings["explanation_s"] = round(time.perf_counter() - t0, 3)
    else:
        timings["explanation_s"] = 0.0

    total_pipeline_time = round(time.perf_counter() - t_start, 3)
    timings["total_pipeline_s"] = total_pipeline_time

    # ── Step 6: Assemble Comprehensive Unified Contract ─────────────────────
    # Pull fresh anomalies (including generated explanation and impact)
    fresh_anomalies = get_stored_anomalies(db)

    # Build response: strictly preserves fields expected by T2.1 / T2.2 evaluators
    # while adding rich dashboard-ready payloads for invoices, forecast, and impact.
    return {
        "status": "success",
        "pipeline_version": "1.0",
        "total_anomalies_detected": len(fresh_anomalies),
        "flagged_transactions": anomaly_result.get("flagged_transactions", len(flagged_tx_ids)),
        "flag_threshold": FLAG_THRESHOLD,
        "anomalies": fresh_anomalies,
        "invoices": {
            "total_scanned": invoice_result.get("total_invoices_scanned", 0),
            "total_issues": invoice_result.get("total_issues_found", 0),
            "duplicate_count": invoice_result.get("duplicate_count", 0),
            "missing_po_count": invoice_result.get("missing_po_count", 0),
        },
        "forecast": {
            "horizon_days": forecast_result.get("horizon_days", horizon_days),
            "method": forecast_result.get("method"),
            "trend_summary": (
                db.query(Anomaly).first()  # check DB forecast trend summary
                and get_stored_forecast(db).get("trend_summary")
                or forecast_result.get("trend_summary", "")
            ),
            "points_count": len(forecast_result.get("forecast", [])),
        },
        "impact_linking": {
            "evaluated_anomalies": len(flagged_tx_ids),
            "impacts_computed": len(impacts),
        },
        "explanations": explanation_result,
        "timings": timings,
    }
