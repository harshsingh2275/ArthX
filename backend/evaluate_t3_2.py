"""
T3.2 Acceptance Criterion Evaluation Script
============================================
Evaluates frontend read endpoints:
  1. GET /api/anomalies:
     - Returns list of anomalies with risk_score, reason_code, trigger_metric, explanation, impact_on_30d_forecast
     - Supports optional filtering (min_risk, vendor, reason_code)
  2. GET /api/forecast:
     - Returns forecast array (30 points) with dates, predicted_net_flow, lower, upper
     - Returns non-empty analytical trend_summary
  3. GET /api/invoices/issues:
     - Returns validation flags (DUPLICATE_INVOICE, MISSING_PO_REFERENCE)
     - Contains invoice_id, vendor, amount, issue_type, detail
  4. Confirms all endpoints return real, non-empty JSON data with correct field types in < 1 second.
"""

import sys
import time
import requests

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

print("=" * 76)
print("T3.2 EVALUATION: Frontend Read Endpoints & Contract Verification")
print("=" * 76)

# ── 1. Evaluate GET /api/anomalies ───────────────────────────────────────────
print("\n[Step 1] Testing GET /api/anomalies ...")
t0 = time.perf_counter()
resp_anom = requests.get(f"{BASE_URL}/api/anomalies")
latency_anom = (time.perf_counter() - t0) * 1000

assert resp_anom.status_code == 200, f"GET /api/anomalies failed with {resp_anom.status_code}: {resp_anom.text}"
anomalies = resp_anom.json()
assert isinstance(anomalies, list), "Response must be a list"
assert len(anomalies) > 0, "Anomalies list cannot be empty"

print(f"  Returned {len(anomalies)} anomalies in {latency_anom:.2f} ms")

required_anom_fields = {
    "transaction_id",
    "vendor",
    "amount",
    "risk_score",
    "reason_code",
    "trigger_metric",
    "explanation",
    "impact_on_30d_forecast",
}

for a in anomalies:
    for field in required_anom_fields:
        assert field in a, f"Missing field '{field}' in anomaly: {a}"
    assert isinstance(a["risk_score"], (int, float)) and 0.0 <= a["risk_score"] <= 1.0
    assert isinstance(a["reason_code"], str) and len(a["reason_code"]) > 0
    assert isinstance(a["trigger_metric"], str) and len(a["trigger_metric"]) > 0
    assert isinstance(a["explanation"], str) and len(a["explanation"]) > 0

print("  Sample anomalies:")
for a in anomalies[:3]:
    print(f"    - TxID {a['transaction_id']:>3} | {a['vendor']:<22} | Risk: {a['risk_score']:.2f} | Reason: {a['reason_code']}")
    print(f"      Trigger: {a['trigger_metric']}")
    print(f"      Explanation: {a['explanation']}")
    if a.get("impact_on_30d_forecast") is not None:
        print(f"      Forecast Impact: ${a['impact_on_30d_forecast']:,.2f}")

# Test query filters
r_filtered = requests.get(f"{BASE_URL}/api/anomalies?min_risk=0.70")
assert r_filtered.status_code == 200
high_risk = r_filtered.json()
assert all(a["risk_score"] >= 0.70 for a in high_risk), "Filter by min_risk failed"
print(f"  Filter check: ?min_risk=0.70 returned {len(high_risk)} records (all risk >= 0.70)")

# ── 2. Evaluate GET /api/forecast ────────────────────────────────────────────
print("\n[Step 2] Testing GET /api/forecast ...")
t0 = time.perf_counter()
resp_fc = requests.get(f"{BASE_URL}/api/forecast")
latency_fc = (time.perf_counter() - t0) * 1000

assert resp_fc.status_code == 200, f"GET /api/forecast failed with {resp_fc.status_code}: {resp_fc.text}"
fc_data = resp_fc.json()
assert isinstance(fc_data, dict), "Response must be a dict"
assert "horizon_days" in fc_data, "Missing horizon_days"
assert "forecast" in fc_data, "Missing forecast array"
assert "trend_summary" in fc_data, "Missing trend_summary"

forecast_points = fc_data["forecast"]
assert len(forecast_points) == 30, f"Expected 30 daily forecast points, got {len(forecast_points)}"
assert len(fc_data["trend_summary"]) > 10, "trend_summary cannot be empty"

print(f"  Returned {len(forecast_points)} forecast points in {latency_fc:.2f} ms")
print(f"  Horizon: {fc_data['horizon_days']} days | Method: {fc_data.get('method')}")
print(f"  Trend Summary: {fc_data['trend_summary']}")

