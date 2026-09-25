"""
ArthX Synthetic Seed Data Generator — T1.1
Generates statistically realistic financial transactions and invoices with deliberately
injected anomalies for testing anomaly detection and cash flow forecasting.

Design decisions:
- SEED = 42 for full determinism
- 12 months of history (Oct 2025 - Sep 2026)
- 18 recurring vendors with distinct statistical signatures
- Clear declining trend in net cash flow over the final 60 days (larger outflows)
- Injected anomalies are designed to score high on per-vendor z-score (>3 sigma)
- One HIGH-IMPACT anomaly (large outflow, dated ~30 days ago) specifically designed
  to visibly shift the 30-day cash flow forecast when excluded (the star T2.5 feature)
"""

import random
import math
import json
import csv
import os
from datetime import date, timedelta
from pathlib import Path

SEED = 42
random.seed(SEED)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent
START_DATE = date(2025, 10, 1)
END_DATE = date(2026, 9, 25)   # Today-ish; 360 days of history
HIGH_IMPACT_ANOMALY_DATE = date(2026, 8, 28)  # ~28 days ago, firmly in forecast window

# ---------------------------------------------------------------------------
# Vendor Definitions: each vendor has a distinct payment pattern
# ---------------------------------------------------------------------------
VENDORS = [
    {
        "name": "ArunCapital Payroll",
        "category": "Payroll",
        "type": "outflow",
        "pattern": "bimonthly",      # 1st and 15th
        "mean": 52000.00,
        "std": 400.00,               # very low variance — payroll is consistent
        "invoice_fraction": 0.0,     # payroll doesn't generate invoices
    },
    {
        "name": "DataSync SaaS",
        "category": "SaaS",
        "type": "outflow",
        "pattern": "monthly_first",  # 1st of each month
        "mean": 4800.00,
        "std": 50.00,                # SaaS almost never varies
        "invoice_fraction": 1.0,
    },
    {
        "name": "CloudOps Pro",
        "category": "SaaS",
        "type": "outflow",
        "pattern": "monthly_first",
        "mean": 2200.00,
        "std": 80.00,
        "invoice_fraction": 1.0,
    },
    {
        "name": "SecureVault AI",
        "category": "SaaS",
        "type": "outflow",
        "pattern": "monthly_15th",   # 15th of each month
        "mean": 1450.00,
        "std": 30.00,
        "invoice_fraction": 1.0,
    },
    {
        "name": "PowerGrid Utilities",
        "category": "Utilities",
        "type": "outflow",
        "pattern": "monthly_10th",
        "mean": 3200.00,
        "std": 420.00,               # seasonal variation
        "seasonal": True,            # higher in Jan, Jun-Jul (heating/AC)
        "invoice_fraction": 1.0,
    },
    {
        "name": "AquaFlow Services",
        "category": "Utilities",
        "type": "outflow",
        "pattern": "monthly_10th",
        "mean": 850.00,
        "std": 90.00,
        "invoice_fraction": 1.0,
    },
    {
        "name": "Broadband Express",
        "category": "Utilities",
        "type": "outflow",
        "pattern": "monthly_20th",
        "mean": 1200.00,
        "std": 20.00,               # telecom is very consistent
        "invoice_fraction": 1.0,
    },
    {
        "name": "OfficeDepot Supplies",
        "category": "Office Supplies",
        "type": "outflow",
        "pattern": "irregular",     # every 3-5 weeks, variable amount
        "mean": 680.00,
        "std": 190.00,
        "invoice_fraction": 0.7,
    },
    {
        "name": "TechGear Solutions",
        "category": "Office Supplies",
        "type": "outflow",
        "pattern": "irregular",
        "mean": 1100.00,
        "std": 350.00,
        "invoice_fraction": 0.6,
    },
    {
        "name": "FlightEasy Travel",
        "category": "Travel",
        "type": "outflow",
        "pattern": "irregular",     # quarterly peaks around conferences
        "mean": 2800.00,
        "std": 900.00,
        "invoice_fraction": 0.5,
    },
    {
        "name": "HotelStay Corp",
        "category": "Travel",
        "type": "outflow",
        "pattern": "irregular",
        "mean": 1600.00,
        "std": 550.00,
        "invoice_fraction": 0.4,
    },
    {
        "name": "LegalEdge Partners",
        "category": "Professional Services",
        "type": "outflow",
        "pattern": "monthly_end",   # end-of-month billing
        "mean": 8500.00,
        "std": 1200.00,
        "invoice_fraction": 1.0,
    },
    {
        "name": "AdNova Marketing",
        "category": "Marketing",
        "type": "outflow",
        "pattern": "monthly_first",
        "mean": 6500.00,
        "std": 800.00,
        "invoice_fraction": 1.0,
    },
    {
        "name": "MaintenancePro",
        "category": "Facilities",
        "type": "outflow",
        "pattern": "irregular",
        "mean": 2200.00,
        "std": 700.00,
        "invoice_fraction": 0.8,
    },
    {
        "name": "ClientFirst Revenue",
        "category": "Revenue",
        "type": "inflow",
        "pattern": "monthly_first",  # main revenue inflow
        "mean": 95000.00,
        "std": 8000.00,
        "invoice_fraction": 0.0,
    },
    {
        "name": "ProjectAlpha Revenue",
        "category": "Revenue",
        "type": "inflow",
        "pattern": "irregular",      # project-based, variable
        "mean": 18000.00,
        "std": 6000.00,
        "invoice_fraction": 0.0,
    },
    {
        "name": "RetainerB2B Inc",
        "category": "Revenue",
        "type": "inflow",
        "pattern": "monthly_15th",
        "mean": 12000.00,
        "std": 500.00,
        "invoice_fraction": 0.0,
    },
    {
        "name": "ContractPlus Ltd",
        "category": "Professional Services",
        "type": "outflow",
        "pattern": "monthly_end",
        "mean": 3800.00,
        "std": 400.00,
        "invoice_fraction": 1.0,
    },
]

