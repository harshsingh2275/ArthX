"""
T3.1 Acceptance Criterion Evaluation Script
============================================
Evaluates the master orchestration endpoint POST /api/analysis/run:
  1. Triggering sequential pipeline:
     - Anomaly detection (T2.1)
     - Invoice validation (T2.4)
     - Cash flow forecasting (T2.2)
     - Forecast impact linking (T2.5)
     - Explainability generation (T2.3)
  2. Data persistence across all tables:
     - anomalies (with explanations and forecast impacts)
     - forecasts (with 30 daily points and trend_summary)
     - invoice_issues (with duplicates and missing PO flags)
  3. Latency of subsequent GET requests:
     - GET /api/anomalies (<1s)
     - GET /api/forecast (<1s)
     - GET /api/invoices/issues (<1s)
"""

import sys
import time
import requests
from pathlib import Path

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

print("=" * 76)
print("T3.1 EVALUATION: Master Pipeline Orchestration & Read Latency")
print("=" * 76)

# ── 1. Call Master Orchestration Endpoint ────────────────────────────────────
print("\n[Step 1] Triggering POST /api/analysis/run (Master Pipeline) ...")
t_start = time.perf_counter()
resp = requests.post(f"{BASE_URL}/api/analysis/run?run_explainer=true&horizon_days=30")
pipeline_duration = time.perf_counter() - t_start

assert resp.status_code == 200, f"Pipeline returned error {resp.status_code}: {resp.text}"
data = resp.json()
print(f"  Pipeline completed in {pipeline_duration:.2f} seconds.")

# ── 2. Validate Orchestration Output Contract ────────────────────────────────
print("\n[Step 2] Validating Pipeline Response Contract ...")
assert data.get("status") == "success", "status must be success"
total_anomalies = data.get("total_anomalies_detected", 0)
flagged_txs = data.get("flagged_transactions", 0)
invoices = data.get("invoices", {})
forecast = data.get("forecast", {})
impact_linking = data.get("impact_linking", {})
explanations = data.get("explanations", {})
timings = data.get("timings", {})

print(f"  Anomalies Detected:        {total_anomalies}")
print(f"  Flagged Transactions:      {flagged_txs}")
print(f"  Invoices Scanned:          {invoices.get('total_scanned')}")
print(f"  Invoice Issues Found:      {invoices.get('total_issues')} (Duplicates: {invoices.get('duplicate_count')}, Missing PO: {invoices.get('missing_po_count')})")
print(f"  Forecast Horizon:          {forecast.get('horizon_days')} days ({forecast.get('points_count')} points, method={forecast.get('method')})")
print(f"  Forecast Impacts Computed: {impact_linking.get('impacts_computed')}")
print(f"  Explanations Generated:    {explanations.get('anomalies', {}).get('explained')} anomalies, forecast={explanations.get('forecast', {}).get('explanation_source')}")

assert total_anomalies >= 15, f"Expected >= 15 anomalies, got {total_anomalies}"
assert flagged_txs >= 15, f"Expected >= 15 flagged transactions, got {flagged_txs}"
assert invoices.get("total_scanned") == 135, f"Expected 135 invoices, got {invoices.get('total_scanned')}"
assert invoices.get("duplicate_count") == 14, f"Expected 14 duplicates, got {invoices.get('duplicate_count')}"
assert invoices.get("missing_po_count") == 50, f"Expected 50 missing POs, got {invoices.get('missing_po_count')}"
assert forecast.get("points_count") == 30, f"Expected 30 forecast points, got {forecast.get('points_count')}"
assert len(forecast.get("trend_summary", "")) > 10, "trend_summary is empty"

print("  ✅ All pipeline stages completed and verified in response.")

# ── 3. Verify Specific Impact Linking and Explanations ────────────────────────
print("\n[Step 3] Verifying High-Impact Anomaly (TxID 211) & Grounded Explanations ...")
anomalies = data.get("anomalies", [])
tx_211 = next((a for a in anomalies if a.get("transaction_id") == 211), None)

assert tx_211 is not None, "High-impact anomaly TxID 211 not found in anomalies!"
impact_211 = tx_211.get("impact_on_30d_forecast")
print(f"  TxID 211 (PowerGrid Utilities $78,000):")
print(f"    - Risk Score: {tx_211.get('risk_score')}")
print(f"    - Trigger:    {tx_211.get('trigger_metric')}")
print(f"    - Impact on 30d forecast: ${impact_211:,.2f}" if impact_211 is not None else "    - Impact: None")
print(f"    - Explanation: {tx_211.get('explanation')}")

assert impact_211 is not None and impact_211 > 10000.0, f"Expected > $10,000 forecast shift for TxID 211, got {impact_211}"
assert tx_211.get("explanation") and len(tx_211.get("explanation")) > 10, "Explanation missing for TxID 211"
print("  ✅ High-impact linking and grounded explanation confirmed.")

# ── 4. Verify Subsequent Read Endpoints & Latency (< 1s) ──────────────────────
print("\n[Step 4] Verifying Dashboard Read Endpoints and Latency (< 1.0s requirement) ...")

endpoints = [
    ("/api/anomalies", "Anomalies List (T3.2 specification)"),
    ("/api/analysis/anomalies", "Anomalies List (Analysis namespace)"),
    ("/api/forecast", "Cash Flow Forecast (T3.2 specification)"),
    ("/api/invoices/issues", "Invoice Validation Issues (T3.2 specification)"),
]

all_latencies_pass = True
for path, desc in endpoints:
    t0 = time.perf_counter()
    r = requests.get(f"{BASE_URL}{path}")
    latency_ms = (time.perf_counter() - t0) * 1000

    assert r.status_code == 200, f"Failed GET {path}: {r.status_code}"
    res_data = r.json()
    count = len(res_data) if isinstance(res_data, list) else len(res_data.get("forecast", []))
    assert count > 0, f"GET {path} returned empty data!"

    is_fast = latency_ms < 1000.0
    status_tag = "PASS (<1s)" if is_fast else "FAIL (>1s)"
    if not is_fast:
        all_latencies_pass = False

    print(f"  [{status_tag}] {path:<28} -> {latency_ms:>6.2f} ms ({count} records) | {desc}")

# ── 5. Final Acceptance Evaluation ───────────────────────────────────────────
print("\n" + "=" * 76)
print("T3.1 ACCEPTANCE CRITERIA VERIFICATION")
print("=" * 76)

criterion_1 = data.get("status") == "success"
criterion_2 = total_anomalies >= 15 and invoices.get("total_issues") == 64 and forecast.get("points_count") == 30
criterion_3 = all_latencies_pass

print(f"  1. Single POST /api/analysis/run populates all dashboard data:  {'PASS' if criterion_1 and criterion_2 else 'FAIL'}")
print(f"  2. Full pipeline execution (Detection, Invoices, Forecast, LLM): {'PASS' if criterion_1 else 'FAIL'}")
print(f"  3. Subsequent GET endpoints return in under 1 second (<1s):      {'PASS' if criterion_3 else 'FAIL'}")

overall = criterion_1 and criterion_2 and criterion_3
print(f"\n  OVERALL T3.1 STATUS: {'PASS ✅ (Task T3.1 Acceptance Criteria Met)' if overall else 'FAIL ❌'}")
print("=" * 76)

if not overall:
    sys.exit(1)
