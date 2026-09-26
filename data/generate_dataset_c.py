"""
ArthX Synthetic Seed Data Generator — Dataset C: CASH FLOW CRISIS
===================================================================
Same schema as A, but:
  - Fewer anomalies (8 injected, mostly minor)
  - Dramatically steeper declining cash flow trend in the last 90 days
    (outflows ramp up 70% by end, revenue also declines 20%)
  - The big story is the FORECAST ENGINE — detecting a cash flow cliff
  - The high-impact anomaly causes a visible but not dominant forecast shift
  - Useful for showcasing forecasting + impact linking vs A's balanced view

SEED = 271 (deterministic)
"""

import random
import math
import json
import csv
from datetime import date, timedelta
from pathlib import Path

SEED = 271
random.seed(SEED)

DATA_DIR = Path(__file__).parent / "dataset_c"
DATA_DIR.mkdir(exist_ok=True)

START_DATE = date(2025, 10, 1)
END_DATE   = date(2026, 9, 25)
HIGH_IMPACT_ANOMALY_DATE = date(2026, 9, 1)

VENDORS = [
    {"name": "ArunCapital Payroll",   "category": "Payroll",               "type": "outflow", "pattern": "bimonthly",     "mean": 52000.00, "std": 400.00,   "invoice_fraction": 0.0},
    {"name": "DataSync SaaS",         "category": "SaaS",                  "type": "outflow", "pattern": "monthly_first", "mean": 4800.00,  "std": 50.00,    "invoice_fraction": 1.0},
    {"name": "CloudOps Pro",          "category": "SaaS",                  "type": "outflow", "pattern": "monthly_first", "mean": 2200.00,  "std": 80.00,    "invoice_fraction": 1.0},
    {"name": "SecureVault AI",        "category": "SaaS",                  "type": "outflow", "pattern": "monthly_15th",  "mean": 1450.00,  "std": 30.00,    "invoice_fraction": 1.0},
    {"name": "PowerGrid Utilities",   "category": "Utilities",             "type": "outflow", "pattern": "monthly_10th",  "mean": 3200.00,  "std": 420.00,   "invoice_fraction": 1.0, "seasonal": True},
    {"name": "AquaFlow Services",     "category": "Utilities",             "type": "outflow", "pattern": "monthly_10th",  "mean": 850.00,   "std": 90.00,    "invoice_fraction": 1.0},
    {"name": "Broadband Express",     "category": "Utilities",             "type": "outflow", "pattern": "monthly_20th",  "mean": 1200.00,  "std": 20.00,    "invoice_fraction": 1.0},
    {"name": "OfficeDepot Supplies",  "category": "Office Supplies",       "type": "outflow", "pattern": "irregular",     "mean": 680.00,   "std": 190.00,   "invoice_fraction": 0.7},
    {"name": "TechGear Solutions",    "category": "Office Supplies",       "type": "outflow", "pattern": "irregular",     "mean": 1100.00,  "std": 350.00,   "invoice_fraction": 0.6},
    {"name": "FlightEasy Travel",     "category": "Travel",                "type": "outflow", "pattern": "irregular",     "mean": 2800.00,  "std": 900.00,   "invoice_fraction": 0.5},
    {"name": "HotelStay Corp",        "category": "Travel",                "type": "outflow", "pattern": "irregular",     "mean": 1600.00,  "std": 550.00,   "invoice_fraction": 0.4},
    {"name": "LegalEdge Partners",    "category": "Professional Services", "type": "outflow", "pattern": "monthly_end",   "mean": 8500.00,  "std": 1200.00,  "invoice_fraction": 1.0},
    {"name": "AdNova Marketing",      "category": "Marketing",             "type": "outflow", "pattern": "monthly_first", "mean": 6500.00,  "std": 800.00,   "invoice_fraction": 1.0},
    {"name": "MaintenancePro",        "category": "Facilities",            "type": "outflow", "pattern": "irregular",     "mean": 2200.00,  "std": 700.00,   "invoice_fraction": 0.8},
    # Revenue sources DECLINING — this creates the cash flow crisis
    {"name": "ClientFirst Revenue",   "category": "Revenue",               "type": "inflow",  "pattern": "monthly_first", "mean": 95000.00, "std": 8000.00,  "invoice_fraction": 0.0, "revenue_decline": True},
    {"name": "ProjectAlpha Revenue",  "category": "Revenue",               "type": "inflow",  "pattern": "irregular",     "mean": 18000.00, "std": 6000.00,  "invoice_fraction": 0.0},
    {"name": "RetainerB2B Inc",       "category": "Revenue",               "type": "inflow",  "pattern": "monthly_15th",  "mean": 12000.00, "std": 500.00,   "invoice_fraction": 0.0},
    {"name": "ContractPlus Ltd",      "category": "Professional Services", "type": "outflow", "pattern": "monthly_end",   "mean": 3800.00,  "std": 400.00,   "invoice_fraction": 1.0},
]