VENDOR_MAP = {v["name"]: v for v in VENDORS}

# ---------------------------------------------------------------------------
# Helper: Gaussian sample, clamped to positive
# ---------------------------------------------------------------------------
def gauss_positive(mean, std, min_val=None):
    val = random.gauss(mean, std)
    if min_val is not None:
        val = max(min_val, val)
    return round(val, 2)

def seasonal_multiplier(d: date, vendor: dict) -> float:
    """Return a seasonal multiplier for utility vendors: higher in Jan & Jul."""
    if not vendor.get("seasonal", False):
        return 1.0
    month = d.month
    if month in (1, 12):   # Winter heating
        return random.uniform(1.18, 1.35)
    if month in (6, 7, 8): # Summer cooling
        return random.uniform(1.10, 1.25)
    if month in (3, 4, 5, 9, 10, 11):  # Mild weather
        return random.uniform(0.85, 1.0)
    return 1.0

def declining_trend_multiplier(d: date) -> float:
    """
    Returns a multiplier for OUTFLOW amounts in the last 60 days of the dataset.
    This creates a clear declining net cash flow trend that the forecasting engine can detect.
    The trend starts at END_DATE - 60 and ramps outflows up by up to 40% by END_DATE.
    """
    trend_start = END_DATE - timedelta(days=60)
    if d < trend_start:
        return 1.0
    days_into_trend = (d - trend_start).days
    # Linear ramp from 0% to 40% extra outflow over 60 days
    increase = 0.40 * (days_into_trend / 60.0)
    return 1.0 + increase

