"""
ArthX Analysis Service — T2.1
Orchestrates anomaly detection: runs the detector, persists results to the
anomalies table, and updates transaction status to 'flagged' for high-risk hits.

Single-responsibility:
  - anomaly_detector.py:  pure detection logic (no DB writes)
  - analysis.py (this):   persistence + transaction status update
  - routes/analysis.py:   HTTP routing / response formatting
"""

from datetime import date
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from ml.anomaly_detector import run_detection, AnomalyResult
from models.anomaly import Anomaly
from models.transaction import Transaction, TransactionStatus


# Risk score threshold above which a transaction is marked 'flagged' in the DB
FLAG_THRESHOLD: float = 0.50


def _clear_anomalies(db: Session) -> int:
    """Remove all existing anomaly records. Returns count deleted."""
    count = db.query(Anomaly).delete()
    db.commit()
    return count


def _persist_anomaly(db: Session, result: AnomalyResult) -> Anomaly:
    """Insert a single AnomalyResult as an Anomaly row."""
    record = Anomaly(
        transaction_id=result.transaction_id,
        vendor=result.vendor,
        amount=result.amount,
        risk_score=result.risk_score,
        reason_code=result.primary_reason_code,
        trigger_metric=result.trigger_metric,
        # explanation populated later by T2.4 LLM layer
        explanation=None,
        impact_on_30d_forecast=None,
    )
    db.add(record)
    return record


def _update_transaction_status(
    db: Session,
    result: AnomalyResult,
) -> None:
    """
    Mark a transaction as 'flagged' if risk_score >= FLAG_THRESHOLD,
    and 'normal' otherwise (resets stale flags on re-run).
    """
    tx = db.query(Transaction).filter(Transaction.id == result.transaction_id).first()
    if tx is None:
        return
    if result.risk_score >= FLAG_THRESHOLD:
        tx.status = TransactionStatus.FLAGGED
    # We do not downgrade here — only set flagged in this function


def _reset_all_transaction_statuses(db: Session) -> None:
    """
    Reset all transaction statuses to 'normal' before a fresh detection run,
    so stale flags from previous runs don't persist when the data changes.
    """
    db.query(Transaction).update({"status": TransactionStatus.NORMAL})
    db.commit()


def run_analysis(db: Session) -> Dict[str, Any]:
    """
    Full analysis pipeline (idempotent — safe to re-run):
      1. Clear previous anomaly records
      2. Reset all transaction statuses to normal
      3. Run detection engine against current DB state
      4. Persist each anomaly result
      5. Flag transactions with risk_score >= FLAG_THRESHOLD
      6. Return summary dict for the API response
    """
    # Step 1: Clear stale anomaly records
    _clear_anomalies(db)

    # Step 2: Reset transaction statuses
    _reset_all_transaction_statuses(db)

    # Step 3: Run detection (pure, no DB side effects)
    results: List[AnomalyResult] = run_detection(db)

    # Steps 4 & 5: Persist and flag
    flagged_count = 0
    for result in results:
        _persist_anomaly(db, result)
        if result.risk_score >= FLAG_THRESHOLD:
            _update_transaction_status(db, result)
            flagged_count += 1

    db.commit()

    # Build response
    return {
        "status": "success",
        "total_anomalies_detected": len(results),
        "flagged_transactions": flagged_count,
        "flag_threshold": FLAG_THRESHOLD,
        "anomalies": [r.to_contract() for r in results],
    }


def get_stored_anomalies(db: Session) -> List[Dict[str, Any]]:
    """Retrieve persisted anomaly records from the DB, ordered by risk_score desc."""
    rows = (
        db.query(Anomaly)
        .order_by(Anomaly.risk_score.desc())
        .all()
    )
    return [row.to_dict() for row in rows]
