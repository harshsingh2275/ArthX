"""
T2.4 Acceptance Criterion Evaluation Script
============================================
Evaluates the Invoice Validation Logic against:
  1. API endpoint POST /api/invoices/validate & GET /api/invoices/issues
  2. Deliberately injected duplicate invoices recorded in data/anomaly_manifest.json
  3. Missing PO reference invoices
  4. Output contract format: {invoice_id, issue_type, detail, vendor, amount}
  5. Pure unit / edge case validation
"""

import json
import sys
from pathlib import Path
from datetime import date, timedelta
import requests

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"
MANIFEST_PATH = Path(__file__).parent.parent / "data" / "anomaly_manifest.json"

print("=" * 76)
print("T2.4 EVALUATION: Testing Invoice Validation Logic (API & Seed Data)")
print("=" * 76)

# ── 1. Call Validation Endpoint ──────────────────────────────────────────────
print("\n[Step 1] Calling POST /api/invoices/validate ...")
try:
    resp = requests.post(f"{BASE_URL}/api/invoices/validate?window_days=7")
    assert resp.status_code == 200, f"API returned {resp.status_code}: {resp.text}"
    val_result = resp.json()
except Exception as e:
    print(f"❌ Failed to call validation API: {e}")
    sys.exit(1)

print("  API Response Summary:")
print(f"    Status:                  {val_result.get('status')}")
print(f"    Total Invoices Scanned:  {val_result.get('total_invoices_scanned')}")
print(f"    Total Issues Found:      {val_result.get('total_issues_found')}")
print(f"    Duplicate Invoices:      {val_result.get('duplicate_count')}")
print(f"    Missing PO Invoices:     {val_result.get('missing_po_count')}")

issues = val_result.get("issues", [])
assert len(issues) > 0, "No issues returned by validation endpoint"

# ── 2. Verify Output Contract Shape ──────────────────────────────────────────
print("\n[Step 2] Verifying Output Contract Shape ...")
required_keys = {"invoice_id", "issue_type", "detail", "vendor", "amount"}
for issue in issues[:5]:
    missing_keys = required_keys - set(issue.keys())
    assert not missing_keys, f"Issue missing required keys: {missing_keys} in {issue}"
    assert isinstance(issue["invoice_id"], int), "invoice_id must be int"
    assert isinstance(issue["issue_type"], str) and len(issue["issue_type"]) > 0, "issue_type must be non-empty str"
    assert isinstance(issue["detail"], str) and len(issue["detail"]) > 0, "detail must be non-empty str"
print(f"  ✅ Output contract verified across {len(issues)} issues (contains invoice_id, issue_type, detail, vendor, amount)")

# ── 3. Evaluate Duplicate Detection Against Injected Seed Invoices ───────────
print("\n[Step 3] Evaluating Duplicate Detection against Manifest Injected Data ...")
with open(MANIFEST_PATH, "r") as f:
    manifest = json.load(f)

injected_duplicate_pairs = manifest.get("duplicate_invoices", [])
print(f"  Manifest specifies {len(injected_duplicate_pairs)} duplicate pairs.")

expected_duplicate_ids = set()
for pair in injected_duplicate_pairs:
    for i_id in pair["invoice_ids"]:
        expected_duplicate_ids.add(i_id)

print(f"  Expected duplicate invoice IDs ({len(expected_duplicate_ids)}): {sorted(expected_duplicate_ids)}")

duplicate_issues = [i for i in issues if i["issue_type"] == "DUPLICATE_INVOICE"]
detected_duplicate_ids = {i["invoice_id"] for i in duplicate_issues}
print(f"  Detected duplicate invoice IDs ({len(detected_duplicate_ids)}): {sorted(detected_duplicate_ids)}")

# Metrics
caught_duplicate_ids = expected_duplicate_ids & detected_duplicate_ids
missed_duplicate_ids = expected_duplicate_ids - detected_duplicate_ids
false_positive_ids = detected_duplicate_ids - expected_duplicate_ids

recall = len(caught_duplicate_ids) / len(expected_duplicate_ids) * 100 if expected_duplicate_ids else 0.0