# ---------------------------------------------------------------------------
# Transaction generation utilities
# ---------------------------------------------------------------------------
def dates_for_pattern(pattern: str, year: int, month: int) -> list:
    """Return list of dates for a vendor's payment pattern within a given month."""
    try:
        if pattern == "bimonthly":
            return [date(year, month, 1), date(year, month, 15)]
        elif pattern == "monthly_first":
            return [date(year, month, 1)]
        elif pattern == "monthly_15th":
            return [date(year, month, 15)]
        elif pattern == "monthly_10th":
            return [date(year, month, 10)]
        elif pattern == "monthly_20th":
            return [date(year, month, 20)]
        elif pattern == "monthly_end":
            # Last business day approximation: use day 28
            return [date(year, month, 28)]
        elif pattern == "irregular":
            # 60% chance of appearing in any given month
            if random.random() < 0.6:
                day = random.randint(2, 27)
                return [date(year, month, day)]
            return []
    except ValueError:
        return []
    return []

# ---------------------------------------------------------------------------
# Generate all normal transactions
# ---------------------------------------------------------------------------
transactions = []
tx_id = 1

# Store normal transactions grouped by vendor for z-score verification later
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
            # Apply seasonal multiplier
            amount *= seasonal_multiplier(tx_date, vendor)
            # Apply declining trend multiplier for outflows (this is the designed trend)
            if vendor["type"] == "outflow":
                amount *= declining_trend_multiplier(tx_date)
            amount = round(amount, 2)
            transactions.append({
                "id": tx_id,
                "date": tx_date.isoformat(),
                "vendor": vendor["name"],
                "category": vendor["category"],
                "amount": amount,
                "type": vendor["type"],
                "status": "normal",
                "description": f"Regular {vendor['pattern'].replace('_', ' ')} payment",
                "_is_injected": False,
            })
            vendor_normal_amounts[vendor["name"]].append(amount)
            tx_id += 1
    # Advance to next month
    if month == 12:
        current = date(year + 1, 1, 1)
    else:
        current = date(year, month + 1, 1)

# ---------------------------------------------------------------------------
# Compute per-vendor statistics for anomaly design
# ---------------------------------------------------------------------------
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
# Inject anomalies — each designed to have z-score > 3 or pattern violation
# ---------------------------------------------------------------------------
anomaly_manifest = []  # Will be saved as JSON

def add_anomaly(tx_dict, reason, expected_zscore, anomaly_type):
    anomaly_manifest.append({
        "transaction_id": tx_dict["id"],
        "vendor": tx_dict["vendor"],
        "amount": tx_dict["amount"],
        "date": tx_dict["date"],
        "anomaly_type": anomaly_type,
        "reason": reason,
        "expected_zscore": round(expected_zscore, 2),
        "is_high_impact": tx_dict.get("_high_impact", False),
    })

# -----------------------------------------------------------------------
# GROUP A: Amount outliers (>5x vendor mean → z-score typically >8)
# -----------------------------------------------------------------------
amount_outlier_specs = [
    ("DataSync SaaS",       date(2026, 1, 1),  28500.00, "Amount is 5.9x vendor mean ($4,800)"),
    ("CloudOps Pro",        date(2026, 3, 1),  14200.00, "Amount is 6.5x vendor mean ($2,200)"),
    ("SecureVault AI",      date(2026, 5, 15), 10800.00, "Amount is 7.4x vendor mean ($1,450)"),
    ("LegalEdge Partners",  date(2026, 2, 28), 62000.00, "Amount is 7.3x vendor mean ($8,500)"),
    ("OfficeDepot Supplies",date(2026, 4, 12), 7900.00,  "Amount is 11.6x vendor mean ($680)"),
    ("Broadband Express",   date(2026, 6, 20), 8100.00,  "Amount is 6.75x vendor mean ($1,200)"),
]