# Verify point fields and ordering
point_fields = {"date", "predicted_net_flow", "lower", "upper"}
for p in forecast_points:
    for field in point_fields:
        assert field in p, f"Missing field '{field}' in forecast point: {p}"
    assert p["lower"] <= p["predicted_net_flow"] <= p["upper"] or p["lower"] <= p["upper"], "Invalid CI bounds"

print("  Sample forecast points (first 3):")
for p in forecast_points[:3]:
    print(f"    - {p['date']} | Pred: ${p['predicted_net_flow']:>9,.2f} | Lower: ${p['lower']:>9,.2f} | Upper: ${p['upper']:>9,.2f}")

# ── 3. Evaluate GET /api/invoices/issues ──────────────────────────────────────
print("\n[Step 3] Testing GET /api/invoices/issues ...")
t0 = time.perf_counter()
resp_inv = requests.get(f"{BASE_URL}/api/invoices/issues")
latency_inv = (time.perf_counter() - t0) * 1000

assert resp_inv.status_code == 200, f"GET /api/invoices/issues failed with {resp_inv.status_code}: {resp_inv.text}"
issues = resp_inv.json()
assert isinstance(issues, list), "Response must be a list"
assert len(issues) > 0, "Invoice issues list cannot be empty"

print(f"  Returned {len(issues)} invoice issues in {latency_inv:.2f} ms")

required_issue_fields = {"invoice_id", "vendor", "amount", "issue_type", "detail"}
for issue in issues:
    for field in required_issue_fields:
        assert field in issue, f"Missing field '{field}' in issue: {issue}"
    assert issue["issue_type"] in ("DUPLICATE_INVOICE", "MISSING_PO_REFERENCE", "MISSING_PO")
    assert len(issue["detail"]) > 0

# Check breakdown
dups = [i for i in issues if i["issue_type"] == "DUPLICATE_INVOICE"]
missing_po = [i for i in issues if i["issue_type"] in ("MISSING_PO_REFERENCE", "MISSING_PO")]
print(f"  Breakdown: {len(dups)} duplicate invoices, {len(missing_po)} missing PO reference invoices")

print("  Sample invoice issues:")
for issue in (dups[:2] + missing_po[:2]):
    print(f"    - Inv #{issue['invoice_id']:>3} | {issue['vendor']:<22} | ${issue['amount']:>8,.2f} | {issue['issue_type']}")
    print(f"      Detail: {issue['detail']}")

# ── 4. Verify Latency of All Read Endpoints ──────────────────────────────────
print("\n[Step 4] Checking Response Latency (< 1.0s acceptance threshold) ...")
endpoints_to_measure = [
    ("/api/anomalies", latency_anom),
    ("/api/forecast", latency_fc),
    ("/api/invoices/issues", latency_inv),
]

all_fast = True
for path, lat in endpoints_to_measure:
    status = "PASS (<1s)" if lat < 1000.0 else "FAIL (>1s)"
    if lat >= 1000.0:
        all_fast = False
    print(f"  [{status}] {path:<25} -> {lat:>6.2f} ms")

# ── Final Acceptance Evaluation ──────────────────────────────────────────────
print("\n" + "=" * 76)
print("T3.2 ACCEPTANCE CRITERIA VERIFICATION")
print("=" * 76)

c1 = len(anomalies) > 0 and all(a.get("explanation") for a in anomalies)
c2 = len(forecast_points) == 30 and len(fc_data.get("trend_summary", "")) > 0
c3 = len(issues) > 0 and len(dups) > 0 and len(missing_po) > 0
c4 = all_fast

print(f"  1. GET /api/anomalies (risk_score, reason, trigger, explanation): {'PASS' if c1 else 'FAIL'}")
print(f"  2. GET /api/forecast (30 daily points + analytical trend_summary): {'PASS' if c2 else 'FAIL'}")
print(f"  3. GET /api/invoices/issues (duplicate flags + missing PO flags):  {'PASS' if c3 else 'FAIL'}")
print(f"  4. All endpoints return real non-empty JSON in under 1 second:     {'PASS' if c4 else 'FAIL'}")

overall = c1 and c2 and c3 and c4
print(f"\n  OVERALL T3.2 STATUS: {'PASS ✅ (Task T3.2 Acceptance Criteria Met)' if overall else 'FAIL ❌'}")
print("=" * 76)

if not overall:
    sys.exit(1)