print(f"\n{'-' * 76}")
print("DUPLICATE DETECTION RESULTS:")
print(f"{'-' * 76}")
for pair in injected_duplicate_pairs:
    ids = pair["invoice_ids"]
    status_str = "CAUGHT" if all(i in detected_duplicate_ids for i in ids) else "MISSED"
    print(f"  [{status_str}] Invoices {ids} | {pair['vendor']} | ${pair['amount']:,.2f} | {pair['gap_days']}d gap")
    for i_id in ids:
        matching_issues = [i for i in duplicate_issues if i["invoice_id"] == i_id]
        if matching_issues:
            print(f"           -> Inv #{i_id}: {matching_issues[0]['detail']}")

if missed_duplicate_ids:
    print(f"\n  ❌ Missed duplicate IDs: {sorted(missed_duplicate_ids)}")
else:
    print("\n  ✅ Zero missed duplicates: 100% of injected duplicate invoices caught!")

if false_positive_ids:
    print(f"  ⚠️  False positive duplicate IDs: {sorted(false_positive_ids)}")
else:
    print("  ✅ Zero false positive duplicates among normal invoices!")

# ── 4. Evaluate Missing PO Reference Invoices ────────────────────────────────
print(f"\n{'-' * 76}")
print("[Step 4] Evaluating Missing PO Reference Detection ...")
print(f"{'-' * 76}")

missing_po_issues = [
    i for i in issues
    if i["issue_type"] in ("MISSING_PO_REFERENCE", "MISSING_PO")
]
detected_missing_po_ids = {i["invoice_id"] for i in missing_po_issues}

manifest_missing_po = manifest.get("missing_po_invoices", [])
manifest_missing_ids = {m["invoice_id"] for m in manifest_missing_po}
print(f"  Checking sample missing PO invoices from manifest: {sorted(manifest_missing_ids)}")

all_sample_caught = manifest_missing_ids.issubset(detected_missing_po_ids)
for m in manifest_missing_po:
    caught = m["invoice_id"] in detected_missing_po_ids
    print(f"  [{'CAUGHT' if caught else 'MISSED'}] Inv #{m['invoice_id']} | {m['vendor']} | ${m['amount']:,.2f}")
    if caught:
        m_issue = next(i for i in missing_po_issues if i["invoice_id"] == m["invoice_id"])
        print(f"           -> {m_issue['detail']}")

print(f"  Total invoices flagged for missing PO: {len(detected_missing_po_ids)}")
assert all_sample_caught, "Not all manifest missing PO invoices were caught!"

# ── 5. Evaluate GET /api/invoices/issues Endpoint ────────────────────────────
print(f"\n{'-' * 76}")
print("[Step 5] Evaluating GET /api/invoices/issues Read Endpoint ...")
print(f"{'-' * 76}")

resp_all = requests.get(f"{BASE_URL}/api/invoices/issues")
assert resp_all.status_code == 200, f"Failed GET /api/invoices/issues: {resp_all.text}"
stored_issues = resp_all.json()
print(f"  GET /api/invoices/issues returned {len(stored_issues)} persisted records.")
assert len(stored_issues) == len(issues), f"Persisted count ({len(stored_issues)}) != returned count ({len(issues)})"

# Test filter by issue_type=DUPLICATE_INVOICE
resp_dups = requests.get(f"{BASE_URL}/api/invoices/issues?issue_type=DUPLICATE_INVOICE")
assert resp_dups.status_code == 200
dups_filtered = resp_dups.json()
print(f"  GET /api/invoices/issues?issue_type=DUPLICATE_INVOICE returned {len(dups_filtered)} records.")
assert all(d["issue_type"] == "DUPLICATE_INVOICE" for d in dups_filtered)
assert len(dups_filtered) == len(duplicate_issues)

# Test filter by invoice_id
resp_single = requests.get(f"{BASE_URL}/api/invoices/issues?invoice_id=122")
assert resp_single.status_code == 200
single_issues = resp_single.json()
print(f"  GET /api/invoices/issues?invoice_id=122 returned {len(single_issues)} records:")
for s in single_issues:
    print(f"    - Type: {s['issue_type']} | Detail: {s['detail']}")

