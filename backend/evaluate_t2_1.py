"""
T2.1 Acceptance Criterion Evaluation Script
============================================
Calls POST /api/analysis/run, then evaluates the results against
anomaly_manifest.json.
"""

import json
import sys
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8000"
MANIFEST_PATH = Path(__file__).parent.parent / "data" / "anomaly_manifest.json"

print("=" * 72)
print("T2.1 EVALUATION: Running anomaly detection engine...")
print("=" * 72)

resp = requests.post(f"{BASE_URL}/api/analysis/run")
assert resp.status_code == 200, f"API error {resp.status_code}: {resp.text}"
api_result = resp.json()

print(f"\nAPI Summary:")
print(f"  Total anomalies detected:  {api_result['total_anomalies_detected']}")
print(f"  Flagged transactions:       {api_result['flagged_transactions']}")
print(f"  Flag threshold:             {api_result['flag_threshold']}")

with open(MANIFEST_PATH) as f:
    manifest = json.load(f)

injected_ids = set(manifest["anomalous_transaction_ids"])
injected_records = {r["transaction_id"]: r for r in manifest["anomalous_transactions"]}
# Dynamically obtain total transaction count from API or dataset
tx_resp = requests.get(f"{BASE_URL}/api/transactions")
if tx_resp.status_code == 200:
    total_transactions = len(tx_resp.json())
else:
    transactions_path = Path(__file__).parent.parent / "data" / "transactions.json"
    with open(transactions_path) as tf:
        total_transactions = len(json.load(tf))

print(f"\nManifest: {len(injected_ids)} deliberately injected anomaly transaction IDs")

detected: dict = {a["transaction_id"]: a for a in api_result["anomalies"]}
detected_ids = set(detected.keys())

true_positive_ids  = detected_ids & injected_ids
false_negative_ids = injected_ids - detected_ids
false_positive_ids = detected_ids - injected_ids

normal_transaction_count = total_transactions - len(injected_ids)

recall = len(true_positive_ids) / len(injected_ids) * 100
fp_rate = len(false_positive_ids) / normal_transaction_count * 100

print(f"\n{'-' * 72}")
print(f"DETECTED (True Positives) -- {len(true_positive_ids)} / {len(injected_ids)} injected anomalies caught")
print(f"{'-' * 72}")
for tid in sorted(true_positive_ids):
    d = detected[tid]
    m = injected_records[tid]
    print(f"  [CAUGHT] TxID {tid:>3}  risk={d['risk_score']:.2f}  "
          f"code={d['reason_code']:<25} manifest_type={m['anomaly_type']}")
    print(f"           trigger: {d['trigger_metric']}")

print(f"\n{'-' * 72}")
print(f"MISSED (False Negatives) -- {len(false_negative_ids)} injected anomalies NOT flagged")
print(f"{'-' * 72}")
for tid in sorted(false_negative_ids):
    m = injected_records[tid]
    print(f"  [MISSED] TxID {tid:>3}  manifest_type={m['anomaly_type']:<25}  reason: {m['reason']}")

print(f"\n{'-' * 72}")
print(f"FALSE POSITIVES -- {len(false_positive_ids)} normal transactions incorrectly flagged")
print(f"  (FP rate: {fp_rate:.1f}% of {normal_transaction_count} normal transactions)")
print(f"{'-' * 72}")
for tid in sorted(false_positive_ids):
    d = detected[tid]
    print(f"  [FP] TxID {tid:>3}  risk={d['risk_score']:.2f}  code={d['reason_code']:<25}  "
          f"vendor={d['vendor']}")
    print(f"       trigger: {d['trigger_metric']}")

print(f"\n{'=' * 72}")
print(f"ACCEPTANCE CRITERIA EVALUATION")
print(f"{'=' * 72}")
recall_pass = recall >= 80
fp_pass = fp_rate < 5
print(f"  Recall (TP rate):  {recall:.1f}%  -- target >= 80%   --> {'PASS' if recall_pass else 'FAIL'}")
print(f"  FP rate:           {fp_rate:.1f}%  -- target < 5%     --> {'PASS' if fp_pass else 'FAIL'}")

overall = recall_pass and fp_pass
print(f"\n  Overall: {'PASS -- T2.1 acceptance criteria MET' if overall else 'FAIL -- criteria not met'}")
print(f"{'=' * 72}")

print(f"\nHigh-Impact Anomaly Check (TxID 211 -- PowerGrid $78,000):")
if 211 in detected:
    hi = detected[211]
    print(f"  DETECTED  risk_score={hi['risk_score']:.2f}  reason={hi['reason_code']}")
    print(f"  trigger: {hi['trigger_metric']}")
else:
    print("  NOT DETECTED -- this anomaly must be caught")

print(f"\nTop 10 Highest-Risk Detections:")
for a in sorted(api_result["anomalies"], key=lambda x: x["risk_score"], reverse=True)[:10]:
    tag = "[INJECTED]" if a["transaction_id"] in injected_ids else "[NORMAL]  "
    print(f"  {tag} TxID {a['transaction_id']:>3}  risk={a['risk_score']:.2f}  "
          f"{a['reason_code']:<25} vendor={a['vendor']}")

if not overall:
    sys.exit(1)
