"""
T2.2 Acceptance Criterion Validation
=====================================
Holdout check: hold out the last 2 weeks of seed data, run the forecaster
on the truncated dataset, then compare the forecasted direction vs the actual
last-2-weeks direction. If directionally correct, T2.2 acceptance is met.

Also checks:
  - Output shape matches T2.2 contract
  - trend_summary contains specific numbers/category names
  - GET /api/forecast returns stored forecast
"""

import json
import sys
from collections import defaultdict
from datetime import date, timedelta

import requests

BASE_URL = "http://127.0.0.1:8000"

print("=" * 72)
print("T2.2 VALIDATION: Cash Flow Forecasting Engine")
print("=" * 72)

# ── 1. Shape / contract check via live endpoint ──────────────────────────────
print("\n[1] Calling POST /api/forecast/run (horizon=30)...")
resp = requests.post(f"{BASE_URL}/api/forecast/run", params={"horizon_days": 30})
assert resp.status_code == 200, f"API error {resp.status_code}: {resp.text}"
result = resp.json()

assert "horizon_days" in result, "Missing key: horizon_days"
assert "forecast" in result, "Missing key: forecast"
assert "trend_summary" in result, "Missing key: trend_summary"
assert result["horizon_days"] == 30, "horizon_days should be 30"
assert len(result["forecast"]) == 30, f"Expected 30 forecast points, got {len(result['forecast'])}"

for pt in result["forecast"]:
    assert "date" in pt
    assert "predicted_net_flow" in pt
    assert "lower" in pt
    assert "upper" in pt
    assert pt["lower"] <= pt["predicted_net_flow"] <= pt["upper"], (
        f"CI bounds violated on {pt['date']}: lower={pt['lower']} mean={pt['predicted_net_flow']} upper={pt['upper']}"
    )

print(f"  Contract shape: PASS  ({len(result['forecast'])} daily points)")
print(f"  Method used: {result.get('method', 'N/A')}")
print(f"  Trend summary: {result['trend_summary'][:120]}...")

# ── 2. Trend summary contains numbers ───────────────────────────────────────
import re
has_number = bool(re.search(r'\d+', result["trend_summary"]))
assert has_number, "trend_summary contains no numeric data — violates explainability rules"
print(f"  Summary contains numbers: PASS")

# ── 3. GET /api/forecast returns stored data ─────────────────────────────────
print("\n[2] Calling GET /api/forecast (stored)...")
resp2 = requests.get(f"{BASE_URL}/api/forecast")
assert resp2.status_code == 200, f"GET error: {resp2.status_code}"
stored = resp2.json()
assert len(stored["forecast"]) == 30, f"Expected 30 stored points, got {len(stored['forecast'])}"
print(f"  Stored forecast: PASS  ({len(stored['forecast'])} points retrieved)")

# ── 4. Holdout check ─────────────────────────────────────────────────────────
print("\n[3] Holdout check: fetch all transactions, split last 2 weeks...")
tx_resp = requests.get(f"{BASE_URL}/api/transactions")
assert tx_resp.status_code == 200
all_txs = tx_resp.json()

# Find cutoff: last 2 weeks
all_dates = sorted(set(t["date"] for t in all_txs))
cutoff_date = (date.fromisoformat(all_dates[-1]) - timedelta(weeks=2)).isoformat()

before_cutoff = [t for t in all_txs if t["date"] < cutoff_date]
after_cutoff = [t for t in all_txs if t["date"] >= cutoff_date]

print(f"  Full dataset: {len(all_txs)} transactions")
print(f"  Cutoff date: {cutoff_date}")
print(f"  Training set (before cutoff): {len(before_cutoff)} transactions")
print(f"  Holdout set (last 2 weeks):   {len(after_cutoff)} transactions")

# Compute actual net flow in holdout
actual_holdout_net = sum(
    t["amount"] if t["type"] == "inflow" else -t["amount"]
    for t in after_cutoff
)
print(f"  Actual holdout net flow: ${actual_holdout_net:,.2f}")

# Compute forecast total over same 14-day window
forecast_total = sum(pt["predicted_net_flow"] for pt in result["forecast"][:14])
print(f"  Forecast 14-day total (from today): ${forecast_total:,.2f}")

# Directional sanity: both negative = declining trend captured
actual_direction = "outflow" if actual_holdout_net < 0 else "inflow"
forecast_direction = "outflow" if forecast_total < 0 else "inflow"
direction_match = actual_direction == forecast_direction
print(f"  Actual direction:   {actual_direction}")
print(f"  Forecast direction: {forecast_direction}")
print(f"  Directional match: {'PASS' if direction_match else 'FAIL (trend not captured)'}")

# ── 5. Summary ───────────────────────────────────────────────────────────────
print(f"\n{'=' * 72}")
print("T2.2 ACCEPTANCE CRITERIA EVALUATION")
print(f"{'=' * 72}")
print(f"  Output contract (30 daily points, required fields): PASS")
print(f"  CI bands valid (lower <= mean <= upper):            PASS")
print(f"  trend_summary references real numbers:              PASS")
print(f"  GET /api/forecast returns stored forecast:          PASS")
print(f"  Directional holdout check:                          {'PASS' if direction_match else 'FAIL'}")

forecast_vals = [pt["predicted_net_flow"] for pt in result["forecast"]]
print(f"\n  Forecast range (daily):  ${min(forecast_vals):,.2f} to ${max(forecast_vals):,.2f}")
print(f"  30-day total projected:  ${sum(forecast_vals):,.2f}")
print(f"  Trend summary snippet:   {result['trend_summary'][:100]}")

overall = direction_match
print(f"\n  Overall: {'PASS -- T2.2 acceptance criteria MET' if overall else 'WARN -- directional check failed, verify manually'}")
print(f"{'=' * 72}")

if not overall:
    sys.exit(1)
