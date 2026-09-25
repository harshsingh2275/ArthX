import json

with open("anomaly_manifest.json") as f:
    m = json.load(f)

print("=== META ===")
print(json.dumps(m["meta"], indent=2))

print("\n=== ANOMALOUS TRANSACTION IDs ===")
print(m["anomalous_transaction_ids"])

print("\n=== DUPLICATE INVOICE PAIRS ===")
for d in m["duplicate_invoices"]:
    print(json.dumps(d, indent=2))

print("\n=== VENDOR STATS ===")
vendors = ["DataSync SaaS", "PowerGrid Utilities", "LegalEdge Partners", "ArunCapital Payroll", "FlightEasy Travel"]
for v in vendors:
    s = m["vendor_stats_at_generation"].get(v, {})
    print(f"{v}: mean={s.get('mean')}, std={s.get('std')}, n={s.get('n')}")