VENDOR_MAP = {v["name"]: v for v in VENDORS}

def gauss_positive(mean, std, min_val=None):
    val = random.gauss(mean, std)
    if min_val is not None:
        val = max(min_val, val)
    return round(val, 2)

def seasonal_multiplier(d, vendor):
    if not vendor.get("seasonal", False):
        return 1.0
    month = d.month
    if month in (1, 12):   return random.uniform(1.18, 1.35)
    if month in (6, 7, 8): return random.uniform(1.10, 1.25)
    return random.uniform(0.85, 1.0)

def outflow_crisis_multiplier(d):
    """Very steep ramp: outflows climb 70% over the last 90 days."""
    trend_start = END_DATE - timedelta(days=90)
    if d < trend_start:
        return 1.0
    days_into_trend = (d - trend_start).days
    increase = 0.70 * (days_into_trend / 90.0)
    return 1.0 + increase

def revenue_decline_multiplier(d):
    """Revenue shrinks 25% over the last 90 days — the cash flow crisis driver."""
    trend_start = END_DATE - timedelta(days=90)
    if d < trend_start:
        return 1.0
    days_into_trend = (d - trend_start).days
    decrease = 0.25 * (days_into_trend / 90.0)
    return 1.0 - decrease

def dates_for_pattern(pattern, year, month):
    try:
        if pattern == "bimonthly":       return [date(year, month, 1), date(year, month, 15)]
        elif pattern == "monthly_first": return [date(year, month, 1)]
        elif pattern == "monthly_15th":  return [date(year, month, 15)]
        elif pattern == "monthly_10th":  return [date(year, month, 10)]
        elif pattern == "monthly_20th":  return [date(year, month, 20)]
        elif pattern == "monthly_end":   return [date(year, month, 28)]
        elif pattern == "irregular":
            if random.random() < 0.6:
                day = random.randint(2, 27)
                return [date(year, month, day)]
            return []
    except ValueError:
        return []
    return []

# ---------------------------------------------------------------------------
# Generate normal transactions with crisis trend
# ---------------------------------------------------------------------------
transactions = []
tx_id = 1
vendor_normal_amounts = {v["name"]: [] for v in VENDORS}

current = START_DATE
while current <= END_DATE:
    year, month = current.year, current.month
    for vendor in VENDORS:
        dates = dates_for_pattern(vendor["pattern"], year, month)
        for tx_date in dates:
            if tx_date < START_DATE or tx_date > END_DATE:
                continue
            amount = gauss_positive(vendor["mean"], vendor["std"], min_val=10.0)
            amount *= seasonal_multiplier(tx_date, vendor)
            if vendor["type"] == "outflow":
                amount *= outflow_crisis_multiplier(tx_date)
            elif vendor.get("revenue_decline"):
                amount *= revenue_decline_multiplier(tx_date)
            amount = round(amount, 2)
            transactions.append({
                "id": tx_id, "date": tx_date.isoformat(), "vendor": vendor["name"],
                "category": vendor["category"], "amount": amount,
                "type": vendor["type"], "status": "normal",
                "description": f"Regular {vendor['pattern'].replace('_', ' ')} payment",
                "_is_injected": False,
            })
            vendor_normal_amounts[vendor["name"]].append(amount)
            tx_id += 1
    if month == 12: current = date(year + 1, 1, 1)
    else:           current = date(year, month + 1, 1)