for vendor_name, tx_date, amount, reason in amount_outlier_specs:
    stats = vendor_stats.get(vendor_name, {})
    std = stats.get("std", 1.0) or 1.0
    mean = stats.get("mean", amount / 6)
    zscore = (amount - mean) / std
    tx = {
        "id": tx_id,
        "date": tx_date.isoformat(),
        "vendor": vendor_name,
        "category": VENDOR_MAP[vendor_name]["category"],
        "amount": amount,
        "type": VENDOR_MAP[vendor_name]["type"],
        "status": "normal",
        "description": f"ANOMALY: {reason}",
        "_is_injected": True,
        "_high_impact": False,
    }
    add_anomaly(tx, reason, zscore, "AMOUNT_OUTLIER")
    transactions.append(tx)
    tx_id += 1

# -----------------------------------------------------------------------
# GROUP B: Off-schedule timing anomalies (payroll on wrong day)
# -----------------------------------------------------------------------
off_schedule_specs = [
    ("ArunCapital Payroll", date(2026, 3, 12), 52400.00, "Payroll paid mid-month (expected 1st or 15th)"),
    ("ArunCapital Payroll", date(2026, 7, 8),  51900.00, "Payroll paid on 8th (expected 1st or 15th)"),
    ("ClientFirst Revenue", date(2026, 5, 17), 96200.00, "Revenue received on 17th (expected 1st)"),
]

for vendor_name, tx_date, amount, reason in off_schedule_specs:
    stats = vendor_stats.get(vendor_name, {})
    std = stats.get("std", 1.0) or 1.0
    mean = stats.get("mean", amount)
    # Amount is normal, timing is not — z-score reported as timing deviation
    tx = {
        "id": tx_id,
        "date": tx_date.isoformat(),
        "vendor": vendor_name,
        "category": VENDOR_MAP[vendor_name]["category"],
        "amount": amount,
        "type": VENDOR_MAP[vendor_name]["type"],
        "status": "normal",
        "description": f"ANOMALY: {reason}",
        "_is_injected": True,
        "_high_impact": False,
    }
    add_anomaly(tx, reason, -1.0, "OFF_SCHEDULE")  # -1 signals timing anomaly
    transactions.append(tx)
    tx_id += 1

# -----------------------------------------------------------------------
# GROUP C: Round-number suspicious amounts
# -----------------------------------------------------------------------
round_number_specs = [
    ("FlightEasy Travel",   date(2026, 4, 7),  10000.00, "Suspicious round number $10,000 (vendor avg ~$2,800)"),
    ("MaintenancePro",      date(2026, 6, 14), 15000.00, "Suspicious round number $15,000 (vendor avg ~$2,200)"),
    ("TechGear Solutions",  date(2026, 8, 3),  25000.00, "Suspicious round number $25,000 (vendor avg ~$1,100)"),
]

for vendor_name, tx_date, amount, reason in round_number_specs:
    stats = vendor_stats.get(vendor_name, {})
    std = stats.get("std", 1.0) or 1.0
    mean = stats.get("mean", amount / 5)
    zscore = (amount - mean) / std
    tx = {
        "id": tx_id,
        "date": tx_date.isoformat(),
        "vendor": vendor_name,
        "category": VENDOR_MAP[vendor_name]["category"],
        "amount": amount,
        "type": VENDOR_MAP[vendor_name]["type"],
        "status": "normal",
        "description": f"ANOMALY: {reason}",
        "_is_injected": True,
        "_high_impact": False,
    }
    add_anomaly(tx, reason, zscore, "ROUND_NUMBER_OUTLIER")
    transactions.append(tx)
    tx_id += 1

# -----------------------------------------------------------------------
# GROUP D: Duplicate transactions (same vendor + amount within 48h)
# -----------------------------------------------------------------------
duplicate_specs = [
    ("DataSync SaaS",        date(2026, 2, 1),  4850.00, "Duplicate SaaS payment: same vendor+amount paid twice (Feb 1 & Feb 2)"),
    ("DataSync SaaS",        date(2026, 2, 2),  4850.00, "Duplicate SaaS payment: same vendor+amount paid twice (Feb 1 & Feb 2)"),
    ("AquaFlow Services",    date(2026, 5, 10), 862.00,  "Duplicate utility payment (May 10 & May 11)"),
    ("AquaFlow Services",    date(2026, 5, 11), 862.00,  "Duplicate utility payment (May 10 & May 11)"),
    ("LegalEdge Partners",   date(2026, 7, 28), 8750.00, "Duplicate legal fee (July 28 & July 29)"),
    ("LegalEdge Partners",   date(2026, 7, 29), 8750.00, "Duplicate legal fee (July 28 & July 29)"),
]

