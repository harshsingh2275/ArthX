"""
ArthX Forecast Impact Linking — T2.5

Computes the impact of flagged outflow anomalies on the 30-day cash flow forecast:
For each flagged anomaly of type outflow, recomputes the forecast excluding that
transaction and determines the delta in projected net cash flow over the horizon.

Pure computation logic (no direct DB writes).
"""

from typing import Dict, List, Optional, Sequence
from datetime import date
from models.transaction import Transaction, TransactionType
from ml.forecaster import run_forecast, ForecastResult


def compute_forecast_impacts(
    transactions: Sequence[Transaction],
    flagged_transaction_ids: Sequence[int],
    horizon_days: int = 30,
) -> Dict[int, float]:
    """
    For each flagged outflow transaction, recompute the forecast without it
    and calculate:
        delta = (forecast_without_tx.net_flow_sum) - (base_forecast.net_flow_sum)

    A positive delta indicates that excluding the anomaly improves (increases)
    the projected net cash flow (i.e., eliminates an anomalous outflow).

    Returns:
        Dict mapping transaction_id -> delta (float rounded to 2 decimal places).
    """
    if not transactions or not flagged_transaction_ids:
        return {}

    # 1. Base forecast with all transactions
    base_result: ForecastResult = run_forecast(list(transactions), horizon_days=horizon_days)
    base_total = sum(p.predicted_net_flow for p in base_result.forecast)

    tx_map = {t.id: t for t in transactions}
    impacts: Dict[int, float] = {}

    for tx_id in flagged_transaction_ids:
        tx = tx_map.get(tx_id)
        if not tx:
            continue

        # Only compute impact for outflow transactions (anomalous expenses/withdrawals)
        is_outflow = (
            tx.type == TransactionType.OUTFLOW
            or (hasattr(tx.type, "value") and tx.type.value == "outflow")
            or str(tx.type).lower() == "outflow"
        )
        if not is_outflow:
            continue

        # Build transaction list excluding this single transaction
        subset = [t for t in transactions if t.id != tx_id]

        try:
            ex_result: ForecastResult = run_forecast(subset, horizon_days=horizon_days)
            ex_total = sum(p.predicted_net_flow for p in ex_result.forecast)
            delta = round(ex_total - base_total, 2)
            impacts[tx_id] = delta
        except Exception:
            # If recomputation fails for any reason, skip gracefully
            continue

    return impacts