# Per-vendor stats
vendor_stats = {}
for vname, amounts in vendor_normal_amounts.items():
    if not amounts:
        continue
    n = len(amounts)
    mean = sum(amounts) / n
    variance = sum((x - mean) ** 2 for x in amounts) / n if n > 1 else 1.0
    std = math.sqrt(variance)
    vendor_stats[vname] = {"mean": mean, "std": std, "n": n, "amounts": amounts}

# ---------------------------------------------------------------------------
# Inject FEWER anomalies (5-10, mostly minor)
# ---------------------------------------------------------------------------
anomaly_manifest = []

def add_anomaly(tx_dict, reason, expected_zscore, anomaly_type):
    anomaly_manifest.append({
        "transaction_id": tx_dict["id"], "vendor": tx_dict["vendor"],
        "amount": tx_dict["amount"], "date": tx_dict["date"],
        "anomaly_type": anomaly_type, "reason": reason,
        "expected_zscore": round(expected_zscore, 2),
        "is_high_impact": tx_dict.get("_high_impact", False),
    })

# Only 7 injected anomalies — the forecast tells the story
minor_anomaly_specs = [
    ("DataSync SaaS",       date(2026, 1, 1),  28500.00, "AMOUNT_OUTLIER",    "Amount is 5.9x vendor mean ($4,800)"),
    ("CloudOps Pro",        date(2026, 3, 1),  14200.00, "AMOUNT_OUTLIER",    "Amount is 6.5x vendor mean ($2,200)"),
    ("ArunCapital Payroll", date(2026, 4, 12), 52400.00, "OFF_SCHEDULE",      "Payroll paid mid-month (expected 1st or 15th)"),
    ("FlightEasy Travel",   date(2026, 5, 7),  10000.00, "ROUND_NUMBER_OUTLIER", "Suspicious round $10,000 (vendor avg ~$2,800)"),
    ("LegalEdge Partners",  date(2026, 2, 28), 35000.00, "AMOUNT_OUTLIER",    "Amount is 4.1x vendor mean ($8,500)"),
    ("DataSync SaaS",       date(2026, 4, 1),  4850.00,  "DUPLICATE_TRANSACTION", "Duplicate SaaS payment Apr 1"),
    ("DataSync SaaS",       date(2026, 4, 2),  4850.00,  "DUPLICATE_TRANSACTION", "Duplicate SaaS payment Apr 2 (pair with Apr 1)"),
]

for vendor_name, tx_date, amount, anomaly_type, reason in minor_anomaly_specs:
    stats = vendor_stats.get(vendor_name, {})
    std = stats.get("std", 1.0) or 1.0
    mean = stats.get("mean", amount / 5)
    zscore = -1.0 if anomaly_type == "OFF_SCHEDULE" else (amount - mean) / std
    tx = {
        "id": tx_id, "date": tx_date.isoformat(), "vendor": vendor_name,
        "category": VENDOR_MAP[vendor_name]["category"], "amount": amount,
        "type": VENDOR_MAP[vendor_name]["type"], "status": "normal",
        "description": f"ANOMALY: {reason}", "_is_injected": True, "_high_impact": False,
    }
    add_anomaly(tx, reason, zscore, anomaly_type)
    transactions.append(tx)
    tx_id += 1

# HIGH-IMPACT anomaly — large enough to move the forecast, but the trend is the main story
HIGH_IMPACT_TX_ID = tx_id
high_impact_amount = 55000.00
hi_vendor = "PowerGrid Utilities"
hi_stats = vendor_stats.get(hi_vendor, {"mean": 3200, "std": 420})
hi_zscore = (high_impact_amount - hi_stats["mean"]) / hi_stats["std"]