for vendor_name, tx_date, amount, reason in duplicate_specs:
    stats = vendor_stats.get(vendor_name, {})
    std = stats.get("std", 1.0) or 1.0
    mean = stats.get("mean", amount)
    zscore = (amount - mean) / std
    tx = {
        "id": tx_id,
        "date": tx_date.isoformat(),
        "vendor": vendor_name,
        "category": VENDOR_MAP[vendor_name]["category"],
        "amount": amount,
        "type": VENDOR_MAP[vendor_name]["type"],
        "status": "normal",
        "description": f"ANOMALY: {reason}",
        "_is_injected": True,
        "_high_impact": False,
    }
    add_anomaly(tx, reason, zscore, "DUPLICATE_TRANSACTION")
    transactions.append(tx)
    tx_id += 1

# -----------------------------------------------------------------------
# GROUP E: HIGH-IMPACT anomaly (⭐ T2.5 impact-linking feature)
# This single large outflow is designed to measurably shift the 30-day forecast.
# Vendor normal mean ~$3,200, this is $78,000 → z-score ~185 sigma.
# Amount is large enough that excluding it reduces forecast outflows by ~$75k.
# -----------------------------------------------------------------------
HIGH_IMPACT_TX_ID = tx_id
high_impact_amount = 78000.00
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
    "description": "ANOMALY [HIGH-IMPACT]: Unexplained utility charge $78,000 — 24.4x vendor average. Recent enough to shift 30-day forecast.",
    "_is_injected": True,
    "_high_impact": True,
}
add_anomaly(
    high_impact_tx,
    f"Utility charge is $78,000 vs vendor mean ${hi_stats['mean']:.0f} (z-score ~{hi_zscore:.0f}). "
    "Excluding this transaction reduces forecast outflows by ~$78,000 over the next 30 days.",
    hi_zscore,
    "HIGH_IMPACT_AMOUNT_OUTLIER",
)
transactions.append(high_impact_tx)
tx_id += 1

# -----------------------------------------------------------------------
# Sort all transactions by date
# -----------------------------------------------------------------------
transactions.sort(key=lambda t: t["date"])

# -----------------------------------------------------------------------
# Generate invoices (tied to vendors with invoice_fraction > 0)
# -----------------------------------------------------------------------
invoices = []
inv_id = 1
invoice_manifest = []  # Duplicate invoices

outflow_vendors_with_invoices = [v for v in VENDORS if v["invoice_fraction"] > 0 and v["type"] == "outflow"]

# Generate normal invoices from transactions
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
    has_po = random.random() < 0.75
    invoices.append({
        "id": inv_id,
        "vendor": tx["vendor"],
        "amount": tx["amount"],
        "invoice_date": tx_date.isoformat(),
        "due_date": (tx_date + timedelta(days=due_days)).isoformat(),
        "status": random.choices(["paid", "pending", "disputed"], weights=[0.70, 0.25, 0.05])[0],
        "po_reference": f"PO-{tx_date.year}-{inv_id:04d}" if has_po else None,
        "_is_injected": False,
    })
    inv_id += 1

