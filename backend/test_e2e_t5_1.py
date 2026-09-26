"""
T5.1 End-to-End Clean-Run Reliability Test
===========================================
Executes 3 consecutive clean runs from scratch:
  Flow for each run:
    1. Clean Database (unlink SQLite DB file)
    2. Ingest (re-create tables & seed transactions + invoices)
    3. Analyze (trigger POST /api/analysis/run pipeline)
    4. Dashboard Verification (read GET endpoints: anomalies, forecast, invoices/issues, latencies < 1s)
    5. Assistant Verification (query live Groq LLM assistant on key questions)

Acceptance Criteria:
  - 3 consecutive clean runs
  - Zero crashes
  - Zero empty data states
  - Zero errors
"""

import sys
import time
import requests
import subprocess
from pathlib import Path

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"
ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "data" / "arthx.db"
PYTHON_EXE = sys.executable

def clean_database():
    """Delete sqlite db file if it exists."""
    if DB_PATH.exists():
        try:
            DB_PATH.unlink()
            print(f"  [Clean DB] Successfully deleted {DB_PATH.name}")
        except Exception as e:
            print(f"  [Clean DB] Warning: unlink failed ({e}), falling back to table purge")
            # If windows file handle delayed, trigger clear via service
            from database import SessionLocal
            from services.ingestion import clear_all_tables
            db = SessionLocal()
            clear_all_tables(db)
            db.close()
    else:
        print(f"  [Clean DB] DB file {DB_PATH.name} does not exist yet (clean)")

def run_ingest():
    """Run backend/ingest.py CLI to seed fresh tables and records."""
    ingest_script = ROOT_DIR / "backend" / "ingest.py"
    res = subprocess.run([PYTHON_EXE, str(ingest_script)], capture_output=True, text=True, check=True)
    assert "Ingested 211 transactions and 135 invoices" in res.stdout, f"Unexpected ingest output: {res.stdout}"
    print("  [Ingest] Ingestion complete: 211 transactions, 135 invoices loaded.")

def run_analysis():
    """Trigger master orchestration POST /api/analysis/run."""
    t0 = time.perf_counter()
    resp = requests.post(f"{BASE_URL}/api/analysis/run?run_explainer=true&horizon_days=30", timeout=120)
    latency = time.perf_counter() - t0
    assert resp.status_code == 200, f"Analysis pipeline failed ({resp.status_code}): {resp.text}"
    data = resp.json()
    assert data.get("status") == "success", f"Pipeline status not success: {data}"
    
    anomalies_count = data.get("total_anomalies_detected", 0)
    invoices_issues = data.get("invoices", {}).get("total_issues", 0)
    forecast_points = data.get("forecast", {}).get("points_count", 0)
    
    assert anomalies_count >= 15, f"Expected >= 15 anomalies, got {anomalies_count}"
    assert invoices_issues == 64, f"Expected 64 invoice issues, got {invoices_issues}"
    assert forecast_points == 30, f"Expected 30 forecast points, got {forecast_points}"
    
    print(f"  [Analyze] Pipeline completed in {latency:.2f}s | Anomalies: {anomalies_count} | Issues: {invoices_issues} | Forecast: {forecast_points}d")
    return data

def verify_dashboard_endpoints():
    """Verify all frontend dashboard read endpoints return non-empty data in <1s."""
    endpoints = [
        ("/api/anomalies", "anomalies", lambda d: len(d) >= 15),
        ("/api/forecast", "forecast", lambda d: len(d.get("forecast", [])) == 30 and len(d.get("trend_summary", "")) > 10),
        ("/api/invoices/issues", "invoice issues", lambda d: len(d) == 64),
    ]
    
    for path, name, validator in endpoints:
        t0 = time.perf_counter()
        resp = requests.get(f"{BASE_URL}{path}", timeout=5)
        lat_ms = (time.perf_counter() - t0) * 1000
        assert resp.status_code == 200, f"Failed GET {path}: {resp.status_code}"
        data = resp.json()
        assert validator(data), f"Validation failed for {path} response shape: {data}"
        assert lat_ms < 1000.0, f"Latency exceeded 1000ms: {lat_ms:.2f}ms"
        print(f"  [Dashboard API] GET {path:<22} -> {lat_ms:>6.1f}ms (OK)")

def verify_assistant():
    """Verify live grounded queries against POST /api/assistant/query."""
    test_questions = [
        ("What's our cash flow forecast for the next 30 days?", "FORECAST", lambda a: "$" in a or "30" in a or "net" in a.lower()),
        ("Why is PowerGrid Utilities marked as high risk?", "VENDOR_ANOMALY", lambda a: "78,000" in a or "78000" in a or "powergrid" in a.lower()),
        ("What's the stock market doing today?", "OUT_OF_SCOPE", lambda a: any(w in a.lower() for w in ["don't have", "do not have", "not in the data", "only use the data", "not available"])),
    ]
    
    for q, expected_intent, check_fn in test_questions:
        t0 = time.perf_counter()
        resp = requests.post(f"{BASE_URL}/api/assistant/query", json={"question": q}, timeout=30)
        lat_ms = (time.perf_counter() - t0) * 1000
        assert resp.status_code == 200, f"Assistant failed for '{q}': {resp.status_code}"
        res = resp.json()
        intent = res.get("intent")
        answer = res.get("answer", "")
        normalized_answer = answer.replace("’", "'").replace("‘", "'")
        assert intent == expected_intent, f"Expected intent {expected_intent}, got {intent}"
        assert check_fn(normalized_answer), f"Assistant answer check failed for '{q}':\n{answer}"
        print(f"  [Assistant] \"{q[:32]}...\" -> Intent: {intent} ({lat_ms:.0f}ms) -> Valid Grounded Answer")

def run_single_cycle(cycle_num: int):
    print(f"\n{'='*70}")
    print(f"STARTING CLEAN-RUN RELIABILITY CYCLE #{cycle_num} OF 3")
    print(f"{'='*70}")
    
    # 1. Clean DB
    clean_database()
    
    # 2. Ingest
    run_ingest()
    
    # 3. Analyze
    run_analysis()
    
    # 4. Dashboard Endpoints
    verify_dashboard_endpoints()
    
    # 5. Assistant
    verify_assistant()
    
    print(f"\n>>> CYCLE #{cycle_num} COMPLETED SUCCESSFULLY WITH ZERO ERRORS. <<<\n")

def main():
    print("=" * 70)
    print("T5.1 ACCEPTANCE TEST: 3 CONSECUTIVE END-TO-END CLEAN RUNS")
    print("=" * 70)
    
    start_time = time.perf_counter()
    for i in range(1, 4):
        run_single_cycle(i)
        if i < 3:
            time.sleep(1) # short pause between cycles
            
    total_time = time.perf_counter() - start_time
    print("=" * 70)
    print(f"ALL 3 CONSECUTIVE CLEAN RUNS PASSED PERFECTLY in {total_time:.1f}s!")
    print("Zero crashes, zero empty data states, zero console/API errors.")
    print("T5.1 Acceptance Criteria Verifiably MET! [PASS]")
    print("=" * 70)

if __name__ == "__main__":
    main()