high_impact_tx = {
    "id": HIGH_IMPACT_TX_ID,
    "date": HIGH_IMPACT_ANOMALY_DATE.isoformat(),
    "vendor": hi_vendor,
    "category": "Utilities",
    "amount": high_impact_amount,
    "type": "outflow",
    "status": "normal",
    "description": "ANOMALY [HIGH-IMPACT]: Unexplained utility charge $55,000 — 17.2x vendor average. Amplifies the forecast cash flow crisis.",
    "_is_injected": True, "_high_impact": True,
}
add_anomaly(
    high_impact_tx,
    f"Utility charge $55,000 vs vendor mean ${hi_stats['mean']:.0f} (z-score ~{hi_zscore:.0f}). "
    "Combined with the declining revenue trend, excluding this shifts the 30-day forecast by ~$55,000.",
    hi_zscore, "HIGH_IMPACT_AMOUNT_OUTLIER",
)
transactions.append(high_impact_tx)
tx_id += 1

transactions.sort(key=lambda t: t["date"])

# ---------------------------------------------------------------------------
# Generate invoices — fewer duplicate pairs (5)
# ---------------------------------------------------------------------------
invoices = []
inv_id = 1
invoice_manifest = []

for tx in transactions:
    if tx.get("_is_injected"):
        continue
    vendor = VENDOR_MAP.get(tx["vendor"])
    if not vendor or vendor.get("invoice_fraction", 0) == 0:
        continue
    if random.random() > vendor["invoice_fraction"]:
        continue
    tx_date = date.fromisoformat(tx["date"])
    due_days = random.randint(14, 45)
    has_po = random.random() < 0.72
    invoices.append({
        "id": inv_id, "vendor": tx["vendor"], "amount": tx["amount"],
        "invoice_date": tx_date.isoformat(),
        "due_date": (tx_date + timedelta(days=due_days)).isoformat(),
        "status": random.choices(["paid", "pending", "disputed"], weights=[0.70, 0.25, 0.05])[0],
        "po_reference": f"PO-{tx_date.year}-{inv_id:04d}" if has_po else None,
        "_is_injected": False,
    })
    inv_id += 1

dup_invoice_specs = [
    ("DataSync SaaS",       date(2026, 3, 1),  4800.00, date(2026, 3, 5),  "Duplicate SaaS invoice: 4-day gap"),
    ("CloudOps Pro",        date(2026, 4, 1),  2200.00, date(2026, 4, 6),  "Duplicate cloud invoice: 5-day gap"),
    ("LegalEdge Partners",  date(2026, 2, 28), 8500.00, date(2026, 3, 3),  "Near-duplicate legal invoice: 3-day gap"),
    ("AdNova Marketing",    date(2026, 5, 1),  6500.00, date(2026, 5, 7),  "Duplicate marketing retainer"),
    ("PowerGrid Utilities", date(2026, 6, 10), 3350.00, date(2026, 6, 14), "Near-duplicate utility invoice: 4-day gap"),
]

for vendor_name, date1, amount, date2, reason in dup_invoice_specs:
    invoices.append({
        "id": inv_id, "vendor": vendor_name, "amount": amount,
        "invoice_date": date1.isoformat(),
        "due_date": (date1 + timedelta(days=30)).isoformat(),
        "status": "pending", "po_reference": None, "_is_injected": True,
    })
    first_id = inv_id; inv_id += 1
    invoices.append({
        "id": inv_id, "vendor": vendor_name, "amount": amount,
        "invoice_date": date2.isoformat(),
        "due_date": (date2 + timedelta(days=30)).isoformat(),
        "status": "pending", "po_reference": None, "_is_injected": True,
    })
    invoice_manifest.append({
        "invoice_ids": [first_id, inv_id], "vendor": vendor_name,
        "amount": amount, "invoice_date_1": date1.isoformat(),
        "invoice_date_2": date2.isoformat(), "gap_days": (date2 - date1).days,
        "issue_type": "DUPLICATE_INVOICE", "reason": reason,
    })
    inv_id += 1

missing_po_manifest = []
for inv in invoices:
    if not inv.get("_is_injected") and inv.get("po_reference") is None:
        missing_po_manifest.append({
            "invoice_id": inv["id"], "vendor": inv["vendor"],
            "amount": inv["amount"], "invoice_date": inv["invoice_date"],
            "issue_type": "MISSING_PO_REFERENCE",
            "reason": "Invoice has no PO reference number",
        })

