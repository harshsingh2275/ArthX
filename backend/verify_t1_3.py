"""
Verification script for T1.3:
Test read endpoints GET /api/transactions and GET /api/invoices with filtering.
"""
import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(name, url, params=None):
    print(f"\n--- Testing: {name} ---")
    print(f"URL: {url} | Params: {params}")
    resp = requests.get(url, params=params)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code != 200:
        print(f"FAILED: {resp.text}")
        return None
    data = resp.json()
    print(f"Result count: {len(data)}")
    if data:
        print(f"Sample item: {data[0]}")
    return data

def run_tests():
    # 1. Base transactions check
    txs = test_endpoint("All Transactions", f"{BASE_URL}/api/transactions")
    assert txs is not None and len(txs) == 211, f"Expected 211 transactions, got {len(txs) if txs else 0}"
    first_tx = txs[0]
    expected_tx_keys = {"id", "date", "vendor", "category", "amount", "type", "status", "description"}
    assert expected_tx_keys.issubset(first_tx.keys()), f"Missing keys in transaction: {first_tx}"
    print("[PASS] JSON shape for transactions verified.")

    # 2. Date range filtering on transactions
    txs_filtered = test_endpoint(
        "Transactions (Date Range: 2026-06-01 to 2026-08-31)",
        f"{BASE_URL}/api/transactions",
        params={"start_date": "2026-06-01", "end_date": "2026-08-31"}
    )
    assert txs_filtered is not None and len(txs_filtered) > 0, "No transactions returned for date range"
    for t in txs_filtered:
        assert "2026-06-01" <= t["date"] <= "2026-08-31", f"Date out of range: {t['date']}"
    print(f"[PASS] Date range filter verified: {len(txs_filtered)} transactions in range.")

    # 3. Vendor filter on transactions
    txs_vendor = test_endpoint(
        "Transactions (Vendor: PowerGrid)",
        f"{BASE_URL}/api/transactions",
        params={"vendor": "PowerGrid"}
    )
    assert txs_vendor is not None and len(txs_vendor) > 0
    for t in txs_vendor:
        assert "powergrid" in t["vendor"].lower()
    print(f"[PASS] Vendor filter verified: {len(txs_vendor)} transactions for PowerGrid.")

    # 4. Status filter on transactions (all seed transactions are currently 'normal' until T2.1 flags them)
    txs_status = test_endpoint(
        "Transactions (Status: normal)",
        f"{BASE_URL}/api/transactions",
        params={"status": "normal"}
    )
    assert txs_status is not None and len(txs_status) == 211
    for t in txs_status:
        assert t["status"] == "normal"
    print(f"[PASS] Status filter verified: {len(txs_status)} normal transactions.")

    # 5. Base invoices check
    invs = test_endpoint("All Invoices", f"{BASE_URL}/api/invoices")
    assert invs is not None and len(invs) == 135, f"Expected 135 invoices, got {len(invs) if invs else 0}"
    first_inv = invs[0]
    expected_inv_keys = {"id", "vendor", "amount", "invoice_date", "due_date", "status", "po_reference"}
    assert expected_inv_keys.issubset(first_inv.keys()), f"Missing keys in invoice: {first_inv}"
    print("[PASS] JSON shape for invoices verified.")

    # 6. Date range filtering on invoices
    invs_filtered = test_endpoint(
        "Invoices (Date Range: 2026-05-01 to 2026-07-31)",
        f"{BASE_URL}/api/invoices",
        params={"start_date": "2026-05-01", "end_date": "2026-07-31"}
    )
    assert invs_filtered is not None and len(invs_filtered) > 0
    for inv in invs_filtered:
        assert "2026-05-01" <= inv["invoice_date"] <= "2026-07-31", f"Date out of range: {inv['invoice_date']}"
    print(f"[PASS] Date range filter verified: {len(invs_filtered)} invoices in range.")

    # 7. Vendor & Status combined filter on invoices
    invs_vendor_status = test_endpoint(
        "Invoices (Vendor: Cloud, Status: pending)",
        f"{BASE_URL}/api/invoices",
        params={"vendor": "Cloud", "status": "pending"}
    )
    assert invs_vendor_status is not None
    for inv in invs_vendor_status:
        assert "cloud" in inv["vendor"].lower()
        assert inv["status"] == "pending"
    print(f"[PASS] Combined vendor + status filter verified: {len(invs_vendor_status)} matching invoices.")

    print("\nALL ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