# -----------------------------------------------------------------------
# Inject duplicate/near-duplicate invoices (same vendor + amount, dates within 7 days)
# -----------------------------------------------------------------------
dup_invoice_specs = [
    ("DataSync SaaS",       date(2026, 3, 1),  4800.00, date(2026, 3, 5),  "Duplicate SaaS invoice: same vendor+amount submitted 4 days apart"),
    ("CloudOps Pro",        date(2026, 4, 1),  2200.00, date(2026, 4, 6),  "Duplicate cloud invoice: 5-day gap"),
    ("LegalEdge Partners",  date(2026, 2, 28), 8500.00, date(2026, 3, 3),  "Near-duplicate legal invoice: 3-day gap"),
    ("AdNova Marketing",    date(2026, 5, 1),  6500.00, date(2026, 5, 7),  "Duplicate marketing retainer: billed twice in same period"),
    ("PowerGrid Utilities", date(2026, 6, 10), 3350.00, date(2026, 6, 14), "Near-duplicate utility invoice: 4-day gap"),
    ("OfficeDepot Supplies",date(2026, 7, 15), 695.00,  date(2026, 7, 19), "Possible duplicate supply order: same amount, 4 days apart"),
    ("ContractPlus Ltd",    date(2026, 8, 28), 3800.00, date(2026, 9, 2),  "Duplicate contract invoice spanning month boundary"),
]

for vendor_name, date1, amount, date2, reason in dup_invoice_specs:
    # First invoice
    invoices.append({
        "id": inv_id,
        "vendor": vendor_name,
        "amount": amount,
        "invoice_date": date1.isoformat(),
        "due_date": (date1 + timedelta(days=30)).isoformat(),
        "status": "pending",
        "po_reference": None,  # Missing PO makes it extra suspicious
        "_is_injected": True,
    })
    first_id = inv_id
    inv_id += 1
    # Second (duplicate) invoice
    invoices.append({
        "id": inv_id,
        "vendor": vendor_name,
        "amount": amount,
        "invoice_date": date2.isoformat(),
        "due_date": (date2 + timedelta(days=30)).isoformat(),
        "status": "pending",
        "po_reference": None,
        "_is_injected": True,
    })
    invoice_manifest.append({
        "invoice_ids": [first_id, inv_id],
        "vendor": vendor_name,
        "amount": amount,
        "invoice_date_1": date1.isoformat(),
        "invoice_date_2": date2.isoformat(),
        "gap_days": (date2 - date1).days,
        "issue_type": "DUPLICATE_INVOICE",
        "reason": reason,
    })
    inv_id += 1

# Also flag invoices missing PO reference among the normal ones (FR14)
missing_po_manifest = []
for inv in invoices:
    if not inv.get("_is_injected") and inv.get("po_reference") is None:
        missing_po_manifest.append({
            "invoice_id": inv["id"],
            "vendor": inv["vendor"],
            "amount": inv["amount"],
            "invoice_date": inv["invoice_date"],
            "issue_type": "MISSING_PO_REFERENCE",
            "reason": "Invoice has no PO reference number — cannot be matched for 3-way verification",
        })

invoices.sort(key=lambda i: i["invoice_date"])

# -----------------------------------------------------------------------
# Z-Score Verification (Acceptance criterion for T1.1)
# -----------------------------------------------------------------------
print("=" * 70)
print("Z-SCORE VERIFICATION: Injected Anomaly Distinguishability Check")
print("=" * 70)
for entry in anomaly_manifest:
    if entry["anomaly_type"] == "OFF_SCHEDULE":
        print(f"[{entry['anomaly_type']:30s}] TxID={entry['transaction_id']:4d} | {entry['vendor'][:28]} | ${entry['amount']:>10,.2f} | TIMING VIOLATION")
    else:
        print(f"[{entry['anomaly_type']:30s}] TxID={entry['transaction_id']:4d} | {entry['vendor'][:28]} | ${entry['amount']:>10,.2f} | z={entry['expected_zscore']:>7.1f}")

# -----------------------------------------------------------------------
# Cash flow trend verification
# -----------------------------------------------------------------------
print("\n" + "=" * 70)
print("CASH FLOW TREND: Monthly Net Flow Summary")
print("=" * 70)
monthly_flows = {}
for tx in transactions:
    if tx.get("_is_injected") and tx.get("_high_impact"):
        continue  # Exclude high-impact anomaly from trend summary for clarity
    d = date.fromisoformat(tx["date"])
    key = (d.year, d.month)
    sign = -1 if tx["type"] == "outflow" else 1
    monthly_flows[key] = monthly_flows.get(key, 0.0) + sign * tx["amount"]