# ── 6. Unit Edge Case Verification ───────────────────────────────────────────
print(f"\n{'-' * 76}")
print("[Step 6] Unit / Edge Case Verification ...")
print(f"{'-' * 76}")

from ml.invoice_validator import (
    find_duplicate_invoices,
    find_missing_po_invoices,
    validate_invoices,
)

mock_invoices = [
    # Within 7 days, identical amount -> DUPLICATE
    {"id": 1001, "vendor": "Test Vendor", "amount": 500.0, "invoice_date": "2026-01-01", "po_reference": "PO-1"},
    {"id": 1002, "vendor": "Test Vendor", "amount": 500.0, "invoice_date": "2026-01-05", "po_reference": "PO-2"},
    # Different vendor, identical amount -> NOT DUPLICATE
    {"id": 1003, "vendor": "Other Vendor", "amount": 500.0, "invoice_date": "2026-01-03", "po_reference": "PO-3"},
    # Same vendor, different amount -> NOT DUPLICATE
    {"id": 1004, "vendor": "Test Vendor", "amount": 505.0, "invoice_date": "2026-01-02", "po_reference": "PO-4"},
    # Same vendor & amount, but 9 days apart (> 7 days) -> NOT DUPLICATE
    {"id": 1005, "vendor": "Test Vendor", "amount": 500.0, "invoice_date": "2026-01-14", "po_reference": "PO-5"},
    # Missing PO cases (different amounts so they don't trigger duplicate rule)
    {"id": 1006, "vendor": "Test Vendor", "amount": 110.0, "invoice_date": "2026-01-01", "po_reference": None},
    {"id": 1007, "vendor": "Test Vendor", "amount": 120.0, "invoice_date": "2026-01-01", "po_reference": ""},
    {"id": 1008, "vendor": "Test Vendor", "amount": 130.0, "invoice_date": "2026-01-01", "po_reference": "null"},
]

unit_dups = find_duplicate_invoices(mock_invoices, window_days=7)
unit_dup_ids = {d.invoice_id for d in unit_dups}
assert unit_dup_ids == {1001, 1002}, f"Unexpected unit duplicates: {unit_dup_ids} (expected {{1001, 1002}})"
print("  ✅ Unit check: Only exact vendor + amount within 7-day window flagged as duplicate.")

unit_mpo = find_missing_po_invoices(mock_invoices)
unit_mpo_ids = {m.invoice_id for m in unit_mpo}
assert unit_mpo_ids == {1006, 1007, 1008}, f"Unexpected unit missing PO: {unit_mpo_ids} (expected {{1006, 1007, 1008}})"
print("  ✅ Unit check: Missing, empty, or null PO references properly identified.")

# ── Final Acceptance Evaluation ──────────────────────────────────────────────
print("\n" + "=" * 76)
print("T2.4 ACCEPTANCE CRITERIA VERIFICATION")
print("=" * 76)
pass_recall = recall >= 100.0
pass_fp = len(false_positive_ids) == 0
pass_contract = len(issues) > 0 and all(required_keys.issubset(set(i.keys())) for i in issues)
pass_missing_po = all_sample_caught

print(f"  Duplicate Recall:        {recall:.1f}% (target: 100% of injected duplicates) --> {'PASS' if pass_recall else 'FAIL'}")
print(f"  Duplicate False Positives: {len(false_positive_ids)} normal invoices flagged        --> {'PASS' if pass_fp else 'FAIL'}")
print(f"  Missing PO Detection:    All manifest samples flagged                      --> {'PASS' if pass_missing_po else 'FAIL'}")
print(f"  Output Contract Shape:   {{invoice_id, issue_type, detail, vendor, amount}}  --> {'PASS' if pass_contract else 'FAIL'}")

overall = pass_recall and pass_fp and pass_contract and pass_missing_po
print(f"\n  OVERALL T2.4 STATUS: {'PASS ✅ (Task T2.4 Acceptance Criteria Met)' if overall else 'FAIL ❌'}")
print("=" * 76)

if not overall:
    sys.exit(1)
