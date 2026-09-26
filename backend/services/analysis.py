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
from typing import List, Dict, Any, Optional

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


def _reset_all_transaction_statuses(db: Session) -> None:
    """
    Reset all transaction statuses to 'normal' before a fresh detection run,
    so stale flags from previous runs don't persist when the data changes.
    """
    db.query(Transaction).update({"status": TransactionStatus.NORMAL}, synchronize_session=False)
    db.commit()


def run_analysis(db: Session) -> Dict[str, Any]:
    """
    Full analysis pipeline (idempotent — safe to re-run):
      1. Clear previous anomaly records
      2. Reset all transaction statuses to normal
      3. Run detection engine against current DB state
      4. Persist each anomaly result
      5. Flag transactions with risk_score >= FLAG_THRESHOLD in bulk
      6. Return summary dict for the API response
    """
    # Step 1: Clear stale anomaly records
    _clear_anomalies(db)

    # Step 2: Reset transaction statuses
    _reset_all_transaction_statuses(db)

    # Step 3: Run detection (pure, no DB side effects)
    results: List[AnomalyResult] = run_detection(db)

    # Steps 4 & 5: Persist anomalies and bulk update flagged transaction statuses
    flagged_ids = []
    for result in results:
        _persist_anomaly(db, result)
        if result.risk_score >= FLAG_THRESHOLD:
            flagged_ids.append(result.transaction_id)

    flagged_count = len(flagged_ids)
    if flagged_ids:
        db.query(Transaction).filter(Transaction.id.in_(flagged_ids)).update(
            {"status": TransactionStatus.FLAGGED},
            synchronize_session=False,
        )

    db.commit()

    # Build response
    return {
        "status": "success",
        "total_anomalies_detected": len(results),
        "flagged_transactions": flagged_count,
        "flag_threshold": FLAG_THRESHOLD,
        "anomalies": [r.to_contract() for r in results],
    }


def get_stored_anomalies(
    db: Session,
    min_risk: Optional[float] = None,
    vendor: Optional[str] = None,
    reason_code: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Retrieve persisted anomaly records from the DB, ordered by risk_score desc.
    Supports optional filtering by min_risk, vendor, reason_code, and pagination.
    """
    query = db.query(Anomaly)

    if min_risk is not None:
        query = query.filter(Anomaly.risk_score >= min_risk)
    if vendor:
        query = query.filter(Anomaly.vendor.ilike(f"%{vendor.strip()}%"))
    if reason_code:
        query = query.filter(Anomaly.reason_code == reason_code.strip())

    query = query.order_by(Anomaly.risk_score.desc(), Anomaly.id.asc())

    if offset > 0:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    rows = query.all()
    return [row.to_dict() for row in rows]