for (year, month), net in sorted(monthly_flows.items()):
    direction = "+" if net > 0 else "-"
    bar_len = int(abs(net) / 5000)
    bar = direction * min(bar_len, 40)
    print(f"  {year}-{month:02d}: Net ${net:>10,.2f}  {bar}")

# -----------------------------------------------------------------------
# Write output files
# -----------------------------------------------------------------------
# 1. transactions.csv
tx_fields = ["id", "date", "vendor", "category", "amount", "type", "status", "description"]
with open(DATA_DIR / "transactions.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=tx_fields)
    writer.writeheader()
    for tx in transactions:
        writer.writerow({k: tx[k] for k in tx_fields})

# 2. invoices.csv
inv_fields = ["id", "vendor", "amount", "invoice_date", "due_date", "status", "po_reference"]
with open(DATA_DIR / "invoices.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=inv_fields)
    writer.writeheader()
    for inv in invoices:
        writer.writerow({k: inv[k] for k in inv_fields})

# 3. anomaly_manifest.json
full_manifest = {
    "meta": {
        "seed": SEED,
        "generated_date": END_DATE.isoformat(),
        "start_date": START_DATE.isoformat(),
        "end_date": END_DATE.isoformat(),
        "high_impact_anomaly_transaction_id": HIGH_IMPACT_TX_ID,
        "high_impact_anomaly_date": HIGH_IMPACT_ANOMALY_DATE.isoformat(),
        "high_impact_anomaly_amount": high_impact_amount,
        "high_impact_anomaly_vendor": hi_vendor,
        "description": "Record of all deliberately injected anomalies and duplicate invoices. Used for T2.1 acceptance criterion verification and T5.6 non-hardcoding test."
    },
    "anomalous_transactions": anomaly_manifest,
    "anomalous_transaction_ids": [e["transaction_id"] for e in anomaly_manifest],
    "duplicate_invoices": invoice_manifest,
    "missing_po_invoices": missing_po_manifest[:5],  # sample of the first 5
    "vendor_stats_at_generation": {
        k: {"mean": round(v["mean"], 2), "std": round(v["std"], 2), "n": v["n"]}
        for k, v in vendor_stats.items()
    }
}

with open(DATA_DIR / "anomaly_manifest.json", "w") as f:
    json.dump(full_manifest, f, indent=2)

# -----------------------------------------------------------------------
# Print sample rows and summary
# -----------------------------------------------------------------------
print("\n" + "=" * 70)
print("SAMPLE TRANSACTIONS (15 rows: mix of normal + injected)")
print("=" * 70)
sample_normals = [t for t in transactions if not t["_is_injected"]][:8]
sample_injected = [t for t in transactions if t["_is_injected"]][:7]
samples = sorted(sample_normals + sample_injected, key=lambda t: t["date"])
for tx in samples:
    flag = " 🚨 INJECTED" if tx["_is_injected"] else ""
    print(f"  [{tx['id']:4d}] {tx['date']} | {tx['type']:7s} | ${tx['amount']:>10,.2f} | {tx['vendor'][:26]:<26} | {tx['category']}{flag}")

print(f"\n✅  transactions.csv: {len(transactions)} rows")
print(f"✅  invoices.csv:     {len(invoices)} rows")
print(f"✅  anomaly_manifest.json: {len(anomaly_manifest)} anomalous transactions, {len(invoice_manifest)} duplicate invoice pairs")
print(f"\nHigh-impact anomaly: TxID={HIGH_IMPACT_TX_ID}, ${high_impact_amount:,.0f} outflow on {HIGH_IMPACT_ANOMALY_DATE} (z≈{hi_zscore:.0f}σ)")
print("\nDone.")