invoices.sort(key=lambda i: i["invoice_date"])

# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
print("=" * 70)
print("DATASET C (CASH FLOW CRISIS) — VERIFICATION")
print("=" * 70)
for entry in anomaly_manifest:
    if entry["anomaly_type"] == "OFF_SCHEDULE":
        print(f"[{entry['anomaly_type']:30s}] TxID={entry['transaction_id']:4d} | {entry['vendor'][:28]} | ${entry['amount']:>10,.2f} | TIMING")
    else:
        print(f"[{entry['anomaly_type']:30s}] TxID={entry['transaction_id']:4d} | {entry['vendor'][:28]} | ${entry['amount']:>10,.2f} | z={entry['expected_zscore']:>7.1f}")

print("\n" + "=" * 70)
print("MONTHLY CASH FLOW TREND (should show sharp decline from Jul onward)")
print("=" * 70)
monthly_flows = {}
for tx in transactions:
    if tx.get("_is_injected") and tx.get("_high_impact"):
        continue
    d = date.fromisoformat(tx["date"])
    key = (d.year, d.month)
    sign = -1 if tx["type"] == "outflow" else 1
    monthly_flows[key] = monthly_flows.get(key, 0.0) + sign * tx["amount"]
for (year, month), net in sorted(monthly_flows.items()):
    direction = "+" if net > 0 else "-"
    bar = direction * min(int(abs(net) / 5000), 40)
    print(f"  {year}-{month:02d}: Net ${net:>10,.2f}  {bar}")

# ---------------------------------------------------------------------------
# Write output files
# ---------------------------------------------------------------------------
tx_fields = ["id", "date", "vendor", "category", "amount", "type", "status", "description"]
with open(DATA_DIR / "transactions.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=tx_fields)
    writer.writeheader()
    for tx in transactions:
        writer.writerow({k: tx[k] for k in tx_fields})

inv_fields = ["id", "vendor", "amount", "invoice_date", "due_date", "status", "po_reference"]
with open(DATA_DIR / "invoices.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=inv_fields)
    writer.writeheader()
    for inv in invoices:
        writer.writerow({k: inv[k] for k in inv_fields})

full_manifest = {
    "meta": {
        "dataset": "C", "label": "Cash Flow Crisis",
        "seed": SEED, "generated_date": END_DATE.isoformat(),
        "start_date": START_DATE.isoformat(), "end_date": END_DATE.isoformat(),
        "high_impact_anomaly_transaction_id": HIGH_IMPACT_TX_ID,
        "high_impact_anomaly_date": HIGH_IMPACT_ANOMALY_DATE.isoformat(),
        "high_impact_anomaly_amount": high_impact_amount,
        "high_impact_anomaly_vendor": hi_vendor,
        "description": "Cash flow crisis: steep outflow ramp + revenue decline over last 90 days. Only 8 anomalies.",
    },
    "anomalous_transactions": anomaly_manifest,
    "anomalous_transaction_ids": [e["transaction_id"] for e in anomaly_manifest],
    "duplicate_invoices": invoice_manifest,
    "missing_po_invoices": missing_po_manifest[:5],
    "vendor_stats_at_generation": {
        k: {"mean": round(v["mean"], 2), "std": round(v["std"], 2), "n": v["n"]}
        for k, v in vendor_stats.items()
    },
}

with open(DATA_DIR / "anomaly_manifest.json", "w") as f:
    json.dump(full_manifest, f, indent=2)

print(f"\n✅  transactions.csv:        {len(transactions)} rows")
print(f"✅  invoices.csv:            {len(invoices)} rows")
print(f"✅  anomaly_manifest.json:   {len(anomaly_manifest)} anomalous transactions, {len(invoice_manifest)} duplicate invoice pairs")
print(f"\nHigh-impact anomaly: TxID={HIGH_IMPACT_TX_ID}, ${high_impact_amount:,.0f} on {HIGH_IMPACT_ANOMALY_DATE} (z≈{hi_zscore:.0f}σ)")
print("\nDone — Dataset C written to:", DATA_DIR)
